"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Course Schemas ──────────────────────────────────────────

class CourseCreate(BaseModel):
    code: str
    name: str
    department: Optional[str] = None
    credits: Optional[int] = None
    description: str


class CourseSectionOut(BaseModel):
    id: int
    heading: str
    content: str

    class Config:
        from_attributes = True


class CourseOut(BaseModel):
    id: int
    code: str
    name: str
    department: Optional[str] = None
    credits: Optional[int] = None
    description: str
    created_at: datetime
    sections: list[CourseSectionOut] = []

    class Config:
        from_attributes = True


class CourseListOut(BaseModel):
    id: int
    code: str
    name: str
    department: Optional[str] = None
    credits: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Comparison Schemas ──────────────────────────────────────

class CompareTextRequest(BaseModel):
    text: str


class SectionMatchOut(BaseModel):
    input_section: str
    matched_course_code: str
    matched_course_name: str
    matched_section: str
    similarity: float
    is_overlap: bool  # True if similarity >= threshold


class TopCourseMatch(BaseModel):
    course_code: str
    course_name: str
    average_similarity: float
    is_overlap: bool


class ComparisonResponse(BaseModel):
    overall_similarity: float
    overlap_percentage: float
    top_courses: list[TopCourseMatch]
    section_matches: list[SectionMatchOut]
    report_summary: str
