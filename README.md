# Curriculum Orthogonality Checker

AI-powered web application that compares a new course syllabus against stored university course descriptions and calculates semantic overlap percentage.

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
spring26/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI route handlers
│   │   │   ├── courses.py    # CRUD for courses (admin)
│   │   │   └── compare.py    # Comparison endpoints (user)
│   │   ├── core/
│   │   │   ├── config.py     # Environment-based configuration
│   │   │   └── database.py   # Async DB engine & session
│   │   ├── models/
│   │   │   ├── course.py     # SQLAlchemy ORM models
│   │   │   └── schemas.py    # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── embedding_service.py   # Sentence-BERT + FAISS
│   │   │   ├── pdf_service.py         # PDF extraction + section splitting
│   │   │   ├── comparison_service.py  # Orchestrates comparison pipeline
│   │   │   └── course_service.py      # Course CRUD + embedding generation
│   │   ├── seed/
│   │   │   └── seed_data.py   # 5 sample course descriptions
│   │   └── main.py            # FastAPI app entry point
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── public/index.html
│   ├── src/
│   │   ├── api/client.js      # Axios API client
│   │   ├── components/
│   │   │   ├── UploadForm.js      # Text/PDF upload form
│   │   │   ├── ResultsDisplay.js  # Similarity results tables
│   │   │   ├── CourseList.js      # View stored courses
│   │   │   └── AddCourse.js       # Add new course form
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
| **Health Check** | http://localhost:8000/api/health |

## API Endpoints

### Courses (Admin)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/courses/` | List all courses |
| `POST` | `/api/courses/` | Add course + generate embeddings |
| `GET` | `/api/courses/{id}` | Get course details with sections |
| `DELETE` | `/api/courses/{id}` | Delete course + rebuild index |
| `POST` | `/api/courses/rebuild-index` | Manually rebuild FAISS index |

### Comparison (User)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/compare/text` | Compare pasted syllabus text |
| `POST` | `/api/compare/pdf` | Compare uploaded PDF syllabus |

### Example: Compare Text

**Request:**
```json
POST /api/compare/text
{
  "text": "Course Description\nThis course covers supervised and unsupervised machine learning methods including regression, classification, clustering, and neural networks.\n\nLearning Outcomes\n1. Implement linear and logistic regression models.\n2. Build and train neural networks using backpropagation.\n3. Apply clustering algorithms to real datasets.\n\nCourse Content\nLinear regression, gradient descent, logistic regression, decision trees, SVM, neural networks, k-means clustering, PCA, model evaluation, cross-validation."
}
```

**Response:**
```json
{
  "overall_similarity": 0.6892,
  "overlap_percentage": 45.0,
  "top_courses": [
    {
      "course_code": "CS420",
      "course_name": "Machine Learning",
      "average_similarity": 0.8234,
      "is_overlap": true
    },
    {
      "course_code": "CS410",
      "course_name": "Natural Language Processing",
      "average_similarity": 0.4521,
      "is_overlap": false
    },
    {
      "course_code": "CS301",
      "course_name": "Data Structures and Algorithms",
      "average_similarity": 0.2103,
      "is_overlap": false
    }
  ],
  "section_matches": [
    {
      "input_section": "Course Content",
      "matched_course_code": "CS420",
      "matched_course_name": "Machine Learning",
      "matched_section": "Course Content",
      "similarity": 0.9012,
      "is_overlap": true
    }
  ],
  "report_summary": "==================================================\nCURRICULUM ORTHOGONALITY REPORT\n..."
}
```

## Configuration

All configuration is via environment variables (see `backend/.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@db:5432/orthogonality` | Async DB connection |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:80` | Allowed CORS origins |
| `MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence-Transformer model |
| `SIMILARITY_THRESHOLD` | `0.70` | Cosine similarity overlap threshold |
| `FAISS_INDEX_PATH` | `/app/data/faiss_index` | FAISS index storage path |

## How It Works

1. **Store courses**: Admin adds courses → text is split into sections → each section is embedded using Sentence-BERT → embeddings stored in DB and indexed in FAISS.
2. **Compare syllabus**: User uploads PDF or pastes text → text extracted → split into sections → each section embedded → FAISS cosine similarity search → top matches aggregated → results returned with overlap percentages and report.

## Seed Data

5 pre-loaded courses on first startup:
- CS101 — Introduction to Computer Science
- CS301 — Data Structures and Algorithms
- CS350 — Database Management Systems
- CS410 — Natural Language Processing
- CS420 — Machine Learning

## VPS Deployment

1. Install Docker & Docker Compose on your VPS
2. Clone the repository
3. Edit `docker/docker-compose.yml` — update ports and environment variables
4. `cd docker && docker-compose up -d --build`
5. Configure your domain's DNS to point to the VPS IP
6. (Optional) Add SSL with Let's Encrypt / Certbot reverse proxy
