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
from app.services.redis_client import redis_client
from app.services.s3_client import s3_client
from app.utils.logging import logger
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

        # Determine content type based on file extension
        content_type_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain"
        }
        content_type = content_type_map.get(file_ext, "application/octet-stream")

        s3_url = await s3_client.upload_file(
            file_data=file_bytes,
            object_name=f"resumes/{temp_id}/resume{file_ext}",
            content_type=content_type
        )

        logger.info(f"📤 Resume uploaded to MinIO: {s3_url} (temp_id: {temp_id})")

        # ════════════════════════════════════════════════════════
        # STEP 3: Queue parse-only ingestion job
        # ════════════════════════════════════════════════════════
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
            professional_summary=request.professional_summary
        )

        db.add(candidate)
        await db.flush()  # Get candidate.id for foreign keys

        # ════════════════════════════════════════════════════════
        # STEP 3: Create contact record
        # ════════════════════════════════════════════════════════
        if request.email or request.phone or request.location:
            # Parse location if provided (e.g., "Seattle, WA 98101")
            city = None
            region = None
            postal_code = None
            if request.location:
                import re
                # Try to extract city, region, zip
                match = re.match(r"([^,]+),\s*([A-Z]{2})\s*(\d{5})?", request.location)
                if match:
                    city = match.group(1)
                    region = match.group(2)
                    postal_code = match.group(3)
                else:
                    # Just use location as city if parsing fails
                    city = request.location

            contact = CandidateContact(
                candidate_id=candidate.id,
                email=request.email,
                phone=request.phone,
                city=city,
                region=region,
                postal_code=postal_code
            )
            db.add(contact)

        await db.commit()
        await db.refresh(candidate)

        logger.info(f"✅ Candidate created: {request.full_name} ({candidate.id})")

        # ════════════════════════════════════════════════════════
        # STEP 4: Queue FULL ingestion job
        # ════════════════════════════════════════════════════════
        # Get s3_url from parsed_data (stored during parse_only phase)
        s3_url = parsed_data.get("s3_resume_url", f"resumes/{request.temp_id}/resume.pdf")

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
