# 🎯 PROMPT 1: APPLICATION TRACKING SYSTEM

**Estimated Time:** 4-6 hours
**Priority:** 🔴 CRITICAL
**Prerequisites:** PostgreSQL running, schema created (01_schema.sql)

---

## 📋 OBJECTIVE

Implement complete job application tracking so that the ranking system **ONLY** searches candidates who have applied to a specific job.

**Current Problem:**
- Ranking searches ALL 10,000+ candidates in database
- No concept of "who applied to which job"
- Privacy violation + performance nightmare

**After This Prompt:**
- Ranking searches ONLY applicants (~100 candidates per job)
- Application model tracks candidate → job relationships
- API endpoint for candidates to apply
- 100x faster ranking!

---

## 🎯 IMPLEMENTATION CHECKLIST

### Files to Modify
- [ ] `backend/app/models/candidate.py` - Add Application model + relationships
- [ ] `backend/app/api/jobs.py` - Add POST `/jobs/{job_id}/apply` endpoint
- [ ] `backend/app/services/ranking.py` - Filter by applications FIRST (Step 2a)
- [ ] `backend/app/services/sql_filter.py` - Accept `application_ids` parameter
- [ ] `backend/populate_dummy_data.py` - Create sample applications
- [ ] `backend/clear_all_data.py` - Clear applications table

### Success Criteria
- [x] Application model imports without errors
- [x] POST `/api/v1/jobs/{job_id}/apply` creates applications
- [x] Duplicate applications return 409 Conflict
- [x] Ranking pipeline queries applications first
- [x] SQL gates filter by application_ids
- [x] Test data includes applications

---

## 📝 STEP 1: CREATE APPLICATION MODEL

### File: `backend/app/models/candidate.py`

**Location:** Add after the Job class (after line 155)

**Code to Add:**

```python
# ========================================
# Application Model - Job Applications
# ========================================

class ApplicationStatus(str, enum.Enum):
    """
    Application status enumeration.
    Matches database enum: application_status_enum
    """
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
    """
    Job applications - tracks which candidates applied to which jobs.

    BUSINESS RULES:
    - One candidate can apply to a job only ONCE (UNIQUE constraint)
    - Application status tracks hiring pipeline stage
    - Foreign keys CASCADE on delete (delete candidate → delete applications)

    USAGE:
        # Create application
        app = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status=ApplicationStatus.applied
        )

        # Get all applicants for a job
        job.applications  # List[Application]

        # Get all jobs a candidate applied to
        candidate.applications  # List[Application]
    """

    __tablename__ = "application"
    __table_args__ = {"schema": "rightstaff"}

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rightstaff.candidate.id", ondelete="CASCADE"),
        nullable=False
    )
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rightstaff.job.id", ondelete="CASCADE"),
        nullable=False
    )

    # Status tracking
    status = Column(
        SQLEnum(
            ApplicationStatus,
            schema="rightstaff",
            name="application_status_enum"
        ),
        nullable=False,
        default=ApplicationStatus.applied
    )

    # Timestamps
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships (bidirectional)
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
```

**CRITICAL:** Verify imports at top of file:
```python
# Ensure these imports exist (around line 9-14):
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from datetime import datetime
import uuid
import enum
```

---

## 📝 STEP 2: ADD RELATIONSHIPS TO EXISTING MODELS

### File: `backend/app/models/candidate.py`

**Change 1: Candidate Model**
**Location:** Line 35 (after existing relationships)

```python
class Candidate(Base):
    __tablename__ = "candidate"
    __table_args__ = {"schema": "rightstaff"}

    # ... existing fields ...

    # Relationships (for eager loading with joins)
    contact = relationship("CandidateContact", back_populates="candidate", uselist=False)
    resumes = relationship("CandidateResume", back_populates="candidate")
    skills = relationship("CandidateSkill", back_populates="candidate")
    applications = relationship("Application", back_populates="candidate")  # NEW!
```

**Change 2: Job Model**
**Location:** After line 154 (after updated_at field)

```python
class Job(Base):
    __tablename__ = "job"
    __table_args__ = {"schema": "rightstaff"}

    # ... existing fields ...

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    applications = relationship("Application", back_populates="job")  # NEW!
```

---

## 📝 STEP 3: CREATE APPLICATION API ENDPOINT

### File: `backend/app/api/jobs.py`

**Location:** Add after create_job endpoint (after line 93)

**Import Required (add to top of file, line 21):**
```python
from app.models.candidate import Application, ApplicationStatus, Candidate
from sqlalchemy import select, and_
```

