"""
University course catalog scraper service.

GTÜ and Hacettepe both publish their Bologna catalogs via the same ASP.NET
WebForms OIBS stack, so they share an OIBSBolognaScraper base class. İYTE
has its own WordPress-based CENG catalog and uses a dedicated scraper.
İTÜ and ODTÜ currently serve curated seed data and are queued for live
ingestion.
"""
import logging
import re
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)


class UniversityScraper:
    """Base scraper for Turkish university course catalogs."""

    parser_name: str = "base"
    parser_version: str = "1.0.0"

    def __init__(self, code: str, name: str):
        self.code = code
        self.name = name
        self.timeout = ClientTimeout(total=30)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

    async def fetch_page(self, url: str) -> Optional[str]:
        return await fetch_with_retry(url, headers=self.headers, timeout=self.timeout)

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    async def get_departments(self) -> List[Dict[str, str]]:
        raise NotImplementedError

    async def scrape_department_courses(
        self, department_code: str, limit: Optional[int] = None
    ) -> List[Dict]:
        raise NotImplementedError

    async def bulk_import(
        self, department_codes: List[str] = None, limit_per_dept: int = None
    ) -> List[Dict]:
        logger.info(f"Starting bulk import from {self.name}...")

        if department_codes is None:
            departments = await self.get_departments()
            department_codes = [d["code"] for d in departments]

        all_courses: List[Dict] = []
        dept_failures: List[str] = []
        now_iso = datetime.now(timezone.utc)

        for dept_code in department_codes:
            try:
                courses = await self.scrape_department_courses(dept_code, limit=limit_per_dept)
                if limit_per_dept:
                    courses = courses[:limit_per_dept]
                for course in courses:
                    department = course.get("department", "")
                    course.setdefault("university", self.name)
                    course.setdefault("faculty", self.infer_faculty(department))
                    course.setdefault("parser_name", self.parser_name)
                    course.setdefault("parser_version", self.parser_version)
                    course.setdefault("source_fetched_at", now_iso)
                all_courses.extend(courses)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(
                    f"Error scraping {dept_code} from {self.name}: {e}", exc_info=True
                )
                dept_failures.append(dept_code)
                # Graceful partial failure: keep going with remaining departments.
                continue

        logger.info(
            f"Bulk import from {self.name}: {len(all_courses)} courses, "
            f"{len(dept_failures)} department(s) failed: {dept_failures or 'none'}"
        )
        return all_courses

    def infer_faculty(self, department: str) -> str:
        normalized = (department or "").lower()
        if any(t in normalized for t in ["mat", "fiz", "physics", "istat", "statistics"]):
            return "Faculty of Science"
        if any(t in normalized for t in ["müh", "engineering", "computer", "elektr", "machine"]):
            return "Faculty of Engineering"
        return "Related Faculty"


# ═══════════════════════════════════════════════════════════
# Network helpers with retry/backoff
# ═══════════════════════════════════════════════════════════
async def fetch_with_retry(
    url: str,
    *,
    headers: Dict,
    timeout: ClientTimeout,
    max_attempts: int = 3,
    connector: Optional[aiohttp.BaseConnector] = None,
    encoding: Optional[str] = None,
) -> Optional[str]:
    """GET url with exponential backoff on transient errors."""
    last_err: Optional[str] = None
    for attempt in range(1, max_attempts + 1):
        try:
            async with aiohttp.ClientSession(
                timeout=timeout, headers=headers, connector=connector
            ) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text(encoding=encoding, errors="replace")
                    if resp.status in (429, 500, 502, 503, 504):
                        last_err = f"HTTP {resp.status}"
                    else:
                        logger.warning(f"Non-retryable {resp.status} for {url}")
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_err = str(exc)
        backoff = 0.75 * (2 ** (attempt - 1))
        logger.warning(
            f"fetch {url} attempt {attempt}/{max_attempts} failed ({last_err}); "
            f"retrying in {backoff:.2f}s"
        )
        await asyncio.sleep(backoff)
    logger.error(f"fetch {url} gave up after {max_attempts} attempts: {last_err}")
    return None


