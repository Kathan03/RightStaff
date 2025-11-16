# 🎯 PROMPT 2: RESUME-FIRST UPLOAD WORKFLOW

**Estimated Time:** 4-6 hours
**Priority:** 🔴 CRITICAL
**Prerequisites:** Prompt 1 complete, PostgreSQL/Redis/MinIO running

---

## 📋 OBJECTIVE

Implement resume-first upload workflow where users upload their resume FIRST, the system parses it and pre-fills the form, then ingestion happens ONLY after form submission.

**Current Problem:**
- Users must manually fill long forms before uploading resume
- Full ingestion happens immediately (wasted compute)
- Bad UX + potential for orphaned data if user abandons form

**After This Prompt:**
- Users upload resume first → system parses it (fast!)
- Form auto-fills with parsed data (great UX!)
- Full ingestion ONLY after user submits form (optimized!)
- Zero orphaned data in PostgreSQL/Qdrant

---

## 🎯 IMPLEMENTATION CHECKLIST

### Files to Modify
- [ ] `backend/app/api/candidates.py` - Create 3 new endpoints
- [ ] `backend/app/services/ingestion.py` - Add `mode` parameter (parse_only vs full)
- [ ] `backend/app/services/parsers.py` - Add helper methods for field extraction
- [ ] `backend/app/main.py` - Register candidates router

### Success Criteria
- [ ] POST `/api/v1/candidates/upload-resume` returns temp_id + parsed data
- [ ] GET `/api/v1/candidates/parsed/{temp_id}` retrieves cached data
- [ ] POST `/api/v1/candidates` creates candidate + triggers full ingestion
- [ ] Parse-only mode: NO data in PostgreSQL/Qdrant (only Redis cache)
- [ ] Full mode: Complete 7-stage pipeline
- [ ] Redis cache has 1-hour TTL for temp data

---

## 📝 WORKFLOW OVERVIEW

### Three-Stage Process

```
STAGE 1: Anonymous Resume Upload (Parse Only)
──────────────────────────────────────────────
User uploads resume → MinIO storage → Parse-only ingestion → Redis cache
NO PostgreSQL, NO Qdrant yet!

STAGE 2: Form Pre-Fill (Frontend)
──────────────────────────────────
Frontend fetches parsed data from Redis → Auto-fills form fields
User reviews/edits data

STAGE 3: Candidate Creation (Full Ingestion)
─────────────────────────────────────────────
User submits form → Create candidate in PostgreSQL → Full 7-stage ingestion
Clear Redis cache → All systems consistent!
```

---

## 📝 STEP 1: CREATE CANDIDATES API FILE

### File: `backend/app/api/candidates.py`

**Location:** Create new file

**Complete Code:**