**Endpoint Code:**

```python
@router.post("/{job_id}/apply", status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    job_id: str,
    candidate_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit job application for a candidate.

    BUSINESS RULES:
    - Job must be in 'open' status
    - Candidate must exist in database
    - One application per candidate per job (enforced by DB UNIQUE constraint)

    Args:
        job_id: UUID of the job
        candidate_id: UUID of the candidate
        db: Database session (injected)

    Returns:
        {
            "application_id": str,
            "candidate_id": str,
            "job_id": str,
            "status": str,
            "applied_at": str,
            "message": str
        }

    Raises:
        404: Job or candidate not found
        400: Job not open for applications
        409: Candidate already applied (duplicate)
        500: Database error

    Example:
        POST /api/v1/jobs/123e4567-e89b-12d3-a456-426614174000/apply
        Body: {"candidate_id": "987fcdeb-51a2-43f1-b123-456789abcdef"}

        Response (201):
        {
            "application_id": "111e4567-e89b-12d3-a456-426614174000",
            "status": "applied",
            "message": "Application submitted successfully for Senior Python Engineer"
        }
    """
    try:
        # ════════════════════════════════════════════════════════
        # STEP 1: Validate job exists and is open
        # ════════════════════════════════════════════════════════
        job_result = await db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = job_result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        if job.status != JobStatus.open:
            raise HTTPException(
                status_code=400,
                detail=f"Job '{job.title}' is not open for applications (current status: {job.status})"
            )

        # ════════════════════════════════════════════════════════
        # STEP 2: Validate candidate exists
        # ════════════════════════════════════════════════════════
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()

        if not candidate:
            raise HTTPException(
                status_code=404,
                detail=f"Candidate {candidate_id} not found"
            )

        # ════════════════════════════════════════════════════════
        # STEP 3: Check for duplicate application
        # ════════════════════════════════════════════════════════
        existing_result = await db.execute(
            select(Application).where(
                and_(
                    Application.candidate_id == candidate_id,
                    Application.job_id == job_id
                )
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Candidate '{candidate.full_name}' already applied to '{job.title}' "
                    f"(application_id: {existing.id}, status: {existing.status})"
                )
            )

        # ════════════════════════════════════════════════════════
        # STEP 4: Create application
        # ════════════════════════════════════════════════════════
        application = Application(
            candidate_id=candidate_id,
            job_id=job_id,
            status=ApplicationStatus.applied
        )

        db.add(application)
        await db.commit()
        await db.refresh(application)

        logger.info(
            f"✅ Application created: {candidate.full_name} → {job.title} "
            f"(application_id: {application.id})"
        )

        # ════════════════════════════════════════════════════════
        # STEP 5: Return response
        # ════════════════════════════════════════════════════════
        return {
            "application_id": str(application.id),
            "candidate_id": str(candidate_id),
            "job_id": str(job_id),
            "status": application.status.value,
            "applied_at": application.applied_at.isoformat(),
            "message": f"Application submitted successfully for {job.title}"
        }

    except HTTPException:
        # Re-raise HTTP exceptions (4xx errors)
        raise
    except Exception as e:
        # Log unexpected errors and return 500
        logger.error(f"❌ Error creating application: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create application: {str(e)}"
        )
```

---

## 📝 STEP 4: FIX RANKING TO FILTER BY APPLICATIONS

### File: `backend/app/services/ranking.py`

**Location:** Lines 92-101 (inside `rank_candidates` method)

**FIND THIS CODE:**
```python
# Step 2: SQL gating
eligible_candidate_ids = await apply_combined_sql_gates(
    must_have_skills=job_data.get('must_have_skills_json', []),
    min_years_experience=job_data.get('min_years_experience'),
    max_years_experience=job_data.get('max_years_experience'),
    preferred_location=job_data.get('location')
)
logger.info(f"📊 {len(eligible_candidate_ids)} candidates passed SQL gates")
```

