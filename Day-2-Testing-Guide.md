# 🧪 Day 2 Testing Guide - Manual Verification Steps

## Overview

This guide provides step-by-step commands to manually test and verify that Day 2 implementation is:
- ✅ 100% bug-free
- ✅ Production-grade
- ✅ All criteria met
- ✅ Ready for future development

**Time Required:** 10-15 minutes  
**Prerequisites:** Docker services running, FastAPI server running

---

## Pre-Flight Checks

### 1. Verify All Services Are Running

```bash
# Check Docker containers status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected Output:**
```
NAMES                   STATUS              PORTS
rightstaff-postgres     Up X minutes        0.0.0.0:5432->5432/tcp
rightstaff-redis        Up X minutes        0.0.0.0:6379->6379/tcp
rightstaff-qdrant       Up X minutes        0.0.0.0:6333->6333/tcp, 0.0.0.0:6334->6334/tcp
rightstaff-minio        Up X minutes        0.0.0.0:9000->9000/tcp, 0.0.0.0:9001->9001/tcp
```

**✅ PASS:** All 4 containers running  
**❌ FAIL:** Any container missing or restarting → Run `docker-compose up -d`

---

### 2. Check FastAPI Health Endpoint

```bash
# Test health endpoint
curl -s http://localhost:8000/health | python -m json.tool
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
    "timestamp": "2025-11-06T..."
}
```

**✅ PASS:** All services show "ok"  
**❌ FAIL:** Any service shows error → Check Docker logs: `docker logs rightstaff-[service-name]`

---

### 3. Verify FastAPI Server is Running

```bash
# Check FastAPI process
# Windows PowerShell:
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Or check the terminal running uvicorn - should see:
# INFO:     Uvicorn running on http://127.0.0.1:8000
```

**✅ PASS:** FastAPI running without errors  
**❌ FAIL:** Server crashed → Check terminal output for error messages

---

## Core Functionality Tests

### 4. Verify Qdrant Collection Exists

```bash
# Check if candidates_v1 collection was created
curl -s http://localhost:6333/collections/candidates_v1 | python -m json.tool
```

**Expected Output:**
```json
{
    "result": {
        "status": "green",
        "vectors_count": ...,
        "points_count": ...,
        "config": {
            "params": {
                "vectors": {
                    "size": 384,
                    "distance": "Cosine"
                }
            }
        }
    }
}
```

**✅ PASS:** Collection exists with vector size 384, Cosine distance  
**❌ FAIL:** Collection doesn't exist → Check ingestion worker startup logs

---

### 5. Get Test Candidate ID

```bash
# Query database for a candidate
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "SELECT id, full_name FROM rightstaff.candidate LIMIT 1;"
```

**Expected Output:**
```
                  id                  |    full_name
--------------------------------------+-----------------
 a1b2c3d4-1234-5678-90ab-cdef12345678 | Prathyusha Elipay
```

**Action:** Copy the UUID (first column) for use in next steps.

**Store in variable (PowerShell):**
```powershell
$CANDIDATE_ID = "PASTE_UUID_HERE"
```

---

### 6. Verify Test Resume Exists in MinIO

```bash
# Check if test resume exists
# Option 1: Via MinIO Console
# Open browser: http://localhost:9001
# Login: minioadmin / minioadmin123
# Navigate to: rightstaff-resumes/resumes/
# Verify: pratz_v2.pdf exists

# Option 2: Via API (if mc client installed)
docker exec rightstaff-minio mc ls local/rightstaff-resumes/resumes/
```

**Expected Output:**
```
[2025-11-06 ...] 245KB pratz_v2.pdf
```

**✅ PASS:** Resume file exists  
**❌ FAIL:** File missing → Check database seed script ran successfully

---

## Pipeline Testing (The Main Event!)

### 7. Trigger Resume Ingestion via Webhook

```bash
# Replace $CANDIDATE_ID with UUID from Step 5

# Windows PowerShell:
$body = @"
{
    "event_type": "profile_created",
    "candidate_id": "$CANDIDATE_ID",
    "timestamp": "2025-11-06T10:00:00Z",
    "s3_resume_url": "s3://rightstaff-resumes/resumes/pratz_v2.pdf",
    "profile_snapshot": {}
}
"@

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/webhooks/candidate-updated" -ContentType "application/json" -Body $body | ConvertTo-Json

