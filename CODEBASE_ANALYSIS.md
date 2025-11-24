# RightStaff Codebase Comprehensive Analysis Report

## Executive Summary

RightStaff is an AI-powered candidate ranking and matching system built with:
- **Backend**: FastAPI (Python) with async support
- **Frontend**: React + TypeScript
- **Databases**: PostgreSQL, Qdrant (vector DB), Redis (cache/queue), MinIO (file storage)
- **Architecture**: Microservices-like with background worker pattern
- **ML Components**: Sentence transformers for embeddings, cross-encoders for re-ranking, spaCy/LLM for NER

---

## 1. DIRECTORY STRUCTURE

```
RightStaff/
├── backend/                          # Python FastAPI application
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── config.py                # Settings management
│   │   ├── database.py              # SQLAlchemy async setup
│   │   ├── api/                     # REST API endpoints
│   │   │   ├── webhooks.py          # Webhook handlers
│   │   │   ├── candidates.py        # Candidate operations
│   │   │   ├── jobs.py              # Job operations & ranking
│   │   │   ├── chat.py              # WebSocket chatbot
│   │   │   └── admin.py             # Admin/monitoring
│   │   ├── models/
│   │   │   └── candidate.py         # SQLAlchemy ORM models
│   │   ├── services/                # Business logic
│   │   │   ├── ingestion.py         # Background worker & pipeline
│   │   │   ├── ranking.py           # Main ranking orchestration
│   │   │   ├── embeddings.py        # Text → vectors
│   │   │   ├── job_embeddings.py    # Job-specific embeddings
│   │   │   ├── vector_store.py      # Qdrant client
│   │   │   ├── retrieval.py         # Dense semantic search
│   │   │   ├── reranker.py          # Cross-encoder re-ranking
│   │   │   ├── scoring.py           # Structured scoring
│   │   │   ├── explanation.py       # Ranking explanations
│   │   │   ├── parsers.py           # Resume parsing
│   │   │   ├── skill_extractor.py   # Unified skill extraction
│   │   │   ├── llm_parser.py        # LLM-based field extraction
│   │   │   ├── ontology.py          # Skills taxonomy & normalization
│   │   │   ├── sql_filter.py        # SQL-based filtering gates
│   │   │   ├── redis_client.py      # Redis async wrapper
│   │   │   ├── s3_client.py         # MinIO async wrapper
│   │   │   ├── metrics.py           # Observability metrics
│   │   │   └── chatbot_langgraph.py # RAG chatbot with LangGraph
│   │   └── utils/
│   │       └── logging.py           # Structured logging
│   ├── tests/                       # Unit & integration tests
│   └── feature_tests/               # Feature-level tests
├── frontend/                        # React + TypeScript
│   ├── src/
│   │   ├── App.tsx                  # Main component
│   │   ├── index.tsx                # React entry point
│   │   ├── pages/                   # Page components
│   │   │   ├── RecruiterDashboard.tsx
│   │   │   └── CandidatePortal.tsx
│   │   ├── components/
│   │   │   ├── recruiter/          # Recruiter UI
│   │   │   │   ├── JobForm.tsx
│   │   │   │   ├── CandidateRanking.tsx
│   │   │   │   └── Chatbot.tsx
│   │   │   ├── candidate/          # Candidate UI
│   │   │   │   ├── ResumeUpload.tsx
│   │   │   │   ├── CandidateForm.tsx
│   │   │   │   └── JobList.tsx
│   │   │   └── shared/             # Shared components
│   │   │       ├── Navbar.tsx
│   │   │       ├── Loading.tsx
│   │   │       └── ErrorBoundary.tsx
│   │   ├── api/                    # API clients
│   │   │   ├── client.ts           # Axios configuration
│   │   │   ├── candidates.ts       # Candidate API calls
│   │   │   ├── jobs.ts             # Job API calls
│   │   │   └── chat.ts             # Chat API calls
│   │   ├── store/                  # State management
│   │   │   ├── candidateStore.ts
│   │   │   └── recruiterStore.ts
│   │   └── types/
│   │       └── index.ts            # TypeScript interfaces
├── database/                        # Schema migration scripts
├── docker/                          # Docker configuration
└── scripts/                         # Helper scripts
```

---

## 2. DATABASE MODELS & RELATIONSHIPS

### **PostgreSQL Schema** (rightstaff schema)

#### **Core Models**

##### **Candidate** (Recruiter & Candidate Data)
- **Table**: `candidate`
- **Fields**:
  - `id` (UUID, PK): Unique identifier
  - `full_name` (Text): Candidate's name
  - `years_experience` (Numeric): Total years in field
  - `professional_summary` (Text): Career overview
  - `created_at` (DateTime): Record creation timestamp
  - `updated_at` (DateTime): Last update timestamp
- **Relationships**:
  - `contact` (1:1) → CandidateContact
  - `resumes` (1:N) → CandidateResume
  - `skills` (M:N) → Skill via CandidateSkill
  - `applications` (1:N) → Application

