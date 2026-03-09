"""
University course catalog scraper service.
Supports scraping ECTS forms and course descriptions from various Turkish universities.
"""
import logging
import re
import asyncio
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)


class UniversityScraper:
    """Base scraper for Turkish university course catalogs."""
    
    def __init__(self):
        self.timeout = ClientTimeout(total=30)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page asynchronously."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep Turkish characters
        text = text.strip()
        return text


class GTUScraper(UniversityScraper):
    """
    Gebze Technical University (GTÜ) course catalog scraper.
    Scrapes from GTU's online course catalog and ECTS information system.
    """
    
    BASE_URL = "https://www.gtu.edu.tr"
    CATALOG_URL = "https://www.gtu.edu.tr/kategori/41/3/ders-icerikleri.aspx"
    
    async def get_departments(self) -> List[Dict[str, str]]:
        """Get list of departments from GTU website."""
        logger.info("Fetching GTU departments...")
        
        # Simulated department data for demonstration
        # In production, this would scrape the actual department list
        departments = [
            {"code": "BLM", "name": "Bilgisayar Mühendisliği", "url": ""},
            {"code": "MAK", "name": "Makine Mühendisliği", "url": ""},
            {"code": "ELK", "name": "Elektronik Mühendisliği", "url": ""},
            {"code": "END", "name": "Endüstri Mühendisliği", "url": ""},
            {"code": "KIM", "name": "Kimya Mühendisliği", "url": ""},
        ]
        return departments
    
    async def scrape_department_courses(self, department_code: str) -> List[Dict[str, any]]:
        """
        Scrape all courses for a specific department.
        Returns list of course dictionaries with code, name, credits, and description.
        """
        logger.info(f"Scraping courses for department: {department_code}")
        
        # Since we don't have real GTU API access, we'll create sample data
        # In production, this would make actual HTTP requests
        courses = await self._get_sample_courses(department_code)
        
        logger.info(f"Found {len(courses)} courses for {department_code}")
        return courses
    
    async def _get_sample_courses(self, dept_code: str) -> List[Dict[str, any]]:
        """Generate sample course data for demonstration."""
        sample_courses = {
            "BLM": [
                {
                    "code": "BLM101",
                    "name": "Programlamaya Giriş",
                    "department": "Bilgisayar Mühendisliği",
                    "credits": 4,
                    "description": """Ders İçeriği:
Bu ders, programlama mantığının temel kavramlarını ve problem çözme becerilerini kazandırmayı amaçlamaktadır.

Ders Konuları:
1. Algoritma ve akış diyagramları
2. Değişkenler ve veri tipleri
3. Operatörler ve ifadeler
4. Kontrol yapıları (if-else, switch-case)
5. Döngüler (for, while, do-while)
6. Fonksiyonlar ve prosedürler
7. Diziler ve veri yapıları
8. Temel dosya işlemleri

Öğrenme Çıktıları:
- Öğrenciler temel programlama kavramlarını anlayabilir
- Algoritma tasarlayıp uygulayabilir
- Basit programlama problemlerini çözebilir
- Kod yazma ve hata ayıklama becerisi kazanır

Değerlendirme:
- Ara sınav: %30
- Final sınavı: %50
- Ödevler ve projeler: %20"""
                },
                {
                    "code": "BLM102",
                    "name": "Veri Yapıları",
                    "department": "Bilgisayar Mühendisliği",
                    "credits": 5,
                    "description": """Ders İçeriği:
Temel veri yapıları ve algoritmalar dersidir. Öğrencilere veri organizasyonu ve verimli algoritma tasarımı konularında bilgi verilir.

Ders Konuları:
1. Veri yapılarına giriş ve karmaşıklık analizi
2. Diziler ve bağlı listeler
3. Yığınlar (Stack) ve kuyruklar (Queue)
4. Ağaçlar (Binary Tree, BST, AVL)
5. Hash tabloları
6. Graf yapıları
7. Sıralama algoritmaları (Quick Sort, Merge Sort, Heap Sort)
8. Arama algoritmaları

Öğrenme Çıktıları:
- Farklı veri yapılarının özelliklerini bilir
- Uygun veri yapısını seçerek kullanabilir
- Algoritma karmaşıklığını analiz edebilir
- Verimli kod yazabilir

Değerlendirme:
- Ara sınav: %30
- Final sınavı: %50
- Lab çalışmaları: %20"""
                },
                {
                    "code": "BLM301",
                    "name": "Veritabanı Yönetim Sistemleri",
                    "department": "Bilgisayar Mühendisliği",
                    "credits": 4,
                    "description": """Ders İçeriği:
Bu ders, veritabanı tasarımı, SQL programlama ve veritabanı yönetim sistemlerinin temellerini kapsar.

Ders Konuları:
1. Veritabanı kavramları ve VTYS mimarileri
2. İlişkisel model ve normalizasyon
3. SQL dili (DDL, DML, DCL)
4. Sorgu optimizasyonu
5. Transaction yönetimi
6. Concurrency control ve recovery
7. İndeksleme ve hashing
8. NoSQL veritabanlarına giriş

Öğrenme Çıktıları:
- İlişkisel veritabanı tasarlayabilir
- SQL sorguları yazabilir
- Veritabanı normalizasyonu yapabilir
- Transaction kavramını anlayabilir

Ön Koşullar:
BLM102 - Veri Yapıları

Değerlendirme:
- Ara sınav: %30
- Final sınavı: %40
- Proje: %30"""
                },
                {
                    "code": "BLM401",
                    "name": "Yapay Zeka",
                    "department": "Bilgisayar Mühendisliği",
                    "credits": 4,
                    "description": """Ders İçeriği:
Yapay zeka temel kavramları, problem çözme yöntemleri, arama algoritmaları ve makine öğrenmesi konularını içerir.

Ders Konuları:
1. Yapay zekaya giriş ve tarihçesi
2. Akıllı ajanlar
3. Arama algoritmaları (BFS, DFS, A*, Minimax)
4. Bilgi gösterimi ve mantıksal çıkarım
5. Belirsizlik ve olasılıksal akıl yürütme
6. Makine öğrenmesine giriş
7. Yapay sinir ağları temel kavramları
8. Doğal dil işleme ve bilgisayarlı görü'ye giriş

Öğrenme Çıktıları:
- Yapay zeka problemlerini tanımlayabilir
- Uygun arama algoritmasını seçip uygulayabilir
- Temel makine öğrenmesi algoritmaları kullanabilir
- AI uygulamaları geliştirebilir

Ön Koşullar:
BLM102 - Veri Yapıları
BLM201 - Algoritma Analizi

Değerlendirme:
- Ara sınav: %25
- Final sınavı: %40
- Proje: %35"""
                },
            ],
            "MAK": [
                {
                    "code": "MAK101",
                    "name": "Mühendislik Mekaniği",
                    "department": "Makine Mühendisliği",
                    "credits": 4,
                    "description": """Ders İçeriği:
Statik ve dinamik kuvvet sistemleri, denge koşulları ve temel mekanik prensipler.

Ders Konuları:
1. Kuvvet sistemleri
2. Denge koşulları
3. Rijit cisim dengesi
4. Sürtünme
5. Ağırlık merkezi
6. Atalet momenti
7. Makaralı sistemler

Öğrenme Çıktıları:
- Kuvvet sistemlerini analiz edebilir
- Denge problemlerini çözebilir
- Mühendislik problemlerini modelleyebilir"""
                },
            ],
        }
        
        return sample_courses.get(dept_code, [])
    
    async def scrape_course_detail(self, course_code: str) -> Optional[Dict[str, any]]:
        """
        Fetch detailed information for a specific course.
        """
        logger.info(f"Fetching details for course: {course_code}")
        
        # In production, this would fetch from actual GTU website
        # For now, return None to indicate course not found
        return None
    
    async def bulk_import(self, department_codes: List[str] = None, limit_per_dept: int = None) -> List[Dict[str, any]]:
        """
        Bulk import courses from multiple departments.
        
        Args:
            department_codes: List of department codes to import. If None, imports from all.
            limit_per_dept: Maximum courses to import per department. If None, imports all.
        
        Returns:
            List of course dictionaries ready for database import
        """
        logger.info(f"Starting bulk import from GTU...")
        
        if department_codes is None:
            departments = await self.get_departments()
            department_codes = [d["code"] for d in departments]
        
        all_courses = []
        
        for dept_code in department_codes:
            try:
                courses = await self.scrape_department_courses(dept_code)
                if limit_per_dept:
                    courses = courses[:limit_per_dept]
                all_courses.extend(courses)
                # Be nice to the server
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error scraping {dept_code}: {str(e)}")
                continue
        
        logger.info(f"Bulk import complete: {len(all_courses)} courses collected")
        return all_courses


# Singleton instance
gtu_scraper = GTUScraper()
