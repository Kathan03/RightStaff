# RightStaff - Complete Project Structure Guide

**Comprehensive documentation of every file in the RightStaff codebase**

---

## 📂 Project Directory Structure

```
RightStaff/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── candidates.py
│   │   │   ├── chat.py
│   │   │   ├── jobs.py
│   │   │   └── webhooks.py
│   │   ├── models/            # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   └── candidate.py
│   │   ├── services/          # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── chatbot.py
│   │   │   ├── embeddings.py
│   │   │   ├── explanations.py
│   │   │   ├── ingestion.py
│   │   │   ├── ingestion_monitor.py
│   │   │   ├── job_embeddings.py
│   │   │   ├── llm_parser.py
│   │   │   ├── metrics.py
│   │   │   ├── ontology.py
│   │   │   ├── parsers.py
│   │   │   ├── ranking.py
│   │   │   ├── redis_client.py
│   │   │   ├── reranker.py
│   │   │   ├── retrieval.py
│   │   │   ├── s3_client.py
│   │   │   ├── scoring.py
│   │   │   ├── skill_extraction.py
│   │   │   ├── sql_filters.py
│   │   │   └── vector_store.py
│   │   ├── utils/             # Utility functions
│   │   │   ├── __init__.py
│   │   │   └── logging.py
│   │   ├── __init__.py
│   │   ├── config.py          # Application configuration
│   │   ├── database.py        # Database connection
│   │   └── main.py            # FastAPI app entry point
│   ├── clear_all_data.py      # Database cleanup script
│   ├── populate_dummy_data.py # Test data generation
│   ├── check_database.py      # Database verification
│   └── requirements.txt       # Python dependencies
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── api/               # API client layer
│   │   │   ├── candidates.ts
│   │   │   ├── chat.ts
│   │   │   ├── client.ts
│   │   │   └── jobs.ts
│   │   ├── components/        # React components
│   │   │   ├── candidate/
│   │   │   │   ├── CandidateCard.tsx
│   │   │   │   ├── CandidateForm.tsx
│   │   │   │   └── ResumeUpload.tsx
│   │   │   ├── recruiter/
│   │   │   │   ├── JobForm.tsx
│   │   │   │   ├── RankingDashboard.tsx
│   │   │   │   └── RankingResults.tsx
│   │   │   └── shared/
│   │   │       ├── Button.tsx
│   │   │       ├── Card.tsx
│   │   │       ├── Input.tsx
│   │   │       └── Select.tsx
│   │   ├── pages/             # Page components
│   │   │   ├── CandidatePage.tsx
│   │   │   └── RecruiterPage.tsx
│   │   ├── store/             # Zustand state management
│   │   │   ├── candidateStore.ts
│   │   │   └── recruiterStore.ts
│   │   ├── types/             # TypeScript type definitions
│   │   │   └── index.ts
│   │   ├── App.tsx            # Root React component
│   │   ├── index.tsx          # React entry point
│   │   └── setupTests.ts      # Test configuration
│   ├── package.json           # Node dependencies
│   └── tsconfig.json          # TypeScript configuration
├── database/
│   └── scripts/
│       ├── 00_rollback.sql           # Drop all tables
│       ├── 01_schema.sql             # PostgreSQL schema (REQUIRED)
│       └── 03_postseed_helpers.sql   # Helper SQL functions
├── docker/
│   ├── docker-compose.yml     # Multi-container orchestration
│   └── .env.docker            # Docker environment variables
├── README.md                  # Project documentation
└── PROJECT_STRUCTURE.md       # This file
```

---

## 🐍 Backend - Python FastAPI Application

### **Core Application Files**

#### `backend/app/main.py`
**Purpose:** FastAPI application entry point and lifecycle management

**Key Functions:**
- `lifespan()` - Async context manager for app lifecycle
  - Initializes Qdrant collections on startup
  - Starts background tasks (ingestion worker, monitor)
  - Cleans up on shutdown

**Endpoints:**
- `GET /` - Root endpoint with welcome message
- `GET /health` - Health check (PostgreSQL, Qdrant, Redis, MinIO)

**Background Tasks:**
- Ingestion Worker - Processes resume ingestion jobs from Redis queue
- Ingestion Monitor - Auto-healing for missing vectors (every 5 minutes)

**Dependencies:**
- FastAPI, Uvicorn
- app.api.* (all API routers)
- app.services.ingestion
- app.services.vector_store

**Called By:** Uvicorn server (`uvicorn app.main:app`)

---

#### `backend/app/config.py`
**Purpose:** Centralized configuration using Pydantic Settings

**Main Class:**
```python
class Settings(BaseSettings):
    # Environment
    debug: bool
    env: str

    # PostgreSQL
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    # Qdrant
    qdrant_host: str
    qdrant_port: int
    qdrant_collection: str
    qdrant_jobs_collection: str

    # Redis
    redis_host: str
    redis_port: int
    redis_password: str
    redis_db: int

    # MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_use_ssl: bool

    # AI Models
    embedding_model: str
    embedding_dim: int
    chunk_size: int
    chunk_overlap: int
    reranker_model: str
    openai_api_key: str

    # API Settings
    api_rate_limit: int
    max_file_size_mb: int

    @property
    def database_url(self) -> str
    @property
    def async_database_url(self) -> str
```

**Environment Variables:** Reads from `backend/.env`

**Used By:** All modules requiring configuration

---

#### `backend/app/database.py`
**Purpose:** SQLAlchemy async database connection management

**Key Components:**
- `engine` - AsyncEngine with connection pooling
- `AsyncSessionLocal` - Session factory for database transactions
- `Base` - Declarative base for ORM models
- `get_db()` - FastAPI dependency for injecting DB sessions

**Configuration:**
- Pool size: 10 connections
- Max overflow: 20 connections
- Pool recycle: 3600 seconds (1 hour)
- Pool pre-ping: True (health checks)

**Used By:** All API endpoints and services requiring database access

---

### **API Layer - `backend/app/api/`**

#### `backend/app/api/candidates.py`
**Purpose:** Candidate management endpoints

**Endpoints:**

**1. `POST /api/v1/candidates/upload-resume`**
- **Purpose:** Anonymous resume upload for parsing
- **Flow:**
  1. Validate file type (PDF/DOCX/TXT)
  2. Generate temp_id (UUID)
  3. Upload to MinIO
  4. Queue parse-only job in Redis
  5. Poll Redis for parsed result (30s timeout)
  6. Return parsed candidate data
