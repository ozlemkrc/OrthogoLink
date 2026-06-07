"""
Unit tests for the deterministic logic in ``comparison_service``.

These cover the scoring, classification, aggregation, and reporting helpers —
the parts of the pipeline whose correctness does not depend on the embedding
model. The semantic-quality of matches is evaluated separately by
``eval/benchmark.py``.
"""
import pytest

from app.services import comparison_service as cs
from app.models.schemas import SectionMatchOut, SectionMatchDetail


def make_match(
    similarity: float,
    *,
    input_section: str = "Course Content",
    course_code: str = "CS301",
    course_name: str = "Data Structures",
    matched_section: str = "Course Content",
    is_overlap: bool | None = None,
    keywords: list[str] | None = None,
    university: str | None = "Local Seed Catalog",
    faculty: str | None = "Faculty of Engineering",
) -> SectionMatchOut:
    """Construct a SectionMatchOut with sensible defaults for testing."""
    return SectionMatchOut(
        input_section=input_section,
        matched_course_code=course_code,
        matched_course_name=course_name,
        matched_university=university,
        matched_faculty=faculty,
        matched_section=matched_section,
        similarity=similarity,
        is_overlap=similarity >= 0.7 if is_overlap is None else is_overlap,
        similarity_reason="test",
        details=SectionMatchDetail(
            input_snippet="x",
            matched_snippet="y",
            shared_keywords=keywords or [],
            threshold=0.7,
        ),
    )


# ── _classify_overlap ────────────────────────────────────────────

@pytest.mark.parametrize("pct,expected", [
    (0, "low"),
    (19.9, "low"),
    (20, "moderate"),
    (49.9, "moderate"),
    (50, "high"),
    (100, "high"),
])
def test_classify_overlap_boundaries(pct, expected):
    assert cs._classify_overlap(pct) == expected


# ── _clamp_threshold ─────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    (0.7, 0.7),
    (0.1, 0.3),       # below floor -> clamped up
    (0.99, 0.95),     # above ceiling -> clamped down
    (0.3, 0.3),
    (0.95, 0.95),
])
def test_clamp_threshold_range(value, expected):
    assert cs._clamp_threshold(value) == pytest.approx(expected)


def test_clamp_threshold_invalid_returns_default():
    default = cs.THRESHOLD_PROFILES[cs.DEFAULT_PROFILE]["threshold"]
    assert cs._clamp_threshold("not-a-number") == default
    assert cs._clamp_threshold(None) == default


# ── _confidence_level ────────────────────────────────────────────

def test_confidence_low_when_too_few_sections():
    matches = [make_match(0.9) for _ in range(10)]
    assert cs._confidence_level(matches, total_sections=1) == "low"


def test_confidence_low_when_too_few_matches():
    matches = [make_match(0.9), make_match(0.9)]
    assert cs._confidence_level(matches, total_sections=5) == "low"


def test_confidence_high_for_many_strong_matches():
    matches = [make_match(0.8) for _ in range(8)]
    assert cs._confidence_level(matches, total_sections=5) == "high"


def test_confidence_medium_for_moderate_matches():
    matches = [make_match(0.62) for _ in range(5)]
    assert cs._confidence_level(matches, total_sections=5) == "medium"


def test_confidence_low_for_weak_matches():
    matches = [make_match(0.5) for _ in range(5)]
    assert cs._confidence_level(matches, total_sections=5) == "low"


# ── _shared_keywords ─────────────────────────────────────────────

def test_shared_keywords_intersects_and_filters_stopwords():
    left = "Introduction to sorting algorithms and trees"
    right = "Advanced sorting algorithms with balanced trees"
    shared = cs._shared_keywords(left, right, limit=8)
    assert "sorting" in shared
    assert "algorithms" in shared
    assert "trees" in shared
    # Stopwords must never appear.
    assert "introduction" not in shared
    assert "and" not in shared