**REPLACE WITH:**
```python
# ════════════════════════════════════════════════════════════════
# Step 2a: Get candidates who applied to this job
# ════════════════════════════════════════════════════════════════
from app.models.candidate import Application
from app.database import AsyncSessionLocal

async with AsyncSessionLocal() as db:
    application_result = await db.execute(
        select(Application.candidate_id)
        .where(Application.job_id == job_id)
    )
    applied_candidate_ids = [str(row[0]) for row in application_result.all()]

# Early exit if no applications
if not applied_candidate_ids:
    logger.warning(f"⚠️  No applications found for job {job_id}")
    return []

logger.info(f"📋 {len(applied_candidate_ids)} candidates applied to job {job_id}")

# ════════════════════════════════════════════════════════════════
# Step 2b: Apply SQL gates ONLY on candidates who applied
# ════════════════════════════════════════════════════════════════
eligible_candidate_ids = await apply_combined_sql_gates(
    application_ids=applied_candidate_ids,  # NEW: Filter by applications first!
    must_have_skills=job_data.get('must_have_skills_json', []),
    min_years_experience=job_data.get('min_years_experience'),
    max_years_experience=job_data.get('max_years_experience'),
    preferred_location=job_data.get('location')
)
logger.info(f"📊 {len(eligible_candidate_ids)} applicants passed SQL gates")
```

**Add imports at top of file (around line 10):**
```python
from sqlalchemy import select
```

---

## 📝 STEP 5: UPDATE SQL FILTER TO ACCEPT application_ids

### File: `backend/app/services/sql_filter.py`

**Change 1: Update filter_candidates_by_must_have_skills signature (line 30)**

**FIND:**
```python
async def filter_candidates_by_must_have_skills(
    must_have_skills: List[str],
    db: Optional[AsyncSession] = None
) -> Set[str]:
```

**REPLACE WITH:**
```python
async def filter_candidates_by_must_have_skills(
    must_have_skills: List[str],
    application_ids: Optional[List[str]] = None,  # NEW PARAMETER
    db: Optional[AsyncSession] = None
) -> Set[str]:
```

**Change 2: Update docstring (line 34)**

**ADD THIS TO DOCSTRING:**
```python
"""
Filter candidates who have ALL must-have skills (AND logic).

This is the ONTOLOGY GATE - critical for ranking quality.

PERFORMANCE OPTIMIZATION:
If application_ids provided, filter by them FIRST to reduce search space.
Example: 100 applicants vs 10,000 candidates = 100x faster query.

Args:
    must_have_skills: List of required skill names (e.g., ["Python", "AWS"])
    application_ids: Optional list of candidate UUIDs to filter by (NEW!)
    db: Optional database session (creates new if not provided)

Returns:
    Set of candidate UUIDs (as strings) who pass the gate
"""
```

**Change 3: Update query logic (after line 74)**

**FIND:**
```python
query = (
    select(CandidateSkill.candidate_id)
    .join(Skill, CandidateSkill.skill_id == Skill.id)
    .where(Skill.name.in_(must_have_skills))
    .group_by(CandidateSkill.candidate_id)
    .having(func.count(func.distinct(CandidateSkill.skill_id)) == len(must_have_skills))
)
```

**REPLACE WITH:**
```python
# Build query
query = (
    select(CandidateSkill.candidate_id)
    .join(Skill, CandidateSkill.skill_id == Skill.id)
    .where(Skill.name.in_(must_have_skills))
)

# PERFORMANCE OPTIMIZATION: Filter by application_ids FIRST
if application_ids:
    from uuid import UUID
    # Convert string UUIDs to UUID objects for SQL query
    uuid_list = [UUID(app_id) for app_id in application_ids]
    query = query.where(CandidateSkill.candidate_id.in_(uuid_list))
    logger.info(f"  → Filtering by {len(application_ids)} application IDs")

# Apply skill matching logic
query = query.group_by(CandidateSkill.candidate_id).having(
    func.count(func.distinct(CandidateSkill.skill_id)) == len(must_have_skills)
)
```

**Change 4: Update apply_combined_sql_gates signature (line 198)**

**FIND:**
```python
async def apply_combined_sql_gates(
    must_have_skills: Optional[List[str]] = None,
    min_years_experience: Optional[float] = None,
    max_years_experience: Optional[float] = None,
    preferred_location: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> Set[str]:
```

**REPLACE WITH:**
```python
async def apply_combined_sql_gates(
    application_ids: Optional[List[str]] = None,  # NEW: Add as FIRST parameter
    must_have_skills: Optional[List[str]] = None,
    min_years_experience: Optional[float] = None,
    max_years_experience: Optional[float] = None,
    preferred_location: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> Set[str]:
```

**Change 5: Handle empty application_ids (add at start of function, line 237)**

**ADD THIS CODE:**
```python
# CRITICAL: If application_ids provided but empty, return empty set
if application_ids is not None and not application_ids:
    logger.info("⚠️  Empty application_ids list - returning empty set")
    return set()

if application_ids:
    logger.info(f"🔍 Starting SQL gates for {len(application_ids)} applicants")
```

