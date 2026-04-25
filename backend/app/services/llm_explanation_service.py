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
            return f"""Sen deneyimli bir müfredat danışmanısın. Bir öğretim üyesi, kendi üniversitesine yeni bir ders eklemeyi planlıyor ve başka üniversitelerde benzer derslerin zaten var olup olmadığını araştırıyor.

Önerilen yeni ders izlencesi, başka bir üniversitedeki şu dersle **{overlap_severity} örtüşüyor**:

**Karşılaştırılan ders:** {course_code} — {course_name} ({university})

**Örtüşen bölüm çiftleri** (önerilen ders ↔ karşılaştırılan ders):
{pair_lines}

**Ortak akademik terminoloji:** {kw_str}

---

Bu verileri analiz et ve şu dört soruyu yanıtla. **Sayıları, yüzdeleri veya bölüm kodlarını tekrarlama** — bunları kullanıcı zaten görüyor.

1. **Akademik alan:** Bu bölüm adları ve terminoloji hangi alt disiplini temsil ediyor?
2. **Standart kapsam:** Bu benzerlik, söz konusu konunun üniversitelerde yaygın biçimde nasıl öğretildiğini gösteriyor; bu alanda standart kabul gören konular neler?
3. **Farklılaşma fırsatı:** Önerilen ders, {university}'deki mevcut yaklaşımın ele almadığı hangi özgün açıyı veya derinliği sunabilir?
4. **Devam kararı:** Bu karşılaştırmaya dayanarak, yeni dersin eklenmesi desteklenebilir mi — ve eğer öyleyse, onu neden değerli kılar?

3-5 cümle, akıcı akademik dil."""
        else:
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
4. **Komite önerisi:** Tek ve somut eylem önerisi (birleştir / ön koşul yap / kapsam daralt / farklılaştır).

3-5 cümle, akıcı akademik dil."""

    if is_cross_university:
        return f"""You are an experienced curriculum advisor. A faculty member is planning to propose a new course at their university and is checking whether similar courses already exist at other institutions.

The proposed new course syllabus **{overlap_severity} overlaps** with the following course at another university:

**Compared course:** {course_code} — {course_name} ({university})

**Overlapping section pairs** (proposed course ↔ compared course):
{pair_lines}

**Shared academic terminology:** {kw_str}

---

Analyze this and answer the four questions below. **Do NOT restate numbers, percentages, or section codes** — the user already sees those.

1. **Academic domain:** What sub-discipline do these section names and terminology represent?
2. **Standard coverage:** What does this similarity reveal about how this topic is commonly taught across universities — what topics are considered standard in this area?
3. **Differentiation opportunity:** What unique angle or depth could the proposed course offer that the existing course at {university} does not address?
4. **Proceed decision:** Based on this comparison, is adding the new course justifiable — and if so, what would make it worthwhile?

3-5 sentences in fluent academic prose."""

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
4. **Committee recommendation:** One concrete action (merge / set as prerequisite / narrow scope / differentiate).

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


MAX_SUMMARY_COURSES = 8


def _build_summary_prompt(top_courses: list, overlap_class: str, language: str, is_cross_university: bool) -> str:
    course_lines = []
    all_keywords: set[str] = set()
    for c in top_courses[:MAX_SUMMARY_COURSES]:
        status = "OVERLAP" if c.is_overlap else "similar"
        uni = c.matched_university or "Unknown"
        kws = (c.details.shared_keywords or []) if c.details else []
        all_keywords.update(kws[:6])
        course_lines.append(
            f"  • {c.course_code} — {c.course_name} ({uni}) [{status}]"
        )

    courses_block = "\n".join(course_lines) or "  • (no courses)"
    kw_str = ", ".join(list(all_keywords)[:MAX_KEYWORDS]) or "(none)"

    overlap_count = sum(1 for c in top_courses if c.is_overlap)

    if language == "tr":
        if is_cross_university:
            return f"""Sen deneyimli bir müfredat danışmanısın. Bir öğretim üyesi, kendi üniversitesine yeni bir ders eklemeyi planlıyor ve başka üniversitelerdeki benzer dersleri araştırıyor.

Otomatik analiz şu sonuçları döndürdü ({overlap_count} örtüşme tespit edildi):

{courses_block}

Alanda öne çıkan ortak terminoloji: {kw_str}

---

Bu sonuçların tümünü birlikte değerlendirerek 4-6 cümlelik akıcı, bütünleşik bir analiz yaz. Şu soruları yanıtla:
- Bu eşleşmeler bir araya geldiğinde hangi akademik alanı ve yaygın içeriği temsil ediyor?
- Bu konu, farklı üniversitelerde genellikle nasıl yapılandırılıyor?
- Önerilen yeni dersin doldurabileceği boşluk veya farklılaşma fırsatı var mı?
- Genel değerlendirme: bu ders eklenmeye değer mi, ve öyleyse neyi farklı yapmalı?

