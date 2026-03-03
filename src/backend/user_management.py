"""
Phase 1 – User Management Module
Handles registration, JWT authentication, and resume ingestion via FastAPI.

Endpoints:
  POST /auth/register   – create a new account
  POST /auth/login      – returns a Bearer JWT
  GET  /users/me        – fetch authenticated user's profile
  POST /users/me/resume – upload JSON or PDF resume; stores parsed profile
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import bcrypt as _bcrypt
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
import sqlalchemy as sa
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ─── Config ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8-hour sessions

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./career_portal.db")

# ─── Database setup ───────────────────────────────────────────────────────────
engine       = sa.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id              = sa.Column(sa.Integer, primary_key=True, index=True)
    email           = sa.Column(sa.String, unique=True, index=True, nullable=False)
    hashed_password = sa.Column(sa.String, nullable=False)
    full_name       = sa.Column(sa.String)
    profile_json    = sa.Column(sa.Text)   # parsed resume stored as JSON blob
    created_at      = sa.Column(sa.DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email:     EmailStr
    password:  str
    full_name: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type:   str


class UserProfile(BaseModel):
    id:               int
    email:            str
    full_name:        Optional[str]
    profile:          Optional[Dict[str, Any]]
    profile_complete: bool


# ─── Auth utilities ───────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire  = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str     = Depends(oauth2_scheme),
    db:    Session = Depends(get_db),
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise credentials_exception
    return user


# ─── FastAPI application ──────────────────────────────────────────────────────
app = FastAPI(title="Career Portal – User Management", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/auth/register", status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
    if db.query(UserModel).filter(UserModel.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = UserModel(
        email           = user.email,
        hashed_password = hash_password(user.password),
        full_name       = user.full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered", "id": db_user.id}


@app.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate and return a Bearer JWT."""
    user = db.query(UserModel).filter(UserModel.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserProfile)
def read_me(current_user: UserModel = Depends(get_current_user)):
    """Return the authenticated user's stored profile."""
    profile = json.loads(current_user.profile_json) if current_user.profile_json else None
    return UserProfile(
        id               = current_user.id,
        email            = current_user.email,
        full_name        = current_user.full_name,
        profile          = profile,
        profile_complete = current_user.profile_json is not None,
    )


@app.post("/users/me/resume")
def upload_resume(
    file:         UploadFile = File(...),
    current_user: UserModel  = Depends(get_current_user),
    db:           Session    = Depends(get_db),
):
    """
    Phase 8A — Semantic resume upload with global state sync.
    1. Parse resume (semantic role inference → implied skills)
    2. Run ResumeInferenceAgent synchronously → MRV, MPI, skill_trajectory
    3. Merge enrichment into profile and persist
    4. Return enriched profile so dashboard updates all stat cards immediately
    """
    import asyncio
    from src.backend.engine.resume_parser import parse_resume_bytes

    content    = file.file.read()
    structured = parse_resume_bytes(content, file.content_type or "")

    # Phase 8A: Run ResumeInferenceAgent to enrich with MRV / MPI / trajectory
    try:
        from src.backend.agents.resume_inference_agent import ResumeInferenceAgent
        agent  = ResumeInferenceAgent()
        loop   = asyncio.new_event_loop()
        result = loop.run_until_complete(agent.run({"profile": structured, "market": "US"}))
        loop.close()
        if result.success:
            structured.update({
                "mrv":                   result.data.get("mrv"),
                "mrv_score":             result.data.get("mrv_score"),
                "market_pressure_index": result.data.get("market_pressure_index"),
                "skill_trajectory":      result.data.get("skill_trajectory"),
                "inferred_skills":       result.data.get("inferred_skills", structured.get("inferred_skills", [])),
                "readiness_breakdown":   result.data.get("readiness_breakdown"),
            })
    except Exception:
        pass  # Enrichment is best-effort; base parse always succeeds

    current_user.profile_json = json.dumps(structured)
    db.commit()
    return {
        "message":   "Resume parsed and enriched",
        "profile":   structured,
        "mrv_score": structured.get("mrv_score"),
        "mpi":       structured.get("market_pressure_index"),
    }


# ─── Dev entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.backend.user_management:app", host="0.0.0.0", port=8000, reload=True)