**Change 6: Pass application_ids to filter functions (line 242)**

**FIND:**
```python
# Gate 1: Must-have skills
if must_have_skills:
    skills_set = await filter_candidates_by_must_have_skills(must_have_skills, db)
```

**REPLACE WITH:**
```python
# Gate 1: Must-have skills
if must_have_skills:
    skills_set = await filter_candidates_by_must_have_skills(
        must_have_skills,
        application_ids=application_ids,  # NEW!
        db=db
    )
```

---

## 📝 STEP 6: UPDATE TEST DATA GENERATOR

### File: `backend/populate_dummy_data.py`

**Location:** After candidate and job creation (search for "Create jobs" section)

**Add this code block:**

```python
print("\n" + "="*60)
print("CREATING JOB APPLICATIONS")
print("="*60)

# Import Application model
from app.models.candidate import Application, ApplicationStatus

# Get first 3 jobs and first 10 candidates for demo
jobs_result = await session.execute(select(Job).limit(3))
jobs = jobs_result.scalars().all()

candidates_result = await session.execute(select(Candidate).limit(10))
candidates = candidates_result.scalars().all()

if not jobs:
    print("⚠️  No jobs found - skipping application creation")
elif not candidates:
    print("⚠️  No candidates found - skipping application creation")
else:
    applications_created = 0

    # Create applications: first 10 candidates apply to first 3 jobs
    for job in jobs:
        for candidate in candidates:
            try:
                # Create application
                application = Application(
                    candidate_id=candidate.id,
                    job_id=job.id,
                    status=ApplicationStatus.applied
                )
                session.add(application)
                applications_created += 1
            except Exception as e:
                print(f"⚠️  Failed to create application: {e}")
                continue

    await session.commit()
    print(f"✅ Created {applications_created} applications")
    print(f"   Jobs: {len(jobs)}")
    print(f"   Candidates: {len(candidates)}")
    print(f"   Applications per job: ~{applications_created // len(jobs)}")
```

**Add import at top of file:**
```python
from app.models.candidate import Application, ApplicationStatus
```

---

## 📝 STEP 7: UPDATE DATA CLEANUP SCRIPT

### File: `backend/clear_all_data.py`

**Location:** BEFORE deleting candidates or jobs (find DELETE FROM statements)

**Add this code FIRST:**

```python
print("\n" + "="*60)
print("CLEARING APPLICATIONS")
print("="*60)

try:
    # Delete applications FIRST (foreign key dependencies)
    await session.execute(text("DELETE FROM rightstaff.application"))
    await session.commit()
    print("✅ Applications table cleared")
except Exception as e:
    print(f"⚠️  Error clearing applications: {e}")
    await session.rollback()
```

**WHY DELETE APPLICATIONS FIRST?**
- Applications have foreign keys to candidates and jobs
- PostgreSQL requires child records deleted before parents
- CASCADE works on DELETE candidate, but explicit clear is safer

---

## 🧪 VALIDATION & TESTING

### Step 1: Verify Model Import

```bash
cd /home/user/RightStaff/backend
python -c "from app.models.candidate import Application, ApplicationStatus; print('✅ Models import successfully')"
```

**Expected Output:**
```
✅ Models import successfully
```

### Step 2: Verify Database Schema

```bash
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='rightstaff' AND table_name='application'
ORDER BY ordinal_position;
"
```

**Expected Output:**
```
 column_name  |           data_type            | is_nullable
--------------+--------------------------------+-------------
 id           | uuid                           | NO
 candidate_id | uuid                           | NO
 job_id       | uuid                           | NO
 status       | USER-DEFINED                   | NO
 applied_at   | timestamp with time zone       | NO
 updated_at   | timestamp with time zone       | NO
```

### Step 3: Test API Endpoint

```bash
# Start the server
cd /home/user/RightStaff/backend
uvicorn app.main:app --reload &

# Wait for server to start
sleep 5

# Get a job_id and candidate_id
JOB_ID=$(curl -s http://localhost:8000/api/v1/jobs | jq -r '.[0].id')
CANDIDATE_ID=$(curl -s http://localhost:8000/api/v1/candidates | jq -r '.[0].id')

# Test application creation
curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/apply?candidate_id=${CANDIDATE_ID}" \
  -H "Content-Type: application/json" \
  | jq .

# Expected: 201 Created with application_id
```