- **Returns:** Candidate data for form pre-fill
- **Mode:** Parse-only (no database insertion)

**2. `POST /api/v1/candidates/`**
- **Purpose:** Create candidate profile with full ingestion
- **Flow:**
  1. Receive candidate data + temp_id
  2. Insert into PostgreSQL (candidate, contact, preferences, etc.)
  3. Queue full ingestion job
  4. Return candidate ID
- **Mode:** Full ingestion (embeddings, skills, vectors)

**Dependencies:**
- app.models.candidate (ORM models)
- app.services.s3_client (MinIO)
- app.services.redis_client (Queue)
- app.services.ingestion (Processing)

**Called By:** Frontend candidate upload flow

---

#### `backend/app/api/jobs.py`
**Purpose:** Job posting management and candidate ranking

**Endpoints:**

**1. `POST /api/v1/jobs/`**
- **Purpose:** Create job posting with AI fields
- **Flow:**
  1. Receive job data (title, description, required skills)
  2. Insert into PostgreSQL
  3. Generate job embeddings (profile + skills vectors)
  4. Store in Qdrant
  5. Return job ID

**2. `GET /api/v1/jobs/{job_id}/rank`**
- **Purpose:** Rank candidates for a specific job
- **Flow:**
  1. Fetch job details from PostgreSQL
  2. Generate job embeddings if not cached
  3. Semantic search in Qdrant (top N candidates)
  4. SQL filtering (must-have skills, experience)
  5. Structured scoring (experience match, completeness)
  6. Score blending (40% dense + 35% structured + 25% completeness)
  7. Candidate banding (High/Medium/Low)
  8. Generate explanations with evidence
  9. Return ranked candidate list
- **Returns:** Ranked candidates with scores, bands, explanations

**Dependencies:**
- app.services.ranking (Main ranking logic)
- app.services.job_embeddings (Job vector generation)
- app.services.vector_store (Qdrant)
- app.services.scoring (Structured scoring)
- app.services.explanations (Result explanations)

**Called By:** Frontend ranking dashboard

---

#### `backend/app/api/webhooks.py`
**Purpose:** External webhook handlers for Portal team integration

**Endpoints:**

**1. `POST /api/v1/webhooks/candidate-updated`**
- **Purpose:** Handle candidate profile updates from Portal
- **Flow:**
  1. Receive candidate_id from webhook
  2. Queue full re-ingestion job
  3. Return 202 Accepted
- **Mode:** Async processing via Redis queue

**2. `POST /api/v1/webhooks/job-ingestion`**
- **Purpose:** Handle new job postings from Portal
- **Flow:**
  1. Receive job_id
  2. Generate job embeddings
  3. Store in Qdrant
  4. Return 200 OK

**Dependencies:**
- app.services.redis_client
- app.services.job_embeddings

**Called By:** External Portal system (Portal team)

---

#### `backend/app/api/chat.py`
**Purpose:** WebSocket chatbot endpoint (PLACEHOLDER - Not fully implemented)

**Endpoints:**

**1. `WS /api/v1/jobs/{job_id}/chat`**
- **Purpose:** Job-scoped Q&A chatbot
- **Planned Flow:**
  1. Establish WebSocket connection
  2. Receive user query
  3. RAG pipeline: Retrieve relevant candidate chunks
  4. LLM generation with streaming
  5. Stream response tokens
  6. Close connection
- **Status:** Placeholder structure exists, needs implementation

**Dependencies (Planned):**
- app.services.chatbot
- app.services.retrieval
- app.services.vector_store

---

#### `backend/app/api/admin.py`
**Purpose:** Administrative endpoints and system diagnostics

**Endpoints:**

**1. `GET /api/v1/admin/stats`**
- **Purpose:** System statistics
- **Returns:** Candidate count, job count, vector count, queue depth

**2. `POST /api/v1/admin/reindex`**
- **Purpose:** Trigger re-indexing of all candidates
- **Flow:**
  1. Queue re-ingestion jobs for all candidates
  2. Return job count

**Dependencies:**
- app.database
- app.services.vector_store
- app.services.redis_client

**Called By:** Admin tools, monitoring systems

---

### **Models Layer - `backend/app/models/`**

#### `backend/app/models/candidate.py`
**Purpose:** SQLAlchemy ORM models for all database tables

**Main Classes:**

**1. `Candidate`**
- **Table:** `rightstaff.candidate`
- **Fields:** id (UUID PK), full_name, years_experience, professional_summary, created_at, updated_at
- **Relationships:**
  - contact (1:1 → CandidateContact)
  - preference (1:1 → CandidatePreference)
  - resumes (1:N → CandidateResume)
  - skills (M:N → Skill via candidate_skill)
  - applications (1:N → Application)

**2. `CandidateContact`**
- **Table:** `rightstaff.candidate_contact`
- **Fields:** candidate_id (PK, FK), email, phone, city, region, country
- **Relationship:** candidate (N:1 → Candidate)

**3. `CandidatePreference`**
- **Table:** `rightstaff.candidate_preference`
- **Fields:** candidate_id (PK, FK), work_authorization, work_arrangement, desired_salary_min/max, open_to_remote
- **Relationship:** candidate (N:1 → Candidate)

**4. `CandidateDemographics`**
- **Table:** `rightstaff.candidate_demographics`
- **Fields:** candidate_id (PK, FK), disability, ethnicity, veteran_status
- **Note:** Excluded from ranking for fairness

**5. `CandidateResume`**
- **Table:** `rightstaff.candidate_resume`
- **Fields:** id (UUID PK), candidate_id (FK), s3_url, file_type, is_latest, uploaded_at
- **Constraint:** UNIQUE partial index on (candidate_id) WHERE is_latest = true
- **Relationship:** candidate (N:1 → Candidate)

**6. `Skill`**
- **Table:** `rightstaff.skill`
- **Fields:** id (UUID PK), name (UNIQUE), parent_skill_id
- **Relationships:**
  - candidates (M:N → Candidate via candidate_skill)
  - synonyms (1:N → SkillSynonym)

**7. `CandidateSkill`**
- **Table:** `rightstaff.candidate_skill`
- **Fields:** candidate_id (PK, FK), skill_id (PK, FK), level, years
- **Relationships:**
  - candidate (N:1 → Candidate)
  - skill (N:1 → Skill)

