# 🚀 RightStaff Day-5 Implementation Plan
## Complete Application Tracking + Job Embeddings Optimization

**Timeline:** 2 Days (Fast Development with Claude Code)
**Goal:** Production-ready MVP with application tracking and optimized job embeddings
**Approach:** 3 detailed prompts for systematic implementation

---

## 📊 EXECUTIVE SUMMARY

### Current State (Before Implementation)
- ✅ Basic ingestion pipeline (candidate resumes)
- ✅ SQL filtering + Dense retrieval + Structured scoring
- ✅ Ranking API works for ALL candidates (incorrect)
- ❌ NO application tracking (ranks everyone, not just applicants)
- ❌ Job embeddings created on-the-fly during ranking (slow)
- ❌ Resume-first upload workflow missing

### Target State (After Implementation)
- ✅ Application tracking (rank ONLY applicants)
- ✅ Job embeddings at ingestion time (fast ranking)
- ✅ Resume-first upload (parse → form pre-fill → submit → ingest)
- ✅ Separate Qdrant collections (candidates_v1, jobs_v1)
- ✅ Zero data inconsistencies across PostgreSQL, Qdrant, MinIO, Redis

### Architecture Changes

```
┌────────────────────────────────────────────────────────────────┐
│                   BEFORE (Current Issues)                       │
├────────────────────────────────────────────────────────────────┤
│  1. Ranking searches ALL candidates (10,000+)                  │
│  2. Job embeddings created during ranking (slow)               │
│  3. Resume upload → immediate ingestion (no form pre-fill)     │
│  4. Jobs + Candidates in same Qdrant collection (messy)        │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                   AFTER (Optimized Design)                      │
├────────────────────────────────────────────────────────────────┤
│  1. Ranking searches ONLY applicants (~100)                    │
│  2. Job embeddings pre-computed at job creation (fast)         │
│  3. Resume → parse → form → submit → ingest (UX optimized)     │
│  4. Separate collections: candidates_v1, jobs_v1 (clean)       │
└────────────────────────────────────────────────────────────────┘
```

---

## 🎯 IMPLEMENTATION OVERVIEW

### Task Breakdown (3 Prompts)

| Prompt | Focus Area | Estimated Time | Critical Path |
|--------|-----------|----------------|---------------|
| **Prompt 1** | Application Tracking + Database Models | 4-6 hours | ✅ CRITICAL |
| **Prompt 2** | Resume-First Upload + Ingestion Modes | 4-6 hours | ✅ CRITICAL |
| **Prompt 3** | Job Embeddings Optimization + Collection Separation | 3-4 hours | 🟡 HIGH |

**Total Time:** ~12-16 hours (2 days with testing)

---

## 📋 PROMPT 1: APPLICATION TRACKING SYSTEM

### Objective
Implement complete job application tracking so ranking only searches candidates who applied to a job.

### Files Modified
1. `backend/app/models/candidate.py` - Add Application model + relationships
2. `backend/app/api/jobs.py` - Add `/jobs/{job_id}/apply` endpoint
3. `backend/app/services/ranking.py` - Filter by applications FIRST
4. `backend/app/services/sql_filter.py` - Accept `application_ids` parameter
5. `backend/populate_dummy_data.py` - Create sample applications
6. `backend/clear_all_data.py` - Clear applications table

### Success Criteria
- ✅ Application model exists and imports successfully
- ✅ POST `/api/v1/jobs/{job_id}/apply` creates applications
- ✅ Duplicate applications return 409 Conflict
- ✅ Ranking pipeline filters by applications (Step 2a in ranking.py)
- ✅ SQL gates receive `application_ids` parameter
- ✅ Test data includes applications

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│              APPLICATION TRACKING WORKFLOW                   │
└─────────────────────────────────────────────────────────────┘

1. Candidate applies to job
   POST /api/v1/jobs/{job_id}/apply
   ├── Validate job exists and is open
   ├── Validate candidate exists
   ├── Check for duplicate application (UNIQUE constraint)
   ├── Create application record
   └── Return: {application_id, status: "applied"}

2. Recruiter triggers ranking
   POST /api/v1/jobs/{job_id}/rank_full
   ├── Step 2a: Get applicants
   │   SELECT candidate_id FROM application WHERE job_id = ?
   │   Result: [uuid1, uuid2, ..., uuid100]
   │
   ├── Step 2b: Apply SQL gates ON applicants
   │   filter_by_skills(application_ids=[uuid1, uuid2, ...])
   │   Result: [uuid1, uuid5, ...] (subset who meet requirements)
   │
   ├── Step 3: Dense retrieval on eligible
   ├── Step 4: Structured scoring
   └── Return: Ranked applicants