# Or using curl (Git Bash / WSL / Linux / Mac):
curl -X POST http://localhost:8000/api/v1/webhooks/candidate-updated \
  -H "Content-Type: application/json" \
  -d "{
    \"event_type\": \"profile_created\",
    \"candidate_id\": \"$CANDIDATE_ID\",
    \"timestamp\": \"2025-11-06T10:00:00Z\",
    \"s3_resume_url\": \"s3://rightstaff-resumes/resumes/pratz_v2.pdf\",
    \"profile_snapshot\": {}
  }"
```

**Expected Response:**
```json
{
    "status": "accepted",
    "candidate_id": "a1b2c3d4-...",
    "processing_job_id": "ingest_a1b2c3d4_1730889600.123",
    "estimated_completion_seconds": 30
}
```

**✅ PASS:** Status 200, returns job_id  
**❌ FAIL:** Error response → Check if candidate_id exists in database

---

### 8. Monitor Pipeline Execution (Real-Time)

**Action:** Watch the terminal running FastAPI. Within 10-30 seconds, you should see:

**Expected Log Output:**
```
📬 Received webhook: profile_created for candidate a1b2c3d4-...
✅ Queued job ingest_a1b2c3d4_...
📦 Processing job ingest_a1b2c3d4_...
[1/6] Fetching candidate details: a1b2c3d4-...
✅ Found candidate: Prathyusha Elipay
[2/6] Downloading resume from s3://rightstaff-resumes/resumes/pratz_v2.pdf
Downloading from bucket=rightstaff-resumes, key=resumes/pratz_v2.pdf
✅ Downloaded 245123 bytes
[3/6] Parsing resume (extracting text)
Parsing resume: pratz_v2.pdf (format: .pdf, size: 245123 bytes)
✅ Extracted 3542 chars (format: pdf, pages: 2)
[4/6] Chunking text (size=400, overlap=50)
Split text into 12 chunks (avg size: 295 chars)
✅ Created 12 chunks
[5/6] Generating embeddings for 12 chunks
Loading embedding model: sentence-transformers/all-MiniLM-L6-v2
⚠️  Using CPU for embeddings (slower, consider GPU for production)
Warming up model with test embedding...
✅ Model loaded successfully (dim=384)
Generating embeddings for 12 texts (batch_size=32)
✅ Generated 12 embeddings (dim=384)
[6/6] Storing vectors in Qdrant
Deleting old vectors for candidate a1b2c3d4-... (if any)
Deleting all vectors for candidate: a1b2c3d4-...
✅ Deleted vectors for candidate: a1b2c3d4-...
Upserting 12 vectors to collection 'candidates_v1'
✅ Successfully upserted 12 vectors
✅✅✅ Successfully processed job ingest_a1b2c3d4_...
   Candidate: Prathyusha Elipay
   Location: State College
   Text: 3542 chars
   Chunks: 12
   Vectors: 12 (dim=384)
```

**Critical Checkpoints:**
- ✅ All 6 stages complete (no errors)
- ✅ Real text extracted (NOT "Placeholder text...")
- ✅ Chunk count reasonable (8-20 for typical resume)
- ✅ Embedding model loads successfully
- ✅ All vectors stored in Qdrant
- ✅ Final summary matches expectations

**❌ FAIL Scenarios:**

| **Symptom** | **Cause** | **Fix** |
|-------------|-----------|---------|
| Stage 3 shows "Placeholder text..." | Old parser code not replaced | Verify `parsers.py` updated with real implementation |
| Stage 5 model load fails | Network issue / model not found | Pre-download: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"` |
| Stage 6 upsert fails | Qdrant connection issue | Check `docker logs rightstaff-qdrant` |
| Empty text extracted (0 chars) | PDF encrypted or corrupted | Try different PDF |

---

### 9. Verify Vectors in Qdrant

```bash
# Check collection statistics
curl -s http://localhost:6333/collections/candidates_v1 | python -m json.tool | grep -E "points_count|vectors_count"
```

**Expected Output:**
```
    "vectors_count": 12,
    "points_count": 12,
```

