# 📥 RightStaff Ingestion Pipelines - Complete Guide

## 📖 Table of Contents
1. [Overview](#overview)
2. [Pipeline 1: Candidate Resume Webhook Ingestion](#pipeline-1-candidate-resume-webhook-ingestion)
3. [Pipeline 2: Candidate Resume Upload via API](#pipeline-2-candidate-resume-upload-via-api)
4. [Pipeline 3: Job Ingestion via Webhook](#pipeline-3-job-ingestion-via-webhook)
5. [Pipeline 4: Dummy Data Population](#pipeline-4-dummy-data-population)
6. [Database Schemas](#database-schemas)
7. [Data Flow Diagrams](#data-flow-diagrams)
8. [Universal Variable Names & Consistency](#universal-variable-names--consistency)
9. [Schema Consistency Verification](#schema-consistency-verification)

---

## Overview

RightStaff has **4 distinct ingestion pipelines** that populate data across **4 databases**:
- **PostgreSQL**: Structured data (candidates, jobs, skills, applications)
- **Qdrant**: Vector embeddings (for semantic search)
- **Redis**: Caching and job queues
- **MinIO**: File storage (resume PDFs/DOCX)

All pipelines follow consistent naming conventions and schema structures to ensure data integrity.

---

## Pipeline 1: Candidate Resume Webhook Ingestion

### **Purpose**
Receives resume upload notifications from Portal team and processes them through complete ingestion pipeline.

### **Entry Point**
`backend/app/api/webhooks.py` → `candidate_updated_webhook()`

### **Trigger**
Portal team sends webhook when candidate profile is created/updated.

### **Flow Diagram**
```
Portal Team
    ↓ (HTTP POST)
Webhook Endpoint (/api/v1/webhooks/candidate-updated)
    ↓
Validate candidate exists in PostgreSQL
    ↓
Queue job in Redis (ingestion_queue)
    ↓
Return 202 Accepted (immediate response)
    ↓
Background Worker (ingestion.py) polls Redis
    ↓
FULL 7-STAGE PIPELINE:
    ├─ Stage 1: Fetch candidate details from PostgreSQL
    ├─ Stage 2: Download resume from MinIO
    ├─ Stage 3: Parse resume (extract text using Unstructured)
    ├─ Stage 4: Extract skills (LLM hybrid mode if enabled, spaCy fallback)
    ├─ Stage 4.5: Store skills in PostgreSQL (skill + candidate_skill tables)
    ├─ Stage 4.6: Store resume record in PostgreSQL (candidate_resume table)
    ├─ Stage 5: Chunk text (split into 400-char overlapping chunks)
    ├─ Stage 6: Generate embeddings (1 profile + 1 skills + N chunks)
    └─ Stage 7: Store vectors in Qdrant (resumes collection)

**LLM Support:** When `USE_LLM_PARSING=true`, Stage 4 uses hybrid method (LLM + spaCy) for better accuracy. When disabled, uses spaCy only.
```

### **Data Flow**

#### **Input:**
```json
{
  "event_type": "resume_uploaded",
  "candidate_id": "a1b2c3d4-1234-5678-90ab-cdef12345678",
  "timestamp": "2024-01-15T10:30:00Z",
  "s3_resume_url": "s3://bucket/resumes/candidate_id/resume.pdf",
  "profile_snapshot": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

#### **Databases Touched:**

**PostgreSQL:**
- **Read:** `candidate` table (validate existence)
- **Write:**
  - `skill` table (create new skills if not exist)
  - `candidate_skill` table (link candidate to skills)
  - `candidate_resume` table (store resume metadata)

**Redis:**
- **Write:** Queue job in `ingestion_queue` (LIST)
- **Read:** Background worker polls queue with `BRPOP`

**MinIO:**
- **Read:** Download resume file from s3_url

**Qdrant:**
- **Write:** Store 3 types of vectors in `resumes` collection:
  1. **Profile vector** (kind="profile"): Full resume summary
  2. **Skills vector** (kind="skills"): Extracted skills
  3. **Chunk vectors** (kind="chunk"): Resume text chunks (typically 5-15 chunks)

#### **Qdrant Payload Structure:**
```python
# Profile vector
{
    "candidate_id": "a1b2c3d4-...",
    "kind": "profile",
    "full_name": "John Doe",
    "text": "John Doe\nSoftware Engineer...",  # First 500 chars
    "skills": ["Python", "Django", "PostgreSQL"],
    "filename": "resume.pdf",
    "created_at": "2024-01-15T10:30:00Z"
}

# Skills vector
{
    "candidate_id": "a1b2c3d4-...",
    "kind": "skills",
    "skills": ["Python", "Django", "PostgreSQL"],
    "skills_count": 3,
    "filename": "resume.pdf",
    "created_at": "2024-01-15T10:30:00Z"
}

# Chunk vector (one per chunk)
{
    "candidate_id": "a1b2c3d4-...",
    "kind": "chunk",
    "chunk_index": 0,
    "chunk_text": "5 years of Python development...",
    "start_char": 0,
    "end_char": 400,
    "char_count": 400,
    "skills_detected": ["Python", "Django"],
    "filename": "resume.pdf",
    "created_at": "2024-01-15T10:30:00Z"
}
```

### **File Location**
`backend/app/api/webhooks.py:28-88` (webhook endpoint)
`backend/app/services/ingestion.py:173-633` (processing pipeline)

---

## Pipeline 2: Candidate Resume Upload via API

### **Purpose**
Allows users to upload resumes directly via frontend, with a 3-stage process for optimal UX.

### **Entry Point**
`backend/app/api/candidates.py`

### **Trigger**
User uploads resume file via frontend form.

### **3-Stage Process**

#### **Stage 1: Upload Resume (Parse-Only Mode)**

**Endpoint:** `POST /api/v1/candidates/upload-resume`

**Flow:**
```
User uploads file (PDF/DOCX/TXT)
    ↓
Generate temp_id (UUID)
    ↓
Upload file to MinIO (resumes/{temp_id}/resume.{ext})
    ↓
Queue PARSE_ONLY job in Redis
    ↓
Background worker processes in parse-only mode:
    ├─ Download resume from MinIO
    ├─ Parse text using Unstructured library
    ├─ Extract fields (LLM if enabled, regex fallback):
    │   - full_name, email, phone, location
    │   - years_experience, professional_summary
    │   - skills (extracted and normalized through ontology)
    └─ Cache parsed data in Redis (1-hour TTL)
    ↓
Poll Redis for completion (30 second timeout)
    ↓
Return temp_id + parsed data to frontend
```

**Data Flow:**
- **MinIO Write:** Store resume file
- **Redis Write:** Queue parse-only job
- **Redis Write:** Cache parsed data (`parsed_candidate:{temp_id}`)
- **NO PostgreSQL or Qdrant writes** (this is key!)

**Response:**
```json
{
  "temp_id": "temp-uuid-1234",
  "parsed_data": {
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+1-555-0101",
    "skills": ["Python", "Django", "PostgreSQL"],
    "years_experience": 5.0,
    "location": {
      "city": "San Francisco",
      "region": "CA",
      "country": "US"
    },
    "professional_summary": "...",
    "s3_resume_url": "s3://bucket/resumes/temp-uuid-1234/resume.pdf"
  },
  "message": "Resume parsed successfully. Use temp_id to create candidate."
}
```

**File Location:** `backend/app/api/candidates.py:66-186`

---

#### **Stage 2: Get Parsed Data (Form Pre-Fill)**

**Endpoint:** `GET /api/v1/candidates/parsed/{temp_id}`

**Flow:**
```
Frontend requests parsed data
    ↓
Fetch from Redis cache (parsed_candidate:{temp_id})
    ↓
Return cached data (or 404 if expired)
```

**Data Flow:**
- **Redis Read:** Retrieve cached parsed data

**File Location:** `backend/app/api/candidates.py:193-247`

---

#### **Stage 3: Create Candidate (Full Ingestion)**

**Endpoint:** `POST /api/v1/candidates/`

**Flow:**
```
User submits form (with temp_id + any edits)
    ↓
Validate temp_id exists in Redis cache
    ↓
Create Candidate record in PostgreSQL
    ↓
Create CandidateContact record in PostgreSQL
    ↓
Queue FULL ingestion job in Redis
    ↓
Clear Redis cache (parsed_candidate:{temp_id})
    ↓
Return candidate_id
    ↓
Background worker processes FULL pipeline:
    └─ Same 7-stage pipeline as Pipeline 1
       (creates embeddings and stores in Qdrant)
```

**Data Flow:**
- **PostgreSQL Write:**
  - `candidate` table (create record)
  - `candidate_contact` table (create record)
- **Redis Delete:** Clear cached parsed data
- **Redis Write:** Queue full ingestion job
- **Qdrant Write:** (via background worker) Store vectors

**File Location:** `backend/app/api/candidates.py:254-389`

---

## Pipeline 3: Job Ingestion via Webhook

### **Purpose**
Receives job posting notifications from Portal team and generates job embeddings for semantic matching.

### **Entry Point**
`backend/app/api/webhooks.py` → `job_ingestion_webhook()`

### **Trigger**
Portal team sends webhook when job is created/updated.

### **Flow Diagram**
```
Portal Team
    ↓ (HTTP POST)
Webhook Endpoint (/api/v1/webhooks/job-ingestion)
    ↓
Normalize skills using ontology
    ↓
Expand skills (find related skills/variants)
    ↓
Generate dual embeddings:
    ├─ Profile embedding (title + description)
    └─ Skills embedding (expanded skills)
    ↓
Store in Qdrant jobs_v1 collection (2 points)
    ↓
Cache embeddings in Redis (1-hour TTL)
    ↓
Return success
```

### **Data Flow**

#### **Input:**
```json
{
  "job_id": "job-uuid-5678",
  "title": "Senior Python Engineer",
  "description": "We're looking for...",
  "required_skills": ["Python", "AWS", "Docker"],
  "must_have_skills": ["Python"],
  "preferred_skills": ["FastAPI", "PostgreSQL"]
}
```

#### **Databases Touched:**

**Ontology Service:**
- **Read:** Skill taxonomy (for normalization and expansion)
- **Process:**
  - Normalize: "python" → "Python"
  - Expand: "Python" → ["Python", "Python3", "Python Programming"]

**Embeddings Service:**
- **Generate:**
  - Profile vector (from title + description)
  - Skills vector (from expanded skills)

**Qdrant:**
- **Write:** Store 2 points in `jobs_v1` collection:
  1. `{job_id}_profile` - Profile embedding
  2. `{job_id}_skills` - Skills embedding

**Redis:**
- **Write:** Cache embeddings (`job_embeddings:{job_id}`) with 1-hour TTL

#### **Qdrant Payload Structure:**
```python
# Profile point
{
    "id": "job-uuid-5678_profile",
    "vector": [0.1, -0.2, 0.3, ...],  # 384 dims
    "payload": {
        "job_id": "job-uuid-5678",
        "type": "profile",
        "title": "Senior Python Engineer",
        "created_at": "2024-01-15T10:30:00Z"
    }
}

# Skills point
{
    "id": "job-uuid-5678_skills",
    "vector": [0.2, -0.1, 0.4, ...],  # 384 dims
    "payload": {
        "job_id": "job-uuid-5678",
        "type": "skills",
        "skills": ["Python", "Python3", "AWS", "Docker", ...],  # Expanded
        "created_at": "2024-01-15T10:30:00Z"
    }
}
```

### **File Location**
`backend/app/api/webhooks.py:108-257`

---

## Pipeline 4: Dummy Data Population

### **Purpose**
Populates all databases with realistic test data for development and testing.

### **Entry Point**
`backend/populate_dummy_data.py` → `populate_all()`

### **Trigger**
Manually run by developer: `python populate_dummy_data.py`

### **Flow Diagram**
```
Run populate_dummy_data.py
    ↓
1. Create Jobs in PostgreSQL (6 jobs)
    ├─ Senior Python Engineer
    ├─ Full-Stack Engineer (React + Python)
    ├─ Data Engineer - Big Data Platform
    ├─ Java Backend Engineer - Microservices
    ├─ DevOps Engineer - Cloud Infrastructure
    └─ Machine Learning Engineer
    ↓
2. Create Skills Ontology in PostgreSQL (50+ skills)
    └─ Python, JavaScript, React, AWS, Docker, etc.
    ↓
3. Create Candidates in PostgreSQL (8 candidates)
    ├─ Candidate records
    ├─ CandidateContact records
    └─ CandidateSkill links (many-to-many)
    ↓
4. Generate Candidate Embeddings in Qdrant
    └─ For each candidate: 1 profile + 1 skills + 1 chunk
    ↓
5. Upload Resumes to MinIO (5 out of 8 candidates)
    └─ Create CandidateResume records in PostgreSQL
    ↓
6. Generate Job Embeddings in Qdrant
    └─ For each job: 1 profile + 1 skills
    ↓
7. Create Job Applications in PostgreSQL
    └─ 10 candidates × 3 jobs = 30 applications
```

### **Data Flow**

#### **PostgreSQL Writes:**
- **job** table: 6 jobs
- **skill** table: 50+ skills
- **candidate** table: 8 candidates
- **candidate_contact** table: 8 records
- **candidate_skill** table: ~50 links (many-to-many)
- **candidate_resume** table: 5 records
- **application** table: 30 applications

**Total PostgreSQL Records:** ~160

#### **Qdrant Writes:**
- **resumes collection:**
  - 8 candidates × 3 vectors = 24 total
  - (1 profile + 1 skills + 1 chunk per candidate)
- **jobs_v1 collection:**
  - 6 jobs × 2 vectors = 12 total
  - (1 profile + 1 skills per job)

**Total Qdrant Points:** 36

#### **MinIO Writes:**
- 5 resume files (3 candidates without resumes for testing)
- Path format: `resumes/{candidate_id}/{filename}.txt`

### **File Location**
`backend/populate_dummy_data.py`

### **Candidate Data Sample**
```python
{
    "full_name": "Sarah Chen",
    "years_experience": 8.0,
    "professional_summary": "Senior Full-Stack Engineer...",
    "contact": {
        "email": "sarah.chen@example.com",
        "phone": "+1-415-555-0101",
        "city": "San Francisco",
        "region": "CA",
        "country": "US"
    },
    "skills": [
        {"name": "Python", "level": "Expert", "years": 8.0},
        {"name": "React", "level": "Expert", "years": 6.0},
        {"name": "PostgreSQL", "level": "Advanced", "years": 7.0},
        ...
    ]
}
```

---

## Database Schemas

### **PostgreSQL Schema** (`rightstaff` schema)

#### **candidate table**
```sql
CREATE TABLE rightstaff.candidate (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    years_experience NUMERIC(5, 2),
    professional_summary TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

**Used By:**
- Pipeline 1: Read (validate), Write (skills linking via candidate_skill)
- Pipeline 2: Write (create record)
- Pipeline 4: Write (create 8 records)

---

#### **candidate_contact table**
```sql
CREATE TABLE rightstaff.candidate_contact (
    candidate_id UUID PRIMARY KEY REFERENCES rightstaff.candidate(id) ON DELETE CASCADE,
    email VARCHAR,
    phone VARCHAR,
    address_line1 TEXT,
    address_line2 TEXT,
    city TEXT,
    region TEXT,  -- NOT "state"! (important for consistency)
    postal_code VARCHAR,
    country VARCHAR
);
```

**Used By:**
- Pipeline 2: Write (create record)
- Pipeline 4: Write (create 8 records)

---

#### **candidate_resume table**
```sql
CREATE TABLE rightstaff.candidate_resume (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES rightstaff.candidate(id) ON DELETE CASCADE,
    s3_url TEXT NOT NULL,
    file_type VARCHAR,
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

**Used By:**
- Pipeline 1: Write (store resume metadata)
- Pipeline 4: Write (create 5 records)

---

#### **skill table**
```sql
CREATE TABLE rightstaff.skill (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    parent_skill_id UUID REFERENCES rightstaff.skill(id) ON DELETE SET NULL
);
```

**Purpose:** Skills ontology with parent-child relationships

**Used By:**
- Pipeline 1: Write (create skills if not exist)
- Pipeline 4: Write (create 50+ skills)

---

#### **candidate_skill table**
```sql
CREATE TABLE rightstaff.candidate_skill (
    candidate_id UUID REFERENCES rightstaff.candidate(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES rightstaff.skill(id) ON DELETE CASCADE,
    level TEXT,  -- "Expert", "Advanced", "Intermediate", "Beginner"
    years NUMERIC(5, 2),
    PRIMARY KEY (candidate_id, skill_id)
);
```

**Purpose:** Many-to-many relationship between candidates and skills

**Used By:**
- Pipeline 1: Write (link extracted skills to candidate)
- Pipeline 4: Write (create ~50 links)

---

#### **job table**
```sql
CREATE TABLE rightstaff.job (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    department TEXT,
    location TEXT,
    status rightstaff.job_status_enum NOT NULL DEFAULT 'draft',
    required_skills_json JSONB,
    must_have_skills_json JSONB,
    min_years_experience NUMERIC(5, 2),
    max_years_experience NUMERIC(5, 2),
    work_arrangement VARCHAR,  -- "remote", "hybrid", "onsite"
    employment_type VARCHAR,   -- "full-time", "part-time", "contract"
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

**Used By:**
- Pipeline 3: Read (get job metadata for embedding generation)
- Pipeline 4: Write (create 6 jobs)

---

#### **application table**
```sql
CREATE TABLE rightstaff.application (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES rightstaff.candidate(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES rightstaff.job(id) ON DELETE CASCADE,
    status rightstaff.application_status_enum NOT NULL DEFAULT 'applied',
    applied_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (candidate_id, job_id)  -- One application per candidate per job
);
```

**Purpose:** Tracks which candidates applied to which jobs

**Used By:**
- Pipeline 4: Write (create 30 applications)

---

### **Qdrant Schema**

#### **Collection: `resumes` (default collection for candidates)**

**Configuration:**
- Vector size: 384 dimensions
- Distance metric: Cosine similarity
- Model: `sentence-transformers/all-MiniLM-L6-v2`

**Point Structure:**
```python
{
    "id": "auto-generated-uuid",
    "vector": List[float],  # 384 dimensions
    "payload": Dict[str, Any]
}
```

**Payload Types:**

1. **Profile Vector** (`kind="profile"`):
```python
{
    "candidate_id": "UUID-string",
    "kind": "profile",
    "full_name": "John Doe",
    "text": "First 500 chars of resume",
    "skills": ["Python", "Django", "PostgreSQL"],
    "filename": "resume.pdf",
    "created_at": "2024-01-15T10:30:00Z"
}
```

2. **Skills Vector** (`kind="skills"`):
```python
{
    "candidate_id": "UUID-string",
    "kind": "skills",
    "skills": ["Python", "Django", "PostgreSQL"],
    "skills_count": 3,
    "filename": "resume.pdf",
    "created_at": "2024-01-15T10:30:00Z"
}
```

3. **Chunk Vector** (`kind="chunk"`):
```python
{
    "candidate_id": "UUID-string",
    "kind": "chunk",
    "chunk_index": 0,
    "chunk_text": "Resume text chunk...",
    "start_char": 0,
    "end_char": 400,
    "char_count": 400,
    "skills_detected": ["Python", "Django"],
    "filename": "resume.pdf",
    "created_at": "2024-01-15T10:30:00Z"
}
```

**Used By:**
- Pipeline 1: Write (1 profile + 1 skills + N chunks per candidate)
- Pipeline 2 Stage 3: Write (via background worker)
- Pipeline 4: Write (3 vectors per candidate × 8 candidates = 24 total)

---

#### **Collection: `jobs_v1` (for job embeddings)**

**Configuration:**
- Vector size: 384 dimensions
- Distance metric: Cosine similarity
- Model: `sentence-transformers/all-MiniLM-L6-v2`

**Point Structure:**
```python
{
    "id": "{job_id}_profile" or "{job_id}_skills",
    "vector": List[float],  # 384 dimensions
    "payload": Dict[str, Any]
}
```

**Payload Types:**

1. **Job Profile Vector** (`type="profile"`):
```python
{
    "job_id": "UUID-string",
    "type": "profile",
    "title": "Senior Python Engineer",
    "created_at": "2024-01-15T10:30:00Z"
}
```

2. **Job Skills Vector** (`type="skills"`):
```python
{
    "job_id": "UUID-string",
    "type": "skills",
    "skills": ["Python", "Python3", "AWS", "Docker", ...],  # Expanded skills
    "created_at": "2024-01-15T10:30:00Z"
}
```

**Used By:**
- Pipeline 3: Write (2 points per job)
- Pipeline 4: Write (2 vectors per job × 6 jobs = 12 total)

---

### **Redis Schema**

#### **1. Ingestion Queue** (`ingestion_queue`)
- **Type:** LIST
- **Content:** JSON strings with job metadata
- **Operations:** `LPUSH` (add job), `BRPOP` (get job with blocking)

**Format:**
```json
{
    "job_id": "ingest_candidate-uuid_1705314600.123",
    "candidate_id": "UUID",
    "s3_resume_url": "s3://bucket/resumes/...",
    "mode": "full" | "parse_only",
    "event_type": "profile_created" | "profile_updated" | "resume_uploaded"
}
```

**Used By:**
- Pipeline 1: Write (queue job)
- Pipeline 2 Stage 1: Write (queue parse-only job)
- Pipeline 2 Stage 3: Write (queue full job)
- Background Worker: Read (poll for jobs)

---

#### **2. Parsed Candidate Cache** (`parsed_candidate:{temp_id}`)
- **Type:** STRING (JSON)
- **TTL:** 3600 seconds (1 hour)

**Format:**
```json
{
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+1-555-0101",
    "skills": ["Python", "Django"],
    "years_experience": 5.0,
    "location": {
        "city": "San Francisco",
        "region": "CA",
        "country": "US"
    },
    "professional_summary": "...",
    "s3_resume_url": "s3://..."
}
```

**Used By:**
- Pipeline 2 Stage 1: Write (cache parsed data)
- Pipeline 2 Stage 2: Read (retrieve parsed data)
- Pipeline 2 Stage 3: Read (validate), Delete (cleanup)

---

#### **3. Job Rankings Cache** (`job_rankings:{job_id}`)
- **Type:** STRING (JSON)
- **TTL:** 3600 seconds (1 hour)

**Format:**
```json
{
    "job_id": "UUID",
    "qualified_candidate_ids": ["UUID1", "UUID2", ...],
    "total_qualified": 10,
    "computed_at": "2024-01-15T10:30:00Z",
    "gates_applied": {
        "must_have_skills": ["Python"],
        "min_years": 5.0,
        "max_years": 10.0,
        "location": "San Francisco, CA"
    }
}
```

**Used By:**
- Ranking service (not part of ingestion, but uses cached data)

---

#### **4. Job Embeddings Cache** (`job_embeddings:{job_id}`)
- **Type:** STRING (JSON)
- **TTL:** 3600 seconds (1 hour)

**Format:**
```json
{
    "profile_vector": [0.1, -0.2, 0.3, ...],  # 384 floats
    "skills_vector": [0.2, -0.1, 0.4, ...]    # 384 floats
}
```

**Used By:**
- Pipeline 3: Write (cache embeddings)
- Ranking service: Read (retrieve cached embeddings)

---

#### **5. Dead Letter Queue** (`dlq`)
- **Type:** LIST
- **Content:** JSON strings with failed job metadata

**Format:**
```json
{
    "job_id": "ingest_...",
    "candidate_id": "UUID",
    "s3_resume_url": "s3://...",
    "mode": "full",
    "failed_at": "2024-01-15T10:30:00Z",
    "error": "Error message here",
    "final_retry_count": 4
}
```

**Used By:**
- Background Worker: Write (move failed jobs after max retries)

---

### **MinIO Schema**

**Bucket:** `rightstaff-resumes` (or configured bucket name)

**Object Structure:**
- **Path format:** `resumes/{candidate_id}/resume.{ext}`
- **Examples:**
  - `resumes/a1b2c3d4-1234-5678-90ab-cdef12345678/resume.pdf`
  - `resumes/temp-uuid-1234/resume.docx`

**Content Types:**
- `.pdf`: `application/pdf`
- `.docx`: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `.doc`: `application/msword`
- `.txt`: `text/plain`

**Used By:**
- Pipeline 1: Read (download resume)
- Pipeline 2 Stage 1: Write (upload resume)
- Pipeline 2 Stage 3: Read (download resume for full ingestion)
- Pipeline 4: Write (upload 5 test resumes)

---

## Data Flow Diagrams

### **Complete System Data Flow**

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────────┤
│  • Portal Team Webhooks (Candidate/Job updates)                    │
│  • Frontend API Calls (Direct uploads)                             │
│  • Manual Scripts (populate_dummy_data.py)                         │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ├───────────────────────────────────────────────────────┐
               │                                                       │
               ▼                                                       ▼
    ┌──────────────────┐                                  ┌──────────────────┐
    │  Webhook/API     │                                  │  Direct Script   │
    │  Endpoints       │                                  │  Execution       │
    └────────┬─────────┘                                  └────────┬─────────┘
             │                                                     │
             ▼                                                     ▼
    ┌──────────────────┐                                  ┌──────────────────┐
    │  Redis Queue     │                                  │  Direct DB       │
    │  (Async Jobs)    │                                  │  Operations      │
    └────────┬─────────┘                                  └────────┬─────────┘
             │                                                     │
             ▼                                                     │
    ┌──────────────────┐                                          │
    │  Background      │                                          │
    │  Worker          │                                          │
    └────────┬─────────┘                                          │
             │                                                     │
             ├─────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PROCESSING LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Parse       │→ │ Extract      │→ │ Normalize    │             │
│  │ Documents   │  │ Skills       │  │ via Ontology │             │
│  └─────────────┘  └──────────────┘  └──────────────┘             │
│                                            │                       │
│                                            ▼                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Chunk       │→ │ Generate     │→ │ Store        │             │
│  │ Text        │  │ Embeddings   │  │ Vectors      │             │
│  └─────────────┘  └──────────────┘  └──────────────┘             │
│                                                                     │
└────────────���─┬──────────────────────────────────────────────────────┘
               │
               ├───────────────┬─────────────┬──────────────┐
               │               │             │              │
               ▼               ▼             ▼              ▼
      ┌─────────────┐  ┌─────────────┐ ┌──────────┐ ┌──────────┐
      │ PostgreSQL  │  │   Qdrant    │ │  Redis   │ │  MinIO   │
      │             │  │             │ │          │ │          │
      │ • Candidate │  │ • Profile   │ │ • Cache  │ │ • Resumes│
      │ • Jobs      │  │   Vectors   │ │ • Queue  │ │   (PDF/  │
      │ • Skills    │  │ • Skills    │ │ • DLQ    │ │   DOCX)  │
      │ • Apps      │  │   Vectors   │ │          │ │          │
      │             │  │ • Chunks    │ │          │ │          │
      └─────────────┘  └─────────────┘ └──────────┘ └──────────┘
```

---

### **Pipeline 1: Webhook Ingestion - Detailed Workflow**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE 1: WEBHOOK INGESTION                             │
│                    Entry: webhooks.py → candidate_updated_webhook()          │
└─────────────────────────────────────────────────────────────────────────────┘

Portal Team sends HTTP POST
         │
         ▼
┌─────────────────────────────────────┐
│  /api/v1/webhooks/candidate-updated │
│  webhooks.py:28-88                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Validate Request                   │
│  • Check candidate_id exists        │
│  • Check s3_resume_url present      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  Query PostgreSQL                   │────→│  PostgreSQL     │
│  SELECT * FROM candidate            │     │  candidate      │
│  WHERE id = candidate_id            │     │  table          │
└──────────────┬──────────────────────┘     └─────────────────┘
               │
               ▼
        ┌──────────────┐
        │  Candidate   │
        │  exists?     │
        └──────┬───────┘
               │
      ┌────────┴────────┐
      │ NO              │ YES
      ▼                 ▼
┌──────────┐    ┌─────────────────────────────┐
│  Return  │    │  Create ingestion job       │
│  404     │    │  {                          │
└──────────┘    │    job_id: "ingest_...",    │
                │    candidate_id: UUID,      │
                │    s3_resume_url: "s3://",  │
                │    mode: "full",            │
                │    event_type: "..."        │
                │  }                          │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐     ┌─────────────────┐
                │  LPUSH to Redis             │────→│  Redis          │
                │  ingestion_queue            │     │  ingestion_queue│
                └──────────────┬──────────────┘     └─────────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  Return 202 Accepted        │
                │  (immediate response)       │
                └─────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                         BACKGROUND WORKER (Async)
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────┐     ┌─────────────────┐
│  BRPOP from Redis                   │←────│  Redis          │
│  ingestion_queue (blocking)         │     │  ingestion_queue│
│  ingestion.py:173-633               │     └─────────────────┘
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         7-STAGE ENRICHMENT PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐
│  STAGE 1: Fetch Candidate           │
│  ingestion.py:350-380               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  Query PostgreSQL                   │────→│  PostgreSQL     │
│  SELECT * FROM candidate            │     │  candidate      │
│  JOIN candidate_contact             │     │  candidate_contact
│  WHERE id = candidate_id            │     └─────────────────┘
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  STAGE 2: Download Resume           │
│  s3_client.py:download_file()       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  Download from MinIO                │────→│  MinIO          │
│  s3_resume_url → local temp file    │     │  resumes bucket │
└──────────────┬──────────────────────┘     └─────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  STAGE 3: Parse Resume              │
│  parsers.py:parse_resume()          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Unstructured Library               │
│  • Detect file type (PDF/DOCX/TXT)  │
│  • Extract raw text                 │
│  • Clean and normalize              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  STAGE 4: Extract Skills            │
│  skill_extractor.py:extract_skills()│
│  ingestion.py:415-434               │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │  LLM Enabled?    │
        │  (USE_LLM_PARSING)│
        └────────┬─────────┘
                 │
      ┌──────────┴──────────┐
      │ YES                 │ NO
      ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  method="hybrid" │  │  method="spacy"  │
│                  │  │                  │
│  1. LLM extract  │  │  1. spaCy NER    │
│     (llm_parser) │  │     (ontology)   │
│  2. spaCy NER    │  │  2. Normalize    │
│     (ontology)   │  │                  │
│  3. Merge lists  │  │                  │
│  4. Normalize    │  │                  │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Normalized Skills  │
         │  List[str]          │
         └──────────┬──────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│  STAGE 4.5: Store Skills            │
│  ingestion.py:440-490               │
└──────────────┬──────────────────────┘
               │
               ├─────────────────────────────┐
               ▼                             ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│  PostgreSQL: skill table    │  │  PostgreSQL: candidate_skill│
│                             │  │                             │
│  INSERT INTO skill (name)   │  │  DELETE existing links      │
│  ON CONFLICT DO NOTHING     │  │  INSERT new skill links     │
│  (create if not exists)     │  │  (candidate_id, skill_id)   │
└─────────────────────────────┘  └─────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  STAGE 4.6: Store Resume Record     │
│  ingestion.py:495-520               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  PostgreSQL: candidate_resume       │────→│  PostgreSQL     │
│                                     │     │  candidate_resume
│  • Mark old resumes is_latest=false │     └─────────────────┘
│  • INSERT new resume record         │
│    (s3_url, file_type, is_latest)   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  STAGE 5: Chunk Text                │
│  parsers.py:chunk_text()            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Split into overlapping chunks      │
│  • chunk_size: 400 characters       │
│  • overlap: 100 characters          │
│  • Returns: List[Dict] with:        │
│    - chunk_text                     │
│    - chunk_index                    │
│    - start_char, end_char           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  STAGE 6: Generate Embeddings       │
│  embeddings.py:generate_embeddings()│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  sentence-transformers              │
│  all-MiniLM-L6-v2                   │
│                                     │
│  Generate 3 types of vectors:       │
│  1. Profile: full resume text       │
│  2. Skills: skill list joined       │
│  3. Chunks: each chunk separately   │
│                                     │
│  Output: List of 384-dim vectors    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  STAGE 7: Store Vectors             │
│  vector_store.py:upsert_vectors()   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  Qdrant: resumes collection         │────→│  Qdrant         │
│                                     │     │  resumes        │
│  1. Delete old vectors for          │     │  collection     │
│     this candidate_id               │     └─────────────────┘
│  2. Upsert new vectors:             │
│     • 1 profile vector              │
│     • 1 skills vector               │
│     • N chunk vectors               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  ✅ Pipeline Complete               │
│  Log success metrics                │
└─────────────────────────────────────┘
```

---

### **Pipeline 2: API Upload - Detailed Workflow**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE 2: API UPLOAD (3-STAGE PROCESS)                  │
│                    Entry: candidates.py                                      │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                         STAGE 1: UPLOAD & PARSE-ONLY
═══════════════════════════════════════════════════════════════════════════════

User uploads file via frontend
         │
         ▼
┌─────────────────────────────────────┐
│  POST /api/v1/candidates/upload-resume
│  candidates.py:66-186               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Validate file                      │
│  • Check file size (< 10MB)         │
│  • Check extension (.pdf/.docx/.txt)│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Generate temp_id                   │
│  temp_id = uuid.uuid4()             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  Upload to MinIO                    │────→│  MinIO          │
│  Path: resumes/{temp_id}/resume.ext │     │  resumes bucket │
└──────────────┬──────────────────────┘     └─────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Create parse-only job              │
│  {                                  │
│    job_id: "parse_...",             │
│    candidate_id: temp_id,           │ ← Note: temp_id, not real candidate_id
│    s3_resume_url: "s3://...",       │
│    mode: "parse_only",              │
│    event_type: "upload"             │
│  }                                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  LPUSH to Redis                     │────→│  Redis          │
│  ingestion_queue                    │     │  ingestion_queue│
└──────────────┬──────────────────────┘     └─────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Poll for completion                │
│  (30 second timeout)                │
└──────────────┬──────────────────────┘
               │
               │ (Meanwhile, background worker processes...)
               │
               ▼

═══════════════════════════════════════════════════════════════════════════════
                    BACKGROUND WORKER - PARSE-ONLY MODE
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────┐     ┌─────────────────┐
│  BRPOP from Redis                   │←────│  Redis          │
│  ingestion_queue                    │     │  ingestion_queue│
│  ingestion.py:173-340               │     └─────────────────┘
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │  mode ==         │
        │  "parse_only"?   │
        └────────┬─────────┘
                 │ YES
                 ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  Download from MinIO                │────→│  MinIO          │
│  s3_resume_url → local temp file    │     │  resumes bucket │
└──────────────┬──────────────────────┘     └─────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Parse resume text                  │
│  parsers.py:parse_resume()          │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │  LLM Enabled?    │
        └────────┬─────────┘
                 │
      ┌──────────┴──────────┐
      │ YES                 │ NO
      ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  LLM Parser      │  │  Regex Extraction│
│  llm_parser.py   │  │  parsers.py      │
│                  │  │                  │
│  Extract ALL:    │  │  extract_name()  │
│  • full_name     │  │  extract_email() │
│  • email         │  │  extract_phone() │
│  • phone         │  │  etc.            │
│  • location      │  │                  │
│  • years_exp     │  │                  │
│  • summary       │  │                  │
│  • skills        │  │                  │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│  Extract skills (unified)           │
│  skill_extractor.py:extract_skills()│
│  method="hybrid" or "spacy"         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Build parsed_data dict             │
│  {                                  │
│    full_name: "John Doe",           │
│    email: "john@example.com",       │
│    phone: "+1-555-1234",            │
│    location: {city, region, country}│
│    years_experience: 5.0,           │
│    professional_summary: "...",     │
│    skills: ["Python", "Django"],    │
│    s3_resume_url: "s3://..."        │
│  }                                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  Cache in Redis                     │────→│  Redis          │
│  Key: parsed_candidate:{temp_id}    │     │  TTL: 1 hour    │
│  Value: JSON(parsed_data)           │     └─────────────────┘
└─────────────────────────────────────┘
               │
               │ (Back to API endpoint polling...)
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  GET from Redis cache               │←────│  Redis          │
│  parsed_candidate:{temp_id}         │     │  cache          │
└──────────────┬──────────────────────┘     └─────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Return to frontend                 │
│  {                                  │
│    temp_id: "uuid",                 │
│    parsed_data: {...},              │
│    message: "Resume parsed..."      │
│  }                                  │
└─────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                    STAGE 2: GET PARSED DATA (Form Pre-Fill)
═══════════════════════════════════════════════════════════════════════════════

Frontend requests parsed data
         │
         ▼
┌─────────────────────────────────────┐
│  GET /api/v1/candidates/parsed/{id} │
│  candidates.py:193-247              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  GET from Redis                     │────→│  Redis          │
│  Key: parsed_candidate:{temp_id}    │     │  cache          │
└──────────────┬──────────────────────┘     └─────────────────┘
               │
               ▼
        ┌──────────────────┐
        │  Data exists?    │
        └────────┬─────────┘
                 │
      ┌──────────┴──────────┐
      │ NO                  │ YES
      ▼                     ▼
┌──────────┐        ┌─────────────────────┐
│  Return  │        │  Return parsed_data │
│  404     │        │  (for form pre-fill)│
└──────────┘        └─────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                    STAGE 3: CREATE CANDIDATE (Full Ingestion)
═══════════════════════════════════════════════════════════════════════════════

User submits form with edits
         │
         ▼
┌─────────────────────────────────────┐
│  POST /api/v1/candidates/           │
│  candidates.py:254-389              │
│  Body: {temp_id, full_name, ...}    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐     ┌─────────────────┐
│  Validate temp_id in Redis          │────→│  Redis          │
│  Key: parsed_candidate:{temp_id}    │     │  cache          │
└──────────────┬──────────────────────┘     └─────────────────┘
               │
               ▼
        ┌──────────────────┐
        │  temp_id valid?  │
        └────────┬─────────┘
                 │
      ┌──────────┴──────────┐
      │ NO                  │ YES
      ▼                     ▼
┌──────────┐        ┌─────────────────────────────┐
│  Return  │        │  Create Candidate in        │
│  400     │        │  PostgreSQL                 │
└──────────┘        │                             │
                    │  candidate_id = uuid4()     │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
         ┌─────────────────────┐     ┌─────────────────────┐
         │  PostgreSQL:        │     │  PostgreSQL:        │
         │  candidate table    │     │  candidate_contact  │
         │                     │     │                     │
         │  INSERT candidate   │     │  INSERT contact     │
         │  • id (new UUID)    │     │  • candidate_id     │
         │  • full_name        │     │  • email, phone     │
         │  • years_experience │     │  • city, region     │
         │  • summary          │     │  • country          │
         └─────────────────────┘     └─────────────────────┘
                    │
                    ▼
         ┌─────────────────────────────┐
         │  Rename MinIO file          │
         │  resumes/{temp_id}/...      │
         │        ↓                    │
         │  resumes/{candidate_id}/... │
         └──────────────┬──────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐
         │  Create FULL ingestion job  │
         │  {                          │
         │    candidate_id: NEW UUID,  │ ← Now real candidate_id
         │    s3_resume_url: updated,  │
         │    mode: "full",            │
         │    event_type: "created"    │
         │  }                          │
         └──────────────┬──────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐     ┌─────────────────┐
         │  LPUSH to Redis             │────→│  Redis          │
         │  ingestion_queue            │     │  ingestion_queue│
         └──────────────┬──────────────┘     └─────────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐     ┌─────────────────┐
         │  DELETE from Redis          │────→│  Redis          │
         │  parsed_candidate:{temp_id} │     │  (cleanup cache)│
         └──────────────┬──────────────┘     └─────────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐
         │  Return to frontend         │
         │  {                          │
         │    id: candidate_id,        │
         │    full_name: "...",        │
         │    message: "Created..."    │
         │  }                          │
         └─────────────────────────────┘
                        │
                        │ (Background worker processes FULL pipeline...)
                        │
                        ▼
         ┌─────────────────────────────┐
         │  Same 7-STAGE PIPELINE      │
         │  as Pipeline 1              │
         │  (see above)                │
         │                             │
         │  Creates:                   │
         │  • Skills in PostgreSQL     │
         │  • Resume record            │
         │  • Vectors in Qdrant        │
         └─────────────────────────────┘
```

---

### **Key Differences Between Pipelines**

| Aspect | Pipeline 1 (Webhook) | Pipeline 2 (API Upload) |
|--------|---------------------|------------------------|
| **Trigger** | Portal team webhook | User file upload |
| **Candidate Creation** | Portal creates first | Stage 3 creates candidate |
| **Parse-Only Mode** | Never | Stage 1 only |
| **Form Pre-Fill** | No | Yes (Stage 2) |
| **User Edits** | No | Yes (before Stage 3) |
| **Same 7-Stage Pipeline** | Yes | Yes (in Stage 3) |

---

## Universal Variable Names & Consistency

To ensure data integrity across all pipelines, these naming conventions are strictly followed:

### **1. Candidate Identification**
- **Variable:** `candidate_id`
- **Type:** UUID (stored as UUID in PostgreSQL, converted to string in Qdrant)
- **Consistency:** Always use `candidate_id`, never `candidate_uuid` or `cand_id`

### **2. Resume Files**
- **Variable:** `s3_url` or `s3_resume_url`
- **Format:** Full S3/MinIO URL
- **Examples:**
  - `s3://rightstaff-resumes/resumes/candidate-uuid/resume.pdf`
  - `http://minio:9000/rightstaff-resumes/resumes/candidate-uuid/resume.pdf`

### **3. Skills**
- **Type:** Always `List[str]` (never dict, never JSON string)
- **Normalization:** All skills normalized through ontology
- **Examples:** `["Python", "Django", "PostgreSQL"]`
- **Canonical names:** Use official names (e.g., "JavaScript" not "JS")

### **4. Location**
- **PostgreSQL:** Separate fields (city, region, country)
- **Qdrant/Redis:** Can be dict or separate fields
- **Consistency:** Both LLM and regex return dict format:
  ```python
  {
      "city": "San Francisco",
      "region": "CA",  # NOT "state"!
      "country": "US"
  }
  ```

### **5. Job Metadata**
- **Variable:** `job_id` (UUID string)
- **Skills:**
  - `required_skills` or `required_skills_json` (List[str] or JSONB)
  - `must_have_skills` or `must_have_skills_json` (List[str] or JSONB)

### **6. Vector Metadata**
- **Candidate vectors:**
  - `kind`: "profile" | "skills" | "chunk"
  - `candidate_id`: Always string in Qdrant
- **Job vectors:**
  - `type`: "profile" | "skills"
  - `job_id`: Always string in Qdrant

### **7. Timestamps**
- **PostgreSQL:** TIMESTAMP (timezone-aware)
- **Qdrant/Redis:** ISO 8601 string format
- **Example:** `"2024-01-15T10:30:00Z"`
- **Function:** Always use `datetime.utcnow().isoformat()`

---

## Schema Consistency Verification

### **Verification Checklist**

#### ✅ **PostgreSQL Consistency**
- [ ] All UUID fields use `UUID` type (not VARCHAR)
- [ ] Location uses `region` field (not "state")
- [ ] Skills stored in `candidate_skill` table (many-to-many)
- [ ] All timestamps use `TIMESTAMP` type
- [ ] Foreign keys cascade on delete (`ON DELETE CASCADE`)

#### ✅ **Qdrant Consistency**
- [ ] All vectors are 384 dimensions (sentence-transformers model)
- [ ] Candidate vectors use `kind` field ("profile", "skills", "chunk")
- [ ] Job vectors use `type` field ("profile", "skills")
- [ ] All `candidate_id` and `job_id` converted to strings
- [ ] Skills arrays contain only normalized canonical names

#### ✅ **Redis Consistency**
- [ ] Job queue uses LIST type with `LPUSH`/`BRPOP`
- [ ] Cache keys follow pattern: `{category}:{id}`
- [ ] All cached data has TTL set (no infinite cache)
- [ ] JSON strings are valid and properly formatted

#### ✅ **MinIO Consistency**
- [ ] All resume paths follow: `resumes/{candidate_id}/resume.{ext}`
- [ ] Content types correctly set based on file extension
- [ ] File names preserve original extension

### **Cross-Pipeline Consistency**

#### **Skill Extraction:**
- ✅ Pipeline 1: Extracts via spaCy + patterns → normalizes → stores in PostgreSQL + Qdrant
- ✅ Pipeline 2 Stage 1: Extracts via LLM/regex → normalizes → caches in Redis
- ✅ Pipeline 2 Stage 3: Uses cached skills → stores in PostgreSQL via full pipeline
- ✅ Pipeline 3: Expands via ontology → stores in Qdrant
- ✅ Pipeline 4: Hardcoded skills → normalizes → stores in PostgreSQL + Qdrant

**Result:** All pipelines use same normalization function (`normalize_skill()` from ontology.py)

#### **Location Format:**
- ✅ LLM parser returns: `{"city": str, "region": str, "country": str}`
- ✅ Regex parser returns: `{"city": str, "region": str, "country": str}`
- ✅ PostgreSQL stores: Separate columns (city, region, country)
- ✅ Qdrant stores: In payload (flexible format)

**Result:** Both extraction methods return same format, mapping correctly to DB schema

#### **Candidate ID:**
- ✅ PostgreSQL: UUID type
- ✅ Qdrant: Converted to string
- ✅ Redis: String in JSON
- ✅ MinIO: String in file path

**Result:** Consistent UUID handling across all databases

---

## Testing & Verification

See [TESTING_INGESTION_PIPELINES.md](./TESTING_INGESTION_PIPELINES.md) for:
- Commands to test each pipeline
- Database verification queries
- Expected outputs and schemas
- Troubleshooting guide

---

## Summary

### **Pipeline Comparison Table**

| Pipeline | Entry Point | Trigger | PostgreSQL | Qdrant | Redis | MinIO | Mode |
|----------|------------|---------|------------|--------|-------|-------|------|
| **1. Webhook** | webhooks.py | Portal webhook | Read, Write | Write | Write, Read | Read | FULL |
| **2. API Upload (Stage 1)** | candidates.py | User upload | - | - | Write | Write | PARSE_ONLY |
| **2. API Upload (Stage 2)** | candidates.py | Form pre-fill | - | - | Read | - | - |
| **2. API Upload (Stage 3)** | candidates.py | Form submit | Write | Write* | Write, Delete | Read* | FULL |
| **3. Job Webhook** | webhooks.py | Portal webhook | - | Write | Write | - | - |
| **4. Dummy Data** | populate_dummy_data.py | Manual script | Write | Write | - | Write | - |

*Via background worker

### **Database Write Summary**

| Database | Pipeline 1 | Pipeline 2 | Pipeline 3 | Pipeline 4 |
|----------|-----------|-----------|-----------|-----------|
| **PostgreSQL** | Skills, Resume metadata | Candidate, Contact | - | All tables |
| **Qdrant** | Profile, Skills, Chunks | Profile, Skills, Chunks* | Profile, Skills | All vectors |
| **Redis** | Queue job | Queue + Cache | Cache embeddings | - |
| **MinIO** | - | Upload file | - | Upload files |

*Via background worker

---

## Skill Extraction Module Hierarchy

### **Understanding the 3 Modules**

The skill extraction system uses a **3-layer architecture** for maximum flexibility:

```
┌─────────────────────────────────────────────┐
│         llm_parser.py                       │
│  (Resume-level LLM extraction)              │
│                                              │
│  Purpose: Parse ENTIRE resume using LLM     │
│  Extracts: name, email, phone, location,    │
│           years_exp, summary, skills         │
│                                              │
│  When: Parse-only mode (Pipeline 2 Stage 1) │
│        Full mode (Pipeline 1 & 2 Stage 3)   │
└─────────────────┬───────────────────────────┘
                  │
                  │ calls for skills only
                  ↓
┌─────────────────────────────────────────────┐
│       skill_extractor.py                    │
│  (Unified skill extraction interface)       │
│                                              │
│  Purpose: Extract & normalize skills        │
│  Methods: "hybrid", "llm", "spacy"          │
│                                              │
│  When: Whenever skills need extraction      │
└─────────────────┬───────────────────────────┘
                  │
                  ├──── method="llm" ────→ calls llm_parser.py
                  │                        (gets skills from LLM)
                  │
                  ├──── method="spacy" ──→ calls ontology.py
                  │                        (uses spaCy NER)
                  │
                  └──── method="hybrid" ─→ calls BOTH
                                           (merges results)
                  │
                  ↓ (all methods)
                  │
                  ↓ normalize through
                  │
┌─────────────────────────────────────────────┐
│          ontology.py                        │
│  (Low-level skill extraction & taxonomy)    │
│                                              │
│  Purpose: spaCy NER + pattern matching      │
│  Functions:                                  │
│    - extract_skills_from_text() [spaCy]    │
│    - normalize_skill() [taxonomy lookup]    │
│    - expand_skills() [find variants]       │
│                                              │
│  When: Called by skill_extractor.py         │
└─────────────────────────────────────────────┘
```

---

### **Module Details**

#### **1. `ontology.py` - Foundation Layer**

**Location:** `backend/app/services/ontology.py`

**Purpose:** Low-level skill extraction and normalization

**Key Functions:**
- `extract_skills_from_text(text: str) -> List[str]`
  - Uses spaCy NER to find SKILL entities
  - Pattern matching (regex) for common skills
  - Returns raw skill list

- `normalize_skill(skill: str) -> str`
  - Normalizes skill names ("javascript" → "JavaScript")
  - Uses taxonomy to map variants ("JS" → "JavaScript")

- `expand_skills(skills: List[str]) -> List[str]`
  - Finds skill variants ("Python" → ["Python", "Python3"])

**When Called:**
- By `skill_extractor.py` when `method="spacy"`
- For normalization (all methods)

**Invoked By FastAPI Endpoints:**
- Not directly invoked by API endpoints
- Called through the skill extraction chain:
  - `POST /api/v1/webhooks/candidate-updated` → `ingestion.py` → `skill_extractor.py` → `ontology.py`
  - `POST /api/v1/candidates/upload-resume` → `ingestion.py` → `skill_extractor.py` → `ontology.py`
  - `POST /api/v1/candidates/` → `ingestion.py` → `skill_extractor.py` → `ontology.py`

---

#### **2. `skill_extractor.py` - Unified Interface**

**Location:** `backend/app/services/skill_extractor.py`

**Purpose:** High-level abstraction - ONE interface for all extraction methods

**Key Function:**
```python
async def extract_skills(
    text: str,
    method: Literal["hybrid", "llm", "spacy"] = "hybrid",
    normalize: bool = True
) -> List[str]:
    """
    Main entry point for skill extraction.

    method="hybrid": LLM + spaCy (best accuracy, ~90%)
    method="llm": LLM only (good accuracy, ~85%)
    method="spacy": spaCy only (baseline, ~70%)
    """
```

**Workflow:**
1. Extract raw skills based on method
2. Normalize ALL skills through ontology
3. Return consistent format: `List[str]`

**When Called:**
- By `ingestion.py` (parse-only and full modes)
- Anywhere skills need extraction

**Invoked By FastAPI Endpoints:**
- `POST /api/v1/webhooks/candidate-updated` ([webhooks.py](backend/app/api/webhooks.py))
  → `enqueue_job()` → background worker → `ingestion.py` → `skill_extractor.py`
- `POST /api/v1/candidates/upload-resume` ([candidates.py](backend/app/api/candidates.py))
  → `ingestion.py` → `skill_extractor.py`
- `POST /api/v1/candidates/` ([candidates.py](backend/app/api/candidates.py))
  → `ingestion.py` → `skill_extractor.py`

---

#### **3. `llm_parser.py` - LLM Resume Parser**

**Location:** `backend/app/services/llm_parser.py`

**Purpose:** Extract ALL fields from resume using LLM

**Key Function:**
```python
class LLMResumeParser:
    async def parse_resume(self, resume_text: str) -> Dict:
        """
        Extract ALL fields using LLM.

        Returns:
        {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-1234",
            "location": {"city": "SF", "region": "CA", "country": "US"},
            "years_experience": 5.0,
            "professional_summary": "...",
            "skills": ["Python", "Django", "AWS"]
        }
        """
```

**When Called:**
- By `ingestion.py` in parse-only mode
- By `skill_extractor.py` when `method="llm"` or `method="hybrid"`

**Invoked By FastAPI Endpoints:**
- `POST /api/v1/webhooks/candidate-updated` ([webhooks.py](backend/app/api/webhooks.py))
  → `enqueue_job()` → background worker → `ingestion.py` → `llm_parser.py` (when `USE_LLM_PARSING=true`)
- `POST /api/v1/candidates/upload-resume` ([candidates.py](backend/app/api/candidates.py))
  → `ingestion.py` → `llm_parser.py` (parse-only mode)
- `POST /api/v1/candidates/` ([candidates.py](backend/app/api/candidates.py))
  → `ingestion.py` → `llm_parser.py` (full mode)

---

### **Call Flow Examples**

#### **Example 1: Pipeline 1 with LLM Enabled**
```python
# In ingestion.py (full mode)

# Step 1: Extract skills using unified interface
if settings.use_llm_parsing:
    skills = await extract_skills(text, method="hybrid")
    # This internally:
    #   1. Calls llm_parser.parse_resume() for LLM skills
    #   2. Calls ontology.extract_skills_from_text() for spaCy skills
    #   3. Merges both lists
    #   4. Normalizes through ontology.normalize_skill()
else:
    skills = await extract_skills(text, method="spacy")
    # This internally:
    #   1. Calls ontology.extract_skills_from_text()
    #   2. Normalizes through ontology.normalize_skill()
```

#### **Example 2: Pipeline 2 Stage 1 (Parse-Only)**
```python
# In ingestion.py (parse_only mode)

# Step 1: Use LLM to parse entire resume
if settings.use_llm_parsing:
    llm_result = await llm_parser.parse_resume(text)
    # Returns: {full_name, email, phone, skills, ...}

    # Step 2: Extract skills using hybrid method
    skills = await extract_skills(text, method="hybrid")
else:
    # Fallback to regex for fields
    full_name = extract_name(text)
    email = extract_email(text)
    # ...

    # Extract skills using spaCy only
    skills = await extract_skills(text, method="spacy")
```

---

### **Configuration**

All pipelines respect the `USE_LLM_PARSING` setting:

**Enable LLM Parsing:**
```bash
# In .env or environment
USE_LLM_PARSING=true
LLM_PARSER_MODEL=Qwen/Qwen2-1.5B-Instruct
```

**Disable LLM Parsing (Default):**
```bash
USE_LLM_PARSING=false
```

---

### **Why This Architecture?**

1. **Flexibility:** Change extraction method with ONE line
2. **Consistency:** All methods return same format
3. **Fallback:** Graceful degradation (LLM → spaCy → regex)
4. **Maintainability:** Each module has clear responsibility
5. **Performance:** Can switch based on accuracy needs

---

**Document Version:** 1.3
**Last Updated:** 2025-11-19
**Maintained By:** RightStaff Development Team