```python
"""
Candidate API Endpoints

WORKFLOW:
1. POST /upload-resume → Anonymous upload, parse-only, cache in Redis
2. GET /parsed/{temp_id} → Fetch cached data for form pre-fill
3. POST / → Create candidate, trigger full ingestion, clear cache
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
import uuid
import json
import asyncio

from app.database import get_db
from app.models.candidate import Candidate, CandidateContact, CandidateResume
from app.config import get_redis_client, get_s3_client
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════

class CandidateCreateRequest(BaseModel):
    """Request body for creating a candidate after form submission."""
    temp_id: str = Field(..., description="Temporary ID from upload-resume endpoint")
    full_name: str
    years_experience: Optional[float] = None
    professional_summary: Optional[str] = None
    location: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class UploadResumeResponse(BaseModel):
    """Response from anonymous resume upload."""
    temp_id: str
    parsed_data: dict
    message: str


class ParsedDataResponse(BaseModel):
    """Response from fetching parsed data."""
    temp_id: str
    data: dict


class CandidateCreateResponse(BaseModel):
    """Response from candidate creation."""
    candidate_id: str
    status: str
    message: str


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 1: Anonymous Resume Upload (Parse Only)
# ═══════════════════════════════════════════════════════════════

@router.post("/upload-resume", response_model=UploadResumeResponse)
async def upload_resume_anonymous(
    file: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)")
):
    """
    Stage 1: Anonymous resume upload with parse-only ingestion.

    WORKFLOW:
    1. Generate temp_id (UUID)
    2. Upload resume to MinIO (resumes/{temp_id}/resume.pdf)
    3. Queue parse-only job to ingestion worker
    4. Wait for parsing to complete (poll Redis)
    5. Return temp_id + parsed data for form pre-fill

    CRITICAL: This does NOT create candidate in PostgreSQL or Qdrant!
    Only caches parsed data in Redis with 1-hour TTL.

    Args:
        file: Resume file upload

    Returns:
        {
            "temp_id": str,
            "parsed_data": {
                "full_name": str,
                "email": str,
                "phone": str,
                "skills": List[str],
                "years_experience": float,
                "location": str,
                "professional_summary": str
            },
            "message": str
        }

    Raises:
        400: Invalid file type
        500: Upload or parsing failed
        504: Parsing timeout (> 30 seconds)
    """
    try:
        # ════════════════════════════════════════════════════════
        # STEP 1: Validate file type
        # ════════════════════════════════════════════════════════
        allowed_types = {".pdf", ".docx", ".doc", ".txt"}
        file_ext = "." + file.filename.split(".")[-1].lower()

        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file_ext}. Allowed: {allowed_types}"
            )

        # ════════════════════════════════════════════════════════
        # STEP 2: Generate temp_id and upload to MinIO
        # ════════════════════════════════════════════════════════
        temp_id = str(uuid.uuid4())
        file_bytes = await file.read()

        s3_client = get_s3_client()
        s3_url = await s3_client.upload_file(
            file_bytes=file_bytes,
            file_name=f"resumes/{temp_id}/resume{file_ext}",
            bucket_name="rightstaff-resumes"
        )

        logger.info(f"📤 Resume uploaded to MinIO: {s3_url} (temp_id: {temp_id})")

        # ════════════════════════════════════════════════════════
        # STEP 3: Queue parse-only ingestion job
        # ════════════════════════════════════════════════════════
        redis_client = get_redis_client()
        job_data = {
            "job_id": f"parse_{temp_id}",
            "candidate_id": temp_id,
            "s3_resume_url": s3_url,
            "mode": "parse_only"  # CRITICAL: Parse-only mode!
        }

        await redis_client.lpush("ingestion_queue", json.dumps(job_data))
        logger.info(f"📋 Queued parse-only job for {temp_id}")

        # ════════════════════════════════════════════════════════
        # STEP 4: Wait for parsing to complete (poll Redis)
        # ════════════════════════════════════════════════════════
        max_retries = 30  # 30 seconds max
        for i in range(max_retries):
            cached = await redis_client.get(f"parsed_candidate:{temp_id}")
            if cached:
                parsed_data = json.loads(cached)
                logger.info(f"✅ Parsing complete for {temp_id}")

                return UploadResumeResponse(
                    temp_id=temp_id,
                    parsed_data=parsed_data,
                    message=f"Resume parsed successfully. Use temp_id to create candidate."
                )

            await asyncio.sleep(1)

        # Timeout after 30 seconds
        raise HTTPException(
            status_code=504,
            detail="Resume parsing timeout. Please try again."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in upload_resume_anonymous: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload resume: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 2: Get Parsed Data (Form Pre-Fill)
# ═══════════════════════════════════════════════════════════════

@router.get("/parsed/{temp_id}", response_model=ParsedDataResponse)
async def get_parsed_data(temp_id: str):
    """
    Stage 2: Retrieve cached parsed data for form pre-fill.

    WORKFLOW:
    1. Fetch from Redis: parsed_candidate:{temp_id}
    2. If expired (> 1 hour) or not found, return 404
    3. Return parsed data for form auto-fill

    Args:
        temp_id: Temporary ID from upload-resume endpoint

    Returns:
        {
            "temp_id": str,
            "data": {
                "full_name": str,
                "email": str,
                "phone": str,
                "skills": List[str],
                "years_experience": float,
                "location": str,
                "professional_summary": str
            }
        }

    Raises:
        404: Session expired or invalid temp_id
    """
    try:
        redis_client = get_redis_client()
        cached = await redis_client.get(f"parsed_candidate:{temp_id}")

        if not cached:
            raise HTTPException(
                status_code=404,
                detail="Session expired or invalid temp_id. Please upload resume again."
            )

        parsed_data = json.loads(cached)
        logger.info(f"📋 Retrieved parsed data for {temp_id}")

        return ParsedDataResponse(
            temp_id=temp_id,
            data=parsed_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in get_parsed_data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve parsed data: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 3: Create Candidate (Full Ingestion)
# ═══════════════════════════════════════════════════════════════

@router.post("/", response_model=CandidateCreateResponse)
async def create_candidate(
    request: CandidateCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Stage 3: Create candidate after form submission.

    WORKFLOW:
    1. Validate temp_id exists in Redis
    2. Create candidate in PostgreSQL
    3. Create contact record
    4. Queue FULL ingestion job (with embeddings)
    5. Clear Redis cache
    6. Return candidate_id

    CRITICAL: This triggers the FULL 7-stage ingestion pipeline!

    Args:
        request: Candidate data from form submission
        db: Database session (injected)

    Returns:
        {
            "candidate_id": str,
            "status": "ingestion_queued",
            "message": str
        }

    Raises:
        400: Invalid or expired temp_id
        500: Database or queue error
    """
    try:
        # ════════════════════════════════════════════════════════
        # STEP 1: Validate temp_id exists in Redis
        # ════════════════════════════════════════════════════════
        redis_client = get_redis_client()
        cached = await redis_client.get(f"parsed_candidate:{request.temp_id}")

        if not cached:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired temp_id. Please upload resume again."
            )

        parsed_data = json.loads(cached)
        logger.info(f"📋 Creating candidate from temp_id: {request.temp_id}")

        # ════════════════════════════════════════════════════════
        # STEP 2: Create candidate in PostgreSQL
        # ════════════════════════════════════════════════════════
        candidate = Candidate(
            id=UUID(request.temp_id),  # Reuse temp_id!
            full_name=request.full_name,
            years_experience=request.years_experience,
            professional_summary=request.professional_summary,
            location=request.location
        )

        db.add(candidate)
        await db.flush()  # Get candidate.id for foreign keys

        # ════════════════════════════════════════════════════════
        # STEP 3: Create contact record
        # ════════════════════════════════════════════════════════
        if request.email or request.phone:
            contact = CandidateContact(
                candidate_id=candidate.id,
                email=request.email,
                phone=request.phone
            )
            db.add(contact)

        await db.commit()
        await db.refresh(candidate)

        logger.info(f"✅ Candidate created: {request.full_name} ({candidate.id})")

        # ════════════════════════════════════════════════════════
        # STEP 4: Queue FULL ingestion job
        # ════════════════════════════════════════════════════════
        s3_client = get_s3_client()
        # Resume already in MinIO from stage 1
        s3_url = f"resumes/{request.temp_id}/resume.pdf"

        job_data = {
            "job_id": f"ingest_{request.temp_id}",
            "candidate_id": request.temp_id,
            "s3_resume_url": s3_url,
            "mode": "full"  # FULL pipeline with embeddings!
        }

        await redis_client.lpush("ingestion_queue", json.dumps(job_data))
        logger.info(f"📋 Queued FULL ingestion job for {candidate.id}")

        # ════════════════════════════════════════════════════════
        # STEP 5: Clear Redis cache
        # ════════════════════════════════════════════════════════
        await redis_client.delete(f"parsed_candidate:{request.temp_id}")
        logger.info(f"🗑️  Cleared Redis cache for {request.temp_id}")

        # ════════════════════════════════════════════════════════
        # STEP 6: Return response
        # ════════════════════════════════════════════════════════
        return CandidateCreateResponse(
            candidate_id=str(candidate.id),
            status="ingestion_queued",
            message=f"Candidate created successfully. Full ingestion in progress."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in create_candidate: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create candidate: {str(e)}"
        )
```

