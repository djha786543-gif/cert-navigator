FROM python:3.12-slim

WORKDIR /app

# Install only v1 production deps (no sentence-transformers / celery / pgvector)
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Copy only what the v1 backend needs
COPY src/ ./src/
COPY data/ ./data/
COPY .env.example ./.env

EXPOSE 8001

CMD ["sh", "-c", "uvicorn src.backend.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
