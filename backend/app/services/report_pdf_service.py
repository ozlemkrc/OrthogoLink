"""
Renders a detailed Curriculum Orthogonality Report as a downloadable PDF.

Builds a styled, multi-section document (summary, verdict, AI analysis,
course-level findings, section-level matches) from a ComparisonResponse using
ReportLab. A Unicode TTF font is registered so Turkish course names render
correctly; falls back to the built-in Helvetica when no TTF is available.
"""
import logging
import os
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.schemas import ComparisonResponse

logger = logging.getLogger(__name__)

# Candidate Unicode TTFs: DejaVu (Linux/Docker via fonts-dejavu-core),
# then Arial (Windows dev). First existing pair wins.
_FONT_CANDIDATES = [
    (
        "DejaVuSans",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    (
        "Arial",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ),
]

# Brand palette (kept close to the web UI tone).
_INK = colors.HexColor("#1a2233")
_MUTED = colors.HexColor("#5b6678")
_LINE = colors.HexColor("#d9dee8")
_HEADER_BG = colors.HexColor("#2d3a55")
_ROW_ALT = colors.HexColor("#f4f6fa")
_OVERLAP = colors.HexColor("#c0392b")
_OVERLAP_BG = colors.HexColor("#fdecea")
_OK = colors.HexColor("#1e8449")
_ACCENT = colors.HexColor("#2d6cdf")


def _register_fonts() -> tuple[str, str]:
    """Register a Unicode TTF family; return (regular, bold) font names."""
    for family, regular_path, bold_path in _FONT_CANDIDATES:
        if not os.path.exists(regular_path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(family, regular_path))
            bold_name = family
            if os.path.exists(bold_path):
                bold_name = f"{family}-Bold"
                pdfmetrics.registerFont(TTFont(bold_name, bold_path))
            return family, bold_name
        except Exception as exc:  # pragma: no cover - font edge cases
            logger.warning("Failed to register font %s: %s", family, exc)
    # Built-in core fonts (Latin-1 only; Turkish glyphs may be missing).
    return "Helvetica", "Helvetica-Bold"


_FONT, _FONT_BOLD = _register_fonts()

_OVERLAP_LABELS = {
    "high": "HIGH OVERLAP - significant content already covered elsewhere",
    "moderate": "MODERATE OVERLAP - partial conceptual alignment with existing courses",
    "low": "LOW OVERLAP - largely orthogonal to existing catalog",
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "RTitle", parent=base["Title"], fontName=_FONT_BOLD,
            fontSize=20, textColor=_INK, spaceAfter=2, alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "RSubtitle", parent=base["Normal"], fontName=_FONT,
            fontSize=9, textColor=_MUTED, spaceAfter=2,
        ),
        "h2": ParagraphStyle(
            "RH2", parent=base["Heading2"], fontName=_FONT_BOLD,
            fontSize=13, textColor=_INK, spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "RBody", parent=base["Normal"], fontName=_FONT,
            fontSize=9.5, textColor=_INK, leading=14, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "RSmall", parent=base["Normal"], fontName=_FONT,
            fontSize=8, textColor=_MUTED, leading=11,
        ),
        "cell": ParagraphStyle(
            "RCell", parent=base["Normal"], fontName=_FONT,
            fontSize=8.5, textColor=_INK, leading=11,
        ),
        "cell_head": ParagraphStyle(
            "RCellHead", parent=base["Normal"], fontName=_FONT_BOLD,
            fontSize=8.5, textColor=colors.white, leading=11,
        ),
        "verdict": ParagraphStyle(
            "RVerdict", parent=base["Normal"], fontName=_FONT_BOLD,
            fontSize=11, textColor=colors.white, leading=15,
        ),
        "verdict_sub": ParagraphStyle(
            "RVerdictSub", parent=base["Normal"], fontName=_FONT,
            fontSize=9, textColor=colors.white, leading=13,
        ),
    }


def _esc(text) -> str:
    """Escape XML special chars so user content is safe in ReportLab Paragraphs."""
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _verdict_color(overlap_class: str) -> colors.Color:
    return {
        "high": _OVERLAP,
        "moderate": colors.HexColor("#b9770e"),
        "low": _OK,
    }.get(overlap_class, _OK)