---

## 📝 STEP 2: ADD TWO-MODE SUPPORT TO INGESTION

### File: `backend/app/services/ingestion.py`

**Location:** Modify `process_job` method (around line 170)

**FIND THIS CODE:**
```python
async def process_job(self, job_data: dict):
    """Process a candidate ingestion job."""
    candidate_id = job_data["candidate_id"]
    s3_url = job_data["s3_resume_url"]
```

**REPLACE WITH:**
```python
async def process_job(self, job_data: dict):
    """
    Process a candidate ingestion job.

    MODES:
    - parse_only: Extract text and fields only (Stage 1)
    - full: Complete 7-stage pipeline with embeddings (Stage 3)
    """
    candidate_id = job_data["candidate_id"]
    s3_url = job_data["s3_resume_url"]
    mode = job_data.get("mode", "full")  # Default to full for backward compatibility

    logger.info(f"🚀 Starting ingestion for {candidate_id} (mode: {mode})")

    # ══════════════════════════════════════════════════════════════
    # MODE: PARSE_ONLY (Stage 1 - Resume Upload)
    # ══════════════════════════════════════════════════════════════
    if mode == "parse_only":
        try:
            # Download resume from MinIO
            resume_bytes = await self.s3_client.download_file(s3_url)
            logger.info(f"📥 Downloaded resume from {s3_url}")

            # Parse text from resume
            from app.services.parsers import parse_resume_text
            text = parse_resume_text(resume_bytes, file_type=".pdf")
            logger.info(f"📄 Parsed resume text ({len(text)} chars)")

            # Extract fields
            from app.services.parsers import (
                extract_name,
                extract_email,
                extract_phone,
                extract_location,
                calculate_years_experience
            )

            parsed_data = {
                "full_name": extract_name(text) or "Unknown",
                "email": extract_email(text),
                "phone": extract_phone(text),
                "skills": await self.extract_skills(text),
                "years_experience": calculate_years_experience(text),
                "location": extract_location(text),
                "professional_summary": text[:500]  # First 500 chars
            }

            # Cache in Redis with 1-hour TTL
            await self.redis_client.set(
                f"parsed_candidate:{candidate_id}",
                json.dumps(parsed_data),
                ex=3600  # 1 hour
            )

            logger.info(f"✅ Parse-only complete for {candidate_id}")
            logger.info(f"   Name: {parsed_data['full_name']}")
            logger.info(f"   Email: {parsed_data['email']}")
            logger.info(f"   Skills: {len(parsed_data['skills'])} found")

            return  # STOP HERE - no embeddings, no Qdrant, no PostgreSQL!

        except Exception as e:
            logger.error(f"❌ Parse-only failed for {candidate_id}: {e}")
            raise

    # ══════════════════════════════════════════════════════════════
    # MODE: FULL (Stage 3 - Complete 7-Stage Pipeline)
    # ══════════════════════════════════════════════════════════════
    else:  # mode == "full"
        # ... existing 7-stage pipeline code continues here ...
        # (keep all existing code from line 180 onwards)
```

