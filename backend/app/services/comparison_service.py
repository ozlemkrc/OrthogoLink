"""
Comparison service v2: section-aware, deduped, threshold-profile aware.
Takes input text -> splits -> embeds -> FAISS search -> dedup -> aggregate -> report.
"""
import logging
import re
from collections import defaultdict
from typing import List, Optional
from app.services.embedding_service import embedding_service
from app.services.pdf_service import split_into_sections
from app.core.config import get_settings
from app.models.schemas import (
    SectionMatchOut,
    SectionMatchDetail,
    TopCourseMatch,
    TopCourseDetail,
    TopCourseContribution,
    ComparisonResponse,
)

SNIPPET_LIMIT = 600
TOP_CONTRIBUTING_MATCHES = 3
MAX_MATCHES_PER_INPUT_SECTION = 5  # after per-course dedup

logger = logging.getLogger(__name__)
settings = get_settings()

# Threshold profiles: trade-off between recall (lenient) and precision (strict).
THRESHOLD_PROFILES = {
    "strict":   {"threshold": 0.78, "weak_floor": 0.55},
    "balanced": {"threshold": settings.SIMILARITY_THRESHOLD, "weak_floor": 0.45},
    "lenient":  {"threshold": 0.60, "weak_floor": 0.35},
}
DEFAULT_PROFILE = "balanced"

UNIVERSITY_PREFIX_MAP = {
    "BLM": ("Gebze Teknik Üniversitesi", "Mühendislik Fakültesi"),
    "ELK": ("Gebze Teknik Üniversitesi", "Mühendislik Fakültesi"),
    "MAK": ("Gebze Teknik Üniversitesi", "Mühendislik Fakültesi"),
    "END": ("Gebze Teknik Üniversitesi", "Mühendislik Fakültesi"),
    "KIM": ("Gebze Teknik Üniversitesi", "Mühendislik Fakültesi"),
    "FIZ": ("Gebze Teknik Üniversitesi", "Temel Bilimler Fakültesi"),
    "BLG": ("İstanbul Teknik Üniversitesi", "Bilgisayar ve Bilişim Fakültesi"),
    "YZV": ("İstanbul Teknik Üniversitesi", "Bilgisayar ve Bilişim Fakültesi"),
    "EHB": ("İstanbul Teknik Üniversitesi", "Elektrik-Elektronik Fakültesi"),
    "KON": ("İstanbul Teknik Üniversitesi", "Elektrik-Elektronik Fakültesi"),
    "BBM": ("Hacettepe Üniversitesi", "Mühendislik Fakültesi"),
    "EEM": ("Hacettepe Üniversitesi", "Mühendislik Fakültesi"),
    "IST": ("Hacettepe Üniversitesi", "Fen Fakültesi"),
}

AMBIGUOUS_PREFIX_MAP = {
    "CENG": ["Orta Doğu Teknik Üniversitesi", "İzmir Yüksek Teknoloji Enstitüsü"],
    "EEE": ["Orta Doğu Teknik Üniversitesi", "İzmir Yüksek Teknoloji Enstitüsü"],
    "MATH": ["Orta Doğu Teknik Üniversitesi", "İzmir Yüksek Teknoloji Enstitüsü"],
    "MAT": ["Gebze Teknik Üniversitesi", "Hacettepe Üniversitesi"],
    "ME": ["İzmir Yüksek Teknoloji Enstitüsü"],
    "IE": ["Orta Doğu Teknik Üniversitesi"],
    "STAT": ["Orta Doğu Teknik Üniversitesi"],
}

STOPWORDS = {
    "introduction", "intro", "to", "and", "of", "in", "for", "the", "with", "on",
    "ders", "giriş", "ile", "ve", "bir", "that", "this", "course", "analysis",
    "ects", "akts", "syllabus", "weekly", "haftalık",
}


