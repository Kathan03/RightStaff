"""
Automated Ingestion Monitoring and Self-Healing System

This service runs alongside the ingestion worker and:
1. Monitors the DLQ for failed jobs
2. Automatically replays failed jobs after investigation
3. Ensures all candidates with resumes have vectors in Qdrant
4. Self-heals the system by re-queuing missing ingestions

Run this as a background task in main.py startup.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.candidate import Candidate, CandidateResume
from app.services.redis_client import redis_client
from app.services.vector_store import vector_store
from app.utils.logging import logger
from qdrant_client.models import Filter, FieldCondition, MatchValue


class IngestionMonitor:
    """
    Automated monitoring and self-healing for the ingestion pipeline.

    Features:
    - DLQ monitoring and automatic replay
    - Health checks for candidate vectors
    - Automatic re-queueing of missing ingestions
    - Alerting on persistent failures
    """

    def __init__(self):
        self.running = False
        self.check_interval = 300  # 5 minutes
        self.dlq_replay_delay = 600  # 10 minutes before retry
        self.max_dlq_retries = 3

    async def start(self):
        """Start the monitoring loop."""
        self.running = True
        logger.info("🔍 Ingestion Monitor started")

        while self.running:
            try:
                # Check 1: Monitor DLQ
                await self._check_dlq()

                # Check 2: Ensure all candidates have vectors
                await self._check_missing_vectors()

                # Wait before next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"❌ Monitor error: {e}")
                await asyncio.sleep(60)  # Backoff on error

    def stop(self):
        """Stop the monitoring loop."""
        self.running = False
        logger.info("🛑 Ingestion Monitor stopped")

    async def _check_dlq(self):
        """
        Check DLQ for failed jobs and automatically replay them.

        Strategy:
        1. Get all DLQ entries
        2. For each entry older than replay_delay:
           - Log the error details
           - Check retry count
           - If < max_retries: replay the job
           - If >= max_retries: alert and keep in DLQ for manual review
        """
        try:
            dlq_depth = await redis_client.get_dlq_depth("ingestion_queue_dlq")

            if dlq_depth == 0:
                return  # No failed jobs

            logger.info(f"📬 DLQ contains {dlq_depth} failed jobs")

            # Get all DLQ entries
            entries = await redis_client.get_dlq_entries("ingestion_queue_dlq", 0, dlq_depth - 1)

            for entry_str in entries:
                job_data = json.loads(entry_str)
                candidate_id = job_data.get('candidate_id', 'unknown')
                failed_at_str = job_data.get('failed_at')
                retry_count = job_data.get('final_retry_count', 0)
                error_msg = job_data.get('error', 'Unknown error')
                traceback = job_data.get('traceback', 'No traceback available')

                # Log the error with full details
                logger.warning(
                    f"DLQ Entry: candidate_id={candidate_id}, "
                    f"error={error_msg}, retry_count={retry_count}"
                )

                # Parse failed_at timestamp
                if failed_at_str:
                    failed_at = datetime.fromisoformat(failed_at_str)
                    time_since_failure = datetime.utcnow() - failed_at

                    # Check if enough time has passed for replay
                    if time_since_failure.total_seconds() < self.dlq_replay_delay:
                        continue  # Too soon to retry

                # Check retry count
                if retry_count >= self.max_dlq_retries:
                    logger.error(
                        f"🚨 PERSISTENT FAILURE: candidate_id={candidate_id} "
                        f"failed {retry_count} times. Manual intervention required!"
                    )
                    logger.error(f"Error: {error_msg}")
                    logger.error(f"Traceback:\n{traceback}")
                    continue  # Keep in DLQ for manual review

                # Replay the job
                logger.info(f"♻️  Auto-replaying job for candidate {candidate_id} (retry #{retry_count + 1})")

                # Pop from DLQ and replay
                await redis_client.pop_dlq("ingestion_queue_dlq")
                await redis_client.replay_dlq_entry(entry_str, "ingestion_queue")

        except Exception as e:
            logger.error(f"❌ Error checking DLQ: {e}")

    async def _check_missing_vectors(self):
        """
        Ensure all candidates with resumes have vectors in Qdrant.

        Strategy:
        1. Query all candidates with latest resumes from PostgreSQL
        2. For each candidate, check if vectors exist in Qdrant
        3. If missing, queue a new ingestion job

        This catches candidates who:
        - Had ingestion failures that exhausted retries
        - Were created before monitoring started
        - Had vectors deleted accidentally
        """
        try:
            async with AsyncSessionLocal() as db:
                # Get all candidates with resumes
                result = await db.execute(
                    select(Candidate, CandidateResume)
                    .join(CandidateResume, Candidate.id == CandidateResume.candidate_id)
                    .where(CandidateResume.is_latest == True)
                )

                candidates_checked = 0
                missing_vectors = []

                for candidate, resume in result.all():
                    candidates_checked += 1

                    # Check if vectors exist in Qdrant
                    points = vector_store.client.scroll(
                        collection_name="candidates_v1",
                        scroll_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="candidate_id",
                                    match=MatchValue(value=str(candidate.id))
                                )
                            ]
                        ),
                        limit=1
                    )[0]

                    if not points:
                        # No vectors found!
                        missing_vectors.append((candidate, resume))
                        logger.warning(
                            f"⚠️  Missing vectors for {candidate.full_name} ({candidate.id})"
                        )

                if missing_vectors:
                    logger.warning(
                        f"🔧 Found {len(missing_vectors)} candidates without vectors. Auto-queueing ingestion..."
                    )

                    # Re-queue ingestion for all missing
                    for candidate, resume in missing_vectors:
                        job_data = {
                            "job_id": f"auto_heal_{candidate.id}_{datetime.utcnow().timestamp()}",
                            "candidate_id": str(candidate.id),
                            "s3_resume_url": resume.s3_url,
                            "mode": "full",
                            "retry_count": 0,
                            "auto_healed": True
                        }

                        await redis_client.lpush("ingestion_queue", json.dumps(job_data))
                        logger.info(f"✅ Queued auto-heal job for {candidate.full_name}")
                else:
                    logger.info(f"✅ Health check passed: {candidates_checked} candidates, all have vectors")

        except Exception as e:
            logger.error(f"❌ Error checking missing vectors: {e}")


# Global monitor instance
ingestion_monitor = IngestionMonitor()