##### **CandidateContact** (Contact Information)
- **Table**: `candidate_contact`
- **Fields**:
  - `candidate_id` (UUID, FK, PK): Reference to candidate
  - `email` (String): Email address
  - `phone` (String): Phone number
  - `address_line1`, `address_line2` (Text): Street address
  - `city` (Text): City
  - `region` (Text): State/Province (e.g., "WA")
  - `postal_code` (String): ZIP/Postal code
  - `country` (String): Country
- **Relationships**:
  - `candidate` (1:1) → Candidate

##### **CandidateResume** (Resume File Metadata)
- **Table**: `candidate_resume`
- **Fields**:
  - `id` (UUID, PK): Unique resume ID
  - `candidate_id` (UUID, FK): Reference to candidate
  - `s3_url` (Text): MinIO URL where file is stored
  - `file_type` (String): "pdf", "docx", "txt"
  - `is_latest` (Boolean): Is this the current resume?
  - `uploaded_at` (DateTime): Upload timestamp
- **Relationships**:
  - `candidate` (N:1) → Candidate

##### **Skill** (Ontology/Taxonomy)
- **Table**: `skill`
- **Fields**:
  - `id` (UUID, PK): Unique skill ID
  - `name` (Text, UNIQUE): Canonical skill name (e.g., "Python")
  - `parent_skill_id` (UUID, FK, nullable): Parent skill for hierarchy
- **Relationships**:
  - Self-referential for skill hierarchy
  - `candidates` (M:N) → Candidate via CandidateSkill

##### **CandidateSkill** (Many-to-Many: Candidate ↔ Skill)
- **Table**: `candidate_skill`
- **Fields**:
  - `candidate_id` (UUID, FK, PK): Reference to candidate
  - `skill_id` (UUID, FK, PK): Reference to skill
  - `level` (Text): Proficiency level ("beginner", "intermediate", "expert")
  - `years` (Numeric): Years of experience with skill
- **Relationships**:
  - `candidate` (N:1) → Candidate
  - `skill` (N:1) → Skill

##### **Job** (Job Postings)
- **Table**: `job`
- **Fields**:
  - `id` (UUID, PK): Unique job ID
  - `title` (Text): Job title (e.g., "Senior Python Engineer")
  - `description` (Text): Job description
  - `department` (Text): Department name
  - `location` (Text): Job location (e.g., "Seattle, WA")
  - `status` (Enum): "draft" | "open" | "closed" | "cancelled"
  - **AI Fields**:
    - `required_skills_json` (JSONB): Nice-to-have skills
    - `must_have_skills_json` (JSONB): Non-negotiable skills
    - `min_years_experience` (Numeric): Minimum years required
    - `max_years_experience` (Numeric): Maximum years acceptable
    - `work_arrangement` (String): "remote", "hybrid", "onsite"
    - `employment_type` (String): "full-time", "part-time", "contract"
  - `created_at` (DateTime): Record creation
  - `updated_at` (DateTime): Last update
- **Relationships**:
  - `applications` (1:N) → Application

##### **Application** (Job Applications)
- **Table**: `application`
- **Fields**:
  - `id` (UUID, PK): Unique application ID
  - `candidate_id` (UUID, FK): Reference to candidate
  - `job_id` (UUID, FK): Reference to job
  - `status` (Enum): "sourced" | "applied" | "screen" | "shortlist" | "interview" | "offer" | "hired" | "rejected" | "withdrawn"
  - `applied_at` (DateTime): Application submission time
  - `updated_at` (DateTime): Last status change
  - **Constraints**: UNIQUE(candidate_id, job_id) - One application per candidate per job
- **Relationships**:
  - `candidate` (N:1) → Candidate
  - `job` (N:1) → Job

---

### **Vector Database (Qdrant)**

#### **Collection 1: candidates_v1** (Resume Embeddings)
- **Vector Size**: 384 dimensions (all-MiniLM-L6-v2)
- **Distance Metric**: Cosine
- **Point Types**: 3 vectors per candidate resume

**Payload Structure**:
```json
{
  "candidate_id": "uuid",
  "type": "profile|skills|chunk",
  "chunk_index": 0,
  "chunk_text": "...",
  "skills": ["Python", "Django"],
  "start_char": 0,
  "end_char": 400,
  "created_at": "ISO timestamp"
}
```

#### **Collection 2: jobs_v1** (Job Embeddings)
- **Vector Size**: 384 dimensions
- **Distance Metric**: Cosine
- **Point Types**: 2 vectors per job

**Payload Structure**:
```json
{
  "job_id": "uuid",
  "type": "profile|skills",
  "title": "Job Title",
  "skills": ["Python", "AWS"],
  "created_at": "ISO timestamp"
}
```

---

### **Redis** (Cache & Queues)

