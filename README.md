# RightStaff - AI-Powered Candidate Ranking System

**RightStaff** is an intelligent recruitment platform that uses Retrieval-Augmented Generation (RAG) and semantic search to match candidates with job openings. The system automatically parses resumes, extracts skills, generates embeddings, and ranks candidates based on job requirements.

---

## 🎯 Project Overview

RightStaff transforms traditional applicant tracking by combining:
- **Resume parsing** with PDF/DOCX support
- **Semantic search** using vector embeddings
- **AI-powered skill extraction** with OpenAI and spaCy
- **Multi-stage ranking** with hybrid search and cross-encoder re-ranking
- **Auto-healing ingestion** pipeline with retry mechanisms

The system maintains three types of vector representations per candidate:
1. **Profile vectors** - Full resume summary
2. **Skills vectors** - Extracted competencies
3. **Chunk vectors** - Resume text segments for context retrieval

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  - Candidate Upload   - Job Management   - Ranking Dashboard   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST API
┌───────────────────────────▼─────────────────────────────────────┐
│                     FastAPI Backend                              │
│  - API Endpoints   - Ingestion Worker   - Auto-Healing Monitor │
└──┬────────┬────────┬────────┬─────────┬────────────────────────┘
   │        │        │        │         │
   ▼        ▼        ▼        ▼         ▼
┌─────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│PostgreSQL│Qdrant│ MinIO │ Redis │OpenAI│
│ (OLTP) │(Vector)│(S3)  │(Queue)│ API  │
└─────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

---

## 🛠️ Technology Stack

### **Backend**
| Technology | Version | Purpose | Why We Use It |
|------------|---------|---------|---------------|
| **Python** | 3.11+ | Core language | Excellent AI/ML ecosystem |
| **FastAPI** | Latest | Web framework | Async support, automatic API docs, type safety |
| **SQLAlchemy** | 2.0+ | ORM | AsyncPG support, declarative models |
| **asyncpg** | Latest | PostgreSQL driver | High-performance async queries |
| **Pydantic** | 2.0+ | Data validation | Type safety, environment config |
| **Tenacity** | Latest | Retry logic | Resilient background jobs |
| **Structlog** | Latest | Logging | JSON structured logs, context binding |

### **AI/ML Frameworks**
| Technology | Version | Purpose | Why We Use It |
|------------|---------|---------|---------------|
| **sentence-transformers** | Latest | Embeddings | Fast, local semantic embeddings (384-dim) |
| **spaCy** | 3.7+ | NLP | Skill extraction fallback, entity recognition |
| **OpenAI API** | Latest | LLM parsing | GPT-4 for resume parsing, skill extraction |
| **pypdf** | Latest | PDF parsing | Extract text from resume PDFs |
| **python-docx** | Latest | DOCX parsing | Extract text from Word resumes |

### **Databases & Storage**
| Technology | Version | Purpose | Why We Use It |
|------------|---------|---------|---------------|
| **PostgreSQL** | 18 | OLTP database | ACID compliance, JSONB support, proven reliability |
| **Qdrant** | 1.7+ | Vector database | Fast cosine similarity search, collection management |
| **MinIO** | Latest | Object storage | S3-compatible, self-hosted resume storage |
| **Redis** | 7.2+ | Cache & queue | Job queue, parsed data cache, job embeddings cache |

### **Frontend**
| Technology | Version | Purpose | Why We Use It |
|------------|---------|---------|---------------|
| **React** | 19+ | UI framework | Component reusability, large ecosystem |
| **TypeScript** | 4.9+ | Type safety | Catch errors at compile time |
| **React Router** | 6.30+ | Client routing | SPA navigation |
| **Zustand** | 5.0+ | State management | Lightweight alternative to Redux |
| **React Hook Form** | 7.66+ | Form handling | Performance, validation with Zod |
| **Axios** | 1.13+ | HTTP client | Promise-based, interceptors |
| **Tailwind CSS** | 3.4+ | Styling | Utility-first, rapid development |
| **Lucide React** | Latest | Icons | Modern, consistent icon set |

### **Infrastructure**
| Technology | Purpose |
|------------|---------|
| **Docker Compose** | Multi-container orchestration |
| **Docker** | Containerization |

---

## 📊 Database Schema

### **PostgreSQL (OLTP)**

