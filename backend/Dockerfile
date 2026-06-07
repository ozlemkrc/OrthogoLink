FROM python:3.11-slim

WORKDIR /app

# System dependencies
# fonts-dejavu-core: Unicode TTF so Turkish course names render in PDF reports
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=5 -r requirements.txt

# Pre-download the sentence-transformers model at build time.
# MUST match the default MODEL_NAME in app/core/config.py — the multilingual
# model is required for Turkish↔English cross-lingual comparison (the English-only
# all-MiniLM-L6-v2 fails on Turkish syllabi; see eval/benchmark.py). Override at
# build with --build-arg MODEL_NAME=... and set the same value via env at runtime.
ARG MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${MODEL_NAME}')"

# Application code
COPY . .

# Create data directory for FAISS index persistence
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
