"""
Unit tests for section splitting in ``pdf_service``.

PDF byte extraction itself (``extract_text_from_pdf``) is a thin wrapper over
PyPDF2 and is not unit tested here; the section-splitting logic that feeds the
embedding pipeline is the part with real branching behaviour.
"""
import pytest

from app.services import pdf_service as ps


# ── Heading-based splitting ──────────────────────────────────────

def test_splits_on_known_bilingual_headings():
    text = (
        "Course Description\n"
        "This course introduces the fundamentals of algorithms and data structures.\n"
        "Learning Outcomes\n"
        "Students will be able to analyze algorithmic complexity and design data structures.\n"
        "Course Content\n"
        "Sorting, searching, trees, graphs, hashing, and dynamic programming techniques.\n"
    )
    sections = ps.split_into_sections(text)
    headings = {s["heading"] for s in sections}
    assert "Course Description" in headings
    assert "Learning Outcomes" in headings
    assert "Course Content" in headings


def test_splits_on_turkish_headings():
    text = (
        "Ders Tanımı\n"
        "Bu ders algoritmalar ve veri yapıları konularına giriş niteliğindedir.\n"
        "Öğrenme Çıktıları\n"
        "Öğrenciler algoritma karmaşıklığını analiz edebilecek duruma gelir.\n"
        "Ders İçeriği\n"
        "Sıralama, arama, ağaçlar, çizgeler ve dinamik programlama teknikleri.\n"
    )
    sections = ps.split_into_sections(text)
    headings = {s["heading"] for s in sections}
    assert "Ders Tanımı" in headings
    assert "Ders İçeriği" in headings
    assert "Öğrenme Çıktıları" in headings


def test_numbered_headings_detected():
    text = (
        "1. Overview\n"
        "An introductory overview of relational database systems and their design.\n"
        "2. Topics\n"
        "Normalization, indexing, transactions, query optimization, and concurrency.\n"
    )
    sections = ps.split_into_sections(text)
    assert len(sections) >= 2


def test_short_content_under_min_length_dropped():
    # Content shorter than the 20-char minimum should not become a section.
    text = (
        "Course Content\n"
        "short\n"
        "Learning Outcomes\n"
        "Students will master the full breadth of database design principles here.\n"
    )
    sections = ps.split_into_sections(text)
    contents = [s["content"] for s in sections]
    assert "short" not in contents


# ── Chunk fallback ───────────────────────────────────────────────

def test_chunk_fallback_when_no_headings():
    # A long wall of text with no detectable headings should be chunked into
    # multiple overlapping pieces rather than a single giant section.
    sentence = (
        "The system computes semantic similarity between course syllabi using "
        "sentence embeddings and approximate nearest neighbour search. "
    )
    text = sentence * 40  # well over the chunk target size
    sections = ps.split_into_sections(text)
    assert len(sections) >= 2
    assert all(s["heading"].startswith("Chunk") for s in sections)


def test_chunk_fallback_overlap_keeps_continuity():
    sentence = "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda. "
    text = sentence * 30
    chunks = ps._chunk_fallback(text)
    assert len(chunks) >= 2
    # Chunks should be bounded by the target size (plus boundary snap slack).
    assert all(len(c["content"]) <= ps.CHUNK_TARGET_CHARS + 5 for c in chunks)


def test_short_text_returns_single_full_content():
    sections = ps._chunk_fallback("Just a short blurb about one topic only.")
    assert len(sections) == 1
    assert sections[0]["heading"] == "Full Content"


def test_empty_text_returns_no_sections():
    assert ps._chunk_fallback("") == []
    assert ps.split_into_sections("") == []


def test_single_long_unbroken_section_triggers_fallback():
    # One heading followed by an extremely long body should fall back to chunking
    # because the single section exceeds 2x the chunk target.
    body = (
        "Topic content describing algorithmic techniques in great detail. "
        * 60
    )
    text = f"Course Content\n{body}\n"
    sections = ps.split_into_sections(text)
    assert len(sections) >= 2