# ═══════════════════════════════════════════════════════════
# OIBS Bologna catalog base (used by GTÜ and Hacettepe)
# ═══════════════════════════════════════════════════════════
class OIBSBolognaScraper(UniversityScraper):
    """
    Base for universities running the OIBS Bologna catalog.

    Catalog page exposes course rows in an ASP.NET WebForms grid; clicking a
    course triggers __doPostBack which 302s to progCourseDetails.aspx with the
    real curCourse id. We replay that flow over a single aiohttp session.
    """

    parser_name = "oibs-bologna"
    parser_version = "2.0.0"

    BASE_URL: str = ""          # e.g. https://obs.gtu.edu.tr/oibs/bologna
    HOST_PREFIX: str = ""       # used to prefix relative Location headers
    PROGRAMS: Dict[str, Dict] = {}

    def __init__(self, code: str, name: str):
        super().__init__(code, name)
        self.timeout = ClientTimeout(total=90)

    async def get_departments(self) -> List[Dict[str, str]]:
        return [{"code": code, "name": prog["name"]} for code, prog in self.PROGRAMS.items()]

    async def scrape_department_courses(
        self, dept_code: str, limit: Optional[int] = None
    ) -> List[Dict]:
        prog = self.PROGRAMS.get((dept_code or "").upper())
        if not prog:
            logger.warning(f"{self.name}: unknown department code '{dept_code}'")
            return []

        catalog_url = f"{self.BASE_URL}/progCourses.aspx?lang=tr&curSunit={prog['sunit']}"
        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(
            timeout=self.timeout, headers=self.headers, connector=connector
        ) as session:
            catalog_html = await self._fetch_text(session, catalog_url)
            if not catalog_html:
                return []

            viewstate = self._extract_form_value(catalog_html, "__VIEWSTATE")
            viewstate_gen = self._extract_form_value(catalog_html, "__VIEWSTATEGENERATOR")
            if not viewstate:
                logger.error(f"{self.name}: __VIEWSTATE missing on catalog page")
                return []

            rows = self._parse_catalog_rows(catalog_html)
            logger.info(f"{self.name} {dept_code}: catalog lists {len(rows)} courses")

            # Optional filter: drop language electives from Hacettepe catalogs.
            rows = [r for r in rows if self._keep_row(r)]

            if limit:
                rows = rows[:limit]
                logger.info(
                    f"{self.name} {dept_code}: limiting detail fetch to {len(rows)}"
                )

            scraped: List[Dict] = []
            failed = 0
            for idx, row in enumerate(rows, 1):
                try:
                    detail_url = await self._resolve_detail_url(
                        session, catalog_url, viewstate, viewstate_gen, row["event_target"]
                    )
                    if not detail_url:
                        failed += 1
                        continue
                    detail_html = await self._fetch_text(session, detail_url)
                    if not detail_html:
                        failed += 1
                        continue
                    course = self._build_course(row, detail_html, prog, detail_url)
                    if course:
                        scraped.append(course)
                    await asyncio.sleep(0.25)
                except Exception as exc:
                    failed += 1
                    logger.warning(
                        f"{self.name}: failed to scrape course #{idx} "
                        f"({row.get('code')}): {exc}"
                    )
                    continue

            logger.info(
                f"{self.name} {dept_code}: scraped {len(scraped)} courses, "
                f"{failed} failed"
            )
            return scraped

    # ---- overridable policy hooks ----
    def _keep_row(self, row: Dict) -> bool:  # pragma: no cover - override hook
        return True

    # ---- internal helpers ----
    async def _fetch_text(
        self, session: aiohttp.ClientSession, url: str, max_attempts: int = 3
    ) -> Optional[str]:
        last_err: Optional[str] = None
        for attempt in range(1, max_attempts + 1):
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    if resp.status in (429, 500, 502, 503, 504):
                        last_err = f"HTTP {resp.status}"
                    else:
                        logger.warning(f"{self.name}: GET {url} -> HTTP {resp.status}")
                        return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_err = str(exc)
            backoff = 0.6 * (2 ** (attempt - 1))
            logger.warning(
                f"{self.name}: GET {url} attempt {attempt}/{max_attempts} "
                f"failed ({last_err}); retrying in {backoff:.2f}s"
            )
            await asyncio.sleep(backoff)
        logger.error(f"{self.name}: giving up on {url} after {max_attempts} attempts")
        return None

    async def _resolve_detail_url(
        self,
        session: aiohttp.ClientSession,
        catalog_url: str,
        viewstate: str,
        viewstate_gen: str,
        event_target: str,
    ) -> Optional[str]:
        data = {
            "__EVENTTARGET": event_target,
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstate_gen,
        }
        try:
            async with session.post(catalog_url, data=data, allow_redirects=False) as resp:
                location = resp.headers.get("Location")
                if resp.status in (301, 302, 303) and location:
                    if location.startswith("/"):
                        return f"{self.HOST_PREFIX}{location}"
                    if location.startswith("http"):
                        return location
                    return f"{self.BASE_URL}/{location.lstrip('/')}"
                logger.debug(
                    f"{self.name}: postback for {event_target} returned "
                    f"{resp.status}, no redirect"
                )
                return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.warning(f"{self.name}: postback error for {event_target}: {exc}")
            return None

    @staticmethod
    def _extract_form_value(html: str, name: str) -> Optional[str]:
        match = re.search(
            rf'<input[^>]*name="{re.escape(name)}"[^>]*value="([^"]*)"',
            html,
        )
        return match.group(1) if match else None

    def _parse_catalog_rows(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find(id="grdBolognaDersler")
        if not table:
            return []

        rows: List[Dict] = []
        for tr in table.find_all("tr"):
            code_link = tr.find("a", id=re.compile(r"btnDersKod_\d+"))
            if not code_link:
                continue
            code = self.clean_text(code_link.get_text())
            if not code:
                continue

            name_span = tr.find("span", id=re.compile(r"lblDersAd_\d+"))
            akts_span = tr.find("span", id=re.compile(r"lblAKTS_\d+"))
            hours_span = tr.find("span", id=re.compile(r"Label3_\d+"))
            type_span = tr.find("span", id=re.compile(r"Label5_\d+"))

            href = code_link.get("href") or ""
            target_match = re.search(r"__doPostBack\('([^']+)'", href)
            if not target_match:
                continue

            try:
                ects = int((akts_span.get_text(strip=True) if akts_span else "").strip() or 0)
            except ValueError:
                ects = 0

            rows.append({
                "code": code,
                "name": self.clean_text(name_span.get_text()) if name_span else "",
                "ects": ects or None,
                "hours": self.clean_text(hours_span.get_text()) if hours_span else "",
                "type": self.clean_text(type_span.get_text()) if type_span else "",
                "event_target": target_match.group(1),
            })
        return rows

    def _build_course(
        self, row: Dict, detail_html: str, prog: Dict, detail_url: str
    ) -> Optional[Dict]:
        soup = BeautifulSoup(detail_html, "html.parser")

        amac = self._text_of(soup, "dlDers_AMACLabel_0")
        icerik = self._text_of(soup, "dlDers_ICERIKLabel_0")
        kaynaklar = self._text_of(soup, "dlDers_KAYNAKLARLabel_0")
        koordinator = self._text_of(soup, "dlDers_DERS_KOORDINATORLabel_0")
        veren = self._text_of(soup, "dlDers_DERS_VERENLabel_0")

        outcomes = self._extract_learning_outcomes(soup)
        topics = self._extract_weekly_topics(soup)
        assessment = self._extract_assessment(soup)

        if not any([amac, icerik, outcomes, topics]):
            logger.debug(f"{self.name}: skipping {row['code']} — no detail content")
            return None

        description = self._compose_description(
            row=row,
            prog=prog,
            amac=amac,
            icerik=icerik,
            outcomes=outcomes,
            topics=topics,
            assessment=assessment,
            kaynaklar=kaynaklar,
            koordinator=koordinator,
            veren=veren,
        )

        return {
            "code": row["code"],
            "name": row["name"] or row["code"],
            "department": prog["department"],
            "faculty": prog["faculty"],
            "credits": row.get("ects"),
            "description": description,
            "source_url": detail_url,
        }

    @staticmethod
    def _text_of(soup: BeautifulSoup, element_id: str) -> str:
        el = soup.find(id=element_id)
        if not el:
            return ""
        return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()

    def _extract_learning_outcomes(self, soup: BeautifulSoup) -> List[str]:
        outcomes: List[str] = []
        for table_id in ("grdOgrenmeCiktilari", "grdOgrenmeCiktilari1"):
            table = soup.find(id=table_id)
            if not table:
                continue
            for tr in table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                text = self.clean_text(tds[1].get_text(" ", strip=True))
                text = text.strip(' "“”')
                if text:
                    outcomes.append(text)
        return outcomes

    def _extract_weekly_topics(self, soup: BeautifulSoup) -> List[str]:
        topics: List[str] = []
        table = soup.find(id="grdDersKonu")
        if not table:
            return topics
        for tr in table.find_all("tr"):
            label = tr.find("span", id=re.compile(r"grdDersKonu_Label1_\d+"))
            if not label:
                continue
            text = self.clean_text(label.get_text(" ", strip=True))
            if text:
                topics.append(text)
        return topics

    def _extract_assessment(self, soup: BeautifulSoup) -> List[str]:
        items: List[str] = []
        for tip in soup.find_all("span", id=re.compile(r"grd_degerlendirme_lblCalismaTip_\d+")):
            idx = tip.get("id", "").rsplit("_", 1)[-1]
            sayi = soup.find(id=f"grd_degerlendirme_lblDS_Sayi_{idx}")
            katki = soup.find(id=f"grd_degerlendirme_lblDS_Katki_{idx}")
            label = self.clean_text(tip.get_text())
            count = self.clean_text(sayi.get_text()) if sayi else ""
            weight = self.clean_text(katki.get_text()) if katki else ""
            if label and weight:
                items.append(
                    f"{label}: %{weight} (sayı: {count})" if count else f"{label}: %{weight}"
                )
        return items

    def _compose_description(
        self,
        row: Dict,
        prog: Dict,
        amac: str,
        icerik: str,
        outcomes: List[str],
        topics: List[str],
        assessment: List[str],
        kaynaklar: str,
        koordinator: str,
        veren: str,
    ) -> str:
        parts: List[str] = ["Ders Tanımı"]
        header_bits = [row["code"], row.get("name", "")]
        if prog.get("department"):
            header_bits.append(prog["department"])
        if row.get("hours"):
            header_bits.append(f"Ders saati: {row['hours']}")
        if row.get("type"):
            header_bits.append(row["type"])
        if row.get("ects"):
            header_bits.append(f"AKTS: {row['ects']}")
        parts.append(" | ".join(b for b in header_bits if b))

        if amac:
            parts += ["\nAmaç", amac]
        if icerik:
            parts += ["\nDers İçeriği", icerik]
        if outcomes:
            parts.append("\nÖğrenme Çıktıları")
            parts.extend(f"{i}. {o}" for i, o in enumerate(outcomes, 1))
        if topics:
            parts.append("\nHaftalık Plan")
            parts.extend(f"Hafta {i}: {t}" for i, t in enumerate(topics, 1))
        if assessment:
            parts.append("\nDeğerlendirme")
            parts.extend(assessment)
        if kaynaklar:
            parts += ["\nKaynaklar", kaynaklar]
        instructors = [v for v in (veren, koordinator) if v]
        if instructors:
            parts += ["\nÖğretim Üyesi", " / ".join(dict.fromkeys(instructors))]

        return "\n".join(parts).strip()


# ═══════════════════════════════════════════════════════════
# GTÜ
# ═══════════════════════════════════════════════════════════
class GTUScraper(OIBSBolognaScraper):
    parser_name = "gtu-oibs-bologna"
    parser_version = "2.0.0"

    BASE_URL = "https://obs.gtu.edu.tr/oibs/bologna"
    HOST_PREFIX = "https://obs.gtu.edu.tr"
    PROGRAMS = {
        "BLM": {
            "sunit": 23058,
            "name": "Bilgisayar Mühendisliği",
            "department": "Bilgisayar Mühendisliği",
            "faculty": "Mühendislik Fakültesi",
        },
    }

    def __init__(self):
        super().__init__("gtu", "Gebze Teknik Üniversitesi")


# ═══════════════════════════════════════════════════════════
# Hacettepe (live via OIBS Bologna)
# ═══════════════════════════════════════════════════════════
# Language-elective course codes are excluded per project requirement.
HACETTEPE_LANGUAGE_PREFIXES = (
    "GER", "FRA", "ITA", "ESP", "RUS", "CHN", "JPN", "ARA", "YDA", "YDF",
    "YDI", "YDJ", "YDR", "YDS", "YDC",
)


class HacettepeScraper(OIBSBolognaScraper):
    parser_name = "hacettepe-oibs-bologna"
    parser_version = "2.0.0"

    BASE_URL = "https://bilsis.hacettepe.edu.tr/oibs/bologna"
    HOST_PREFIX = "https://bilsis.hacettepe.edu.tr"
    PROGRAMS = {
        # curSunit 356 is the Bilgisayar Mühendisliği program noted in the plan.
        "BBM": {
            "sunit": 356,
            "name": "Bilgisayar Mühendisliği",
            "department": "Bilgisayar Mühendisliği",
            "faculty": "Mühendislik Fakültesi",
        },
    }

    def __init__(self):
        super().__init__("hacettepe", "Hacettepe Üniversitesi")

    def _keep_row(self, row: Dict) -> bool:
        code_upper = (row.get("code") or "").upper()
        for prefix in HACETTEPE_LANGUAGE_PREFIXES:
            if code_upper.startswith(prefix):
                return False
        return True


# ═══════════════════════════════════════════════════════════
# İTÜ - seeded (live scraper deferred)
# ═══════════════════════════════════════════════════════════
class ITUScraper(UniversityScraper):
    parser_name = "itu-seed"
    parser_version = "1.0.0"
    BASE_URL = "https://www.sis.itu.edu.tr"

    def __init__(self):
        super().__init__("itu", "İstanbul Teknik Üniversitesi")

    async def get_departments(self) -> List[Dict[str, str]]:
        return [
            {"code": "BLG", "name": "Bilgisayar Mühendisliği"},
            {"code": "YZV", "name": "Yapay Zeka ve Veri Mühendisliği"},
            {"code": "EHB", "name": "Elektronik ve Haberleşme Mühendisliği"},
            {"code": "KON", "name": "Kontrol ve Otomasyon Mühendisliği"},
            {"code": "MAT", "name": "Matematik Mühendisliği"},
        ]

    async def scrape_department_courses(
        self, dept_code: str, limit: Optional[int] = None
    ) -> List[Dict]:
        return _ITU_SEED.get(dept_code, [])


# ═══════════════════════════════════════════════════════════
# METU - live scraper for catalog.metu.edu.tr
# ═══════════════════════════════════════════════════════════
class METUScraper(UniversityScraper):
    """
    Live scraper for METU (ODTÜ) academic catalog.

    Program listing: https://catalog.metu.edu.tr/program.php?fac_prog=<id>
      - Table rows with <td class="short_course"> hold a link to the course
        detail page.  Columns: code, name, METU credit, hours, lab, ECTS.
    Course detail: https://catalog.metu.edu.tr/course.php?prog=<id>&course_code=<num>
      - <table class="course"> for metadata (ECTS, coordinator, semester, prereqs)
      - <h3>Course Content</h3> followed by a plain-text sibling node
      - Three <iframe> elements load objectives / learning outcomes from
        odtusyllabus.metu.edu.tr (JavaScript-served, not scraped here)
    """

    parser_name = "metu-catalog"
    parser_version = "2.0.0"
    BASE_URL = "https://catalog.metu.edu.tr"
    CONCURRENCY = 4

    PROGRAMS: Dict[str, Dict] = {
        "CENG": {
            "fac_prog": 571,
            "name": "Computer Engineering",
            "department": "Computer Engineering",
            "faculty": "Faculty of Engineering",
        },
        "EEE": {
            "fac_prog": 567,
            "name": "Electrical and Electronics Engineering",
            "department": "Electrical and Electronics Engineering",
            "faculty": "Faculty of Engineering",
        },
        "IE": {
            "fac_prog": 568,
            "name": "Industrial Engineering",
            "department": "Industrial Engineering",
            "faculty": "Faculty of Engineering",
        },
        "ME": {
            "fac_prog": 569,
            "name": "Mechanical Engineering",
            "department": "Mechanical Engineering",
            "faculty": "Faculty of Engineering",
        },
    }

    def __init__(self):
        super().__init__("metu", "Orta Doğu Teknik Üniversitesi")
        self.timeout = ClientTimeout(total=60)

    async def fetch_page(self, url: str) -> Optional[str]:
        return await fetch_with_retry(
            url, headers=self.headers, timeout=self.timeout, encoding="iso-8859-9"
        )

    async def get_departments(self) -> List[Dict[str, str]]:
        return [{"code": code, "name": prog["name"]} for code, prog in self.PROGRAMS.items()]

    async def scrape_department_courses(
        self, dept_code: str, limit: Optional[int] = None
    ) -> List[Dict]:
        prog = self.PROGRAMS.get((dept_code or "").upper())
        if not prog:
            logger.warning(f"METU: unknown department '{dept_code}'")
            return []

        prog_url = f"{self.BASE_URL}/program.php?fac_prog={prog['fac_prog']}"
        html = await self.fetch_page(prog_url)
        if not html:
            logger.error(f"METU: failed to fetch program page for {dept_code}")
            return []

        entries = self._parse_program_page(html)
        logger.info(f"METU {dept_code}: found {len(entries)} courses in curriculum")

        if limit:
            entries = entries[:limit]

        semaphore = asyncio.Semaphore(self.CONCURRENCY)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(
            timeout=self.timeout, headers=self.headers, connector=connector
        ) as session:
            tasks = [
                self._scrape_course(session, semaphore, entry, prog)
                for entry in entries
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        courses: List[Dict] = []
        failed = 0
        for r in results:
            if isinstance(r, dict):
                courses.append(r)
            else:
                failed += 1
                if isinstance(r, Exception):
                    logger.debug(f"METU: task raised {r}")

        logger.info(f"METU {dept_code}: scraped {len(courses)} courses, {failed} failed/skipped")
        return courses

    # ---- program page parsing ----

    def _parse_program_page(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        entries: List[Dict] = []
        seen: set = set()

        for td in soup.find_all("td", class_="short_course"):
            a = td.find("a")
            if not a:
                continue
            href = a.get("href", "")
            code = self.clean_text(a.get_text())
            if not code or not href:
                continue

            m = re.search(r"course\.php\?prog=(\d+)&course_code=(\d+)", href)
            if not m:
                continue
            prog_id, course_num = m.group(1), m.group(2)
            if course_num in seen:
                continue
            seen.add(course_num)

            name_td = td.find_next_sibling("td", class_="course")
            name = self.clean_text(name_td.get_text()) if name_td else ""

            ects = None
            tr = td.parent
            if tr:
                tds = tr.find_all("td")
                if tds:
                    try:
                        ects = float(self.clean_text(tds[-1].get_text()))
                    except ValueError:
                        pass

            entries.append({
                "code": code,
                "name": name,
                "ects": ects,
                "url": f"{self.BASE_URL}/course.php?prog={prog_id}&course_code={course_num}",
            })

        return entries

    # ---- per-course detail scraping ----

    async def _scrape_course(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        entry: Dict,
        prog: Dict,
    ) -> Optional[Dict]:
        async with semaphore:
            html = await self._get_with_retry(session, entry["url"])
            await asyncio.sleep(0.2)
        if not html:
            return None
        try:
            return self._parse_course_detail(entry, prog, html)
        except Exception as exc:
            logger.warning(f"METU: parse error for {entry['code']}: {exc}")
            return None

    async def _get_with_retry(
        self, session: aiohttp.ClientSession, url: str, max_attempts: int = 3
    ) -> Optional[str]:
        last_err: Optional[str] = None
        for attempt in range(1, max_attempts + 1):
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text(errors="replace")
                    if resp.status in (429, 500, 502, 503, 504):
                        last_err = f"HTTP {resp.status}"
                    else:
                        logger.warning(f"METU: GET {url} -> HTTP {resp.status}")
                        return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_err = str(exc)
            backoff = 0.6 * (2 ** (attempt - 1))
            await asyncio.sleep(backoff)
        logger.warning(f"METU: giving up on {url}: {last_err}")
        return None

    def _parse_course_detail(self, entry: Dict, prog: Dict, html: str) -> Optional[Dict]:
        soup = BeautifulSoup(html, "html.parser")

        h2 = soup.find("h2")
        title = self.clean_text(h2.get_text()) if h2 else ""

        ects = entry.get("ects")
        coordinator = ""
        semester = ""
        prereq_text = ""

        course_table = soup.find("table", class_="course")
        if course_table:
            for tr in course_table.find_all("tr"):
                tds = tr.find_all("td")
                if not tds:
                    continue
                b_tag = tds[0].find("b")
                label = self.clean_text(tds[0].get_text()).lower()

                if "ects credit" in label and len(tds) >= 2:
                    try:
                        ects = float(self.clean_text(tds[1].get_text()))
                    except ValueError:
                        pass
                elif "coordinator" in label and len(tds) >= 2:
                    coordinator = self.clean_text(tds[1].get_text())
                elif "offered semester" in label and len(tds) >= 2:
                    semester = self.clean_text(tds[1].get_text())
                elif b_tag and "prerequisite" in b_tag.get_text().lower() and len(tds) >= 2:
                    links = tds[1].find_all("a")
                    if links:
                        prereq_text = ", ".join(a.get_text(strip=True) for a in links)

        # Course content is a plain-text NavigableString immediately after <h3>Course Content</h3>
        content = ""
        for h3 in soup.find_all("h3"):
            if "course content" in h3.get_text().lower():
                for sibling in h3.next_siblings:
                    tag_name = getattr(sibling, "name", None)
                    if tag_name in ("iframe", "h2", "h3"):
                        break
                    if tag_name is None:
                        text = self.clean_text(str(sibling))
                        if text:
                            content = text
                            break
                    else:
                        text = self.clean_text(sibling.get_text(" ", strip=True))
                        if text:
                            content = text
                            break
                break

        if not title and not content:
            logger.debug(f"METU: no content for {entry['code']}, skipping")
            return None

        description = self._compose_description(
            title=title or entry["code"],
            content=content,
            ects=ects,
            semester=semester,
            prereq=prereq_text,
            coordinator=coordinator,
        )

        return {
            "code": entry["code"],
            "name": entry.get("name") or title,
            "department": prog["department"],
            "faculty": prog["faculty"],
            "credits": ects,
            "description": description,
            "source_url": entry["url"],
        }

    def _compose_description(
        self,
        title: str,
        content: str,
        ects,
        semester: str,
        prereq: str,
        coordinator: str,
    ) -> str:
        parts = [f"Course: {title}"]

        meta = []
        if ects:
            meta.append(f"ECTS: {ects}")
        if semester:
            meta.append(f"Offered: {semester}")
        if meta:
            parts.append(" | ".join(meta))

        if content:
            parts += ["\nCourse Content", content]
        if prereq:
            parts += ["\nPrerequisites", prereq]
        if coordinator:
            parts += ["\nCourse Coordinator", coordinator]

        return "\n".join(parts).strip()


# ═══════════════════════════════════════════════════════════
# İYTE - live scraper for the CENG department WordPress catalog
# ═══════════════════════════════════════════════════════════
# Section labels used to carve the free-text body of each course page.
# Labels are matched case-insensitively and must appear inside a <strong> tag.
IYTE_SECTION_LABELS = [
    "Course Objectives",
    "Course Description",
    "Course Content",
    "Course Contents",
    "Recommended or Required Reading",
    "Recommended Reading",
    "Required Reading",
    "Textbook",
    "Textbooks",
    "Learning Outcomes",
    "Grading",
    "Grading:",
    "Submissions",
    "Submissions:",
    "Prerequisites",
]


class IYTEScraper(UniversityScraper):
    """
    Live scraper for the İYTE Computer Engineering department catalog.

    Listing: https://ceng.iyte.edu.tr/education/undergraduate-program/courses/
    Each course page lives under /courses/ceng-NNN/ with a WordPress layout:
      - <h1 class="course-code">CENG 112</h1>
      - <h2 class="course-name">Data Structures</h2>
      - <div class="course-prerequisites">...</div>
      - <div class="wpb_text_column">...free-form description with <strong>
         labels and one weekly-topics <table>...</div>
    """

    parser_name = "iyte-ceng-wp"
    parser_version = "2.0.0"

    BASE_URL = "https://ceng.iyte.edu.tr"
    LIST_URL = f"{BASE_URL}/education/undergraduate-program/courses/"
    CONCURRENCY = 5

    def __init__(self):
        super().__init__("iyte", "İzmir Yüksek Teknoloji Enstitüsü")
        self.timeout = ClientTimeout(total=60)

    async def get_departments(self) -> List[Dict[str, str]]:
        return [{"code": "CENG", "name": "Computer Engineering"}]

    async def scrape_department_courses(
        self, dept_code: str, limit: Optional[int] = None
    ) -> List[Dict]:
        if (dept_code or "").upper() != "CENG":
            logger.warning(f"IYTE: unknown department '{dept_code}'")
            return []

        links = await self._fetch_course_links()
        if not links:
            logger.error("IYTE: listing page returned no course links")
            return []
        if limit:
            links = links[:limit]

        logger.info(f"IYTE CENG: fetching {len(links)} detail pages")

        semaphore = asyncio.Semaphore(self.CONCURRENCY)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(
            timeout=self.timeout, headers=self.headers, connector=connector
        ) as session:
            tasks = [
                self._scrape_one(session, semaphore, code, name, url)
                for code, name, url in links
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        courses: List[Dict] = []
        failed = 0
        for r in results:
            if isinstance(r, dict):
                courses.append(r)
            else:
                failed += 1
                if isinstance(r, Exception):
                    logger.debug(f"IYTE: task raised {r}")

        logger.info(f"IYTE CENG: scraped {len(courses)} / failed {failed}")
        return courses

    async def _fetch_course_links(self) -> List[tuple]:
        html = await fetch_with_retry(
            self.LIST_URL, headers=self.headers, timeout=self.timeout
        )
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        # Links appear twice per course (code link + name link). Merge by slug.
        by_slug: Dict[str, Dict] = {}
        for a in soup.find_all("a", href=True):
            m = re.search(r"/courses/(ceng-\d+)/?$", a["href"])
            if not m:
                continue
            slug = m.group(1)
            text = self.clean_text(a.get_text())
            entry = by_slug.setdefault(slug, {"url": a["href"], "parts": []})
            if text:
                entry["parts"].append(text)

        links: List[tuple] = []
        for slug, entry in by_slug.items():
            parts = entry["parts"]
            # First text is usually the code ("CENG 112"); second is the name.
            code_raw = parts[0] if parts else slug
            name = parts[1] if len(parts) > 1 else ""
            code = re.sub(r"\s+", "", code_raw).upper()
            if not re.match(r"^CENG\d+", code):
                code = slug.replace("-", "").upper()
            links.append((code, name, entry["url"]))

        # Stable order so retries hit pages in the same sequence.
        links.sort(key=lambda t: t[0])
        logger.info(f"IYTE: discovered {len(links)} course links")
        return links

    async def _scrape_one(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        code: str,
        name: str,
        url: str,
    ) -> Optional[Dict]:
        async with semaphore:
            html = await self._get_with_retry(session, url)
            await asyncio.sleep(0.15)  # light pacing
        if not html:
            return None
        try:
            return self._parse_detail(code, name, url, html)
        except Exception as exc:
            logger.warning(f"IYTE: parse error for {code} ({url}): {exc}")
            return None

    async def _get_with_retry(
        self, session: aiohttp.ClientSession, url: str, max_attempts: int = 3
    ) -> Optional[str]:
        last_err: Optional[str] = None
        for attempt in range(1, max_attempts + 1):
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    if resp.status in (429, 500, 502, 503, 504):
                        last_err = f"HTTP {resp.status}"
                    else:
                        logger.warning(f"IYTE: GET {url} -> HTTP {resp.status}")
                        return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_err = str(exc)
            backoff = 0.6 * (2 ** (attempt - 1))
            await asyncio.sleep(backoff)
        logger.warning(f"IYTE: giving up on {url}: {last_err}")
        return None

    # ---- detail page parsing ----
    def _parse_detail(
        self, code: str, name: str, url: str, html: str
    ) -> Optional[Dict]:
        soup = BeautifulSoup(html, "html.parser")

        if not name:
            h2 = soup.find("h2", class_="course-name")
            if h2:
                name = self.clean_text(h2.get_text())

        prereq_div = soup.find("div", class_="course-prerequisites")
        prereq = self.clean_text(prereq_div.get_text(" ", strip=True)) if prereq_div else ""

        text_col = soup.find("div", class_="wpb_text_column")
        if not text_col:
            logger.debug(f"IYTE: no content body for {code}")
            return None

        sections = self._segment_body(text_col)
        weekly = self._extract_weekly_topics(text_col)

        # Require at least a catalog description or learning outcomes to count
        # the page as having real content (skip empty elective placeholders).
        has_content = any(sections.get(k) for k in (
            "__intro__", "course description", "course content",
            "course objectives", "learning outcomes",
        )) or bool(weekly)
        if not has_content:
            logger.debug(f"IYTE: skipping {code} — no usable content")
            return None

        description = self._compose_description(
            code=code, name=name, prereq=prereq, sections=sections, weekly=weekly
        )
        if len(description) < 80:
            return None

        return {
            "code": code,
            "name": name or code,
            "department": "Computer Engineering",
            "faculty": "Faculty of Engineering",
            "credits": None,
            "description": description,
            "source_url": url,
        }

    def _segment_body(self, text_col) -> Dict[str, str]:
        """
        Walk top-level <p>/<ul>/<ol> elements. A <p> whose first <strong>
        matches a known label starts a new section; subsequent elements
        accumulate into that section until the next label. Text before the
        first label is stored under '__intro__'.
        """
        label_map = {lbl.rstrip(":").lower(): lbl.rstrip(":") for lbl in IYTE_SECTION_LABELS}
        sections: Dict[str, List[str]] = {"__intro__": []}
        current = "__intro__"

        for el in text_col.children:
            # Skip NavigableStrings and scripts/styles
            if getattr(el, "name", None) is None:
                continue
            if el.name == "table":
                # Weekly topics table handled separately; skip here.
                continue
            text = el.get_text(" ", strip=True)
            if not text:
                continue

            strong = el.find("strong") if el.name in ("p", "div") else None
            if strong:
                strong_text = self.clean_text(strong.get_text()).rstrip(":")
                key = strong_text.lower()
                if key in label_map:
                    current = key
                    sections.setdefault(current, [])
                    # Capture any trailing text after the <strong> in the same <p>.
                    remainder = self.clean_text(
                        text.replace(self.clean_text(strong.get_text()), "", 1)
                    ).lstrip(":").strip()
                    if remainder:
                        sections[current].append(remainder)
                    continue
            sections.setdefault(current, []).append(self.clean_text(text))

        return {k: "\n".join(v).strip() for k, v in sections.items() if v}

    def _extract_weekly_topics(self, text_col) -> List[str]:
        for table in text_col.find_all("table"):
            headers = [self.clean_text(th.get_text()) for th in table.find_all("th")]
            header_text = " ".join(headers).lower()
            # IYTE uses a Week | Topics table; avoid the Program Outcomes matrix.
            looks_weekly = ("week" in header_text and "topic" in header_text) or (
                not headers
                and any("week" in self.clean_text(td.get_text()).lower()
                        for td in table.find_all("td")[:4])
            )
            if not looks_weekly:
                # Heuristic fallback: first-column numeric week indices.
                rows = table.find_all("tr")
                numeric_first_col = sum(
                    1 for tr in rows
                    if tr.find("td") and re.match(r"^\d{1,2}$", self.clean_text(tr.find("td").get_text()))
                )
                if numeric_first_col < 3:
                    continue

            topics: List[str] = []
            for tr in table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                week_label = self.clean_text(tds[0].get_text())
                topic_text = self.clean_text(" ".join(td.get_text(" ", strip=True) for td in tds[1:]))
                if not topic_text:
                    continue
                if not re.match(r"^\d{1,2}$", week_label):
                    continue
                topics.append(topic_text)
            if topics:
                return topics
        return []

    def _compose_description(
        self,
        *,
        code: str,
        name: str,
        prereq: str,
        sections: Dict[str, str],
        weekly: List[str],
    ) -> str:
        parts: List[str] = [f"Course: {code} — {name}"]
        if prereq:
            parts.append(prereq)

        intro = sections.get("__intro__")
        if intro:
            parts += ["\nCourse Description", intro]

        # Render the remaining labeled sections in a predictable order so
        # downstream heading-based splitting stays consistent across courses.
        for label_key in [
            "course objectives", "learning outcomes", "course content",
            "course contents", "recommended or required reading",
            "recommended reading", "required reading", "textbook", "textbooks",
            "grading", "submissions",
        ]:
            value = sections.get(label_key)
            if not value:
                continue
            pretty = next(
                (lbl for lbl in IYTE_SECTION_LABELS
                 if lbl.rstrip(":").lower() == label_key),
                label_key.title(),
            )
            parts += [f"\n{pretty}", value]

        if weekly:
            parts.append("\nWeekly Topics")
            parts.extend(f"Week {i}: {t}" for i, t in enumerate(weekly, 1))

        return "\n".join(parts).strip()


# ═══════════════════════════════════════════════════════════
# Seed catalogs (inlined; not persisted to DB by default)
# ═══════════════════════════════════════════════════════════
_ITU_SEED: Dict[str, List[Dict]] = {
    "BLG": [
        {
            "code": "BLG101E",
            "name": "Introduction to Information Systems",
            "department": "Bilgisayar Mühendisliği",
            "credits": 4,
            "description": (
                "Course Description\n"
                "Fundamentals of information systems and computer science. Students learn "
                "basic concepts of computing, programming, and digital systems.\n\n"
                "Learning Outcomes\n"
                "1. Understand fundamental concepts of information systems\n"
                "2. Write basic programs using Python\n"
                "3. Understand binary number systems and logic gates\n\n"
                "Course Content\n"
                "Introduction to computing, number systems, Boolean algebra, Python basics, "
                "control flow, functions, lists and strings, file operations, algorithms."
            ),
        },
        {
            "code": "BLG202E",
            "name": "Data Structures",
            "department": "Bilgisayar Mühendisliği",
            "credits": 4,
            "description": (
                "Course Description\n"
                "Fundamental data structures and algorithm analysis.\n\n"
                "Course Content\n"
                "Arrays, linked lists, stacks, queues, recursion, trees, BST, AVL, heaps, "
                "priority queues, hash tables, graphs, sorting algorithms, complexity analysis."
            ),
        },
    ],
    "YZV": [
        {
            "code": "YZV301E",
            "name": "Deep Learning",
            "department": "Yapay Zeka ve Veri Mühendisliği",
            "credits": 4,
            "description": (
                "Course Description\n"
                "Theory and practice of deep learning.\n\n"
                "Course Content\n"
                "Feedforward networks, backprop, optimization, regularization, CNNs, RNNs, "
                "attention and transformers, GANs, VAEs, transfer learning."
            ),
        },
    ],
}


# ═══════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════
gtu_scraper = GTUScraper()
itu_scraper = ITUScraper()
metu_scraper = METUScraper()
hacettepe_scraper = HacettepeScraper()
iyte_scraper = IYTEScraper()

UNIVERSITY_SCRAPERS = {
    "gtu": gtu_scraper,
    "itu": itu_scraper,
    "metu": metu_scraper,
    "hacettepe": hacettepe_scraper,
    "iyte": iyte_scraper,
}