def compare_syllabus(
    text: str,
    university_filter: Optional[List[str]] = None,
    department_filter: Optional[List[str]] = None,
    threshold_profile: Optional[str] = None,
) -> ComparisonResponse:
    profile_name = (threshold_profile or DEFAULT_PROFILE).lower()
    profile = THRESHOLD_PROFILES.get(profile_name, THRESHOLD_PROFILES[DEFAULT_PROFILE])
    threshold = profile["threshold"]
    weak_floor = profile["weak_floor"]

    input_sections = split_into_sections(text)
    logger.info(
        f"compare_syllabus: {len(input_sections)} sections, profile={profile_name}, threshold={threshold}"
    )

    # Raw results keyed per input section, to allow per-section dedup by course.
    per_section_best: dict[str, dict[str, SectionMatchOut]] = defaultdict(dict)

    for section in input_sections:
        combined_text = f"{section['heading']}: {section['content']}"
        query_embedding = embedding_service.encode_single(combined_text)

        top_k = 20 if (university_filter or department_filter) else 12
        results = embedding_service.search(query_embedding, top_k=top_k)

        for result in results:
            score = result["score"]
            # Drop noise far below any reasonable similarity.
            if score < weak_floor:
                continue

            if university_filter:
                code_upper = result["course_code"].upper()
                if not any(code_upper.startswith(p.upper()) for p in university_filter):
                    continue

            if department_filter:
                course_dept = result.get("department", "") or ""
                if course_dept and not any(
                    d.lower() in course_dept.lower() for d in department_filter
                ):
                    continue

            matched_university = (result.get("university") or "").strip() or None
            matched_faculty = (result.get("faculty") or "").strip() or None
            if not matched_university or not matched_faculty:
                inferred_uni, inferred_fac = _infer_source_context(
                    result["course_code"], result.get("department", "")
                )
                matched_university = matched_university or inferred_uni
                matched_faculty = matched_faculty or inferred_fac

            shared_keywords = _shared_keywords(
                f"{section['heading']} {section['content']}",
                f"{result['section_heading']} {result.get('section_content', '')}",
                limit=8,
            )
            similarity_reason = _build_similarity_reason(
                input_heading=section["heading"],
                matched_heading=result["section_heading"],
                score=score,
                threshold=threshold,
                shared_keywords=shared_keywords,
                university=matched_university,
                faculty=matched_faculty,
            )

            match = SectionMatchOut(
                input_section=section["heading"],
                matched_course_code=result["course_code"],
                matched_course_name=result["course_name"],
                matched_university=matched_university,
                matched_faculty=matched_faculty,
                matched_section=result["section_heading"],
                similarity=round(score, 4),
                is_overlap=score >= threshold,
                similarity_reason=similarity_reason,
                details=SectionMatchDetail(
                    input_snippet=_truncate(section["content"]),
                    matched_snippet=_truncate(result.get("section_content", "")),
                    shared_keywords=shared_keywords,
                    threshold=threshold,
                ),
            )

            # Dedup: per input section, keep only the strongest match per course.
            bucket = per_section_best[section["heading"]]
            existing = bucket.get(result["course_code"])
            if not existing or match.similarity > existing.similarity:
                bucket[result["course_code"]] = match

    # Flatten + per-section top-k prune to reduce report noise.
    all_section_matches: list[SectionMatchOut] = []
    for heading, course_bucket in per_section_best.items():
        ranked = sorted(course_bucket.values(), key=lambda m: m.similarity, reverse=True)
        all_section_matches.extend(ranked[:MAX_MATCHES_PER_INPUT_SECTION])

    # Aggregate by course.
    course_matches: dict[str, list[SectionMatchOut]] = defaultdict(list)
    for m in all_section_matches:
        course_matches[m.matched_course_code].append(m)

    top_courses: list[TopCourseMatch] = []
    for code, matches in course_matches.items():
        sorted_matches = sorted(matches, key=lambda m: m.similarity, reverse=True)
        # Weighted aggregation: top-k average favors courses with multiple strong hits
        # over those with one outlier, without being dragged down by weak tails.
        top_n = sorted_matches[:TOP_CONTRIBUTING_MATCHES]
        agg = sum(m.similarity for m in top_n) / len(top_n)
        universities = [m.matched_university for m in matches if m.matched_university]
        faculties = [m.matched_faculty for m in matches if m.matched_faculty]
        explanation = _course_level_explanation(sorted_matches, threshold)
        top_courses.append(TopCourseMatch(
            course_code=code,
            course_name=matches[0].matched_course_name,
            matched_university=_most_common(universities),
            matched_faculty=_most_common(faculties),
            average_similarity=round(agg, 4),
            is_overlap=agg >= threshold,
            explanation=explanation,
            details=_build_top_course_detail(sorted_matches, threshold),
        ))

    top_courses.sort(key=lambda c: c.average_similarity, reverse=True)
    all_section_matches.sort(key=lambda m: m.similarity, reverse=True)

    # Overall metrics use the overlap share across input sections (sections that
    # found at least one above-threshold match), not raw match averages — this
    # prevents duplicate strong matches from inflating the score.
    total_input_sections = max(len(input_sections), 1)
    overlapping_sections = {
        m.input_section for m in all_section_matches if m.is_overlap
    }
    overlap_pct = (len(overlapping_sections) / total_input_sections) * 100
    overall_sim = (
        sum(m.similarity for m in all_section_matches) / len(all_section_matches)
        if all_section_matches else 0.0
    )
    overlap_class = _classify_overlap(overlap_pct)
    confidence = _confidence_level(all_section_matches, total_input_sections)

    filter_info = ""
    if university_filter:
        filter_info = f" (filtered by: {', '.join(university_filter)})"
    report = _generate_report(
        overall_sim=overall_sim,
        overlap_pct=overlap_pct,
        overlap_class=overlap_class,
        confidence=confidence,
        threshold=threshold,
        profile_name=profile_name,
        top_courses=top_courses,
        num_sections=total_input_sections,
        overlapping_section_count=len(overlapping_sections),
        filter_info=filter_info,
    )

    return ComparisonResponse(
        overall_similarity=round(overall_sim, 4),
        overlap_percentage=round(overlap_pct, 2),
        overlap_class=overlap_class,
        confidence=confidence,
        threshold=round(threshold, 4),
        threshold_profile=profile_name,
        top_courses=top_courses[:10],
        section_matches=all_section_matches,
        report_summary=report,
    )


