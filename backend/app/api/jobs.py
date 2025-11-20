"""
Job ranking endpoints - implements SQL gating (Day 3).
Vector search will be added in Days 5-8.

DAY 3: SQL gating only
FUTURE: Full semantic ranking pipeline
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional
import logging
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models.candidate import Job, JobStatus, Application, ApplicationStatus, Candidate
from app.services.sql_filter import apply_combined_sql_gates
from app.services.redis_client import redis_client

from decimal import Decimal
import json
from fastapi.encoders import jsonable_encoder

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Convert to float
        return super().default(obj)



logger = logging.getLogger(__name__)

router = APIRouter()


class RankingRequest(BaseModel):
    """Request for candidate ranking."""
    job_id: str
    use_cache: bool = True


class JobCreateRequest(BaseModel):
    """Request to create a job (for testing)."""
    title: str
    description: str
    required_skills: List[str]
    must_have_skills: List[str] = []
    min_years_experience: Optional[float] = None
    max_years_experience: Optional[float] = None
    location: Optional[str] = None


class ApplyToJobRequest(BaseModel):
    """Request body for applying to a job."""
    candidate_id: str


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_job(
    request: JobCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new job posting (for testing).
    
    Args:
        request: Job creation data
        db: Database session
    
    Returns:
        Created job metadata
    """
    job = Job(
        title=request.title,
        description=request.description,
        required_skills_json=request.required_skills,
        must_have_skills_json=request.must_have_skills,
        min_years_experience=request.min_years_experience,
        max_years_experience=request.max_years_experience,
        location=request.location,
        status=JobStatus.open
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    logger.info(f"✅ Created job: {job.title} (ID: {job.id})")
    
    return {
        "job_id": str(job.id),
        "title": job.title,
        "status": "created"
    }


@router.get("/")
async def get_all_jobs(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all jobs from the database.

    Returns:
        List of all jobs with their details
    """
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc())
    )
    jobs = result.scalars().all()

    return [
        {
            "id": str(job.id),
            "title": job.title,
            "description": job.description,
            "required_skills": job.required_skills_json or [],
            "must_have_skills": job.must_have_skills_json or [],
            "min_years_experience": float(job.min_years_experience) if job.min_years_experience else None,
            "max_years_experience": float(job.max_years_experience) if job.max_years_experience else None,
            "location": job.location,
            "status": job.status.value if job.status else "open",
            "created_at": job.created_at.isoformat() if job.created_at else None
        }
        for job in jobs
    ]


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific job by ID.

    Args:
        job_id: UUID of the job
        db: Database session

    Returns:
        Job details
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "id": str(job.id),
        "title": job.title,
        "description": job.description,
        "required_skills": job.required_skills_json or [],
        "must_have_skills": job.must_have_skills_json or [],
        "min_years_experience": float(job.min_years_experience) if job.min_years_experience else None,
        "max_years_experience": float(job.max_years_experience) if job.max_years_experience else None,
        "location": job.location,
        "status": job.status.value if job.status else "open",
        "created_at": job.created_at.isoformat() if job.created_at else None
    }


@router.post("/{job_id}/apply", status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    job_id: str,
    request: ApplyToJobRequest,
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
        candidate_id = request.candidate_id
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


@router.get("/{job_id}/applicants")
async def get_job_applicants(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all candidates who have applied to a specific job.

    Args:
        job_id: UUID of the job
        db: Database session

    Returns:
        List of applicants with their details
    """
    try:
        # Verify job exists
        job_result = await db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = job_result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Get all applications for this job with candidate details
        from app.models.candidate import CandidateContact

        applications_result = await db.execute(
            select(Application, Candidate)
            .join(Candidate, Application.candidate_id == Candidate.id)
            .where(Application.job_id == job_id)
            .order_by(Application.applied_at.desc())
        )

        applicants = []
        for application, candidate in applications_result.all():
            # Get contact info
            contact_result = await db.execute(
                select(CandidateContact).where(CandidateContact.candidate_id == candidate.id)
            )
            contact = contact_result.scalar_one_or_none()

            applicants.append({
                "application_id": str(application.id),
                "candidate_id": str(candidate.id),
                "full_name": candidate.full_name,
                "email": contact.email if contact else None,
                "phone": contact.phone if contact else None,
                "location": f"{contact.city}, {contact.region}" if contact and contact.city else None,
                "years_experience": float(candidate.years_experience) if candidate.years_experience else None,
                "professional_summary": candidate.professional_summary,
                "status": application.status.value,
                "applied_at": application.applied_at.isoformat()
            })

        return {
            "job_id": str(job_id),
            "job_title": job.title,
            "total_applicants": len(applicants),
            "applicants": applicants
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting applicants: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get applicants: {str(e)}"
        )


@router.post("/rank") #It just filters by SQL gates no ranking is done.
async def rank_candidates(
    request: RankingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger candidate filtering for a job.
    
    SQL gating only (must-have skills, years, location)
    
    Args:
        request: Ranking request (job_id, use_cache)
        db: Database session
    
    Returns:
        Ranking results with qualified candidate IDs
    """
    try:
        # Fetch job
        result = await db.execute(
            select(Job).where(Job.id == request.job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")
        
        logger.info(f"🎯 SQL filtering only candidates who applied to job: {job.title}")

        # Get candidates who applied to this job
        from app.models.candidate import Application
        application_result = await db.execute(
            select(Application.candidate_id)
            .where(Application.job_id == request.job_id)
        )
        applied_candidate_ids = [str(row[0]) for row in application_result.all()]

        logger.info(f"📋 {len(applied_candidate_ids)} candidates applied to job")

        if not applied_candidate_ids:
            logger.warning(f"⚠️  No applications found for job {request.job_id}")
            return jsonable_encoder({
                "status": "completed",
                "job_id": str(job.id),
                "job_title": job.title,
                "total_qualified": 0,
                "pipeline_stage": "sql_gating_only",
                "note": "No candidates have applied to this job yet"
            })

        # Apply SQL gating ONLY on candidates who applied
        qualified_candidate_ids = await apply_combined_sql_gates(
            application_ids=applied_candidate_ids,  # Filter by applications first!
            must_have_skills=job.must_have_skills_json or [],
            min_years_experience=float(job.min_years_experience) if job.min_years_experience else None,
            max_years_experience=float(job.max_years_experience) if job.max_years_experience else None,
            preferred_location=job.location,
            db=db
        )
        
        # Cache results
        cache_key = f"job_rankings:{request.job_id}"
        ranking_data = {
            "job_id": str(job.id),
            "qualified_candidate_ids": list(qualified_candidate_ids),
            "total_qualified": len(qualified_candidate_ids),
            "computed_at": datetime.utcnow().isoformat(),  # pyright: ignore[reportDeprecated]
            "gates_applied": {
                "must_have_skills": job.must_have_skills_json or [],
                # Convert Decimal to float for JSON serialization
                "min_years": float(job.min_years_experience) if job.min_years_experience is not None else None,
                "max_years": float(job.max_years_experience) if job.max_years_experience is not None else None,
                "location": job.location
            }
        }

        # Use DecimalEncoder as fallback for any remaining Decimal objects
        await redis_client.set(cache_key, json.dumps(ranking_data, cls=DecimalEncoder), ex=3600)
        
        logger.info(f"✅ Ranking complete: {len(qualified_candidate_ids)} qualified candidates")
        
        # return {
        #     "status": "completed",
        #     "job_id": str(job.id),
        #     "job_title": job.title,
        #     "total_qualified": len(qualified_candidate_ids),
        #     "pipeline_stage": "sql_gating_only",
        #     "note": "Full semantic ranking will be added in Days 5-8"
        # }
        return jsonable_encoder({
            "status": "completed",
            "job_id": str(job.id),
            "job_title": job.title,
            "total_qualified": len(qualified_candidate_ids),
            "pipeline_stage": "sql_gating_only", 
            "note": "Full semantic ranking will be added in Days 5-8"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ranking candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/rankings")
async def get_job_rankings(
    job_id: str,
    top_k: int = 20
):
    """
    Get cached rankings for a job.

    Args:
        job_id: Job UUID
        top_k: Number of results to return

    Returns:
        Cached ranking results
    """
    cache_key = f"job_rankings:{job_id}"
    cached_data = await redis_client.get(cache_key)

    if not cached_data:
        return {
            "job_id": job_id,
            "status": "not_found",
            "message": "No rankings found. Trigger ranking first via POST /jobs/rank"
        }

    ranking_data = json.loads(cached_data)
    qualified_ids = ranking_data["qualified_candidate_ids"][:top_k]

    return {
        "job_id": job_id,
        "status": "found",
        "total_qualified": ranking_data["total_qualified"],
        "returned_count": len(qualified_ids),
        "candidate_ids": qualified_ids,
        "computed_at": ranking_data["computed_at"],
        "gates_applied": ranking_data["gates_applied"]
    }


from app.services.ranking import ranking_service
from pydantic import UUID4


class RankedCandidateResponse(BaseModel):
    """Response for a single ranked candidate."""
    candidate_id: str
    final_score: float
    band: str
    confidence: float
    summary: str
    reasons: List[str]
    evidence_snippets: List[dict]
    score_breakdown: dict


class RankingResponse(BaseModel):
    """Complete ranking response."""
    job_id: str
    ranked_candidates: List[RankedCandidateResponse]
    metadata: dict


class FullRankingRequest(BaseModel):
    """Request for full ranking with all pipeline stages."""
    use_cache: bool = True


@router.post("/{job_id}/rank_full", response_model=RankingResponse) #Actually ranks the candidtaes
async def rank_candidates_full(
    job_id: str,
    request: FullRankingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate complete ranked candidate list for a job.

    This is the main ranking endpoint that:
    1. Applies SQL gates (hard filters)
    2. Performs semantic search (dense retrieval)
    3. Calculates structured scores
    4. Blends scores and bands candidates
    5. Generates explanations
    6. Returns ranked list with evidence

    Cache TTL: 5 minutes
    """
    try:
        # Call ranking service
        results = await ranking_service.rank_candidates(
            job_id=job_id,
            filters=None,
            use_cache=request.use_cache
        )

        # Convert to response format
        ranked_candidates = [
            RankedCandidateResponse(
                candidate_id=r.candidate_id,
                final_score=r.final_score,
                band=r.band,
                confidence=r.confidence,
                summary=r.summary,
                reasons=r.reasons,
                evidence_snippets=r.evidence_snippets,
                score_breakdown=r.score_breakdown
            )
            for r in results
        ]

        return RankingResponse(
            job_id=job_id,
            ranked_candidates=ranked_candidates,
            metadata={
                'total_candidates': len(results),
                'high_confidence': len([r for r in results if r.band == 'high']),
                'medium_confidence': len([r for r in results if r.band == 'medium']),
                'low_confidence': len([r for r in results if r.band == 'low'])
            }
        )

    except Exception as e:
        logger.error(f"Ranking failed for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ranking failed: {str(e)}"
        )