**CRITICAL:** Keep all existing code for the full pipeline! Only add the parse_only mode BEFORE it.

---

## 📝 STEP 3: ADD FIELD EXTRACTION HELPERS

### File: `backend/app/services/parsers.py`

**Location:** Add after existing parse_resume function

**Code to Add:**

```python
# ═══════════════════════════════════════════════════════════════
# Field Extraction Utilities (for parse-only mode)
# ═══════════════════════════════════════════════════════════════

import re
from typing import Optional
from datetime import datetime


def extract_name(text: str) -> Optional[str]:
    """
    Extract candidate name from resume text.

    HEURISTICS:
    - First non-empty line often contains name
    - Look for capitalized words at start
    - Exclude common headers (Resume, CV, etc.)

    Args:
        text: Resume text

    Returns:
        Extracted name or None
    """
    lines = text.split("\n")
    excluded_words = {"resume", "cv", "curriculum vitae", "professional profile"}

    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if not line:
            continue

        # Skip common headers
        if line.lower() in excluded_words:
            continue

        # Look for capitalized words (likely a name)
        if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+", line):
            return line

    return None


def extract_email(text: str) -> Optional[str]:
    """
    Extract email address from resume text.

    Pattern: word@word.tld

    Args:
        text: Resume text

    Returns:
        Email address or None
    """
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    """
    Extract phone number from resume text.

    Patterns:
    - (123) 456-7890
    - 123-456-7890
    - 123.456.7890
    - +1 123 456 7890

    Args:
        text: Resume text

    Returns:
        Phone number or None
    """
    patterns = [
        r"\(\d{3}\)\s*\d{3}[-.\s]?\d{4}",  # (123) 456-7890
        r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}",  # 123-456-7890
        r"\+\d{1,3}\s?\d{3}\s?\d{3}\s?\d{4}"  # +1 123 456 7890
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return None


def extract_location(text: str) -> Optional[str]:
    """
    Extract location from resume text.

    HEURISTICS:
    - Look for city, state patterns
    - Look for zip codes
    - Common location keywords

    Args:
        text: Resume text

    Returns:
        Location string or None
    """
    # Pattern: City, State ZIP
    pattern = r"[A-Z][a-z]+,\s*[A-Z]{2}\s*\d{5}"
    match = re.search(pattern, text)
    if match:
        return match.group(0)

    # Pattern: City, State
    pattern = r"[A-Z][a-z]+,\s*[A-Z]{2}\b"
    match = re.search(pattern, text)
    if match:
        return match.group(0)

    return None


def calculate_years_experience(text: str) -> Optional[float]:
    """
    Calculate years of experience from resume text.

    HEURISTICS:
    - Find date ranges (Jan 2020 - Dec 2023)
    - Calculate total duration
    - Look for explicit "X years experience" mentions

    Args:
        text: Resume text

    Returns:
        Years of experience or None
    """
    # Pattern: "X years of experience"
    pattern = r"(\d+\.?\d*)\s*(?:\+)?\s*years?\s+(?:of\s+)?experience"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Pattern: Date ranges (TODO: Implement date parsing)
    # For now, return None (can be enhanced later)
    return None


def parse_resume_text(resume_bytes: bytes, file_type: str) -> str:
    """
    Parse resume bytes to text.

    Wrapper around existing parse_resume function.

    Args:
        resume_bytes: Resume file bytes
        file_type: File extension (.pdf, .docx, .txt)

    Returns:
        Extracted text
    """
    from app.services.parsers import parse_resume
    return parse_resume(resume_bytes, file_type)
```

