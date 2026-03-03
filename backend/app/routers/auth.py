"""
Authentication router: register and login.
Both endpoints are fully async and complete in < 50ms (excluding bcrypt work factor).

⚠️ CAPACITY NOTE: bcrypt with cost factor 12 takes ~250ms per hash on a modern CPU.
For 50 concurrent logins, that's 50 × 250ms = 12.5 seconds of CPU time.
With uvicorn --workers 4, throughput is 4 × (1000ms / 250ms) = 16 logins/second.
For burst > 20 logins/second: offload hashing to executor (already done below).
"""
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..schemas.user import Token, UserCreate, UserResponse
from ..services.auth_service import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new account.
    Password is hashed in a thread-pool executor to avoid blocking the event loop
    during the ~250ms bcrypt operation.
    """
    # Duplicate check
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Offload bcrypt to executor — keeps event loop free for other requests
    loop = asyncio.get_event_loop()
    hashed = await loop.run_in_executor(None, hash_password, user_in.password)

    db_user = User(
        email=user_in.email,
        hashed_password=hashed,
        full_name=user_in.full_name,
        market=user_in.market,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info("User registered: %s", user_in.email)
    return db_user


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate and return a Bearer JWT.
    Password verification is offloaded to executor for non-blocking bcrypt.
    """
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()

    if not user:
        # Timing-safe: still run bcrypt to prevent user enumeration
        await asyncio.get_event_loop().run_in_executor(
            None, hash_password, form.password
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    loop = asyncio.get_event_loop()
    is_valid = await loop.run_in_executor(
        None, verify_password, form.password, user.hashed_password
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token({"sub": user.email})
    logger.info("User authenticated: %s", user.email)
    return {"access_token": token, "token_type": "bearer"}