| Key Pattern | Type | Purpose | TTL |
|---|---|---|---|
| `ingestion_queue` | LIST | Pending resume ingestion jobs | Persistent |
| `ingestion_queue_dlq` | LIST | Failed jobs after max retries | Persistent |
| `parsed_candidate:{temp_id}` | STRING (JSON) | Cached resume parsing results | 1 hour |
| `job_rankings:{job_id}` | STRING (JSON) | Cached ranking results | 5 minutes |
| `job_embeddings:{job_id}` | STRING (JSON) | Pre-computed job embeddings | 1 hour |

---

### **MinIO** (File Storage)

- **Bucket**: `rightstaff-resumes`
- **Directory Structure**:
  ```
  resumes/
  ├── {candidate_id}/
  │   └── resume.pdf (or .docx, .txt)
  └── {temp_id}/  (for temporary uploads)
      └── resume.pdf
  ```

---

## 3. API ENDPOINTS

### **Webhook Endpoints** (`/api/v1/webhooks`)

#### **POST /api/v1/webhooks/candidate-updated**
- **Purpose**: Receive candidate resume updates from Portal team
- **Request Body**:
  ```json
  {
    "event_type": "profile_created|profile_updated|resume_uploaded",
    "candidate_id": "uuid",
    "timestamp": "ISO timestamp",
    "s3_resume_url": "s3://bucket/path/resume.pdf",
    "profile_snapshot": { "name": "...", "email": "..." }
  }
  ```
- **Response**: 202 Accepted
- **Flow**:
  1. Validate candidate exists in PostgreSQL
  2. Queue job in Redis `ingestion_queue`
  3. Return immediately (async processing)
- **Dependencies**: PostgreSQL, Redis

#### **POST /api/v1/webhooks/job-ingestion**
- **Purpose**: Receive job postings and generate embeddings
- **Request Body**:
  ```json
  {
    "job_id": "uuid",
    "title": "Senior Python Engineer",
    "description": "...",
    "required_skills": ["Python", "AWS"],
    "must_have_skills": ["Python"],
    "preferred_skills": ["FastAPI"]
  }
  ```
- **Response**: 200 OK
- **Flow**:
  1. Normalize and expand skills using ontology
  2. Generate dual embeddings (profile + skills)
  3. Store in Qdrant `jobs_v1` collection
  4. Cache in Redis (1 hour TTL)
- **Dependencies**: Ontology, Embeddings, Qdrant, Redis

---

### **Job Endpoints** (`/api/v1/jobs`)

#### **POST /api/v1/jobs/**
- **Purpose**: Create a job posting (for testing)
- **Request Body**:
  ```json
  {
    "title": "Senior Engineer",
    "description": "...",
    "required_skills": ["Python"],
    "must_have_skills": ["Python"],
    "min_years_experience": 5,
    "max_years_experience": 15,
    "location": "Seattle, WA"
  }
  ```
- **Response**: 201 Created with job_id

#### **POST /api/v1/jobs/{job_id}/apply**
- **Purpose**: Submit job application
- **Query Params**: `candidate_id`
- **Response**: 201 Created with application_id
- **Business Rules**:
  - Job must be in "open" status
  - Candidate must exist
  - One application per candidate per job (UNIQUE constraint)

#### **POST /api/v1/jobs/rank**
- **Purpose**: Filter candidates using SQL gates only
- **Request Body**: `{ "job_id": "uuid", "use_cache": true }`
- **Response**: `{ "status": "completed", "total_qualified": N, ... }`
- **Flow**: Apply must-have skills, years, location filters

#### **GET /api/v1/jobs/{job_id}/rankings**
- **Purpose**: Get cached ranking results
- **Query Params**: `top_k=20` (number of results)
- **Response**: Cached candidate IDs

#### **POST /api/v1/jobs/{job_id}/rank_full**
- **Purpose**: Generate complete ranked candidate list
- **Request Body**: `{ "use_cache": true }`
- **Response**: Full ranking with scores and explanations
- **Pipeline**:
  1. SQL gating (hard filters)
  2. Dense semantic search
  3. Structured scoring
  4. Cross-encoder re-ranking
  5. Score blending
  6. Confidence banding
  7. Explanation generation

---

### **Candidate Endpoints** (`/api/v1/candidates`)

#### **POST /api/v1/candidates/upload-resume**
- **Purpose**: Anonymous resume upload with parsing
- **Request**: `FormData` with file
- **Response**: 200 OK
  ```json
  {
    "temp_id": "uuid",
    "parsed_data": {
      "full_name": "John Doe",
      "email": "john@example.com",
      "phone": "555-1234",
      "skills": ["Python", "Django"],
      "years_experience": 5,
      "location": "Seattle, WA",
      "professional_summary": "..."
    }
  }
  ```
- **Flow**:
  1. Upload to MinIO
  2. Queue parse-only job in Redis
  3. Poll for completion (30 second timeout)
  4. Return parsed data (cached in Redis)
- **Key**: NO PostgreSQL/Qdrant writes at this stage

#### **GET /api/v1/candidates/parsed/{temp_id}**
- **Purpose**: Retrieve cached parsed resume data
- **Response**: 200 OK with parsed data
- **Raises**: 404 if expired (> 1 hour)

