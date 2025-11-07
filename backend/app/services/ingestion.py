"""
Background worker that processes ingestion jobs from Redis queue.
Flow: Poll Redis → Fetch candidate → Download resume → Parse → Chunk → Embed → Store in Qdrant
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
from app.services.parsers import parse_resume, chunk_text
from app.services.embeddings import embedding_service
from app.services.vector_store import vector_store
from app.utils.logging import logger

class IngestionWorker:
    """Background worker for processing resume ingestion jobs."""
    
    def __init__(self):
        self.running = False
    
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
                
                # Step 3: Process the job
                await self.process_job(job_data)
                
            except Exception as e:
                logger.error(f"❌ Worker error: {e}")
                await asyncio.sleep(1)  # Backoff on error
    
    def stop(self):
        """Stop the worker gracefully."""
        self.running = False
        logger.info("🛑 Ingestion worker stopped")
    
    async def process_job(self, job_data: dict):
        """
        Process a single ingestion job - THE COMPLETE PIPELINE.
        
        Pipeline stages:
        1. Fetch candidate details from PostgreSQL
        2. Download resume from MinIO
        3. Parse resume (extract text)
        4. Chunk text (split into semantic units)
        5. Generate embeddings (convert to vectors)
        6. Store in Qdrant (save vectors + metadata)
        
        Why this order?
        - Each stage depends on previous stage's output
        - Early stages are fast (fetch, download)
        - Late stages are expensive (embedding, storage)
        - If early stage fails, we don't waste compute on late stages
        
        Error handling:
        - Logs errors at each stage
        - Raises exception to indicate failure
        - TODO (Day 3): Add retry logic with exponential backoff
        
        Args:
            job_data: Job metadata from Redis queue
                {
                    "job_id": str,
                    "candidate_id": str (UUID),
                    "s3_resume_url": str,
                    "event_type": str,
                    "timestamp": str (ISO format)
                }
        """
        async with AsyncSessionLocal() as db:
            try:
                candidate_id = job_data["candidate_id"]
                s3_url = job_data["s3_resume_url"]
                
                # ========================================
                # STAGE 1: Fetch candidate details
                # ========================================
                logger.info(f"[1/6] Fetching candidate details: {candidate_id}")
                
                result = await db.execute(
                    select(Candidate)
                    .options(selectinload(Candidate.contact))
                    .where(Candidate.id == candidate_id)
                )
                candidate = result.scalar_one_or_none()
                
                if not candidate:
                    logger.error(f"❌ Candidate {candidate_id} not found in database")
                    return
                
                logger.info(f"✅ Found candidate: {candidate.full_name}")
                
                # ========================================
                # STAGE 2: Download resume from MinIO
                # ========================================
                logger.info(f"[2/6] Downloading resume from {s3_url}")
                
                resume_bytes = await s3_client.download_file(s3_url)
                
                logger.info(f"✅ Downloaded {len(resume_bytes)} bytes")
                
                # ========================================
                # STAGE 3: Parse resume (extract text)
                # ========================================
                logger.info(f"[3/6] Parsing resume (extracting text)")
                
                parsed_data = await parse_resume(resume_bytes, s3_url)
                text = parsed_data["text"]
                metadata = parsed_data["metadata"]
                
                logger.info(
                    f"✅ Extracted {metadata['char_count']} chars "
                    f"(format: {metadata['format']}, pages: {metadata.get('page_count', 'N/A')})"
                )
                
                # ========================================
                # STAGE 4: Chunk text
                # ========================================
                logger.info(f"[4/6] Chunking text (size=400, overlap=50)")
                
                chunks = chunk_text(
                    text,
                    chunk_size=400,
                    chunk_overlap=50
                )
                
                if not chunks:
                    logger.warning(f"⚠️  No chunks generated (text too short?). Skipping embedding.")
                    return
                
                logger.info(f"✅ Created {len(chunks)} chunks")
                
                # ========================================
                # STAGE 5: Generate embeddings
                # ========================================
                logger.info(f"[5/6] Generating embeddings for {len(chunks)} chunks")
                
                # Extract text from chunks for embedding
                chunk_texts = [chunk["text"] for chunk in chunks]
                
                # Batch embed (more efficient than one-by-one)
                embeddings = await embedding_service.embed_batch(
                    chunk_texts,
                    batch_size=32  # Good default for CPU
                )
                
                logger.info(f"✅ Generated {len(embeddings)} embeddings (dim={len(embeddings[0])})")
                
                # ========================================
                # STAGE 6: Store in Qdrant
                # ========================================
                logger.info(f"[6/6] Storing vectors in Qdrant")
                
                # Build payloads (metadata for each vector)
                payloads = []
                for chunk, embedding in zip(chunks, embeddings):
                    payload = {
                        "candidate_id": str(candidate_id),
                        "chunk_index": chunk["chunk_index"],
                        "chunk_text": chunk["text"],
                        "start_char": chunk["start_char"],
                        "end_char": chunk["end_char"],
                        "char_count": chunk["char_count"],
                        "filename": metadata["filename"],
                        "created_at": datetime.utcnow().isoformat()
                    }
                    payloads.append(payload)
                
                # Delete old vectors for this candidate (if re-indexing)
                # Why delete first?
                # - Prevents duplicate vectors if resume was updated
                # - Ensures we don't have stale data from old resume
                logger.info(f"Deleting old vectors for candidate {candidate_id} (if any)")
                vector_store.delete_by_candidate_id(str(candidate_id))
                
                # Upsert new vectors
                success = vector_store.upsert_vectors(
                    vectors=embeddings,
                    payloads=payloads
                )
                
                if not success:
                    raise Exception("Vector upsert failed")
                
                logger.info(f"✅ Stored {len(embeddings)} vectors in Qdrant")
                
                # ========================================
                # SUCCESS SUMMARY
                # ========================================
                logger.info(
                    f"✅✅✅ Successfully processed job {job_data['job_id']}\n"
                    f"   Candidate: {candidate.full_name}\n"
                    f"   Location: {candidate.contact.city if candidate.contact else 'N/A'}\n"
                    f"   Text: {metadata['char_count']} chars\n"
                    f"   Chunks: {len(chunks)}\n"
                    f"   Vectors: {len(embeddings)} (dim={len(embeddings[0])})"
                )
                
            except Exception as e:
                logger.error(f"❌ Job processing failed: {e}")
                # TODO (Day 3): Implement retry logic with exponential backoff
                # TODO (Day 3): Move to dead letter queue after max retries
                raise

# Global worker instance
ingestion_worker = IngestionWorker()