**✅ PASS:** Points count matches chunks from logs (e.g., 12)  
**❌ FAIL:** Count is 0 → Pipeline didn't complete, check logs

---

### 10. Query Specific Candidate's Vectors

```bash
# Replace $CANDIDATE_ID with your UUID

# PowerShell:
$scrollBody = @"
{
    "filter": {
        "must": [
            {
                "key": "candidate_id",
                "match": {"value": "$CANDIDATE_ID"}
            }
        ]
    },
    "limit": 3,
    "with_payload": true,
    "with_vector": false
}
"@

Invoke-RestMethod -Method Post -Uri "http://localhost:6333/collections/candidates_v1/points/scroll" -ContentType "application/json" -Body $scrollBody | ConvertTo-Json -Depth 5

# Or using curl:
curl -X POST http://localhost:6333/collections/candidates_v1/points/scroll \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {
        \"must\": [{
            \"key\": \"candidate_id\",
            \"match\": {\"value\": \"$CANDIDATE_ID\"}
        }]
    },
    \"limit\": 3,
    \"with_payload\": true,
    \"with_vector\": false
}"
```

**Expected Output:**
```json
{
    "result": {
        "points": [
            {
                "id": "a1b2c3d4-..._chunk_0",
                "payload": {
                    "candidate_id": "a1b2c3d4-...",
                    "chunk_index": 0,
                    "chunk_text": "Software Engineer with 5 years of experience...",
                    "start_char": 0,
                    "end_char": 423,
                    "char_count": 423,
                    "filename": "pratz_v2.pdf",
                    "created_at": "2025-11-06T..."
                }
            },
            ...
        ]
    }
}
```

**✅ PASS:** 
- Points returned (not empty)
- Payload has all required fields
- `chunk_text` contains real resume content (not placeholder)
- `chunk_index` sequential (0, 1, 2, ...)
- `candidate_id` matches

**❌ FAIL:** No points returned → Check if webhook job completed

---

## Advanced Tests

### 11. Test Re-Indexing (Idempotency)

**Purpose:** Verify that re-processing same candidate replaces vectors (no duplicates)

```bash
# Send same webhook AGAIN
# (Use same command as Step 7)

curl -X POST http://localhost:8000/api/v1/webhooks/candidate-updated \
  -H "Content-Type: application/json" \
  -d "{
    \"event_type\": \"resume_uploaded\",
    \"candidate_id\": \"$CANDIDATE_ID\",
    \"timestamp\": \"2025-11-06T11:00:00Z\",
    \"s3_resume_url\": \"s3://rightstaff-resumes/resumes/pratz_v2.pdf\",
    \"profile_snapshot\": {}
  }"
```

**Watch Logs For:**
```
Deleting old vectors for candidate a1b2c3d4-... (if any)
✅ Deleted vectors for candidate: a1b2c3d4-...
```

**Verify Vector Count Unchanged:**
```bash
# Check points count again
curl -s http://localhost:6333/collections/candidates_v1 | python -m json.tool | grep "points_count"
```

**Expected:** Same count as before (e.g., still 12, not 24)

**✅ PASS:** Vector count unchanged, old vectors deleted  
**❌ FAIL:** Count doubled → Delete logic not working

---

### 12. Test with Different Candidate

**Purpose:** Verify pipeline works for multiple candidates

```bash
# Get another candidate ID
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "SELECT id, full_name FROM rightstaff.candidate OFFSET 1 LIMIT 1;"

# Trigger webhook for second candidate (use same resume for testing)
# Follow Step 7 with new candidate_id
```

**Expected:**
- Both candidates' vectors coexist in Qdrant
- Total points_count increases (e.g., 12 → 24)

---

### 13. Test Error Handling - Invalid Candidate

**Purpose:** Verify proper error handling for non-existent candidate

```bash
# Use fake UUID
curl -X POST http://localhost:8000/api/v1/webhooks/candidate-updated \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "profile_created",
    "candidate_id": "00000000-0000-0000-0000-000000000000",
    "timestamp": "2025-11-06T10:00:00Z",
    "s3_resume_url": "s3://rightstaff-resumes/resumes/pratz_v2.pdf",
    "profile_snapshot": {}
  }'
```

