FROM python:3.11-slim

WORKDIR /app

# System dependencies
# fonts-dejavu-core: Unicode TTF so Turkish course names render in PDF reports
# (no build-essential: every dependency in requirements.txt ships a prebuilt
# cp311 manylinux wheel, so nothing is compiled from source)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch, installed BEFORE requirements.txt: sentence-transformers
# depends on torch, and the default PyPI Linux build bundles the full CUDA
# stack (~3 GB of nvidia-* downloads) that a CPU-only server never executes.
# Pre-installing the cpu wheel (~190 MB) satisfies the dependency so pip
# never fetches the CUDA build.
RUN pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=5 -r requirements.txt

# Pre-download the sentence-transformers model at build time.
# MUST match the default MODEL_NAME in app/core/config.py — the multilingual
# model is required for Turkish↔English cross-lingual comparison (the English-only
# all-MiniLM-L6-v2 fails on Turkish syllabi; see eval/benchmark.py). Override at
# build with --build-arg MODEL_NAME=... and set the same value via env at runtime.
ARG MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
# HF_HUB_DISABLE_XET: use the plain CDN download path — the xet transfer
# backend can stall indefinitely on some networks. The download timeout makes
# a stalled connection error out (and fail the build) instead of hanging.
RUN HF_HUB_DISABLE_XET=1 HF_HUB_DOWNLOAD_TIMEOUT=60 \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${MODEL_NAME}')"

# Application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