def _metric_table(result: ComparisonResponse, st: dict, content_width: float) -> Table:
    rows = [
        ("Overall similarity", _pct(result.overall_similarity)),
        ("Overlap percentage", f"{result.overlap_percentage:.1f}%"),
        ("Overlap class", result.overlap_class.upper()),
        ("Confidence", result.confidence.upper()),
        ("Threshold profile", f"{result.threshold_profile} (cutoff {_pct(result.threshold)})"),
        ("Detected language", (result.detected_language or "unknown").upper()),
        ("Courses matched", str(len(result.top_courses))),
        ("Section matches", str(len(result.section_matches))),
    ]
    data = [
        [Paragraph(label, st["small"]), Paragraph(f"<b>{value}</b>", st["body"])]
        for label, value in rows
    ]
    table = Table(data, colWidths=[content_width * 0.4, content_width * 0.6])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, _LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _verdict_block(result: ComparisonResponse, st: dict, content_width: float) -> Table:
    color = _verdict_color(result.overlap_class)
    label = _OVERLAP_LABELS.get(result.overlap_class, _OVERLAP_LABELS["low"])
    overlap_courses = sum(1 for c in result.top_courses if c.is_overlap)
    detail = (
        f"{overlap_courses} of {len(result.top_courses)} matched courses cross the "
        f"overlap threshold of {_pct(result.threshold)}. Confidence: {result.confidence.upper()}."
    )
    inner = [
        [Paragraph(label, st["verdict"])],
        [Paragraph(detail, st["verdict_sub"])],
    ]
    table = Table(inner, colWidths=[content_width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
    ]))
    return table


def _status_chip(is_overlap: bool, st: dict) -> Paragraph:
    style = ParagraphStyle(
        "chip", parent=st["cell"], fontName=_FONT_BOLD,
        textColor=_OVERLAP if is_overlap else _OK,
    )
    return Paragraph("OVERLAP" if is_overlap else "UNIQUE", style)