---

## 📝 STEP 4: REGISTER CANDIDATES ROUTER

### File: `backend/app/main.py`

**Location:** After line 46 (where other routers are imported and registered)

**Add Import:**
```python
from app.api import webhooks, jobs, admin, candidates  # Add candidates
```

**Add Router Registration:**
```python
# Register routes
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(candidates.router, prefix="/api/v1/candidates", tags=["candidates"])  # NEW!
```

---

## 🧪 VALIDATION & TESTING

### Step 1: Verify Router Registration

```bash
cd /home/user/RightStaff/backend
python -c "from app.api import candidates; print('✅ Candidates API imports successfully')"
```

### Step 2: Start Server and Check Endpoints

```bash
# Start server
uvicorn app.main:app --reload &

# Wait for startup
sleep 5

# Check Swagger UI
echo "Visit: http://localhost:8000/docs"
echo "Should see 3 new endpoints:"
echo "  - POST /api/v1/candidates/upload-resume"
echo "  - GET /api/v1/candidates/parsed/{temp_id}"
echo "  - POST /api/v1/candidates/"
```

### Step 3: Test Resume Upload (Parse-Only)

```bash
# Create test resume
echo "John Doe
Software Engineer
john.doe@example.com
(123) 456-7890

EXPERIENCE:
Senior Python Developer
2020 - Present

SKILLS:
Python, AWS, Docker, FastAPI
" > /tmp/test_resume.txt

# Upload resume
curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@/tmp/test_resume.txt" \
  | jq .

# Expected response:
# {
#   "temp_id": "uuid-here",
#   "parsed_data": {
#     "full_name": "John Doe",
#     "email": "john.doe@example.com",
#     "phone": "(123) 456-7890",
#     "skills": ["Python", "AWS", "Docker", "FastAPI"],
#     ...
#   },
#   "message": "Resume parsed successfully..."
# }
```

