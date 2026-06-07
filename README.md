# OrthogoLink - Curriculum Orthogonality Checker

AI-powered web application that compares a new course syllabus against stored university course descriptions and calculates semantic overlap percentage. Supports cross-university comparison across 5 Turkish universities.

## Features

### Core
- **Semantic Comparison Engine** - Sentence-BERT (paraphrase-multilingual-MiniLM-L12-v2) + FAISS for fast cosine similarity search, with Turkish↔English cross-lingual matching
- **Optional Cross-Encoder Re-ranking** - retrieve-then-rerank stage for higher precision on confusable course pairs (validated by the eval harness)
- **PDF & Text Input** - Upload PDF syllabi or paste text directly
- **Section-Level Analysis** - Splits syllabi into sections (Learning Outcomes, Course Content, etc.) for granular matching
- **Cross-University Comparison** - Compare a syllabus against courses from specific universities
- **Detailed Reports** - Downloadable TXT and CSV reports with overlap analysis

### University Support
| University | Code | Status |
|-----------|------|--------|
| Gebze Teknik Universitesi (GTU) | gtu | Available |
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
| AI/NLP | Sentence-Transformers bi-encoder (`paraphrase-multilingual-MiniLM-L12-v2`) + optional cross-encoder re-ranker |
| Vector search | PostgreSQL + `pgvector` (HNSW cosine index); FAISS retained for the offline benchmark |
| Database | PostgreSQL 16 (`pgvector/pgvector:pg16`) |
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
│   │   │   ├── embedding_service.py    # Sentence-BERT bi-encoder + cross-encoder + FAISS (benchmark)
│   │   │   ├── vector_search.py        # pgvector cosine search (production backend)
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

1. **Store courses**: Admin adds courses or imports from universities -> text is split into semantic sections -> each section embedded using Sentence-BERT -> embeddings stored in PostgreSQL (`pgvector` column, HNSW-indexed)
2. **Compare**: User uploads PDF or pastes text -> extracted text split into sections -> each section embedded -> pgvector cosine similarity search (optionally cross-encoder re-ranked) -> top matches aggregated -> overlap report generated
3. **Cross-university**: Same as above, but with optional filters to compare against specific university course code prefixes

## Testing & Evaluation

Two layers — see [backend/tests/README.md](backend/tests/README.md) for details.

- **Unit tests** (`backend/tests/`) cover the deterministic logic (overlap
  classification, confidence, aggregation, report generation, section
  splitting). Heavy deps are stubbed, so they run in <1s with no model download:
  ```bash
  cd backend && pip install -r requirements-dev.txt && python -m pytest tests/ -v
  ```
- **Evaluation harness** (`backend/eval/`) measures overlap-detection quality
  against a labeled, bilingual benchmark and sweeps the similarity threshold,
  reporting precision / recall / F1. This is how the threshold and model choice
  are justified empirically:
  ```bash
  docker exec docker-backend-1 python -m eval.benchmark
  ```
  On the seed benchmark the multilingual model reaches **F1 = 1.00 at cutoff
  0.75** (perfect on all TR/EN cross-lingual pairs), versus F1 ≈ 0.55 for the
  English-only model — the evidence for using `paraphrase-multilingual-MiniLM-L12-v2`.

### Cross-encoder re-ranking (optional precision stage)

The default pipeline is a fast **bi-encoder** (embed once, FAISS cosine search).
Enabling `RERANK_ENABLED` adds a second **cross-encoder** stage that re-reads each
`(query section, candidate section)` pair jointly and re-scores the bi-encoder's
top `RERANK_CANDIDATES`. The cross-encoder score is squashed to `[0,1]` and blended
with cosine via `RERANK_WEIGHT`, so existing thresholds stay meaningful. This is the
classic *retrieve-then-rerank* design: the bi-encoder gives speed, the cross-encoder
gives precision on confusable pairs (e.g. Machine Learning vs. Data Mining, Linear
Algebra vs. Calculus).

The benchmark proves the trade-off empirically — run both modes head-to-head:

```bash
docker exec docker-backend-1 python -m eval.benchmark --compare
```

It prints baseline vs. re-rank precision/recall/F1 at each cutoff and the best-F1
delta, and helps tune `RERANK_WEIGHT`. Re-ranking is off by default so the system
stays fast unless the benchmark justifies turning it on.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async DB connection |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed CORS origins |
| `MODEL_NAME` | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence-Transformer model (multilingual; required for TR/EN comparison) |
| `SIMILARITY_THRESHOLD` | `0.70` | Overlap threshold |
| `SEARCH_BACKEND` | `pgvector` | `pgvector` (multi-worker, DB-backed) or `faiss` (single-worker, in-process) |
| `EMBEDDING_DIM` | `384` | Embedding size; pgvector column dimension (must match the model) |
| `RERANK_ENABLED` | `false` | Enable cross-encoder re-ranking of bi-encoder candidates |
| `RERANK_MODEL` | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | Multilingual cross-encoder used for re-ranking |
| `RERANK_CANDIDATES` | `30` | Bi-encoder candidates re-scored per input section |
| `RERANK_WEIGHT` | `0.5` | Blend weight: `final = (1-w)·cosine + w·cross_encoder` |
| `MIN_INPUT_CHARS` | `50` | Reject syllabus input shorter than this |
| `MAX_INPUT_CHARS` | `50000` | Reject syllabus input larger than this (memory/CPU guard) |
| `MAX_UPLOAD_BYTES` | `10485760` | Max accepted PDF upload size (10 MB) |
| `SECRET_KEY` | `...` | JWT secret key. **Required in production** — the app refuses to start (when `DEBUG=false`) if left at the built-in default. |
| `RATE_LIMIT_ENABLED` | `true` | Enable per-IP API rate limiting |
| `RATE_LIMIT` | `60/minute` | Per-IP request budget applied to all routes |

> **Deployment note — scaling.** With the default `SEARCH_BACKEND=pgvector`,
> embeddings are searched in PostgreSQL (via the `pgvector` extension), so the
> backend can run with **multiple uvicorn workers** and survives restarts —
> runtime course add/update/delete/import is visible to every worker immediately,
> with no in-memory index to keep in sync.
>
> The legacy `SEARCH_BACKEND=faiss` keeps the index in process memory and must run
> with a **single** worker (it is also the backend the standalone
> `eval/benchmark.py` uses, since the benchmark has no database).

## Production Hardening

- **Fail-loud config** — at startup (when `DEBUG=false`) the app refuses to run if
  `SECRET_KEY` is still the built-in default, and warns on default DB credentials,
  so an insecure deploy can't ship silently.
- **Per-IP rate limiting** — `slowapi` applies `RATE_LIMIT` (default `60/minute`)
  to every route, protecting the embedding-heavy `/compare` endpoints from abuse.
- **CI** — GitHub Actions runs the backend unit-test suite on every push and PR
  (`.github/workflows/ci.yml`).

## Seed Data

5 pre-loaded courses on first startup:
- CS101 - Introduction to Computer Science
- CS301 - Data Structures and Algorithms
- CS350 - Database Management Systems
- CS410 - Natural Language Processing
- CS420 - Machine Learning