#### Core Tables
```sql
-- Candidates
candidate (id, full_name, years_experience, professional_summary, created_at, updated_at)
candidate_contact (candidate_id PK, email, phone, city, region, country)
candidate_preference (candidate_id PK, work_authorization, work_arrangement, desired_salary_min/max, open_to_remote)
candidate_demographics (candidate_id PK, disability, ethnicity, veteran_status)
candidate_resume (id, candidate_id, s3_url, file_type, is_latest, uploaded_at)

-- Experience & Education
candidate_experience (id, candidate_id, title, company, employment_type, start_date, end_date, description, industry)
candidate_education (id, candidate_id, degree, institution, field_of_study, graduation_year, gpa, honors)
candidate_certification (id, candidate_id, name, issuer, issued_on, expires_on, credential_url)

-- Skills (Many-to-Many)
skill (id, name UNIQUE, parent_skill_id)
skill_synonym (id, skill_id, synonym)
candidate_skill (candidate_id, skill_id, level, years)  -- PK: (candidate_id, skill_id)

-- Jobs & Applications
job (id, title, description, department, location, status, required_skills_json, must_have_skills_json,
     min_years_experience, max_years_experience, work_arrangement, employment_type,
     is_remote, visa_sponsorship_available, created_at, updated_at)
application (id, candidate_id, job_id, status, applied_at, updated_at)  -- UNIQUE: (candidate_id, job_id)

-- Enums
job_status_enum: 'draft', 'open', 'on_hold', 'closed', 'filled'
application_status_enum: 'sourced', 'applied', 'screen', 'shortlist', 'interview', 'offer', 'hired', 'rejected', 'withdrawn'
employment_type_enum: 'full_time', 'contract', 'internship', 'freelance'
work_arrangement_enum: 'Remote', 'Hybrid', 'On-site'
```

**Schema Name:** `rightstaff`
**User:** `right_staff`

### **Qdrant (Vector Database)**

#### Collection: `candidates_v1`
- **Vector Size:** 384 dimensions
- **Distance Metric:** Cosine similarity
- **Vectors per Candidate:**
  - 1 profile vector (full resume summary)
  - 1 skills vector (concatenated skills)
  - N chunk vectors (resume text chunks, 400 chars with 50 char overlap)

**Payload Schema:**
```json
{
  "candidate_id": "uuid",
  "kind": "profile | skills | chunk",
  "full_name": "string",
  "text": "string (snippet for profile/chunk)",
  "skills": ["skill1", "skill2"],
  "skills_count": "int (for skills kind)",
  "chunk_index": "int (for chunk kind)",
  "chunk_text": "string (for chunk kind)",
  "start_char": "int",
  "end_char": "int",
  "char_count": "int",
  "filename": "string",
  "created_at": "ISO timestamp"
}
```

#### Collection: `jobs_v1`
- **Vector Size:** 384 dimensions
- **Vectors per Job:**
  - 1 profile vector (title + description)
  - 1 skills vector (must-have 3x weighted + nice-to-have)

**Payload Schema:**
```json
{
  "job_id": "uuid",
  "title": "string",
  "kind": "profile | skills",
  "required_skills": ["skill1", "skill2"],
  "must_have_skills": ["skill1"],
  "created_at": "ISO timestamp"
}
```

### **MinIO (Object Storage)**
- **Bucket:** `rightstaff-resumes`
- **Path Structure:** `resumes/{candidate_uuid}/resume.{ext}`
- **Supported Formats:** PDF, DOCX, DOC, TXT
- **Access:** Private (pre-signed URLs on demand)

### **Redis (Cache & Queue)**
- **Queue:** `ingestion_queue` (job processing)
- **DLQ:** `ingestion_queue_dlq` (failed jobs)
- **Cache Keys:**
  - `parsed_candidate:{temp_id}` (TTL: 1 hour) - Parse-only results
  - `job_embeddings:{job_id}:{hash}` (TTL: 1 hour) - Cached job vectors

---

## 🤖 RAG & Ingestion Pipeline

### **How RAG is Enabled**

RightStaff implements a **hybrid RAG approach**:

1. **Semantic Search (Vector Retrieval)**
   - Query job requirements → Generate embedding
   - Search Qdrant for top N candidates by cosine similarity
   - Retrieve profile, skills, and chunk vectors

2. **Keyword Matching (SQL Filters)**
   - Filter candidates by must-have skills (PostgreSQL JSONB)
   - Apply experience range constraints
   - Check work authorization, location preferences

3. **Context Augmentation**
   - Retrieved candidate profiles + resume chunks
   - Job description + requirements
   - Skill overlap analysis

