"""
Comparison service: orchestrates the syllabus comparison pipeline.
Takes input text → splits → embeds → searches FAISS → aggregates results.
"""
import logging
from collections import defaultdict
from app.services.embedding_service import embedding_service
from app.services.pdf_service import split_into_sections
from app.core.config import get_settings
from app.models.schemas import (
    SectionMatchOut,
    TopCourseMatch,
    ComparisonResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()

THRESHOLD = settings.SIMILARITY_THRESHOLD


def compare_syllabus(text: str) -> ComparisonResponse:
    """
    Full comparison pipeline:
    1. Split input text into sections
    2. Embed each section
    3. Search FAISS index for each section
    4. Aggregate results into section-level and course-level scores
    5. Generate summary report
    """

    # Step 1: Split input into sections
    input_sections = split_into_sections(text)
    logger.info(f"Input split into {len(input_sections)} sections")

    all_section_matches: list[SectionMatchOut] = []
    course_scores: dict[str, list[float]] = defaultdict(list)
    course_names: dict[str, str] = {}

    # Step 2 & 3: Embed and search each section
    for section in input_sections:
        combined_text = f"{section['heading']}: {section['content']}"
        query_embedding = embedding_service.encode_single(combined_text)

        results = embedding_service.search(query_embedding, top_k=5)

        for result in results:
            score = result["score"]
            match = SectionMatchOut(
                input_section=section["heading"],
                matched_course_code=result["course_code"],
                matched_course_name=result["course_name"],
                matched_section=result["section_heading"],
                similarity=round(score, 4),
                is_overlap=score >= THRESHOLD,
            )
            all_section_matches.append(match)

            # Track per-course best scores
            key = result["course_code"]
            course_scores[key].append(score)
            course_names[key] = result["course_name"]

    # Step 4: Aggregate course-level similarity
    top_courses = []
    for code, scores in course_scores.items():
        avg = sum(scores) / len(scores)
        top_courses.append(TopCourseMatch(
            course_code=code,
            course_name=course_names[code],
            average_similarity=round(avg, 4),
            is_overlap=avg >= THRESHOLD,
        ))

    # Sort by average similarity descending, take top 3
    top_courses.sort(key=lambda c: c.average_similarity, reverse=True)
    top_courses = top_courses[:3]

    # Step 5: Calculate overall similarity and overlap percentage
    if all_section_matches:
        all_scores = [m.similarity for m in all_section_matches]
        overall_sim = sum(all_scores) / len(all_scores)
        overlap_count = sum(1 for m in all_section_matches if m.is_overlap)
        overlap_pct = (overlap_count / len(all_section_matches)) * 100
    else:
        overall_sim = 0.0
        overlap_pct = 0.0

    # Sort section matches by similarity descending
    all_section_matches.sort(key=lambda m: m.similarity, reverse=True)

    # Step 6: Generate text report
    report = _generate_report(overall_sim, overlap_pct, top_courses, len(input_sections))

    return ComparisonResponse(
        overall_similarity=round(overall_sim, 4),
        overlap_percentage=round(overlap_pct, 2),
        top_courses=top_courses,
        section_matches=all_section_matches,
        report_summary=report,
    )


def _generate_report(
    overall_sim: float,
    overlap_pct: float,
    top_courses: list[TopCourseMatch],
    num_sections: int,
) -> str:
    """Generate a human-readable comparison report."""
    lines = [
        "=" * 50,
        "CURRICULUM ORTHOGONALITY REPORT",
        "=" * 50,
        "",
        f"Input syllabus was analyzed across {num_sections} section(s).",
        f"Overall average similarity: {overall_sim:.2%}",
        f"Overlap percentage (sections above {THRESHOLD:.0%} threshold): {overlap_pct:.1f}%",
        "",
    ]

    if overlap_pct > 50:
        lines.append("⚠ HIGH OVERLAP — This syllabus significantly overlaps with existing courses.")
    elif overlap_pct > 25:
        lines.append("⚡ MODERATE OVERLAP — Some sections share content with existing courses.")
    else:
        lines.append("✅ LOW OVERLAP — This syllabus is largely orthogonal to existing courses.")

    lines.append("")
    lines.append("Top matching courses:")
    for i, course in enumerate(top_courses, 1):
        flag = " [OVERLAP]" if course.is_overlap else ""
        lines.append(
            f"  {i}. {course.course_code} — {course.course_name}: "
            f"{course.average_similarity:.2%}{flag}"
        )

    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)
