"""
Webhook endpoints for receiving candidate profile updates from Portal team.
Flow: Webhook → Validate → Queue in Redis → Return 202 Accepted
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, UUID4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.candidate import Candidate
from app.services.redis_client import redis_client
from app.utils.logging import logger
import json
import uuid

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class WebhookPayload(BaseModel):
    """Webhook payload from Portal team."""
    event_type: str  # "profile_created" | "profile_updated" | "resume_uploaded"
    candidate_id: UUID4
    timestamp: datetime
    s3_resume_url: str
    profile_snapshot: dict

@router.post("/candidate-updated")
async def candidate_updated_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive webhook from Portal team when candidate profile changes.

    Flow:
    1. Validate candidate exists in PostgreSQL
    2. Queue async processing job in Redis
    3. Return immediately (202 Accepted)

    Returns:
        - 202: Job queued successfully
        - 404: Candidate not found
        - 500: Internal error
    """
    try:
        logger.info(f"Received webhook: {payload.event_type} for candidate {payload.candidate_id}")

        # Step 1: Validate candidate exists
        result = await db.execute(
            select(Candidate).where(Candidate.id == payload.candidate_id)
        )
        candidate = result.scalar_one_or_none()

        if not candidate:
            logger.error(f"Candidate {payload.candidate_id} not found in database")
            raise HTTPException(
                status_code=404,
                detail=f"Candidate {payload.candidate_id} not found"
            )

        # Step 2: Create job and queue in Redis
        job_id = f"ingest_{payload.candidate_id}_{datetime.utcnow().timestamp()}"
        job_data = {
            "job_id": job_id,
            "candidate_id": str(payload.candidate_id),
            "event_type": payload.event_type,
            "s3_resume_url": payload.s3_resume_url,
            "timestamp": payload.timestamp.isoformat()
        }

        # Push to Redis queue (LPUSH = add to left/front of list)
        await redis_client.lpush("ingestion_queue", json.dumps(job_data))
        logger.info(f"Queued job {job_id} for candidate {candidate.full_name}")

        # Step 3: Return immediately (don't wait for processing)
        return {
            "status": "accepted",
            "candidate_id": str(payload.candidate_id),
            "processing_job_id": job_id,
            "estimated_completion_seconds": 30
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# Job Ingestion Webhook
# ═══════════════════════════════════════════════════════════════

from typing import List, Optional


class JobIngestionRequest(BaseModel):
    """Request body for job ingestion webhook."""
    job_id: str
    title: str
    description: str
    required_skills: List[str]
    must_have_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None


@router.post("/job-ingestion")
async def job_ingestion_webhook(request: JobIngestionRequest):
    """
    Webhook called by Portal team when job is created/updated.

    WORKFLOW:
    1. Expand skills using ontology
    2. Generate dual embeddings (profile + skills)
    3. Store in jobs_v1 Qdrant collection
    4. Cache in Redis (1 hour TTL)

    CRITICAL: This creates embeddings at JOB CREATION TIME,
    not during ranking. Ranking will fetch these pre-computed embeddings.

    Args:
        request: Job data from Portal

    Returns:
        {
            "status": "success",
            "job_id": str,
            "embeddings_created": bool,
            "cached": bool
        }

    Example:
        POST /api/v1/webhooks/job-ingestion
        Body: {
            "job_id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Senior Python Engineer",
            "description": "We're looking for...",
            "required_skills": ["Python", "AWS", "Docker"],
            "must_have_skills": ["Python"],
            "preferred_skills": ["FastAPI", "PostgreSQL"]
        }

        Response:
        {
            "status": "success",
            "job_id": "123e4567-e89b-12d3-a456-426614174000",
            "embeddings_created": true,
            "cached": true
        }
    """
    try:
        logger.info(f"📥 Job ingestion webhook triggered for: {request.title}")

        # ════════════════════════════════════════════════════════
        # STEP 1: Expand skills using ontology
        # ════════════════════════════════════════════════════════
        from app.services.ontology import expand_skills, normalize_skill

        # Normalize and expand skills
        normalized_skills = []
        for skill in request.required_skills:
            normalized = normalize_skill(skill, use_taxonomy=True)
            if normalized:
                normalized_skills.append(normalized)

        # Expand skills with variants
        expanded_skills = await expand_skills(normalized_skills, use_taxonomy=True)

        # Remove duplicates
        expanded_skills = list(set(expanded_skills))
        logger.info(f"   Expanded {len(request.required_skills)} skills → {len(expanded_skills)}")

        # ════════════════════════════════════════════════════════
        # STEP 2: Generate job embeddings
        # ════════════════════════════════════════════════════════
        from app.services.job_embeddings import generate_job_embeddings

        embeddings = await generate_job_embeddings(
            job_id=request.job_id,
            title=request.title,
            description=request.description,
            required_skills=expanded_skills
        )

        logger.info(f"   Generated embeddings:")
        logger.info(f"     Profile vector: {len(embeddings['profile_vector'])} dims")
        logger.info(f"     Skills vector: {len(embeddings['skills_vector'])} dims")

        # ════════════════════════════════════════════════════════
        # STEP 3: Store in Qdrant jobs_v1 collection
        # ════════════════════════════════════════════════════════
        from app.services.vector_store import vector_store
        from datetime import datetime

        points = [
            {
                "id": f"{request.job_id}_profile",
                "vector": embeddings["profile_vector"],
                "payload": {
                    "job_id": request.job_id,
                    "type": "profile",
                    "title": request.title,
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            {
                "id": f"{request.job_id}_skills",
                "vector": embeddings["skills_vector"],
                "payload": {
                    "job_id": request.job_id,
                    "type": "skills",
                    "skills": expanded_skills,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
        ]

        await vector_store.upsert_points(
            points=points,
            collection_name="jobs_v1"  # Separate collection!
        )

        logger.info(f"   Stored 2 points in jobs_v1 collection")

        # ════════════════════════════════════════════════════════
        # STEP 4: Cache in Redis (1 hour TTL)
        # ════════════════════════════════════════════════════════
        await redis_client.set(
            f"job_embeddings:{request.job_id}",
            json.dumps({
                "profile_vector": embeddings["profile_vector"],
                "skills_vector": embeddings["skills_vector"]
            }),
            ex=3600  # 1 hour TTL
        )

        logger.info(f"✅ Job embeddings created and cached for {request.job_id}")

        # ════════════════════════════════════════════════════════
        # STEP 5: Return response
        # ════════════════════════════════════════════════════════
        return {
            "status": "success",
            "job_id": request.job_id,
            "embeddings_created": True,
            "cached": True,
            "profile_text": embeddings["profile_text"][:100] + "...",
            "skills_count": len(expanded_skills)
        }

    except Exception as e:
        logger.error(f"❌ Error in job_ingestion_webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job embeddings: {str(e)}"
        )