4. **Cross-Encoder Re-Ranking**
   - Re-rank top candidates using `cross-encoder/ms-marco-MiniLM-L-6-v2`
   - Considers full context (query + candidate profile)
   - Produces final ranked list

### **Ingestion Pipeline Architecture**

```
┌──────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE (8 STAGES)                  │
└──────────────────────────────────────────────────────────────────┘

Stage 1: API Receives Resume Upload
   ↓ (POST /api/v1/candidates/upload-resume)
   - Validate file type (PDF/DOCX/TXT)
   - Generate temp_id (UUID)
   - Upload to MinIO: s3://rightstaff-resumes/resumes/{temp_id}/resume.pdf

Stage 2: Queue Parse-Only Job
   ↓ (LPUSH to Redis ingestion_queue)
   - Job: {"job_id": "parse_{temp_id}", "mode": "parse_only", "s3_url": "..."}

Stage 3: Background Worker Picks Job
   ↓ (Ingestion Worker BRPOP from queue)
   - Download resume from MinIO
   - Extract text (pypdf/python-docx)

Stage 4: Parse Resume (LLM or spaCy)
   ↓ (OpenAI GPT-4 or spaCy fallback)
   - Extract: name, email, phone, experience, education, skills
   - Cache parsed data in Redis (TTL: 1 hour)
   - Return parsed data to API

Stage 5: User Submits Candidate Form
   ↓ (POST /api/v1/candidates/ with temp_id + form data)
   - Create Candidate record in PostgreSQL
   - Create CandidateContact, CandidatePreference, etc.
   - Queue FULL ingestion job

Stage 6: Full Ingestion Processing
   ↓ (Background worker processes full ingestion)
   a) Fetch candidate details from PostgreSQL
   b) Download resume from MinIO
   c) Parse resume text
   d) Extract skills (OpenAI or spaCy)
   e) Store skills in PostgreSQL (candidate_skill table)
   f) Chunk resume text (400 chars, 50 overlap)
   g) Generate embeddings (sentence-transformers)
   h) Store vectors in Qdrant (profile + skills + chunks)

Stage 7: Auto-Healing Monitor (Every 5 Minutes)
   ↓ (Ingestion Monitor background task)
   - Query PostgreSQL for all candidates with resumes
   - Check Qdrant for missing vectors
   - Auto-queue missing candidates for re-ingestion

Stage 8: Failure Handling
   ↓ (Tenacity retry with exponential backoff)
   - Retry failed jobs (max 5 attempts)
   - Move exhausted jobs to DLQ
   - Log errors with full traceback
```

### **When Pipelines Activate**

| Trigger | Pipeline | Mode | Result |
|---------|----------|------|--------|
| **Resume Upload** | Parse-only | Anonymous | Cached parsed data for form pre-fill |
| **Candidate Creation** | Full ingestion | Authenticated | Complete profile with vectors in Qdrant |
| **Profile Update Webhook** | Full re-ingestion | External | Re-embed updated profile |
| **Missing Vectors Detected** | Auto-healing | System | Self-repair for failed ingestions |
| **Job Creation** | Job embeddings | System | Generate job vectors for matching |

---

## 🚀 Setup Guide (New Desktop)

### **Prerequisites**
- Docker Desktop installed
- Python 3.11+ installed
- Node.js 16+ and npm installed
- Git installed

---

### **Step 1: Clone Repository**
```bash
git clone <repository-url>
cd RightStaff
```

---

### **Step 2: Start Docker Services**
```bash
cd docker
docker-compose up -d
```

**Services Started:**
- PostgreSQL (port 5433)
- Qdrant (port 6333)
- Redis (port 6379)
- MinIO (port 9000, console 9001)

**Wait 10 seconds for services to initialize.**

---

### **Step 3: Setup Backend**

#### a) Create Python Virtual Environment
```bash
cd ../backend
python -m venv venv
```

#### b) Activate Virtual Environment
**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

#### c) Install Dependencies
```bash
pip install -r requirements.txt
```

#### d) Download spaCy Model
```bash
python -m spacy download en_core_web_sm
```

#### e) Configure Environment Variables
Edit `backend/.env`:
```env
# OpenAI API Key (required for LLM parsing)
OPENAI_API_KEY=sk-your-key-here

# Database (already configured for Docker)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=rightstaff
POSTGRES_USER=right_staff
POSTGRES_PASSWORD=dev_password_123

# Other services (defaults work with Docker)
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_HOST=localhost
REDIS_PORT=6379
MINIO_ENDPOINT=localhost:9000
MINIO_BUCKET=rightstaff-resumes
```