#### **POST /api/v1/candidates/**
- **Purpose**: Create candidate and trigger full ingestion
- **Request Body**:
  ```json
  {
    "temp_id": "uuid",
    "full_name": "John Doe",
    "years_experience": 5,
    "professional_summary": "...",
    "location": "Seattle, WA",
    "email": "john@example.com",
    "phone": "555-1234"
  }
  ```
- **Response**: 201 Created
- **Flow**:
  1. Validate temp_id exists in Redis
  2. Create Candidate in PostgreSQL
  3. Create CandidateContact record
  4. Queue FULL ingestion job
  5. Clear Redis cache
  6. Return candidate_id

---

### **Chat Endpoints** (`/api/v1/chat`)

#### **WebSocket /api/v1/chat/{job_id}**
- **Purpose**: Real-time RAG chatbot for candidate Q&A
- **Message Format**:
  ```json
  { "question": "Who has Python?", "history": [...] }
  ```
- **Response**:
  ```json
  {
    "type": "response|error",
    "content": "response text",
    "citations": ["candidate_id:uuid"]
  }
  ```
- **Flow**:
  1. Check guardrails (EEOC compliance)
  2. Retrieve relevant candidate context
  3. Generate response with citations
  4. Send streaming response

#### **POST /api/v1/chat/{job_id}/email/{candidate_id}**
- **Purpose**: Draft personalized email to candidate
- **Request Body**: `{ "email_type": "outreach|interview|rejection" }`
- **Response**: `{ "email": "draft text" }`

---

### **Admin Endpoints** (`/api/v1/admin`)

#### **GET /api/v1/admin/metrics**
- **Purpose**: Get system metrics (counters, timings, gauges)
- **Response**: Detailed metrics object

#### **GET /api/v1/admin/dlq**
- **Purpose**: Get Dead Letter Queue status
- **Response**: `{ "depth": N, "sample_entries": [...] }`

#### **POST /api/v1/admin/dlq/replay**
- **Purpose**: Replay all failed jobs from DLQ
- **Response**: `{ "replayed_count": N }`

#### **POST /api/v1/admin/dlq/clear**
- **Purpose**: Clear all DLQ entries (WARNING: destructive)
- **Response**: `{ "deleted_count": N }`

#### **GET /api/v1/admin/health/detailed**
- **Purpose**: Detailed health check with component metrics
- **Response**: Worker stats, queue depth, DLQ depth, vector count

---

### **System Endpoints**

#### **GET /health**
- **Purpose**: Comprehensive health check
- **Response**: Status of API, PostgreSQL, Qdrant, Redis, MinIO

#### **GET /**
- **Purpose**: Root endpoint info
- **Response**: Links to docs and health check

---

## 4. DATA FLOW PATHS

### **Flow 1: Resume Upload & Ingestion Pipeline**

```
User Frontend
    ↓
POST /candidates/upload-resume
    ↓ [Stage 1: Upload]
MinIO.upload_file()
    ↓
Queue parse-only job → Redis ingestion_queue
    ↓
Poll Redis → GET /candidates/parsed/{temp_id}
    ↓
Return to UI with pre-filled form
    ↓
User submits form
    ↓
POST /candidates/ (with temp_id)
    ↓ [Stage 2: Create Candidate]
PostgreSQL:
  ├─ INSERT Candidate
  ├─ INSERT CandidateContact
  └─ COMMIT
    ↓
Queue FULL ingestion job → Redis ingestion_queue
    ↓
[Background Worker Processing - 7 Stages]
    ├─ Stage 1: Fetch candidate from PostgreSQL
    ├─ Stage 2: Download resume from MinIO
    ├─ Stage 3: Parse text (Unstructured lib)
    ├─ Stage 4: Extract skills (LLM/spaCy)
    ├─ Stage 4.5: Store skills in PostgreSQL
    │   └─ INSERT Skill (if new)
    │   └─ INSERT CandidateSkill
    ├─ Stage 4.6: Store resume metadata
    │   └─ INSERT CandidateResume
    ├─ Stage 5: Chunk text (400 chars, 50 char overlap)
    ├─ Stage 6: Generate embeddings
    │   ├─ Profile embedding (resume summary)
    │   ├─ Skills embedding (skill list)
    │   └─ Chunk embeddings (N chunks)
    └─ Stage 7: Store vectors in Qdrant
        └─ UPSERT candidates_v1 collection
    ↓
Mark job as complete in metrics
```

### **Flow 2: Job Ingestion**

```
Portal Team
    ↓
POST /webhooks/job-ingestion
    ├─ Normalize skills → ontology.normalize_skill()
    ├─ Expand skills → ontology.expand_skills()
    ├─ Generate embeddings:
    │   ├─ Profile embedding (title + description)
    │   └─ Skills embedding (expanded skills list)
    ├─ Store in Qdrant jobs_v1:
    │   ├─ UPSERT {job_id}_profile vector
    │   └─ UPSERT {job_id}_skills vector
    └─ Cache in Redis (1 hour TTL)
```

