# 🚀 RightStaff AI Backend - Complete Automated Setup Prompt for Claude Code

## CONTEXT
You are setting up the **RightStaff AI Backend** - a production-grade, AI-powered candidate ranking engine. This is the **AI Team's** portion of a larger project. The **Portal Team** manages the frontend and relational database, but you'll simulate their parts temporarily using a "Test Harness" approach.

**Project Goals:**
- Learn Senior AI Engineering skills (primary)
- Build a complete, deployable AI backend (secondary)
- Timeline: 10.5 days (MVP scope)

**Tech Stack (MVP):**
- **Backend**: FastAPI (Python 3.11+)
- **Databases**: PostgreSQL 15 (relational), Qdrant v1.7.0 (vectors), Redis 7.2 (cache/queue), MinIO (S3-compatible storage)
- **AI/ML**: sentence-transformers, spaCy, Unstructured (parsing)
- **Deployment**: Docker Compose (local), production-ready architecture

---

## AUTOMATED SETUP TASKS

### ⚙️ TASK 1: Create Project Structure

Create the following directory structure from scratch:

```
rightstaff-ai/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py
│   │   │   ├── ranking.py
│   │   │   ├── chatbot.py
│   │   │   ├── vector_store.py
│   │   │   ├── redis_client.py
│   │   │   └── parsers.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── webhooks.py
│   │   │   ├── candidates.py
│   │   │   ├── jobs.py
│   │   │   └── chat.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── skills.py
│   │       └── logging.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_parsers.py
│   │   ├── test_skills.py
│   │   ├── test_vector_store.py
│   │   ├── test_ranking.py
│   │   ├── test_fairness.py
│   │   └── locustfile.py
│   ├── requirements.txt
│   ├── .env
│   └── pytest.ini
├── frontend/
│   └── index.html
├── database/
│   └── (SQL files will be placed here manually)
├── docker/
│   ├── docker-compose.yml
│   └── .env.docker
├── data/
│   ├── postgres/
│   ├── qdrant/
│   ├── redis/
│   └── minio/
├── .gitignore
├── .dockerignore
├── README.md
└── Makefile
```

### 📝 TASK 2: Create Configuration Files

#### **File: .gitignore**
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