def test_shared_keywords_respects_limit_and_min_length():
    left = "data data structures graphs heaps"
    right = "data structures graphs heaps queues"
    shared = cs._shared_keywords(left, right, limit=2)
    assert len(shared) == 2
    # 3-char tokens are excluded by the >=4 char rule.
    assert all(len(k) >= 4 for k in shared)


def test_shared_keywords_handles_turkish_characters():
    left = "Veri yapıları ağaçlar çizgeler"
    right = "Veri yapıları ağaçlar kümeler"
    shared = cs._shared_keywords(left, right, limit=8)
    assert "yapıları" in shared
    assert "ağaçlar" in shared


def test_shared_keywords_empty_inputs():
    assert cs._shared_keywords("", "") == []
    assert cs._shared_keywords(None, None) == []


# ── _truncate ────────────────────────────────────────────────────

def test_truncate_short_text_unchanged():
    assert cs._truncate("hello") == "hello"


def test_truncate_long_text_adds_ellipsis():
    text = "a" * (cs.SNIPPET_LIMIT + 50)
    out = cs._truncate(text)
    assert out.endswith("…")
    assert len(out) <= cs.SNIPPET_LIMIT + 1


def test_truncate_empty():
    assert cs._truncate("") == ""
    assert cs._truncate(None) == ""


# ── _most_common ─────────────────────────────────────────────────

def test_most_common_returns_majority():
    assert cs._most_common(["A", "B", "A", "A", "B"]) == "A"


def test_most_common_empty_returns_none():
    assert cs._most_common([]) is None


# ── _infer_source_context ────────────────────────────────────────

def test_infer_source_known_prefix():
    uni, fac = cs._infer_source_context("BLM301", "Bilgisayar Mühendisliği")
    assert uni == "Gebze Teknik Üniversitesi"
    assert fac == "Mühendislik Fakültesi"


def test_infer_source_ambiguous_prefix():
    uni, fac = cs._infer_source_context("CENG301", "Computer Engineering")
    assert uni.startswith("Ambiguous")
    assert "Orta Doğu" in uni and "İzmir" in uni


def test_infer_source_single_ambiguous_resolves():
    uni, _ = cs._infer_source_context("IE202", "Industrial Engineering")
    assert uni == "Orta Doğu Teknik Üniversitesi"


def test_infer_source_seed_catalog():
    uni, _ = cs._infer_source_context("CS101", "Computer Science")
    assert uni == "Local Seed Catalog"


def test_infer_source_unknown_prefix_returns_none_uni():
    uni, fac = cs._infer_source_context("ZZZ999", "")
    assert uni is None
    assert fac is None


# ── _faculty_from_department ─────────────────────────────────────

@pytest.mark.parametrize("dept,expected", [
    ("Matematik", "Faculty of Science"),
    ("Physics", "Faculty of Science"),
    ("Computer Engineering", "Faculty of Engineering"),
    ("Makine Mühendisliği", "Faculty of Engineering"),
    ("History", "Related Faculty"),
    ("", None),
])
def test_faculty_from_department(dept, expected):
    assert cs._faculty_from_department(dept) == expected


# ── _course_level_explanation ────────────────────────────────────

def test_course_explanation_all_above_threshold():
    matches = [make_match(0.85), make_match(0.8), make_match(0.75)]
    text = cs._course_level_explanation(matches, threshold=0.7)
    assert "all 3 contributing matches clear" in text
    assert "85" in text  # best similarity rendered as percent


def test_course_explanation_partial():
    matches = [make_match(0.85), make_match(0.6), make_match(0.5)]
    text = cs._course_level_explanation(matches, threshold=0.7)
    assert "1/3 contributing matches clear" in text


def test_course_explanation_none_above():
    matches = [make_match(0.6), make_match(0.5)]
    text = cs._course_level_explanation(matches, threshold=0.7)
    assert "fall below the threshold" in text


def test_course_explanation_empty():
    assert cs._course_level_explanation([], threshold=0.7) == "No contributing matches."


# ── _build_top_course_detail ─────────────────────────────────────

