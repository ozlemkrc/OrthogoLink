"""
Comparison API routes (User-side).
Handles text input, PDF upload, and cross-university comparison.
"""
import csv
import io
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.course import Course, ComparisonResult, SectionMatch, User
from app.models.schemas import CompareTextRequest, ComparisonResponse
from app.services.comparison_service import compare_syllabus
from app.services.pdf_service import extract_text_from_pdf
from app.services.llm_explanation_service import generate_ai_summary

router = APIRouter(prefix="/compare", tags=["Comparison"])
_settings = get_settings()
logger = logging.getLogger(__name__)


async def _add_ai_summary(
    result: ComparisonResponse,
    language: str,
    is_cross_university: bool = False,
) -> None:
    """Generate one AI summary for all results and attach it to the response."""
    try:
        text, source = await generate_ai_summary(
            top_courses=result.top_courses,
            overlap_class=result.overlap_class,
            language=language,
            is_cross_university=is_cross_university,
        )
        result.ai_summary = text
        result.ai_summary_source = source
    except Exception:
        pass  # never let AI enrichment break the response


class CrossUniCompareRequest(BaseModel):
    text: str
    university_filter: Optional[List[str]] = None
    department_filter: Optional[List[str]] = None
    threshold_profile: Optional[str] = None  # strict | balanced | lenient
    include_ai_explanations: bool = False
    explanation_language: Optional[str] = None  # "tr" | "en"


@router.post("/text", response_model=ComparisonResponse)
async def compare_text(request: CompareTextRequest, db: AsyncSession = Depends(get_db)):
    """Compare pasted syllabus text against stored courses."""
    if len(request.text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Input text is too short. Please provide a meaningful syllabus text.",
        )
    try:
        result = compare_syllabus(request.text, threshold_profile=request.threshold_profile)
        if request.include_ai_explanations:
            lang = request.explanation_language or _settings.AI_DEFAULT_LANGUAGE
            await _add_ai_summary(result, lang)
        await _save_comparison(db, request.text, result)
        return result
    except Exception as e:
        logger.error("Text comparison failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Comparison failed. Please try again.")


@router.post("/pdf", response_model=ComparisonResponse)
async def compare_pdf(
    file: UploadFile = File(...),
    threshold_profile: Optional[str] = None,
    include_ai_explanations: bool = False,
    explanation_language: Optional[str] = None,
    university_filter: Optional[List[str]] = Query(None),
    department_filter: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF syllabus and compare against stored courses."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        contents = await file.read()
        text = extract_text_from_pdf(contents)

        if len(text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Could not extract enough text from the PDF.",
            )

        result = compare_syllabus(
            text,
            threshold_profile=threshold_profile,
            university_filter=university_filter or None,
            department_filter=department_filter or None,
        )
        if include_ai_explanations:
            lang = explanation_language or _settings.AI_DEFAULT_LANGUAGE
            is_cross = bool(university_filter or department_filter)
            await _add_ai_summary(result, lang, is_cross_university=is_cross)
        await _save_comparison(db, text, result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF comparison failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="PDF processing failed. Please try again.")


@router.post("/cross-university", response_model=ComparisonResponse)
async def compare_cross_university(request: CrossUniCompareRequest, db: AsyncSession = Depends(get_db)):
    """
    Compare syllabus against courses from specific universities.
    Filter by university code prefixes (e.g., BLM for GTU, CENG for METU/IYTE).
    """
    if len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Input text is too short.")

    try:
        result = compare_syllabus(
            request.text,
            university_filter=request.university_filter,
            department_filter=request.department_filter,
            threshold_profile=request.threshold_profile,
        )
        if request.include_ai_explanations:
            lang = request.explanation_language or _settings.AI_DEFAULT_LANGUAGE
            await _add_ai_summary(result, lang, is_cross_university=True)
        await _save_comparison(db, request.text, result)
        return result
    except Exception as e:
        logger.error("Cross-university comparison failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Comparison failed. Please try again.")


@router.get("/history")
async def get_comparison_history(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    _user: User = Depends(get_current_user),
):
    """Get recent comparison history. Requires authentication."""
    result = await db.execute(
        select(ComparisonResult)
        .order_by(ComparisonResult.created_at.desc())
        .limit(limit)
    )
    comparisons = result.scalars().all()
    return [
        {
            "id": c.id,
            "input_preview": c.input_text_preview,
            "overall_similarity": c.overall_similarity,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comparisons
    ]


@router.get("/history/{comparison_id}")
async def get_comparison_detail(
    comparison_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get detailed comparison result by ID. Requires authentication."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(ComparisonResult)
        .options(selectinload(ComparisonResult.matches))
        .where(ComparisonResult.id == comparison_id)
    )
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Comparison not found")

    return {
        "id": comp.id,
        "input_preview": comp.input_text_preview,
        "overall_similarity": comp.overall_similarity,
        "report_summary": comp.report_summary,
        "created_at": comp.created_at.isoformat() if comp.created_at else None,
        "matches": [
            {
                "input_section": m.input_section_heading,
                "matched_course_code": m.matched_course_code,
                "matched_course_name": m.matched_course_name,
                "matched_section": m.matched_section_heading,
                "similarity": m.similarity_score,
            }
            for m in comp.matches
        ],
    }


@router.post("/export-csv")
async def export_csv(request: CompareTextRequest):
    """Export comparison results as CSV."""
    if len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Input text is too short.")

    result = compare_syllabus(request.text, threshold_profile=request.threshold_profile)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Overall Similarity", f"{result.overall_similarity:.4f}"])
    writer.writerow(["Overlap Percentage", f"{result.overlap_percentage:.2f}%"])
    writer.writerow([])

    # Top courses
    writer.writerow(["Top Matching Courses"])
    writer.writerow(["Rank", "Code", "Name", "University", "Faculty", "Avg Similarity", "Status", "Explanation"])
    for i, course in enumerate(result.top_courses, 1):
        writer.writerow([
            i,
            course.course_code,
            course.course_name,
            course.matched_university or "",
            course.matched_faculty or "",
            f"{course.average_similarity:.4f}",
            "OVERLAP" if course.is_overlap else "UNIQUE",
            course.explanation,
        ])
    writer.writerow([])

    # Section matches
    writer.writerow(["Section-Level Matches"])
    writer.writerow([
        "Input Section",
        "Matched Course Code",
        "Matched Course Name",
        "University",
        "Faculty",
        "Matched Section",
        "Similarity",
        "Status",
        "Why Similar",
    ])
    for match in result.section_matches:
        writer.writerow([
            match.input_section,
            match.matched_course_code,
            match.matched_course_name,
            match.matched_university or "",
            match.matched_faculty or "",
            match.matched_section,
            f"{match.similarity:.4f}",
            "OVERLAP" if match.is_overlap else "OK",
            match.similarity_reason,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orthogonality-report.csv"},
    )


async def _save_comparison(db: AsyncSession, text: str, result: ComparisonResponse):
    """Save comparison result to database for history tracking."""
    try:
        comp = ComparisonResult(
            input_text_preview=text[:500],
            overall_similarity=result.overall_similarity,
            report_summary=result.report_summary,
        )
        db.add(comp)
        await db.flush()

        for match in result.section_matches[:50]:  # cap at 50 matches
            sm = SectionMatch(
                comparison_id=comp.id,
                input_section_heading=match.input_section,
                matched_course_code=match.matched_course_code,
                matched_course_name=match.matched_course_name,
                matched_section_heading=match.matched_section,
                similarity_score=match.similarity,
            )
            db.add(sm)

        await db.flush()
    except Exception as e:
        logger.warning(f"Failed to save comparison history: {e}")
