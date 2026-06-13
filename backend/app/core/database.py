"""
Async database engine and session management.
"""
import logging
import re
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Synchronous engine used by the pgvector search path (vector_search.py). The
# comparison pipeline is synchronous (CPU-bound embedding already blocks), so the
# similarity query runs over this engine. Lazily connects — no connection is
# opened until the first search, so importing this module never needs the DB.
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency that provides an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    pgvector = settings.SEARCH_BACKEND == "pgvector"
    async with engine.begin() as conn:
        # The extension must exist before create_all, so a fresh DB can create the
        # course_sections.embedding_vec column with the vector(...) type.
        if pgvector:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_course_source_columns(conn)
        await _migrate_course_composite_uniqueness(conn)
        await _backfill_course_source_columns(conn)
        await _migrate_user_role(conn)
        await _migrate_comparison_user_id(conn)
        if pgvector:
            await _migrate_pgvector(conn)
            await _backfill_embedding_vectors(conn)


async def _migrate_pgvector(conn):
    """Ensure the pgvector column, ANN index, and model-marker table exist."""
    dim = settings.EMBEDDING_DIM
    await conn.execute(
        text(f"ALTER TABLE course_sections ADD COLUMN IF NOT EXISTS embedding_vec vector({dim})")
    )
    # Singleton table marking which embedding model the stored vectors were built
    # with, so a model change triggers a re-embed of all sections on startup.
    await conn.execute(text(
        "CREATE TABLE IF NOT EXISTS embedding_meta ("
        " id INTEGER PRIMARY KEY DEFAULT 1,"
        " model_name TEXT,"
        " CONSTRAINT embedding_meta_singleton CHECK (id = 1))"
    ))
    # HNSW index for fast approximate cosine search; harmless on an empty table.
    await conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_course_sections_embedding_vec "
        "ON course_sections USING hnsw (embedding_vec vector_cosine_ops)"
    ))


async def _backfill_embedding_vectors(conn):
    """Populate embedding_vec from the legacy binary ``embedding`` column for any
    rows migrated from a pre-pgvector database. New writes set both columns."""
    import numpy as np

    rows = await conn.execute(text(
        "SELECT id, embedding FROM course_sections "
        "WHERE embedding_vec IS NULL AND embedding IS NOT NULL"
    ))
    pending = rows.fetchall()
    if not pending:
        return

    migrated = 0
    for row in pending:
        try:
            arr = np.frombuffer(row.embedding, dtype=np.float32)
        except Exception:
            continue
        if arr.size != settings.EMBEDDING_DIM:
            continue
        # Numeric-only literal (no bound vector param) → driver-agnostic, safe.
        literal = "[" + ",".join(f"{x:.8f}" for x in arr.tolist()) + "]"
        await conn.execute(
            text(f"UPDATE course_sections SET embedding_vec = '{literal}'::vector WHERE id = :id"),
            {"id": row.id},
        )
        migrated += 1
    logger.info("pgvector backfill: populated %d section vector(s) from legacy binary", migrated)


UNIVERSITY_PREFIX_MAP = {
    "BLM": "Gebze Teknik Üniversitesi",
    "ELK": "Gebze Teknik Üniversitesi",
    "MAK": "Gebze Teknik Üniversitesi",
    "END": "Gebze Teknik Üniversitesi",
    "KIM": "Gebze Teknik Üniversitesi",
    "FIZ": "Gebze Teknik Üniversitesi",
    "BBM": "Hacettepe Üniversitesi",
    "EEM": "Hacettepe Üniversitesi",
    "IST": "Hacettepe Üniversitesi",
    "IE": "Orta Doğu Teknik Üniversitesi",
    "STAT": "Orta Doğu Teknik Üniversitesi",
    "ME": "İzmir Yüksek Teknoloji Enstitüsü",
    "CS": "Local Seed Catalog",
}

AMBIGUOUS_PREFIX_MAP = {
    "CENG": "Ambiguous (Orta Doğu Teknik Üniversitesi / İzmir Yüksek Teknoloji Enstitüsü)",
    "EEE": "Ambiguous (Orta Doğu Teknik Üniversitesi / İzmir Yüksek Teknoloji Enstitüsü)",
    "MATH": "Ambiguous (Orta Doğu Teknik Üniversitesi / İzmir Yüksek Teknoloji Enstitüsü)",
    "MAT": "Ambiguous (Gebze Teknik Üniversitesi / Hacettepe Üniversitesi)",
}


async def _migrate_user_role(conn):
    await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user'"))


async def _migrate_comparison_user_id(conn):
    """Add the per-user owner column so history can be scoped to its creator."""
    await conn.execute(text(
        "ALTER TABLE comparison_results ADD COLUMN IF NOT EXISTS "
        "user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"
    ))


async def _migrate_course_source_columns(conn):
    await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS university VARCHAR(255)"))
    await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS faculty VARCHAR(255)"))
    await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS source_url VARCHAR(500)"))
    await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS source_fetched_at TIMESTAMPTZ"))
    await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS parser_name VARCHAR(100)"))
    await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS parser_version VARCHAR(50)"))


async def _migrate_course_composite_uniqueness(conn):
    """Migrate from code-only uniqueness to (university, code) composite uniqueness."""
    await conn.execute(text("ALTER TABLE courses DROP CONSTRAINT IF EXISTS courses_code_key"))
    await conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'uq_courses_university_code'
                ) THEN
                    ALTER TABLE courses
                    ADD CONSTRAINT uq_courses_university_code UNIQUE (university, code);
                END IF;
            END
            $$;
            """
        )
    )


async def _backfill_course_source_columns(conn):
    rows = await conn.execute(text("SELECT id, code, department FROM courses WHERE university IS NULL OR faculty IS NULL"))
    pending = rows.fetchall()
    if not pending:
        return

    for row in pending:
        code = row.code or ""
        department = row.department or ""
        university = _infer_university(code)
        faculty = _infer_faculty(department)
        await conn.execute(
            text("""
                UPDATE courses
                SET university = COALESCE(university, :university),
                    faculty = COALESCE(faculty, :faculty)
                WHERE id = :course_id
            """),
            {
                "university": university,
                "faculty": faculty,
                "course_id": row.id,
            },
        )


def _infer_university(course_code: str):
    prefix_match = re.match(r"^[A-Za-z]+", course_code)
    prefix = prefix_match.group(0).upper() if prefix_match else ""
    if prefix in UNIVERSITY_PREFIX_MAP:
        return UNIVERSITY_PREFIX_MAP[prefix]
    if prefix in AMBIGUOUS_PREFIX_MAP:
        return AMBIGUOUS_PREFIX_MAP[prefix]
    return "Unknown"


def _infer_faculty(department: str):
    normalized = department.lower()
    if not normalized:
        return "Related Faculty"
    if any(token in normalized for token in ["mat", "fiz", "physics", "istat", "statistics"]):
        return "Faculty of Science"
    if any(token in normalized for token in ["müh", "engineering", "computer", "elektr", "machine"]):
        return "Faculty of Engineering"
    return "Related Faculty"
