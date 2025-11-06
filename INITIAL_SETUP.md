# 🚀 RightStaff AI Backend - Complete Automated Setup Prompt for Claude Code (CORRECTED)

## CONTEXT
You are setting up the **RightStaff AI Backend** - a production-grade, AI-powered candidate ranking engine. This is the **AI Team's** portion of a larger project. The **Portal Team** manages the frontend and relational database, but you'll simulate their parts temporarily using a "Test Harness" approach.

**Project Goals:**
- Learn Senior AI Engineering skills (primary)
- Build a complete, deployable AI backend (secondary)
- Timeline: **14 days (2 weeks) for complete MVP including cross-encoder re-ranking and WebSocket chatbot**

**Tech Stack (MVP):**
- **Backend**: FastAPI (Python 3.11+)
- **Databases**: PostgreSQL 18 (relational), Qdrant v1.7.0 (vectors), Redis 7.2 (cache/queue), MinIO (S3-compatible storage)
- **AI/ML**: sentence-transformers (includes CrossEncoder for re-ranking), spaCy, Unstructured (parsing), bge-reranker-base
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
    image: postgres:18-alpine
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

# Cross-Encoder for Re-ranking (MVP)
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# OpenAI (for production or optional MVP enhancement)
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

**NOTE**: `sentence-transformers` includes `CrossEncoder` functionality for pairwise re-ranking. No additional packages needed for cross-encoder re-ranking in MVP.

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

[Same as before: config.py, logging.py, redis_client.py, parsers.py, main.py]

*(Keeping these files identical to maintain consistency - they're already correct)*

---

### 📄 TASK 4: Create README.md (CORRECTED)

#### **File: README.md**
```markdown
# 🚀 RightStaff AI Backend

Production-grade AI candidate ranking engine with explainable results, cross-encoder re-ranking, and RAG-powered WebSocket chatbot.

## 🎯 Features (MVP - All Included in 14-Day Timeline)

- **Semantic Candidate Ranking**: Vector-based similarity search with ontology gating
- **Cross-Encoder Re-Ranking**: Pairwise scoring using bge-reranker-base for improved accuracy
- **Explainable Results**: Every ranking includes citations to evidence chunks
- **RAG Chatbot with WebSocket**: Job-scoped Q&A grounded in candidate data with real-time streaming
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
    Job Description → Semantic Search → Cross-Encoder Re-Rank
                                      ↓
                   Explainable Results + WebSocket Chatbot
```

## 🛠️ Tech Stack

**MVP (Complete in 14 Days):**
- FastAPI, PostgreSQL 18, Qdrant v1.7.0, Redis 7.2, MinIO
- sentence-transformers (embeddings + CrossEncoder re-ranking), spaCy, Unstructured (parsing)
- WebSocket support for real-time chatbot
- Docker Compose

**Production (Post-MVP):**
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

## 🗺️ MVP Roadmap (14-Day Timeline)

**Days 1-4: Foundation**
- ✅ Docker environment setup
- ✅ Resume ingestion pipeline (parse, chunk, embed)
- ✅ Vector database (Qdrant) integration
- ✅ Redis queue for webhooks

**Days 5-8: Core Ranking**
- ✅ Ontology gate (must-have skills)
- ✅ Dense retrieval (semantic search)
- ✅ Structured scoring (years, recency, location)
- ✅ Redis caching for performance

**Days 9-12: Advanced Features (IN MVP)**
- ✅ **Cross-encoder re-ranking** (pairwise scoring with bge-reranker-base)
- ✅ **WebSocket chatbot** (job-scoped RAG with streaming)
- ✅ Explanation generation with citations
- ✅ Email drafting functionality

**Days 13-14: Testing & Delivery**
- ✅ Comprehensive testing (unit, integration, fairness)
- ✅ Structured logging and observability
- ✅ API documentation
- ✅ Internal demo and handoff to Portal team

## 🚀 Post-MVP (Weeks 3+)

- Migration to Pinecone + OpenAI embeddings
- Production deployment (Kubernetes/AWS)
- Portal team frontend integration
- Adaptive learning from agent feedback
- Multi-job matching (reverse ranking)
- Interview scheduling integration

## 🤝 Contributing

This is a learning project. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

MIT License - See [LICENSE](LICENSE)

## 🙏 Acknowledgments

Built as part of a Senior AI Engineering learning path.
```

---

### 🎨 TASK 5: Create Simple Frontend (Mock UI)

[Same as before - no changes needed for the HTML file]

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
- **Placeholder Files**: `ranking.py`, `chatbot.py`, `database.py`, `skills.py`, `webhooks.py`, `jobs.py`, `chat.py` should be created with detailed TODO comments indicating they are MVP features (Days 5-12)
- **Cross-Encoder Implementation**: Will use sentence-transformers' `CrossEncoder` class (no additional packages needed)
- **WebSocket Implementation**: FastAPI's built-in WebSocket support (already in requirements)
- **Testing**: Test files will be implemented during Days 13-14

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
- ✅ **Comprehensive README with correct 14-day timeline**

**Estimated Time**: 10-15 minutes for Claude Code to generate all files
**Next Steps**: User will add SQL files, then implement ranking pipeline (Days 5-8), then cross-encoder re-ranking (Days 9-10), then WebSocket chatbot (Days 11-12)

---

## 🔑 KEY CHANGES FROM PREVIOUS VERSION

1. **README Timeline Corrected**: Cross-encoder and WebSocket chatbot are now explicitly in the 14-day MVP roadmap (Days 9-12)
2. **Environment Variables**: Added `RERANKER_MODEL` to .env for clarity
3. **Requirements Note**: Clarified that sentence-transformers includes CrossEncoder functionality
4. **Roadmap**: Detailed 14-day breakdown with all features clearly in scope

**CRITICAL**: The PRD document already had this correct - only the setup automation prompt's README was wrong!
