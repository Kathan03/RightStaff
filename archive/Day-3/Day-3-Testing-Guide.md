# 🧪 Day 3 Testing Guide - RightStaff AI

## Overview

This guide provides step-by-step testing commands using **PowerShell `Invoke-WebRequest`** to verify all Day 3 implementations.

**What You're Testing:**
- Retry logic with exponential backoff
- Dead Letter Queue functionality
- Skills extraction from resumes
- SQL gating logic (filtering by skills, years, location)
- Job management endpoints
- Metrics collection and admin endpoints

**Prerequisites:**
- Docker containers running (PostgreSQL, Redis, Qdrant, MinIO)
- FastAPI server running (`uvicorn app.main:app --reload`)
- Day 1-2 implementations working

---

## TEST CATEGORY 1: Pre-Flight Checks

### Test 1.1: Verify All Services Running

```powershell
# Check Docker containers
docker ps

# Expected: 4 containers running
# - rightstaff-postgres
# - rightstaff-redis
# - rightstaff-qdrant
# - rightstaff-minio
```

**PASS Criteria:** All 4 containers show STATUS "Up"

### Test 1.2: Health Check

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Expected Output:**
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
  "timestamp": "2025-11-07T..."
}
```

**PASS Criteria:** All services show "ok"

### Test 1.3: Verify FastAPI Docs Accessible

```powershell
Start-Process "http://localhost:8000/docs"
```

**PASS Criteria:** Swagger UI opens, shows new endpoints:
- POST /api/v1/jobs/
- POST /api/v1/jobs/rank
- GET /api/v1/jobs/{job_id}/rankings
- GET /api/v1/admin/metrics
- GET /api/v1/admin/dlq

---

## TEST CATEGORY 2: Skills Extraction

### Test 2.1: Check spaCy Model Installed

```powershell
cd backend
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('spaCy model loaded successfully')"
```

**Expected Output:** `spaCy model loaded successfully`

**PASS Criteria:** No errors

### Test 2.2: Test Skills Taxonomy Loading

```powershell
# Check if taxonomy file exists
Test-Path "skills_taxonomy.json"

# Should return: True
```

**PASS Criteria:** File exists at root directory

### Test 2.3: Test Skills Extraction (via Python)

```powershell
cd backend
python -c @"
import asyncio
from app.services.ontology import extract_skills_from_text

async def test():
    text = 'Software engineer with 5 years Python, React, AWS, and PostgreSQL experience'
    skills = await extract_skills_from_text(text)
    print(f'Extracted skills: {skills}')

asyncio.run(test())
"@
```

**Expected Output:** 
```
Extracted skills: ['AWS', 'PostgreSQL', 'Python', 'React']
```

**PASS Criteria:** Skills list contains expected items (Python, React, AWS, PostgreSQL)

---

## TEST CATEGORY 3: Retry Logic & Dead Letter Queue

### Test 3.1: Trigger Ingestion with Valid Resume

```powershell
# First, get a candidate ID
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "SELECT id, full_name FROM rightstaff.candidate LIMIT 1;"

# Copy the UUID, then:
$candidateId = "c4c41cb0-bf08-413d-8fb5-54ea3ac955bf"  # Replace with actual UUID