Sayıları, yüzdeleri veya ders kodlarını tekrarlama — bunları kullanıcı zaten görüyor."""
        else:
            return f"""Sen deneyimli bir müfredat komitesi danışmanısın. Yeni bir ders teklifi mevcut müfredata karşı değerlendirildi.

Analiz şu eşleşmeleri buldu ({overlap_count} örtüşme tespit edildi):

{courses_block}

Alanda öne çıkan ortak terminoloji: {kw_str}

---

Bu sonuçların tümünü birlikte değerlendirerek 4-6 cümlelik akıcı, bütünleşik bir analiz yaz. Şu soruları yanıtla:
- Bu eşleşmeler hangi ortak akademik alanı temsil ediyor?
- Örtüşmenin niteliği nedir — içerik tekrarı mı, ön koşul ilişkisi mi, yoksa yöntemsel benzerlik mi?
- Sorunun kapsamı nedir — münferit bir çakışma mı, yoksa daha geniş bir müfredat sorunu mu?
- Komite için tek ve net bir eylem önerisi.

Sayıları, yüzdeleri veya ders kodlarını tekrarlama — bunları kullanıcı zaten görüyor."""

    if is_cross_university:
        return f"""You are an experienced curriculum advisor. A faculty member is planning to propose a new course at their university and has used an automated tool to find similar courses at other institutions.

The analysis returned the following matches ({overlap_count} flagged as overlapping):

{courses_block}

Common academic terminology across matches: {kw_str}

---

Write a single cohesive analysis of 4-6 sentences covering all these results together. Address:
- What academic area and common content do these matches collectively represent?
- How is this topic typically structured across universities?
- Is there a gap or differentiation opportunity the proposed course could fill?
- Overall verdict: is adding this course justified, and if so, what should make it distinctive?

Do NOT repeat course codes, numbers, or percentages — the user already sees those."""

    return f"""You are an experienced curriculum committee advisor. A new course proposal has been evaluated against the existing course catalog.

The analysis found the following matches ({overlap_count} flagged as overlapping):

{courses_block}

Common academic terminology across matches: {kw_str}

---

Write a single cohesive analysis of 4-6 sentences covering all these results together. Address:
- What shared academic area do these matches represent?
- What is the nature of the overlaps — content redundancy, prerequisite relationships, or methodological similarity?
- What is the scope of the problem — an isolated duplication or a broader curriculum concern?
- One clear committee recommendation.

Do NOT repeat course codes, numbers, or percentages — the user already sees those."""


async def generate_ai_summary(
    top_courses: list,
    overlap_class: str,
    language: str = "tr",
    is_cross_university: bool = False,
) -> tuple[str, str]:
    """
    Returns (summary_text, source).
    source: "ai" | "ai_cached" | "fallback"
    Never raises.
    """
    from app.core.config import get_settings
    settings = get_settings()

    if not top_courses:
        return "", "fallback"

    if not settings.AI_EXPLANATIONS_ENABLED or not settings.AI_API_KEY:
        overlap_count = sum(1 for c in top_courses if c.is_overlap)
        if language == "tr":
            return f"{len(top_courses)} eşleşen ders bulundu, {overlap_count} tanesi örtüşme olarak işaretlendi.", "fallback"
        return f"{len(top_courses)} matching course(s) found, {overlap_count} flagged as overlap.", "fallback"

    cache_raw = "|".join(
        f"{c.course_code}:{c.average_similarity:.2f}:{c.is_overlap}"
        for c in top_courses[:MAX_SUMMARY_COURSES]
    ) + f"|{overlap_class}|{language}|{is_cross_university}"
    key = hashlib.sha256(cache_raw.encode()).hexdigest()

    if key in _cache:
        cached = _cache[key]
        return cached["text"], "ai_cached"

    prompt = _build_summary_prompt(top_courses, overlap_class, language, is_cross_university)
    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[:MAX_PROMPT_CHARS - 1].rstrip() + "…"

    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            text = await _call_gemini(
                api_key=settings.AI_API_KEY,
                model=settings.AI_MODEL,
                prompt=prompt,
                timeout=float(settings.AI_TIMEOUT_SECONDS),
            )
            _cache[key] = {"text": text}
            return text, "ai"
        except asyncio.TimeoutError as exc:
            logger.warning("Gemini summary timed out")
            last_exc = exc
            break
        except Exception as exc:
            err = str(exc)
            if "429" in err and attempt < 2:
                m = re.search(r"retryDelay.*?(\d+)s", err)
                wait = int(m.group(1)) + 1 if m else (5 * (attempt + 1))
                logger.info("Gemini rate-limited on summary, retrying in %ds…", wait)
                await asyncio.sleep(wait)
                last_exc = exc
            else:
                logger.warning("Gemini summary failed: %s", exc)
                last_exc = exc
                break

    overlap_count = sum(1 for c in top_courses if c.is_overlap)
    if language == "tr":
        return f"{len(top_courses)} eşleşen ders bulundu, {overlap_count} tanesi örtüşme olarak işaretlendi.", "fallback"
    return f"{len(top_courses)} matching course(s) found, {overlap_count} flagged as overlap.", "fallback"