# Docker
docker-compose.override.yml
```

#### **File: .dockerignore**
```dockerignore
**/__pycache__
**/.venv
**/.git
**/.gitignore
**/.dockerignore
**/venv
**/.pytest_cache
**/.coverage
**/htmlcov
**/*.pyc
**/*.pyo
**/*.pyd
.Python
*.log
data/
```

#### **File: docker/docker-compose.yml**
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

#### **File: docker/.env.docker**
```env
# PostgreSQL
POSTGRES_PASSWORD=dev_password_123

# Redis
REDIS_PASSWORD=dev_redis_123

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
```

#### **File: backend/.env**
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

# Redis
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
API_RATE_LIMIT=100
MAX_FILE_SIZE_MB=5
```

#### **File: backend/requirements.txt**
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

# Redis
redis==5.0.1

# Object Storage
boto3==1.34.10
minio==7.2.0

# Document Processing
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

# Error Handling
tenacity==8.2.3

# Logging
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

#### **File: backend/pytest.ini**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    -ra
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
```

#### **File: Makefile**
```makefile
.PHONY: help setup start stop restart logs clean test install

help:
	@echo "RightStaff AI Backend - Available Commands:"
	@echo "  make setup     - Initial project setup"
	@echo "  make start     - Start all Docker services"
	@echo "  make stop      - Stop Docker services (keep data)"
	@echo "  make restart   - Restart Docker services"
	@echo "  make logs      - View Docker logs"
	@echo "  make clean     - Remove all data (WARNING: destructive)"
	@echo "  make install   - Install Python dependencies"
	@echo "  make test      - Run pytest suite"

venv:
	@echo "🐍 Creating virtual environment..."
	python -m venv venv
	@echo "✅ Virtual environment created!"
	@echo "👉 Activate with: source venv/bin/activate (Linux/Mac) or venv\Scripts\activate (Windows)"

setup:
	@echo "🚀 Setting up RightStaff AI Backend..."
	@if [ ! -d "venv" ]; then \
		echo "⚠️  No virtual environment detected!"; \
		echo "👉 Run 'make venv' first, then activate it."; \
		exit 1; \
	fi
	cd docker && docker-compose up -d
	@echo "⏳ Waiting for services to be healthy..."
	sleep 10
	cd backend && pip install -r requirements.txt
	python -m spacy download en_core_web_sm
	@echo "✅ Setup complete!"

start:
	cd docker && docker-compose up -d

stop:
	cd docker && docker-compose down

restart:
	cd docker && docker-compose restart

logs:
	cd docker && docker-compose logs -f

clean:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd docker && docker-compose down -v; \
		rm -rf data/*; \
		echo "✅ All data deleted"; \
	fi

install:
	@if [ ! -d "venv" ]; then \
		echo "⚠️  Please create and activate virtual environment first"; \
		echo "   make venv"; \
		echo "   source venv/bin/activate"; \
		exit 1; \
	fi
	cd backend && pip install -r requirements.txt
	python -m spacy download en_core_web_sm

test:
	cd backend && pytest tests/ -v --cov=app --cov-report=html
```

---

### 🐍 TASK 3: Create Core Python Files

#### **File: backend/app/config.py**
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
    
    # Redis
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

#### **File: backend/app/utils/logging.py**
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

#### **File: backend/app/services/redis_client.py**
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

#### **File: backend/app/services/parsers.py**
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

#### **File: backend/app/main.py**
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

### 📄 TASK 4: Create README.md

#### **File: README.md**
```markdown
# 🚀 RightStaff AI Backend

Production-grade AI candidate ranking engine with explainable results and RAG-powered chatbot.

## 🎯 Features

- **Semantic Candidate Ranking**: Vector-based similarity search with ontology gating
- **Explainable Results**: Every ranking includes citations to evidence chunks
- **RAG Chatbot**: Job-scoped Q&A grounded in candidate data
- **Webhook Integration**: Async processing via Redis queues
- **Production-Ready**: Structured logging, health checks, comprehensive testing

## 🏗️ Architecture

```
Portal Team → Webhook → AI Team (This Repo)
                 ↓
           [Redis Queue]
                 ↓
    Resume → Parse → Chunk → Embed → Qdrant
                                      ↓
              Job Description → Rank Candidates
                                      ↓
                          Explainable Results + Chatbot
```

## 🛠️ Tech Stack

**MVP:**
- FastAPI, PostgreSQL 15, Qdrant v1.7.0, Redis 7.2, MinIO
- sentence-transformers, spaCy, Unstructured (parsing)
- Docker Compose

**Production:**
- Pinecone (vector DB), AWS S3, ElastiCache (Redis)
- OpenAI embeddings, Kubernetes/ECS

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (with WSL2 backend)
- Python 3.11+
- 8GB RAM (16GB recommended)

### Setup

```bash
# Clone repository
git clone <repo-url>
cd rightstaff-ai

# Start all services (Docker + Python setup)
make setup

# Start backend server
cd backend
source ../venv/bin/activate  # On Windows: ..\venv\Scripts\activate
uvicorn app.main:app --reload
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Access points
- API Docs: http://localhost:8000/docs
- Qdrant Dashboard: http://localhost:6333/dashboard
- MinIO Console: http://localhost:9001
```

## 📋 Available Commands

```bash
make help      # Show all commands
make start     # Start Docker services
make stop      # Stop Docker services
make logs      # View Docker logs
make test      # Run pytest suite
make clean     # Remove all data (destructive)
```

## 📚 Documentation

- [Setup Guide](docs/SETUP.md)
- [API Documentation](http://localhost:8000/docs)
- [Architecture](docs/ARCHITECTURE.md)
- [Testing Strategy](docs/TESTING.md)

## 🧪 Testing

```bash
# Run all tests
pytest backend/tests/ -v --cov=backend/app --cov-report=html

# Run specific test category
pytest -m unit
pytest -m integration

# Load testing
locust -f backend/tests/locustfile.py --host=http://localhost:8000
```

## 📊 Success Metrics

- **Ranking Quality**: Agent thumbs-up rate ≥80%
- **Performance**: p95 latency <5s (ranking), <2.5s (chatbot)
- **Cost**: $0 (MVP), <$0.03/run (production)
- **Fairness**: Zero correlation with protected attributes

## 🔒 Security & Compliance

- PII redaction in logs and vector metadata
- Read-only PostgreSQL access for AI team
- Exclude candidate_demographics from ranking
- Audit trails for all operations

## 🗺️ Roadmap

**Phase 1 (MVP - Days 1-10):**
- ✅ Docker environment
- ✅ Resume ingestion pipeline
- ✅ Basic ranking (ontology gate + dense retrieval)
- ✅ REST API

**Phase 2 (Weeks 2-3):**
- Cross-encoder re-ranking
- RAG chatbot with WebSocket
- Comprehensive testing

**Phase 3 (Weeks 4+):**
- Migration to Pinecone + OpenAI embeddings
- Production deployment (Kubernetes)
- Portal team integration

## 🤝 Contributing

This is a learning project. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

MIT License - See [LICENSE](LICENSE)

## 🙏 Acknowledgments

Built as part of a Senior AI Engineering learning path.
```

---

### 🎨 TASK 5: Create Simple Frontend (Mock UI)

#### **File: frontend/index.html**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RightStaff - Candidate Upload (Test Harness)</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 600px;
            margin: 40px auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }
        
        input[type="text"],
        input[type="email"],
        input[type="number"],
        input[type="file"],
        select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        input:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .checkbox-group {
            display: flex;
            gap: 20px;
            margin-top: 10px;
        }
        
        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
        }
        
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .result {
            margin-top: 20px;
            padding: 16px;
            border-radius: 8px;
            display: none;
        }
        
        .result.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .result.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 RightStaff AI</h1>
        <p class="subtitle">Candidate Upload Test Harness (AI Team Internal Use Only)</p>
        
        <form id="candidateForm">
            <!-- Resume Upload -->
            <div class="form-group">
                <label for="resume">Resume (PDF/DOCX) *</label>
                <input type="file" id="resume" name="resume" accept=".pdf,.docx" required>
            </div>
            
            <!-- Personal Info -->
            <div class="form-group">
                <label for="full_name">Full Name *</label>
                <input type="text" id="full_name" name="full_name" required placeholder="Jane Doe">
            </div>
            
            <div class="form-group">
                <label for="email">Email *</label>
                <input type="email" id="email" name="email" required placeholder="jane@example.com">
            </div>
            
            <div class="form-group">
                <label for="phone">Phone</label>
                <input type="text" id="phone" name="phone" placeholder="+1 (555) 123-4567">
            </div>
            
            <!-- Location -->
            <div class="form-group">
                <label for="city">City *</label>
                <input type="text" id="city" name="city" required placeholder="Austin">
            </div>
            
            <div class="form-group">
                <label for="region">State/Region *</label>
                <input type="text" id="region" name="region" required placeholder="TX">
            </div>
            
            <!-- Experience -->
            <div class="form-group">
                <label for="years_experience">Years of Experience *</label>
                <input type="number" id="years_experience" name="years_experience" min="0" max="50" required placeholder="5">
            </div>
            
            <!-- Preferences -->
            <div class="form-group">
                <label for="salary">Salary Requirement (USD)</label>
                <input type="number" id="salary" name="salary" min="0" placeholder="120000">
            </div>
            
            <div class="form-group">
                <label>Preferences</label>
                <div class="checkbox-group">
                    <div class="checkbox-item">
                        <input type="checkbox" id="open_to_remote" name="open_to_remote">
                        <label for="open_to_remote" style="margin: 0;">Open to Remote</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="visa_sponsorship" name="visa_sponsorship">
                        <label for="visa_sponsorship" style="margin: 0;">Needs Visa Sponsorship</label>
                    </div>
                </div>
            </div>
            
            <button type="submit" id="submitBtn">Upload Candidate</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 10px; color: #666;">Processing resume...</p>
        </div>
        
        <div class="result" id="result"></div>
    </div>

    <script>
        const form = document.getElementById('candidateForm');
        const submitBtn = document.getElementById('submitBtn');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Reset UI
            submitBtn.disabled = true;
            loading.style.display = 'block';
            result.style.display = 'none';
            
            // Gather form data
            const formData = new FormData();
            formData.append('resume', document.getElementById('resume').files[0]);
            formData.append('full_name', document.getElementById('full_name').value);
            formData.append('email', document.getElementById('email').value);
            formData.append('phone', document.getElementById('phone').value || '');
            formData.append('city', document.getElementById('city').value);
            formData.append('region', document.getElementById('region').value);
            formData.append('years_experience', document.getElementById('years_experience').value);
            formData.append('salary_requirement_amount', document.getElementById('salary').value || '0');
            formData.append('open_to_remote', document.getElementById('open_to_remote').checked);
            formData.append('visa_sponsorship_required_at_hire', document.getElementById('visa_sponsorship').checked);
            
            try {
                const response = await fetch('http://localhost:8000/api/v1/candidates/ingest', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    result.className = 'result success';
                    result.innerHTML = `
                        <strong>✅ Success!</strong><br>
                        Candidate ID: ${data.candidate_id}<br>
                        Vectors Created: ${data.vectors_created}<br>
                        Processing Time: ${data.processing_time_seconds?.toFixed(2)}s
                    `;
                } else {
                    throw new Error(data.detail || 'Upload failed');
                }
            } catch (error) {
                result.className = 'result error';
                result.innerHTML = `
                    <strong>❌ Error</strong><br>
                    ${error.message}
                `;
            } finally {
                loading.style.display = 'none';
                result.style.display = 'block';
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
```

---

## ✅ EXECUTION CHECKLIST

After running this prompt, verify:

1. **Directory Structure**: All folders and files created
2. **Docker Services**: `cd docker && docker-compose up -d` (all 4 services healthy)
3. **Python Environment**: `cd backend && pip install -r requirements.txt` (no errors)
4. **spaCy Model**: `python -m spacy download en_core_web_sm` (success)
5. **Backend Server**: `uvicorn app.main:app --reload` (starts without errors)
6. **Health Check**: `curl http://localhost:8000/health` (returns JSON)
7. **API Docs**: http://localhost:8000/docs (Swagger UI loads)
8. **Qdrant**: http://localhost:6333/dashboard (dashboard loads)
9. **MinIO**: http://localhost:9001 (login works)
10. **Redis**: `docker exec -it rightstaff-redis redis-cli -a dev_redis_123 PING` (returns PONG)

---

## 📝 NOTES FOR CLAUDE CODE

- **SQL Files**: User will manually place SQL files in `database/` directory
- **Placeholder Files**: `ranking.py`, `chatbot.py`, `database.py`, `skills.py`, `webhooks.py`, `jobs.py`, `chat.py`, and test files should be created as empty files with TODO comments for now
- **Error Handling**: Add tenacity retry decorators in Phase 2
- **Testing**: Test files will be implemented in Phase 2
- **Mock UI**: Serves from FastAPI static route (add route in main.py)

---

## 🎯 SUCCESS CRITERIA

After running this prompt, you should have:
- ✅ Complete project structure
- ✅ All Docker services running
- ✅ Python environment configured
- ✅ Basic FastAPI app with health check
- ✅ Core utilities (logging, Redis, parsing) implemented
- ✅ Mock UI for testing candidate ingestion
- ✅ Makefile for common commands
- ✅ Comprehensive README

**Estimated Time**: 10-15 minutes for Claude Code to generate all files
**Next Steps**: User will add SQL files, then we implement ranking pipeline (Phase 2)