$body = @{
    event_type = "profile_created"
    candidate_id = $candidateId
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    s3_resume_url = "s3://rightstaff-resumes/resumes/pratz_v2.pdf"
    profile_snapshot = @{}
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/webhooks/candidate-updated" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

$response.Content | ConvertFrom-Json | ConvertTo-Json
```

**Expected Output:**
```json
{
  "status": "accepted",
  "candidate_id": "...",
  "processing_job_id": "ingest_...",
  "estimated_completion_seconds": 30
}
```

**Monitor logs** (in the terminal running uvicorn):
- Should see 7 stages now (added skills extraction)
- Stage 4 should show: `[4/7] Extracting skills from resume text`
- Should see: `✅ Extracted X skills: Python, JavaScript, ...`

**PASS Criteria:**
- HTTP 202 response
- Logs show all 7 stages complete
- No retry attempts (first attempt succeeds)

### Test 3.2: Check Dead Letter Queue is Empty

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq" -Method GET
$dlqStatus = $response.Content | ConvertFrom-Json
$dlqStatus | ConvertTo-Json
```

**Expected Output:**
```json
{
  "depth": 0,
  "sample_entries": []
}
```

**PASS Criteria:** `depth` is 0 (no failed jobs)

### Test 3.3: Simulate Retry (Invalid S3 URL)

```powershell
# Send webhook with non-existent resume

$candidateId = "c4c41cb0-bf08-413d-8fb5-54ea3ac955bf"
$body = @{
    event_type = "profile_created"
    candidate_id = $candidateId
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    s3_resume_url = "s3://rightstaff-resumes/resumes/NONEXISTENT.pdf"
    profile_snapshot = @{}
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/webhooks/candidate-updated" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

$response.Content | ConvertFrom-Json | ConvertTo-Json
```

**Monitor logs:** (THis is not working)
- Should see retry attempts with exponential backoff:
  - `⚠️ Retry attempt #1`
  - Wait 2 seconds
  - `⚠️ Retry attempt #2`
  - Wait 4 seconds
  - `⚠️ Retry attempt #3`
  - Wait 8 seconds
  - `⚠️ Retry attempt #4`
  - Wait 16 seconds
  - `⚠️ Retry attempt #5`
- After max retries: `📬 Moved job ingest_... to DLQ`

**PASS Criteria:**
- 5 retry attempts (1 original + 4 retries)
- Exponential backoff visible (2s, 4s, 8s, 16s)
- Job moved to DLQ after max retries

### Test 3.4: Verify Job in DLQ

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq" -Method GET
$dlqStatus = $response.Content | ConvertFrom-Json
$dlqStatus | ConvertTo-Json -Depth 10
```

**Expected Output:**
```json
{
  "depth": 1,
  "sample_entries": [
    {
      "job_id": "ingest_...",
      "candidate_id": "...",
      "s3_resume_url": "s3://.../NONEXISTENT.pdf",
      "failed_at": "2025-11-07T...",
      "error": "...",
      "final_retry_count": 5
    }
  ]
}
```

**PASS Criteria:** 
- `depth` is 1
- Failed job appears in `sample_entries`
- Shows `final_retry_count: 5`

### Test 3.5: Replay Job from DLQ (Should Fail Again)

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/dlq/replay" -Method POST
$response.Content | ConvertFrom-Json | ConvertTo-Json
```

**Expected Output:**
```json
{
  "status": "completed",
  "replayed_count": 1
}
```

**Monitor logs:**
- Should see job replayed and fail again (S3 file still doesn't exist)
- Should move back to DLQ after retries

**PASS Criteria:** Job is replayed (visible in logs)

---

## TEST CATEGORY 4: SQL Gating Logic

### Test 4.1: Add Skills to Database (Setup for Testing)

First, add some skills to the database:

```powershell
# Add Python skill
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c @"
INSERT INTO rightstaff.skill (id, name) VALUES (gen_random_uuid(), 'Python') ON CONFLICT (name) DO NOTHING;
INSERT INTO rightstaff.skill (id, name) VALUES (gen_random_uuid(), 'JavaScript') ON CONFLICT (name) DO NOTHING;
INSERT INTO rightstaff.skill (id, name) VALUES (gen_random_uuid(), 'React') ON CONFLICT (name) DO NOTHING;
INSERT INTO rightstaff.skill (id, name) VALUES (gen_random_uuid(), 'PostgreSQL') ON CONFLICT (name) DO NOTHING;
"@

# Link skills to candidate (get candidate and skill IDs first)
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c @"
SELECT c.id AS candidate_id, c.full_name, s.id AS skill_id, s.name AS skill_name
FROM rightstaff.candidate c
CROSS JOIN rightstaff.skill s
WHERE s.name IN ('Python', 'JavaScript')
LIMIT 2;
"@

# Copy the IDs and insert into candidate_skill
# docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "INSERT INTO rightstaff.candidate_skill (candidate_id, skill_id, level, years) VALUES ('CANDIDATE_UUID', 'SKILL_UUID', 'Expert', 5.0);"
```

### Test 4.2: Run Database Migration

```powershell
# Apply the new job fields migration
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -f /docker-entrypoint-initdb.d/04_job_fields_for_ai.sql
```

**Expected Output:**
```
ALTER TABLE
CREATE INDEX
...
```

**PASS Criteria:** No errors, job table now has new columns

### Test 4.3: Verify Job Table Schema

```powershell
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "\d rightstaff.job"
```

**PASS Criteria:** Should show new columns:
- description
- required_skills_json
- must_have_skills_json
- min_years_experience
- max_years_experience

---

## TEST CATEGORY 5: Job Management Endpoints

### Test 5.1: Create a Job

```powershell
$body = @{
    title = "Senior Python Developer"
    description = "We are looking for an experienced Python developer with React and PostgreSQL experience."
    required_skills = @("Python", "React", "PostgreSQL")
    must_have_skills = @("Python")
    min_years_experience = 3.0
    max_years_experience = 10.0
    location = "State College"
    work_arrangement = "Remote"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

$job = $response.Content | ConvertFrom-Json
$job | ConvertTo-Json

# Save job_id for next tests
$jobId = "6855dc32-71b2-48a0-97e6-298d9e21eec5"
```

**Expected Output:**
```json
{
  "job_id": "uuid-here",
  "title": "Senior Python Developer",
  "status": "created"
}
```

**PASS Criteria:** HTTP 201, job_id returned

### Test 5.2: Trigger Ranking for Job

```powershell
$body = @{
    job_id = $jobID
    use_cache = $false
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/rank" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

$rankingResult = $response.Content | ConvertFrom-Json
$rankingResult | ConvertTo-Json
```

**Expected Output:**
```json
{
  "status": "completed",
  "job_id": "...",
  "job_title": "Senior Python Developer",
  "total_qualified": 1,
  "pipeline_stage": "sql_gating_only",
  "note": "Full semantic ranking will be added in Days 5-8"
}
```

**Monitor logs:**
- Should see: `🎯 Ranking candidates for job: Senior Python Developer`
- Should see: `✅ X candidates passed must-have skills gate`
- Should see: `✅✅✅ SQL Gating Complete: X candidates qualified`

**PASS Criteria:** 
- HTTP 200 response
- `total_qualified` >= 0 (depends on test data)
- Logs show SQL gating executed

### Test 5.3: Retrieve Rankings

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/$jobId/rankings?top_k=10" -Method GET
$rankings = $response.Content | ConvertFrom-Json
$rankings | ConvertTo-Json -Depth 10
```

**Expected Output:**
```json
{
  "job_id": "...",
  "status": "found",
  "total_qualified": 1,
  "returned_count": 1,
  "candidate_ids": ["uuid1"],
  "computed_at": "2025-11-07T...",
  "gates_applied": {
    "must_have_skills": ["Python"],
    "min_years": 3.0,
    "max_years": 10.0,
    "location": "State College"
  }
}
```

**PASS Criteria:**
- `status` is "found"
- `candidate_ids` array returned
- `gates_applied` matches job requirements

---

## TEST CATEGORY 6: Metrics & Monitoring

### Test 6.1: Check Metrics

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/metrics" -Method GET
$metrics = $response.Content | ConvertFrom-Json
$metrics | ConvertTo-Json -Depth 10
```

**Expected Output:**
```json
{
  "counters": {
    "ingestion_jobs_success": 1,
    "ingestion_jobs_failed": 1,
    "ingestion_retries": 5
  },
  "timings": {
    "ingestion_total": {
      "count": 1,
      "avg": 8.5,
      "min": 8.5,
      "max": 8.5
    },
    "ingestion_stage_4_skills": {
      "count": 1,
      "avg": 0.3,
      ...
    }
  },
  "gauges": {},
  "system": {
    "embedding_model": {
      "loaded": true,
      "model_name": "sentence-transformers/all-MiniLM-L6-v2",
      "device": "cpu",
      "embedding_dim": 384
    },
    "qdrant_collection": {
      "vectors_count": 12,
      "points_count": 12,
      "status": "green",
      "vector_size": 384
    }
  }
}
```

**PASS Criteria:**
- Counters show ingestion activity
- Timings show stage durations
- System info shows loaded models

---

## TEST CATEGORY 7: Integration Test (Full Flow)

### Test 7.1: End-to-End Pipeline with Skills

```powershell
# 1. Create a job requiring specific skills
$body = @{
    title = "Full Stack Developer"
    description = "Looking for a full stack developer with Python and React experience"
    required_skills = @("Python", "React", "PostgreSQL")
    must_have_skills = @("Python", "React")
    min_years_experience = 2.0
} | ConvertTo-Json

$jobResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/" `
    -Method POST -Body $body -ContentType "application/json"
$job = $jobResponse.Content | ConvertFrom-Json
$jobId = $job.job_id

# 2. Trigger ingestion for candidate (adds skills to Qdrant payload)
$candidateBody = @{
    event_type = "resume_uploaded"
    candidate_id = $candidateId
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    s3_resume_url = "s3://rightstaff-resumes/resumes/pratz_v2.pdf"
    profile_snapshot = @{}
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/v1/webhooks/candidate-updated" `
    -Method POST -Body $candidateBody -ContentType "application/json"

# Wait for processing (10 seconds)
Start-Sleep -Seconds 10

# 3. Trigger ranking
$rankBody = @{ job_id = $jobId } | ConvertTo-Json
$rankResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/rank" `
    -Method POST -Body $rankBody -ContentType "application/json"

# 4. Get rankings
$rankingsResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/$jobId/rankings" -Method GET
$rankings = $rankingsResponse.Content | ConvertFrom-Json
$rankings | ConvertTo-Json -Depth 10
```

**PASS Criteria:**
- Job created successfully
- Ingestion completes with skills extraction
- Ranking returns qualified candidates
- Qdrant vectors include skills in payload

### Test 7.2: Query Qdrant to Verify Skills in Payload

```powershell
# Using Qdrant REST API
$body = @{
    limit = 1
    with_payload = $true
    with_vector = $false
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:6333/collections/candidates_v1/points/scroll" `
    -Method POST -Body $body -ContentType "application/json"

$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Expected Output:**
```json
{
  "result": {
    "points": [
      {
        "id": "...",
        "payload": {
          "candidate_id": "...",
          "chunk_text": "...",
          "skills": ["Python", "JavaScript", "React", "PostgreSQL"]
        }
      }
    ]
  }
}
```

**PASS Criteria:** `payload.skills` array is populated

---

## TEST CATEGORY 8: Error Handling

### Test 8.1: Test Invalid Job ID

```powershell
$body = @{ job_id = "00000000-0000-0000-0000-000000000000" } | ConvertTo-Json
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/rank" `
        -Method POST -Body $body -ContentType "application/json"
} catch {
    $_.Exception.Response.StatusCode
    # Should be 404
}
```

**PASS Criteria:** HTTP 404 error

### Test 8.2: Test Missing Required Fields

```powershell
$body = @{ title = "Test Job" } | ConvertTo-Json
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/jobs/" `
        -Method POST -Body $body -ContentType "application/json"
} catch {
    $_.Exception.Response.StatusCode
    # Should be 422 (Validation Error)
}
```

**PASS Criteria:** HTTP 422 error

---

## FINAL SUCCESS CHECKLIST

Mark each item as you complete it:

### Infrastructure
- [ ] All Docker containers running
- [ ] FastAPI starts without errors
- [ ] Health check returns all "ok"
- [ ] New dependencies installed (tenacity, spacy, fuzzywuzzy)
- [ ] spaCy model downloaded (`en_core_web_sm`)

### Retry Logic
- [ ] Ingestion succeeds on first attempt (no retries)
- [ ] Invalid S3 URL triggers 5 retry attempts
- [ ] Exponential backoff visible (2s, 4s, 8s, 16s)
- [ ] Failed jobs move to DLQ after max retries

### Dead Letter Queue
- [ ] DLQ depth shows failed jobs
- [ ] DLQ entries contain error info and retry count
- [ ] Replay functionality works
- [ ] DLQ clearing works

### Skills Extraction
- [ ] spaCy model loads successfully
- [ ] Skills taxonomy file exists and loads
- [ ] Skills extracted from sample text
- [ ] Ingestion pipeline includes skills (Stage 4)
- [ ] Qdrant payload includes skills array

### SQL Gating
- [ ] Database migration adds job fields
- [ ] Must-have skills filter works
- [ ] Years of experience filter works
- [ ] Location filter works
- [ ] Combined gates return intersection

### Job Management
- [ ] Create job endpoint works
- [ ] Rank candidates endpoint works
- [ ] Get rankings endpoint works
- [ ] Redis caching works
- [ ] Job router registered in FastAPI

### Metrics & Monitoring
- [ ] Metrics endpoint returns data
- [ ] Counters track ingestion events
- [ ] Timings show stage durations
- [ ] DLQ admin endpoint works
- [ ] Admin router registered in FastAPI

### Code Quality
- [ ] No syntax errors
- [ ] All type hints present
- [ ] Extensive docstrings
- [ ] No hard-coded values
- [ ] Proper error handling

### Integration
- [ ] End-to-end flow works (job → ingestion → ranking)
- [ ] Skills flow through entire pipeline
- [ ] Qdrant vectors include skills metadata
- [ ] Metrics collected throughout

---

## TROUBLESHOOTING

### Issue: `ModuleNotFoundError: No module named 'tenacity'`

**Solution:**
```powershell
cd backend
pip install tenacity spacy fuzzywuzzy python-Levenshtein
python -m spacy download en_core_web_sm
```

### Issue: Skills taxonomy not found

**Solution:**
```powershell
# Check if file exists
Test-Path "skills_taxonomy.json"

# If not, create it (will be provided in separate file)
```

### Issue: Retry logic not triggering

**Solution:**
- Check logs for exception type
- Verify exception is in RETRIABLE_EXCEPTIONS list
- Check tenacity decorator is applied

### Issue: SQL gating returns no candidates

**Solution:**
- Verify skills exist in database: `SELECT * FROM rightstaff.skill;`
- Verify candidate-skill links: `SELECT * FROM rightstaff.candidate_skill;`
- Check years_experience field is populated
- Try removing filters one by one to isolate issue

### Issue: Qdrant payload doesn't include skills

**Solution:**
- Check ingestion logs for Stage 4 (skills extraction)
- Verify skills extraction returns non-empty list
- Check payloads construction in ingestion.py Stage 7

---

## PERFORMANCE BENCHMARKS

Expected timings for Day 3 (with added skills extraction):

| Stage | Day 2 | Day 3 | Change |
|-------|-------|-------|--------|
| 1. Fetch Candidate | 0.1s | 0.1s | Same |
| 2. Download Resume | 1-2s | 1-2s | Same |
| 3. Parse Resume | 1-3s | 1-3s | Same |
| **4. Extract Skills** | - | **0.3-1s** | **NEW** |
| 5. Chunk Text | 0.3s | 0.3s | Same |
| 6. Generate Embeddings | 3-10s | 3-10s | Same |
| 7. Store Vectors | 1-2s | 1-2s | Same |
| **TOTAL** | **8-18s** | **9-20s** | **+1-2s** |

**SQL Gating Performance:**
- Must-have skills filter: < 50ms for 10K candidates
- Combined gates (skills + years + location): < 100ms

---

## NEXT STEPS (Day 4 Preview)

After Day 3 completion, Day 4 will add:
- Unit tests for all new services
- Integration tests for full pipeline
- Load testing for retry logic
- Performance profiling for SQL gates
- Documentation updates

**Celebrate Day 3 completion! 🎉**

You now have:
- ✅ Production-grade retry logic
- ✅ Dead Letter Queue for reliability
- ✅ Skills extraction for ranking
- ✅ SQL gating for performance
- ✅ Job management endpoints
- ✅ Monitoring and metrics

This sets the foundation for Days 5-8 semantic ranking implementation!

