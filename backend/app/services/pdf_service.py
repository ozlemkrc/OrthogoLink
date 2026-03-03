"""
PDF text extraction and text section splitting service.
"""
import re
import logging
from io import BytesIO
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

# Common ECTS / syllabus section headings
SECTION_PATTERNS = [
    r"(?i)^#{1,3}\s+",                          # Markdown headings
    r"(?i)^(?:\d+[\.\)]\s+)",                    # Numbered headings: "1. " or "1) "
    r"(?i)^(course\s+description|ders\s+tanımı)",
    r"(?i)^(learning\s+outcomes?|öğrenme\s+çıktıları)",
    r"(?i)^(course\s+content|ders\s+içeriği)",
    r"(?i)^(objectives?|amaç)",
    r"(?i)^(prerequisites?|ön\s+koşul)",
    r"(?i)^(assessment|değerlendirme)",
    r"(?i)^(weekly\s+schedule|haftalık\s+plan)",
    r"(?i)^(textbooks?|references?|kaynaklar)",
    r"(?i)^(teaching\s+methods?|öğretim\s+yöntem)",
    r"(?i)^(ects\s+credits?|akts)",
    r"(?i)^(course\s+code|ders\s+kodu)",
    r"(?i)^(course\s+name|ders\s+adı)",
    r"(?i)^(instructor|öğretim\s+üyesi)",
    r"(?i)^(syllabus|müfredat)",
    r"(?i)^(topics?\s+covered|konu)",
]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text content from a PDF file."""
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    full_text = "\n\n".join(pages)
    logger.info(f"Extracted {len(full_text)} characters from PDF ({len(reader.pages)} pages)")
    return full_text


def split_into_sections(text: str) -> list[dict]:
    """
    Split text into logical sections based on heading detection.
    Returns list of {"heading": str, "content": str}.
    Falls back to paragraph-based splitting if no headings found.
    """
    lines = text.split("\n")
    sections = []
    current_heading = "General"
    current_content = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        is_heading = False
        for pattern in SECTION_PATTERNS:
            if re.match(pattern, stripped):
                is_heading = True
                break

        # Also detect short lines in ALL CAPS or Title Case as headings
        if not is_heading and len(stripped) < 80 and stripped[0].isupper():
            word_count = len(stripped.split())
            if word_count <= 8:
                upper_ratio = sum(1 for c in stripped if c.isupper()) / max(len(stripped.replace(" ", "")), 1)
                if upper_ratio > 0.5 or stripped.endswith(":"):
                    is_heading = True

        if is_heading:
            # Save accumulated content under previous heading
            if current_content:
                content_text = " ".join(current_content).strip()
                if len(content_text) > 20:  # Skip near-empty sections
                    sections.append({"heading": current_heading, "content": content_text})
            current_heading = stripped.rstrip(":")
            current_content = []
        else:
            current_content.append(stripped)

    # Final section
    if current_content:
        content_text = " ".join(current_content).strip()
        if len(content_text) > 20:
            sections.append({"heading": current_heading, "content": content_text})

    # Fallback: if we couldn't split well, treat entire text as one section
    if not sections:
        sections.append({"heading": "Full Content", "content": text.strip()})

    logger.info(f"Split text into {len(sections)} sections")
    return sections