### **Flow 3: Candidate Ranking Pipeline**

```
Recruiter
    ↓
POST /jobs/{job_id}/rank_full
    ↓ [Check Cache]
Redis GET job_rankings:{job_id}
    → If found: Return cached results
    ↓ [Not Cached - Full Pipeline]
    ├─ Step 1: Fetch job data from PostgreSQL
    ├─ Step 2: Get applicant candidate IDs
    │   └─ SELECT candidate_id FROM application WHERE job_id = ?
    ├─ Step 3: SQL Gating
    │   ├─ Must-have skills filter
    │   │   └─ SELECT candidate_id WHERE skills ⊇ must_haves
    │   ├─ Years experience filter
    │   │   └─ SELECT candidate_id WHERE years BETWEEN min AND max
    │   └─ Location filter
    │       └─ SELECT candidate_id WHERE city = preferred_location
    ├─ Step 4: Dense Retrieval
    │   ├─ Fetch job embeddings from Redis/Qdrant
    │   ├─ Search candidates_v1 with job profile embedding
    │   ├─ Search candidates_v1 with job skills embedding
    │   ├─ Combine scores: 0.5*profile + 0.3*skills + 0.2*chunks
    │   └─ Return top 100 candidates
    ├─ Step 5: Cross-Encoder Re-ranking
    │   ├─ Score top 100 with pairwise cross-encoder
    │   └─ Weight: 0.25 in final blend
    ├─ Step 6: Structured Scoring
    │   ├─ Score nice-to-have skills (0.35)
    │   ├─ Score experience (0.20)
    │   ├─ Score recency (0.15)
    │   ├─ Score domain match (0.10)
    │   └─ Score location match (0.20)
    ├─ Step 7: Blend Scores
    │   └─ Final = 0.30*dense + 0.30*structured + 0.25*pairwise + 0.15*completeness
    ├─ Step 8: Confidence Banding
    │   ├─ High: score > 0.75
    │   ├─ Medium: 0.5 < score ≤ 0.75
    │   └─ Low: score ≤ 0.5
    ├─ Step 9: Generate Explanations
    │   ├─ Summary (band-based)
    │   ├─ Top reasons (skills, experience, location)
    │   └─ Evidence snippets (top matching resume chunks)
    └─ Cache results in Redis (5 minute TTL)
    ↓
Return RankingResponse with all candidates ranked
```

### **Flow 4: Query Chatbot**

```
Recruiter
    ↓
WebSocket /chat/{job_id}
    ├─ Send: { "question": "Who has Python?" }
    ├─ Server: check_guardrails() → EEOC compliance
    │   └─ If violates protected attributes: Return guardrail error
    ├─ retrieve_context():
    │   ├─ Rank candidates for job
    │   ├─ Embed question
    │   ├─ Search candidate vectors for relevant chunks
    │   └─ Return top 5 matches
    ├─ generate_response():
    │   ├─ Build context from retrieved chunks
    │   ├─ Generate LLM response
    │   └─ Add citations (candidate IDs)
    └─ Send response via WebSocket
```

---

## 5. SERVICE LAYER ARCHITECTURE

### **Service Classes & Responsibilities**

#### **IngestionWorker** (`services/ingestion.py`)
- **Purpose**: Background worker processing resume ingestion jobs
- **Key Methods**:
  - `start()`: Begin infinite polling loop
  - `process_job_with_retry()`: Process single job with retry logic
  - `_process_job_with_tenacity()`: Actual processing (with @retry decorator)
  - `_move_to_dlq()`: Move failed job to Dead Letter Queue
- **Retry Logic**:
  - Max 5 attempts (1 original + 4 retries)
  - Exponential backoff: 2s, 4s, 8s, 16s
  - Catches: ConnectionError, TimeoutError, S3Error
- **Metrics Tracked**:
  - `ingestion_jobs_success`: Successful ingestions
  - `ingestion_jobs_failed`: Failed ingestions
  - Stage-specific timings

#### **RankingService** (`services/ranking.py`)
- **Purpose**: Orchestrates complete ranking pipeline
- **Key Methods**:
  - `rank_candidates()`: Main entry point
  - `_fetch_job_data()`: Get job from DB
  - `_fetch_candidates_data()`: Get candidate details
- **Weights**:
  - Dense: 0.30
  - Structured: 0.30
  - Pairwise (cross-encoder): 0.25
  - Completeness: 0.15
- **Output**: `List[RankedCandidate]` with scores, bands, explanations

#### **EmbeddingService** (`services/embeddings.py`)
- **Purpose**: Generate text embeddings using sentence-transformers
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (384 dims)
- **Key Methods**:
  - `embed_text()`: Single text → vector
  - `embed_texts()`: Multiple texts → vectors (batch)
- **Features**:
  - Lazy loading (loads on first use)
  - Device detection (CUDA/MPS/CPU)
  - Model warmup on initialization
- **Performance**: ~3000 sentences/second on CPU