def _classify_overlap(overlap_pct: float) -> str:
    if overlap_pct >= 50:
        return "high"
    if overlap_pct >= 20:
        return "moderate"
    return "low"


def _confidence_level(matches: list[SectionMatchOut], total_sections: int) -> str:
    """Confidence reflects sample size and the strength of top matches."""
    if total_sections < 2 or len(matches) < 3:
        return "low"
    top = sorted((m.similarity for m in matches), reverse=True)[:5]
    if not top:
        return "low"
    mean_top = sum(top) / len(top)
    if mean_top >= 0.75 and len(matches) >= 8:
        return "high"
    if mean_top >= 0.6:
        return "medium"
    return "low"


def _generate_report(
    *,
    overall_sim: float,
    overlap_pct: float,
    overlap_class: str,
    confidence: str,
    threshold: float,
    profile_name: str,
    top_courses: list[TopCourseMatch],
    num_sections: int,
    overlapping_section_count: int,
    filter_info: str,
) -> str:
    class_labels = {
        "high": "HIGH OVERLAP — significant content already covered elsewhere",
        "moderate": "MODERATE OVERLAP — partial conceptual alignment with existing courses",
        "low": "LOW OVERLAP — largely orthogonal to existing catalog",
    }
    lines = [
        "=" * 60,
        "CURRICULUM ORTHOGONALITY REPORT",
        "=" * 60,
        "",
        f"Analyzed {num_sections} input section(s){filter_info}.",
        f"Threshold profile: {profile_name} (cutoff {threshold:.0%}).",
        f"Overall average similarity: {overall_sim:.2%}",
        f"Overlapping sections: {overlapping_section_count}/{num_sections} "
        f"({overlap_pct:.1f}%)",
        f"Result: {class_labels[overlap_class]}",
        f"Confidence: {confidence.upper()} — based on sample size and match strength.",
        "",
    ]

    shown = top_courses[:10]
    if shown:
        lines.append(f"Top matching courses (showing {len(shown)}):")
        for i, course in enumerate(shown, 1):
            flag = " [OVERLAP]" if course.is_overlap else ""
            source = f" | {course.matched_university or 'Unknown'}"
            if course.matched_faculty:
                source += f" / {course.matched_faculty}"
            lines.append(
                f"  {i}. {course.course_code} — {course.course_name}: "
                f"{course.average_similarity:.2%}{flag}{source}"
            )
            lines.append(f"     Why: {course.explanation}")
    else:
        lines.append("No matches above the weak-match floor were found.")

    lines += ["", "=" * 60]
    return "\n".join(lines)


