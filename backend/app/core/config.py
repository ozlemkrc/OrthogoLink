"""
Application configuration loaded from environment variables.
"""
from typing import ClassVar
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Curriculum Orthogonality Checker"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/orthogonality"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@db:5432/orthogonality"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:80,http://localhost"

    # AI Model — multilingual model for cross-language (TR/EN) semantic comparison
    MODEL_NAME: str = "paraphrase-multilingual-MiniLM-L12-v2"
    SIMILARITY_THRESHOLD: float = 0.70

    # Cross-encoder re-ranking — a second, more accurate (but slower) model that
    # re-scores the bi-encoder's top candidates. The bi-encoder retrieves fast;
    # the cross-encoder reads each (query, candidate) pair jointly for sharper
    # precision. Disabled by default so behavior is unchanged until the benchmark
    # (eval/benchmark.py --compare) validates the gain and tunes the weight.
    RERANK_ENABLED: bool = False
    RERANK_MODEL: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"  # multilingual
    RERANK_CANDIDATES: int = 30   # bi-encoder candidates re-scored per input section
    RERANK_WEIGHT: float = 0.5    # blend: final = (1-w)*cosine + w*cross_encoder

    # Input limits — guard against oversized payloads that would blow up memory
    # or stall the embedding step. Tunable via env for larger syllabi.
    MIN_INPUT_CHARS: int = 50            # below this, input is not meaningful
    MAX_INPUT_CHARS: int = 50_000        # ~15-20 pages of syllabus text
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB PDF upload cap

    # Vector search backend:
    #   "pgvector" — embeddings searched in PostgreSQL via the pgvector extension.
    #                Shared across processes, so the API can run with MULTIPLE
    #                uvicorn workers and survives restarts. (default, production)
    #   "faiss"    — legacy in-process FAISS index. Requires a SINGLE worker.
    #                Also the backend the standalone eval/benchmark.py uses.
    SEARCH_BACKEND: str = "pgvector"
    EMBEDDING_DIM: int = 384  # dimension of MODEL_NAME's output; pgvector column size

    # FAISS index path (only used when SEARCH_BACKEND="faiss")
    FAISS_INDEX_PATH: str = "/app/data/faiss_index"

    # Auth — must be set via .env in any real deployment
    SECRET_KEY: str = "orthogolink-dev-key-do-not-use-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Admin bootstrap. When both are set, an admin user is provisioned at startup.
    # This is the ONLY way to get an admin in production: the public /auth/register
    # endpoint never grants admin (outside a local DEBUG run), so there is no
    # "first request wins admin" race on a fresh deployment.
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""

    # API rate limiting (per client IP). Protects the public endpoints — the
    # /compare routes run embeddings on user input and are the most abusable.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT: str = "60/minute"
    # Behind a reverse proxy (nginx/CapRover) the direct socket peer is always the
    # proxy, which would collapse every client into a single rate-limit bucket.
    # When true, derive the client IP from the leftmost X-Forwarded-For entry.
    # Only safe when the app is actually behind a trusted proxy that sets XFF.
    RATE_LIMIT_TRUSTED_PROXY: bool = True

    # AI Explanations
    AI_EXPLANATIONS_ENABLED: bool = False
    AI_PROVIDER: str = "gemini"
    AI_MODEL: str = "gemini-2.5-flash"
    AI_API_KEY: str = ""
    AI_TIMEOUT_SECONDS: int = 20
    AI_MAX_COURSES_PER_REQUEST: int = 3
    AI_DEFAULT_LANGUAGE: str = "en"

    class Config:
        env_file = ".env"

    # ── Production safety ────────────────────────────────────
    _DEFAULT_SECRET: ClassVar[str] = "orthogolink-dev-key-do-not-use-in-production"

    def production_issues(self) -> list[str]:
        """Return blocking misconfigurations for a non-DEBUG (production) deploy.

        Used to *fail loud* at startup instead of silently running insecure. Only
        the most dangerous default — shipping the built-in JWT secret, which would
        let anyone forge tokens — is treated as blocking.
        """
        issues: list[str] = []
        if self.SECRET_KEY == self._DEFAULT_SECRET:
            issues.append(
                "SECRET_KEY is still the built-in development default — set a unique "
                "random value (e.g. python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
            )
        return issues

    def production_warnings(self) -> list[str]:
        """Non-blocking hardening advice surfaced at startup."""
        warnings: list[str] = []
        if "postgres:postgres@" in self.DATABASE_URL:
            warnings.append("DATABASE_URL uses the default postgres:postgres credentials.")
        return warnings


@lru_cache()
def get_settings() -> Settings:
    return Settings()