#### f) Populate Database with Test Data
```bash
python populate_dummy_data.py
```

**Expected Output:**
```
✅ Jobs: 6
✅ Candidates: 8
✅ Skills: 49
✅ Candidate Vectors: 24
✅ Resumes in MinIO: 5
```

#### g) Verify Database
```bash
python check_database.py
```

**Expected Output:**
```
Applications: 48
Jobs: 6
Candidates: 8
```

---

### **Step 4: Setup Frontend**

#### a) Install Dependencies
```bash
cd ../frontend
npm install
```

#### b) Configure API Endpoint
Edit `frontend/src/config.ts` (if needed):
```typescript
export const API_BASE_URL = 'http://localhost:8000';
```

---

### **Step 5: Start the Application**

#### a) Start Backend (Terminal 1)
```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Backend will be available at:** http://localhost:8000
**API Docs:** http://localhost:8000/docs

#### b) Start Frontend (Terminal 2)
```bash
cd frontend
npm start
```

**Frontend will be available at:** http://localhost:3000

---

### **Step 6: Verify Everything Works**

1. **Open Frontend:** http://localhost:3000
2. **Check API Health:** http://localhost:8000/health
3. **View API Docs:** http://localhost:8000/docs
4. **MinIO Console:** http://localhost:9001 (minioadmin / minioadmin123)

---

## 🧪 Testing the System

### **1. Upload a Resume**
- Navigate to "Upload Resume" page
- Drag & drop a PDF/DOCX resume
- System will parse and extract data
- Fill candidate form with parsed data
- Submit to create candidate profile

### **2. Create a Job Posting**
- Navigate to "Jobs" page
- Click "Create Job"
- Fill in job details and required skills
- Submit to create job with embeddings

### **3. Rank Candidates**
- Navigate to "Ranking" page
- Select a job
- System will rank all candidates
- View ranked results with scores

---

## 🔧 Useful Commands

### **Clear All Data**
```bash
cd backend
python clear_all_data.py
```

### **Re-populate Test Data**
```bash
python populate_dummy_data.py
```

### **Check Database State**
```bash
python check_database.py
```

### **Stop Docker Services**
```bash
cd docker
docker-compose down
```

### **View Docker Logs**
```bash
docker-compose logs -f postgres
docker-compose logs -f qdrant
```

---

## 📁 Project Structure

```
RightStaff/
├── backend/              # FastAPI backend application
│   ├── app/
│   │   ├── api/         # API route handlers
│   │   ├── models/      # SQLAlchemy ORM models
│   │   ├── services/    # Business logic (ingestion, ranking, embeddings)
│   │   ├── utils/       # Utilities (logging, parsing)
│   │   ├── config.py    # Pydantic settings
│   │   ├── database.py  # Database connection
│   │   └── main.py      # FastAPI app entry point
│   ├── clear_all_data.py
│   ├── populate_dummy_data.py
│   ├── check_database.py
│   └── requirements.txt
├── frontend/             # React TypeScript frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── store/       # Zustand state management
│   │   ├── types/       # TypeScript type definitions
│   │   └── App.tsx
│   └── package.json
├── database/
│   └── scripts/
│       ├── 01_schema.sql          # PostgreSQL schema (ESSENTIAL)
│       ├── 00_rollback.sql        # Drop all tables
│       └── 03_postseed_helpers.sql # Helper functions
├── docker/
│   ├── docker-compose.yml
│   └── .env.docker
└── README.md
```

For detailed file-by-file documentation, see **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)**.

---

## 🐛 Troubleshooting

### **Port Already in Use**
If PostgreSQL port 5432 is taken:
- We use 5433 by default (already configured)
- Or stop local PostgreSQL service

### **OpenAI API Rate Limits**
- System falls back to spaCy for skill extraction
- LLM parsing is optional (set `USE_LLM_PARSING=false` in .env)

### **MinIO Connection Issues**
```bash
docker restart rightstaff-minio
```

### **Qdrant Collection Errors**
```bash
# Recreate collections
cd backend
python -c "from app.services.vector_store import vector_store; vector_store.initialize_collections()"
```

### **Database Schema Mismatch**
```bash
# Reset database
cd docker
docker-compose down -v
docker-compose up -d
# Wait 10 seconds, then repopulate
cd ../backend
python populate_dummy_data.py
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is proprietary software.

---

## 📧 Contact

For questions or support, contact the development team.

---

**Built with ❤️ for modern recruitment**
