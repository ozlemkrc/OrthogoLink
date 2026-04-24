# OrthogoLink - Curriculum Orthogonality Checker

AI-powered web application that compares a new course syllabus against stored university course descriptions and calculates semantic overlap percentage. Supports cross-university comparison across 5 Turkish universities.

## Features

### Core
- **Semantic Comparison Engine** - Sentence-BERT (all-MiniLM-L6-v2) + FAISS for fast cosine similarity search
- **PDF & Text Input** - Upload PDF syllabi or paste text directly
- **Section-Level Analysis** - Splits syllabi into sections (Learning Outcomes, Course Content, etc.) for granular matching
- **Cross-University Comparison** - Compare a syllabus against courses from specific universities
- **Detailed Reports** - Downloadable TXT and CSV reports with overlap analysis

### University Support
| University | Code | Status |
|-----------|------|--------|
| Gebze Teknik Universitesi (GTU) | gtu | Available |
| Istanbul Teknik Universitesi (ITU) | itu | Available |
| Orta Dogu Teknik Universitesi (METU) | metu | Available |
| Hacettepe Universitesi | hacettepe | Available |
| Izmir Yuksek Teknoloji Enstitusu (IYTE) | iyte | Available |

### Management
- **Course CRUD** - Add, edit, delete courses with automatic embedding regeneration
- **Search & Filter** - Find courses by code, name, or department
- **Bulk Import** - Import entire department catalogs from any supported university
- **Dashboard** - Statistics overview with department distribution and comparison history
- **Authentication** - JWT-based user login/registration
- **Comparison History** - Track and review past comparisons

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy (async) |
| AI/NLP | Sentence-Transformers (`all-MiniLM-L6-v2`), FAISS |
| Database | PostgreSQL 16 |
| Frontend | React 18, Axios |
| Deployment | Docker, Docker Compose, Nginx |

## Project Structure

```
OrthogoLink/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── courses.py         # CRUD, search, stats, dashboard
│   │   │   ├── compare.py         # Comparison, cross-uni, history, CSV export
│   │   │   ├── import_courses.py  # Multi-university import
│   │   │   └── auth.py            # Authentication (register/login)
│   │   ├── core/
│   │   │   ├── config.py          # Environment configuration
│   │   │   └── database.py        # Async DB engine & session
│   │   ├── models/
│   │   │   ├── course.py          # ORM models (Course, Section, User, etc.)
│   │   │   └── schemas.py         # Pydantic schemas
│   │   ├── services/
│   │   │   ├── embedding_service.py    # Sentence-BERT + FAISS
│   │   │   ├── pdf_service.py          # PDF extraction + section splitting
│   │   │   ├── comparison_service.py   # Comparison pipeline with filtering
│   │   │   ├── course_service.py       # Course CRUD + embeddings
│   │   │   └── university_scraper.py   # 5 university scrapers
│   │   ├── seed/
│   │   │   └── seed_data.py
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js
│   │   ├── components/
│   │   │   ├── Dashboard.js          # Statistics overview
│   │   │   ├── UploadForm.js         # Text/PDF upload
│   │   │   ├── ResultsDisplay.js     # Comparison results
│   │   │   ├── CrossUniCompare.js    # Cross-university comparison
│   │   │   ├── CourseList.js         # Search, filter, edit, delete
│   │   │   ├── AddCourse.js          # Add new course
│   │   │   ├── ImportCourses.js      # Multi-university import
│   │   │   ├── ComparisonHistory.js  # Past comparisons
│   │   │   ├── AuthModal.js          # Login/Register
│   │   │   └── StatusBar.js          # Health status
│   │   ├── App.js
│   │   ├── index.js
│   │   └── index.css
│   ├── nginx.conf
│   └── Dockerfile
├── docker/
│   └── docker-compose.yml
└── README.md
```

## Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose installed

### Run

```bash
cd docker
docker-compose up --build
```

First startup will:
1. Pull/build all images (backend build downloads the AI model ~90MB)
2. Start PostgreSQL
3. Start the FastAPI backend (creates tables, seeds 5 sample courses)
4. Build and serve the React frontend via Nginx

### Access

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost |
| **API Docs** | http://localhost:8000/docs |

## API Endpoints

### Courses
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/courses/` | List courses (supports `?search=` and `?department=`) |
| `POST` | `/api/courses/` | Add course + generate embeddings |
| `GET` | `/api/courses/{id}` | Get course details |
| `PUT` | `/api/courses/{id}` | Update course |
| `DELETE` | `/api/courses/{id}` | Delete course + rebuild index |
| `GET` | `/api/courses/departments` | List unique departments |
| `GET` | `/api/courses/stats` | Dashboard statistics |

### Comparison
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/compare/text` | Compare text syllabus |
| `POST` | `/api/compare/pdf` | Compare PDF syllabus |
| `POST` | `/api/compare/cross-university` | Cross-university comparison with filters |
| `GET` | `/api/compare/history` | Comparison history |
| `POST` | `/api/compare/export-csv` | Export results as CSV |

### Import
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/import/universities` | List supported universities |
| `GET` | `/api/import/{uni}/departments` | Get departments |
| `POST` | `/api/import/{uni}/preview` | Preview courses |
| `POST` | `/api/import/{uni}/import` | Import courses |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Login |
| `GET` | `/api/auth/me` | Get current user |

## How It Works

1. **Store courses**: Admin adds courses or imports from universities -> text is split into semantic sections -> each section embedded using Sentence-BERT -> embeddings stored in DB and FAISS index
2. **Compare**: User uploads PDF or pastes text -> extracted text split into sections -> each section embedded -> FAISS cosine similarity search -> top matches aggregated -> overlap report generated
3. **Cross-university**: Same as above, but with optional filters to compare against specific university course code prefixes

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async DB connection |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed CORS origins |
| `MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence-Transformer model |
| `SIMILARITY_THRESHOLD` | `0.70` | Overlap threshold |
| `SECRET_KEY` | `...` | JWT secret key |

## Seed Data

5 pre-loaded courses on first startup:
- CS101 - Introduction to Computer Science
- CS301 - Data Structures and Algorithms
- CS350 - Database Management Systems
- CS410 - Natural Language Processing
- CS420 - Machine Learning
