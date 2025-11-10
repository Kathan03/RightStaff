# backend/app/api/admin.py
"""
Admin endpoints for monitoring, metrics, and DLQ management.

Endpoints:
- GET /admin/metrics - View system metrics
- GET /admin/dlq - View Dead Letter Queue status
- POST /admin/dlq/replay - Replay failed jobs from DLQ
- POST /admin/dlq/clear - Clear DLQ (warning: destructive)

Why admin endpoints?
- Observability: Monitor system health
- Debugging: Investigate failed jobs
- Operations: Replay or clear DLQ
"""

from fastapi import APIRouter
import logging
import json

from app.services.redis_client import redis_client
from app.services.metrics import metrics_collector
from app.services.vector_store import vector_store
from app.services.embeddings import embedding_service
from app.services.ontology import is_spacy_available

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics")
async def get_metrics():
    """
    Get current system metrics.
    
    Returns metrics for:
    - Counters: Job success/failure counts
    - Timings: Stage durations (avg, min, max)
    - Gauges: Point-in-time values
    - System: Embedding model, Qdrant collection info
    
    Returns:
        Dictionary with all metrics
    """
    metrics = metrics_collector.get_metrics()
    
    # Add system metrics
    try:
        metrics["system"] = {
            "embedding_model": embedding_service.get_model_info(),
            "qdrant_collection": vector_store.get_collection_info(),
            "spacy_ner": {
                "available": is_spacy_available(),
                "status": "enabled" if is_spacy_available() else "degraded (pattern-only)",
                "coverage": "90%" if is_spacy_available() else "80%"
            }
        }
    except Exception as e:
        logger.warning(f"Failed to fetch system metrics: {e}")
        metrics["system"] = {"error": str(e)}
    
    return metrics


@router.get("/dlq")
async def get_dlq_status():
    """
    Get Dead Letter Queue status.
    
    Returns:
    - depth: Number of failed jobs in DLQ
    - sample_entries: First 10 failed jobs (with error details)
    
    Use this to:
    - Monitor DLQ depth (alert if > threshold)
    - Investigate failure patterns
    - Debug specific job failures
    """
    depth = await redis_client.get_dlq_depth()
    entries = await redis_client.get_dlq_entries(start=0, end=9)
    
    return {
        "depth": depth,
        "sample_entries": [json.loads(e) for e in entries] if entries else []
    }


@router.post("/dlq/replay")
async def replay_dlq():
    """
    Replay all jobs from DLQ.
    
    Use when:
    - Fixed bug that caused failures
    - Temporary service outage resolved
    - Want to retry all failed jobs
    
    How it works:
    1. Pop each job from DLQ
    2. Remove error metadata
    3. Reset retry count
    4. Push back to main queue
    
    Returns:
        Number of jobs replayed
    """
    depth = await redis_client.get_dlq_depth()
    replayed = 0
    
    for _ in range(depth):
        entry = await redis_client.pop_dlq()
        if entry:
            await redis_client.replay_dlq_entry(entry)
            replayed += 1
    
    logger.info(f"♻️  Replayed {replayed} jobs from DLQ")
    
    return {
        "status": "completed",
        "replayed_count": replayed
    }


@router.post("/dlq/clear")
async def clear_dlq():
    """
    Clear all entries from DLQ.
    
    ⚠️  WARNING: This permanently deletes all failed jobs!
    
    Use with caution. Consider:
    - Exporting DLQ first (via GET /admin/dlq)
    - Understanding why jobs failed
    - Fixing root cause before clearing
    
    Returns:
        Number of entries deleted
    """
    deleted_count = await redis_client.clear_dlq()
    
    logger.warning(f"🗑️  Cleared DLQ: {deleted_count} entries deleted")
    
    return {
        "status": "completed",
        "deleted_count": deleted_count,
        "warning": "All failed jobs have been permanently deleted"
    }


@router.get("/health/detailed")
async def detailed_health():
    """
    Detailed health check with component metrics.
    
    Returns:
    - Worker stats (jobs processed, failed)
    - Redis queue depth
    - DLQ depth
    - Qdrant vector count
    
    Use for monitoring/alerting.
    """
    from app.services.ingestion import ingestion_worker
    
    try:
        dlq_depth = await redis_client.get_dlq_depth()
    except Exception as e:
        dlq_depth = f"error: {e}"
    
    try:
        collection_info = vector_store.get_collection_info()
        vector_count = collection_info.get("vectors_count", "unknown")
    except Exception as e:
        vector_count = f"error: {e}"
    
    return {
        "status": "ok",
        "worker": {
            "running": ingestion_worker.running,
            "jobs_processed": ingestion_worker.jobs_processed,
            "jobs_failed": ingestion_worker.jobs_failed
        },
        "dlq_depth": dlq_depth,
        "vector_count": vector_count
    }