def _top_courses_table(result: ComparisonResponse, st: dict, content_width: float) -> Table:
    header = [
        Paragraph("#", st["cell_head"]),
        Paragraph("Code", st["cell_head"]),
        Paragraph("Course", st["cell_head"]),
        Paragraph("Source", st["cell_head"]),
        Paragraph("Sim.", st["cell_head"]),
        Paragraph("Status", st["cell_head"]),
    ]
    data = [header]
    overlap_rows = []
    for i, course in enumerate(result.top_courses, 1):
        source = _esc(course.matched_university or "Unknown")
        if course.matched_faculty:
            source += f"<br/><font size=7 color='#5b6678'>{_esc(course.matched_faculty)}</font>"
        data.append([
            Paragraph(str(i), st["cell"]),
            Paragraph(_esc(course.course_code), st["cell"]),
            Paragraph(_esc(course.course_name), st["cell"]),
            Paragraph(source, st["cell"]),
            Paragraph(_pct(course.average_similarity), st["cell"]),
            _status_chip(course.is_overlap, st),
        ])
        if course.is_overlap:
            overlap_rows.append(i)

    widths = [
        content_width * 0.05, content_width * 0.13, content_width * 0.37,
        content_width * 0.27, content_width * 0.08, content_width * 0.10,
    ]
    table = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("GRID", (0, 0), (-1, -1), 0.3, _LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for idx in range(1, len(data)):
        if idx in overlap_rows:
            style.append(("BACKGROUND", (0, idx), (-1, idx), _OVERLAP_BG))
        elif idx % 2 == 0:
            style.append(("BACKGROUND", (0, idx), (-1, idx), _ROW_ALT))
    table.setStyle(TableStyle(style))
    return table


def _section_matches_table(result: ComparisonResponse, st: dict, content_width: float) -> Table:
    header = [
        Paragraph("Your section", st["cell_head"]),
        Paragraph("Matched course", st["cell_head"]),
        Paragraph("Their section", st["cell_head"]),
        Paragraph("Sim.", st["cell_head"]),
        Paragraph("Status", st["cell_head"]),
    ]
    data = [header]
    overlap_rows = []
    for i, m in enumerate(result.section_matches, 1):
        course = f"{_esc(m.matched_course_code)}<br/><font size=7 color='#5b6678'>{_esc(m.matched_course_name)}</font>"
        data.append([
            Paragraph(_esc(m.input_section), st["cell"]),
            Paragraph(course, st["cell"]),
            Paragraph(_esc(m.matched_section), st["cell"]),
            Paragraph(_pct(m.similarity), st["cell"]),
            _status_chip(m.is_overlap, st),
        ])
        if m.is_overlap:
            overlap_rows.append(i)

    widths = [
        content_width * 0.26, content_width * 0.27, content_width * 0.27,
        content_width * 0.09, content_width * 0.11,
    ]
    table = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("GRID", (0, 0), (-1, -1), 0.3, _LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for idx in range(1, len(data)):
        if idx in overlap_rows:
            style.append(("BACKGROUND", (0, idx), (-1, idx), _OVERLAP_BG))
        elif idx % 2 == 0:
            style.append(("BACKGROUND", (0, idx), (-1, idx), _ROW_ALT))
    table.setStyle(TableStyle(style))
    return table


def _ai_text_to_paragraphs(text: str, st: dict) -> list:
    """Render AI summary, converting **bold** markers to PDF bold tags."""
    import re

    flowables = []
    cleaned = re.sub(r"\s+(\d+\.\s)", r"\n\1", text).strip()
    for chunk in cleaned.split("\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        safe = (
            chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
        flowables.append(Paragraph(safe, st["body"]))
    return flowables


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(_FONT, 7.5)
    canvas.setFillColor(_MUTED)
    canvas.drawString(
        20 * mm, 12 * mm,
        "OrthogoLink - Curriculum Orthogonality Report",
    )
    canvas.drawRightString(
        A4[0] - 20 * mm, 12 * mm, f"Page {doc.page}",
    )
    canvas.setStrokeColor(_LINE)
    canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
    canvas.restoreState()


def generate_report_pdf(result: ComparisonResponse) -> bytes:
    """Build the full PDF report and return it as bytes."""
    buffer = BytesIO()
    margin = 20 * mm
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=18 * mm, bottomMargin=22 * mm,
        title="Curriculum Orthogonality Report",
    )
    content_width = A4[0] - 2 * margin
    st = _styles()
    story = []

    # Header
    story.append(Paragraph("Curriculum Orthogonality Report", st["title"]))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%d %B %Y, %H:%M')}", st["subtitle"],
    ))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=_ACCENT, spaceAfter=10))

    # Verdict
    story.append(_verdict_block(result, st, content_width))
    story.append(Spacer(1, 12))

    # Summary metrics
    story.append(Paragraph("Summary", st["h2"]))
    story.append(_metric_table(result, st, content_width))

    # AI analysis
    if result.ai_summary:
        story.append(Paragraph("AI Analysis", st["h2"]))
        story.extend(_ai_text_to_paragraphs(result.ai_summary, st))

    # Course-level findings
    story.append(Paragraph("Top Matching Courses", st["h2"]))
    if result.top_courses:
        story.append(_top_courses_table(result, st, content_width))
        story.append(Spacer(1, 8))
        story.append(Paragraph("Course-level findings", st["h2"]))
        for i, course in enumerate(result.top_courses, 1):
            flag = " (OVERLAP)" if course.is_overlap else ""
            heading = (
                f"<b>{i}. {_esc(course.course_code)} - {_esc(course.course_name)}</b> "
                f"&mdash; {_pct(course.average_similarity)}{flag}"
            )
            story.append(Paragraph(heading, st["body"]))
            if course.explanation:
                story.append(Paragraph(_esc(course.explanation), st["small"]))
            if course.details and course.details.shared_keywords:
                kws = _esc(", ".join(course.details.shared_keywords))
                story.append(Paragraph(f"Shared terms: {kws}", st["small"]))
            story.append(Spacer(1, 5))
    else:
        story.append(Paragraph(
            "No matches above the weak-match floor were found. The proposed "
            "syllabus appears orthogonal to the existing catalog.", st["body"],
        ))

    # Section-level matches
    if result.section_matches:
        story.append(Paragraph(
            f"Section-Level Matches ({len(result.section_matches)})", st["h2"],
        ))
        story.append(_section_matches_table(result, st, content_width))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()