**Expected Response:**
```json
{
    "detail": "Candidate 00000000-0000-0000-0000-000000000000 not found"
}
```

**Status Code:** 404

**✅ PASS:** Returns 404, descriptive error message  
**❌ FAIL:** 500 error or generic message → Error handling needs improvement

---

### 14. Test Error Handling - Invalid S3 URL

**Purpose:** Verify graceful failure when file doesn't exist

```bash
# Use valid candidate but fake S3 URL
curl -X POST http://localhost:8000/api/v1/webhooks/candidate-updated \
  -H "Content-Type: application/json" \
  -d "{
    \"event_type\": \"profile_created\",
    \"candidate_id\": \"$CANDIDATE_ID\",
    \"timestamp\": \"2025-11-06T10:00:00Z\",
    \"s3_resume_url\": \"s3://rightstaff-resumes/resumes/nonexistent.pdf\",
    \"profile_snapshot\": {}
  }"
```

**Expected Webhook Response:** 202 Accepted (job queued)

**Expected Worker Logs:**
```
❌ Error downloading s3://rightstaff-resumes/resumes/nonexistent.pdf: ...
❌ Job processing failed: ...
```

**✅ PASS:** Job fails gracefully, descriptive error logged  
**❌ FAIL:** Worker crashes → Error handling insufficient

---

## Code Quality Verification

### 15. Check for Placeholder Code

```bash
# Search for remaining placeholders in Day 2 files
grep -r "Placeholder text" backend/app/services/parsers.py
grep -r "TODO (Day 2)" backend/app/services/
```

**Expected Output:** (no results)

**✅ PASS:** No placeholders or Day 2 TODOs remain  
**❌ FAIL:** Found placeholders → Code not fully implemented

---

### 16. Verify Type Hints

```bash
# Check key functions have type hints
grep "def parse_resume" backend/app/services/parsers.py
grep "def chunk_text" backend/app/services/parsers.py
grep "async def embed_batch" backend/app/services/embeddings.py
```

**Expected:** All functions have type hints for parameters and return values

**Example:**
```python
async def parse_resume(resume_bytes: bytes, filename: str) -> dict:
```

**✅ PASS:** Type hints present  
**❌ FAIL:** Missing type hints → Add them for production readiness

---

### 17. Verify No Blocking Operations in Async

```bash
# Check S3 client uses asyncio.to_thread
grep "asyncio.to_thread" backend/app/services/s3_client.py
```

**Expected:** Found in `download_file()` and `upload_file()` methods

**✅ PASS:** Async properly implemented  
**❌ FAIL:** Not found → Blocking I/O will hurt performance

---

## Performance Benchmarks

### 18. Measure Pipeline Speed

**Action:** Time the complete pipeline execution

```bash
# Trigger webhook and measure time
# Start timer when webhook returns 202
# Stop timer when logs show "✅✅✅ Successfully processed job"

# Typical timings (CPU):
# - Stage 1-2 (DB + S3): <2 seconds
# - Stage 3 (Parsing): 1-3 seconds
# - Stage 4 (Chunking): <1 second
# - Stage 5 (Embeddings): 3-10 seconds (depends on chunk count)
# - Stage 6 (Qdrant): 1-2 seconds
# TOTAL: 8-18 seconds for typical resume
```

**Acceptable Performance:**
- ✅ **Good:** <15 seconds total (CPU)
- ✅ **Excellent:** <5 seconds total (GPU)
- ⚠️ **Slow:** >30 seconds (check CPU usage, model loading)

---

### 19. Check Model Loading Time

**Action:** Restart FastAPI and trigger first embedding job

```bash
# Stop FastAPI (Ctrl+C in terminal)
# Restart: uvicorn app.main:app --reload
# Trigger webhook (Step 7)
# Check logs for model loading time
```

**Expected:**
```
Loading embedding model: sentence-transformers/all-MiniLM-L6-v2
⚠️  Using CPU for embeddings
Warming up model with test embedding...
✅ Model loaded successfully (dim=384)
```

**Model loading should take:** 2-5 seconds (first time only)

**✅ PASS:** Model loads once, stays in memory  
**❌ FAIL:** Model reloads on every job → Lazy loading broken

---

## Final Validation

### 20. Complete Success Checklist

