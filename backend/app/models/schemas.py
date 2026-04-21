"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# -- Course Schemas --

class CourseCreate(BaseModel):
    code: str
    name: str
    university: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[int] = None
    description: str
    source_url: Optional[str] = None
    source_fetched_at: Optional[datetime] = None
    parser_name: Optional[str] = None
    parser_version: Optional[str] = None


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    university: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[int] = None
    description: Optional[str] = None


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
    university: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[int] = None
    description: str
    source_url: Optional[str] = None
    source_fetched_at: Optional[datetime] = None
    parser_name: Optional[str] = None
    parser_version: Optional[str] = None
    created_at: datetime
    sections: list[CourseSectionOut] = []

    class Config:
        from_attributes = True


class CourseListOut(BaseModel):
    id: int
    code: str
    name: str
    university: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# -- Comparison Schemas --

class CompareTextRequest(BaseModel):
    text: str
    threshold_profile: Optional[str] = None  # "strict" | "balanced" | "lenient"


class SectionMatchDetail(BaseModel):
    input_snippet: str
    matched_snippet: str
    shared_keywords: list[str] = []
    threshold: float


class SectionMatchOut(BaseModel):
    input_section: str
    matched_course_code: str
    matched_course_name: str
    matched_university: Optional[str] = None
    matched_faculty: Optional[str] = None
    matched_section: str
    similarity: float
    is_overlap: bool
    similarity_reason: str
    details: Optional[SectionMatchDetail] = None


class TopCourseContribution(BaseModel):
    input_section: str
    matched_section: str
    similarity: float


class TopCourseDetail(BaseModel):
    match_count: int
    best_similarity: float
    threshold: float
    shared_keywords: list[str] = []
    contributing_matches: list[TopCourseContribution] = []


class TopCourseMatch(BaseModel):
    course_code: str
    course_name: str
    matched_university: Optional[str] = None
    matched_faculty: Optional[str] = None
    average_similarity: float
    is_overlap: bool
    explanation: str
    details: Optional[TopCourseDetail] = None


class ComparisonResponse(BaseModel):
    overall_similarity: float
    overlap_percentage: float
    overlap_class: str = "low"  # "high" | "moderate" | "low"
    confidence: str = "medium"  # "high" | "medium" | "low"
    threshold: float = 0.70
    threshold_profile: str = "balanced"
    top_courses: list[TopCourseMatch]
    section_matches: list[SectionMatchOut]
    report_summary: str
