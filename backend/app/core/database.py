"""
Async database engine and session management.
"""
import re
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_course_source_columns(conn)
        await _migrate_course_composite_uniqueness(conn)
        await _backfill_course_source_columns(conn)
        await _migrate_user_role(conn)


UNIVERSITY_PREFIX_MAP = {
    "BLM": "Gebze Teknik Üniversitesi",
    "ELK": "Gebze Teknik Üniversitesi",
    "MAK": "Gebze Teknik Üniversitesi",
    "END": "Gebze Teknik Üniversitesi",
    "KIM": "Gebze Teknik Üniversitesi",
    "FIZ": "Gebze Teknik Üniversitesi",
    "BLG": "İstanbul Teknik Üniversitesi",
    "YZV": "İstanbul Teknik Üniversitesi",
    "EHB": "İstanbul Teknik Üniversitesi",
    "KON": "İstanbul Teknik Üniversitesi",
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