```

### Database Schema

```sql
-- Already exists in database/scripts/01_schema.sql (lines 277-285)
CREATE TABLE IF NOT EXISTS application (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id  uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  job_id        uuid NOT NULL REFERENCES job(id) ON DELETE CASCADE,
  status        application_status_enum NOT NULL DEFAULT 'applied',
  applied_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (candidate_id, job_id)
);
```

### Critical Implementation Details

#### 1. Application Model (candidate.py)

```python
class ApplicationStatus(str, enum.Enum):
    """Matches database enum exactly."""
    sourced = "sourced"
    applied = "applied"
    screen = "screen"
    shortlist = "shortlist"
    interview = "interview"
    offer = "offer"
    hired = "hired"
    rejected = "rejected"
    withdrawn = "withdrawn"


class Application(Base):
    __tablename__ = "application"
    __table_args__ = {"schema": "rightstaff"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("rightstaff.candidate.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("rightstaff.job.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLEnum(ApplicationStatus, schema="rightstaff", name="application_status_enum"), nullable=False, default=ApplicationStatus.applied)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
```

**Why CASCADE?**
- Delete candidate → auto-delete their applications
- Maintains referential integrity
- Prevents orphaned records

#### 2. Ranking Pipeline Changes (ranking.py lines 92-101)

**BEFORE (Wrong):**
```python
# Step 2: SQL gating
eligible_candidate_ids = await apply_combined_sql_gates(
    must_have_skills=job_data.get('must_have_skills_json', []),
    ...
)
# Problem: Searches ALL candidates in database
```

**AFTER (Correct):**
```python
# Step 2a: Get candidates who applied to this job
from app.models.candidate import Application
async with AsyncSessionLocal() as db:
    application_result = await db.execute(
        select(Application.candidate_id)
        .where(Application.job_id == job_id)
    )
    applied_candidate_ids = [str(row[0]) for row in application_result.all()]

if not applied_candidate_ids:
    logger.warning(f"No applications for job {job_id}")
    return []

logger.info(f"📋 {len(applied_candidate_ids)} candidates applied")

# Step 2b: Apply SQL gates ONLY on applicants
eligible_candidate_ids = await apply_combined_sql_gates(
    application_ids=applied_candidate_ids,  # NEW!
    must_have_skills=job_data.get('must_have_skills_json', []),
    ...
)
```

**Performance Impact:**
- Before: Search 10,000 candidates
- After: Search 100 applicants
- **100x faster!**

#### 3. SQL Filter Changes (sql_filter.py)

**New Signature:**
```python
async def filter_candidates_by_must_have_skills(
    must_have_skills: List[str],
    application_ids: Optional[List[str]] = None,  # NEW PARAMETER
    db: Optional[AsyncSession] = None
) -> Set[str]:
    """
    Filter candidates by skills, optionally scoped to application_ids.

    CRITICAL: If application_ids provided, filter by them FIRST (reduces search space).
    """
```

**Query Logic:**
```python
query = (
    select(CandidateSkill.candidate_id)
    .join(Skill, CandidateSkill.skill_id == Skill.id)
    .where(Skill.name.in_(must_have_skills))
)

# NEW: Filter by application_ids FIRST (if provided)
if application_ids:
    from uuid import UUID
    uuid_list = [UUID(app_id) for app_id in application_ids]
    query = query.where(CandidateSkill.candidate_id.in_(uuid_list))

# Then apply skill matching
query = query.group_by(CandidateSkill.candidate_id).having(
    func.count(func.distinct(CandidateSkill.skill_id)) == len(must_have_skills)
)
```

**Why Filter Applications First?**
- SQL index on application.job_id is fast
- Reduces candidate_skill join size
- PostgreSQL query optimizer benefits from smaller dataset

---

## 📋 PROMPT 2: RESUME-FIRST UPLOAD WORKFLOW

### Objective
Implement resume-first upload with form pre-fill, ensuring ingestion happens ONLY after form submission.

### Files Modified
1. `backend/app/api/candidates.py` - Implement 3 new endpoints
2. `backend/app/services/ingestion.py` - Add `mode` parameter (parse_only vs full)
3. `backend/app/services/parsers.py` - Add helper methods for field extraction
4. `backend/app/main.py` - Register candidates router

### Success Criteria
- ✅ POST `/api/v1/candidates/upload-resume` returns temp_id + parsed data
- ✅ GET `/api/v1/candidates/parsed/{temp_id}` retrieves cached data
- ✅ POST `/api/v1/candidates` creates candidate + triggers full ingestion
- ✅ Ingestion.py supports two modes: parse_only and full
- ✅ Redis cache has 1-hour TTL for temp data
- ✅ **CRITICAL:** No data in PostgreSQL/Qdrant until form submission

### Workflow Comparison

**OLD WORKFLOW (Current):**
```
1. User fills out long form manually
2. User uploads resume at end
3. System ingests resume (full pipeline)
4. User waits for processing
❌ Bad UX: Manual data entry
❌ Wasted compute: Full ingestion before user commits
```

**NEW WORKFLOW (Optimized):**
```
1. User uploads resume FIRST
2. System parses resume (parse-only mode, NO embeddings)
3. System caches parsed data in Redis (1 hour TTL)
4. Frontend pre-fills form with parsed data
5. User reviews/edits form (quick!)
6. User submits form
7. System creates candidate in PostgreSQL + triggers FULL ingestion
✅ Better UX: Auto-filled form
✅ Optimized compute: Full ingestion only after commit
✅ No orphaned data: Temp data auto-expires
```

### Data Flow

```
┌────────────────────────────────────────────────────────────────┐
│           RESUME-FIRST UPLOAD WORKFLOW (3 Stages)              │
└────────────────────────────────────────────────────────────────┘

STAGE 1: Anonymous Resume Upload (Parse Only)
─────────────────────────────────────────────
POST /api/v1/candidates/upload-resume
  ├── Generate temp_id (UUID)
  ├── Upload resume to MinIO: resumes/{temp_id}/resume.pdf
  ├── Queue job to ingestion worker with mode="parse_only"
  ├── Ingestion worker:
  │   ├── Download resume from MinIO
  │   ├── Parse text (PDF/DOCX/TXT)
  │   ├── Extract fields:
  │   │   ├── full_name (regex + heuristics)
  │   │   ├── email (regex)
  │   │   ├── phone (regex)
  │   │   ├── skills (ontology.extract_skills)
  │   │   ├── years_experience (calculate from dates)
  │   │   └── location (NER extraction)
  │   ├── Cache in Redis: parsed_candidate:{temp_id}
  │   └── STOP HERE (no embeddings, no Qdrant, no PostgreSQL)
  └── Return: {temp_id, parsed_data: {...}}

STAGE 2: Form Pre-Fill (Frontend)
──────────────────────────────────
GET /api/v1/candidates/parsed/{temp_id}
  ├── Fetch from Redis: parsed_candidate:{temp_id}
  ├── If expired (> 1 hour): Return 404
  └── Return parsed_data for form auto-fill

STAGE 3: Candidate Creation (Full Ingestion)
─────────────────────────────────────────────
POST /api/v1/candidates
  ├── Body: {temp_id, full_name, email, skills, ...}
  ├── Validate temp_id exists in Redis
  ├── Create candidate in PostgreSQL:
  │   candidate = Candidate(
  │       id=UUID(temp_id),  # Reuse temp_id!
  │       full_name=request.full_name,
  │       ...
  │   )
  ├── Queue job to ingestion worker with mode="full"
  ├── Ingestion worker:
  │   ├── Resume already in MinIO (resumes/{temp_id}/resume.pdf)
  │   ├── Download + Parse
  │   ├── Chunk text
  │   ├── Generate embeddings
  │   ├── Store in Qdrant (candidates_v1 collection)
  │   └── COMPLETE 7-stage pipeline
  ├── Clear Redis temp data
  └── Return: {candidate_id, status: "ingestion_queued"}
```

### Critical Implementation Details

#### 1. Ingestion.py Two-Mode Support

**New Parameter:**
```python
async def process_job(self, job_data: dict):
    candidate_id = job_data["candidate_id"]
    s3_url = job_data["s3_resume_url"]
    mode = job_data.get("mode", "full")  # NEW: "parse_only" or "full"
```

**Mode Logic:**
```python
if mode == "parse_only":
    # ══════════════════════════════════════════
    # STAGE 1-3 ONLY: Download + Parse + Cache
    # ══════════════════════════════════════════

    # Download resume from MinIO
    resume_bytes = await s3_client.download_file(s3_url)

    # Parse text
    text = parse_resume(resume_bytes, file_type=".pdf")

    # Extract fields
    parsed_data = {
        "full_name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": await extract_skills_from_text(text),
        "years_experience": calculate_experience(text),
        "location": extract_location(text),
        "professional_summary": text[:200]  # First 200 chars
    }

    # Cache in Redis with 1-hour TTL
    await redis_client.set(
        f"parsed_candidate:{candidate_id}",
        json.dumps(parsed_data),
        ex=3600  # 1 hour
    )

    logger.info(f"✅ Parse-only complete for {candidate_id}")
    return  # STOP HERE - no embeddings, no Qdrant

else:  # mode == "full"
    # ══════════════════════════════════════════
    # FULL 7-STAGE PIPELINE (existing code)
    # ══════════════════════════════════════════

    # 1. Fetch candidate from PostgreSQL (must exist now!)
    # 2. Download resume from MinIO
    # 3. Parse resume
    # 4. Extract skills
    # 5. Chunk text
    # 6. Generate embeddings
    # 7. Store in Qdrant

    # ... existing implementation ...
```

**Why This Matters:**
- Parse-only: 2-3 seconds (fast feedback)
- Full pipeline: 10-15 seconds (commit only when ready)
- No orphaned data: Redis auto-expires temp data

#### 2. Candidate API Endpoints (candidates.py)

**Endpoint 1: Anonymous Upload**
```python
@router.post("/upload-resume")
async def upload_resume_anonymous(
    file: UploadFile = File(...),
):
    """
    Stage 1: Anonymous resume upload.

    Returns temp_id + parsed data for form pre-fill.
    No candidate created yet!
    """
    # 1. Generate temp_id
    temp_id = str(uuid.uuid4())

    # 2. Upload to MinIO
    s3_url = await s3_client.upload_file(
        file_bytes=await file.read(),
        file_name=f"resumes/{temp_id}/resume.pdf"
    )

    # 3. Queue parse-only job
    job_data = {
        "job_id": f"parse_{temp_id}",
        "candidate_id": temp_id,
        "s3_resume_url": s3_url,
        "mode": "parse_only"  # CRITICAL!
    }
    await redis_client.lpush("ingestion_queue", json.dumps(job_data))

    # 4. Wait for parsing to complete (poll Redis)
    for _ in range(30):  # 30 seconds max
        cached = await redis_client.get(f"parsed_candidate:{temp_id}")
        if cached:
            return {
                "temp_id": temp_id,
                "parsed_data": json.loads(cached)
            }
        await asyncio.sleep(1)

    raise HTTPException(500, "Parsing timeout")
```

**Endpoint 2: Get Parsed Data**
```python
@router.get("/parsed/{temp_id}")
async def get_parsed_data(temp_id: str):
    """
    Stage 2: Retrieve cached parsed data.

    Frontend uses this to pre-fill form.
    """
    cached = await redis_client.get(f"parsed_candidate:{temp_id}")
    if not cached:
        raise HTTPException(404, "Session expired or invalid temp_id")

    return json.loads(cached)
```

**Endpoint 3: Create Candidate**
```python
@router.post("/")
async def create_candidate(
    request: CandidateCreateRequest,  # Includes temp_id + form data
    db: AsyncSession = Depends(get_db)
):
    """
    Stage 3: Create candidate after form submission.

    CRITICAL: This triggers FULL ingestion!
    """
    # 1. Validate temp_id
    cached = await redis_client.get(f"parsed_candidate:{request.temp_id}")
    if not cached:
        raise HTTPException(400, "Invalid or expired temp_id")

    # 2. Create candidate in PostgreSQL
    candidate = Candidate(
        id=UUID(request.temp_id),  # Reuse temp_id!
        full_name=request.full_name,
        years_experience=request.years_experience,
        professional_summary=request.professional_summary,
        ...
    )
    db.add(candidate)
    await db.commit()

    # 3. Queue FULL ingestion job
    job_data = {
        "job_id": f"ingest_{request.temp_id}",
        "candidate_id": request.temp_id,
        "s3_resume_url": f"resumes/{request.temp_id}/resume.pdf",
        "mode": "full"  # FULL pipeline now!
    }
    await redis_client.lpush("ingestion_queue", json.dumps(job_data))

    # 4. Clear temp data
    await redis_client.delete(f"parsed_candidate:{request.temp_id}")

    return {
        "candidate_id": request.temp_id,
        "status": "ingestion_queued"
    }
```

#### 3. Register Router (main.py)

**Add to main.py (line 46):**
```python
from app.api import webhooks, jobs, admin, candidates  # Add candidates

# Register routes
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(candidates.router, prefix="/api/v1/candidates", tags=["candidates"])  # NEW!
```

### Data Consistency Guarantees

```
┌────────────────────────────────────────────────────────────────┐
│           DATA CONSISTENCY ACROSS DATABASES                     │
└────────────────────────────────────────────────────────────────┘

SCENARIO 1: User uploads resume but abandons form
────────────────────────────────────────────────
  MinIO:      resumes/{temp_id}/resume.pdf ✅ (orphaned)
  Redis:      parsed_candidate:{temp_id} ✅ (expires in 1 hour)
  PostgreSQL: (empty) ✅
  Qdrant:     (empty) ✅

  Result: Orphaned file in MinIO (acceptable, cleanup job can remove)
  Impact: Minimal (1 file vs 1000s of database records)

SCENARIO 2: User completes form and submits
────────────────────────────────────────────
  MinIO:      resumes/{temp_id}/resume.pdf ✅
  Redis:      (deleted) ✅
  PostgreSQL: candidate record ✅
  Qdrant:     embedding vectors ✅

  Result: All databases consistent!

SCENARIO 3: Ingestion fails during full pipeline
─────────────────────────────────────────────────
  PostgreSQL: candidate record ✅ (created first)
  Qdrant:     (partial or empty) ❌

  Solution: Retry logic in ingestion.py (exponential backoff)
  Fallback: Re-index endpoint to trigger re-ingestion
```

---

## 📋 PROMPT 3: JOB EMBEDDINGS OPTIMIZATION

### Objective
Pre-compute job embeddings at job creation time (not during ranking) for 10x faster ranking performance.

### Files Modified
1. `backend/app/api/webhooks.py` - Add job ingestion webhook
2. `backend/app/services/job_embeddings.py` - Refactor to be callable separately
3. `backend/app/services/retrieval.py` - Fetch embeddings instead of creating
4. `backend/app/services/vector_store.py` - Add collection_name parameter
5. `backend/populate_dummy_data.py` - Generate job embeddings
6. `backend/clear_all_data.py` - Clear both collections

### Success Criteria
- ✅ POST `/api/v1/webhooks/job-ingestion` creates job embeddings
- ✅ Job embeddings stored in `jobs_v1` collection
- ✅ retrieval.py fetches pre-computed embeddings (doesn't create)
- ✅ Ranking latency reduced by 50%+
- ✅ Test data includes job embeddings in Qdrant

### Architecture Change

**BEFORE (Slow):**
```
Ranking Request
  ├── Fetch job from PostgreSQL
  ├── Generate job embeddings (sentence-transformers)  ← 500ms delay
  ├── Search Qdrant with embeddings
  └── Return results

Total Time: ~2-3 seconds
```

**AFTER (Fast):**
```
Job Creation/Update
  ├── Webhook triggered
  ├── Generate job embeddings (one-time)  ← 500ms (one-time cost)
  └── Store in jobs_v1 collection

Ranking Request
  ├── Fetch job from PostgreSQL
  ├── Fetch pre-computed embeddings from Qdrant  ← 50ms (10x faster!)
  ├── Search candidates with embeddings
  └── Return results

Total Time: ~1-1.5 seconds (50% faster!)
```

### Data Flow

```
┌────────────────────────────────────────────────────────────────┐
│         JOB EMBEDDINGS AT INGESTION TIME WORKFLOW              │
└────────────────────────────────────────────────────────────────┘

JOB CREATION (Portal Team)
───────────────────────────
1. Portal creates job in PostgreSQL
2. Portal calls webhook: POST /api/v1/webhooks/job-ingestion
   Body: {
     "job_id": "uuid-123",
     "title": "Senior Python Engineer",
     "description": "...",
     "required_skills": ["Python", "AWS", "Docker"],
     ...
   }

3. Webhook handler:
   ├── Generate dual embeddings:
   │   ├── Profile vector: embed(title + description)
   │   └── Skills vector: embed(expanded_skills)
   ├── Store in Qdrant jobs_v1 collection:
   │   ├── Point 1: {vector: profile_vec, payload: {job_id, type: "profile"}}
   │   └── Point 2: {vector: skills_vec, payload: {job_id, type: "skills"}}
   └── Cache in Redis: job_embeddings:{job_id} (1 hour TTL)

4. Return: {status: "embeddings_created"}


RANKING REQUEST (Recruiter)
────────────────────────────
1. POST /api/v1/jobs/{job_id}/rank_full

2. retrieval.py:
   ├── Check Redis cache: job_embeddings:{job_id}
   ├── If not cached, fetch from Qdrant:
   │   query = vector_store.search(
   │       collection_name="jobs_v1",
   │       filter={"job_id": job_id}
   │   )
   │   Extract: profile_vector, skills_vector
   ├── Search candidates using job vectors
   └── Return ranked candidates

Performance: 50ms (vs 500ms before)
```

### Critical Implementation Details

#### 1. Job Ingestion Webhook (webhooks.py)

**New Endpoint:**
```python
@router.post("/job-ingestion")
async def job_ingestion_webhook(
    job_id: str,
    title: str,
    description: str,
    required_skills: List[str],
    must_have_skills: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Webhook called by Portal team when job is created/updated.

    Generates and stores job embeddings immediately.

    Flow:
    1. Expand skills using ontology
    2. Generate dual embeddings (profile + skills)
    3. Store in jobs_v1 Qdrant collection
    4. Cache in Redis
    """
    logger.info(f"📥 Job ingestion webhook triggered for: {title}")

    # 1. Expand skills
    from app.services.ontology import ontology_service
    expanded_skills = []
    for skill in required_skills:
        variants = ontology_service.expand_skill(skill)
        expanded_skills.extend(variants)

    # 2. Generate embeddings
    from app.services.embeddings import embedding_service
    from app.services.job_embeddings import generate_job_embeddings

    embeddings = await generate_job_embeddings(
        job_id=job_id,
        title=title,
        description=description,
        required_skills=expanded_skills
    )

    # 3. Store in Qdrant jobs_v1 collection
    from app.services.vector_store import vector_store
    from qdrant_client.models import PointStruct

    points = [
        PointStruct(
            id=f"{job_id}_profile",
            vector=embeddings["profile_vector"],
            payload={
                "job_id": job_id,
                "type": "profile",
                "title": title,
                "created_at": datetime.utcnow().isoformat()
            }
        ),
        PointStruct(
            id=f"{job_id}_skills",
            vector=embeddings["skills_vector"],
            payload={
                "job_id": job_id,
                "type": "skills",
                "skills": expanded_skills,
                "created_at": datetime.utcnow().isoformat()
            }
        )
    ]

    vector_store.upsert_points(
        points=points,
        collection_name="jobs_v1"  # Separate collection!
    )

    # 4. Cache in Redis
    await redis_client.set(
        f"job_embeddings:{job_id}",
        json.dumps(embeddings),
        ex=3600  # 1 hour TTL
    )

    logger.info(f"✅ Job embeddings created and stored for {job_id}")

    return {
        "status": "success",
        "job_id": job_id,
        "embeddings_created": True,
        "cached": True
    }
```

#### 2. Job Embeddings Service (job_embeddings.py)

**Refactor to Standalone Function:**
```python
async def generate_job_embeddings(
    job_id: str,
    title: str,
    description: str,
    required_skills: List[str]
) -> Dict[str, Any]:
    """
    Generate dual job embeddings (profile + skills).

    This is now a standalone function that can be called:
    - During job creation (webhook)
    - During ranking (if cache miss)

    Returns:
        {
            "job_id": str,
            "profile_vector": List[float],  # 384-dim
            "skills_vector": List[float],   # 384-dim
            "profile_text": str,
            "skills_text": str
        }
    """
    from app.services.embeddings import embedding_service

    # 1. Create profile text
    profile_text = f"{title}\n\n{description}"

    # 2. Create skills text
    skills_text = " ".join(required_skills)

    # 3. Generate embeddings
    profile_vector = await embedding_service.embed_text(profile_text)
    skills_vector = await embedding_service.embed_text(skills_text)

    return {
        "job_id": job_id,
        "profile_vector": profile_vector,
        "skills_vector": skills_vector,
        "profile_text": profile_text,
        "skills_text": skills_text
    }
```

#### 3. Retrieval Service Changes (retrieval.py)

**BEFORE (Creates Embeddings):**
```python
async def retrieve_candidates(self, job_data, candidate_ids, top_k):
    # Generate job embeddings on-the-fly
    embeddings = await generate_job_embeddings(job_data)  # SLOW!
    # ... search
```

**AFTER (Fetches Embeddings):**
```python
async def retrieve_candidates(self, job_data, candidate_ids, top_k):
    job_id = job_data["id"]

    # 1. Check Redis cache
    cached = await redis_client.get(f"job_embeddings:{job_id}")
    if cached:
        embeddings = json.loads(cached)
        logger.info(f"✅ Using cached job embeddings for {job_id}")
    else:
        # 2. Fetch from Qdrant jobs_v1 collection
        from app.services.vector_store import vector_store

        results = vector_store.client.scroll(
            collection_name="jobs_v1",
            scroll_filter={
                "must": [
                    {"key": "job_id", "match": {"value": job_id}}
                ]
            },
            limit=10
        )

        # Extract vectors
        profile_vector = None
        skills_vector = None

        for point in results[0]:
            if point.payload["type"] == "profile":
                profile_vector = point.vector
            elif point.payload["type"] == "skills":
                skills_vector = point.vector

        if not profile_vector or not skills_vector:
            raise ValueError(f"Job embeddings not found for {job_id}. Run job ingestion webhook first!")

        embeddings = {
            "profile_vector": profile_vector,
            "skills_vector": skills_vector
        }

        # Cache for future requests
        await redis_client.set(
            f"job_embeddings:{job_id}",
            json.dumps(embeddings),
            ex=3600
        )

        logger.info(f"✅ Fetched job embeddings from Qdrant for {job_id}")

    # 3. Search candidates (existing logic)
    # ... rest of retrieval
```

#### 4. Vector Store Collection Support (vector_store.py)

**Add collection_name Parameter:**
```python
def upsert_points(
    self,
    points: List[PointStruct],
    collection_name: Optional[str] = None  # NEW PARAMETER
):
    """
    Upsert points to Qdrant collection.

    Args:
        points: List of PointStruct objects
        collection_name: Collection name (defaults to self.collection_name)
    """
    target_collection = collection_name or self.collection_name

    self.client.upsert(
        collection_name=target_collection,
        points=points
    )

    logger.info(f"✅ Upserted {len(points)} points to {target_collection}")
```

**Initialize Both Collections on Startup:**
```python
def initialize_collections(self):
    """Initialize both candidates_v1 and jobs_v1 collections."""
    # Candidates collection
    self.create_collection(
        vector_size=384,
        collection_name="candidates_v1"
    )

    # Jobs collection
    self.create_collection(
        vector_size=384,
        collection_name="jobs_v1"
    )

    logger.info("✅ Both collections initialized")
```

---

## 🧪 TESTING STRATEGY

### Unit Tests (pytest)
```python
# test_application_tracking.py
async def test_create_application():
    """Test application creation."""
    # Create job and candidate
    # Apply to job
    # Verify application exists
    # Verify duplicate returns 409

async def test_ranking_filters_by_applications():
    """Test ranking only searches applicants."""
    # Create 100 candidates
    # 10 apply to job
    # Trigger ranking
    # Verify only 10 are searched

# test_resume_upload.py
async def test_parse_only_mode():
    """Test parse-only ingestion."""
    # Upload resume with mode="parse_only"
    # Verify Redis cache populated
    # Verify PostgreSQL empty
    # Verify Qdrant empty

async def test_full_ingestion_after_form():
    """Test full ingestion after form submit."""
    # Upload resume (parse-only)
    # Submit form
    # Verify PostgreSQL populated
    # Verify Qdrant populated
    # Verify Redis cache cleared

# test_job_embeddings.py
async def test_job_ingestion_webhook():
    """Test job embedding creation."""
    # Call webhook with job data
    # Verify embeddings in jobs_v1 collection
    # Verify Redis cache

async def test_retrieval_uses_cached_embeddings():
    """Test retrieval fetches pre-computed embeddings."""
    # Create job embeddings
    # Trigger ranking
    # Verify no new embeddings generated
```

### Integration Tests (E2E)
```python
# test_complete_workflow.py
async def test_end_to_end_workflow():
    """Test complete workflow from upload to ranking."""
    # 1. Upload resume (parse-only)
    # 2. Verify form pre-fill data
    # 3. Submit form
    # 4. Wait for ingestion
    # 5. Create job with embeddings
    # 6. Candidate applies to job
    # 7. Trigger ranking
    # 8. Verify candidate appears in results
```

### Performance Benchmarks
```python
# test_performance.py
async def test_ranking_performance():
    """Benchmark ranking latency."""
    # Before optimization: ~2-3 seconds
    # After optimization: ~1-1.5 seconds
    # Target: 50% improvement
```

---

## 📊 VALIDATION CHECKLIST

### Day 1 End Validation
- [ ] Application model imports successfully
- [ ] POST `/api/v1/jobs/{job_id}/apply` works
- [ ] Ranking filters by applications (check logs)
- [ ] Duplicate applications return 409
- [ ] Test data includes applications
- [ ] Resume upload returns parsed data
- [ ] Form pre-fill endpoint works
- [ ] Candidate creation triggers full ingestion
- [ ] No orphaned data in PostgreSQL/Qdrant

### Day 2 End Validation
- [ ] Job webhook creates embeddings
- [ ] Embeddings stored in jobs_v1 collection
- [ ] Retrieval fetches (not creates) embeddings
- [ ] Ranking latency improved by 50%+
- [ ] Both collections (candidates_v1, jobs_v1) exist
- [ ] Clear script removes both collections
- [ ] Populate script creates job embeddings
- [ ] All tests pass

---

## 🚨 CRITICAL GOTCHAS & DEBUGGING TIPS

### Common Errors

**1. "Application table not found"**
```bash
# Solution: Run schema migration
psql -U right_staff -d rightstaff -f database/scripts/01_schema.sql
```

**2. "Enum type application_status_enum does not exist"**
```python
# Solution: Verify enum in Python matches database
# Database: application_status_enum (underscore)
# Python: ApplicationStatus (camel case)
# SQLAlchemy: SQLEnum(..., name="application_status_enum")
```

**3. "No job embeddings found in Qdrant"**
```python
# Solution: Run job ingestion webhook first
# Or populate dummy data with job embeddings
python backend/populate_dummy_data.py
```

**4. "Ranking returns 0 results"**
```python
# Debug steps:
# 1. Check if applications exist: SELECT * FROM rightstaff.application;
# 2. Check if candidates have skills: SELECT * FROM rightstaff.candidate_skill;
# 3. Check SQL gate logs (logger.info messages)
```

**5. "Redis connection refused"**
```bash
# Solution: Start Redis via Docker
cd docker && docker-compose up -d redis
```

### Performance Monitoring

```python
# Add timing logs in ranking.py
start_time = time.time()
eligible_ids = await apply_combined_sql_gates(...)
logger.info(f"⏱️  SQL gating took {time.time() - start_time:.2f}s")

start_time = time.time()
retrieval_results = await dense_retriever.retrieve_candidates(...)
logger.info(f"⏱️  Dense retrieval took {time.time() - start_time:.2f}s")
```

**Target Latencies:**
- SQL gating: < 100ms
- Dense retrieval: < 500ms (with pre-computed job embeddings)
- Structured scoring: < 200ms
- Total ranking: < 1.5s

---

## 📈 SUCCESS METRICS

### Functional Metrics
- ✅ 100% of rankings search only applicants (correctness)
- ✅ 0 duplicate applications allowed (data integrity)
- ✅ 0 orphaned candidate records (consistency)
- ✅ 100% of job embeddings pre-computed (optimization)

### Performance Metrics
- 🎯 Ranking latency: < 1.5s (50% improvement)
- 🎯 Parse-only mode: < 3s (fast feedback)
- 🎯 Full ingestion: < 15s (acceptable for background)
- 🎯 Job embedding creation: < 1s (one-time cost)

### Code Quality Metrics
- ✅ All functions have type hints
- ✅ All functions have docstrings
- ✅ All database queries use async/await
- ✅ All errors have proper HTTP status codes
- ✅ All logs use structured format with emojis

---

## 🎯 IMPLEMENTATION TIMELINE

### Day 1 (8 hours)
```
Morning (4 hours) - PROMPT 1
├── 09:00-10:00: Application model + relationships
├── 10:00-11:30: Apply endpoint + error handling
├── 11:30-12:30: Ranking pipeline changes
└── 12:30-13:00: Testing + validation

Afternoon (4 hours) - PROMPT 2
├── 14:00-15:00: Candidates API (3 endpoints)
├── 15:00-16:30: Ingestion.py two-mode support
├── 16:30-17:30: Field extraction helpers
└── 17:30-18:00: Integration testing
```

### Day 2 (6 hours)
```
Morning (4 hours) - PROMPT 3
├── 09:00-10:00: Job webhook + embeddings
├── 10:00-11:00: Retrieval.py optimization
├── 11:00-12:00: Collection separation
└── 12:00-13:00: Testing + benchmarking

Afternoon (2 hours) - FINAL VALIDATION
├── 14:00-15:00: End-to-end testing
├── 15:00-15:30: Performance benchmarks
└── 15:30-16:00: Documentation updates
```

---

## 📝 NEXT STEPS

1. **Review this plan** - Ensure you understand every section
2. **Set up testing environment** - Clear databases, verify services running
3. **Start with Prompt 1** - Application tracking is foundation
4. **Ask questions** - Clarify anything unclear before coding
5. **Test incrementally** - Validate after each prompt

---

## 🎓 LEARNING OBJECTIVES

By the end of this implementation, you will have mastered:

1. **Database Design** - Foreign keys, cascades, unique constraints
2. **API Design** - RESTful endpoints, error handling, status codes
3. **Async Python** - SQLAlchemy async, background workers
4. **Vector Databases** - Qdrant collections, metadata filtering
5. **Caching Strategies** - Redis TTL, cache invalidation
6. **Performance Optimization** - Pre-computation, index usage
7. **Data Consistency** - Transactional integrity across databases
8. **Production Engineering** - Logging, monitoring, error handling

---

**Document Version:** 1.0
**Last Updated:** 2025-11-16
**Author:** Senior Engineering Mentor
**Status:** Ready for Implementation

**Ready to start?** Let's build this! 🚀