### Step 4: Test Duplicate Application (Should Fail)

```bash
# Try to apply again (should return 409 Conflict)
curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/apply?candidate_id=${CANDIDATE_ID}" \
  -H "Content-Type: application/json" \
  | jq .

# Expected: 409 Conflict with error message
```

### Step 5: Test Ranking Pipeline

```bash
# Trigger ranking
curl -X POST "http://localhost:8000/api/v1/jobs/${JOB_ID}/rank_full" \
  -H "Content-Type: application/json" \
  -d '{"use_cache": false}' \
  | jq .

# Check logs - should see:
# "📋 N candidates applied to job {job_id}"
# "📊 M applicants passed SQL gates"
```

---

## 🚨 TROUBLESHOOTING

### Error: "Table application does not exist"

**Solution:**
```bash
# Re-run schema script
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -f /docker-entrypoint-initdb.d/01_schema.sql
```

### Error: "Enum type application_status_enum does not exist"

**Check database:**
```bash
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT typname FROM pg_type WHERE typname LIKE '%application%';
"
```

**Should show:**
```
 typname
-------------------------
 application_status_enum
```

### Error: "No applications found" (but you created them)

**Check database:**
```bash
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "
SELECT COUNT(*) FROM rightstaff.application;
"
```

**If 0, run populate script:**
```bash
python backend/populate_dummy_data.py
```

### Error: "Ranking returns 0 results"

**Debug checklist:**
1. Check applications exist: `SELECT * FROM rightstaff.application;`
2. Check candidates have skills: `SELECT * FROM rightstaff.candidate_skill;`
3. Check SQL gate logs (look for emoji markers in terminal)
4. Verify must_have_skills match actual skills in database

---

## ✅ SUCCESS CRITERIA CHECKLIST

After completing this prompt, verify:

- [ ] Application model exists: `from app.models.candidate import Application` works
- [ ] Relationships work: `job.applications` returns list
- [ ] API endpoint works: POST `/api/v1/jobs/{id}/apply` returns 201
- [ ] Duplicate check works: Second application returns 409
- [ ] Ranking filters by applications: Check logs for "📋 N candidates applied"
- [ ] SQL gates receive application_ids: Check logs for "Filtering by N application IDs"
- [ ] Test data includes applications: `SELECT COUNT(*) FROM application` > 0
- [ ] Clear script works: Deletes applications without foreign key errors

---

## 🎯 PERFORMANCE VALIDATION

**Before (searches ALL candidates):**
```sql
-- Query searches entire candidate_skill table
SELECT candidate_id FROM rightstaff.candidate_skill
JOIN rightstaff.skill ON ...
WHERE skill.name IN ('Python', 'AWS')
GROUP BY candidate_id
HAVING COUNT(*) = 2;
-- Returns: 500 candidates (from 10,000 total)
-- Time: ~200ms
```

**After (searches ONLY applicants):**
```sql
-- Query filtered by application_ids first
SELECT candidate_id FROM rightstaff.candidate_skill
JOIN rightstaff.skill ON ...
WHERE skill.name IN ('Python', 'AWS')
  AND candidate_id IN (uuid1, uuid2, ..., uuid100)  -- Only 100 applicants!
GROUP BY candidate_id
HAVING COUNT(*) = 2;
-- Returns: 20 candidates (from 100 applicants)
-- Time: ~20ms (10x faster!)
```

---

## 📊 WHAT YOU LEARNED

1. **SQLAlchemy Relationships** - Bidirectional relationships with back_populates
2. **Cascade Deletes** - Foreign keys with ON DELETE CASCADE
3. **Unique Constraints** - Database-level enforcement of business rules
4. **Enum Types** - Matching Python enums with PostgreSQL enums
5. **Error Handling** - Proper HTTP status codes (404, 400, 409, 500)
6. **Query Optimization** - Filtering by application_ids first reduces search space
7. **Async/Await** - SQLAlchemy async patterns for FastAPI

---

## 🚀 NEXT STEPS

After completing this prompt:

1. **Run all validation steps** - Ensure everything works
2. **Check server logs** - Look for emoji markers (✅ 📋 📊)
3. **Test with Swagger UI** - http://localhost:8000/docs
4. **Verify database state** - Check application table has records
5. **Ready for Prompt 2** - Resume-first upload workflow

---

**Estimated Completion Time:** 4-6 hours
**Complexity:** Medium
**Impact:** 🔴 CRITICAL (fixes fundamental ranking bug)

**Ready? Let's implement!** 🚀
