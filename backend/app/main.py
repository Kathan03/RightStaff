"""
Main FastAPI application entry point.
RightStaff AI Backend - Candidate Ranking Engine
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime

from app.api import webhooks, jobs, admin, candidates  # NEW: jobs, admin routers (Day 3), candidates (Day 5)
from app.services.ingestion import ingestion_worker
from app.utils.logging import logger
from decimal import Decimal
import json
from fastapi.responses import JSONResponse

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


app = FastAPI(
    title="RightStaff AI Backend",
    description="AI-powered candidate ranking with explainable results",
    version="1.0.0"
)
app.json_encoder = DecimalEncoder


# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])  # NEW: Day 3
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])  # NEW: Day 3
app.include_router(candidates.router, prefix="/api/v1/candidates", tags=["candidates"])  # NEW: Day 5

@app.on_event("startup")
async def startup_event():
    """Start background worker when FastAPI starts."""
    # Initialize Qdrant collections (candidates_v1 and jobs_v1)
    from app.services.vector_store import vector_store
    vector_store.initialize_collections()

    asyncio.create_task(ingestion_worker.start())
    logger.info("FastAPI app started with background worker")

@app.get("/health")
async def health_check():
    """
    Comprehensive health check for all services.
    Returns status of: API, PostgreSQL, Qdrant, Redis, MinIO
    """
    from app.database import AsyncSessionLocal
    from app.services.redis_client import redis_client
    from app.services.vector_store import vector_store
    from app.services.s3_client import s3_client
    from sqlalchemy import text

    services = {
        "api": "unknown",
        "database": "unknown",
        "qdrant": "unknown",
        "redis": "unknown",
        "minio": "unknown"
    }

    # Check API (if we got here, it's working)
    services["api"] = "ok"

    # Check PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        services["database"] = "ok"
    except Exception as e:
        services["database"] = f"error: {str(e)[:50]}"
        logger.error(f"PostgreSQL health check failed: {e}")

    # Check Qdrant
    try:
        # Just check if we can connect
        collections = vector_store.client.get_collections()
        services["qdrant"] = "ok"
    except Exception as e:
        services["qdrant"] = f"error: {str(e)[:50]}"
        logger.error(f"Qdrant health check failed: {e}")

    # Check Redis
    try:
        await redis_client.ping()
        services["redis"] = "ok"
    except Exception as e:
        services["redis"] = f"error: {str(e)[:50]}"
        logger.error(f"Redis health check failed: {e}")

    # Check MinIO
    try:
        # Check if bucket exists
        if s3_client.client.bucket_exists(s3_client.bucket_name):
            services["minio"] = "ok"
        else:
            services["minio"] = "warning: bucket not found"
    except Exception as e:
        services["minio"] = f"error: {str(e)[:50]}"
        logger.error(f"MinIO health check failed: {e}")

    # Determine overall health status
    all_ok = all(status == "ok" for status in services.values())

    return {
        "status": "healthy" if all_ok else "unhealthy",
        "services": services,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return {
        "message": "RightStaff AI Backend",
        "docs": "/docs",
        "health": "/health"
    }
