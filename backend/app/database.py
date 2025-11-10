"""
Database connection and session management.
Provides async SQLAlchemy setup for PostgreSQL.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import settings
from app.utils.logging import logger


from decimal import Decimal
import json

def default_encoder(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Create async engine with connection pooling
# Why async? FastAPI is async, so we need async database queries
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,              # Log SQL queries in development
    pool_pre_ping=True,                # Check connection health before using
    pool_size=10,                      # Number of persistent connections
    max_overflow=20,                   # Additional connections under load
    pool_recycle=3600,                 # Recycle connections after 1 hour
    json_serializer=lambda obj: json.dumps(obj, default=default_encoder)
)

# Session factory - creates new database sessions
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,            # Don't expire objects after commit
    autocommit=False,
    autoflush=False
)

# Base class for ORM models
Base = declarative_base()

# Dependency for FastAPI routes
async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides a database session.

    Usage in routes:
        @app.get("/candidates")
        async def get_candidates(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Candidate))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database (create tables if needed)."""
    async with engine.begin() as conn:
        # In production, use Alembic migrations instead
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

def check_db_connection() -> bool:
    """
    DEPRECATED: Synchronous health check (kept for compatibility).
    Use async version in main.py instead.
    """
    logger.warning("check_db_connection is deprecated, use async version")
    return True
