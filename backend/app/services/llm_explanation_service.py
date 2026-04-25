"""
LLM-based curriculum insight service — calls Gemini REST API directly via aiohttp.
No Google SDK required; aiohttp is already a project dependency.
"""
import asyncio
import hashlib
import logging
import re
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Hard cap on prompt length sent to Gemini to avoid 429 / quota-per-request errors.
# Free-tier flash models accept far more, but smaller prompts = fewer rate-limit hits
# and faster responses. ~3500 chars ≈ 900 tokens, well under any per-minute cap.
MAX_PROMPT_CHARS = 3500
MAX_PAIR_LINES = 4
MAX_KEYWORDS = 12
MAX_SECTION_CHARS = 90


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"

# In-memory cache: sha256(course_code|sections_key|threshold_profile|language) → dict
_cache: dict[str, dict] = {}


def _cache_key(course_code: str, sections_key: str, threshold_profile: str, language: str) -> str:
    raw = f"{course_code}|{sections_key}|{threshold_profile}|{language}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def _call_gemini(api_key: str, model: str, prompt: str, timeout: float) -> str:
    """
    POST to Gemini generateContent REST endpoint.
    Raises on HTTP errors so the caller can handle fallback / retry.
    """
    url = f"{GEMINI_API_BASE}/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 800,
            "temperature": 0.4,
            # Gemini 2.5 reserves output tokens for hidden "thinking" — disable it
            # so the full budget is spent on the visible answer.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            data = await resp.json()

            if resp.status == 429:
                raise Exception(f"429 RESOURCE_EXHAUSTED. {data}")
            if resp.status != 200:
                raise Exception(f"{resp.status} {data}")

            candidates = data.get("candidates") or []
            if not candidates:
                raise Exception(f"Gemini returned no candidates: {data}")
            cand = candidates[0]
            parts = (cand.get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts).strip()
            if not text:
                finish = cand.get("finishReason", "UNKNOWN")
                raise Exception(f"Gemini returned empty text (finishReason={finish})")
            return text


def _build_insight_prompt(
    course_code: str,
    course_name: str,
    university: str,
    overlap_class: str,
    shared_keywords: list[str],
    contributing_matches: list,
    language: str,
    is_cross_university: bool = False,
) -> str:
    pair_lines = "\n".join(
        f'  • "{_truncate(m.input_section, MAX_SECTION_CHARS)}" ↔ "{_truncate(m.matched_section, MAX_SECTION_CHARS)}"'
        for m in (contributing_matches or [])[:MAX_PAIR_LINES]
    ) or "  • (section-level pairs not available)"

    kw_str = ", ".join(shared_keywords[:MAX_KEYWORDS]) if shared_keywords else "(none detected)"

    overlap_severity = {
        "high":     ("kritik düzeyde" if language == "tr" else "critically"),
        "moderate": ("orta düzeyde"   if language == "tr" else "moderately"),
        "low":      ("kısmen"         if language == "tr" else "partially"),
    }.get(overlap_class, "kısmen" if language == "tr" else "partially")

    if language == "tr":
        if is_cross_university:
            q4 = "4. **Kıyaslama içgörüsü:** Bu örtüşme, söz konusu konunun farklı üniversitelerde nasıl ele alındığı hakkında ne söylüyor? Yeni ders, mevcut yaklaşımlardan nasıl farklılaşabilir?"
        else:
            q4 = "4. **Komite önerisi:** Tek ve somut eylem önerisi (birleştir / ön koşul yap / kapsam daralt / farklılaştır)."

        return f"""Sen Türkiye'deki bir üniversitede görev yapan deneyimli bir müfredat komitesi danışmanısın.

Değerlendirilen yeni ders izlencesi, aşağıdaki kayıtlı dersle **{overlap_severity} örtüşüyor**:

**Kayıtlı ders:** {course_code} — {course_name} ({university})

**Örtüşen bölüm çiftleri** (yeni izlence ↔ kayıtlı ders):
{pair_lines}

**Ortak akademik terminoloji:** {kw_str}

---

Bu verileri analiz et ve şu dört soruyu yanıtla. **Sayıları, yüzdeleri veya bölüm kodlarını tekrarlama** — bunları kullanıcı zaten görüyor. Bunun yerine kendi akademik bilginle bu bölüm adlarının ve terimlerin ne anlama geldiğini çıkar.

1. **Akademik alan:** Bu bölüm adları ve terminoloji hangi alt disiplini temsil ediyor?
2. **Örtüşmenin niteliği:** Temel içerik tekrarı mı, ön koşul ilişkisi mi, yoksa yöntemsel örtüşme mi?
3. **Öğrenci üzerindeki etki:** Her iki dersi alan bir öğrenci hangi konuları iki kez öğrenir?
{q4}

3-5 cümle, akıcı akademik dil."""

    if is_cross_university:
        q4 = "4. **Benchmark insight:** What does this overlap reveal about how this topic is approached across institutions? How could the new course differentiate itself from the existing offerings?"
    else:
        q4 = "4. **Committee recommendation:** One concrete action (merge / set as prerequisite / narrow scope / differentiate)."

    return f"""You are an experienced curriculum committee advisor at a university.

The new course syllabus being evaluated **{overlap_severity} overlaps** with the following registered course:

**Registered course:** {course_code} — {course_name} ({university})

**Overlapping section pairs** (new syllabus ↔ registered course):
{pair_lines}

**Shared academic terminology:** {kw_str}

---

Analyze this and answer the four questions below. **Do NOT restate numbers, percentages, or section codes** — the user already sees those. Use your own academic knowledge to infer what these section names and terms mean intellectually.

1. **Academic domain:** What sub-discipline do these section names and terminology represent?
2. **Nature of overlap:** Core content redundancy, prerequisite relationship, or methodological overlap?
3. **Student impact:** What specific topics would a student learn twice if taking both courses?
{q4}

3-5 sentences in fluent academic prose."""