**8. `Job`**
- **Table:** `rightstaff.job`
- **Fields:** id (UUID PK), title, description, department, location, status (enum), required_skills_json (JSONB), must_have_skills_json (JSONB), min_years_experience, max_years_experience, work_arrangement, employment_type, is_remote, visa_sponsorship_available, created_at, updated_at
- **Relationships:** applications (1:N → Application)

**9. `Application`**
- **Table:** `rightstaff.application`
- **Fields:** id (UUID PK), candidate_id (FK), job_id (FK), status (enum), applied_at, updated_at
- **Constraint:** UNIQUE (candidate_id, job_id)
- **Relationships:**
  - candidate (N:1 → Candidate)
  - job (N:1 → Job)

**Enums:**
- `JobStatus`: draft, open, on_hold, closed, filled
- `ApplicationStatus`: sourced, applied, screen, shortlist, interview, offer, hired, rejected, withdrawn

**Used By:** All API endpoints, services requiring database access

---

### **Services Layer - `backend/app/services/`**

#### `backend/app/services/ingestion.py`
**Purpose:** Resume ingestion pipeline - 8-stage processing

**Main Class:**
```python
class IngestionWorker:
    def __init__(self):
        # Initialize services

    async def start(self):
        # Main worker loop - BRPOP from Redis queue

    async def _process_job_with_tenacity(self, job_data: dict):
        # Wrapper with retry logic (Tenacity)
        # Max 5 retries with exponential backoff

    async def _process_job(self, job_data: dict):
        # Main processing logic (8 stages)
```

**8-Stage Pipeline:**

**Stage 1: Fetch Candidate Details**
- Query PostgreSQL for candidate data
- Get contact, preference, resume info

**Stage 2: Download Resume**
- Fetch from MinIO using s3_url
- Supports PDF, DOCX, TXT

**Stage 3: Parse Resume**
- Extract text from file
- Detect encoding (UTF-8, Latin-1, etc.)

**Stage 4: Extract Skills**
- Use OpenAI API or spaCy fallback
- Normalize skill names
- Store in PostgreSQL (candidate_skill table)

**Stage 5: Store Resume Record**
- Update candidate_resume table
- Mark as is_latest = true

**Stage 6: Chunk Resume Text**
- Split into chunks (400 chars, 50 char overlap)
- Prepare for embedding

**Stage 7: Generate Embeddings**
- Profile vector (full resume summary)
- Skills vector (concatenated skills)
- Chunk vectors (each text chunk)

**Stage 8: Store in Qdrant**
- Delete old vectors
- Upsert new vectors with payloads

**Modes:**
- `parse_only` - Parse and cache only (no DB insertion)
- `full` - Complete ingestion with embeddings

**Failure Handling:**
- Tenacity retry (max 5 attempts, exponential backoff)
- Dead Letter Queue (DLQ) for exhausted retries
- Full error logging with traceback

**Dependencies:**
- app.services.s3_client (MinIO)
- app.services.llm_parser (OpenAI)
- app.services.skill_extraction (spaCy)
- app.services.embeddings (sentence-transformers)
- app.services.vector_store (Qdrant)
- app.services.redis_client (Queue, Cache)

**Called By:**
- Background worker (main.py startup)
- Webhook handlers

---

#### `backend/app/services/ingestion_monitor.py`
**Purpose:** Auto-healing system for missing vectors

**Main Class:**
```python
class IngestionMonitor:
    def __init__(self):
        self.check_interval = 300  # 5 minutes

    async def start(self):
        # Infinite loop with periodic checks

    async def _check_missing_vectors(self):
        # Query PostgreSQL for candidates with resumes
        # Check Qdrant for missing vectors
        # Auto-queue re-ingestion jobs
```

**Check Logic:**
1. Query all candidates with `is_latest = true` resumes
2. For each candidate, check Qdrant for vectors
3. If missing, queue auto-heal job with prefix `auto_heal_{candidate_id}_{timestamp}`

**Run Frequency:** Every 5 minutes (configurable)

**Dependencies:**
- app.database
- app.services.vector_store
- app.services.redis_client

**Called By:** Background task in main.py

---

#### `backend/app/services/vector_store.py`
**Purpose:** Qdrant vector database client and operations

**Main Class:**
```python
class VectorStore:
    def __init__(self):
        self.client = QdrantClient(...)
        self.collection_name = "candidates_v1"
        self.jobs_collection_name = "jobs_v1"

    def initialize_collections(self):
        # Create collections if missing
        # Vector size: 384, Distance: Cosine

    def upsert_vectors(self, vectors, payloads):
        # Store candidate vectors with metadata

    def delete_by_candidate_id(self, candidate_id):
        # Remove all vectors for a candidate

    def search(self, query_vector, limit=50, filter=None):
        # Semantic search by cosine similarity

    def get_collection_info(self):
        # Return vector count, size stats
```

**Collections:**

**1. `candidates_v1`**
- Vector size: 384 dimensions
- Distance: Cosine similarity
- Payload: candidate_id, kind, full_name, text, skills, chunk_index, etc.

**2. `jobs_v1`**
- Vector size: 384 dimensions
- Distance: Cosine similarity
- Payload: job_id, title, kind, required_skills, must_have_skills

**Vector Point ID Generation:**
- Hash-based: `hash(f"{candidate_id}_{kind}_{chunk_index}")`
- Masked to positive 64-bit int

**Used By:**
- ingestion.py (storing vectors)
- ranking.py (searching vectors)
- ingestion_monitor.py (checking vectors)

---

#### `backend/app/services/embeddings.py`
**Purpose:** Generate semantic embeddings using sentence-transformers

**Main Class:**
```python
class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embedding_dim = 384

    def embed_text(self, text: str) -> List[float]:
        # Generate single embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Batch embedding for efficiency
```

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
- Dimension: 384
- Speed: Fast (local, no API calls)
- Quality: Good for semantic similarity

**Used By:**
- ingestion.py (candidate embeddings)
- job_embeddings.py (job embeddings)
- ranking.py (query embeddings)

---

#### `backend/app/services/job_embeddings.py`
**Purpose:** Generate and cache job embeddings

