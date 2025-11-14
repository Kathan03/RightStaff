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
