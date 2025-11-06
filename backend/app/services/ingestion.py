"""
Background worker that processes ingestion jobs from Redis queue.
Flow: Poll Redis → Fetch candidate → Download resume → Parse → (Day 4: Embed & Store)
"""
import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.candidate import Candidate, CandidateContact, CandidateResume
from app.services.redis_client import redis_client
from app.services.s3_client import s3_client
from app.services.parsers import parse_resume
from app.utils.logging import logger

class IngestionWorker:
    """Background worker for processing resume ingestion jobs."""

    def __init__(self):
        self.running = False

    async def start(self):
        """Start the background worker loop."""
        self.running = True
        logger.info("Ingestion worker started - polling Redis queue")

        while self.running:
            try:
                # Step 1: Pop job from Redis queue (blocking pop, 5s timeout)
                # BRPOP = Blocking Right POP (take from right/end of list)
                result = await redis_client.brpop("ingestion_queue", timeout=5)

                if result is None:
                    # No jobs in queue, loop again
                    continue

                # Step 2: Parse job data
                _, job_data_str = result  # result is (queue_name, data)
                job_data = json.loads(job_data_str)

                logger.info(f"Processing job {job_data['job_id']}")

                # Step 3: Process the job
                await self.process_job(job_data)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)  # Backoff on error

    def stop(self):
        """Stop the worker gracefully."""
        self.running = False
        logger.info("Ingestion worker stopped")

    async def process_job(self, job_data: dict):
        """
        Process a single ingestion job.

        Steps:
        1. Fetch candidate details from PostgreSQL
        2. Download resume from MinIO
        3. Parse resume (extract text)
        4. TODO (Day 4): Chunk text and generate embeddings
        5. TODO (Day 5): Upsert vectors to Qdrant
        """
        async with AsyncSessionLocal() as db:
            try:
                candidate_id = job_data["candidate_id"]
                s3_url = job_data["s3_resume_url"]

                # Step 1: Fetch candidate details with eager loading
                result = await db.execute(
                    select(Candidate)
                    .options(selectinload(Candidate.contact))
                    .where(Candidate.id == candidate_id)
                )
                candidate = result.scalar_one_or_none()

                if not candidate:
                    logger.error(f"Candidate {candidate_id} not found in database")
                    return

                logger.info(f"Processing candidate: {candidate.full_name}")

                # Step 2: Download resume from MinIO
                logger.info(f"Downloading resume from {s3_url}")
                resume_bytes = await s3_client.download_file(s3_url)

                # Step 3: Parse resume (extract text)
                logger.info(f"Parsing resume for {candidate.full_name}")
                parsed_data = await parse_resume(resume_bytes, s3_url)

                # Step 4: Log success (Day 4 will add chunking/embedding)
                text_length = len(parsed_data["text"])
                logger.info(f"Extracted {text_length} characters from resume")
                logger.info(f"   Candidate: {candidate.full_name}")
                logger.info(f"   Location: {candidate.contact.city if candidate.contact else 'N/A'}")

                # TODO (Day 4): Chunk text
                # chunks = chunk_text(parsed_data["text"], chunk_size=400, overlap=50)

                # TODO (Day 4): Generate embeddings
                # embeddings = await generate_embeddings(chunks)

                # TODO (Day 5): Upsert to Qdrant
                # await qdrant_client.upsert(vectors=embeddings, metadata=...)

                logger.info(f"Successfully processed job {job_data['job_id']}")

            except Exception as e:
                logger.error(f"Job processing failed: {e}")
                # TODO (Day 2): Implement retry logic with exponential backoff
                raise

# Global worker instance
ingestion_worker = IngestionWorker()