### Step 4: Verify Redis Cache

```bash
# Get temp_id from previous response
TEMP_ID="<temp_id_from_upload>"

# Check Redis cache
docker exec -it rightstaff-redis redis-cli GET "parsed_candidate:${TEMP_ID}"

# Should return JSON with parsed data
```

### Step 5: Verify NO Data in PostgreSQL Yet

```bash
# Check candidates table (should NOT have temp_id yet)
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT id, full_name FROM rightstaff.candidate WHERE id = '${TEMP_ID}';
"

# Expected: 0 rows (data not in PostgreSQL yet!)
```

### Step 6: Test Form Pre-Fill Endpoint

```bash
# Fetch parsed data
curl "http://localhost:8000/api/v1/candidates/parsed/${TEMP_ID}" | jq .

# Expected: Same parsed data as upload response
```

### Step 7: Test Candidate Creation (Full Ingestion)

```bash
# Create candidate (triggers full ingestion)
curl -X POST "http://localhost:8000/api/v1/candidates/" \
  -H "Content-Type: application/json" \
  -d "{
    \"temp_id\": \"${TEMP_ID}\",
    \"full_name\": \"John Doe\",
    \"email\": \"john.doe@example.com\",
    \"phone\": \"(123) 456-7890\",
    \"years_experience\": 5.0,
    \"professional_summary\": \"Senior Python Developer\"
  }" \
  | jq .

# Expected:
# {
#   "candidate_id": "<temp_id>",
#   "status": "ingestion_queued",
#   "message": "Candidate created successfully..."
# }
```

### Step 8: Verify Full Ingestion

```bash
# Wait for ingestion worker to process (10-15 seconds)
sleep 15

# Check PostgreSQL
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT id, full_name, years_experience FROM rightstaff.candidate WHERE id = '${TEMP_ID}';
"

# Expected: 1 row with candidate data

# Check Qdrant
curl "http://localhost:6333/collections/candidates_v1/points/scroll" | jq .

# Should include points with candidate_id metadata
```

---

## 🚨 TROUBLESHOOTING

### Error: "Session expired or invalid temp_id"

**Cause:** Redis cache expired (> 1 hour) or ingestion worker failed

**Solution:**
```bash
# Check Redis
docker exec -it rightstaff-redis redis-cli KEYS "parsed_candidate:*"

# If empty, re-upload resume
```

### Error: "Resume parsing timeout"

**Cause:** Ingestion worker not running or too slow

**Solution:**
```bash
# Check worker logs
docker logs rightstaff-worker

# Restart worker
docker restart rightstaff-worker
```

### Error: "Failed to create candidate"

**Cause:** Database constraint violation or temp_id already used

**Solution:**
```bash
# Check if candidate exists
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT * FROM rightstaff.candidate WHERE id = '${TEMP_ID}';
"

# If exists, use new temp_id (re-upload resume)
```