def _fallback_explanation(
    course_code: str,
    course_name: str,
    average_similarity: float,
    match_count: int,
    shared_keywords: list[str],
    language: str,
) -> str:
    kw_count = len(shared_keywords or [])
    if language == "tr":
        kw_part = f" {kw_count} ortak anahtar terim tespit edildi." if kw_count else ""
        return (
            f"Bu ders, '{course_name}' ({course_code}) dersiyle "
            f"ortalama %{average_similarity * 100:.1f} benzerlik göstermektedir. "
            f"{match_count} bölüm eşleşmesi bulundu.{kw_part}"
        )
    kw_part = f" {kw_count} shared keyword(s) identified." if kw_count else ""
    return (
        f"This syllabus shows {average_similarity * 100:.1f}% average similarity "
        f"with '{course_name}' ({course_code}). "
        f"{match_count} section match(es) found.{kw_part}"
    )


async def generate_ai_explanation(
    course_code: str,
    course_name: str,
    university: str,
    average_similarity: float,
    is_overlap: bool,
    detail,
    threshold: float,
    overlap_class: str,
    threshold_profile: str = "balanced",
    language: str = "tr",
    is_cross_university: bool = False,
) -> tuple[str, str, str]:
    """
    Returns (insight_text, confidence, source).
    source: "ai" | "ai_cached" | "fallback"
    Never raises — always returns a usable string.
    """
    from app.core.config import get_settings
    settings = get_settings()

    if not settings.AI_EXPLANATIONS_ENABLED or not settings.AI_API_KEY:
        return _fallback_explanation(
            course_code, course_name, average_similarity,
            detail.match_count, detail.shared_keywords, language,
        ), "low", "fallback"

    sections_key = "|".join(
        f"{m.input_section}:{m.matched_section}"
        for m in (detail.contributing_matches or [])
    )
    key = _cache_key(course_code, sections_key, threshold_profile, language)

    if key in _cache:
        cached = _cache[key]
        return cached["text"], cached["confidence"], "ai_cached"

    prompt = _build_insight_prompt(
        course_code, course_name, university, overlap_class,
        detail.shared_keywords, detail.contributing_matches, language,
        is_cross_university=is_cross_university,
    )
    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[:MAX_PROMPT_CHARS - 1].rstrip() + "…"

    last_exc: Optional[Exception] = None
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            text = await _call_gemini(
                api_key=settings.AI_API_KEY,
                model=settings.AI_MODEL,
                prompt=prompt,
                timeout=float(settings.AI_TIMEOUT_SECONDS),
            )
            confidence = "high" if detail.best_similarity > threshold + 0.08 else "medium"
            _cache[key] = {"text": text, "confidence": confidence}
            return text, confidence, "ai"

        except asyncio.TimeoutError as exc:
            logger.warning("Gemini timed out for %s", course_code)
            last_exc = exc
            break

        except Exception as exc:
            err = str(exc)
            if "429" in err and attempt < max_attempts - 1:
                m = re.search(r"retryDelay.*?(\d+)s", err)
                wait = int(m.group(1)) + 1 if m else (5 * (attempt + 1))
                logger.info("Gemini rate-limited for %s, retrying in %ds…", course_code, wait)
                await asyncio.sleep(wait)
                last_exc = exc
            else:
                logger.warning("Gemini failed for %s: %s", course_code, exc)
                last_exc = exc
                break

    return _fallback_explanation(
        course_code, course_name, average_similarity,
        detail.match_count, detail.shared_keywords, language,
    ), "low", "fallback"
