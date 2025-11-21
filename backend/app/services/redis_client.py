"""
Redis client for caching and queue management.

Async version for FastAPI compatibility.

Features:
- Dead Letter Queue methods (push_dlq, get_dlq_entries, get_dlq_depth)
- DLQ replay functionality
- DLQ management (pop, clear)
"""

from redis.asyncio import Redis
from typing import List, Optional
from app.config import settings
from app.utils.logging import logger

class RedisClient:
    """Async Redis client for queuing and caching."""

    def __init__(self):
        self.client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        logger.info(f"Redis client initialized (async): {settings.redis_host}:{settings.redis_port}")

    async def ping(self):
        """Health check."""
        return await self.client.ping()

    async def lpush(self, key: str, value: str):
        """Push to left/front of list."""
        return await self.client.lpush(key, value)

    async def brpop(self, key: str, timeout: int = 0):
        """Blocking pop from right/end of list."""
        return await self.client.brpop(key, timeout)

    async def get(self, key: str):
        """Get value from Redis."""
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        """Set value in Redis with optional expiry."""
        return await self.client.set(key, value, ex=ex)

    async def delete(self, key: str):
        """Delete key from Redis."""
        return await self.client.delete(key)
    
    # ========================================
    # Dead Letter Queue Methods
    # ========================================
    
    async def push_dlq(self, value: str, queue_name: str = "ingestion_queue_dlq"):
        """
        Push failed job to Dead Letter Queue.
        
        DLQ is a separate Redis list that stores jobs that failed after max retries.
        
        Why separate queue?
        - Don't pollute main queue with failed jobs
        - Easy to monitor DLQ depth
        - Can process DLQ separately (manual review, replay)
        
        Args:
            value: JSON-serialized job data with error info
            queue_name: DLQ name (default: ingestion_queue_dlq)
        
        Returns:
            Number of elements in DLQ after push
        """
        result = await self.client.lpush(queue_name, value)
        logger.warning(f"📬 Pushed to DLQ: {queue_name} (depth: {result})")
        return result
    
    async def get_dlq_entries(
        self,
        queue_name: str = "ingestion_queue_dlq",
        start: int = 0,
        end: int = 99
    ) -> List[str]:
        """
        Get failed jobs from DLQ (without removing them).
        
        Uses LRANGE to peek at DLQ contents without modifying it.
        
        Args:
            queue_name: DLQ name
            start: Start index (0 = oldest)
            end: End index (99 = get first 100)
        
        Returns:
            List of JSON-serialized job entries
        
        Example:
            # Get first 10 failed jobs
            entries = await redis_client.get_dlq_entries(start=0, end=9)
        """
        entries = await self.client.lrange(queue_name, start, end)
        return entries
    
    async def get_dlq_depth(self, queue_name: str = "ingestion_queue_dlq") -> int:
        """
        Get number of jobs in DLQ.
        
        Useful for monitoring/alerting.
        
        Args:
            queue_name: DLQ name
        
        Returns:
            Number of jobs in DLQ
        """
        depth = await self.client.llen(queue_name)
        return depth
    
    async def pop_dlq(self, queue_name: str = "ingestion_queue_dlq") -> Optional[str]:
        """
        Pop one job from DLQ (removes it).
        
        Use this for DLQ replay functionality.
        
        Args:
            queue_name: DLQ name
        
        Returns:
            JSON-serialized job data, or None if DLQ empty
        """
        entry = await self.client.rpop(queue_name)
        return entry
    
    async def replay_dlq_entry(
        self,
        entry: str,
        target_queue: str = "ingestion_queue"
    ):
        """
        Replay a DLQ entry by pushing it back to main queue.
        
        This removes error metadata and resets retry count.
        
        Args:
            entry: JSON-serialized DLQ entry
            target_queue: Queue to push to (default: ingestion_queue)
        
        Example:
            # Replay single job
            entry = await redis_client.pop_dlq()
            if entry:
                await redis_client.replay_dlq_entry(entry)
        """
        import json
        from datetime import datetime
        
        # Parse DLQ entry
        dlq_data = json.loads(entry)
        
        # Clean up DLQ metadata
        job_data = {
            k: v for k, v in dlq_data.items()
            if k not in ["failed_at", "error", "final_retry_count"]
        }
        
        # Reset retry count
        job_data["retry_count"] = 0
        job_data["replayed_at"] = datetime.utcnow().isoformat()
        
        # Push back to main queue
        await self.lpush(target_queue, json.dumps(job_data))
        logger.info(f"♻️  Replayed job {job_data['job_id']} from DLQ to {target_queue}")
    
    async def clear_dlq(self, queue_name: str = "ingestion_queue_dlq") -> int:
        """
        Clear all entries from DLQ.
        
        ⚠️  WARNING: This permanently deletes all failed jobs!
        Use with caution. Consider exporting DLQ first.
        
        Args:
            queue_name: DLQ name
        
        Returns:
            Number of entries deleted
        """
        depth = await self.get_dlq_depth(queue_name)
        await self.delete(queue_name)
        logger.warning(f"🗑️  Cleared DLQ: {queue_name} ({depth} entries deleted)")
        return depth

    async def close(self):
        """Close Redis connection."""
        await self.client.close()
        logger.info("Redis connection closed")

# Singleton instance
redis_client = RedisClient()
