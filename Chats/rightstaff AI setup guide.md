# RightStaff AI Backend - Complete Setup Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Understanding the SQL Files](#understanding-sql-files)
3. [Project Structure](#project-structure)
4. [Environment Setup](#environment-setup)
5. [Docker Services Configuration](#docker-services)
6. [Python Backend Setup](#python-backend)
7. [Core Services Implementation](#core-services)
8. [API Endpoints](#api-endpoints)
9. [Frontend Test Harness](#frontend-test-harness)
10. [Testing the System](#testing)
11. [Daily Workflow](#daily-workflow)
12. [Troubleshooting](#troubleshooting)

---

## 1. Project Overview {#project-overview}

**RightStaff** is an AI-powered staffing platform that matches candidates to jobs using:
- **Semantic Search**: Vector embeddings for similarity matching
- **Explainable Ranking**: Transparent scoring with citations
- **RAG Chatbot**: Grounded Q&A about candidates

**Your Role**: Build the AI Team's backend services (ingestion, ranking, chatbot)

**Tech Stack**:
- **Backend**: FastAPI (Python)
- **Databases**: PostgreSQL (relational), Qdrant (vectors), MinIO (files)
- **AI/ML**: sentence-transformers, spaCy, LangChain
- **Deployment**: Docker Compose (local), Kubernetes (production)

---

## 2. Understanding the SQL Files {#understanding-sql-files}

Your teammate provided 4 SQL files:

### **00_rollback.sql**
- **Purpose**: Complete database reset
- **When to use**: If you need to start fresh
- **What it does**: Drops all tables, types, schema, and roles in reverse dependency order

### **01_schema.sql**
- **Purpose**: Creates the complete database structure
- **What it does**:
  - Creates `rightstaff` schema
  - Defines enums (job_status, application_status, etc.)
  - Creates 20+ tables (candidates, skills, jobs, applications)
  - Sets up foreign keys, indexes, constraints
  - Adds triggers for auto-updating timestamps
- **This is the foundation**: Everything else builds on this

### **02_seed_smoketest.sql**
- **Purpose**: Adds test data and validates schema
- **What it does**:
  - Inserts sample candidate (Prathyusha Elipay)
  - Creates test skills, interests, jobs
  - Runs constraint tests (duplicates, cascades)
  - Shows example queries
- **Use this**: To verify database is working correctly

### **03_postseed_helpers.sql**
- **Purpose**: Utility functions
- **What it does**: Adds `set_latest_resume()` function to safely update which resume is "current"

**How They're Used**:
- Placed in `database/` folder
- Auto-executed by PostgreSQL Docker container on first startup (via volume mount)
- Run in alphabetical order (00 → 01 → 02 → 03)

---

## 3. Project Structure {#project-structure}

```
rightstaff-ai/
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── config.py                # Configuration management
│   │   ├── database.py              # PostgreSQL connection
│   │   ├── models/                  # Pydantic models (request/response)
│   │   │   └── __init__.py
│   │   ├── services/                # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py        # Resume processing & embedding
│   │   │   ├── ranking.py           # Candidate ranking (Phase 2)
│   │   │   ├── chatbot.py           # RAG chatbot (Phase 3)
│   │   │   └── vector_store.py      # Qdrant operations
│   │   ├── api/                     # API routes
│   │   │   ├── __init__.py
│   │   │   ├── candidates.py        # Candidate CRUD + ingestion
│   │   │   ├── jobs.py              # Job ranking (placeholder)
│   │   │   └── chat.py              # WebSocket chatbot (placeholder)
│   │   └── utils/                   # Helper functions
│   │       ├── __init__.py
│   │       ├── parsers.py           # PDF/DOCX parsing (future)
│   │       └── skills.py            # Skill extraction
│   ├── tests/                       # Unit/integration tests
│   │   └── __init__.py
│   ├── requirements.txt             # Python dependencies
│   └── .env                         # Environment variables
│
├── frontend/                         # Simple test UI
│   └── index.html                   # Candidate submission form
│
├── database/                         # SQL files (provided by teammate)
│   ├── 00_rollback.sql
│   ├── 01_schema.sql
│   ├── 02_seed_smoketest.sql
│   └── 03_postseed_helpers.sql
│
├── docker/                           # Docker configuration
│   ├── docker-compose.yml           # All services definition
│   └── .env.docker                  # Docker environment variables
│
├── data/                            # Local data (gitignored)
│   ├── postgres/                    # PostgreSQL data
│   ├── qdrant/                      # Qdrant vector storage
│   └── minio/                       # Resume files
│
├── .gitignore
└── README.md
```

---

## 4. Environment Setup {#environment-setup}

### Prerequisites
- ✅ WSL (Ubuntu)
- ✅ Docker Desktop
- ✅ Python 3.10+
- ✅ Node.js (for future frontend work)
- ✅ PostgreSQL 18 (not needed locally, runs in Docker)

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
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
.venv

# Environment variables
.env
.env.local
.env.docker

# Data directories
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

# Model files
*.pth
*.bin
models/
```

Save: Ctrl+O, Enter, Ctrl+X

### Step 3: Create Directory Structure

```bash
mkdir -p backend/app/{api,models,services,utils}
mkdir -p frontend
mkdir -p database
mkdir -p docker
mkdir -p data/{postgres,qdrant,minio}
mkdir -p tests

# Create __init__.py files
touch backend/app/__init__.py
touch backend/app/{api,models,services,utils}/__init__.py
```

---

## 5. Docker Services Configuration {#docker-services}

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
    image: qdrant/qdrant:latest
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

**What each service does**:
- **PostgreSQL**: Stores candidate profiles, skills, jobs (structured data from SQL files)
- **Qdrant**: Stores vector embeddings for semantic search
- **MinIO**: Stores resume PDF/DOCX files (S3-compatible, local)

### Step 2: Create Docker Environment File

```bash
nano docker/.env.docker
```

Paste:
```env
# PostgreSQL
POSTGRES_PASSWORD=dev_password_123

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

# Check status
docker-compose ps
```

**Expected output**:
```
NAME                    STATUS          PORTS
rightstaff-postgres     Up 10 seconds   0.0.0.0:5432->5432/tcp
rightstaff-qdrant       Up 10 seconds   0.0.0.0:6333->6333/tcp
rightstaff-minio        Up 10 seconds   0.0.0.0:9000->9000/tcp
```

### Step 5: Verify Services

**PostgreSQL**:
```bash
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff

# List tables
\dt rightstaff.*

# Check seed data
SELECT full_name, years_experience FROM rightstaff.candidate;

# Exit
\q
```

**Qdrant** (browser): http://localhost:6333/dashboard

**MinIO** (browser): http://localhost:9001
- Login: `minioadmin` / `minioadmin123`
- Create bucket: `rightstaff-resumes`

---

## 6. Python Backend Setup {#python-backend}

### Step 1: Create Virtual Environment

```bash
cd ~/rightstaff-ai
python3 -m venv venv
source venv/bin/activate
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

# Object Storage
boto3==1.34.10
minio==7.2.0

# Document Processing
PyPDF2==3.0.1
python-docx==1.1.0
pypdf==3.17.4

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

# Utilities
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
email-validator==2.1.0
structlog==23.3.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# CORS
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

**Takes 5-10 minutes** (~2GB download)

### Step 4: Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

### Step 5: Create Configuration Files

**backend/app/config.py** - See artifact `fastapi_main` section
**backend/app/database.py** - Database connection utilities
**backend/.env** - Environment variables

```bash
nano backend/.env
```

Paste:
```env
DEBUG=True

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rightstaff
POSTGRES_USER=right_staff
POSTGRES_PASSWORD=dev_password_123

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=rightstaff-resumes

# OpenAI (leave empty for now)
OPENAI_API_KEY=
```

---

## 7. Core Services Implementation {#core-services}

All code artifacts are provided above. Copy them to appropriate files:

1. **backend/app/main.py** - FastAPI application
2. **backend/app/config.py** - Configuration management
3. **backend/app/database.py** - Database connection
4. **backend/app/services/vector_store.py** - Qdrant operations
5. **backend/app/services/ingestion.py** - Resume processing
6. **backend/app/utils/skills.py** - Skill extraction
7. **backend/app/api/candidates.py** - Candidate endpoints
8. **backend/app/api/jobs.py** - Job ranking (placeholder)
9. **backend/app/api/chat.py** - Chatbot (placeholder)

---

## 8. API Endpoints {#api-endpoints}

### Candidate Ingestion
```
POST /api/v1/candidates/ingest
Content-Type: multipart/form-data

Parameters:
- resume (file): PDF/DOCX
- full_name (string, required)
- email (string, required)
- phone, city, region, years_experience, etc.

Response:
{
  "candidate_id": "uuid",
  "status": "success",
  "vectors_created": 15,
  "resume_s3_url": "s3://...",
  "processing_time_seconds": 3.4
}
```

### Get Candidate Profile
```
GET /api/v1/candidates/{candidate_id}

Response:
{
  "candidate_id": "uuid",
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "skills": [{"name": "Python", "level": "advanced", "years": 3.5}],
  ...
}
```

### Get Vector Info
```
GET /api/v1/candidates/{candidate_id}/vectors

Response:
{
  "candidate_id": "uuid",
  "total_vectors": 15,
  "breakdown": {"profile": 1, "skills": 1, "chunks": 13}
}
```

### Job Ranking (Placeholder)
```
POST /api/v1/jobs/{job_id}/rank

Request:
{
  "run_id": "uuid",
  "filters": {"min_years_experience": 3}
}

Response:
{
  "job_id": "uuid",
  "ranked_candidates": [...]
}
```

### Chatbot WebSocket (Placeholder)
```
WS /api/v1/jobs/{job_id}/chat

Client → Server:
{"message": "Does candidate X have AWS certification?"}

Server → Client:
{
  "response": "Yes, candidate has AWS Solutions Architect...",
  "citations": ["chunk_15"],
  "confidence": 0.92
}
```

### Health Check
```
GET /health

Response:
{
  "status": "healthy",
  "app": "RightStaff AI",
  "database": "connected",
  "vector_db": "connected"
}
```

---

## 9. Frontend Test Harness {#frontend-test-harness}

Create **frontend/index.html** - See artifact `simple_frontend`

**Features**:
- Resume upload (PDF/DOCX)
- Candidate profile form (Workday-style)
- Real-time submission to backend API
- Success/error feedback
- Mobile responsive

**Access**: http://localhost:8000/static/index.html

---

## 10. Testing the System {#testing}

### Test 1: Start Backend Server

```bash
cd ~/rightstaff-ai
source venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     🚀 Starting RightStaff AI
INFO:     ✓ Database connection successful
INFO:     Loading embedding model: sentence-transformers/all-MiniLM-L6-v2
INFO:     ✓ Model loaded (dim: 384)
INFO:     ✓ Qdrant collection initialized
INFO:     Application startup complete.
```

### Test 2: Health Check

Browser: http://localhost:8000/health

### Test 3: API Documentation

Browser: http://localhost:8000/docs (Swagger UI)

### Test 4: Submit Test Candidate

1. Open: http://localhost:8000/static/index.html
2. Fill form + upload resume
3. Submit

### Test 5: Verify Data

**PostgreSQL**:
```bash
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "SELECT full_name, email FROM rightstaff.candidate;"
```

**Qdrant**: http://localhost:6333/dashboard

**MinIO**: http://localhost:9001 → Browse bucket

---

## 11. Daily Workflow {#daily-workflow}

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
uvicorn app.main:app --reload
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

### Resetting Database

```bash
# Stop services
docker-compose down -v

# Start fresh
docker-compose up -d

# Database will auto-run SQL files again
```

---

## 12. Troubleshooting {#troubleshooting}

### Docker Issues

**Problem**: Containers won't start
```bash
docker-compose down -v
docker-compose up -d
docker-compose logs
```

**Problem**: PostgreSQL tables not created
```bash
docker logs rightstaff-postgres
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -f /docker-entrypoint-initdb.d/01_schema.sql
```

### Python Issues

**Problem**: Import errors
```bash
source venv/bin/activate
pip install -r backend/requirements.txt --upgrade
```

**Problem**: spaCy model missing
```bash
python -m spacy download en_core_web_sm
```

### Connection Issues

**Problem**: Can't connect to PostgreSQL
- Check Docker is running: `docker ps`
- Verify port 5432 is not used: `netstat -an | grep 5432`
- Check .env file has correct credentials

**Problem**: Frontend can't reach API
- Verify CORS is enabled in main.py
- Check FastAPI is running on 0.0.0.0:8000
- Try http://localhost:8000/health

### MinIO Issues

**Problem**: Bucket not found
- Open http://localhost:9001
- Login and manually create `rightstaff-resumes` bucket

---

## Next Steps

**Phase 2 (Week 2-3)**: Implement ranking pipeline
- Ontology gate (SQL skill matching)
- Dense retrieval (vector similarity)
- Structured scoring (years, location, salary)
- Cross-encoder re-ranking
- Explanation generation

**Phase 3 (Week 4)**: Implement RAG chatbot
- OpenAI integration
- Context retrieval from Qdrant + PostgreSQL
- WebSocket real-time streaming
- Email draft generation

**Phase 4 (Week 5-6)**: Production migration
- Switch to Pinecone (vector DB)
- Switch to OpenAI embeddings
- Deploy to Kubernetes/AWS
- Portal team integration

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
- Frontend: http://localhost:8000/static/index.html
- Qdrant: http://localhost:6333/dashboard
- MinIO: http://localhost:9001
- PostgreSQL: `localhost:5432`

**Logs**:
```bash
docker logs rightstaff-postgres
docker logs rightstaff-qdrant
docker logs rightstaff-minio
```

---

**Documentation Version**: 1.0  
**Last Updated**: November 2025  
**Author**: RightStaff AI Team