**Main Class:**
```python
class JobEmbeddingService:
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour

    async def get_or_create_embeddings(self, job_id: UUID) -> dict:
        # Check Redis cache
        # If miss, generate and cache

    async def _generate_embeddings(self, job: Job) -> dict:
        # Profile vector: title + description
        # Skills vector: must-have (3x) + nice-to-have
```

**Dual Embedding Strategy:**

**1. Profile Vector**
- Text: `{title}. {description}`
- Purpose: Capture overall job context

**2. Skills Vector**
- Text: Must-have skills repeated 3x + Required skills 1x
- Purpose: Emphasize critical skills
- Example: "Python Python Python FastAPI PostgreSQL Docker"

**Caching:**
- Redis key: `job_embeddings:{job_id}:{hash}`
- TTL: 1 hour
- Invalidation: On job update

**Used By:**
- ranking.py (fetching job embeddings)
- webhooks.py (pre-generating embeddings)

---

#### `backend/app/services/ranking.py`
**Purpose:** Main candidate ranking logic with hybrid scoring

**Main Function:**
```python
async def rank_candidates_for_job(
    job_id: UUID,
    db: AsyncSession,
    top_k: int = 50
) -> List[dict]:
    # 1. Fetch job details
    # 2. Get job embeddings
    # 3. Dense retrieval (Qdrant)
    # 4. SQL filtering (must-have skills)
    # 5. Structured scoring
    # 6. Score blending
    # 7. Banding (High/Medium/Low)
    # 8. Explanations
    # 9. Return ranked list
```

**Scoring Pipeline:**

**Step 1: Dense Retrieval**
- Search Qdrant with job profile vector
- Get top N candidates (typically 50)
- Score: Cosine similarity (0-1)

**Step 2: SQL Filtering**
- Filter by must-have skills (PostgreSQL JSONB)
- Apply experience range
- Check work authorization

**Step 3: Structured Scoring**
- Experience match: |candidate_exp - job_exp| / job_max_exp
- Profile completeness: Has resume, skills, contact info
- Location match: City/region overlap

**Step 4: Score Blending**
```python
final_score = (
    0.40 * dense_score +
    0.35 * structured_score +
    0.25 * completeness_score
)
```

**Step 5: Candidate Banding**
- High: Top 20% (score ≥ P80)
- Medium: 20-60% (P40 ≤ score < P80)
- Low: Bottom 40% (score < P40)

**Step 6: Explanations**
- Extract evidence from resume chunks
- Cite skill matches
- Note experience alignment

**Dependencies:**
- app.services.job_embeddings
- app.services.vector_store
- app.services.scoring
- app.services.sql_filters
- app.services.explanations

**Called By:** API endpoint `GET /api/v1/jobs/{job_id}/rank`

---

#### `backend/app/services/scoring.py`
**Purpose:** Structured scoring calculations

**Main Functions:**

**1. `calculate_experience_score(candidate_years, min_years, max_years)`**
- Returns 0-1 score
- Penalizes under-qualified and over-qualified

**2. `calculate_completeness_score(candidate)`**
- Checks: Has resume, has skills, has contact info
- Returns proportion of fields completed

**3. `calculate_location_score(candidate_city, job_location)`**
- Fuzzy string matching
- Returns 0-1 similarity

**Used By:** ranking.py

---

#### `backend/app/services/sql_filters.py`
**Purpose:** SQL-based candidate filtering

**Main Function:**
```python
async def filter_candidates(
    db: AsyncSession,
    must_have_skills: List[str],
    min_years: float,
    max_years: float
) -> List[UUID]:
    # Build dynamic SQL query
    # JSONB @> operator for skills
    # Return candidate IDs
```

**Query Logic:**
- Uses PostgreSQL JSONB containment (`@>`)
- Applies experience range
- Returns only matching candidate UUIDs

**Used By:** ranking.py

---

#### `backend/app/services/explanations.py`
**Purpose:** Generate human-readable explanations for ranking results

**Main Function:**
```python
def generate_explanation(
    candidate: dict,
    job: dict,
    scores: dict
) -> dict:
    # Analyze skill overlap
    # Extract evidence from resume chunks
    # Build explanation text
    # Return structured explanation
```

**Explanation Components:**
- **Skill Match:** "Has 8/10 required skills (Python, FastAPI, PostgreSQL...)"
- **Experience:** "5 years experience matches job requirement (3-7 years)"
- **Evidence:** Resume chunk citations with highlighted skills
- **Band Reason:** "High confidence - strong match on critical skills"

**Used By:** ranking.py

---

#### `backend/app/services/skill_extraction.py`
**Purpose:** Extract skills from resume text using NLP

**Main Functions:**

**1. `extract_skills_openai(text: str) -> List[str]`**
- Use OpenAI GPT-4 to extract skills
- Structured JSON output
- Fallback to spaCy on failure

**2. `extract_skills_spacy(text: str) -> List[str]`**
- Use spaCy NER and pattern matching
- 400+ technical skill patterns
- Taxonomy normalization (Python3 → Python)

**Skill Patterns:**
- Programming languages: Python, Java, JavaScript, etc.
- Frameworks: React, FastAPI, Django, etc.
- Databases: PostgreSQL, MongoDB, Redis, etc.
- Cloud: AWS, Azure, GCP, Docker, Kubernetes
- Tools: Git, CI/CD, Terraform, etc.

**Used By:** ingestion.py

---

#### `backend/app/services/parsers.py`
**Purpose:** Extract text from resume files (PDF, DOCX, TXT)

**Main Functions:**

**1. `parse_pdf(file_bytes: bytes) -> str`**
- Use pypdf library
- Extract all pages
- Handle encrypted PDFs

**2. `parse_docx(file_bytes: bytes) -> str`**
- Use python-docx library
- Extract paragraphs and tables

**3. `parse_txt(file_bytes: bytes) -> str`**
- Detect encoding (chardet)
- Handle UTF-8, Latin-1, CP1252, etc.

**Used By:** ingestion.py

---

#### `backend/app/services/llm_parser.py`
**Purpose:** Use OpenAI GPT-4 to parse resume into structured data

**Main Function:**
```python
async def parse_resume_with_llm(text: str) -> dict:
    # Prompt: "Extract candidate info from resume"
    # Returns: {name, email, phone, experience, education, skills}
```

**Prompt Template:**
```
Extract the following from this resume:
- Full name
- Email
- Phone number
- Years of experience
- Education (degree, institution, year)
- Top skills (list)

Resume:
{text}

Return JSON format.
```

