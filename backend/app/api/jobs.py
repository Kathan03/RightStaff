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
from sqlalchemy import select

from app.database import get_db
from app.models.candidate import Job, JobStatus
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


@router.post("/rank")
async def rank_candidates(
    request: RankingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger candidate ranking for a job.
    
    Day 3: SQL gating only (must-have skills, years, location)
    Days 5-8: Will add vector search + semantic ranking
    
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
        
        logger.info(f"🎯 Ranking candidates for job: {job.title}")
        
        # Apply SQL gating
        qualified_candidate_ids = await apply_combined_sql_gates(
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


# ========================================
# NEW DAY 4: Complete Ranking Pipeline
# ========================================

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


@router.post("/{job_id}/rank_full", response_model=RankingResponse)
async def rank_candidates_full(
    job_id: str,
    request: FullRankingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate complete ranked candidate list for a job (Day 4).

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
