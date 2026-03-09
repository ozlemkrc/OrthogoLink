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
from app.api.routes import courses, compare, import_courses
from app.services.embedding_service import embedding_service
from app.services.course_service import rebuild_faiss_index
from app.models.course import Course, CourseSection

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("Starting application...")
    embedding_service.load_model()

    # Initialize database tables
    await init_db()

    # Try to load existing FAISS index
    if not embedding_service.load_index():
        # If no saved index, rebuild from DB
        async with async_session() as db:
            await rebuild_faiss_index(db)

    # Seed sample data if empty
    await seed_database()

    logger.info("Application ready")
    yield

    # Shutdown
    embedding_service.save_index()
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

# Register routers
app.include_router(courses.router, prefix="/api")
app.include_router(compare.router, prefix="/api")
app.include_router(import_courses.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    index_size = embedding_service.index.ntotal if embedding_service.index else 0

    # Fetch lightweight DB stats for quick visibility in UI
    course_count = 0
    section_count = 0
    async with async_session() as db:
        course_count = await db.scalar(select(func.count()).select_from(Course))
        section_count = await db.scalar(select(func.count()).select_from(CourseSection))

    return {
        "status": "healthy",
        "model": settings.MODEL_NAME,
        "similarity_threshold": settings.SIMILARITY_THRESHOLD,
        "index_vectors": index_size,
        "course_count": course_count,
        "section_count": section_count,
    }