#### **VectorStore** (`services/vector_store.py`)
- **Purpose**: Qdrant client for vector storage and search
- **Key Methods**:
  - `create_collection()`: Initialize collection (idempotent)
  - `upsert_vectors()`: Insert/update vectors with payloads
  - `search()`: Similarity search with filtering
  - `delete_by_candidate()`: Remove all vectors for a candidate
- **Collections**:
  - `candidates_v1`: Resume embeddings
  - `jobs_v1`: Job embeddings
- **Distance Metric**: Cosine (for normalized embeddings)

#### **DenseRetriever** (`services/retrieval.py`)
- **Purpose**: Semantic search for candidates
- **Key Methods**:
  - `retrieve_candidates()`: Find similar candidates for job
- **Weights**:
  - Profile: 0.5
  - Skills: 0.3
  - Chunks: 0.2
- **Output**: `List[DenseRetrievalResult]` with evidence chunks

#### **StructuredScorer** (`services/scoring.py`)
- **Purpose**: Calculate objective scores from candidate data
- **Key Methods**:
  - `calculate_score()`: Compute all scoring components
  - `_score_nice_to_have_skills()`: Coverage percentage
  - `_score_experience()`: Years experience with diminishing returns
  - `_score_recency()`: Profile freshness (months since update)
  - `_score_domain()`: Domain match
  - `_score_location()`: Location preference match
- **Weights**:
  - Nice-to-have: 0.35
  - Experience: 0.20
  - Recency: 0.15
  - Domain: 0.10
  - Location: 0.20

#### **RerankerService** (`services/reranker.py`)
- **Purpose**: Cross-encoder pairwise scoring
- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Key Methods**:
  - `rerank()`: Reorder candidates by pairwise relevance
- **Input**: Job description + candidate summaries
- **Output**: Sorted candidates with `pairwise_score`

#### **ExplanationGenerator** (`services/explanation.py`)
- **Purpose**: Generate human-readable ranking explanations
- **Key Methods**:
  - `generate()`: Create explanation object
  - `_generate_summary()`: One-line overview
  - `_extract_reasons()`: Top 3-5 reasons
  - `_format_evidence()`: Supporting evidence snippets
- **Output**: Explanation with summary, reasons, evidence

#### **JobEmbeddingService** (`services/job_embeddings.py`)
- **Purpose**: Generate and cache job embeddings
- **Key Methods**:
  - `get_or_create_job_embeddings()`: Fetch or create dual embeddings
  - `_prepare_skills_text()`: Format skills for embedding
  - `_store_job_vectors()`: Store in Qdrant
- **Caching**: 1 hour TTL in Redis

#### **SkillExtractor** (`services/skill_extractor.py`)
- **Purpose**: Unified skill extraction interface
- **Methods**:
  - `extract_skills()`: Main entry point
  - `_extract_hybrid()`: LLM + spaCy
  - `_extract_llm()`: LLM only
  - `_extract_spacy()`: spaCy + patterns only
- **Output**: Normalized, deduplicated, sorted skill list
- **Modes**: "hybrid" (best), "llm" (good), "spacy" (baseline)

#### **Ontology** (`services/ontology.py`)
- **Purpose**: Skills taxonomy, normalization, and expansion
- **Key Functions**:
  - `load_skills_taxonomy()`: Load from JSON file
  - `normalize_skill()`: Map variant → canonical
  - `expand_skills()`: Add synonyms and related skills
  - `extract_skills_from_text()`: Extract from text (spaCy)
- **Taxonomy Structure**: Canonical name → synonyms, category, parent

#### **SQLFilter** (`services/sql_filter.py`)
- **Purpose**: SQL-based hard filtering gates
- **Key Functions**:
  - `filter_candidates_by_must_have_skills()`: AND logic (has all)
  - `filter_candidates_by_years_experience()`: Range check
  - `filter_candidates_by_location()`: City matching
  - `apply_combined_sql_gates()`: Apply all filters
- **Output**: Set of qualified candidate IDs
- **Performance**: < 100ms for 10K candidates

#### **RedisClient** (`services/redis_client.py`)
- **Purpose**: Async Redis wrapper
- **Key Methods**:
  - `lpush()`: Add to queue
  - `brpop()`: Blocking pop (with timeout)
  - `get()` / `set()`: Cache operations
  - `push_dlq()`: Move to Dead Letter Queue
  - `get_dlq_entries()`: Peek at DLQ
  - `replay_dlq_entry()`: Re-queue from DLQ

#### **S3Client** (`services/s3_client.py`)
- **Purpose**: MinIO/S3 async wrapper
- **Key Methods**:
  - `download_file()`: Get resume from MinIO
  - `upload_file()`: Store resume to MinIO
- **Implementation**: Uses `asyncio.to_thread()` for async I/O

#### **LLMResumeParser** (`services/llm_parser.py`)
- **Purpose**: LLM-based field extraction from resumes
- **Model**: `Qwen/Qwen2.5-0.5B-Instruct` (0.5B params, ~1GB download)
- **Fallback**: `HuggingFaceTB/SmolLM-135M-Instruct` (135M params)
- **Key Methods**:
  - `parse_resume()`: Extract all fields from resume text
  - `_clean_*()`: Validate and clean extracted data
