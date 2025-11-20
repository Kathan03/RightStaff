# 🧪 Testing Ingestion Pipelines - Complete Guide

## 📖 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Testing Each Pipeline](#testing-each-pipeline)
4. [Database Verification](#database-verification)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### **1. Start All Services**
```bash
# Make sure all databases are running
cd RightStaff
docker-compose up -d

# Verify services are healthy
docker ps

# Expected output: postgres, qdrant, redis, minio (all "Up")
```

### **2. Start Backend Server**
```bash
# Terminal 1: Start backend server
cd backend
../venv/Scripts/activate  # Windows
source ../venv/bin/activate  # Linux/Mac

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Wait for: "Application startup complete"
```

### **3. Verify Health**
```bash
# Open browser or use curl
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "vector_store": "connected",
    "s3": "connected"
  }
}
```

---

## Quick Start

### **Complete Test Loop (All Pipelines)**

```bash
# Step 1: Clear all data
cd backend
../venv/Scripts/python clear_all_data.py

# Step 2: Populate dummy data (tests all pipelines)
../venv/Scripts/python populate_dummy_data.py

# Step 3: Verify data
../venv/Scripts/python check_database.py
```

**Expected Output:**
```
CLEARING ALL DATA
==================
1️⃣ Clearing PostgreSQL...
   ✅ Cleared table: rightstaff.candidate_skill
   ✅ Cleared table: rightstaff.candidate_contact
   ...
   ✅ PostgreSQL cleared successfully

2️⃣ Clearing MinIO...
   ✅ MinIO cleared: 5 objects deleted

3️⃣ Clearing Qdrant collections...
   ✅ Deleted collection: resumes
   ✅ Deleted collection: jobs_v1
   ✅ Recreated both collections

4️⃣ Clearing Redis cache...
   ✅ Redis cache cleared

✅ All data cleared successfully!

---

POPULATING DUMMY DATA
======================
CREATING JOBS
  ✅ Created 6 new jobs:
     • Senior Python Engineer (San Francisco, CA (Hybrid))
     • Full-Stack Engineer (React + Python) (Remote (US Only))
     ...

1️⃣ Creating skills ontology...
   ✅ Created 50 new skills
   📊 Total skills available: 50

2️⃣ Creating candidates...
   ✅ 1/8: Sarah Chen
   ✅ 2/8: Michael Rodriguez
   ...
   ✅ Created 8 new candidates with full profiles
   📊 Total candidates available: 8

3️⃣ Populating Qdrant with embeddings...
   ✅ 1/8: Sarah Chen (profile + skills + 1 chunk)
   ✅ 2/8: Michael Rodriguez (profile + skills + 1 chunk)
   ...

4️⃣ Uploading resumes to MinIO...
   ✅ 1/8: Sarah Chen - Uploaded 5234 bytes
   ✅ 2/8: Michael Rodriguez - Uploaded 4987 bytes
   ...
   • Uploaded: 5 new resumes
   • Skipped: 3 candidates (for testing)

CREATING JOB EMBEDDINGS
  ✅ Senior Python Engineer: embeddings created
  ✅ Full-Stack Engineer (React + Python): embeddings created
  ...
✅ Created embeddings for 6/6 jobs

CREATING JOB APPLICATIONS
✅ Applications summary:
   • Created: 30 new applications
   • Total jobs: 3
   • Total candidates: 10

✅ Dummy data populated successfully!

📊 Summary:
   • Jobs: 6
   • Candidates: 8
   • Skills: 50
   • Candidate Vectors in Qdrant: 8
   • Job Embeddings in Qdrant: 12 (profile + skills)
   • Resumes in MinIO: 5 (3 candidates without resumes for testing)
```

---

## Testing Each Pipeline

### **Pipeline 1: Candidate Resume Webhook Ingestion**

**LLM Support:** Pipeline 1 now supports LLM-based skill extraction. When `USE_LLM_PARSING=true`, uses hybrid method (LLM + spaCy) for better accuracy. Disabled by default.

#### **Test: Send Webhook**

**Prerequisites:**
- Candidate must exist in PostgreSQL
- Resume file must be in MinIO

**Create Test Candidate:**
```bash
# Terminal 2: Create test candidate in database
cd backend
../venv/Scripts/python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.candidate import Candidate, CandidateContact
from uuid import uuid4

async def create_test_candidate():
    async with AsyncSessionLocal() as db:
        candidate_id = uuid4()
        candidate = Candidate(
            id=candidate_id,
            full_name='Test Webhook User',
            years_experience=5.0,
            professional_summary='Test candidate for webhook testing'
        )
        contact = CandidateContact(
            candidate_id=candidate_id,
            email='test@webhook.com',
            phone='+1-555-9999',
            city='Test City',
            region='CA',
            country='US'
        )
        db.add(candidate)
        db.add(contact)
        await db.commit()
        print(f'Created test candidate: {candidate_id}')

asyncio.run(create_test_candidate())
"
```

**Upload Test Resume to MinIO:**
```bash
# Create test resume file
echo "Test Resume
Name: Test Webhook User
Email: test@webhook.com
Phone: +1-555-9999

EXPERIENCE:
Senior Python Developer - 5 years
Skills: Python, Django, PostgreSQL, AWS, Docker

EDUCATION:
BS Computer Science" > /tmp/test_resume.txt

# Upload to MinIO using curl (copy candidate_id from above)
CANDIDATE_ID="<paste-candidate-id-here>"

curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@/tmp/test_resume.txt" \
  -H "Content-Type: multipart/form-data"

# Note the s3_url from response
```

**Send Webhook:**
```bash
# Send webhook (use candidate_id and s3_url from above)
curl -X POST "http://localhost:8000/api/v1/webhooks/candidate-updated" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "resume_uploaded",
    "candidate_id": "<paste-candidate-id-here>",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "s3_resume_url": "<paste-s3-url-here>",
    "profile_snapshot": {
      "name": "Test Webhook User",
      "email": "test@webhook.com"
    }
  }'
```

**Expected Response:**
```json
{
  "status": "accepted",
  "candidate_id": "...",
  "processing_job_id": "ingest_...",
  "estimated_completion_seconds": 30
}
```

**Verify Processing:**
```bash
# Check backend logs (Terminal 1)
# You should see:
# 📦 Processing job ingest_...
# [1/7] Fetching candidate details: ...
# [2/7] Downloading resume from ...
# [3/7] Parsing resume (extracting text)
# [4/7] Extracting skills from resume text
# [4.5/7] Storing skills in PostgreSQL
# [4.6/8] Storing resume record in PostgreSQL
# [5/8] Chunking text (size=400, overlap=50)
# [6/8] Generating embeddings (1 profile + 1 skills + N chunks)
# [7/8] Storing vectors in Qdrant
# ✅✅✅ Successfully processed job ...
```

**Verify Data in Databases:**
```bash
# PostgreSQL: Check skills were stored
psql -U rightstaff_user -d rightstaff_db -c "
SELECT cs.candidate_id, s.name, cs.level, cs.years
FROM rightstaff.candidate_skill cs
JOIN rightstaff.skill s ON cs.skill_id = s.id
WHERE cs.candidate_id = '<paste-candidate-id-here>';
"

# Expected output:
# candidate_id | name       | level | years
# -------------|------------|-------|------
# ...          | Python     | NULL  | NULL
# ...          | Django     | NULL  | NULL
# ...          | PostgreSQL | NULL  | NULL

# Qdrant: Check vectors were stored
curl "http://localhost:6333/collections/resumes/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "must": [
        {
          "key": "candidate_id",
          "match": {"value": "<paste-candidate-id-here>"}
        }
      ]
    },
    "limit": 10
  }' | python -m json.tool

# Expected: 3+ points (1 profile + 1 skills + N chunks)
```

---

### **Pipeline 2: Candidate Resume Upload via API**

#### **Test: Complete 3-Stage Process**

**Stage 1: Upload Resume (Parse-Only)**
```bash
# Create test resume
echo "John Smith
Email: john.smith@example.com
Phone: +1-555-1234
Location: Seattle, WA

PROFESSIONAL SUMMARY:
Experienced software engineer with 8 years in backend development.

SKILLS:
- Python (Expert, 8 years)
- FastAPI (Advanced, 3 years)
- PostgreSQL (Expert, 7 years)
- Docker (Advanced, 4 years)
- AWS (Intermediate, 5 years)

EXPERIENCE:
Senior Backend Engineer at TechCorp (2020 - Present)
- Built scalable microservices using FastAPI
- Managed PostgreSQL databases
- Deployed to AWS with Docker" > /tmp/john_smith_resume.txt

# Upload resume
curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@/tmp/john_smith_resume.txt" \
  | python -m json.tool
```

**Expected Response:**
```json
{
  "temp_id": "temporary-uuid-1234",
  "parsed_data": {
    "full_name": "John Smith",
    "email": "john.smith@example.com",
    "phone": "+1-555-1234",
    "location": {
      "city": "Seattle",
      "region": "WA",
      "country": "US"
    },
    "years_experience": 8.0,
    "professional_summary": "Experienced software engineer...",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
    "s3_resume_url": "s3://bucket/resumes/temporary-uuid-1234/resume.txt"
  },
  "message": "Resume parsed successfully. Use temp_id to create candidate."
}
```

**Stage 2: Get Parsed Data**
```bash
# Get parsed data using temp_id from Stage 1
TEMP_ID="<paste-temp-id-here>"

curl "http://localhost:8000/api/v1/candidates/parsed/${TEMP_ID}" \
  | python -m json.tool
```

**Expected Response:**
```json
{
  "temp_id": "temporary-uuid-1234",
  "data": {
    "full_name": "John Smith",
    "email": "john.smith@example.com",
    ...
  }
}
```

**Stage 3: Create Candidate**
```bash
# Create candidate using temp_id
curl -X POST "http://localhost:8000/api/v1/candidates/" \
  -H "Content-Type: application/json" \
  -d '{
    "temp_id": "'${TEMP_ID}'",
    "full_name": "John Smith",
    "years_experience": 8.0,
    "professional_summary": "Experienced software engineer with 8 years in backend development.",
    "email": "john.smith@example.com",
    "phone": "+1-555-1234",
    "location": "Seattle, WA"
  }' | python -m json.tool
```

**Expected Response:**
```json
{
  "candidate_id": "permanent-uuid-5678",
  "status": "ingestion_queued",
  "message": "Candidate created successfully. Full ingestion in progress."
}
```

**Verify Full Ingestion:**
```bash
# Wait 30 seconds for background processing
sleep 30

# Check PostgreSQL
psql -U rightstaff_user -d rightstaff_db -c "
SELECT c.id, c.full_name, c.years_experience, cc.email, cc.city, cc.region
FROM rightstaff.candidate c
JOIN rightstaff.candidate_contact cc ON c.id = cc.candidate_id
WHERE c.full_name = 'John Smith';
"

# Expected output: One row with John Smith's data

# Check Qdrant vectors
curl "http://localhost:6333/collections/resumes/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "must": [
        {
          "key": "full_name",
          "match": {"value": "John Smith"}
        }
      ]
    },
    "limit": 10
  }' | python -m json.tool

# Expected: 3+ points (profile + skills + chunks)
```

---

### **Pipeline 3: Job Ingestion via Webhook**

#### **Test: Send Job Webhook**

```bash
# Send job ingestion webhook
curl -X POST "http://localhost:8000/api/v1/webhooks/job-ingestion" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-job-'$(uuidgen)'",
    "title": "Senior DevOps Engineer",
    "description": "We are looking for an experienced DevOps engineer to manage our cloud infrastructure. Must have experience with AWS, Terraform, Docker, and Kubernetes. You will be responsible for CI/CD pipelines and system reliability.",
    "required_skills": ["AWS", "Terraform", "Docker", "Kubernetes", "Python"],
    "must_have_skills": ["AWS", "Docker"],
    "preferred_skills": ["Jenkins", "Ansible"]
  }' | python -m json.tool
```

**Expected Response:**
```json
{
  "status": "success",
  "job_id": "test-job-uuid",
  "embeddings_created": true,
  "cached": true,
  "profile_text": "Senior DevOps Engineer\nWe are looking for...",
  "skills_count": 12
}
```

**Verify Qdrant Storage:**
```bash
# Check jobs_v1 collection
curl "http://localhost:6333/collections/jobs_v1/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 20
  }' | python -m json.tool

# Should see 2 points per job (profile + skills)
```

**Verify Redis Cache:**
```bash
# Check Redis cache
docker exec -it rightstaff-redis-1 redis-cli

# In Redis CLI:
KEYS job_embeddings:*
GET job_embeddings:test-job-uuid
# (Should see JSON with profile_vector and skills_vector)

EXIT
```

---

### **Pipeline 4: Dummy Data Population**

This pipeline is tested by the Quick Start section. See above.

---

## Database Verification

### **PostgreSQL Verification**

#### **Connect to PostgreSQL:**
```bash
# Option 1: Using psql from host
psql -U rightstaff_user -d rightstaff_db -h localhost -p 5432

# Option 2: Using Docker
docker exec -it rightstaff-postgres-1 psql -U rightstaff_user -d rightstaff_db
```

#### **Check All Tables:**
```sql
-- Set schema
SET search_path TO rightstaff;

-- Count records in each table
SELECT
    'candidate' as table_name, COUNT(*) as count FROM candidate
UNION ALL
SELECT 'candidate_contact', COUNT(*) FROM candidate_contact
UNION ALL
SELECT 'candidate_resume', COUNT(*) FROM candidate_resume
UNION ALL
SELECT 'skill', COUNT(*) FROM skill
UNION ALL
SELECT 'candidate_skill', COUNT(*) FROM candidate_skill
UNION ALL
SELECT 'job', COUNT(*) FROM job
UNION ALL
SELECT 'application', COUNT(*) FROM application;
```

**Expected Output (after populate_dummy_data.py):**
```
   table_name     | count
------------------+-------
 candidate        |     8
 candidate_contact|     8
 candidate_resume |     5
 skill            |    50
 candidate_skill  |    50
 job              |     6
 application      |    30
```

#### **Verify Candidate Data:**
```sql
-- Get candidate with contact and skills
SELECT
    c.full_name,
    c.years_experience,
    cc.email,
    cc.city,
    cc.region,
    STRING_AGG(s.name, ', ' ORDER BY s.name) as skills
FROM candidate c
JOIN candidate_contact cc ON c.id = cc.candidate_id
LEFT JOIN candidate_skill cs ON c.id = cs.candidate_id
LEFT JOIN skill s ON cs.skill_id = s.id
GROUP BY c.id, c.full_name, c.years_experience, cc.email, cc.city, cc.region
ORDER BY c.full_name;
```

**Expected Output:**
```
  full_name        | years_experience |        email        |     city      | region |           skills
-------------------+------------------+---------------------+---------------+--------+----------------------------
 Sarah Chen        |             8.00 | sarah.chen@...      | San Francisco | CA     | AWS, Docker, FastAPI, ...
 Michael Rodriguez |             5.00 | m.rodriguez@...     | Austin        | TX     | Apache Spark, AWS, ...
 ...
```

#### **Verify Resume Records:**
```sql
-- Check resume records
SELECT
    c.full_name,
    cr.s3_url,
    cr.file_type,
    cr.is_latest,
    cr.uploaded_at
FROM candidate_resume cr
JOIN candidate c ON cr.candidate_id = c.id
ORDER BY cr.uploaded_at DESC;
```

#### **Verify Skills Linking:**
```sql
-- Count skills per candidate
SELECT
    c.full_name,
    COUNT(cs.skill_id) as skill_count,
    STRING_AGG(s.name, ', ' ORDER BY s.name) as skills
FROM candidate c
LEFT JOIN candidate_skill cs ON c.id = cs.candidate_id
LEFT JOIN skill s ON cs.skill_id = s.id
GROUP BY c.id, c.full_name
ORDER BY skill_count DESC;
```

#### **Verify Job Applications:**
```sql
-- Check applications
SELECT
    j.title as job_title,
    c.full_name as candidate_name,
    a.status,
    a.applied_at
FROM application a
JOIN job j ON a.job_id = j.id
JOIN candidate c ON a.candidate_id = c.id
ORDER BY j.title, c.full_name;
```

---

### **Qdrant Verification**

#### **Check Collection Info:**
```bash
# Get collection stats
curl "http://localhost:6333/collections/resumes" | python -m json.tool

# Expected response:
{
  "result": {
    "status": "green",
    "optimizer_status": "ok",
    "vectors_count": 24,      # 8 candidates × 3 vectors
    "indexed_vectors_count": 24,
    "points_count": 24,
    "segments_count": 1,
    ...
  }
}

# Check jobs_v1 collection
curl "http://localhost:6333/collections/jobs_v1" | python -m json.tool

# Expected:
{
  "result": {
    "vectors_count": 12,      # 6 jobs × 2 vectors
    "points_count": 12,
    ...
  }
}
```

#### **Verify Candidate Vectors:**
```bash
# Get all vectors for a specific candidate
curl "http://localhost:6333/collections/resumes/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "must": [
        {
          "key": "full_name",
          "match": {"value": "Sarah Chen"}
        }
      ]
    },
    "limit": 10,
    "with_payload": true,
    "with_vector": false
  }' | python -m json.tool
```

**Expected Response:**
```json
{
  "result": {
    "points": [
      {
        "id": "uuid-1",
        "payload": {
          "candidate_id": "...",
          "kind": "profile",
          "full_name": "Sarah Chen",
          "text": "Sarah Chen\nSenior Full-Stack Engineer...",
          "skills": ["Python", "React", "PostgreSQL", "AWS", "Docker", ...],
          "created_at": "2024-01-15T10:30:00Z"
        }
      },
      {
        "id": "uuid-2",
        "payload": {
          "candidate_id": "...",
          "kind": "skills",
          "skills": ["Python", "React", ...],
          "skills_count": 7
        }
      },
      {
        "id": "uuid-3",
        "payload": {
          "candidate_id": "...",
          "kind": "chunk",
          "chunk_index": 0,
          "chunk_text": "...",
          "skills_detected": ["Python", "React"]
        }
      }
    ]
  }
}
```

#### **Verify Vector Kinds:**
```bash
# Count vectors by kind
curl "http://localhost:6333/collections/resumes/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 100,
    "with_payload": ["kind"],
    "with_vector": false
  }' | python -m json.tool | grep '"kind"' | sort | uniq -c

# Expected output:
#   8 "kind": "profile"
#   8 "kind": "skills"
#   8 "kind": "chunk"    (or more if chunks > 1)
```

#### **Verify Job Vectors:**
```bash
# Get all job vectors
curl "http://localhost:6333/collections/jobs_v1/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 20,
    "with_payload": true,
    "with_vector": false
  }' | python -m json.tool
```

**Expected:** 2 points per job (profile + skills)

---

### **Redis Verification**

```bash
# Connect to Redis
docker exec -it rightstaff-redis-1 redis-cli

# In Redis CLI:

# Check all keys
KEYS *

# Expected keys:
# - ingestion_queue (LIST)
# - parsed_candidate:* (STRING with TTL)
# - job_rankings:* (STRING with TTL)
# - job_embeddings:* (STRING with TTL)
# - dlq (LIST)

# Check queue depth
LLEN ingestion_queue
# Expected: 0 (all jobs processed)

# Check DLQ
LLEN dlq
# Expected: 0 (no failed jobs)

# Check cached parsed candidates
KEYS parsed_candidate:*
# Expected: May have active sessions

# Get a cached candidate
GET parsed_candidate:<some-temp-id>
# Expected: JSON with parsed data

# Check TTL (time to live)
TTL parsed_candidate:<some-temp-id>
# Expected: Number of seconds remaining (up to 3600)

EXIT
```

---

### **MinIO Verification**

```bash
# Option 1: Web UI
# Open http://localhost:9001 in browser
# Login: minioadmin / minioadmin
# Navigate to "rightstaff-resumes" bucket
# Should see resumes/ folder with files

# Option 2: Using mc (MinIO Client)
# Install mc: https://min.io/docs/minio/linux/reference/minio-mc.html

# Configure mc
mc alias set local http://localhost:9000 minioadmin minioadmin

# List all objects
mc ls local/rightstaff-resumes/resumes/ --recursive

# Expected output:
# [2024-01-15 10:30:00 PST] 5.2KiB resumes/candidate-uuid-1/sarah_chen_resume.txt
# [2024-01-15 10:30:05 PST] 4.9KiB resumes/candidate-uuid-2/michael_rodriguez_resume.txt
# ...

# Count objects
mc ls local/rightstaff-resumes/resumes/ --recursive | wc -l
# Expected: 5 (after populate_dummy_data.py)

# Download a resume for inspection
mc cp local/rightstaff-resumes/resumes/candidate-uuid-1/resume.txt /tmp/test_resume.txt
cat /tmp/test_resume.txt
```

---

## Troubleshooting

### **Issue: Webhook Returns 404 "Candidate not found"**

**Cause:** Candidate doesn't exist in PostgreSQL

**Solution:**
```bash
# Verify candidate exists
psql -U rightstaff_user -d rightstaff_db -c "
SELECT id, full_name FROM rightstaff.candidate
WHERE id = '<candidate-id-from-webhook>';
"

# If empty, create candidate first (see Pipeline 2 test)
```

---

### **Issue: Parse-Only Mode Times Out (504 Error)**

**Cause:**
- Ingestion worker not running
- Job queue blocked
- Resume file too large

**Solution:**
```bash
# 1. Check if worker is running
# Look for logs: "Ingestion worker started - polling Redis queue"

# 2. Check Redis queue depth
docker exec -it rightstaff-redis-1 redis-cli LLEN ingestion_queue
# If > 10, worker might be slow

# 3. Check DLQ for errors
docker exec -it rightstaff-redis-1 redis-cli LLEN dlq
# If > 0, check errors:
docker exec -it rightstaff-redis-1 redis-cli LRANGE dlq 0 -1

# 4. Check resume file size
ls -lh /tmp/test_resume.txt
# Should be < 10MB
```

---

### **Issue: No Vectors in Qdrant**

**Cause:**
- Full ingestion mode not triggered
- Embeddings service failed
- Qdrant connection issue

**Solution:**
```bash
# 1. Check backend logs for errors
# Look for: "✅✅✅ Successfully processed job"
# Or errors: "❌ Job processing failed"

# 2. Verify Qdrant is accessible
curl http://localhost:6333/collections

# 3. Check if collections exist
curl http://localhost:6333/collections/resumes
curl http://localhost:6333/collections/jobs_v1

# 4. Manually test embeddings
cd backend
../venv/Scripts/python -c "
import asyncio
from app.services.embeddings import embedding_service

async def test():
    embedding = await embedding_service.embed_text('test')
    print(f'Embedding dim: {len(embedding)}')

asyncio.run(test())
"
# Expected: Embedding dim: 384
```

---

### **Issue: Skills Not Stored in PostgreSQL**

**Cause:**
- Skills extraction failed
- Ontology service error
- Skills already exist but not linked

**Solution:**
```bash
# 1. Check if skills exist in skill table
psql -U rightstaff_user -d rightstaff_db -c "
SELECT COUNT(*) FROM rightstaff.skill;
"
# Expected: > 0

# 2. Check candidate_skill links
psql -U rightstaff_user -d rightstaff_db -c "
SELECT COUNT(*) FROM rightstaff.candidate_skill;
"
# Expected: > 0

# 3. Test skill extraction manually
cd backend
../venv/Scripts/python -c "
import asyncio
from app.services.ontology import extract_skills_from_text

async def test():
    text = 'Experienced in Python, Django, and PostgreSQL'
    skills = await extract_skills_from_text(text)
    print(f'Extracted skills: {skills}')

asyncio.run(test())
"
# Expected: Extracted skills: ['Python', 'Django', 'PostgreSQL']
```

---

### **Issue: Redis Cache Not Working**

**Cause:**
- Redis connection issue
- TTL expired too quickly
- Wrong key pattern

**Solution:**
```bash
# 1. Test Redis connection
docker exec -it rightstaff-redis-1 redis-cli PING
# Expected: PONG

# 2. Check if Redis is accepting connections
docker exec -it rightstaff-redis-1 redis-cli INFO server

# 3. Monitor Redis operations in real-time
docker exec -it rightstaff-redis-1 redis-cli MONITOR
# (Run operations in another terminal and watch output)
```

---

### **Issue: MinIO Files Not Uploading**

**Cause:**
- MinIO not accessible
- Bucket doesn't exist
- Credentials wrong

**Solution:**
```bash
# 1. Check MinIO is running
docker ps | grep minio

# 2. Test MinIO connection
curl http://localhost:9000/minio/health/live
# Expected: Empty response with 200 status

# 3. Check bucket exists
mc ls local/
# Should see "rightstaff-resumes"

# 4. Create bucket if missing
mc mb local/rightstaff-resumes

# 5. Test upload manually
echo "test content" > /tmp/test.txt
mc cp /tmp/test.txt local/rightstaff-resumes/test.txt
mc ls local/rightstaff-resumes/
```

---

## Summary

### **Complete Verification Checklist**

After running all tests, verify:

- [ ] **PostgreSQL**
  - [ ] 8 candidates created
  - [ ] 8 candidate_contact records
  - [ ] 5 candidate_resume records
  - [ ] 50+ skills in skill table
  - [ ] 50+ candidate_skill links
  - [ ] 6 jobs created
  - [ ] 30 applications created

- [ ] **Qdrant**
  - [ ] 24 candidate vectors (8 × 3)
  - [ ] 12 job vectors (6 × 2)
  - [ ] All payloads have correct structure
  - [ ] Vector dimensions = 384

- [ ] **Redis**
  - [ ] ingestion_queue empty (all processed)
  - [ ] dlq empty (no failures)
  - [ ] Cached data has TTL set
  - [ ] Job embeddings cached

- [ ] **MinIO**
  - [ ] 5 resume files uploaded
  - [ ] Files follow naming pattern: `resumes/{candidate_id}/resume.{ext}`
  - [ ] Files are accessible and downloadable

---

**Document Version:** 1.0
**Last Updated:** 2025-01-19
**Maintained By:** RightStaff Development Team