Run through this checklist:

#### Infrastructure
- [ ] All Docker containers running
- [ ] Health endpoint returns all "ok"
- [ ] FastAPI starts without errors
- [ ] No errors in Docker logs

#### PDF Parsing
- [ ] Real text extracted (not "Placeholder text...")
- [ ] Text length >100 chars
- [ ] Format detected (pdf/docx/txt)
- [ ] Multi-page PDFs fully extracted

#### Chunking
- [ ] Text split into multiple chunks (8-20 typical)
- [ ] Chunks have metadata (chunk_index, start_char, end_char)
- [ ] Chunks respect sentence boundaries
- [ ] No empty chunks

#### Embeddings
- [ ] Model loads successfully
- [ ] Device logged (CPU/GPU/MPS)
- [ ] Embeddings dimension = 384
- [ ] Batch processing works

#### Qdrant Storage
- [ ] Collection created (candidates_v1)
- [ ] Vector size = 384
- [ ] Distance = Cosine
- [ ] Points stored successfully
- [ ] Payloads have all fields
- [ ] Re-indexing replaces vectors (no duplicates)

#### Pipeline Integration
- [ ] All 6 stages complete
- [ ] Each stage logs success
- [ ] Final summary accurate
- [ ] End-to-end time reasonable (<20s)

#### Error Handling
- [ ] Invalid candidate returns 404
- [ ] Missing file fails gracefully
- [ ] Error messages descriptive
- [ ] Worker doesn't crash on error

#### Code Quality
- [ ] No placeholder code
- [ ] No "TODO (Day 2)" comments
- [ ] Type hints present
- [ ] Async properly implemented (no blocking)
- [ ] Functions have docstrings

---

## Troubleshooting Reference

### Common Issues

| **Problem** | **Diagnosis Command** | **Solution** |
|-------------|----------------------|--------------|
| Model download fails | Check internet connection | Pre-download model offline |
| PDF parsing empty | `file pratz_v2.pdf` | Try different PDF, check encryption |
| Embeddings dimension wrong | Check model name in config | Verify `all-MiniLM-L6-v2` (384-dim) |
| Qdrant upsert fails | `curl http://localhost:6333/health` | Restart Qdrant container |
| Worker not processing | `docker logs rightstaff-redis` | Check Redis connection |
| Slow embedding | Check CPU usage | Consider GPU, reduce batch_size |

### Quick Reset (If Things Break)

```bash
# Stop everything
docker-compose down

# Clear Qdrant data
rm -rf data/qdrant/*

# Restart
docker-compose up -d

# Restart FastAPI
# (Ctrl+C and run again)
cd backend
uvicorn app.main:app --reload
```

---

## Success Confirmation

If **ALL** of the following are true, Day 2 is **COMPLETE** ✅:

1. ✅ Health checks pass
2. ✅ Real PDF parsing works (verified in logs)
3. ✅ Text chunking creates multiple semantic units
4. ✅ Embeddings generated (384-dimensional)
5. ✅ Vectors stored in Qdrant with metadata
6. ✅ Pipeline runs end-to-end (<20 seconds)
7. ✅ Re-indexing works (no duplicate vectors)
8. ✅ Error handling graceful (no crashes)
9. ✅ No blocking operations in async code
10. ✅ Code quality: type hints, docstrings, no TODOs

**Final Verification Command:**
```bash
# Run complete test sequence
echo "Testing Day 2 Implementation..."
curl -s http://localhost:8000/health | grep -q "healthy" && echo "✅ Health check passed" || echo "❌ Health check failed"
curl -s http://localhost:6333/collections/candidates_v1 | grep -q "384" && echo "✅ Qdrant collection correct" || echo "❌ Qdrant issue"
# Trigger webhook and wait 20 seconds
# Check logs for "✅✅✅ Successfully processed"
```

---

## Next Steps

With Day 2 complete, you're ready for:

- **Day 3:** Error handling (retry logic, dead letter queue, rate limiting)
- **Day 4:** Unit tests, monitoring, observability
- **Days 5-8:** Ranking pipeline (ontology gate, semantic search, structured scoring)

**Congratulations on completing Day 2! 🎉**

The foundation is solid, and all downstream features can now build on this working ingestion pipeline.

