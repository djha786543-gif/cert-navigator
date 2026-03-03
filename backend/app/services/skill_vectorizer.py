"""
Skill Vectorizer — converts resume skills into 384-dimensional embeddings
using sentence-transformers all-MiniLM-L6-v2.

Architecture decisions:
- Model loaded ONCE at startup via warm_up(), shared across all requests.
- Inference runs in asyncio executor to keep event loop non-blocking.
- pgvector stores the result for cosine similarity search.

⚠️ CAPACITY FLAGS:
  1. Model load: ~600 MB RAM, ~2-3s cold start.
     With --workers 4: multiply by 4 → needs 2.4 GB+ free RAM.
     On machines with < 8 GB RAM: use --workers 1 (async handles concurrency).

  2. Throughput: all-MiniLM-L6-v2 on CPU: ~100 sentences/sec.
     For 50 concurrent resume uploads: ~0.5s per vectorization call.
     At > 20 concurrent uploads: offload to Celery worker on dedicated CPU.

  3. AWS migration trigger: If you need GPU-accelerated embeddings for
     real-time matching at > 500 req/min → AWS Lambda + sentence-transformers
     or OpenAI text-embedding-3-small API ($0.02 / 1M tokens).
"""
import asyncio
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_model = None
_lock = asyncio.Lock()


def _load_model_sync():
    """Synchronous model load — called in executor thread."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("sentence-transformers model loaded (all-MiniLM-L6-v2, 384 dims)")
        return model
    except ImportError:
        logger.warning(
            "sentence-transformers not installed. "
            "Skill vectors will be zero-filled. "
            "Run: pip install sentence-transformers"
        )
        return None


async def get_model():
    """Lazy-load once with async double-checked locking."""
    global _model
    if _model is not None:
        return _model
    async with _lock:
        if _model is None:
            loop = asyncio.get_event_loop()
            _model = await loop.run_in_executor(None, _load_model_sync)
    return _model


async def warm_up() -> None:
    """
    Pre-load the model at application startup.
    Prevents cold-start latency on the first user's resume upload.
    Call this from the FastAPI lifespan event.
    """
    logger.info("Warming up embedding model...")
    model = await get_model()
    if model:
        # Run a dummy encode to JIT-compile any lazy components
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: model.encode("warmup"))
        logger.info("Embedding model warm-up complete.")


async def vectorize_skills(skills: List[str]) -> List[float]:
    """
    Encode a list of skill strings into a single 384-dim embedding.

    Strategy: Concatenate skills with ' | ' separator, then encode as one
    sentence. This captures skill co-occurrence patterns better than averaging
    individual vectors. Example:
        ['Python', 'SOX Auditing', 'AI Governance'] →
        "Python | SOX Auditing | AI Governance" → Vector(384)

    Returns a zero vector if model is unavailable.
    """
    model = await get_model()
    if model is None:
        logger.warning("Model unavailable — returning zero vector")
        return [0.0] * 384

    if not skills:
        return [0.0] * 384

    text = " | ".join(str(s) for s in skills if s)
    loop = asyncio.get_event_loop()
    vector = await loop.run_in_executor(
        None, lambda: model.encode(text, normalize_embeddings=True).tolist()
    )
    return vector


async def vectorize_text(text: str) -> List[float]:
    """
    Encode arbitrary text (job description, cert summary) into a 384-dim vector.
    Used for job-to-candidate similarity matching.
    """
    model = await get_model()
    if model is None:
        return [0.0] * 384

    loop = asyncio.get_event_loop()
    vector = await loop.run_in_executor(
        None, lambda: model.encode(text, normalize_embeddings=True).tolist()
    )
    return vector


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Pure-Python cosine similarity — used for in-memory comparisons.
    pgvector handles DB-side similarity at scale via the <=> operator.
    """
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = sum(a * a for a in vec_a) ** 0.5
    mag_b = sum(b * b for b in vec_b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
