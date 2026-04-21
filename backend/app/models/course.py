"""
SQLAlchemy models for course data and embeddings.
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


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
    embedding = Column(LargeBinary, nullable=True)  # serialized numpy array

    course = relationship("Course", back_populates="sections")


class ComparisonResult(Base):
    """Stores results of a comparison run."""
    __tablename__ = "comparison_results"

    id = Column(Integer, primary_key=True, index=True)
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
