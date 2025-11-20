"""
Background worker that processes ingestion jobs from Redis queue.
Flow: Poll Redis → Fetch candidate → Download resume → Parse → Extract skills → Store skills in PostgreSQL → Chunk → Embed → Store in Qdrant

DAY 3 ADDITIONS:
- Retry logic with exponential backoff
- Dead Letter Queue for failed jobs after max retries
- Skills extraction from resume text
- Structured metrics collection

DAY 5+ ADDITIONS:
- Store extracted skills in PostgreSQL for SQL gating
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete
from sqlalchemy.orm import selectinload

# NEW: Retry logic imports
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import logging

from app.database import AsyncSessionLocal
from app.models.candidate import Candidate, CandidateContact, CandidateResume
from app.services.redis_client import redis_client
from app.services.s3_client import s3_client
from app.services.parsers import parse_resume, chunk_text
from app.services.embeddings import embedding_service
from app.services.vector_store import vector_store
from app.services.ontology import extract_skills_from_text  # NEW: Day 3
from app.services.metrics import metrics_collector  # NEW: Day 3
from app.utils.logging import logger

# Import S3Error for retry logic
from minio.error import S3Error

# Exceptions that should trigger retry (transient failures)
# These are errors that might succeed on retry (network issues, timeouts, temporary failures)
RETRIABLE_EXCEPTIONS = (
    # Network/connection errors
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    # S3/MinIO errors (file not found, connection issues, temporary unavailability)
    S3Error,
    # Generic exceptions (for unexpected transient failures)
    # Note: ValueError is intentionally excluded (permanent errors like 'candidate not found')
    Exception,
)

class IngestionWorker:
    """Background worker for processing resume ingestion jobs."""
    
    def __init__(self):
        self.running = False
        self.jobs_processed = 0
        self.jobs_failed = 0
    
    async def start(self):
        """Start the background worker loop."""
        self.running = True
        logger.info("🚀 Ingestion worker started - polling Redis queue")
        
        # Initialize Qdrant collection on startup
        # Why here? Ensures collection exists before any ingestion
        try:
            vector_store.create_collection(vector_size=384)
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            # Continue anyway - will retry on first ingestion job
        
        while self.running:
            try:
                # Step 1: Pop job from Redis queue (blocking pop, 5s timeout)
                result = await redis_client.brpop("ingestion_queue", timeout=5)
                
                if result is None:
                    # No jobs in queue, loop again
                    continue
                
                # Step 2: Parse job data
                _, job_data_str = result  # result is (queue_name, data)
                job_data = json.loads(job_data_str)
                
                logger.info(f"📦 Processing job {job_data['job_id']}")
                
                # Step 3: Process the job (with retry logic)
                try:
                    await self.process_job_with_retry(job_data)
                    self.jobs_processed += 1
                    metrics_collector.increment_counter("ingestion_jobs_success")
                except Exception as e:
                    # Job failed after max retries - move to DLQ
                    logger.error(f"❌ Job {job_data['job_id']} failed after max retries: {e}")
                    self.jobs_failed += 1
                    await self._move_to_dlq(job_data, str(e))
                    metrics_collector.increment_counter("ingestion_jobs_failed")
                
            except Exception as e:
                logger.error(f"❌ Worker error: {e}")
                await asyncio.sleep(1)  # Backoff on error
    
    def stop(self):
        """Stop the worker gracefully."""
        self.running = False
        logger.info(f"🛑 Ingestion worker stopped (processed: {self.jobs_processed}, failed: {self.jobs_failed})")
    
    async def process_job_with_retry(self, job_data: dict):
        """
        Process job with retry logic wrapper.
        
        This method wraps process_job() with retry logic.
        Separate method allows us to track retry count and handle final failure.
        
        Args:
            job_data: Job metadata from Redis queue
        
        Raises:
            Exception: If job fails after max retries
        """
        # Initialize retry metadata
        if "retry_count" not in job_data:
            job_data["retry_count"] = 0
        
        try:
            await self._process_job_with_tenacity(job_data)
        except Exception as e:
            # All retries exhausted
            logger.error(f"Job {job_data['job_id']} exhausted all retries: {e}")
            raise
    
    @retry(
        # Stop after 5 attempts (1 original + 4 retries)
        stop=stop_after_attempt(5),
        # Wait 2^x * 1 seconds between retries (2s, 4s, 8s, 16s)
        wait=wait_exponential(multiplier=1, min=2, max=60),
        # Only retry on specific exceptions (transient failures)
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
        # Log before each sleep
        before_sleep=before_sleep_log(logger, logging.WARNING),
        # Log after each retry
        after=after_log(logger, logging.INFO),
        # Re-raise exception after max attempts
        reraise=True
    )
    async def _process_job_with_tenacity(self, job_data: dict):
        """
        Process job with tenacity retry decorator.
        
        Why separate method?
        - Tenacity decorator needs to wrap a single method
        - Allows clean separation of retry logic from business logic
        - Easier to test and mock
        
        Args:
            job_data: Job metadata
        
        Note: Tenacity tracks its own attempt count, so we don't manually increment
        """
        # Process the job
        await self.process_job(job_data)
    
    async def process_job(self, job_data: dict):
        """
        Process a single ingestion job.

        MODES:
        - parse_only: Extract text and fields only (Stage 1 - Resume Upload)
        - full: Complete 8-stage pipeline with embeddings (Stage 3 - Candidate Creation)

        Pipeline stages (full mode):
        1. Fetch candidate details from PostgreSQL
        2. Download resume from MinIO
        3. Parse resume (extract text)
        4. Extract skills from text
        4.5. Store skills in PostgreSQL (for SQL gating)
        5. Chunk text (split into semantic units)
        6. Generate embeddings (convert to vectors)
        7. Store in Qdrant (save vectors + metadata with skills)

        Error handling:
        - Transient errors → retry with exponential backoff (tenacity)
        - Permanent errors → fail immediately, move to DLQ

        Args:
            job_data: Job metadata from Redis queue
        """
        start_time = datetime.utcnow()
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
                logger.info(f"[parse_only] Downloading resume from {s3_url}")
                resume_bytes = await s3_client.download_file(s3_url)
                logger.info(f"📥 Downloaded resume from {s3_url}")

                # Parse text from resume using Unstructured library
                from app.services.parsers import parse_resume_text

                # Extract file extension from s3_url
                file_ext = s3_url.split('.')[-1] if '.' in s3_url else 'pdf'
                file_type = f".{file_ext}"

                text = await parse_resume_text(resume_bytes, file_type)
                logger.info(f"📄 Parsed resume text ({len(text)} chars)")

                # ══════════════════════════════════════════════════════════════
                # LLM-BASED FIELD EXTRACTION (with regex fallback)
                # ══════════════════════════════════════════════════════════════
                from app.config import settings
                from app.services.skill_extractor import extract_skills

                parsed_data = None
                llm_parsing_attempted = False

                # Try LLM parsing if enabled
                if settings.use_llm_parsing:
                    try:
                        logger.info("🤖 Attempting LLM-based field extraction...")
                        from app.services.llm_parser import get_llm_parser

                        llm_parser = get_llm_parser()
                        llm_result = await llm_parser.parse_resume(text)

                        # ══════════════════════════════════════════════════════════════
                        # SKILL EXTRACTION & NORMALIZATION (Unified Pipeline)
                        # ══════════════════════════════════════════════════════════════
                        # Extract skills using UNIFIED method
                        # Change this ONE line to switch between LLM/spaCy/hybrid
                        normalized_skills = await extract_skills(text, method="hybrid")
                        # Options:
                        #   method="hybrid" - LLM + spaCy (best, default when LLM enabled)
                        #   method="llm"    - LLM only
                        #   method="spacy"  - spaCy only

                        # ══════════════════════════════════════════════════════════════
                        # LOCATION EXTRACTION (consistent format)
                        # ══════════════════════════════════════════════════════════════
                        location_data = llm_result.get("location", {})
                        if isinstance(location_data, dict):
                            # LLM returns dict: {"city": "...", "state": "...", "country": "..."}
                            location_dict = {
                                "city": location_data.get("city"),
                                "region": location_data.get("state"),  # state → region (matches DB schema)
                                "country": location_data.get("country")
                            }
                        else:
                            # Fallback for unexpected format
                            location_dict = {"city": None, "region": None, "country": None}

                        parsed_data = {
                            "full_name": llm_result.get("full_name") or "Unknown",
                            "email": llm_result.get("email"),
                            "phone": llm_result.get("phone"),
                            "skills": normalized_skills,  # Normalized through ontology
                            "years_experience": llm_result.get("years_experience"),
                            "location": location_dict,  # Consistent dict format
                            "professional_summary": llm_result.get("professional_summary") or text[:500],
                            "s3_resume_url": s3_url
                        }

                        llm_parsing_attempted = True
                        logger.info(f"✅ LLM parsing successful")
                        logger.info(f"   Skills: {len(normalized_skills)} (normalized via hybrid method)")
                        logger.info(f"   Location: {location_dict.get('city')}, {location_dict.get('region')}")

                    except Exception as e:
                        logger.warning(f"⚠️  LLM parsing failed, falling back to regex: {e}")
                        llm_parsing_attempted = False

                # Fallback to regex-based extraction if LLM disabled or failed
                if not llm_parsing_attempted or parsed_data is None:
                    logger.info("🔄 Using regex-based field extraction (fallback)")
                    from app.services.parsers import (
                        extract_name,
                        extract_email,
                        extract_phone,
                        extract_location,
                        calculate_years_experience
                    )

                    # ══════════════════════════════════════════════════════════════
                    # SKILL EXTRACTION & NORMALIZATION (Unified Pipeline)
                    # ══════════════════════════════════════════════════════════════
                    # Extract skills using UNIFIED method
                    # Change this ONE line to switch between methods
                    normalized_skills = await extract_skills(text, method="spacy")
                    # Options:
                    #   method="spacy"  - spaCy + patterns (default when LLM disabled)
                    #   method="hybrid" - Would use LLM + spaCy (but LLM is disabled)
                    #   method="llm"    - Would use LLM only (but LLM is disabled)

                    # Parse location string to dict (consistent format)
                    location_str = extract_location(text)
                    location_dict = {"city": None, "region": None, "country": None}

                    if location_str:
                        # Try to parse "City, State" or "City, State ZIP" format
                        parts = location_str.split(',')
                        if len(parts) >= 2:
                            location_dict["city"] = parts[0].strip()
                            # Extract state code (2 letters)
                            state_part = parts[1].strip().split()[0]  # Get first word (state code)
                            if len(state_part) == 2:
                                location_dict["region"] = state_part
                        elif len(parts) == 1:
                            location_dict["city"] = parts[0].strip()

                    parsed_data = {
                        "full_name": extract_name(text) or "Unknown",
                        "email": extract_email(text),
                        "phone": extract_phone(text),
                        "skills": normalized_skills,  # Normalized through ontology
                        "years_experience": calculate_years_experience(text),
                        "location": location_dict,  # Consistent dict format
                        "professional_summary": text[:500],
                        "s3_resume_url": s3_url
                    }

                # Cache in Redis with 1-hour TTL
                await redis_client.set(
                    f"parsed_candidate:{candidate_id}",
                    json.dumps(parsed_data),
                    ex=3600  # 1 hour
                )

                logger.info(f"✅ Parse-only complete for {candidate_id}")
                logger.info(f"   Method: {'LLM' if llm_parsing_attempted else 'Regex'}")
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
        async with AsyncSessionLocal() as db:
            try:
                retry_count = job_data.get("retry_count", 0)

                if retry_count > 0:
                    logger.warning(f"⚠️  Retry attempt for job {job_data['job_id']}")

                # ========================================
                # STAGE 1: Fetch candidate details
                # ========================================
                stage_start = datetime.utcnow()
                logger.info(f"[1/7] Fetching candidate details: {candidate_id}")
                
                result = await db.execute(
                    select(Candidate)
                    .options(selectinload(Candidate.contact))
                    .where(Candidate.id == candidate_id)
                )
                candidate = result.scalar_one_or_none()
                
                if not candidate:
                    # Permanent error - candidate doesn't exist
                    logger.error(f"❌ Candidate {candidate_id} not found in database")
                    raise ValueError(f"Candidate {candidate_id} not found")
                
                logger.info(f"✅ Found candidate: {candidate.full_name}")
                metrics_collector.record_timing("ingestion_stage_1_fetch", stage_start)
                
                # ========================================
                # STAGE 2: Download resume from MinIO
                # ========================================
                stage_start = datetime.utcnow()
                logger.info(f"[2/7] Downloading resume from {s3_url}")
                
                resume_bytes = await s3_client.download_file(s3_url)
                
                logger.info(f"✅ Downloaded {len(resume_bytes)} bytes")
                metrics_collector.record_timing("ingestion_stage_2_download", stage_start)
                
                # ========================================
                # STAGE 3: Parse resume (extract text)
                # ========================================
                stage_start = datetime.utcnow()
                logger.info(f"[3/7] Parsing resume (extracting text)")
                
                parsed_data = await parse_resume(resume_bytes, s3_url)
                text = parsed_data["text"]
                metadata = parsed_data["metadata"]
                
                logger.info(
                    f"✅ Extracted {metadata['char_count']} chars "
                    f"(format: {metadata['format']}, pages: {metadata.get('page_count', 'N/A')})"
                )
                metrics_collector.record_timing("ingestion_stage_3_parse", stage_start)
                
                # ========================================
                # STAGE 4: Extract fields and skills
                # ========================================
                stage_start = datetime.utcnow()
                logger.info(f"[4/7] Extracting fields and skills from resume text")

                # Use unified skill extraction (LLM if enabled, spaCy fallback)
                from app.services.skill_extractor import extract_skills

                if settings.use_llm_parsing:
                    logger.info("Using LLM-based extraction (hybrid mode: LLM + spaCy)")
                    # Extract skills using hybrid method (LLM + spaCy)
                    extracted_skills = await extract_skills(text, method="hybrid")
                else:
                    logger.info("Using spaCy-based extraction (LLM disabled)")
                    # Extract skills using spaCy only
                    extracted_skills = await extract_skills(text, method="spacy")

                logger.info(f"✅ Extracted {len(extracted_skills)} skills: {', '.join(extracted_skills[:5])}{'...' if len(extracted_skills) > 5 else ''}")
                metrics_collector.record_timing("ingestion_stage_4_skills", stage_start)

                # ========================================
                # STAGE 4.5: Store skills in PostgreSQL
                # ========================================
                stage_start = datetime.utcnow()
                logger.info(f"[4.5/7] Storing skills in PostgreSQL")

                from app.models.candidate import Skill, CandidateSkill

                # Delete existing skills for this candidate (idempotent re-indexing)
                await db.execute(
                    delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate_id)
                )

                # For each extracted skill, find or create in skill table
                skills_created = 0
                skills_linked = 0

                for skill_name in extracted_skills:
                    # Find existing skill
                    result = await db.execute(
                        select(Skill).where(Skill.name == skill_name)
                    )
                    skill = result.scalar_one_or_none()

                    # Create skill if it doesn't exist
                    if not skill:
                        skill = Skill(name=skill_name)
                        db.add(skill)
                        await db.flush()  # Get skill.id
                        skills_created += 1
                        logger.debug(f"Created new skill: {skill_name}")

                    # Link candidate to skill
                    candidate_skill = CandidateSkill(
                        candidate_id=candidate_id,
                        skill_id=skill.id,
                        level=None,  # Not extracted yet
                        years=None   # Not extracted yet
                    )
                    db.add(candidate_skill)
                    skills_linked += 1

                await db.commit()

                logger.info(f"✅ Stored {skills_linked} skills in PostgreSQL ({skills_created} new skills created)")
                metrics_collector.record_timing("ingestion_stage_4.5_store_skills", stage_start)

                # ========================================
                # STAGE 4.6: Store resume record in PostgreSQL
                # ========================================
                stage_start = datetime.utcnow()
                logger.info(f"[4.6/8] Storing resume record in PostgreSQL")

                from app.models.candidate import CandidateResume

                # Extract file extension from s3_url
                file_ext = None
                if '.' in s3_url:
                    file_ext = '.' + s3_url.split('.')[-1].lower()

                # Mark all previous resumes as not latest
                await db.execute(
                    text("UPDATE rightstaff.candidate_resume SET is_latest = false WHERE candidate_id = :cid"),
                    {"cid": str(candidate_id)}
                )

                # Create new resume record
                resume_record = CandidateResume(
                    candidate_id=candidate_id,
                    s3_url=s3_url,
                    file_type=file_ext,
                    is_latest=True,
                    uploaded_at=datetime.utcnow()
                )
                db.add(resume_record)
                await db.commit()

                logger.info(f"✅ Stored resume record: {s3_url} (type: {file_ext})")
                metrics_collector.record_timing("ingestion_stage_4.6_store_resume", stage_start)

                # ========================================
                # STAGE 5: Chunk text
                # ========================================
                stage_start = datetime.utcnow()
                logger.info(f"[5/8] Chunking text (size=400, overlap=50)")
                
                chunks = chunk_text(
                    text,
                    chunk_size=400,
                    chunk_overlap=50
                )
                
                if not chunks:
                    logger.warning(f"⚠️  No chunks generated (text too short?). Skipping embedding.")
                    return
                
                logger.info(f"✅ Created {len(chunks)} chunks")
                metrics_collector.record_timing("ingestion_stage_5_chunk", stage_start)
                
                # ========================================
                # STAGE 6: Generate embeddings (profile, skills, chunks)
                # ========================================
                stage_start = datetime.utcnow()
                logger.info(f"[6/8] Generating embeddings (1 profile + 1 skills + {len(chunks)} chunks)")

                # 6a. Generate profile embedding (full resume summary)
                profile_text = f"{candidate.full_name}\n{text[:1000]}"  # Use first 1000 chars as profile
                profile_embedding = await embedding_service.embed_text(profile_text)

                # 6b. Generate skills embedding (extracted skills)
                skills_text = " ".join(extracted_skills) if extracted_skills else "No skills detected"
                skills_embedding = await embedding_service.embed_text(skills_text)

                # 6c. Generate chunk embeddings (resume chunks)
                chunk_texts = [chunk["text"] for chunk in chunks]
                chunk_embeddings = await embedding_service.embed_batch(chunk_texts, batch_size=32)

                logger.info(f"✅ Generated 1 profile + 1 skills + {len(chunk_embeddings)} chunk embeddings (dim={len(profile_embedding)})")
                metrics_collector.record_timing("ingestion_stage_6_embed", stage_start)

                # ========================================
                # STAGE 7: Store in Qdrant (profile + skills + chunks)
                # ========================================
                stage_start = datetime.utcnow()
                logger.info(f"[7/8] Storing vectors in Qdrant")

                # Delete old vectors first (idempotent re-indexing)
                logger.info(f"Deleting old vectors for candidate {candidate_id} (if any)")
                vector_store.delete_by_candidate_id(str(candidate_id))

                # 7a. Build profile payload
                all_vectors = [profile_embedding]
                all_payloads = [{
                    "candidate_id": str(candidate_id),
                    "kind": "profile",
                    "full_name": candidate.full_name,
                    "text": profile_text[:500],  # Store snippet for debugging
                    "skills": extracted_skills,
                    "filename": metadata["filename"],
                    "created_at": datetime.utcnow().isoformat()
                }]

                # 7b. Build skills payload
                all_vectors.append(skills_embedding)
                all_payloads.append({
                    "candidate_id": str(candidate_id),
                    "kind": "skills",
                    "skills": extracted_skills,
                    "skills_count": len(extracted_skills),
                    "filename": metadata["filename"],
                    "created_at": datetime.utcnow().isoformat()
                })

                # 7c. Build chunk payloads
                for chunk, embedding in zip(chunks, chunk_embeddings):
                    all_vectors.append(embedding)
                    all_payloads.append({
                        "candidate_id": str(candidate_id),
                        "kind": "chunk",
                        "chunk_index": chunk["chunk_index"],
                        "chunk_text": chunk["text"],
                        "start_char": chunk["start_char"],
                        "end_char": chunk["end_char"],
                        "char_count": chunk["char_count"],
                        "skills_detected": extracted_skills,  # Skills for this candidate
                        "filename": metadata["filename"],
                        "created_at": datetime.utcnow().isoformat()
                    })

                # Upsert all vectors (1 profile + 1 skills + N chunks)
                success = vector_store.upsert_vectors(
                    vectors=all_vectors,
                    payloads=all_payloads
                )

                if not success:
                    raise Exception("Vector upsert failed")

                logger.info(f"✅ Stored {len(all_vectors)} vectors in Qdrant (1 profile + 1 skills + {len(chunk_embeddings)} chunks)")
                metrics_collector.record_timing("ingestion_stage_7_store", stage_start)
                
                # ========================================
                # SUCCESS SUMMARY
                # ========================================
                total_time = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    f"✅✅✅ Successfully processed job {job_data['job_id']} in {total_time:.2f}s\n"
                    f"   Candidate: {candidate.full_name}\n"
                    f"   Location: {candidate.contact.city if candidate.contact else 'N/A'}\n"
                    f"   Text: {metadata['char_count']} chars\n"
                    f"   Skills: {len(extracted_skills)}\n"
                    f"   Chunks: {len(chunks)}\n"
                    f"   Vectors: {len(all_vectors)} (1 profile + 1 skills + {len(chunk_embeddings)} chunks, dim={len(profile_embedding)})\n"
                    f"   Retry count: {retry_count}"
                )
                
                metrics_collector.record_timing("ingestion_total", start_time)
                
            except ValueError as e:
                # Permanent error - don't retry
                logger.error(f"❌ Permanent error in job processing: {e}")
                raise
            except Exception as e:
                # Transient error - will retry
                logger.error(f"❌ Job processing failed (will retry if retriable): {e}")
                metrics_collector.increment_counter("ingestion_retries")
                raise
    
    async def _move_to_dlq(self, job_data: dict, error_message: str):
        """
        Move failed job to Dead Letter Queue.
        
        Why DLQ?
        - Failed jobs don't get lost
        - Can investigate failures later
        - Can replay jobs after fixing issues
        - Enables alerting on DLQ depth
        
        Args:
            job_data: Original job data
            error_message: Final error message
        """
        dlq_entry = {
            **job_data,
            "failed_at": datetime.utcnow().isoformat(),
            "error": error_message,
            "final_retry_count": job_data.get("retry_count", 0)
        }
        
        try:
            await redis_client.push_dlq(json.dumps(dlq_entry))
            logger.warning(f"📬 Moved job {job_data['job_id']} to DLQ after {job_data.get('retry_count', 0)} retries")
        except Exception as e:
            # If DLQ push fails, log the full job data
            logger.error(f"❌ Failed to push to DLQ: {e}")
            logger.error(f"Lost job data: {json.dumps(dlq_entry)}")

# Global worker instance
ingestion_worker = IngestionWorker()