### Error: "No data in Qdrant after full ingestion"

**Cause:** Ingestion worker failed or collection doesn't exist

**Solution:**
```bash
# Check ingestion worker logs
docker logs rightstaff-worker

# Verify collection exists
curl "http://localhost:6333/collections/candidates_v1"

# If missing, create collection (see vector_store.py)
```

---

## ✅ SUCCESS CRITERIA CHECKLIST

After completing this prompt, verify:

- [ ] POST `/upload-resume` returns temp_id + parsed data
- [ ] GET `/parsed/{temp_id}` retrieves cached data
- [ ] POST `/candidates` creates candidate + queues full ingestion
- [ ] Parse-only mode: NO data in PostgreSQL (check with SELECT query)
- [ ] Parse-only mode: NO data in Qdrant (check with scroll API)
- [ ] Parse-only mode: Data cached in Redis (check with GET)
- [ ] Full mode: Candidate in PostgreSQL (check with SELECT query)
- [ ] Full mode: Embeddings in Qdrant (check with scroll API)
- [ ] Redis cache cleared after candidate creation
- [ ] Redis cache expires after 1 hour (check TTL)

---

## 📊 DATA CONSISTENCY VALIDATION

### Scenario 1: User Abandons Form

```bash
# Upload resume
TEMP_ID=$(curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@/tmp/test_resume.txt" | jq -r '.temp_id')

# DON'T submit form - just wait

# After 1 hour, check Redis
docker exec -it rightstaff-redis redis-cli TTL "parsed_candidate:${TEMP_ID}"
# Should return -2 (expired)

# Check PostgreSQL
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT COUNT(*) FROM rightstaff.candidate WHERE id = '${TEMP_ID}';
"
# Should return 0 (no orphaned data!)
```

### Scenario 2: User Completes Form

```bash
# Upload → Submit → Verify consistency
# (See Step 7-8 in Validation & Testing)

# All systems should be consistent:
# - MinIO: resume.pdf ✅
# - Redis: (deleted) ✅
# - PostgreSQL: candidate ✅
# - Qdrant: embeddings ✅
```

---

## 🎯 PERFORMANCE VALIDATION

**Parse-Only Mode (Stage 1):**
```bash
# Benchmark parsing speed
time curl -X POST "http://localhost:8000/api/v1/candidates/upload-resume" \
  -F "file=@/tmp/test_resume.txt" \
  > /dev/null

# Target: < 3 seconds
```

**Full Ingestion Mode (Stage 3):**
```bash
# Benchmark full pipeline
time curl -X POST "http://localhost:8000/api/v1/candidates/" \
  -H "Content-Type: application/json" \
  -d '{"temp_id": "...", ...}' \
  > /dev/null

# Target: < 15 seconds (background processing acceptable)
```

---

## 📊 WHAT YOU LEARNED

1. **Two-Phase Processing** - Separate parse-only and full ingestion modes
2. **Redis Caching** - Temporary data with TTL for session management
3. **Form Pre-Fill UX** - Better user experience with auto-filled forms
4. **Data Consistency** - Preventing orphaned data across databases
5. **Async File Upload** - FastAPI File handling with MinIO
6. **Text Extraction** - Regex patterns for email, phone, location
7. **Pydantic Models** - Request/response validation
8. **Background Jobs** - Queue-based ingestion with Redis

---

## 🚀 NEXT STEPS

After completing this prompt:

1. **Run all validation steps** - Ensure both modes work
2. **Test abandonment scenario** - Verify no orphaned data
3. **Test completion scenario** - Verify all systems consistent
4. **Check server logs** - Look for emoji markers
5. **Ready for Prompt 3** - Job embeddings optimization

---

**Estimated Completion Time:** 4-6 hours
**Complexity:** Medium-High
**Impact:** 🔴 CRITICAL (fixes UX + prevents orphaned data)

**Ready? Let's implement!** 🚀
