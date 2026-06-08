"""
SQLAlchemy models for course data and embeddings.
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.config import get_settings

# pgvector is the production search backend. Import it lazily with a fallback so
# the model module still imports in environments without pgvector installed
# (e.g. the stubbed unit-test env, which never touches this column).
try:
    from pgvector.sqlalchemy import Vector
    _HAS_PGVECTOR = True
except ImportError:  # pragma: no cover - exercised only without pgvector
    _HAS_PGVECTOR = False

    def Vector(_dim):  # type: ignore  # noqa: N802 - shim mirrors pgvector's API
        """Fallback column type when pgvector is unavailable (tests only)."""
        return LargeBinary()

_settings = get_settings()
_EMBEDDING_DIM = _settings.EMBEDDING_DIM

# The pgvector column is only a real ``vector(...)`` type when the pgvector backend
# is active (and the lib is installed). Under the faiss backend it degrades to a
# placeholder LargeBinary so the schema works on a plain Postgres image with no
# vector extension. The search backend is a deploy-time choice.
if _HAS_PGVECTOR and _settings.SEARCH_BACKEND == "pgvector":
    _EMBEDDING_COLUMN_TYPE = Vector(_EMBEDDING_DIM)
else:
    _EMBEDDING_COLUMN_TYPE = LargeBinary()


class Course(Base):
    """Stored university course with its description."""
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("university", "code", name="uq_courses_university_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    university = Column(String(255), nullable=True)
    faculty = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    credits = Column(Integer, nullable=True)
    description = Column(Text, nullable=False)
    source_url = Column(String(500), nullable=True)
    source_fetched_at = Column(DateTime(timezone=True), nullable=True)
    parser_name = Column(String(100), nullable=True)
    parser_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sections = relationship("CourseSection", back_populates="course", cascade="all, delete-orphan")


class CourseSection(Base):
    """Individual section of a course description with its embedding."""
    __tablename__ = "course_sections"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    heading = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(LargeBinary, nullable=True)  # serialized numpy array (legacy / FAISS rebuild)
    embedding_vec = Column(_EMBEDDING_COLUMN_TYPE, nullable=True)  # pgvector search column (vector type only under pgvector backend)

    course = relationship("Course", back_populates="sections")


class ComparisonResult(Base):
    """Stores results of a comparison run."""
    __tablename__ = "comparison_results"

    id = Column(Integer, primary_key=True, index=True)
    # Owner of this comparison. Nullable because anonymous (unauthenticated)
    # comparisons are still allowed; those rows simply never surface in any
    # user's history. SET NULL on delete so removing a user keeps the aggregate
    # dashboard stats intact.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    input_text_preview = Column(String(500), nullable=True)
    overall_similarity = Column(Float, nullable=False)
    report_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    matches = relationship("SectionMatch", back_populates="comparison", cascade="all, delete-orphan")


class SectionMatch(Base):
    """Individual section-level match within a comparison."""
    __tablename__ = "section_matches"

    id = Column(Integer, primary_key=True, index=True)
    comparison_id = Column(Integer, ForeignKey("comparison_results.id", ondelete="CASCADE"), nullable=False)
    input_section_heading = Column(String(255), nullable=False)
    matched_course_code = Column(String(20), nullable=False)
    matched_course_name = Column(String(255), nullable=False)
    matched_section_heading = Column(String(255), nullable=False)
    similarity_score = Column(Float, nullable=False)

    comparison = relationship("ComparisonResult", back_populates="matches")


class User(Base):
    """Application user for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="user", server_default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
