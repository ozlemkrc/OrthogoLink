"""
FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import select, func
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import init_db, async_session
from app.api.routes import courses, compare, import_courses, auth
from app.services.embedding_service import embedding_service
from app.services.course_service import (
    ensure_pgvector_ready,
    index_vector_count,
)
from app.models.course import Course, CourseSection, User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


async def seed_database():
    """Seed the database with sample courses if empty."""
    from app.models.course import Course
    from app.models.schemas import CourseCreate
    from app.services.course_service import create_course
    from sqlalchemy import select

    async with async_session() as db:
        result = await db.execute(select(Course).limit(1))
        if result.scalar_one_or_none() is not None:
            logger.info("Database already seeded, skipping")
            return

        logger.info("Seeding database with sample courses...")
        from app.seed.seed_data import SEED_COURSES
        for course_data in SEED_COURSES:
            data = CourseCreate(**course_data)
            await create_course(db, data)
        await db.commit()
        logger.info("Database seeding complete")


async def seed_admin():
    """Provision the admin user from ADMIN_USERNAME / ADMIN_PASSWORD if configured.

    Idempotent: if the user already exists it is left untouched (we never silently
    reset a password), only promoting it to admin if somehow it is not. This is the
    supported way to create an admin — registration does not grant admin in
    production, so without this a fresh deployment has no privileged account.
    """
    username = settings.ADMIN_USERNAME.strip()
    password = settings.ADMIN_PASSWORD
    if not username or not password:
        return

    from app.core.security import hash_password

    async with async_session() as db:
        existing = await db.execute(select(User).where(User.username == username))
        user = existing.scalar_one_or_none()
        if user:
            if user.role != "admin":
                user.role = "admin"
                await db.commit()
                logger.info("Promoted existing user '%s' to admin", username)
            return
        db.add(User(
            username=username,
            password_hash=hash_password(password),
            full_name=username,
            role="admin",
        ))
        await db.commit()
        logger.info("Seeded admin user '%s' from environment", username)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("Starting application...")

    # Fail loud on insecure production config rather than silently running with a
    # forgeable default JWT secret. DEBUG=true bypasses this for local dev.
    if not settings.DEBUG:
        issues = settings.production_issues()
        if issues:
            for issue in issues:
                logger.error("INSECURE CONFIG: %s", issue)
            raise RuntimeError(
                "Refusing to start with insecure production config: " + " ".join(issues)
            )
        for warning in settings.production_warnings():
            logger.warning("CONFIG: %s", warning)

    embedding_service.load_model()

    # Initialize database tables (also creates the pgvector extension/column and
    # backfills section vectors from any legacy binary embeddings).
    await init_db()

    # pgvector: search reads the shared DB, so there is no in-process index to
    # load or rebuild. Seed first, then reconcile the model marker (re-embeds
    # only if the configured embedding model changed).
    await seed_database()
    async with async_session() as db:
        await ensure_pgvector_ready(db)

    await seed_admin()

    logger.info("Application ready (search backend: %s)", settings.SEARCH_BACKEND)
    yield

    # Shutdown
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-IP rate limiting. SlowAPIMiddleware applies RATE_LIMIT to every route via
# app.state.limiter, so no endpoint signatures change.
if settings.RATE_LIMIT_ENABLED:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    def _client_key(request):
        # Behind nginx/CapRover, request.client.host is the proxy IP — identical
        # for every visitor. Prefer the original client from X-Forwarded-For so
        # the limit is genuinely per-client. The proxy appends its own hop to the
        # right, so the leftmost entry is the original caller.
        if settings.RATE_LIMIT_TRUSTED_PROXY:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client = forwarded.split(",")[0].strip()
                if client:
                    return client
        return get_remote_address(request)

    limiter = Limiter(key_func=_client_key, default_limits=[settings.RATE_LIMIT])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

# Register routers
app.include_router(courses.router, prefix="/api")
app.include_router(compare.router, prefix="/api")
app.include_router(import_courses.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    # Fetch lightweight DB stats for quick visibility in UI
    course_count = 0
    section_count = 0
    index_size = 0
    async with async_session() as db:
        course_count = await db.scalar(select(func.count()).select_from(Course))
        section_count = await db.scalar(select(func.count()).select_from(CourseSection))
        index_size = await index_vector_count(db)

    return {
        "status": "healthy",
        "model": settings.MODEL_NAME,
        "search_backend": settings.SEARCH_BACKEND,
        "similarity_threshold": settings.SIMILARITY_THRESHOLD,
        "index_vectors": index_size,
        "course_count": course_count,
        "section_count": section_count,
    }