def _infer_source_context(course_code: str, department: str = "") -> tuple[Optional[str], Optional[str]]:
    prefix_match = re.match(r"^[A-Za-z]+", course_code or "")
    prefix = prefix_match.group(0).upper() if prefix_match else ""

    if prefix in UNIVERSITY_PREFIX_MAP:
        return UNIVERSITY_PREFIX_MAP[prefix]
    if prefix in AMBIGUOUS_PREFIX_MAP:
        universities = AMBIGUOUS_PREFIX_MAP[prefix]
        if len(universities) == 1:
            return universities[0], _faculty_from_department(department)
        return (
            f"Ambiguous ({' / '.join(universities)})",
            _faculty_from_department(department),
        )
    if prefix == "CS":
        return "Local Seed Catalog", _faculty_from_department(department)
    return None, _faculty_from_department(department)


def _faculty_from_department(department: str) -> Optional[str]:
    normalized = (department or "").lower()
    if not normalized:
        return None
    if any(t in normalized for t in ["mat", "fiz", "physics", "istat", "statistics"]):
        return "Faculty of Science"
    if any(t in normalized for t in ["müh", "engineering", "computer", "elektr", "machine"]):
        return "Faculty of Engineering"
    return "Related Faculty"


def _build_similarity_reason(
    *,
    input_heading: str,
    matched_heading: str,
    score: float,
    threshold: float,
    shared_keywords: list[str],
    university: Optional[str],
    faculty: Optional[str],
) -> str:
    if score >= max(threshold + 0.12, 0.85):
        strength = "Very strong semantic overlap"
    elif score >= threshold:
        strength = "Strong overlap above threshold"
    elif score >= threshold - 0.1:
        strength = "Moderate conceptual similarity just below threshold"
    else:
        strength = "Weak but related similarity"

    keyword_part = (
        f" Shared terms: {', '.join(shared_keywords[:5])}." if shared_keywords else ""
    )
    source_parts = [p for p in (university, faculty) if p]
    source_text = f" Source: {' / '.join(source_parts)}." if source_parts else ""

    return (
        f"{strength} between input section '{input_heading}' "
        f"and matched section '{matched_heading}'.{keyword_part}{source_text}"
    )


def _course_level_explanation(
    sorted_matches: list[SectionMatchOut], threshold: float
) -> str:
    if not sorted_matches:
        return "No contributing matches."
    best = sorted_matches[0]
    above = sum(1 for m in sorted_matches if m.similarity >= threshold)
    total = len(sorted_matches)
    headings = [m.input_section for m in sorted_matches[:3]]
    heading_list = ", ".join(f"'{h}'" for h in dict.fromkeys(headings))
    if above == 0:
        tag = f"all {total} contributing matches fall below the threshold"
    elif above == total:
        tag = f"all {total} contributing matches clear the threshold"
    else:
        tag = f"{above}/{total} contributing matches clear the threshold"
    return (
        f"Best section-level match at {best.similarity:.2%} from '{best.matched_section}'; "
        f"{tag}. Input sections driving this match: {heading_list}."
    )


def _shared_keywords(left: str, right: str, limit: int = 3) -> list[str]:
    left_tokens = {
        t.lower() for t in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]{4,}", left or "")
        if t.lower() not in STOPWORDS
    }
    right_tokens = {
        t.lower() for t in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]{4,}", right or "")
        if t.lower() not in STOPWORDS
    }
    return sorted(left_tokens.intersection(right_tokens))[:limit]


def _truncate(text: str, limit: int = SNIPPET_LIMIT) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "…"


def _build_top_course_detail(
    sorted_matches: list[SectionMatchOut], threshold: float
) -> Optional[TopCourseDetail]:
    if not sorted_matches:
        return None
    best = sorted_matches[0]
    contributors = [
        TopCourseContribution(
            input_section=m.input_section,
            matched_section=m.matched_section,
            similarity=m.similarity,
        )
        for m in sorted_matches[:TOP_CONTRIBUTING_MATCHES]
    ]

    merged_keywords: list[str] = []
    seen: set[str] = set()
    for m in sorted_matches:
        if not m.details or not m.details.shared_keywords:
            continue
        for kw in m.details.shared_keywords:
            if kw in seen:
                continue
            seen.add(kw)
            merged_keywords.append(kw)
            if len(merged_keywords) >= 8:
                break
        if len(merged_keywords) >= 8:
            break

    return TopCourseDetail(
        match_count=len(sorted_matches),
        best_similarity=best.similarity,
        threshold=threshold,
        shared_keywords=merged_keywords,
        contributing_matches=contributors,
    )


def _most_common(values: list[str]) -> Optional[str]:
    if not values:
        return None
    counts: dict[str, int] = defaultdict(int)
    for v in values:
        counts[v] += 1
    return max(counts, key=counts.get)