- **Features**: Lazy loading, async support, graceful fallback, pre-download script

#### **CandidateChatbot** (`services/chatbot_langgraph.py`)
- **Purpose**: RAG-powered chatbot with EEOC guardrails
- **Key Methods**:
  - `chat()`: Process question → generate response
  - `draft_email()`: Generate personalized email
- **Graph Nodes**:
  1. `check_guardrails()`: EEOC compliance check
  2. `retrieve_context()`: Vector search
  3. `generate_response()`: LLM generation
- **Protected Attributes**: Race, gender, age, religion, disability, marital, pregnancy, national origin

#### **MetricsCollector** (`services/metrics.py`)
- **Purpose**: In-memory observability metrics
- **Metric Types**:
  - Counters: Incrementing values
  - Timings: Duration statistics
  - Gauges: Point-in-time measurements
- **Key Methods**:
  - `increment_counter()`: Record event
  - `record_timing()`: Time operation
  - `set_gauge()`: Set value
  - `get_metrics()`: Get all metrics

---

## 6. Utility Functions & Helpers

### **Parsing Utilities** (`services/parsers.py`)

| Function | Purpose | Returns |
|---|---|---|
| `parse_resume()` | Parse PDF/DOCX/TXT → text | `{"text": str, "metadata": {...}}` |
| `chunk_text()` | Split text into overlapping chunks | `List[str]` |
| `extract_metadata()` | Extract structured fields (regex) | `Dict[field → value]` |
| `extract_name()` | Extract candidate name | `Optional[str]` |
| `extract_email()` | Extract email address | `Optional[str]` |
| `extract_phone()` | Extract phone number | `Optional[str]` |
| `extract_location()` | Extract location | `Optional[str]` |
| `calculate_years_experience()` | Calculate years from text | `Optional[float]` |

### **Logging Utilities** (`utils/logging.py`)

| Function | Purpose |
|---|---|
| `setup_logging()` | Configure structlog (JSON for prod, console for dev) |
| `get_logger()` | Get structured logger instance |
| `redact_pii()` | Remove sensitive fields from logs |

### **Config & Settings** (`config.py`)

| Property | Purpose |
|---|---|
| `database_url` | PostgreSQL sync URL |
| `async_database_url` | PostgreSQL async URL |
| `redis_url` | Redis connection URL |

---

## 7. Webhook Handlers

### **Candidate Updated Webhook**
- **Endpoint**: `POST /api/v1/webhooks/candidate-updated`
- **Handler**: `candidate_updated_webhook()` in `webhooks.py`
- **Processing**:
  1. Validate candidate exists
  2. Queue ingestion job in Redis
  3. Return 202 Accepted immediately
- **Error Handling**: 404 if candidate not found, 500 for other errors

### **Job Ingestion Webhook**
- **Endpoint**: `POST /api/v1/webhooks/job-ingestion`
- **Handler**: `job_ingestion_webhook()` in `webhooks.py`
- **Processing**:
  1. Normalize and expand skills
  2. Generate dual embeddings
  3. Store in Qdrant `jobs_v1`
  4. Cache in Redis
- **Error Handling**: 500 on any failure

---

## 8. Key Dependencies & Integrations

### **External Libraries**

| Library | Purpose | Version |
|---|---|---|
| fastapi | Web framework | Latest |
| sqlalchemy | ORM | Async support |
| pydantic | Data validation | Latest |
| redis | Cache/queue | Async version |
| qdrant-client | Vector DB | Latest |
| minio | File storage | Latest |
| sentence-transformers | Embeddings | Latest |
| spacy | NER (optional) | en_core_web_sm |
| transformers | LLM models | Latest |
| unstructured | Document parsing | Latest |
| langgraph | Chatbot orchestration | Latest |
| tenacity | Retry logic | Latest |

### **Data Flow Diagram**