def test_build_top_course_detail_merges_keywords_and_caps_contributors():
    matches = [
        make_match(0.9, keywords=["sorting", "trees"]),
        make_match(0.85, keywords=["trees", "graphs"]),
        make_match(0.8, keywords=["heaps"]),
        make_match(0.7, keywords=["queues"]),
    ]
    detail = cs._build_top_course_detail(matches, threshold=0.7)
    assert detail.match_count == 4
    assert detail.best_similarity == 0.9
    # Keywords deduped across matches, order preserved.
    assert detail.shared_keywords == ["sorting", "trees", "graphs", "heaps", "queues"]
    # Contributors capped at TOP_CONTRIBUTING_MATCHES.
    assert len(detail.contributing_matches) == cs.TOP_CONTRIBUTING_MATCHES


def test_build_top_course_detail_empty_returns_none():
    assert cs._build_top_course_detail([], threshold=0.7) is None


# ── _blend_score (cross-encoder re-ranking) ──────────────────────

def test_blend_score_weight_zero_is_pure_cosine():
    assert cs._blend_score(0.8, 0.2, weight=0.0) == pytest.approx(0.8)


def test_blend_score_weight_one_is_pure_cross_encoder():
    assert cs._blend_score(0.8, 0.2, weight=1.0) == pytest.approx(0.2)


def test_blend_score_midpoint_averages():
    assert cs._blend_score(0.8, 0.4, weight=0.5) == pytest.approx(0.6)


@pytest.mark.parametrize("weight", [-1.0, 2.0])
def test_blend_score_clamps_weight_into_unit_range(weight):
    # Out-of-range weights are clamped to 0/1 rather than extrapolating.
    out = cs._blend_score(0.8, 0.2, weight=weight)
    assert 0.2 <= out <= 0.8


def test_blend_score_stays_in_unit_interval():
    for c in (0.0, 0.3, 1.0):
        for e in (0.0, 0.5, 1.0):
            out = cs._blend_score(c, e, weight=0.5)
            assert 0.0 <= out <= 1.0


# ── _generate_report ─────────────────────────────────────────────

def test_generate_report_contains_key_sections():
    from app.models.schemas import TopCourseMatch
    top = [TopCourseMatch(
        course_id=1,
        course_code="CS301",
        course_name="Data Structures",
        matched_university="Local Seed Catalog",
        matched_faculty="Faculty of Engineering",
        average_similarity=0.82,
        is_overlap=True,
        explanation="strong",
    )]
    report = cs._generate_report(
        overall_sim=0.8,
        overlap_pct=60.0,
        overlap_class="high",
        confidence="high",
        threshold=0.7,
        profile_name="balanced",
        top_courses=top,
        num_sections=5,
        overlapping_section_count=3,
        filter_info="",
    )
    assert "CURRICULUM ORTHOGONALITY REPORT" in report
    assert "HIGH OVERLAP" in report
    assert "CS301" in report
    assert "[OVERLAP]" in report
    assert "Confidence: HIGH" in report


def test_generate_report_handles_no_matches():
    report = cs._generate_report(
        overall_sim=0.0,
        overlap_pct=0.0,
        overlap_class="low",
        confidence="low",
        threshold=0.7,
        profile_name="balanced",
        top_courses=[],
        num_sections=3,
        overlapping_section_count=0,
        filter_info="",
    )
    assert "No matches above the weak-match floor" in report
    assert "LOW OVERLAP" in report


def test_generate_report_scoring_line_reflects_reranking():
    base_kwargs = dict(
        overall_sim=0.5,
        overlap_pct=10.0,
        overlap_class="low",
        confidence="low",
        threshold=0.7,
        profile_name="balanced",
        top_courses=[],
        num_sections=3,
        overlapping_section_count=0,
        filter_info="",
    )
    assert "cosine" in cs._generate_report(**base_kwargs)
    assert "cross-encoder" in cs._generate_report(**base_kwargs, reranked=True)