**Fallback:** spaCy-based extraction if API fails

**Used By:** ingestion.py (parse-only mode)

---

#### `backend/app/services/s3_client.py`
**Purpose:** MinIO (S3-compatible) client for resume storage

**Main Class:**
```python
class S3Client:
    def __init__(self):
        self.client = Minio(...)
        self.bucket_name = "rightstaff-resumes"
        self._ensure_bucket_exists()

    async def upload_file(self, file_data: bytes, object_name: str, content_type: str) -> str:
        # Upload to MinIO
        # Return s3:// URL

    async def download_file(self, object_name: str) -> bytes:
        # Download from MinIO
        # Return file bytes

    async def delete_file(self, object_name: str):
        # Remove file from bucket
```

**Bucket:** `rightstaff-resumes`
**Path Structure:** `resumes/{candidate_id}/resume.{ext}`

**Used By:**
- candidates.py (upload endpoint)
- ingestion.py (download for processing)

---

#### `backend/app/services/redis_client.py`
**Purpose:** Redis client for queue and cache operations

**Main Class:**
```python
class RedisClient:
    def __init__(self):
        self.client = redis.asyncio.Redis(...)

    async def lpush(self, queue_name: str, data: str):
        # Push to left (front of queue)

    async def brpop(self, queue_name: str, timeout: int):
        # Blocking pop from right (FIFO)

    async def push_dlq(self, data: str):
        # Push to dead letter queue

    async def set(self, key: str, value: str, ex: int):
        # Set with TTL

    async def get(self, key: str) -> str:
        # Get cached value
```

**Queues:**
- `ingestion_queue` - Main job queue
- `ingestion_queue_dlq` - Dead letter queue

**Cache Keys:**
- `parsed_candidate:{temp_id}` (TTL: 1 hour)
- `job_embeddings:{job_id}:{hash}` (TTL: 1 hour)

**Used By:**
- ingestion.py (queue operations)
- candidates.py (cache operations)
- job_embeddings.py (cache operations)

---

#### `backend/app/services/reranker.py`
**Purpose:** Cross-encoder re-ranking (PLACEHOLDER - Not fully implemented)

**Planned Functionality:**
```python
class Reranker:
    def __init__(self):
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def rerank(self, query: str, candidates: List[dict]) -> List[dict]:
        # Pairwise scoring: (query, candidate) → score
        # Sort by cross-encoder score
        # Return re-ranked list
```

**Status:** Placeholder file exists, not integrated into ranking pipeline

**Used By:** None yet (planned for ranking.py)

---

#### `backend/app/services/chatbot.py`
**Purpose:** RAG-based chatbot (PLACEHOLDER - Not fully implemented)

**Planned Class:**
```python
class Chatbot:
    def __init__(self):
        self.retriever = Retriever()
        self.llm = OpenAI()

    async def chat(self, query: str, job_id: UUID) -> AsyncGenerator[str, None]:
        # 1. Retrieve relevant candidate chunks
        # 2. Build context
        # 3. LLM generation with streaming
        # 4. Yield tokens
```

**Status:** Placeholder file exists, not connected to API

**Used By:** None yet (planned for chat.py WebSocket endpoint)

---

#### `backend/app/services/retrieval.py`
**Purpose:** RAG retrieval logic (PLACEHOLDER)

**Planned Functionality:**
- Query expansion
- Multi-vector retrieval
- Context ranking
- Chunk aggregation

**Status:** Placeholder, not implemented

---

#### `backend/app/services/ontology.py`
**Purpose:** Skill taxonomy and normalization

**Main Data:**
```python
SKILL_ONTOLOGY = {
    "Python": ["Python3", "Python 3", "py"],
    "JavaScript": ["JS", "ECMAScript", "Node.js"],
    "PostgreSQL": ["Postgres", "psql"],
    # ... 400+ skill mappings
}
```

**Main Functions:**

**1. `normalize_skill(skill: str) -> str`**
- Map variants to canonical form
- Example: "Python3" → "Python"

**2. `expand_skill(skill: str) -> List[str]`**
- Return all variants
- Example: "Python" → ["Python", "Python3", "py"]

**Used By:**
- skill_extraction.py (normalizing extracted skills)
- sql_filters.py (matching skills in queries)

---

#### `backend/app/services/metrics.py`
**Purpose:** Performance metrics and logging

**Main Functions:**

**1. `log_ranking_latency(duration: float)`**
- Record ranking response time
- Calculate P50, P95, P99

**2. `log_embedding_latency(duration: float)`**
- Record embedding generation time

**3. `log_fairness_metrics(results: List[dict])`**
- Check for demographic bias
- Calculate disparity metrics

**Used By:**
- ranking.py (performance tracking)
- admin.py (metrics dashboard)

---

### **Utils Layer - `backend/app/utils/`**

#### `backend/app/utils/logging.py`
**Purpose:** Structured logging with PII redaction

**Main Functions:**

**1. `setup_logging()`**
- Configure structlog
- JSON output format
- Context binding

**2. `redact_pii(event_dict: dict) -> dict`**
- Remove sensitive fields
- Patterns: password, token, api_key, email, phone

**Logger Features:**
- Structured JSON logs
- Timestamp (ISO 8601)
- Log level (info, warning, error)
- Context binding (request_id, user_id)
- PII redaction

**Used By:** All modules

---

### **Backend Utility Scripts**

#### `backend/clear_all_data.py`
**Purpose:** Clear all data from PostgreSQL, Qdrant, Redis, MinIO

**Main Function:**
```python
async def clear_all():
    await clear_postgresql()  # Delete all tables
    await clear_minio()       # Remove all objects
    await clear_qdrant()      # Delete collections
    await clear_redis()       # Flush database
```

**Warning:** Destructive operation with 3-second countdown

**Used By:** Manual execution for testing/development

---

#### `backend/populate_dummy_data.py`
**Purpose:** Generate comprehensive test data

**Main Function:**
```python
async def main():
    # 1. Create skills (49 total)
    # 2. Create jobs (6 jobs with diverse requirements)
    # 3. Create candidates (8 candidates with varied profiles)
    # 4. Generate resume PDFs
    # 5. Upload resumes to MinIO
    # 6. Generate embeddings
    # 7. Store vectors in Qdrant
    # 8. Create applications (48 total)
    # 9. Summary report
```

