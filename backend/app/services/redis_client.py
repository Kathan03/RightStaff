"""
Redis client for caching and queue management.
Async version for FastAPI compatibility.
"""

from redis.asyncio import Redis
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

    async def close(self):
        """Close Redis connection."""
        await self.client.close()
        logger.info("Redis connection closed")

# Singleton instance
redis_client = RedisClient()