```
┌──────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                           │
│  - RecruiterDashboard, CandidatePortal                          │
│  - JobForm, CandidateForm, ResumeUpload                        │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ HTTP/WebSocket
                                   ↓
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (main.py)                     │
├──────────┬──────────┬──────────┬──────────┬──────────────────────┤
│ Webhooks │   Jobs   │Candidates│  Chat    │     Admin            │
│ (webhook)│(jobs.py) |(cand.py) |(chat.py) │  (admin.py)          │
└─────┬────┴────┬─────┴────┬─────┴─────┬────┴──────────┬───────────┘
      │         │          │           │               │
      ↓         ↓          ↓           ↓               ↓
┌──────────────────────────────────────────────────────────────────┐
│                    Service Layer                                  │
├─────────────────────────────────────────────────────────────────┤
│ • Ingestion (background worker)    • SQLFilter (gates)           │
│ • Ranking (orchestration)          • Ontology (skills)           │
│ • Embeddings (text→vectors)        • Chatbot (RAG)               │
│ • Retrieval (semantic search)      • Metrics (observability)     │
│ • Scoring (objective metrics)      • Parsers (resume)            │
│ • Explanation (why ranked)         • SkillExtractor (unified)    │
│ • Reranking (cross-encoder)        • LLMParser (field extract)   │
│ • JobEmbeddings (dual vectors)     • Logging (structured)        │
└─────┬──────────┬────────────┬──────────────┬────────────────────┘
      │          │            │              │
      ↓          ↓            ↓              ↓
┌──────────────────────────────────────────────────────────────────┐
│                   Storage Layer                                   │
├──────────────┬──────────────┬──────────────┬──────────────────────┤
│ PostgreSQL   │  Qdrant      │    Redis     │     MinIO            │
│ (structured) │  (vectors)   │  (cache)     │  (file storage)      │
│              │              │              │                      │
│ • Candidate  │ • candidates │ • job queues │ • Resumes (PDFs)    │
│ • Job        │   _v1        │ • DLQ        │ • Temp uploads      │
│ • Skill      │ • jobs_v1    │ • Cache      │                      │
│ • Application│              │              │                      │
└──────────────┴──────────────┴──────────────┴──────────────────────┘
```

---

## 9. Testing Strategy

### **Test Files Location**
- `/home/user/RightStaff/backend/tests/` - Unit/integration tests
- `/home/user/RightStaff/backend/feature_tests/` - Feature-level tests
- `/home/user/RightStaff/frontend/src/App.test.tsx` - React tests

### **Key Test Files**
| File | Purpose |
|---|---|
| `test_ranking.py` | Ranking logic tests |
| `test_ranking_comprehensive.py` | End-to-end ranking tests |
| `test_skills.py` | Skill extraction tests |
| `test_parsers.py` | Resume parsing tests |
| `test_llm_parser.py` | LLM field extraction tests |
| `test_fairness.py` | Fairness & bias tests |
| `feature_tests/test_api.py` | API endpoint tests |
| `feature_tests/test_embeddings.py` | Embedding tests |
| `feature_tests/test_vector_store.py` | Qdrant tests |

---

## 10. Critical Code Paths for Test Coverage

### **Path 1: Resume Ingestion (7 Stages)**
1. Webhook receives resume
2. Job queued in Redis
3. Worker polls and fetches
4. Resume downloaded from MinIO
5. Text parsed (Unstructured)
6. Skills extracted (LLM/spaCy)
7. Skills stored in PostgreSQL
8. Text chunked
9. Embeddings generated
10. Vectors stored in Qdrant

### **Path 2: Candidate Ranking (Full Pipeline)**
1. Request received for job
2. Check cache
3. Fetch job and applicants
4. Apply SQL gates
5. Dense retrieval
6. Cross-encoder re-ranking
7. Structured scoring
8. Score blending
9. Confidence banding
10. Explanation generation
11. Cache results
12. Return response

### **Path 3: Chatbot Q&A**
1. WebSocket message received
2. Guardrail check (EEOC)
3. Question embedding
4. Vector search
5. Context retrieval
6. LLM response generation
7. Citation addition
8. Send via WebSocket

---

## 11. Error Handling & Retry Strategies

### **Ingestion Pipeline Error Handling**
- **Transient Errors**: ConnectionError, TimeoutError, S3Error
  - Retry up to 5 times with exponential backoff
  - Move to DLQ after max retries
- **Permanent Errors**: ValueError (candidate not found)
  - Don't retry, move to DLQ immediately

### **API Error Handling**
- **400 Bad Request**: Invalid input
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Duplicate application
- **500 Internal Server Error**: Unexpected failures

---

## 12. Caching Strategy

| Cache Key | Type | TTL | Purpose |
|---|---|---|---|
| `parsed_candidate:{temp_id}` | String | 1 hour | Resume parsing results |
| `job_rankings:{job_id}` | String | 5 min | Ranking results |
| `job_embeddings:{job_id}` | String | 1 hour | Job dual embeddings |
| `ingestion_queue` | List | Persistent | Pending ingestion jobs |
| `ingestion_queue_dlq` | List | Persistent | Failed jobs |

---

## Conclusion

The RightStaff codebase is a well-structured AI ranking system with clear separation of concerns:
- **API Layer**: Clean FastAPI endpoints for webhooks, jobs, candidates, chat
- **Service Layer**: Specialized services for each component (ranking, embeddings, retrieval, etc.)
- **Data Layer**: Four complementary databases (PostgreSQL, Qdrant, Redis, MinIO)
- **Background Processing**: Async ingestion worker with retry and DLQ
- **Explainability**: Built-in explanations and evidence for all rankings

For comprehensive test coverage, focus on:
1. **Integration tests** for each API endpoint
2. **Pipeline tests** for ingestion stages and ranking flow
3. **Unit tests** for scoring, filtering, and explanation logic
4. **Error tests** for retry logic and DLQ handling
5. **E2E tests** for complete workflows (upload → ingest → rank)

