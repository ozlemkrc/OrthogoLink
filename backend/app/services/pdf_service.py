"""
PDF text extraction and text section splitting service.
"""
import re
import logging
from io import BytesIO
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

# Bilingual TR/EN ECTS syllabus heading patterns.
SECTION_PATTERNS = [
    r"(?i)^#{1,3}\s+",
    r"(?i)^(?:\d+[\.\)]\s+)",
    r"(?i)^(course\s+(description|info(rmation)?|details?)|ders\s+(tanımı|bilgileri|içeriği))\b",
    r"(?i)^(learning\s+outcomes?|course\s+outcomes?|öğrenme\s+çıktıları|ders\s+çıktıları|kazanımlar)\b",
    r"(?i)^(course\s+content|content\s+of\s+the\s+course|ders\s+içeriği|içerik)\b",
    r"(?i)^(aims?\s+of\s+the\s+course|course\s+aims?|objectives?|amaç|hedef(ler)?)\b",
    r"(?i)^(prerequisites?|pre[- ]?requisites?|ön\s+koşul(lar)?|ön\s+şart)\b",
    r"(?i)^(assessment|evaluation|grading|değerlendirme|başarı\s+değerlendirme)\b",
    r"(?i)^(weekly\s+(schedule|topics|plan)|course\s+schedule|haftalık\s+(plan|konular|program))\b",
    r"(?i)^(textbooks?|references?|reading\s+list|bibliograph(y|ie)|kaynaklar|ders\s+kitab[ıi])\b",
    r"(?i)^(teaching\s+methods?|instruction\s+methods?|öğretim\s+yöntem(ler)?i)\b",
    r"(?i)^(ects\s+credits?|akts(\s+kredisi)?|credits?)\b",
    r"(?i)^(course\s+code|ders\s+kodu)\b",
    r"(?i)^(course\s+(name|title)|ders\s+adı)\b",
    r"(?i)^(instructor|lecturer|öğretim\s+(üyesi|eleman[ıi]))\b",
    r"(?i)^(syllabus|müfredat|izlence)\b",
    r"(?i)^(topics?\s+covered|covered\s+topics?|konu(lar)?|işlenen\s+konular)\b",
    r"(?i)^(skills?\s+(acquired|gained)|kazandırılan\s+beceriler)\b",
    r"(?i)^(laboratory|lab\s+work|laboratuvar)\b",
    r"(?i)^(language\s+of\s+instruction|öğretim\s+dili)\b",
    r"(?i)^(recommended\s+reading|önerilen\s+kaynaklar)\b",
]

# Fallback chunking parameters when headings cannot be detected.
CHUNK_MIN_CHARS = 400
CHUNK_TARGET_CHARS = 900
CHUNK_OVERLAP = 120
MIN_USEFUL_SECTIONS = 2


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
    Falls back to sliding-chunk splitting when headings are absent or sparse.
    """
    sections = _split_by_headings(text)

    # If heading-based split produced too few useful pieces, use chunk fallback
    # over the original text so we still generate multiple comparable sections.
    if len(sections) < MIN_USEFUL_SECTIONS or _single_section_too_long(sections):
        chunked = _chunk_fallback(text)
        if len(chunked) > len(sections):
            logger.info(
                f"Heading split yielded {len(sections)} sections; "
                f"using chunk fallback with {len(chunked)} chunks"
            )
            return chunked

    logger.info(f"Split text into {len(sections)} sections")
    return sections


def _split_by_headings(text: str) -> list[dict]:
    lines = text.split("\n")
    sections: list[dict] = []
    current_heading = "General"
    current_content: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        is_heading = any(re.match(p, stripped) for p in SECTION_PATTERNS)

        if not is_heading and len(stripped) < 80 and stripped[0].isupper():
            word_count = len(stripped.split())
            if word_count <= 8:
                non_space = max(len(stripped.replace(" ", "")), 1)
                upper_ratio = sum(1 for c in stripped if c.isupper()) / non_space
                if upper_ratio > 0.5 or stripped.endswith(":"):
                    is_heading = True

        if is_heading:
            if current_content:
                content_text = " ".join(current_content).strip()
                if len(content_text) > 20:
                    sections.append({"heading": current_heading, "content": content_text})
            current_heading = stripped.rstrip(":")
            current_content = []
        else:
            current_content.append(stripped)

    if current_content:
        content_text = " ".join(current_content).strip()
        if len(content_text) > 20:
            sections.append({"heading": current_heading, "content": content_text})

    return sections


def _single_section_too_long(sections: list[dict]) -> bool:
    if len(sections) != 1:
        return False
    return len(sections[0]["content"]) > CHUNK_TARGET_CHARS * 2


def _chunk_fallback(text: str) -> list[dict]:
    """Produce overlapping chunks when heading detection failed."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) < CHUNK_MIN_CHARS:
        return [{"heading": "Full Content", "content": cleaned}] if cleaned else []

    chunks: list[dict] = []
    start = 0
    idx = 1
    n = len(cleaned)
    step = max(CHUNK_TARGET_CHARS - CHUNK_OVERLAP, 200)
    while start < n:
        end = min(start + CHUNK_TARGET_CHARS, n)
        # Snap end to the nearest sentence/word boundary
        if end < n:
            boundary = cleaned.rfind(". ", start + step, end)
            if boundary == -1:
                boundary = cleaned.rfind(" ", start + step, end)
            if boundary != -1:
                end = boundary + 1
        chunk = cleaned[start:end].strip()
        if len(chunk) > 20:
            chunks.append({"heading": f"Chunk {idx}", "content": chunk})
            idx += 1
        if end >= n:
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks
