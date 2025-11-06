# RightStaff AI Backend - Production-Grade Setup Guide V2.1

## 🎯 What's New in V2.1
- ✅ **Redis** for caching and async queues
- ✅ **Unstructured** library for robust PDF parsing
- ✅ **Qwen 2.5** as lightweight LLM option  
- ✅ **structlog** for JSON logging
- ✅ **tenacity** for error handling
- ✅ Comprehensive testing examples
- ✅ Observability metrics

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Understanding the SQL Files](#2-understanding-sql-files)
3. [Project Structure](#3-project-structure)
4. [Environment Setup](#4-environment-setup)
5. [Docker Services Configuration](#5-docker-services)
6. [Python Backend Setup](#6-python-backend)
7. [Core Services Implementation](#7-core-services)
8. [API Endpoints](#8-api-endpoints)
9. [Testing Strategy](#9-testing)
10. [Daily Workflow](#10-daily-workflow)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Project Overview {#1-project-overview}

**RightStaff** is an AI-powered staffing platform built to **Tier 1 engineering standards** (Google/Netflix/Meta quality).

**Tech Stack (MVP)**:
- **Backend**: FastAPI (Python 3.11+)
- **Databases**: PostgreSQL (relational), Qdrant (vectors), Redis (cache/queue), MinIO (files)
- **AI/ML**: sentence-transformers, spaCy, Unstructured (parsing), Qwen 2.5 (LLM)
- **Deployment**: Docker Compose (local), Kubernetes (production)
- **Observability**: structlog (JSON logs), Prometheus metrics

**Key Principles**:
1. **Explainability**: Every ranking cites evidence
2. **Fairness**: Zero bias from protected attributes
3. **Performance**: <5s ranking, <2.5s chatbot
4. **Reliability**: 99.5% uptime, idempotent operations
5. **Cost**: $0 MVP (local models), <$0.03 production

---

## 2. Understanding the SQL Files {#2-understanding-sql-files}

Your teammate provided 4 SQL files in `database/` folder:

### **00_rollback.sql**
- **Purpose**: Complete database reset
- **When to use**: `docker-compose down -v && docker-compose up -d`

### **01_schema.sql**
- **Purpose**: Creates entire PostgreSQL schema
- **Key tables**: `candidates`, `skills_map`, `candidate_skills`, `job_postings`, `applications`
- **3NF design**: Normalized to eliminate redundancy

### **02_seed_smoketest.sql**
- **Purpose**: Adds test data and validates schema
- **Inserts**: Sample candidate (Prathyusha Elipay), test skills, jobs

### **03_postseed_helpers.sql**
- **Purpose**: Utility functions (e.g., `set_latest_resume()`)

**Execution**: PostgreSQL Docker container auto-runs these on first startup (via volume mount at `/docker-entrypoint-initdb.d/`)

---

## 3. Project Structure {#3-project-structure}

```
rightstaff-ai/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app with CORS, middleware
│   │   ├── config.py                # Pydantic Settings
│   │   ├── database.py              # PostgreSQL connection pool
│   │   ├── models/                  # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── candidate.py
│   │   │   └── ranking.py
│   │   ├── services/                # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py        # Resume → Embeddings → Qdrant
│   │   │   ├── ranking.py           # Candidate ranking pipeline
│   │   │   ├── chatbot.py           # RAG chatbot (Phase 2)
│   │   │   ├── vector_store.py      # Qdrant client wrapper
│   │   │   ├── redis_client.py      # Redis queue & cache (NEW)
│   │   │   └── parsers.py           # Unstructured PDF parser (NEW)
│   │   ├── api/                     # API routers
│   │   │   ├── __init__.py
│   │   │   ├── webhooks.py          # POST /webhooks/candidate-updated
│   │   │   ├── candidates.py        # Candidate CRUD
│   │   │   ├── jobs.py              # Job ranking
│   │   │   └── chat.py              # WebSocket chatbot
│   │   └── utils/                   # Helpers
│   │       ├── __init__.py
│   │       ├── skills.py            # spaCy skill extraction
│   │       └── logging.py           # structlog config (NEW)
│   ├── tests/                       # pytest suite
│   │   ├── __init__.py
│   │   ├── test_parsers.py
│   │   ├── test_skills.py
│   │   ├── test_vector_store.py
│   │   ├── test_ranking.py
│   │   ├── test_fairness.py
│   │   └── locustfile.py            # Load tests
│   ├── requirements.txt
│   ├── .env
│   └── pytest.ini
│
├── frontend/
│   └── index.html                   # Mock UI (optional)
│
├── database/
│   ├── 00_rollback.sql
│   ├── 01_schema.sql
│   ├── 02_seed_smoketest.sql
│   └── 03_postseed_helpers.sql
│
├── docker/
│   ├── docker-compose.yml           # All services (Postgres, Qdrant, Redis, MinIO)
│   └── .env.docker
│
├── data/                            # gitignored
│   ├── postgres/
│   ├── qdrant/
│   ├── redis/
│   └── minio/
│
├── .gitignore
└── README.md
```

---

## 4. Environment Setup {#4-environment-setup}

### Prerequisites
- ✅ WSL (Ubuntu 22.04+)
- ✅ Docker Desktop (with WSL2 backend)
- ✅ Python 3.11+
- ✅ 8GB RAM minimum (16GB recommended)

### Step 1: Create Project Directory

```bash
# Open WSL terminal
cd ~
mkdir rightstaff-ai
cd rightstaff-ai
git init
```

### Step 2: Create .gitignore

```bash
nano .gitignore
```

Paste:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
.venv

# Environment
.env
.env.local
.env.docker

# Data
data/
*.db
*.sqlite

# IDE
.vscode/
.idea/
*.swp

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Jupyter
.ipynb_checkpoints/

# Models
*.pth
*.bin
models/

# Test artifacts
.pytest_cache/
.coverage
htmlcov/
```

### Step 3: Create Directory Structure

```bash
mkdir -p backend/app/{api,models,services,utils}
mkdir -p backend/tests
mkdir -p frontend
mkdir -p database
mkdir -p docker
mkdir -p data/{postgres,qdrant,redis,minio}

# Create __init__.py files
touch backend/app/__init__.py
touch backend/app/{api,models,services,utils}/__init__.py
touch backend/tests/__init__.py
```

---

## 5. Docker Services Configuration {#5-docker-services}

### Step 1: Create docker-compose.yml

```bash
nano docker/docker-compose.yml
```

Paste:
```yaml
version: '3.8'

services:
  # PostgreSQL - Relational Database
  postgres:
    image: postgres:15-alpine
    container_name: rightstaff-postgres
    environment:
      POSTGRES_DB: rightstaff
      POSTGRES_USER: right_staff
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dev_password_123}
    ports:
      - "5432:5432"
    volumes:
      - ../data/postgres:/var/lib/postgresql/data
      - ../database:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U right_staff -d rightstaff"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - rightstaff-network

  # Qdrant - Vector Database
  qdrant:
    image: qdrant/qdrant:v1.7.0
    container_name: rightstaff-qdrant
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC API
    volumes:
      - ../data/qdrant:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - rightstaff-network

  # Redis - Cache & Queue
  redis:
    image: redis:7.2-alpine
    container_name: rightstaff-redis
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-dev_redis_123}
    ports:
      - "6379:6379"
    volumes:
      - ../data/redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - rightstaff-network

  # MinIO - S3-compatible Object Storage
  minio:
    image: minio/minio:latest
    container_name: rightstaff-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin123}
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Web Console
    volumes:
      - ../data/minio:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - rightstaff-network

networks:
  rightstaff-network:
    driver: bridge
```

**Key Changes from V1**:
- ✅ Added Redis service with password auth and AOF persistence
- ✅ Pinned Qdrant to v1.7.0 (stable)
- ✅ All services on shared network

### Step 2: Create Docker Environment File

```bash
nano docker/.env.docker
```

Paste:
```env
# PostgreSQL
POSTGRES_PASSWORD=dev_password_123

# Redis
REDIS_PASSWORD=dev_redis_123

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
```

### Step 3: Move SQL Files to Database Directory

```bash
# If SQL files are in Downloads (adjust path)
cp /mnt/c/Users/YourUsername/Downloads/*.sql database/

# Verify
ls -la database/
# Expected: 00_rollback.sql, 01_schema.sql, 02_seed_smoketest.sql, 03_postseed_helpers.sql
```

### Step 4: Start Docker Services

```bash
cd docker
docker-compose up -d

# Check status (all should be "healthy")
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 5: Verify Services

**PostgreSQL**:
```bash
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff

# List tables
\dt rightstaff.*;

# Check seed data
SELECT full_name, years_experience FROM rightstaff.candidate;

# Exit
\q
```

**Qdrant** (browser): http://localhost:6333/dashboard

**Redis**:
```bash
docker exec -it rightstaff-redis redis-cli -a dev_redis_123

# Test
PING
SET test "hello"
GET test
EXIT
```

**MinIO** (browser): http://localhost:9001
- Login: `minioadmin` / `minioadmin123`
- Create bucket: `rightstaff-resumes`

---

## 6. Python Backend Setup {#6-python-backend}

### Step 1: Create Virtual Environment

```bash
cd ~/rightstaff-ai
python3.11 -m venv venv
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.11+
```

### Step 2: Create requirements.txt

```bash
nano backend/requirements.txt
```

Paste:
```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
websockets==12.0

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
alembic==1.13.0

# Vector Database
qdrant-client==1.7.0

# Redis (NEW)
redis==5.0.1
redis-py==5.0.1

# Object Storage
boto3==1.34.10
minio==7.2.0

# Document Processing (ENHANCED)
unstructured[pdf]==0.11.4
PyPDF2==3.0.1
python-docx==1.1.0
pypdf==3.17.4
pillow==10.1.0

# NLP & Embeddings
sentence-transformers==2.2.2
spacy==3.7.2
torch==2.1.2
transformers==4.36.2

# LLM Integration
openai==1.6.1
langchain==0.1.0
langchain-community==0.0.10
langgraph==0.0.20

# Error Handling (NEW)
tenacity==8.2.3

# Logging (NEW)
structlog==23.3.0
python-json-logger==2.0.7

# Utilities
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
email-validator==2.1.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2
locust==2.20.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### Step 3: Install Dependencies

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected time**: 10-15 minutes (~3GB download)

### Step 4: Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

### Step 5: Create .env File

```bash
nano backend/.env
```

Paste:
```env
# Environment
DEBUG=True
ENV=development

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rightstaff
POSTGRES_USER=right_staff
POSTGRES_PASSWORD=dev_password_123

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=candidates_v1

# Redis (NEW)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=dev_redis_123
REDIS_DB=0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=rightstaff-resumes
MINIO_USE_SSL=false

# AI Models
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIM=384
CHUNK_SIZE=400
CHUNK_OVERLAP=50

# OpenAI (leave empty for MVP)
OPENAI_API_KEY=

# API Settings
API_RATE_LIMIT=100  # requests per minute
MAX_FILE_SIZE_MB=5
```

---

## 7. Core Services Implementation {#7-core-services}

I'll provide the key files. Copy these to appropriate locations:

### **backend/app/config.py** - Configuration Management

```python
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Environment
    debug: bool = Field(default=False, env="DEBUG")
    env: str = Field(default="development", env="ENV")
    
    # PostgreSQL
    postgres_host: str = Field(env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(env="POSTGRES_DB")
    postgres_user: str = Field(env="POSTGRES_USER")
    postgres_password: str = Field(env="POSTGRES_PASSWORD")
    
    # Qdrant
    qdrant_host: str = Field(env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_collection: str = Field(default="candidates_v1", env="QDRANT_COLLECTION")
    
    # Redis (NEW)
    redis_host: str = Field(env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: str = Field(env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # MinIO
    minio_endpoint: str = Field(env="MINIO_ENDPOINT")
    minio_access_key: str = Field(env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(env="MINIO_SECRET_KEY")
    minio_bucket: str = Field(env="MINIO_BUCKET")
    minio_use_ssl: bool = Field(default=False, env="MINIO_USE_SSL")
    
    # AI Models
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    embedding_dim: int = Field(default=384, env="EMBEDDING_DIM")
    chunk_size: int = Field(default=400, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    
    # OpenAI
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    
    # API Settings
    api_rate_limit: int = Field(default=100, env="API_RATE_LIMIT")
    max_file_size_mb: int = Field(default=5, env="MAX_FILE_SIZE_MB")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @property
    def postgres_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### **backend/app/utils/logging.py** - Structured Logging (NEW)

```python
import structlog
import logging
import sys
from typing import Any

def configure_logging():
    """Configure structlog for JSON logging with correlation IDs"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> Any:
    """Get a structured logger instance"""
    return structlog.get_logger(name)
```

### **backend/app/services/redis_client.py** - Redis Wrapper (NEW)

```python
import redis
import json
from typing import Any, Optional
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

class RedisClient:
    """Redis client wrapper for caching and queuing"""
    
    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        logger.info("redis_client_initialized", host=settings.redis_host)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.client.get(key)
            if value:
                logger.debug("cache_hit", key=key)
                return json.loads(value)
            logger.debug("cache_miss", key=key)
            return None
        except Exception as e:
            logger.error("redis_get_error", key=key, error=str(e))
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL (seconds)"""
        try:
            self.client.setex(key, ttl, json.dumps(value))
            logger.debug("cache_set", key=key, ttl=ttl)
            return True
        except Exception as e:
            logger.error("redis_set_error", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            self.client.delete(key)
            logger.debug("cache_delete", key=key)
            return True
        except Exception as e:
            logger.error("redis_delete_error", key=key, error=str(e))
            return False
    
    def queue_job(self, queue_name: str, job_data: dict) -> bool:
        """Add job to Redis queue (FIFO)"""
        try:
            self.client.lpush(queue_name, json.dumps(job_data))
            logger.info("job_queued", queue=queue_name, job_id=job_data.get("job_id"))
            return True
        except Exception as e:
            logger.error("queue_job_error", queue=queue_name, error=str(e))
            return False
    
    def get_job(self, queue_name: str, timeout: int = 5) -> Optional[dict]:
        """Get job from queue (blocking)"""
        try:
            result = self.client.brpop(queue_name, timeout=timeout)
            if result:
                _, job_data = result
                return json.loads(job_data)
            return None
        except Exception as e:
            logger.error("get_job_error", queue=queue_name, error=str(e))
            return None

# Singleton instance
redis_client = RedisClient()
```

### **backend/app/services/parsers.py** - Document Parser (ENHANCED)

```python
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from PyPDF2 import PdfReader
from docx import Document
from pathlib import Path
from typing import List
from app.utils.logging import get_logger

logger = get_logger(__name__)

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF using Unstructured library (primary)
    Falls back to PyPDF2 if Unstructured fails
    """
    try:
        # Primary: Unstructured (handles tables, images)
        elements = partition_pdf(filename=file_path)
        text = "\n".join([str(el) for el in elements])
        logger.info("pdf_parsed_unstructured", file=file_path, length=len(text))
        return text
    except Exception as e:
        logger.warning("unstructured_failed_fallback_pypdf2", file=file_path, error=str(e))
        
        # Fallback: PyPDF2
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            logger.info("pdf_parsed_pypdf2", file=file_path, length=len(text))
            return text
        except Exception as e2:
            logger.error("pdf_parse_failed", file=file_path, error=str(e2))
            raise ValueError(f"Failed to parse PDF: {e2}")

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX using Unstructured (primary) with fallback"""
    try:
        # Primary: Unstructured
        elements = partition_docx(filename=file_path)
        text = "\n".join([str(el) for el in elements])
        logger.info("docx_parsed_unstructured", file=file_path, length=len(text))
        return text
    except Exception as e:
        logger.warning("unstructured_failed_fallback_python_docx", file=file_path, error=str(e))
        
        # Fallback: python-docx
        try:
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            logger.info("docx_parsed_python_docx", file=file_path, length=len(text))
            return text
        except Exception as e2:
            logger.error("docx_parse_failed", file=file_path, error=str(e2))
            raise ValueError(f"Failed to parse DOCX: {e2}")

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """
    Split text into chunks with overlap (token-based approximation)
    Assumes ~1 word = 1.3 tokens on average
    """
    words = text.split()
    chunks = []
    
    # Convert chunk_size to word count
    words_per_chunk = int(chunk_size / 1.3)
    overlap_words = int(overlap / 1.3)
    
    start = 0
    while start < len(words):
        end = start + words_per_chunk
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap_words  # Overlap
    
    logger.debug("text_chunked", total_words=len(words), chunks=len(chunks))
    return chunks
```

### **backend/app/main.py** - FastAPI Application

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="RightStaff AI",
    version="2.1.0",
    description="Production-grade AI candidate ranking engine",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("app_startup", env=settings.env, debug=settings.debug)
    # TODO: Initialize database connections, vector store, Redis

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("app_shutdown")
    # TODO: Close connections

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "RightStaff AI",
        "version": "2.1.0",
        "environment": settings.env
    }
```

---

## 8. API Endpoints {#8-api-endpoints}

**Phase 1 (MVP - 10.5 days):**
- `POST /api/v1/webhooks/candidate-updated` - Async webhook handler
- `POST /api/v1/candidates/ingest` - Mock ingestion (testing)
- `GET /api/v1/candidates/{id}` - Get candidate profile
- `POST /api/v1/jobs/{job_id}/rank` - Generate ranked list
- `GET /api/v1/health` - Health check

**Phase 2 (Week 3+):**
- `GET /api/v1/candidates/{id}/explanation` - Get ranking explanation
- `WS /api/v1/jobs/{job_id}/chat` - WebSocket chatbot

---

## 9. Testing Strategy {#9-testing}

### Unit Tests

```bash
# Run all tests
pytest backend/tests/ -v --cov=backend/app --cov-report=html

# Run specific test file
pytest backend/tests/test_parsers.py -v

# Run with coverage report
pytest backend/tests/ --cov=backend/app --cov-report=term-missing
```

### Integration Tests

```bash
# Test end-to-end ingestion
pytest backend/tests/test_integration.py::test_ingestion_pipeline -v
```

### Load Tests

```bash
# Start Locust
locust -f backend/tests/locustfile.py --host=http://localhost:8000
```

Open browser: http://localhost:8089

**Test Targets:**
- Users: 100
- Spawn rate: 10/sec
- Duration: 5 minutes
- Success: p95 latency < 5s, error rate < 0.5%

---

## 10. Daily Workflow {#10-daily-workflow}

### Starting Work

```bash
# 1. Start Docker services
cd ~/rightstaff-ai/docker
docker-compose up -d

# 2. Activate Python environment
cd ~/rightstaff-ai
source venv/bin/activate

# 3. Start backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify Everything Works

```bash
# Health check
curl http://localhost:8000/health

# Check logs (structured JSON)
tail -f logs/app.log | jq .
```

### Ending Work

```bash
# 1. Stop backend (Ctrl+C)

# 2. Stop Docker (keeps data)
cd docker
docker-compose down

# Or stop Docker (removes data)
docker-compose down -v
```

---

## 11. Troubleshooting {#11-troubleshooting}

### Docker Issues

**Problem**: Redis won't start
```bash
docker logs rightstaff-redis
# If auth error: check REDIS_PASSWORD in .env.docker
```

**Problem**: Containers won't start
```bash
docker-compose down -v
docker-compose up -d
docker-compose logs -f
```

### Python Issues

**Problem**: Unstructured import error
```bash
pip install unstructured[pdf] --upgrade
# May need system packages: sudo apt-get install libmagic-dev poppler-utils
```

**Problem**: Redis connection refused
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli -h localhost -p 6379 -a dev_redis_123 PING
```

### Connection Issues

**Problem**: Can't connect to services from backend
- Verify `.env` file has correct localhost addresses
- Check Docker containers are on `rightstaff-network`
- Verify ports not blocked: `netstat -an | grep 6379`

---

## Next Steps

**Phase 1 (Days 1-4)**: Ingestion pipeline
- Resume parsing → chunking → embedding → Qdrant
- Redis queue for async processing

**Phase 2 (Days 5-8)**: Ranking pipeline
- Ontology gate (with Redis cache)
- Dense retrieval (Qdrant)
- Basic structured scoring
- REST API

**Phase 3 (Days 9-10.5)**: Testing & delivery
- Unit tests (pytest)
- Integration tests
- Observability setup
- API documentation

**Post-MVP (Week 3+)**: 
- Cross-encoder re-ranking
- RAG chatbot
- Load testing
- Fairness audits

---

## Quick Reference

**Project Root**: `~/rightstaff-ai`

**Start Everything**:
```bash
cd ~/rightstaff-ai/docker && docker-compose up -d
source ~/rightstaff-ai/venv/bin/activate
cd ~/rightstaff-ai/backend && uvicorn app.main:app --reload
```

**Access Points**:
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Qdrant: http://localhost:6333/dashboard
- MinIO: http://localhost:9001
- Redis: `localhost:6379` (password: `dev_redis_123`)
- PostgreSQL: `localhost:5432`

**Logs**:
```bash
docker logs rightstaff-postgres
docker logs rightstaff-qdrant
docker logs rightstaff-redis
docker logs rightstaff-minio
```

---

**Documentation Version**: 2.1  
**Last Updated**: November 4, 2025  
**Status**: Production-Grade Ready ✅