**Test Data:**
- 6 jobs (Python Engineer, Full-Stack, Data Engineer, etc.)
- 8 candidates with realistic profiles
- 49 skills across tech domains
- 5 resume PDFs (3 candidates without resumes for testing)
- 24 vectors in Qdrant (profile + skills + chunks)
- 48 job applications

**Used By:** Manual execution after database setup

---

#### `backend/check_database.py`
**Purpose:** Verify database state

**Main Function:**
```python
async def check():
    # Count applications
    # Count jobs
    # Count candidates
    # Show applications per job
```

**Output Example:**
```
Applications: 48
Jobs: 6
Candidates: 8
Job "Senior Python Engineer": 8 applications
Job "Full-Stack Engineer": 8 applications
...
```

**Used By:** Manual verification after data population

---

## ⚛️ Frontend - React TypeScript Application

### **API Layer - `frontend/src/api/`**

#### `frontend/src/api/client.ts`
**Purpose:** Axios HTTP client configuration

**Exports:**
```typescript
const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  }
});

export default apiClient;
```

**Used By:** All API service files

---

#### `frontend/src/api/candidates.ts`
**Purpose:** Candidate API client functions

**Main Functions:**

**1. `uploadResume(file: File): Promise<CandidateData>`**
- POST /api/v1/candidates/upload-resume
- FormData with multipart/form-data
- Returns parsed candidate data

**2. `createCandidate(data: CandidateInput): Promise<Candidate>`**
- POST /api/v1/candidates/
- Returns created candidate with UUID

**Used By:**
- components/candidate/ResumeUpload.tsx
- components/candidate/CandidateForm.tsx

---

#### `frontend/src/api/jobs.ts`
**Purpose:** Job API client functions

**Main Functions:**

**1. `createJob(data: JobInput): Promise<Job>`**
- POST /api/v1/jobs/
- Returns created job with UUID

**2. `rankCandidates(jobId: string): Promise<RankedCandidate[]>`**
- GET /api/v1/jobs/{jobId}/rank
- Returns ranked candidate list with scores

**Used By:**
- components/recruiter/JobForm.tsx
- components/recruiter/RankingDashboard.tsx

---

#### `frontend/src/api/chat.ts`
**Purpose:** WebSocket chat client (PLACEHOLDER)

**Planned Functions:**
```typescript
function connectChatSocket(jobId: string): WebSocket;
function sendMessage(ws: WebSocket, message: string): void;
```

**Status:** Not implemented

---

### **Components - `frontend/src/components/`**

#### **Candidate Components**

**1. `components/candidate/ResumeUpload.tsx`**
- **Purpose:** Drag-and-drop resume upload
- **Features:**
  - File validation (PDF, DOCX, TXT)
  - Size limit check (5MB)
  - Upload progress indicator
  - Error handling
- **State:** Uses Zustand candidateStore
- **API Calls:** `uploadResume()`

**2. `components/candidate/CandidateForm.tsx`**
- **Purpose:** Candidate profile form with pre-filled data
- **Features:**
  - React Hook Form with Zod validation
  - Pre-populated from parsed resume
  - Editable fields (name, email, skills, experience)
  - Submit to create candidate
- **State:** Uses Zustand candidateStore
- **API Calls:** `createCandidate()`

**3. `components/candidate/CandidateCard.tsx`**
- **Purpose:** Display candidate profile summary
- **Props:** `candidate: Candidate`
- **Features:**
  - Avatar with initials
  - Name, experience, location
  - Skills badges
  - View details button

---

#### **Recruiter Components**

**1. `components/recruiter/JobForm.tsx`**
- **Purpose:** Create job posting form
- **Features:**
  - React Hook Form with validation
  - Rich text editor for description
  - Multi-select for required skills
  - Experience range inputs
  - Work arrangement checkboxes
- **State:** Uses Zustand recruiterStore
- **API Calls:** `createJob()`

**2. `components/recruiter/RankingDashboard.tsx`**
- **Purpose:** Job selection and ranking trigger
- **Features:**
  - Job dropdown selector
  - "Rank Candidates" button
  - Loading state
  - Error handling
- **State:** Uses Zustand recruiterStore
- **API Calls:** `rankCandidates()`

**3. `components/recruiter/RankingResults.tsx`**
- **Purpose:** Display ranked candidate list
- **Props:** `results: RankedCandidate[]`
- **Features:**
  - Candidate cards with scores
  - Banding badges (High/Medium/Low)
  - Explanation tooltips
  - Skill match indicators
  - Evidence citations
  - Sort options (score, experience, name)

---

#### **Shared Components**

**1. `components/shared/Button.tsx`**
- **Purpose:** Reusable button component
- **Variants:** primary, secondary, danger, ghost
- **Sizes:** sm, md, lg

**2. `components/shared/Input.tsx`**
- **Purpose:** Styled input field
- **Features:** Label, error message, placeholder

**3. `components/shared/Select.tsx`**
- **Purpose:** Dropdown select component
- **Features:** Multi-select support, search filtering

**4. `components/shared/Card.tsx`**
- **Purpose:** Container card with elevation
- **Props:** children, title, footer

---

### **Pages - `frontend/src/pages/`**

#### `pages/CandidatePage.tsx`
**Purpose:** Main candidate flow page

**Layout:**
```
┌─────────────────────────────────────┐
│       Resume Upload Component        │
├─────────────────────────────────────┤
│     Candidate Form Component         │
│    (appears after upload)            │
└─────────────────────────────────────┘
```

**Flow:**
1. Upload resume → Parse
2. Pre-fill form with parsed data
3. Edit and submit
4. Navigate to success page

---

#### `pages/RecruiterPage.tsx`
**Purpose:** Recruiter dashboard with job management and ranking

**Layout:**
```
┌────────────────┬────────────────────┐
│  Job Form      │  Ranking Dashboard │
│                │                    │
│  Create Job    │  Select Job        │
│                │  Rank Candidates   │
├────────────────┴────────────────────┤
│     Ranking Results                 │
│  (appears after ranking)            │
└─────────────────────────────────────┘
```

**Flow:**
1. Create job → Generate embeddings
2. Select job → Trigger ranking
3. View ranked results with explanations

---

### **State Management - `frontend/src/store/`**

#### `store/candidateStore.ts`
**Purpose:** Zustand store for candidate state

