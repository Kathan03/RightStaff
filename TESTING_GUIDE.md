# 🧪 RightStaff Comprehensive Testing Guide

**Last Updated**: 2025-11-17
**Version**: 2.0 (Day-5 Complete - Application Tracking + Resume Upload + Job Embeddings)

---

## 📋 Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [API Endpoints Reference](#api-endpoints-reference)
- [Feature Testing](#feature-testing)
- [End-to-End Workflows](#end-to-end-workflows)
- [Unit & Integration Tests](#unit--integration-tests)
- [Performance Testing](#performance-testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

This guide provides comprehensive testing coverage for the RightStaff AI candidate ranking system, covering all implemented features from Days 1-5.

### Current Implementation Status

**✅ Fully Implemented (Days 1-5):**
- Resume ingestion pipeline (7-stage)
- Application tracking system
- Resume-first upload workflow
- Job embeddings optimization
- Semantic ranking with dual embeddings
- Ontology-based skill filtering
- Score blending and candidate banding
- Explainable results with evidence

**⏳ Planned (Days 6-12):**
- Cross-encoder re-ranking
- WebSocket chatbot with RAG
- LLM-powered explanations

### Testing Philosophy

- **Unit Tests**: Test components in isolation (`pytest`)
- **Integration Tests**: Test component interactions (`pytest -m integration`)
- **API Tests**: Test HTTP endpoints (`curl` or `pytest`)
- **E2E Tests**: Test complete user workflows (manual or scripted)
- **Performance Tests**: Benchmark latency and throughput

---

## Quick Start

**Note for Windows PowerShell Users:** All `curl` commands in this guide work on Windows PowerShell. For commands with JSON payloads, you can either:
1. Save JSON to a file and use `curl.exe -d "@file.json"` (recommended)
2. Use PowerShell's `Invoke-RestMethod` instead of curl

### 1. Verify Infrastructure

```bash
# Start all services (Unix/Mac)
cd /home/user/RightStaff
docker-compose -f docker/docker-compose.yml up -d

# Windows PowerShell
cd C:\Users\YourName\Documents\RightStaff
docker-compose -f docker/docker-compose.yml up -d

# Wait for services (30 seconds)
sleep 30  # Unix/Mac
Start-Sleep -Seconds 30  # PowerShell

# Check health
curl http://localhost:8000/health

# Or with PowerShell's native command:
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Expected response:
# {
#   "status": "healthy",
#   "services": {
#     "api": "ok",
#     "database": "ok",
#     "qdrant": "ok",
#     "redis": "ok",
#     "minio": "ok"
#   }
# }
```

### 2. Populate Test Data

```bash
cd backend

# Clear existing data
python clear_all_data.py

# Populate dummy data
python populate_dummy_data.py

# Expected output:
# ✅ Created 8 candidates
# ✅ Created 49 skills
# ✅ Created 55 candidate-skill mappings
# ✅ Created 5 resumes in MinIO
# ✅ Created 30 applications
# ✅ Created embeddings for 5 jobs
```

### 3. Run Quick Smoke Test

```bash
# Quick API test
python test_api_quick.py

# Expected: All endpoints return 200/201/202
```

---

## Prerequisites

### Required Services

- **Docker Desktop** with WSL2 (Windows) or Docker Engine (Linux)
- **PostgreSQL** (port 5432)
- **Qdrant** (port 6333)
- **Redis** (port 6379)
- **MinIO** (ports 9000, 9001)
- **Python 3.11+** with venv

### Required Python Packages

```bash
pip install -r requirements.txt

# Key dependencies:
# - fastapi, uvicorn
# - sqlalchemy, asyncpg
# - qdrant-client
# - redis, minio
# - sentence-transformers
# - spacy (with en_core_web_sm)
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://right_staff:right_staff@localhost:5432/rightstaff

# Qdrant
QDRANT_URL=http://localhost:6333

# Redis
REDIS_URL=redis://localhost:6379

# MinIO
MINIO_URL=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

---

## API Endpoints Reference

### Health & Monitoring

#### GET /health
**Purpose**: Check service health
**Auth**: None
**Response**: Service status for all dependencies

```bash
curl http://localhost:8000/health | jq
```

**Expected Response**:
```json
{
  "status": "healthy",
  "services": {
    "api": "ok",
    "database": "ok",
    "qdrant": "ok",
    "redis": "ok",
    "minio": "ok"
  },
  "timestamp": "2025-11-17T12:00:00Z"
}
```

---

#### GET /api/v1/admin/metrics
**Purpose**: Get system metrics
**Auth**: Admin
**Response**: Counters, timings, system info

```bash
curl http://localhost:8000/api/v1/admin/metrics | jq
```

**Expected Response**:
```json
{
  "counters": {
    "jobs_processed": 150,
    "jobs_failed": 2
  },
  "timings": {
    "parse_stage_avg_ms": 250,
    "embed_stage_avg_ms": 1200
  },
  "system": {
    "embedding_model": "all-MiniLM-L6-v2",
    "qdrant_collection": {
      "vectors_count": 8,
      "indexed_vectors_count": 8
    },
    "spacy_ner": {
      "available": true,
      "status": "enabled"
    }
  }
}
```

---

#### GET /api/v1/admin/health/detailed
**Purpose**: Detailed health with worker stats
**Auth**: Admin
**Response**: Worker metrics, queue depths

```bash
curl http://localhost:8000/api/v1/admin/health/detailed | jq
```

---

#### GET /api/v1/admin/dlq
**Purpose**: View Dead Letter Queue (failed jobs)
**Auth**: Admin
**Response**: DLQ depth and sample entries

```bash
curl http://localhost:8000/api/v1/admin/dlq | jq
```

---

#### POST /api/v1/admin/dlq/replay
**Purpose**: Replay failed jobs from DLQ
**Auth**: Admin
**Response**: Number of jobs replayed

```bash
curl -X POST http://localhost:8000/api/v1/admin/dlq/replay | jq
```

---

#### POST /api/v1/admin/dlq/clear
**Purpose**: Clear all DLQ entries (destructive!)
**Auth**: Admin
**Response**: Number of entries deleted

```bash
curl -X POST http://localhost:8000/api/v1/admin/dlq/clear | jq
```

---

### Candidate Management

#### POST /api/v1/candidates/upload-resume
**Purpose**: Anonymous resume upload (Stage 1 - Parse Only)
**Auth**: None
**Body**: Multipart form with resume file
**Response**: temp_id + parsed data

```bash
# Create test resume
echo "John Doe
Software Engineer
john.doe@example.com
(123) 456-7890

SKILLS:
Python, FastAPI, Docker, PostgreSQL
" > ../resumes/test_resume.txt

# Upload resume
curl.exe -X POST "http://localhost:8000/api/v1/candidates/upload-resume" -F "file=@../resumes/test_resume.txt" | jq

# Expected response:
# {
#   "temp_id": "550e8400-e29b-41d4-a716-446655440000",
#   "parsed_data": {
#     "full_name": "John Doe",
#     "email": "john.doe@example.com",
#     "phone": "(123) 456-7890",
#     "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
#     "years_experience": null,
#     "location": null,
#     "professional_summary": "John Doe\nSoftware Engineer..."
#   },
#   "message": "Resume parsed successfully..."
# }
```

**What It Tests**:
- ✅ File upload to MinIO
- ✅ Parse-only ingestion mode
- ✅ Field extraction (name, email, phone, skills)
- ✅ Redis caching (1-hour TTL)
- ✅ NO PostgreSQL/Qdrant ingestion yet

---

#### GET /api/v1/candidates/parsed/{temp_id}
**Purpose**: Fetch parsed data for form pre-fill (Stage 2)
**Auth**: None
**Response**: Cached parsed data

```bash
TEMP_ID="<temp_id_from_upload>"
$TEMP_ID="239e28a2-4593-44c1-a50d-df89688c656a"

curl.exe "http://localhost:8000/api/v1/candidates/parsed/${TEMP_ID}" | jq

# Expected response:
# {
#   "temp_id": "550e8400-e29b-41d4-a716-446655440000",
#   "data": {
#     "full_name": "John Doe",
#     "email": "john.doe@example.com",
#     ...
#   }
# }
```

**What It Tests**:
- ✅ Redis cache retrieval
- ✅ Session expiration (404 after 1 hour)
- ✅ Form pre-fill data format

---

#### POST /api/v1/candidates
**Purpose**: Create candidate after form submission (Stage 3 - Full Ingestion)
**Auth**: None
**Body**: JSON with temp_id + form data
**Response**: candidate_id + ingestion status

```bash
TEMP_ID="<temp_id_from_upload>"
$TEMP_ID="74c36745-4978-43f5-9d98-b2a85154d726"

$body = @{
    temp_id = $TEMP_ID
    full_name = "John Doe"
    email = "john.doe@example.com"
    phone = "(123) 456-7890"
    years_experience = 5.0
    professional_summary = "Senior Python Developer"
    location = "Austin, TX"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/candidates/" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

# Expected response:
# {
#   "candidate
_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "ingestion_queued",
#   "message": "Candidate created successfully. Full ingestion in progress."
# }
```

**What It Tests**:
- ✅ Candidate creation in PostgreSQL
- ✅ Contact record creation
- ✅ Full 7-stage ingestion trigger
- ✅ Redis cache cleanup
- ✅ Reuse of temp_id as candidate_id

---

### Job Management

#### POST /api/v1/jobs
**Purpose**: Create a job posting
**Auth**: None
**Body**: JSON with job details
**Response**: job_id

```bash
$body = @{
    title = "Senior Python Engineer"
    description = "Build scalable AI systems with FastAPI, PostgreSQL, and Qdrant"
    required_skills = @("Python", "FastAPI", "PostgreSQL", "Docker")
    must_have_skills = @("Python", "FastAPI")
    min_years_experience = 3
    max_years_experience = 10
    location = "Austin, TX"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/jobs" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

# Expected response:
# {
#   "job_id": "123e4567-e89b-12d3-a456-426614174000",
#   "title": "Senior Python Engineer",
#   "status": "created"
# }
```

---

#### POST /api/v1/jobs/{job_id}/apply
**Purpose**: Submit job application (PROMPT_1 feature)
**Auth**: None
**Body**: Query parameter with candidate_id
**Response**: application_id + status

```bash
$JOB_ID="<job_id_from_create>"
$JOB_ID="6bdddf07-6e2b-4c8d-9114-527d7fbf9dca"
$CANDIDATE_ID="<candidate_id_from_create>"
$CANDIDATE_ID="239e28a2-4593-44c1-a50d-df89688c656a"

curl.exe -X POST "http://localhost:8000/api/v1/jobs/$JOB_ID/apply?candidate_id=$CANDIDATE_ID" -H "Content-Type: application/json" | jq

# Expected response (201 Created):
# {
#   "application_id": "789e4567-e89b-12d3-a456-426614174000",
#   "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
#   "job_id": "123e4567-e89b-12d3-a456-426614174000",
#   "status": "applied",
#   "applied_at": "2025-11-17T12:00:00Z",
#   "message": "Application submitted successfully for Senior Python Engineer"
# }

# Test duplicate application (should return 409 Conflict)
curl.exe -X POST "http://localhost:8000/api/v1/jobs/$JOB_ID/apply?candidate_id=$CANDIDATE_ID" -H "Content-Type: application/json" | jq

# Expected response (409 Conflict):
# {
#   "detail": "Candidate 'John Doe' already applied to 'Senior Python Engineer' (application_id: ..., status: applied)"
# }
```

**What It Tests**:
- ✅ Application creation
- ✅ Duplicate prevention (UNIQUE constraint)
- ✅ Job status validation (only open jobs)
- ✅ Candidate existence validation

---

#### POST /api/v1/jobs/rank
**Purpose**: Rank candidates for a job (SQL gating only)
**Auth**: None
**Body**: JSON with job_id
**Response**: Ranked candidates

```bash
$body = @{
    job_id = $JOB_ID
    use_cache = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/jobs/rank" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

---

#### POST /api/v1/jobs/{job_id}/rank_full
**Purpose**: Full semantic ranking (SQL + Dense + Structured scoring)
**Auth**: None
**Body**: Optional use_cache parameter
**Response**: Ranked candidates with scores and explanations

```bash
$body = @{
    use_cache = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/jobs/$JOB_ID/rank_full" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

# Expected response:
# {
#   "job_id": "123e4567-e89b-12d3-a456-426614174000",
#   "candidates": [
#     {
#       "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
#       "rank": 1,
#       "score": 0.87,
#       "band": "high",
#       "scores_breakdown": {
#         "dense": 0.82,
#         "structured": 0.91,
#         "completeness": 0.88
#       },
#       "explanation": "Strong match: 5 years Python experience, FastAPI expert...",
#       "evidence": [
#         "Built RESTful APIs with FastAPI (resume chunk #3)",
#         "5 years Python development (resume chunk #1)"
#       ]
#     }
#   ],
#   "total_applicants": 10,
#   "eligible_after_gates": 8,
#   "latency_ms": 1250
# }
```

**What It Tests**:
- ✅ Application-filtered ranking (only ranks applicants)
- ✅ SQL gates (must-have skills, years, location)
- ✅ Dense retrieval (semantic search in Qdrant)
- ✅ Structured scoring (years, completeness)
- ✅ Score blending (40% dense + 35% structured + 25% completeness)
- ✅ Candidate banding (High/Medium/Low)
- ✅ Explanation generation
- ✅ Pre-computed job embeddings (from jobs_v1 collection)

---

### Webhooks

#### POST /api/v1/webhooks/candidate-updated
**Purpose**: Receive candidate updates from Portal team
**Auth**: None (in production: webhook secret)
**Body**: JSON with event details
**Response**: 202 Accepted with job_id

```bash
# Unix/Mac/Linux
curl -X POST "http://localhost:8000/api/v1/webhooks/candidate-updated" \
  -H "Content-Type: application/json" \
  -d "{
    \"event_type\": \"resume_uploaded\",
    \"candidate_id\": \"${CANDIDATE_ID}\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"s3_resume_url\": \"resumes/${CANDIDATE_ID}/resume.pdf\",
    \"profile_snapshot\": {}
  }" \
  | jq

# Windows PowerShell
$CANDIDATE_ID = "your-candidate-id-here"
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

@"
{
  "event_type": "resume_uploaded",
  "candidate_id": "$CANDIDATE_ID",
  "timestamp": "$timestamp",
  "s3_resume_url": "resumes/$CANDIDATE_ID/resume.pdf",
  "profile_snapshot": {}
}
"@ | Out-File -FilePath candidate_payload.json -Encoding UTF8 -NoNewline

curl.exe -X POST "http://localhost:8000/api/v1/webhooks/candidate-updated" `
  -H "Content-Type: application/json" `
  -d "@candidate_payload.json"

# Expected response (202 Accepted):
# {
#   "status": "accepted",
#   "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
#   "processing_job_id": "ingest_550e8400_...",
#   "estimated_completion_seconds": 30
# }
```

**What It Tests**:
- ✅ Webhook validation
- ✅ Candidate existence check
- ✅ Job queuing in Redis
- ✅ Async processing (returns immediately)

---

#### POST /api/v1/webhooks/job-ingestion
**Purpose**: Pre-compute job embeddings at job creation (PROMPT_3 feature)
**Auth**: None
**Body**: JSON with job details
**Response**: Embeddings created confirmation

```bash
# Unix/Mac/Linux
curl -X POST "http://localhost:8000/api/v1/webhooks/job-ingestion" \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"${JOB_ID}\",
    \"title\": \"Senior Python Engineer\",
    \"description\": \"Build scalable AI systems...\",
    \"required_skills\": [\"Python\", \"FastAPI\", \"PostgreSQL\"],
    \"must_have_skills\": [\"Python\"],
    \"preferred_skills\": [\"Docker\", \"Qdrant\"]
  }" \
  | jq

# Windows PowerShell - Method 1: Using JSON file
@"
{
  "job_id": "$JOB_ID",
  "title": "Senior Python Engineer",
  "description": "Build scalable AI systems...",
  "required_skills": ["Python", "FastAPI", "PostgreSQL"],
  "must_have_skills": ["Python"],
  "preferred_skills": ["Docker", "Qdrant"]
}
"@ | Out-File -FilePath job_payload.json -Encoding UTF8 -NoNewline

curl.exe -X POST "http://localhost:8000/api/v1/webhooks/job-ingestion" `
  -H "Content-Type: application/json" `
  -d "@job_payload.json"

# Windows PowerShell - Method 2: Using Invoke-RestMethod
$JOB_ID = "your-job-id-here"
$body = @{
    job_id = $JOB_ID
    title = "Senior Python Engineer"
    description = "Build scalable AI systems..."
    required_skills = @("Python", "FastAPI", "PostgreSQL")
    must_have_skills = @("Python")
    preferred_skills = @("Docker", "Qdrant")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/webhooks/job-ingestion" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

# Expected response:
# {
#   "status": "success",
#   "job_id": "123e4567-e89b-12d3-a456-426614174000",
#   "embeddings_created": true,
#   "cached": true,
#   "profile_text": "Senior Python Engineer\n\nBuild scalable AI systems...",
#   "skills_count": 12
# }
```

**What It Tests**:
- ✅ Skill expansion using ontology
- ✅ Dual embedding generation (profile + skills)
- ✅ Storage in jobs_v1 Qdrant collection
- ✅ Redis caching (1-hour TTL)
- ✅ Pre-computation for fast ranking

---

## Feature Testing

### Feature 1: Application Tracking (PROMPT_1)

**Purpose**: Ensure ranking searches ONLY candidates who applied to jobs

**Test Steps**:

1. **Create job and candidates**:
```bash
# Create job
JOB_ID=$(curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Job", "description": "Test", "required_skills": ["Python"], "must_have_skills": ["Python"]}' \
  | jq -r '.job_id')

# Create 3 candidates (use upload-resume endpoint)
CANDIDATE_1=$(curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" -F "file=@/tmp/resume1.txt" | jq -r '.temp_id')
CANDIDATE_2=$(curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" -F "file=@/tmp/resume2.txt" | jq -r '.temp_id')
CANDIDATE_3=$(curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" -F "file=@/tmp/resume3.txt" | jq -r '.temp_id')
```

2. **Only candidate 1 and 2 apply**:
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/apply?candidate_id=${CANDIDATE_1}"
curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/apply?candidate_id=${CANDIDATE_2}"
```

3. **Rank candidates**:
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/rank_full" -d '{"use_cache": false}' | jq
```

4. **Verify**:
- ✅ Only 2 candidates returned (not 3)
- ✅ candidate_3 NOT in results (didn't apply)
- ✅ Logs show: "📋 2 candidates applied to job"

**Expected Behavior**:
- Ranking searches applications table first
- Filters candidates by application_ids
- 100x faster SQL queries (100 applicants vs 10,000 candidates)

---

### Feature 2: Resume-First Upload (PROMPT_2)

**Purpose**: Parse resume first, pre-fill form, then full ingestion

**Test Steps**:

**Stage 1: Anonymous Upload (Parse Only)**
```bash
# Upload resume
RESPONSE=$(curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@/tmp/test_resume.txt")

TEMP_ID=$(echo $RESPONSE | jq -r '.temp_id')
PARSED_DATA=$(echo $RESPONSE | jq '.parsed_data')

# Verify parsed data
echo $PARSED_DATA | jq

# Verify NO data in PostgreSQL
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT COUNT(*) FROM rightstaff.candidate WHERE id = '${TEMP_ID}';
"
# Expected: 0 (no candidate record yet!)

# Verify data in Redis
docker exec -it rightstaff-redis redis-cli GET "parsed_candidate:${TEMP_ID}"
# Expected: JSON with parsed data
```

**Stage 2: Form Pre-Fill**
```bash
# Fetch parsed data (simulates frontend)
curl "http://localhost:8000/api/v1/candidates/parsed/${TEMP_ID}" | jq

# Expected: Same parsed data as upload response
```

**Stage 3: Candidate Creation (Full Ingestion)**
```bash
# Submit form
curl -X POST "http://localhost:8000/api/v1/candidates/" \
  -H "Content-Type: application/json" \
  -d "{
    \"temp_id\": \"${TEMP_ID}\",
    \"full_name\": \"John Doe\",
    \"email\": \"john.doe@example.com\",
    \"phone\": \"(123) 456-7890\",
    \"years_experience\": 5.0,
    \"professional_summary\": \"Senior Python Developer\"
  }" | jq

# Wait for ingestion (10-15 seconds)
sleep 15

# Verify data in PostgreSQL
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT id, full_name, years_experience FROM rightstaff.candidate WHERE id = '${TEMP_ID}';
"
# Expected: 1 row with candidate data

# Verify data in Qdrant
curl "http://localhost:6333/collections/candidates_v1/points/scroll" | jq

# Expected: Points with candidate_id metadata

# Verify Redis cache cleared
docker exec -it rightstaff-redis redis-cli GET "parsed_candidate:${TEMP_ID}"
# Expected: (nil) - cache cleared after creation
```

**Expected Behavior**:
- ✅ Parse-only: 2-3 seconds, NO PostgreSQL/Qdrant
- ✅ Full ingestion: 10-15 seconds, complete pipeline
- ✅ No orphaned data (Redis expires after 1 hour)
- ✅ Better UX (auto-filled forms)

---

### Feature 3: Job Embeddings Optimization (PROMPT_3)

**Purpose**: Pre-compute job embeddings for 50% faster ranking

**Test Steps**:

**Step 1: Create job WITHOUT embeddings (slow path)**
```bash
JOB_ID=$(curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Job", "description": "Test", "required_skills": ["Python"]}' \
  | jq -r '.job_id')

# Trigger ranking (will generate embeddings on-the-fly)
time curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/rank_full" \
  -d '{"use_cache": false}' > /dev/null

# Expected: ~2.5-3 seconds (slow!)
```

**Step 2: Create job WITH embeddings (fast path)**
```bash
# Call job ingestion webhook
curl -X POST "http://localhost:8000/api/v1/webhooks/job-ingestion" \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"${JOB_ID}\",
    \"title\": \"Test Job\",
    \"description\": \"Test description\",
    \"required_skills\": [\"Python\", \"FastAPI\"],
    \"must_have_skills\": [\"Python\"]
  }" | jq

# Verify embeddings in jobs_v1 collection
curl "http://localhost:6333/collections/jobs_v1/points/scroll" | jq

# Verify Redis cache
docker exec -it rightstaff-redis redis-cli GET "job_embeddings:${JOB_ID}"

# Trigger ranking (will FETCH embeddings, not generate)
time curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/rank_full" \
  -d '{"use_cache": false}' > /dev/null

# Expected: ~1-1.5 seconds (50% faster!)
```

**Step 3: Verify both collections exist**
```bash
curl "http://localhost:6333/collections" | jq

# Expected: Both candidates_v1 and jobs_v1 in list
```

**Expected Behavior**:
- ✅ Job embeddings in jobs_v1 collection (2 points: profile + skills)
- ✅ Ranking fetches embeddings (50ms vs 500ms)
- ✅ 50% latency reduction (2.5s → 1.5s)
- ✅ Redis caching layer for ultra-fast retrieval

---

## End-to-End Workflows

### Workflow 1: Complete Candidate Journey (PowerShell)

**Scenario**: Create a candidate that will be ranked and selected for a job

**IMPORTANT**: This workflow ensures the candidate is compatible with the job by:
- Matching required skills (Python, FastAPI)
- Meeting experience requirements (5 years, within 3-10 range)
- Being in the same location (San Francisco)

```powershell
# ============================================================
# STEP 1: Create a resume file with matching skills
# ============================================================

$resumeContent = @"
JANE SMITH
Senior Python Developer

Email: jane.smith@example.com
Phone: (555) 123-4567
Location: San Francisco, CA

PROFESSIONAL SUMMARY
Highly skilled Python engineer with 5 years of experience building scalable
web applications using FastAPI, PostgreSQL, and modern cloud technologies.
Proven track record of delivering high-quality software in fast-paced environments.

TECHNICAL SKILLS
- Languages: Python (Expert), JavaScript, SQL
- Frameworks: FastAPI, Django, Flask, React
- Databases: PostgreSQL, Redis, MongoDB
- DevOps: Docker, Kubernetes, AWS, CI/CD
- Tools: Git, Pytest, SQLAlchemy

WORK EXPERIENCE
Senior Python Developer | TechCorp Inc | 2020-Present
- Built RESTful APIs using FastAPI serving 100K+ requests/day
- Designed microservices architecture with Docker and Kubernetes
- Optimized database queries reducing latency by 50%
- Mentored junior developers and conducted code reviews

Python Developer | StartupXYZ | 2019-2020
- Developed web applications using Django and PostgreSQL
- Implemented automated testing with 90% code coverage
- Collaborated with frontend team using React

EDUCATION
B.S. Computer Science | University of California | 2019
"@

# Save resume to file
$resumePath = ".\jane_smith_resume.txt"
$resumeContent | Out-File -FilePath $resumePath -Encoding UTF8 -NoNewline
Write-Host "✅ Created resume file: $resumePath`n"

# ============================================================
# STEP 2: Create job with compatible requirements
# ============================================================

Write-Host "STEP 2: Creating job..."
$jobBody = @{
    title = "Senior Python Engineer"
    description = "Build scalable AI systems with FastAPI, PostgreSQL, and Qdrant. Work on cutting-edge ranking algorithms."
    department = "Engineering"
    location = "San Francisco, CA (Hybrid)"
    required_skills = @("Python", "FastAPI", "PostgreSQL", "Docker")
    must_have_skills = @("Python", "FastAPI")  # Jane has both!
    min_years_experience = 3
    max_years_experience = 10  # Jane has 5 years ✅
    work_arrangement = "hybrid"
    employment_type = "full-time"
} | ConvertTo-Json

$jobResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/jobs" `
    -Method Post `
    -ContentType "application/json" `
    -Body $jobBody

$JOB_ID = $jobResponse.job_id
Write-Host "✅ Job created: $JOB_ID"
Write-Host "   Title: $($jobResponse.title)`n"

# ============================================================
# STEP 3: Upload resume (anonymous)
# ============================================================

Write-Host "STEP 3: Uploading resume..."
$uploadResponse = curl.exe -X POST "http://localhost:8000/api/v1/candidates/upload-resume" `
    -F "file=@$resumePath" `
    -s | ConvertFrom-Json

$TEMP_ID = $uploadResponse.temp_id
Write-Host "✅ Resume uploaded and parsed"
Write-Host "   temp_id: $TEMP_ID"
Write-Host "   Parsed name: $($uploadResponse.parsed_data.full_name)"
Write-Host "   Parsed email: $($uploadResponse.parsed_data.email)"
Write-Host "   Parsed skills: $($uploadResponse.parsed_data.skills -join ', ')`n"

# ============================================================
# STEP 4: Review parsed data (optional verification)
# ============================================================

Write-Host "STEP 4: Verifying parsed data..."
$parsedData = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/candidates/parsed/$TEMP_ID"
Write-Host "✅ Parsed data retrieved (status: $($parsedData.status))`n"

# ============================================================
# STEP 5: Create candidate with form submission
# ============================================================

Write-Host "STEP 5: Creating candidate..."
$candidateBody = @{
    temp_id = $TEMP_ID
    full_name = "Jane Smith"
    email = "jane.smith@example.com"
    phone = "(555) 123-4567"
    years_experience = 5.0
    professional_summary = "Highly skilled Python engineer with 5 years of experience building scalable web applications using FastAPI, PostgreSQL, and modern cloud technologies."
    location = "San Francisco, CA"
} | ConvertTo-Json

$candidateResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/candidates/" `
    -Method Post `
    -ContentType "application/json" `
    -Body $candidateBody

$CANDIDATE_ID = $candidateResponse.candidate_id
Write-Host "✅ Candidate created: $CANDIDATE_ID"
Write-Host "   Processing job: $($candidateResponse.processing_job_id)`n"

# ============================================================
# STEP 6: Wait for embeddings to be generated
# ============================================================

Write-Host "STEP 6: Waiting for full ingestion (embeddings)..."
Start-Sleep -Seconds 15
Write-Host "✅ Ingestion complete`n"

# ============================================================
# STEP 7: Candidate applies to job
# ============================================================

Write-Host "STEP 7: Submitting job application..."
$applicationResponse = curl.exe -X POST "http://localhost:8000/api/v1/jobs/$JOB_ID/apply?candidate_id=$CANDIDATE_ID" `
    -H "Content-Type: application/json" `
    -s | ConvertFrom-Json

Write-Host "✅ Application submitted"
Write-Host "   Application ID: $($applicationResponse.application_id)"
Write-Host "   Status: $($applicationResponse.status)`n"

# ============================================================
# STEP 8: Rank candidates
# ============================================================

Write-Host "STEP 8: Ranking candidates for the job..."
$rankingBody = @{
    use_cache = $false
} | ConvertTo-Json

$rankingResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/jobs/$JOB_ID/rank_full" `
    -Method Post `
    -ContentType "application/json" `
    -Body $rankingBody

Write-Host "✅ Ranking complete!`n"
Write-Host "==================== RANKING RESULTS ====================" -ForegroundColor Cyan
Write-Host "Total candidates: $($rankingResponse.metadata.total_candidates)"
Write-Host "High confidence: $($rankingResponse.metadata.high_confidence)"
Write-Host "Medium confidence: $($rankingResponse.metadata.medium_confidence)"
Write-Host "Low confidence: $($rankingResponse.metadata.low_confidence)`n"

if ($rankingResponse.ranked_candidates.Count -gt 0) {
    $topCandidate = $rankingResponse.ranked_candidates[0]
    Write-Host "🏆 TOP CANDIDATE:" -ForegroundColor Green
    Write-Host "   Candidate ID: $($topCandidate.candidate_id)"
    Write-Host "   Final Score: $([math]::Round($topCandidate.final_score * 100, 1))%"
    Write-Host "   Band: $($topCandidate.band)"
    Write-Host "   Confidence: $([math]::Round($topCandidate.confidence * 100, 1))%"
    Write-Host "   Summary: $($topCandidate.summary)`n"

    Write-Host "   Reasons:" -ForegroundColor Yellow
    foreach ($reason in $topCandidate.reasons) {
        Write-Host "   - $reason"
    }

    Write-Host "`n   Score Breakdown:" -ForegroundColor Yellow
    Write-Host "   - Dense (semantic): $([math]::Round($topCandidate.score_breakdown.dense * 100, 1))%"
    Write-Host "   - Structured: $([math]::Round($topCandidate.score_breakdown.structured * 100, 1))%"
    Write-Host "   - Completeness: $([math]::Round($topCandidate.score_breakdown.completeness * 100, 1))%"

    # Verify it's Jane Smith
    if ($topCandidate.candidate_id -eq $CANDIDATE_ID) {
        Write-Host "`n✅ SUCCESS! Jane Smith was ranked and selected!" -ForegroundColor Green
    } else {
        Write-Host "`n⚠️  Warning: A different candidate was ranked #1" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ No candidates were ranked" -ForegroundColor Red
    Write-Host "   This means no candidates passed the SQL gates or no applications exist"
}

Write-Host "`n========================================================`n"

# Cleanup
Remove-Item -Path $resumePath -ErrorAction SilentlyContinue
```

**Why This Candidate Gets Selected**:

1. **Skills Match** ✅
   - Has `Python` (must-have) ✅
   - Has `FastAPI` (must-have) ✅
   - Has `PostgreSQL` (required) ✅
   - Has `Docker` (required) ✅

2. **Experience Match** ✅
   - Has 5 years experience
   - Job requires 3-10 years ✅

3. **Location Match** ✅
   - Candidate: San Francisco, CA
   - Job: San Francisco, CA (Hybrid) ✅

4. **Application Submitted** ✅
   - Candidate applied to the job
   - Only applicants are ranked

**Expected Output**:
```
✅ Job created: <job_id>
✅ Resume uploaded and parsed
✅ Candidate created: <candidate_id>
✅ Application submitted
✅ Ranking complete!

🏆 TOP CANDIDATE:
   Final Score: 75-85%
   Band: high
   Confidence: 80%+
   Summary: Excellent match for Senior Python Engineer

✅ SUCCESS! Jane Smith was ranked and selected!
```

**Validation Checklist**:
- ✅ Resume parsed correctly (name, email, skills extracted)
- ✅ Candidate created in PostgreSQL
- ✅ Embeddings generated in Qdrant candidates_v1
- ✅ Application created successfully
- ✅ SQL gates passed (skills, experience, location)
- ✅ Ranking returns candidate with high score
- ✅ Semantic similarity match (FastAPI, Python, PostgreSQL)
- ✅ Structured scoring (5 years experience)
- ✅ Explanation and evidence provided

---

### Workflow 2: Bulk Candidate Ingestion

**Scenario**: Portal team sends 100 candidate updates via webhook

```bash
# Simulate 100 webhook calls
for i in {1..100}; do
  CANDIDATE_ID=$(uuidgen)

  curl -X POST "http://localhost:8000/api/v1/webhooks/candidate-updated" \
    -H "Content-Type: application/json" \
    -d "{
      \"event_type\": \"resume_uploaded\",
      \"candidate_id\": \"${CANDIDATE_ID}\",
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
      \"s3_resume_url\": \"resumes/${CANDIDATE_ID}/resume.pdf\",
      \"profile_snapshot\": {}
    }" &
done

# Wait for all webhooks
wait

# Check ingestion worker logs
docker logs rightstaff-backend -f

# Monitor queue depth
curl "http://localhost:8000/api/v1/admin/health/detailed" | jq '.worker'

# Expected:
# - All 100 webhooks accepted (202 status)
# - Worker processes jobs from queue
# - DLQ collects any failures
```

---

### Workflow 3: Job Creation with Embeddings

**Scenario**: Portal team creates job, embeddings pre-computed

```bash
# 1. Portal creates job in their database
# 2. Portal calls our webhook
JOB_ID=$(uuidgen)

curl -X POST "http://localhost:8000/api/v1/webhooks/job-ingestion" \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"${JOB_ID}\",
    \"title\": \"Staff ML Engineer\",
    \"description\": \"Lead ML infrastructure team, build training pipelines...\",
    \"required_skills\": [\"Python\", \"PyTorch\", \"Kubernetes\", \"MLOps\"],
    \"must_have_skills\": [\"Python\", \"PyTorch\"],
    \"preferred_skills\": [\"Kubeflow\", \"Ray\"]
  }" | jq

# 3. Verify embeddings created
curl "http://localhost:6333/collections/jobs_v1/points/scroll" | jq

# 4. Check Redis cache
docker exec -it rightstaff-redis redis-cli GET "job_embeddings:${JOB_ID}"

# 5. Trigger ranking (fast!)
time curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/rank_full" \
  -d '{"use_cache": false}' > /dev/null

# Expected: < 1.5 seconds
```

---

## Unit & Integration Tests

### Running Tests

```bash
cd backend

# All unit tests
pytest tests/ -v

# Specific test file
pytest tests/test_ranking.py -v

# Integration tests only
pytest tests/ -m integration -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

### Test Files

| Test File | Purpose | Coverage | Status |
|-----------|---------|----------|--------|
| `test_health.py` | Infrastructure health | Service connections | ✅ Complete |
| `test_parsers.py` | Document parsing | TXT extraction + chunking (18 tests) | ✅ Complete |
| `test_ontology.py` | Skill extraction | spaCy NER + patterns | ✅ Complete |
| `test_embeddings.py` | Text vectorization | Embedding generation | ✅ Complete |
| `test_job_embeddings.py` | Job vectorization | Dual embeddings | ✅ Complete |
| `test_vector_store.py` | Qdrant operations | Vector CRUD | ✅ Complete |
| `test_ranking.py` | Ranking components | Scoring, blending, banding | ✅ Complete |
| `test_ranking_comprehensive.py` | Full ranking pipeline | E2E ranking | ✅ Complete |
| `test_api.py` | API endpoints | HTTP request/response | ⏳ Partial |
| `test_fairness.py` | Bias detection | 16+ fairness tests | ✅ Complete |

### Example: Running Fairness Tests

```bash
# Run all fairness tests
pytest tests/test_fairness.py -v

# Expected output:
# test_no_gender_bias ............................ PASSED
# test_no_race_bias .............................. PASSED
# test_no_age_bias ............................... PASSED
# test_demographics_excluded ..................... PASSED
# test_consistent_ranking ........................ PASSED
# test_no_correlation_with_protected ............. PASSED
# ...
# =================== 16 passed in 12.5s ===================
```

---

## Performance Testing

### Benchmark 1: Ranking Latency

```bash
# Without job embeddings pre-computed
time curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/rank_full" \
  -d '{"use_cache": false}' > /dev/null

# Target: < 2.5 seconds

# With job embeddings pre-computed
time curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/rank_full" \
  -d '{"use_cache": false}' > /dev/null

# Target: < 1.5 seconds (50% improvement)
```

### Benchmark 2: Resume Upload

```bash
# Parse-only mode
time curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@/tmp/test_resume.txt" > /dev/null

# Target: < 3 seconds
```

### Benchmark 3: Ingestion Pipeline

```bash
# Trigger full ingestion
START=$(date +%s)

curl -X POST "http://localhost:8000/api/v1/candidates/" \
  -H "Content-Type: application/json" \
  -d '{"temp_id": "...", "full_name": "Test"}' > /dev/null

# Wait for completion
sleep 15

END=$(date +%s)
DURATION=$((END - START))

echo "Full ingestion took: ${DURATION}s"

# Target: < 15 seconds
```

### Performance Metrics

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| Resume upload (parse-only) | < 3s | 2-3s | ✅ |
| Full ingestion | < 15s | 10-15s | ✅ |
| Ranking (no cache) | < 1.5s | 1-1.5s | ✅ |
| Ranking (cached) | < 0.1s | 0.05s | ✅ |
| Job embedding generation | < 1s | 0.5s | ✅ |

---

## Troubleshooting

### Issue 1: "Application table not found"

**Symptoms**:
```
ERROR: relation "rightstaff.application" does not exist
```

**Cause**: Database schema not applied or outdated

**Fix**:
```bash
# Re-run schema script
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff \
  -f /docker-entrypoint-initdb.d/01_schema.sql

# Verify table exists
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
\dt rightstaff.application
"
```

---

### Issue 2: "Session expired or invalid temp_id"

**Symptoms**:
```json
{
  "detail": "Session expired or invalid temp_id. Please upload resume again."
}
```

**Cause**: Redis cache expired (> 1 hour) or temp_id doesn't exist

**Fix**:
```bash
# Check Redis cache
docker exec -it rightstaff-redis redis-cli KEYS "parsed_candidate:*"

# If empty, re-upload resume
curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@/tmp/resume.txt"
```

---

### Issue 3: "Job embeddings not found"

**Symptoms**:
```
ValueError: Job embeddings not found for {job_id}. Run job ingestion webhook first!
```

**Cause**: Job embeddings not pre-computed

**Fix**:
```bash
# Call job ingestion webhook
curl -X POST "http://localhost:8000/api/v1/webhooks/job-ingestion" \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"${JOB_ID}\",
    \"title\": \"Job Title\",
    \"description\": \"Job description\",
    \"required_skills\": [\"Python\"]
  }"

# Verify embeddings in Qdrant
curl "http://localhost:6333/collections/jobs_v1/points/scroll" | jq
```

---

### Issue 4: "Collection jobs_v1 not found"

**Symptoms**:
```
qdrant_client.exceptions.UnexpectedResponse: Collection 'jobs_v1' not found
```

**Cause**: Qdrant collections not initialized

**Fix**:
```bash
# Restart backend (triggers initialize_collections)
docker restart rightstaff-backend

# Or create manually
curl -X PUT "http://localhost:6333/collections/jobs_v1" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'
```

---

### Issue 5: "No applications found" but applications exist

**Symptoms**: Ranking returns 0 results even though applications exist

**Cause**: Application records not created or wrong job_id

**Fix**:
```bash
# Check applications table
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT a.id, c.full_name, j.title, a.status
FROM rightstaff.application a
JOIN rightstaff.candidate c ON a.candidate_id = c.id
JOIN rightstaff.job j ON a.job_id = j.id;
"

# If empty, create applications
curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/apply?candidate_id=${CANDIDATE_ID}"
```

---

## Quick Reference

### Common Commands

```bash
# Health check
curl http://localhost:8000/health | jq

# Metrics
curl http://localhost:8000/api/v1/admin/metrics | jq

# Clear all data
cd backend && python clear_all_data.py

# Populate test data
cd backend && python populate_dummy_data.py

# Check database
cd backend && python check_database.py

# Run all tests
pytest backend/tests/ -v

# Check Qdrant collections
curl http://localhost:6333/collections | jq

# Check Redis keys
docker exec -it rightstaff-redis redis-cli KEYS "*"

# View worker logs
docker logs rightstaff-backend -f
```

### Validation Checklist

Before deploying:

- [ ] All services healthy (`GET /health`)
- [ ] Test data populated (8 candidates, 49 skills)
- [ ] Both Qdrant collections exist (candidates_v1, jobs_v1)
- [ ] Application tracking works (only ranks applicants)
- [ ] Resume upload works (3-stage workflow)
- [ ] Job embeddings pre-computed (webhooks work)
- [ ] Ranking latency < 1.5s (50% improvement)
- [ ] All unit tests pass (`pytest tests/ -v`)
- [ ] All fairness tests pass (`pytest tests/test_fairness.py -v`)
- [ ] No data inconsistencies (PostgreSQL, Qdrant, Redis, MinIO)

---

**Last Updated**: 2025-11-17
**Version**: 2.0 (Day-5 Complete)
**Next Update**: After Day-6 implementation (TASK 4-12)