**State:**
```typescript
interface CandidateStore {
  uploadedFile: File | null;
  parsedData: CandidateData | null;
  isUploading: boolean;
  isSubmitting: boolean;
  error: string | null;

  setUploadedFile: (file: File) => void;
  setParsedData: (data: CandidateData) => void;
  uploadResume: (file: File) => Promise<void>;
  submitCandidate: (data: CandidateInput) => Promise<void>;
  reset: () => void;
}
```

**Used By:** Candidate components

---

#### `store/recruiterStore.ts`
**Purpose:** Zustand store for recruiter state

**State:**
```typescript
interface RecruiterStore {
  jobs: Job[];
  selectedJobId: string | null;
  rankedCandidates: RankedCandidate[];
  isRanking: boolean;
  error: string | null;

  setJobs: (jobs: Job[]) => void;
  setSelectedJob: (jobId: string) => void;
  createJob: (data: JobInput) => Promise<void>;
  rankCandidates: (jobId: string) => Promise<void>;
  reset: () => void;
}
```

**Used By:** Recruiter components

---

### **Types - `frontend/src/types/`**

#### `types/index.ts`
**Purpose:** TypeScript type definitions

**Main Types:**

```typescript
interface Candidate {
  id: string;
  full_name: string;
  email: string;
  years_experience: number;
  skills: string[];
  created_at: string;
}

interface Job {
  id: string;
  title: string;
  description: string;
  required_skills: string[];
  must_have_skills: string[];
  min_years_experience: number;
  max_years_experience: number;
  status: JobStatus;
}

interface RankedCandidate {
  candidate: Candidate;
  score: number;
  band: 'High' | 'Medium' | 'Low';
  explanation: string;
  skill_matches: string[];
  evidence: string[];
}

type JobStatus = 'draft' | 'open' | 'on_hold' | 'closed' | 'filled';
type ApplicationStatus = 'sourced' | 'applied' | 'screen' | 'shortlist' | 'interview' | 'offer' | 'hired' | 'rejected' | 'withdrawn';
```

**Used By:** All TypeScript files

---

## 🗄️ Database - SQL Scripts

### `database/scripts/01_schema.sql`
**Purpose:** PostgreSQL database schema (REQUIRED)

**What it creates:**
- Extensions: pgcrypto, citext
- Schema: `rightstaff`
- Role: `right_staff` with permissions
- Enums: job_status_enum, application_status_enum, etc.
- Tables: All 15+ tables with relationships
- Indexes: Performance indexes on common queries
- Triggers: Auto-update `updated_at` timestamps
- Functions: `touch_updated_at()`

**Run When:** Docker container first starts (auto-executed via `/docker-entrypoint-initdb.d/`)

**Status:** ✅ Complete and correct (includes `is_remote`, `visa_sponsorship_available`)

---

### `database/scripts/00_rollback.sql`
**Purpose:** Drop all tables and schema (destructive)

**What it does:**
- Drop all tables in correct order (respecting foreign keys)
- Drop all custom types (enums)
- Drop schema `rightstaff`
- Drop role `right_staff`

**Run When:** Manual execution for complete reset

---

### `database/scripts/03_postseed_helpers.sql`
**Purpose:** Helper SQL functions

**Functions:**

**1. `set_latest_resume(candidate_id UUID, resume_id UUID)`**
- Mark specified resume as latest
- Set all others as not latest
- Ensures only one `is_latest = true` per candidate

**Run When:** After schema creation (optional utilities)

---

## 🐳 Docker Configuration

### `docker/docker-compose.yml`
**Purpose:** Multi-container orchestration

**Services:**

**1. postgres**
- Image: postgres:18-alpine
- Port: 5433 (mapped to 5432 internally)
- Volume: rightstaff-postgres-data (persistent)
- Volume: ../database/scripts (init scripts)
- Health check: pg_isready
- Environment: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

**2. qdrant**
- Image: qdrant/qdrant:v1.7.0
- Ports: 6333 (HTTP), 6334 (gRPC)
- Volume: ../data/qdrant
- Restart: unless-stopped

**3. redis**
- Image: redis:7.2-alpine
- Port: 6379
- Volume: ../data/redis
- Command: redis-server --appendonly yes --requirepass {password}
- Health check: redis-cli ping

**4. minio**
- Image: minio/minio:latest
- Ports: 9000 (API), 9001 (Console)
- Volume: ../data/minio
- Command: server /data --console-address ":9001"
- Environment: MINIO_ROOT_USER, MINIO_ROOT_PASSWORD
- Health check: curl health endpoint

**Network:** rightstaff-network (bridge)

---

### `docker/.env.docker`
**Purpose:** Docker environment variables

**Variables:**
```env
POSTGRES_PASSWORD=dev_password_123
REDIS_PASSWORD=dev_redis_123
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
```

**Note:** Defaults are used if not specified

---

## 🔄 Workflows and Interactions

### **Workflow 1: Resume Upload & Candidate Creation**

```
┌─────────────────────────────────────────────────────────────────┐
│                  CANDIDATE UPLOAD WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

1. User Action: Upload Resume
   Frontend: ResumeUpload.tsx
      ↓ uploadResume(file)
   API Client: candidates.ts
      ↓ POST /api/v1/candidates/upload-resume
   Backend: candidates.py
      ↓
   a) Validate file (PDF/DOCX/TXT)
   b) Generate temp_id (UUID)
   c) Upload to MinIO (s3_client.py)
   d) Queue parse job (redis_client.py)
      ↓
   Background Worker: ingestion.py
   e) Download from MinIO
   f) Parse with LLM (llm_parser.py) or spaCy
   g) Cache result in Redis (1 hour TTL)
   h) Return to API
      ↓
   API Response: Parsed candidate data
      ↓
   Frontend: Update candidateStore.parsedData

2. User Action: Fill Form & Submit
   Frontend: CandidateForm.tsx (pre-filled)
      ↓ submitCandidate(formData)
   API Client: candidates.ts
      ↓ POST /api/v1/candidates/
   Backend: candidates.py
      ↓
   a) Insert Candidate (database.py)
   b) Insert CandidateContact
   c) Insert CandidatePreference
   d) Queue full ingestion job
      ↓
   Background Worker: ingestion.py
   e) Fetch candidate details
   f) Download resume
   g) Parse text
   h) Extract skills (skill_extraction.py)
   i) Store skills in PostgreSQL
   j) Chunk text (400 chars, 50 overlap)
   k) Generate embeddings (embeddings.py)
   l) Store vectors in Qdrant (vector_store.py)
      ↓
   API Response: Candidate ID
      ↓
   Frontend: Navigate to success page
```

---

### **Workflow 2: Job Creation & Ranking**

```
┌─────────────────────────────────────────────────────────────────┐
│                    JOB RANKING WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘

1. Recruiter Action: Create Job
   Frontend: JobForm.tsx
      ↓ createJob(jobData)
   API Client: jobs.ts
      ↓ POST /api/v1/jobs/
   Backend: jobs.py
      ↓
   a) Insert Job (database.py)
   b) Generate job embeddings (job_embeddings.py)
      - Profile vector: title + description
      - Skills vector: must-have (3x) + required
   c) Store in Qdrant (vector_store.py)
   d) Cache in Redis (1 hour TTL)
      ↓
   API Response: Job ID
      ↓
   Frontend: Update recruiterStore.jobs

2. Recruiter Action: Rank Candidates
   Frontend: RankingDashboard.tsx
      ↓ rankCandidates(jobId)
   API Client: jobs.ts
      ↓ GET /api/v1/jobs/{jobId}/rank
   Backend: ranking.py
      ↓

   STAGE 1: Dense Retrieval
   a) Get job embeddings (job_embeddings.py)
   b) Search Qdrant (vector_store.py)
      - Query: job profile vector
      - Limit: 50 candidates
      - Score: Cosine similarity

   STAGE 2: SQL Filtering
   c) Filter by must-have skills (sql_filters.py)
   d) Apply experience range

   STAGE 3: Structured Scoring
   e) Calculate experience score (scoring.py)
   f) Calculate completeness score
   g) Calculate location score

   STAGE 4: Score Blending
   h) Combine scores:
      final = 0.40*dense + 0.35*structured + 0.25*completeness

   STAGE 5: Banding
   i) Calculate percentiles (P40, P80)
   j) Assign bands: High (top 20%), Medium (20-60%), Low (40%+)

   STAGE 6: Explanations
   k) Extract evidence (explanations.py)
   l) Cite skill matches
   m) Note experience alignment
      ↓
   API Response: Ranked candidates with scores, bands, explanations
      ↓
   Frontend: RankingResults.tsx
   - Display ranked list
   - Show scores and bands
   - Display explanations and evidence
```

---

### **Workflow 3: Auto-Healing (Background)**

```
┌─────────────────────────────────────────────────────────────────┐
│              AUTO-HEALING MONITOR WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

Every 5 Minutes:

Background Task: ingestion_monitor.py
   ↓ _check_missing_vectors()

1. Query PostgreSQL (database.py)
   - SELECT all candidates with is_latest = true resumes

2. For each candidate:
   a) Check Qdrant (vector_store.py)
   b) Search for vectors with candidate_id

3. If vectors missing:
   a) Log warning
   b) Generate job ID: auto_heal_{candidate_id}_{timestamp}
   c) Queue re-ingestion job (redis_client.py)
      ↓
4. Ingestion Worker picks up job
   - Full ingestion pipeline
   - Generates embeddings
   - Stores in Qdrant

Result: Self-healing system repairs missing vectors
```

---

### **Workflow 4: Webhook Integration**

```
┌─────────────────────────────────────────────────────────────────┐
│                 WEBHOOK INTEGRATION WORKFLOW                     │
└─────────────────────────────────────────────────────────────────┘

External System (Portal Team):
   ↓ POST /api/v1/webhooks/candidate-updated

Backend: webhooks.py
   ↓
1. Receive candidate_id
2. Validate request
3. Queue re-ingestion job (redis_client.py)
   ↓
4. Return 202 Accepted (async processing)
   ↓

Background Worker: ingestion.py
5. Process re-ingestion
   - Download updated resume
   - Re-extract skills
   - Regenerate embeddings
   - Update Qdrant vectors

Result: Candidate profile updated with latest data
```

---

## 📋 File Dependencies Summary

### **High-Level Module Dependencies**

```
┌────────────────────────────────────────────────────────────────┐
│                      DEPENDENCY GRAPH                           │
└────────────────────────────────────────────────────────────────┘

main.py
  ├─→ api.candidates
  │     ├─→ services.s3_client
  │     ├─→ services.redis_client
  │     ├─→ services.ingestion
  │     └─→ models.candidate
  ├─→ api.jobs
  │     ├─→ services.ranking
  │     ├─→ services.job_embeddings
  │     └─→ models.candidate
  ├─→ api.webhooks
  │     ├─→ services.redis_client
  │     └─→ services.job_embeddings
  └─→ services.ingestion (background)
        ├─→ services.s3_client
        ├─→ services.parsers
        ├─→ services.llm_parser
        ├─→ services.skill_extraction
        ├─→ services.embeddings
        ├─→ services.vector_store
        └─→ services.redis_client

services.ranking
  ├─→ services.job_embeddings
  ├─→ services.vector_store
  ├─→ services.scoring
  ├─→ services.sql_filters
  └─→ services.explanations

services.vector_store
  └─→ config (settings)

services.embeddings
  └─→ config (model settings)

All modules
  └─→ utils.logging
```

---

## 🎯 Key Takeaways

### **Critical Files (Cannot Remove)**
1. `backend/app/main.py` - Application entry point
2. `backend/app/config.py` - Configuration
3. `backend/app/database.py` - Database connection
4. `backend/app/models/candidate.py` - ORM models
5. `backend/app/services/ingestion.py` - Resume processing
6. `backend/app/services/ranking.py` - Candidate ranking
7. `backend/app/services/vector_store.py` - Qdrant client
8. `database/scripts/01_schema.sql` - Database schema

### **Optional/Enhancement Files**
1. `backend/app/services/reranker.py` - Cross-encoder (placeholder)
2. `backend/app/services/chatbot.py` - RAG chatbot (placeholder)
3. `backend/app/api/chat.py` - WebSocket endpoint (placeholder)

### **Development Utilities**
1. `backend/clear_all_data.py` - Database reset
2. `backend/populate_dummy_data.py` - Test data
3. `backend/check_database.py` - Verification

---

**Document Version:** 1.0
**Last Updated:** 2026-01-28
**Maintainer:** RightStaff Development Team

---

For questions or updates, refer to the main [README.md](./README.md).
