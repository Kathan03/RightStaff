# 📚 RightStaff Project Structure - Complete Beginner's Guide

Hey there! 👋 Welcome to your RightStaff project! This guide will explain **everything** about your project structure in super simple terms. Think of this as your roadmap to understanding how everything works together!

---

## 🎯 What is This Project?

**RightStaff** is an AI-powered system that helps companies find the best job candidates. Imagine you're a company looking to hire someone - this system:
1. Receives resumes from candidates
2. Understands what's in those resumes using AI
3. Matches candidates to job openings
4. Ranks them from best to worst fit

Think of it like a super-smart assistant that reads thousands of resumes and tells you "Hey, this person is perfect for this job!"

---

## 🏗️ The Big Picture: Frontend vs Backend

Before we dive in, let's understand two important concepts:

### **Frontend** 🎨
- This is what **users see and interact with**
- Like a website's buttons, forms, and pages
- In your project: `frontend/` folder (very simple right now, just an HTML file)

### **Backend** ⚙️
- This is the **brain** that does all the work behind the scenes
- It processes data, talks to databases, runs AI models
- In your project: `backend/` folder (this is where all the magic happens!)

**Think of it like a restaurant:**
- **Frontend** = The menu and dining room (what customers see)
- **Backend** = The kitchen (where all the cooking happens)

---

## 📁 Project Structure Overview

Your project is organized like a well-organized filing cabinet. Let's break it down:

```
RightStaff/
├── backend/          ← The brain (Python code)
├── frontend/         ← What users see (HTML)
├── database/         ← Database setup scripts
├── docker/           ← Container configuration
├── data/             ← Stored data (resumes, vectors, etc.)
├── scripts/          ← Helper scripts
├── tests/            ← Tests to make sure everything works
├── docs/             ← Documentation
└── archive/          ← Old files (you can ignore this)
```

---

## 🧠 GROUP 1: The Backend (The Brain)

The `backend/` folder contains all the Python code that makes everything work. Let's explore it!

### 📂 `backend/app/` - The Main Application

This is where all your application code lives. Think of it as the "main office" of your backend.

#### **`main.py`** - The Boss 🎯
**What it does:** This is the **entry point** of your entire application. When you start your server, this file runs first!

**Key concepts:**
- **FastAPI**: A Python framework for building APIs (think of it as a tool that helps you create web services)
- **API (Application Programming Interface)**: A way for different programs to talk to each other
- **Router**: A way to organize different endpoints (like different pages on a website)

**Main functionalities:**
1. Creates the FastAPI application (the web server)
2. Sets up CORS (allows your frontend to talk to the backend)
3. Registers all the API routes (connects different parts of your app)
4. Starts a background worker (processes jobs automatically)
5. Provides health check endpoint (checks if everything is working)

**Why it's needed:** Without this file, your application wouldn't know how to start or what to do!

**📎 This File Uses:**
- `api/webhooks.py` -> Imports and registers `webhooks.router`
- `api/jobs.py` -> Imports and registers `jobs.router`
- `api/admin.py` -> Imports and registers `admin.router`
- `services/ingestion.py` -> Imports `ingestion_worker` and starts it
- `database.py` -> Uses `AsyncSessionLocal` for health check
- `services/redis_client.py` -> Uses `redis_client` for health check
- `services/vector_store.py` -> Uses `vector_store` for health check
- `services/s3_client.py` -> Uses `s3_client` for health check
- `utils/logging.py` -> Uses `logger` for logging

**🔄 Complete Call Flow:**
```
User starts server -> uvicorn app.main:app
-> main.py -> app = FastAPI() -> Creates application
-> app.include_router(webhooks.router) -> Registers webhook endpoints
-> app.include_router(jobs.router) -> Registers job endpoints
-> app.include_router(admin.router) -> Registers admin endpoints
-> startup_event() -> ingestion_worker.start() -> Starts background worker
-> Server running -> Ready to accept requests!

User -> GET /health
-> main.py -> health_check() function
-> AsyncSessionLocal() -> database.py -> Tests database
-> redis_client.ping() -> services/redis_client.py -> Tests Redis
-> vector_store.get_collections() -> services/vector_store.py -> Tests Qdrant
-> s3_client.bucket_exists() -> services/s3_client.py -> Tests MinIO
-> Returns health status -> User sees if all services are working
```

**🔍 Understanding `startup_event()` and Background Workers:**

**What is `startup_event()`?**
- `startup_event()` is a **special function** that FastAPI automatically calls when your server starts
- It's decorated with `@app.on_event("startup")` which tells FastAPI: "Run this function when the server starts!"
- Think of it as an **initialization function** that sets up things before your server accepts requests

**What does it do?**
```python
@app.on_event("startup")
async def startup_event():
    """Start background worker when FastAPI starts."""
    asyncio.create_task(ingestion_worker.start())
    logger.info("FastAPI app started with background worker")
```

**Step-by-step explanation:**
1. **`@app.on_event("startup")`**: This is a **decorator** that tells FastAPI: "When the server starts, run this function!"
2. **`async def startup_event()`**: This is the function that runs automatically on startup (or the function decorator calls)
3. **`asyncio.create_task(ingestion_worker.start())`**: This starts the background worker in a separate "task" (like a separate thread, but for async code)
4. **`ingestion_worker.start()`**: This calls the `start()` method of the ingestion worker

**What is a Background Worker?**
- A **background worker** is code that runs **continuously in the background**, even when no one is making requests
- Think of it like a **robot** that's always working, checking for new jobs to process
- It runs in a **separate task** so it doesn't block your main server from handling requests

**What does `ingestion_worker.start()` do?**
The `start()` method in `ingestion.py` does this:
1. Sets `self.running = True` (marks the worker as active)
2. Initializes Qdrant collection (makes sure vector database is ready)
3. Enters an **infinite loop** that:
   - Checks Redis queue for new jobs (`redis_client.brpop()`)
   - If a job is found, processes it (the 7-stage pipeline)
   - If no job is found, waits 5 seconds and checks again
   - Continues forever until the server stops

**Visual Flow:**
```
Server Starts
    ↓
startup_event() runs automatically
    ↓
asyncio.create_task() creates a background task
    ↓
ingestion_worker.start() begins running
    ↓
Worker enters infinite loop:
    ↓
    Check Redis queue for jobs
    ↓
    If job found → Process it (7 stages)
    ↓
    If no job → Wait 5 seconds
    ↓
    Loop again (forever!)
```

**Why is this important?**
- **Without background worker**: When a webhook arrives, you'd have to process the resume immediately (user waits 30+ seconds!)
- **With background worker**: Webhook arrives → Job queued → Worker processes it in background → User gets instant response!

**Real-World Analogy:**
Think of a restaurant:
- **Main server** = The waiter taking orders (handles requests quickly)
- **Background worker** = The kitchen staff (processes orders in the background)
- **startup_event()** = Hiring the kitchen staff when the restaurant opens

The waiter (server) takes orders instantly, while the kitchen (worker) cooks in the background!

---

#### **`config.py`** - The Settings Manager ⚙️
**What it does:** Manages all your application settings and configuration.

**Key concepts:**
- **Environment Variables**: Settings that can change between different environments (development vs production)
- **Settings**: Things like database passwords, API keys, server addresses

**Main functionalities:**
1. Loads settings from environment variables (like database passwords)
2. Provides default values for development
3. Validates settings (makes sure they're correct)
4. Creates connection URLs for databases

**Why it's needed:** Instead of hardcoding passwords everywhere, you keep them in one place. Super important for security!

**Example settings:**
- Database connection info (PostgreSQL)
- Redis connection info (for caching)
- Qdrant connection info (for vector storage)
- MinIO connection info (for file storage)
- AI model settings (which embedding model to use)

**📎 Used By (Dependencies):**
- `database.py` -> Uses `settings` for database connection
- `redis_client.py` -> Uses `settings` for Redis connection
- `vector_store.py` -> Uses `settings` for Qdrant connection
- `embeddings.py` -> Uses `settings` for AI model configuration
- `s3_client.py` -> Uses `settings` for MinIO connection
- `utils/logging.py` -> Uses `settings` for log level configuration
- `services/chatbot.py` -> Uses `settings` for OpenAI API key
- `services/ranking.py` -> Uses `settings` for model configuration

**🔄 Call Flow:**
```
Any file -> from app.config import settings -> settings.database_url
Any file -> from app.config import settings -> settings.redis_host
Any file -> from app.config import settings -> settings.qdrant_host
```

---

#### **`database.py`** - The Database Connection 🔌
**What it does:** Handles all connections to your PostgreSQL database.

**Key concepts:**
- **Database**: A place to store structured data (like a digital filing cabinet)
- **PostgreSQL**: A type of database (very popular and powerful)
- **SQLAlchemy**: A Python library that helps you talk to databases
- **Async**: Code that doesn't block (can do multiple things at once)
- **Session**: A connection to the database that lets you read/write data

**Main functionalities:**
1. Creates a connection pool (reuses connections for efficiency)
2. Provides a session factory (creates new database sessions)
3. Provides `get_db()` function (used by FastAPI routes to get database access)

**Why it's needed:** Every time your app needs to save or read data, it needs a database connection. This file manages all of that!

**📎 Used By (Dependencies):**
- `main.py` -> Uses `AsyncSessionLocal` for health check
- `api/webhooks.py` -> Uses `get_db()` via `Depends(get_db)`
- `api/jobs.py` -> Uses `get_db()` via `Depends(get_db)`
- `services/ingestion.py` -> Uses `AsyncSessionLocal` directly
- `services/sql_filter.py` -> Uses `AsyncSessionLocal` directly

**🔄 Call Flow for `get_db()`:**
```
User Request -> FastAPI Route (webhooks.py or jobs.py)
-> Depends(get_db) -> get_db() function in database.py
-> Creates AsyncSessionLocal() -> Yields session
-> Route uses session -> Closes session automatically
```

**Example from `webhooks.py`:**
```python
@router.post("/candidate-updated")
async def candidate_updated_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db)  # <- FastAPI calls get_db() here!
):
    # db is now a database session you can use
    result = await db.execute(select(Candidate)...)
```

**🔄 Call Flow for `AsyncSessionLocal`:**
```
ingestion.py -> from app.database import AsyncSessionLocal
-> async with AsyncSessionLocal() as session:
-> Use session to query database
-> Session closes automatically when done
```

---

### 📂 `backend/app/models/` - Data Structures 📊

This folder defines what your data looks like. Think of it as blueprints for your database tables.

#### **`candidate.py`** - Candidate Data Models
**What it does:** Defines the structure of candidate data in your database.

**Key concepts:**
- **ORM (Object-Relational Mapping)**: A way to represent database tables as Python classes
- **Model**: A Python class that represents a database table
- **Relationship**: How different tables connect to each other

**Main models:**
1. **`Candidate`**: Main candidate information (name, experience, summary)
2. **`CandidateContact`**: Contact details (email, phone, address)
3. **`CandidateResume`**: Resume files (stored in S3/MinIO)
4. **`Skill`**: Skills ontology (a structured list of all possible skills)
5. **`CandidateSkill`**: Links candidates to their skills
6. **`Job`**: Job postings with requirements

**Why it's needed:** This tells your database what fields to store for each candidate. Without this, your database wouldn't know what data to keep!

**Example:**
```python
# This model says: "A candidate has a name, years of experience, and a summary"
class Candidate:
    id = UUID
    full_name = Text
    years_experience = Numeric
    professional_summary = Text
```

**📎 Used By (Dependencies):**
- `api/webhooks.py` -> Uses `Candidate` model
- `api/jobs.py` -> Uses `Job`, `JobStatus` models
- `services/ingestion.py` -> Uses `Candidate`, `CandidateContact`, `CandidateResume` models
- `services/sql_filter.py` -> Uses `Candidate`, `CandidateSkill`, `Skill`, `CandidateContact` models

**🔄 Call Flow:**
```
webhooks.py -> from app.models.candidate import Candidate
-> Uses Candidate in database query: select(Candidate).where(...)

ingestion.py -> from app.models.candidate import Candidate, CandidateContact, CandidateResume
-> Uses models to fetch candidate data from database

sql_filter.py -> from app.models.candidate import Candidate, CandidateSkill, Skill
-> Uses models to filter candidates by skills
```

---

### 📂 `backend/app/api/` - API Endpoints 🌐

This folder contains all your API endpoints. Think of endpoints as different "doors" that external systems can knock on to get information or trigger actions.

**Key concept:**
- **API Endpoint**: A specific URL that does a specific thing (like `/api/v1/jobs/rank`)

#### **`webhooks.py`** - Receiving Updates 📥
**What it does:** Receives notifications when candidate profiles are created or updated.

**Key concepts:**
- **Webhook**: A way for one system to notify another system about events
- **Queue**: A line of jobs waiting to be processed (like a line at a coffee shop)
- **Redis**: A super-fast database used for queues and caching

**Main functionalities:**
1. Receives webhook from Portal team (when a candidate updates their profile)
2. Validates that the candidate exists in the database
3. Creates a job and adds it to Redis queue
4. Returns immediately (doesn't wait for processing - this is called "async")

**Why it's needed:** When a candidate uploads a new resume, the Portal team sends a webhook. This file receives it and queues it for processing!

**Flow:**
```
Portal Team → Webhook → Validate → Queue in Redis → Return "Accepted"
```

**🔍 What is a Webhook? (Detailed Explanation)**

**Simple Definition:**
A **webhook** is like a **phone call** between two computer systems. When something important happens in one system, it "calls" (sends a message to) another system to let it know.

**Real-World Analogy:**
Think of webhooks like a **doorbell notification system**:

**Without Webhooks (Polling - Bad):**
- You have to **constantly check** if someone is at the door
- You walk to the door every 5 minutes: "Is anyone there?" → No
- You walk again: "Is anyone there?" → No
- This wastes time and energy!

**With Webhooks (Event-Driven - Good):**
- Someone rings the doorbell → **You get notified immediately!**
- You don't have to keep checking
- You only respond when something actually happens

**In Your Project:**

**The Problem:**
- Portal Team has a system where candidates upload resumes
- Your AI system needs to process those resumes
- **Question:** How does your system know when a new resume is uploaded?

**The Solution: Webhooks!**

```
Candidate uploads resume to Portal Team's system
    ↓
Portal Team's system: "Hey! A resume was just uploaded!"
    ↓
Portal Team sends webhook to your system
    ↓
Your system receives webhook: "New resume for candidate #123!"
    ↓
Your system processes the resume
```

**How Webhooks Work:**

1. **Registration**: Your system gives Portal Team a URL (like `https://yourserver.com/api/v1/webhooks/candidate-updated`)

2. **Event Happens**: Something happens in Portal Team's system (candidate uploads resume)

3. **Notification**: Portal Team's system **automatically sends** an HTTP POST request to your URL with information about what happened

4. **Your System Responds**: Your system receives the webhook, processes it, and sends back a response

**Example Webhook Request:**
```json
POST /api/v1/webhooks/candidate-updated
{
  "event_type": "resume_uploaded",
  "candidate_id": "a1b2c3d4-1234-5678-90ab-cdef12345678",
  "timestamp": "2024-01-15T10:30:00Z",
  "s3_resume_url": "s3://bucket/resumes/john_doe_resume.pdf",
  "profile_snapshot": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

**Webhook vs. API - What's the Difference?**

**API (Regular Request):**
- **You** ask for information: "Hey, do you have any new resumes?"
- You have to **keep asking** (polling)
- Like calling a friend: "Did anything happen?" → "No" → Call again later

**Webhook (Event-Driven):**
- **They** tell you when something happens: "Hey! New resume uploaded!"
- You **only respond** when notified
- Like having a friend call you: "Something happened!" → You respond

**Why Webhooks are Better:**
- ✅ **Efficient**: No wasted requests checking for nothing
- ✅ **Real-time**: You know immediately when something happens
- ✅ **Scalable**: Works even with thousands of events
- ✅ **Reliable**: The sender knows if you received it (you send a response)

**In Your RightStaff Project:**

**The Flow:**
```
1. Candidate uploads resume to Portal Team's website
   ↓
2. Portal Team's system processes the upload
   ↓
3. Portal Team sends webhook to your system:
   POST https://your-server.com/api/v1/webhooks/candidate-updated
   ↓
4. Your webhooks.py receives the webhook
   ↓
5. Your system validates the candidate exists
   ↓
6. Your system queues the job in Redis
   ↓
7. Your system responds: "Got it! Job queued!" (202 Accepted)
   ↓
8. Background worker processes the resume later
```

**Key Points:**
- Webhooks are **one-way notifications** (they tell you, you don't ask)
- They're **event-driven** (only sent when something happens)
- They're **asynchronous** (you respond quickly, process later)
- They're like **push notifications** for servers!

**Think of it like this:**
- **API** = You calling a restaurant: "Do you have my order ready?" (you initiate)
- **Webhook** = Restaurant calling you: "Your order is ready!" (they initiate)

In your project, Portal Team uses webhooks to **push** notifications to your system, so you don't have to keep asking "Any new resumes?"

**📎 Used By (Dependencies):**
- `main.py` -> Imports and registers `webhooks.router`

**📎 This File Uses:**
- `database.py` -> `get_db()` function (via `Depends(get_db)`)
- `models/candidate.py` -> `Candidate` model
- `services/redis_client.py` -> `redis_client` for queuing
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow:**
```
Portal Team -> POST /api/v1/webhooks/candidate-updated
-> main.py (FastAPI app) -> webhooks.py (router)
-> candidate_updated_webhook() function
-> Depends(get_db) -> database.py -> get_db() -> Returns session
-> db.execute(select(Candidate)...) -> Queries database
-> redis_client.lpush() -> services/redis_client.py -> Queues job
-> Returns {"status": "accepted"} -> Portal Team gets response
```

---

#### **`jobs.py`** - Job Management 💼
**What it does:** Handles everything related to job postings and candidate ranking.

**Main functionalities:**
1. **Create jobs**: Allows creating new job postings (for testing)
2. **Rank candidates**: Takes a job and finds the best matching candidates
3. **Get rankings**: Retrieves cached ranking results

**Key concepts:**
- **SQL Gating**: Filtering candidates using database queries (must-have skills, years of experience, location)
- **Caching**: Storing results temporarily so you don't have to recalculate them

**Why it's needed:** This is the core feature! When someone wants to find candidates for a job, this endpoint does the work.

**Example flow:**
```
1. Create a job: "Looking for Python developer with 5+ years"
2. Rank candidates: System finds all matching candidates
3. Get rankings: Returns the top candidates
```

**📎 Used By (Dependencies):**
- `main.py` -> Imports and registers `jobs.router`

**📎 This File Uses:**
- `database.py` -> `get_db()` function (via `Depends(get_db)`)
- `models/candidate.py` -> `Job`, `JobStatus` models
- `services/sql_filter.py` -> `apply_combined_sql_gates()` function
- `services/redis_client.py` -> `redis_client` for caching

**🔄 Complete Call Flow for Ranking:**
```
User -> POST /api/v1/jobs/rank
-> main.py (FastAPI app) -> jobs.py (router)
-> rank_candidates() function
-> Depends(get_db) -> database.py -> get_db() -> Returns session
-> db.execute(select(Job)...) -> Fetches job from database
-> apply_combined_sql_gates() -> services/sql_filter.py -> Filters candidates
-> redis_client.set() -> services/redis_client.py -> Caches results
-> Returns ranking results -> User gets response
```

---

#### **`admin.py`** - System Administration 🛠️
**What it does:** Provides tools for monitoring and managing the system.

**Main functionalities:**
1. **View metrics**: See how many jobs processed, success rates, etc.
2. **View DLQ**: Check failed jobs in Dead Letter Queue
3. **Replay DLQ**: Retry failed jobs after fixing issues
4. **Clear DLQ**: Delete failed jobs (use with caution!)

**Key concepts:**
- **DLQ (Dead Letter Queue)**: A special queue for jobs that failed after multiple retries
- **Metrics**: Statistics about how your system is performing

**Why it's needed:** When things go wrong, you need tools to see what happened and fix it!

**📎 Used By (Dependencies):**
- `main.py` -> Imports and registers `admin.router`

**📎 This File Uses:**
- `services/redis_client.py` -> `redis_client` for DLQ operations
- `services/metrics.py` -> `metrics_collector` for system metrics
- `services/vector_store.py` -> `vector_store` for collection info
- `services/embeddings.py` -> `embedding_service` for model info
- `services/ontology.py` -> `is_spacy_available()` function
- `services/ingestion.py` -> `ingestion_worker` for worker stats

**🔄 Complete Call Flow for Metrics:**
```
Admin -> GET /api/v1/admin/metrics
-> main.py (FastAPI app) -> admin.py (router)
-> get_metrics() function
-> metrics_collector.get_metrics() -> services/metrics.py -> Returns metrics
-> embedding_service.get_model_info() -> services/embeddings.py -> Model info
-> vector_store.get_collection_info() -> services/vector_store.py -> Collection stats
-> Returns combined metrics -> Admin sees system status
```

---

#### **`candidates.py`** - Candidate Management 👤
**What it does:** (Likely) Provides endpoints to view and manage candidate data.

**Note:** I didn't read this file, but it probably handles:
- Getting candidate details
- Searching candidates
- Updating candidate information

---

#### **`chat.py`** - Chatbot Interface 💬
**What it does:** (Likely) Provides a chatbot interface for asking questions about candidates.

**Note:** This might use WebSockets for real-time communication.

---

### 📂 `backend/app/services/` - Business Logic 🧩

This folder contains all the "services" - reusable pieces of code that do specific tasks. Think of them as specialized workers in your company.

#### **`ingestion.py`** - Resume Processing Pipeline 🔄
**What it does:** This is the **heart** of your system! It processes resumes from start to finish.

**Key concepts:**
- **Background Worker**: Code that runs continuously, processing jobs from a queue
- **Pipeline**: A series of steps that data goes through
- **Retry Logic**: If something fails, try again (with exponential backoff)
- **DLQ**: Dead Letter Queue for jobs that fail after max retries

**The 7-Stage Pipeline:**
1. **Fetch candidate details** from PostgreSQL
2. **Download resume** from MinIO (S3-compatible storage)
3. **Parse resume** (extract text from PDF/DOCX)
4. **Extract skills** from text using ontology
5. **Chunk text** (split into smaller pieces for embedding)
6. **Generate embeddings** (convert text to vectors using AI)
7. **Store in Qdrant** (save vectors for semantic search)

**Why it's needed:** When a resume is uploaded, this service does ALL the work to make it searchable!

**Example:**
```
Resume PDF → Extract Text → Find Skills → Split into Chunks → 
Convert to Vectors → Store in Vector Database
```

**📎 Used By (Dependencies):**
- `main.py` -> Imports `ingestion_worker` and starts it on startup
- `api/admin.py` -> Uses `ingestion_worker` for worker stats

**📎 This File Uses:**
- `database.py` -> `AsyncSessionLocal` for database queries
- `models/candidate.py` -> `Candidate`, `CandidateContact`, `CandidateResume` models
- `services/redis_client.py` -> `redis_client` for queue operations
- `services/s3_client.py` -> `s3_client` for downloading resumes
- `services/parsers.py` -> `parse_resume()`, `chunk_text()` functions
- `services/embeddings.py` -> `embedding_service` for generating vectors
- `services/vector_store.py` -> `vector_store` for storing vectors
- `services/ontology.py` -> `extract_skills_from_text()` function
- `services/metrics.py` -> `metrics_collector` for tracking performance
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow:**
```
main.py -> startup_event() -> ingestion_worker.start()
-> ingestion.py -> IngestionWorker.start() -> Polls Redis queue
-> redis_client.brpop() -> services/redis_client.py -> Gets job from queue
-> process_job() -> 7-stage pipeline:
  1. AsyncSessionLocal() -> database.py -> Get database session
  2. db.execute(select(Candidate)...) -> Fetch candidate
  3. s3_client.download_file() -> services/s3_client.py -> Download resume
  4. parse_resume() -> services/parsers.py -> Extract text
  5. extract_skills_from_text() -> services/ontology.py -> Find skills
  6. chunk_text() -> services/parsers.py -> Split into chunks
  7. embedding_service.embed_batch() -> services/embeddings.py -> Generate vectors
  8. vector_store.upsert_vectors() -> services/vector_store.py -> Store vectors
-> metrics_collector.record_timing() -> services/metrics.py -> Track metrics
-> Job complete!
```

---

#### **`embeddings.py`** - AI Text Conversion 🤖
**What it does:** Converts text into mathematical vectors (embeddings) that AI can understand.

**Key concepts:**
- **Embedding**: A list of numbers that represents the meaning of text
- **Vector**: A list of numbers (like [0.1, -0.5, 0.8, ...])
- **Semantic Search**: Finding similar text based on meaning, not just keywords
- **Model**: A pre-trained AI that converts text to vectors

**Main functionalities:**
1. Loads the embedding model (sentence-transformers/all-MiniLM-L6-v2)
2. Converts single text to embedding
3. Converts multiple texts to embeddings (batch processing - faster!)

**Why it's needed:** To find similar candidates, you need to convert their resumes into numbers. This service does that!

**Example:**
```
"Python developer with 5 years experience" 
→ [0.123, -0.456, 0.789, ..., 0.012] (384 numbers)
```

**📎 Used By (Dependencies):**
- `services/ingestion.py` -> Uses `embedding_service.embed_batch()`
- `api/admin.py` -> Uses `embedding_service.get_model_info()`

**📎 This File Uses:**
- `config.py` -> `settings` for model configuration

**🔄 Complete Call Flow:**
```
ingestion.py -> embedding_service.embed_batch(chunks)
-> embeddings.py -> EmbeddingService.embed_batch()
-> _load_model() -> Loads AI model (if not loaded)
-> model.encode() -> Converts text to vectors
-> Returns list of embeddings -> ingestion.py receives vectors
```

---

#### **`parsers.py`** - Document Parsing 📄
**What it does:** Extracts text from PDF, DOCX, and TXT files.

**Key concepts:**
- **Parsing**: Extracting structured information from unstructured files
- **Unstructured**: A library that helps parse documents

**Main functionalities:**
1. **`parse_resume()`**: Extracts text from resume files (PDF/DOCX/TXT)
2. **`chunk_text()`**: Splits long text into smaller, overlapping chunks
3. **`extract_metadata()`**: (Future) Extracts name, email, phone from resume

**Why it's needed:** Resumes come as PDFs or Word docs. You need to extract the text first before you can process it!

**Example:**
```
resume.pdf → "John Doe\nSoftware Engineer\n5 years Python experience..."
```

**📎 Used By (Dependencies):**
- `services/ingestion.py` -> Uses `parse_resume()`, `chunk_text()`

**🔄 Complete Call Flow:**
```
ingestion.py -> parse_resume(resume_bytes, s3_url)
-> parsers.py -> parse_resume() function
-> Writes bytes to temp file -> Uses Unstructured library
-> partition_pdf() or partition_docx() -> Extracts text
-> Returns text and metadata -> ingestion.py receives parsed text

ingestion.py -> chunk_text(text, chunk_size=400)
-> parsers.py -> chunk_text() function
-> Splits text into overlapping chunks -> Returns list of chunks
-> ingestion.py receives chunks for embedding
```

---

#### **`vector_store.py`** - Vector Database Client 🗄️
**What it does:** Manages all interactions with Qdrant (your vector database).

**Key concepts:**
- **Vector Database**: A special database designed to store and search vectors
- **Qdrant**: The specific vector database you're using
- **Collection**: A group of vectors (like a table in a regular database)
- **Upsert**: Insert or update (if it exists, update it; if not, create it)

**Main functionalities:**
1. **`create_collection()`**: Creates a new collection for storing vectors
2. **`upsert_vectors()`**: Saves vectors with their metadata
3. **`delete_by_candidate_id()`**: Removes all vectors for a candidate
4. **`search()`**: Searches for similar vectors using semantic similarity
5. **`get_collection_info()`**: Gets collection statistics

**Why it's needed:** You need somewhere to store all those embeddings! Qdrant is perfect for this.

**Example:**
```
Vector: [0.1, -0.2, 0.3, ...]
Metadata: {candidate_id: "123", chunk_index: 0, skills: ["Python", "Django"]}
→ Stored in Qdrant
```

**📎 Used By (Dependencies):**
- `services/ingestion.py` -> Uses `vector_store.upsert_vectors()`, `vector_store.delete_by_candidate_id()`
- `main.py` -> Uses `vector_store` for health check
- `api/admin.py` -> Uses `vector_store.get_collection_info()`
- `services/retrieval.py` -> Uses `vector_store.search()` for semantic search
- `services/job_embeddings.py` -> Uses `vector_store.upsert_points()` for storing job vectors
- `services/chatbot.py` -> Uses `vector_store` for semantic search

**📎 This File Uses:**
- `config.py` -> `settings` for Qdrant connection

**🔄 Complete Call Flow:**
```
ingestion.py -> vector_store.upsert_vectors(vectors, payloads)
-> vector_store.py -> VectorStore.upsert_vectors()
-> Creates PointStruct objects -> client.upsert() -> Saves to Qdrant
-> Returns success -> ingestion.py confirms storage

ingestion.py -> vector_store.delete_by_candidate_id(candidate_id)
-> vector_store.py -> VectorStore.delete_by_candidate_id()
-> client.delete() with filter -> Deletes all vectors for candidate
-> Returns success -> ingestion.py confirms deletion
```

---

#### **`redis_client.py`** - Cache & Queue Manager 🚀
**What it does:** Manages Redis connections for caching and queuing.

**Key concepts:**
- **Redis**: A super-fast in-memory database
- **Cache**: Temporary storage for frequently accessed data
- **Queue**: A line of jobs waiting to be processed
- **DLQ**: Dead Letter Queue for failed jobs

**Main functionalities:**
1. **Queue operations**: Push/pop jobs from queues
2. **Cache operations**: Store/retrieve cached data
3. **DLQ management**: Handle failed jobs

**Why it's needed:** 
- **Caching**: Makes your app faster (don't recalculate rankings every time)
- **Queuing**: Allows async processing (don't make users wait)

**Example:**
```
Job ranking result → Cache in Redis (expires in 1 hour)
Next request → Get from cache (instant!) instead of recalculating
```

**📎 Used By (Dependencies):**
- `api/webhooks.py` -> Uses `redis_client.lpush()` to queue jobs
- `api/jobs.py` -> Uses `redis_client.set()`, `redis_client.get()` for caching
- `api/admin.py` -> Uses `redis_client` for DLQ operations
- `services/ingestion.py` -> Uses `redis_client.brpop()` to get jobs, `redis_client.push_dlq()` for failed jobs
- `main.py` -> Uses `redis_client.ping()` for health check

**📎 This File Uses:**
- `config.py` -> `settings` for Redis connection
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow for Queuing:**
```
webhooks.py -> redis_client.lpush("ingestion_queue", job_data)
-> redis_client.py -> RedisClient.lpush()
-> client.lpush() -> Adds job to Redis queue
-> Returns queue length -> webhooks.py confirms job queued

ingestion.py -> redis_client.brpop("ingestion_queue", timeout=5)
-> redis_client.py -> RedisClient.brpop()
-> client.brpop() -> Gets job from Redis queue (waits if empty)
-> Returns job data -> ingestion.py processes job
```

**🔄 Complete Call Flow for Caching:**
```
jobs.py -> redis_client.set(cache_key, data, ex=3600)
-> redis_client.py -> RedisClient.set()
-> client.set() -> Stores data in Redis with 1-hour expiry
-> Returns success -> jobs.py confirms cached

jobs.py -> redis_client.get(cache_key)
-> redis_client.py -> RedisClient.get()
-> client.get() -> Retrieves data from Redis
-> Returns cached data or None -> jobs.py uses cache or recalculates
```

---

#### **`s3_client.py`** - File Storage Client 📦
**What it does:** Manages file storage using MinIO (S3-compatible storage).

**Key concepts:**
- **S3**: Amazon's Simple Storage Service (for storing files)
- **MinIO**: An open-source S3-compatible storage (used for development)
- **Bucket**: A container for files (like a folder)

**Main functionalities:**
1. Download files from MinIO
2. Upload files to MinIO
3. Check if files exist

**Why it's needed:** Resumes are stored as files. You need a place to keep them!

**Example:**
```
Resume PDF → Upload to MinIO → Get URL: s3://bucket/resume.pdf
Later → Download from MinIO using URL
```

**📎 Used By (Dependencies):**
- `services/ingestion.py` -> Uses `s3_client.download_file()` to get resumes
- `main.py` -> Uses `s3_client` for health check

**📎 This File Uses:**
- `config.py` -> `settings` for MinIO connection
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow:**
```
ingestion.py -> s3_client.download_file(s3_url)
-> s3_client.py -> S3Client.download_file()
-> client.get_object() -> Downloads file from MinIO
-> Returns file bytes -> ingestion.py receives resume file
```

---

#### **`sql_filter.py`** - Database Filtering 🔍
**What it does:** Filters candidates using SQL queries based on job requirements.

**Key concepts:**
- **SQL**: A language for querying databases
- **Filtering**: Selecting only records that match certain criteria
- **Gating**: A filter that candidates must pass (like a gate)

**Main functionalities:**
1. Filters by must-have skills
2. Filters by years of experience (min/max)
3. Filters by location preference

**Why it's needed:** Before doing expensive AI ranking, you first filter out candidates who don't meet basic requirements!

**Example:**
```
Job requires: Python, 5+ years, Remote
→ SQL query finds all candidates with Python skill AND 5+ years AND willing to work remote
```

**📎 Used By (Dependencies):**
- `api/jobs.py` -> Uses `apply_combined_sql_gates()` function

**📎 This File Uses:**
- `database.py` -> `AsyncSessionLocal` for database queries
- `models/candidate.py` -> `Candidate`, `CandidateSkill`, `Skill`, `CandidateContact` models

**🔄 Complete Call Flow:**
```
jobs.py -> apply_combined_sql_gates(must_have_skills, min_years, max_years, location, db)
-> sql_filter.py -> apply_combined_sql_gates() function
-> AsyncSessionLocal() -> database.py -> Get database session
-> db.execute(select(Candidate)...) -> Queries database with filters
-> Returns list of qualified candidate IDs -> jobs.py receives filtered candidates
```

---

#### **`job_embeddings.py`** - Job Embedding Service 💼
**What it does:** Creates and manages embeddings for job descriptions and skills. This is **REQUIRED** for semantic matching!

**Key concepts:**
- **Job Embeddings**: Converting job descriptions into vectors (just like candidate resumes)
- **Dual Embeddings**: Creates two embeddings per job (profile + skills) for better matching
- **Caching**: Job embeddings are cached since jobs change less frequently than candidates

**Main functionalities:**
1. **`get_or_create_job_embeddings()`**: Gets cached embeddings or creates new ones
2. **`_prepare_skills_text()`**: Expands skills using ontology and prepares text for embedding
3. **`_store_job_vectors()`**: Stores job vectors in Qdrant for analysis

**Why two embeddings?**
- **Profile embedding** (50% weight): Captures role, responsibilities, company culture
- **Skills embedding** (30% weight): Captures technical requirements
- Allows weighted semantic search per PRD requirements

**Why it's needed:** To find similar candidates, you need to compare job vectors with candidate vectors. This service creates the job vectors!

**Example:**
```
Job: "Python Developer with 5 years experience"
→ Profile embedding: [0.1, -0.2, 0.3, ...] (from title + description)
→ Skills embedding: [0.2, -0.1, 0.4, ...] (from expanded skills)
→ Both stored and cached for reuse
```

**📎 Used By (Dependencies):**
- `services/retrieval.py` -> Uses `job_embedding_service.get_or_create_job_embeddings()`

**📎 This File Uses:**
- `services/embeddings.py` -> `embedding_service` for generating vectors
- `services/vector_store.py` -> `vector_store` for storing job vectors
- `services/ontology.py` -> `expand_skills()` for skill expansion
- `services/redis_client.py` -> `redis_client` for caching embeddings
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow:**
```
retrieval.py -> job_embedding_service.get_or_create_job_embeddings(job_data)
-> job_embeddings.py -> JobEmbeddingService.get_or_create_job_embeddings()
-> Check Redis cache -> If cached, return cached embeddings
-> If not cached:
   -> embedding_service.embed_text(profile_text) -> services/embeddings.py -> Profile vector
   -> expand_skills() -> services/ontology.py -> Expand skills
   -> embedding_service.embed_text(skills_text) -> services/embeddings.py -> Skills vector
   -> Cache in Redis -> Store in Qdrant -> Return both embeddings
```

---

#### **`retrieval.py`** - Dense Retrieval Service 🔍
**What it does:** Performs semantic search to find candidates similar to a job using vector similarity.

**Key concepts:**
- **Dense Retrieval**: Semantic search using vector similarity (not keyword matching!)
- **Multi-Vector Search**: Searches across profile, skills, and chunk vectors
- **Weighted Combination**: Combines scores from different vector types
- **Evidence Chunks**: Returns actual text snippets that match (for explanations)

**Main functionalities:**
1. **`retrieve_candidates()`**: Main entry point - finds semantically similar candidates
2. **`_search_profiles()`**: Searches candidate profile vectors
3. **`_search_skills()`**: Searches candidate skills vectors
4. **`_search_chunks()`**: Searches candidate resume chunk vectors (with evidence)
5. **`_combine_scores()`**: Combines all scores with weights (50% profile + 30% skills + 20% chunks)

**Why it's needed:** This is the "AI magic" that finds candidates who are similar in meaning, not just keywords!

**Example:**
```
Job: "Software engineer with Python experience"
→ Searches candidate vectors
→ Finds: "Backend developer with 5 years Python" (high similarity!)
→ Finds: "Full-stack dev with Django" (good similarity!)
→ Returns candidates ranked by semantic similarity
```

**📎 Used By (Dependencies):**
- `services/ranking.py` -> Uses `dense_retriever.retrieve_candidates()`

**📎 This File Uses:**
- `services/vector_store.py` -> `vector_store` for searching vectors
- `services/job_embeddings.py` -> `job_embedding_service` for job embeddings
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow:**
```
ranking.py -> dense_retriever.retrieve_candidates(job_data, candidate_ids)
-> retrieval.py -> DenseRetriever.retrieve_candidates()
-> job_embedding_service.get_or_create_job_embeddings() -> services/job_embeddings.py -> Get job vectors
-> _search_profiles() -> vector_store.search() -> services/vector_store.py -> Profile matches
-> _search_skills() -> vector_store.search() -> services/vector_store.py -> Skills matches
-> _search_chunks() -> vector_store.search() -> services/vector_store.py -> Chunk matches (with evidence)
-> _combine_scores() -> Combines all scores with weights
-> Returns ranked candidates with evidence chunks
```

---

#### **`scoring.py`** - Structured Scoring Service 📊
**What it does:** Calculates objective scores based on database fields (experience, skills, recency, location, etc.)

**Key concepts:**
- **Structured Scoring**: Objective metrics from database (not AI-based)
- **Multi-Component**: Scores based on 5 different factors
- **Weighted Combination**: Combines components with specific weights
- **Diminishing Returns**: Experience scoring uses square root to prevent over-indexing

**Main functionalities:**
1. **`calculate_score()`**: Main entry point - calculates all structured scores
2. **`_score_nice_to_have_skills()`**: Scores based on skills coverage
3. **`_score_experience()`**: Scores based on years of experience (with diminishing returns)
4. **`_score_recency()`**: Scores based on profile freshness (exponential decay)
5. **`_score_domain()`**: Scores based on industry/domain match
6. **`_score_location()`**: Scores based on location match or remote eligibility

**Scoring Weights (from PRD):**
- Nice-to-have skills coverage: 35%
- Years experience: 20%
- Recency: 15%
- Domain match: 10%
- Location: 20%

**Why it's needed:** Complements semantic similarity with objective facts. Ensures experienced candidates rank higher and rewards fresh profiles!

**Example:**
```
Candidate: 5 years Python, updated 10 days ago, in San Francisco, has Django skill
Job: Python developer, 3+ years, San Francisco, requires Django
→ Skills score: 1.0 (has Django)
→ Experience score: 0.87 (5 years with diminishing returns)
→ Recency score: 0.72 (10 days ago)
→ Location score: 1.0 (same city)
→ Domain score: 0.8 (engineering match)
→ Combined: 0.35*1.0 + 0.20*0.87 + 0.15*0.72 + 0.10*0.8 + 0.20*1.0 = 0.90
```

**📎 Used By (Dependencies):**
- `services/ranking.py` -> Uses `structured_scorer.calculate_score()`

**📎 This File Uses:**
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow:**
```
ranking.py -> structured_scorer.calculate_score(candidate_data, job_data)
-> scoring.py -> StructuredScorer.calculate_score()
-> _score_nice_to_have_skills() -> Calculates skills coverage
-> _score_experience() -> Calculates experience score (with diminishing returns)
-> _score_recency() -> Calculates recency score (exponential decay)
-> _score_domain() -> Calculates domain match
-> _score_location() -> Calculates location match
-> Combines all scores with weights -> Returns StructuredScore object
```

---

#### **`explanation.py`** - Explanation Generator 📝
**What it does:** Generates human-readable explanations for ranking decisions. Provides transparency and builds trust!

**Key concepts:**
- **Explainable AI**: Making AI decisions understandable to humans
- **Evidence-Based**: Explanations cite actual evidence from resumes
- **Structured Format**: Summary + reasons + evidence snippets
- **Trust Building**: Helps staffing agents understand why candidates are ranked

**Main functionalities:**
1. **`generate()`**: Main entry point - creates comprehensive explanation
2. **`_generate_summary()`**: Creates one-line summary based on ranking band
3. **`_extract_reasons()`**: Extracts top reasons from scoring components
4. **`_format_evidence()`**: Formats evidence chunks with citations

**Why explanations matter:**
- Build trust with staffing agents
- Enable informed decisions
- Meet compliance requirements
- Debug ranking issues

**Example Output:**
```json
{
  "summary": "Excellent match for Python Developer with 85% compatibility",
  "reasons": [
    "Strong skills match: Python, Django, REST API",
    "5 years of relevant experience",
    "Located in San Francisco",
    "Recently updated profile (active candidate)"
  ],
  "evidence": [
    {
      "text": "5 years of Python development experience...",
      "skills_found": ["Python", "Django"],
      "relevance_score": 0.92,
      "location": "Resume chunk 3"
    }
  ]
}
```

**📎 Used By (Dependencies):**
- `services/ranking.py` -> Uses `explanation_generator.generate()`

**📎 This File Uses:**
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow:**
```
ranking.py -> explanation_generator.generate(ranking_result, job_data, retrieval_results, structured_scores)
-> explanation.py -> ExplanationGenerator.generate()
-> _generate_summary() -> Creates one-line summary
-> _extract_reasons() -> Extracts top reasons from scores
-> _format_evidence() -> Formats evidence chunks with citations
-> Returns explanation dict -> ranking.py includes in final result
```

---

#### **`ranking.py`** - Candidate Ranking Orchestrator 🏆
**What it does:** This is the **main ranking service** that orchestrates the complete ranking pipeline from start to finish!

**Key concepts:**
- **Orchestration**: Coordinates multiple services to produce final rankings
- **Pipeline**: A series of steps that candidates go through
- **Score Blending**: Combines multiple scoring methods into one final score
- **Banding**: Groups candidates into confidence levels (high/medium/low)

**The Complete Ranking Pipeline:**
1. **SQL Gating**: Filters candidates using hard requirements (must-have skills, years, location)
2. **Dense Retrieval**: Semantic search using vector similarity (finds similar candidates)
3. **Structured Scoring**: Calculates objective scores (experience, skills, recency, location)
4. **Completeness Scoring**: Measures profile completeness
5. **Score Blending**: Combines all scores with weights (40% dense + 35% structured + 25% completeness)
6. **Banding**: Groups candidates into high/medium/low confidence bands
7. **Explanation Generation**: Creates human-readable explanations for each candidate

**Main functionalities:**
1. **`rank_candidates()`**: Main entry point - runs the complete pipeline
2. **`_blend_scores()`**: Combines dense, structured, and completeness scores
3. **`_band_candidates()`**: Groups candidates by confidence level
4. **`_calculate_completeness_scores()`**: Measures how complete each profile is

**Why it's needed:** This service brings everything together! It takes a job, finds matching candidates, scores them, and returns ranked results with explanations.

**📎 Used By (Dependencies):**
- `api/jobs.py` -> Uses `ranking_service.rank_candidates()`

**📎 This File Uses:**
- `services/sql_filter.py` -> `apply_combined_sql_gates()` for filtering
- `services/retrieval.py` -> `dense_retriever` for semantic search
- `services/scoring.py` -> `structured_scorer` for objective scoring
- `services/explanation.py` -> `explanation_generator` for explanations
- `services/redis_client.py` -> `redis_client` for caching results
- `database.py` -> `AsyncSessionLocal` for database queries
- `models/candidate.py` -> `Job`, `Candidate`, `CandidateContact`, `CandidateSkill`, `Skill` models

**🔄 Complete Call Flow:**
```
jobs.py -> ranking_service.rank_candidates(job_id)
-> ranking.py -> RankingService.rank_candidates()
-> Step 1: Fetch job data from database
-> Step 2: apply_combined_sql_gates() -> services/sql_filter.py -> Filter candidates
-> Step 3: dense_retriever.retrieve_candidates() -> services/retrieval.py -> Semantic search
-> Step 4: structured_scorer.calculate_score() -> services/scoring.py -> Calculate scores
-> Step 5: _calculate_completeness_scores() -> Measure profile completeness
-> Step 6: _blend_scores() -> Combine all scores with weights
-> Step 7: _band_candidates() -> Group into high/medium/low bands
-> Step 8: explanation_generator.generate() -> services/explanation.py -> Create explanations
-> Cache results in Redis -> Return ranked candidates with explanations
```

---

#### **`ontology.py`** - Skills Extraction & Expansion 🎯
**What it does:** Extracts skills from text and expands skill lists using a skills taxonomy.

**Key concepts:**
- **Ontology**: A structured list of concepts and their relationships
- **NER (Named Entity Recognition)**: AI that finds entities in text (like skills)
- **spaCy**: A Python library for natural language processing
- **Skill Expansion**: Finding related skills (e.g., "Python" → "Python3", "Python Programming")

**Main functionalities:**
1. Extracts skills from resume text
2. Matches extracted skills to ontology
3. Expands skill lists (finds related skills)
4. Returns standardized skill names

**Why it's needed:** 
- Resumes mention skills in different ways ("Python programming" vs "Python dev")
- Jobs might say "ML" but candidates have "Machine Learning"
- Skill expansion bridges these gaps for better matching!

**Example:**
```
Resume text: "Experienced in Python, Django, and REST APIs"
→ Extracted skills: ["Python", "Django", "REST API"]

Job requires: "Python"
→ Expanded to: ["Python", "Python3", "Python Programming"]
→ Matches candidate's "Python" skill!
```

**📎 Used By (Dependencies):**
- `services/ingestion.py` -> Uses `extract_skills_from_text()` to find skills in resumes
- `services/job_embeddings.py` -> Uses `expand_skills()` to expand job skill requirements
- `api/admin.py` -> Uses `is_spacy_available()` to check if spaCy is installed

**📎 This File Uses:**
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow:**
```
ingestion.py -> extract_skills_from_text(resume_text)
-> ontology.py -> Extracts skills using spaCy or pattern matching
-> Returns list of standardized skills -> ingestion.py stores in vector metadata

job_embeddings.py -> expand_skills(skill_list)
-> ontology.py -> Expands each skill to related skills
-> Returns expanded skill list -> job_embeddings.py uses for embedding
```

**🌐 Invoked By FastAPI Endpoints:**
- Not directly invoked by API endpoints
- Called through the skill extraction chain:
  - `POST /api/v1/webhooks/candidate-updated` → `ingestion.py` → `skill_extractor.py` → `ontology.py`
  - `POST /api/v1/candidates/upload-resume` → `ingestion.py` → `skill_extractor.py` → `ontology.py`
  - `POST /api/v1/candidates/` → `ingestion.py` → `skill_extractor.py` → `ontology.py`

---

#### **`skill_extractor.py`** - Unified Skill Extraction Interface 🎯
**What it does:** Provides a single, unified interface for extracting skills from text using multiple methods.

**Key concepts:**
- **Method Selection**: Choose between "hybrid", "llm", or "spacy" extraction methods
- **Hybrid Approach**: Combines LLM and spaCy for best accuracy (~90%)
- **Normalization**: All extracted skills are normalized through ontology

**Main functionalities:**
1. Extracts skills using selected method
2. Merges results from multiple sources (in hybrid mode)
3. Normalizes all skills through ontology
4. Returns consistent `List[str]` format

**Why it's needed:**
- Provides ONE entry point for all skill extraction
- Allows easy switching between extraction methods
- Ensures consistent output format across all pipelines

**Example:**
```python
# Extract skills using hybrid method (LLM + spaCy)
skills = await extract_skills(resume_text, method="hybrid")
# Returns: ["Python", "Django", "PostgreSQL", "AWS"]

# Extract skills using spaCy only (faster, lower accuracy)
skills = await extract_skills(resume_text, method="spacy")
```

**📎 Used By (Dependencies):**
- `services/ingestion.py` -> Uses `extract_skills()` for all skill extraction
- `services/llm_parser.py` -> Called by skill_extractor when `method="llm"` or `method="hybrid"`

**📎 This File Uses:**
- `services/ontology.py` -> `extract_skills_from_text()`, `normalize_skill()` for spaCy extraction
- `services/llm_parser.py` -> `LLMResumeParser` for LLM extraction
- `config.py` -> `settings` for checking `USE_LLM_PARSING`

**🔄 Complete Call Flow:**
```
ingestion.py -> extract_skills(text, method="hybrid")
-> skill_extractor.py -> Checks method type
   -> If hybrid: calls llm_parser.py AND ontology.py
   -> If llm: calls llm_parser.py only
   -> If spacy: calls ontology.py only
-> Normalizes all skills through ontology.normalize_skill()
-> Returns deduplicated List[str] -> ingestion.py stores skills
```

**🌐 Invoked By FastAPI Endpoints:**
- `POST /api/v1/webhooks/candidate-updated` ([webhooks.py](backend/app/api/webhooks.py))
  → `enqueue_job()` → background worker → `ingestion.py` → `skill_extractor.py`
- `POST /api/v1/candidates/upload-resume` ([candidates.py](backend/app/api/candidates.py))
  → `ingestion.py` → `skill_extractor.py`
- `POST /api/v1/candidates/` ([candidates.py](backend/app/api/candidates.py))
  → `ingestion.py` → `skill_extractor.py`

---

#### **`llm_parser.py`** - LLM Resume Parser 🤖
**What it does:** Extracts ALL fields from a resume using a local LLM (Large Language Model).

**Key concepts:**
- **LLM**: A large language model that can understand and extract information from text
- **Structured Output**: Extracts specific fields like name, email, skills in a structured format
- **JSON Schema**: Uses JSON schema to ensure consistent output format

**Main functionalities:**
1. Parses entire resume using local LLM (Qwen2.5-0.5B - lightweight 500M parameter model)
2. Extracts: full_name, email, phone, location, years_experience, professional_summary, skills
3. Returns structured dictionary with all extracted fields

**Why it's needed:**
- Much better accuracy than regex for extracting contact information
- Can understand context and extract relevant information
- Returns consistent structured output across all resumes

**Example:**
```python
parser = LLMResumeParser()
result = await parser.parse_resume(resume_text)
# Returns:
# {
#   "full_name": "John Doe",
#   "email": "john@example.com",
#   "phone": "+1-555-1234",
#   "location": {"city": "SF", "region": "CA", "country": "US"},
#   "years_experience": 5.0,
#   "professional_summary": "Experienced software engineer...",
#   "skills": ["Python", "Django", "AWS"]
# }
```

**📎 Used By (Dependencies):**
- `services/ingestion.py` -> Uses `parse_resume()` in parse-only mode
- `services/skill_extractor.py` -> Uses for LLM skill extraction when `method="llm"` or `method="hybrid"`

**📎 This File Uses:**
- `config.py` -> `settings` for model configuration
- `utils/logging.py` -> `logger` for logging

**🔄 Complete Call Flow:**
```
ingestion.py (parse-only mode) -> llm_parser.parse_resume(text)
-> llm_parser.py -> Loads LLM model
-> Sends prompt with JSON schema -> LLM generates structured output
-> Parses JSON response -> Returns dict with all fields
-> ingestion.py caches in Redis for form pre-fill
```

**🌐 Invoked By FastAPI Endpoints:**
- `POST /api/v1/webhooks/candidate-updated` ([webhooks.py](backend/app/api/webhooks.py))
  → `enqueue_job()` → background worker → `ingestion.py` → `llm_parser.py` (when `USE_LLM_PARSING=true`)
- `POST /api/v1/candidates/upload-resume` ([candidates.py](backend/app/api/candidates.py))
  → `ingestion.py` → `llm_parser.py` (parse-only mode)
- `POST /api/v1/candidates/` ([candidates.py](backend/app/api/candidates.py))
  → `ingestion.py` → `llm_parser.py` (full mode)

---

#### **`chatbot.py`** - AI Chatbot 🤖
**What it does:** (Likely) Provides a chatbot that can answer questions about candidates.

**Note:** This probably uses:
- RAG (Retrieval-Augmented Generation): AI that searches your data to answer questions
- WebSockets: For real-time communication

---

#### **`metrics.py`** - Performance Tracking 📊
**What it does:** Tracks system performance metrics.

**Key concepts:**
- **Metrics**: Measurements of system performance
- **Counter**: A metric that only goes up (like "jobs processed")
- **Timer**: A metric that measures how long something takes

**Main functionalities:**
1. Tracks job success/failure counts
2. Tracks timing for each pipeline stage
3. Provides metrics for monitoring

**Why it's needed:** You need to know if your system is working well! Metrics help you spot problems.

---

### 📂 `backend/app/utils/` - Helper Functions 🛠️

This folder contains utility functions - small, reusable pieces of code.

#### **`logging.py`** - Logging Setup 📝
**What it does:** Sets up logging for your application.

**Key concepts:**
- **Logging**: Recording what your application does (for debugging)
- **Logger**: A tool that writes log messages

**Why it's needed:** When something breaks, logs help you figure out what went wrong!

**📎 Used By (Dependencies):**
- `main.py` -> Uses `logger` for application logs
- `database.py` -> Uses `logger` for database logs
- `services/ingestion.py` -> Uses `logger` for pipeline logs
- `services/redis_client.py` -> Uses `logger` for Redis logs
- `services/s3_client.py` -> Uses `logger` for S3 logs
- `api/webhooks.py` -> Uses `logger` for webhook logs

**📎 This File Uses:**
- `config.py` -> `settings` for log level configuration

**🔄 Complete Call Flow:**
```
Any file -> from app.utils.logging import logger
-> logging.py -> logger object (configured on import)
-> logger.info("message") -> Writes log message
-> Log appears in console/file -> Developer sees what happened
```

---

#### **`skills.py`** - Skills Utilities 🎯
**What it does:** (Likely) Helper functions for working with skills.

---

### 📂 `backend/tests/` - Testing Suite 🧪

This folder contains tests to make sure everything works correctly.

**Key concepts:**
- **Testing**: Writing code that checks if your code works
- **Unit Test**: Tests a single function
- **Integration Test**: Tests how multiple parts work together

**Why it's needed:** Tests catch bugs before users do!

**Example test files:**
- `test_api.py`: Tests API endpoints
- `test_ranking.py`: Tests ranking algorithm
- `test_parsers.py`: Tests document parsing

---

### 📂 `backend/requirements.txt` - Dependencies 📦
**What it does:** Lists all Python packages your project needs.

**Key concepts:**
- **Dependencies**: External code libraries your project uses
- **Package**: A bundle of code you can install

**Why it's needed:** When someone else wants to run your project, they need to install all these packages!

**Example packages:**
- `fastapi`: Web framework
- `sqlalchemy`: Database toolkit
- `sentence-transformers`: AI models
- `qdrant-client`: Vector database client

---

## 📥 Data Ingestion Workflows

### **What is Data Ingestion?**
**Data ingestion** is the process of importing, transferring, loading, and processing data for immediate use or storage in a database. In RightStaff, we have multiple ways data enters the system.

### **Why Multiple Pipelines?**
Different sources require different processing:
- **Webhooks**: External systems notify us (Portal Team)
- **API Uploads**: Users upload directly via frontend
- **Scripts**: Developers populate test data

### **Complete Ingestion Documentation**
For comprehensive details about all ingestion pipelines, data flow, and database schemas, see:
- **[INGESTION_PIPELINES.md](./INGESTION_PIPELINES.md)** - Complete pipeline documentation
- **[TESTING_INGESTION_PIPELINES.md](./TESTING_INGESTION_PIPELINES.md)** - Testing guide with commands

### **Quick Overview: 4 Ingestion Pipelines**

#### **Pipeline 1: Candidate Resume Webhook Ingestion** 📥
**When:** Portal Team sends webhook notification
**Trigger:** Candidate uploads resume on Portal Team's system

**Flow:**
```
Webhook → Validate → Queue in Redis → Background Worker → 7-Stage Pipeline
```

**7-Stage Enrichment Pipeline:**
1. Fetch candidate from PostgreSQL
2. Download resume from MinIO
3. Parse resume (extract text)
4. Extract skills (LLM hybrid if enabled, spaCy fallback)
5. Chunk text (split into pieces)
6. Generate embeddings (convert to vectors)
7. Store in Qdrant (save for semantic search)

**LLM Support:** When `USE_LLM_PARSING=true`, uses hybrid method (LLM + spaCy) for better skill extraction accuracy. Disabled by default.

**Databases Used:**
- **PostgreSQL**: Read candidate, write skills
- **MinIO**: Read resume file
- **Redis**: Queue job
- **Qdrant**: Write vectors

**File:** `backend/app/api/webhooks.py:28-88`

---

#### **Pipeline 2: Candidate Resume Upload via API** 📤
**When:** User uploads resume via frontend
**Trigger:** User interaction on website

**3-Stage Process:**

**Stage 1: Upload & Parse** (`parse_only` mode)
```
Upload File → MinIO → Queue Parse Job → Extract Fields → Cache in Redis
```
- Extracts: name, email, phone, skills, location, experience
- Uses LLM if enabled (Qwen), regex fallback
- Caches for 1 hour
- **NO PostgreSQL or Qdrant writes**

**Stage 2: Get Parsed Data**
```
Frontend → Fetch from Redis → Pre-fill Form
```

**Stage 3: Create Candidate** (`full` mode)
```
Submit Form → Create in PostgreSQL → Queue Full Job → 7-Stage Pipeline
```

**Why 3 Stages?**
- **Stage 1**: Fast feedback (user sees extracted data immediately)
- **Stage 2**: Form pre-fill (better UX)
- **Stage 3**: Full processing (happens in background)

**Databases Used:**
- **Stage 1**: MinIO (write), Redis (cache)
- **Stage 2**: Redis (read)
- **Stage 3**: PostgreSQL (write), Redis (queue), Qdrant (write via worker)

**File:** `backend/app/api/candidates.py`

---

#### **Pipeline 3: Job Ingestion via Webhook** 💼
**When:** Portal Team creates/updates job posting
**Trigger:** New job or job update

**Flow:**
```
Webhook → Expand Skills → Generate Embeddings → Store in Qdrant + Cache
```

**Processing:**
1. Normalize skills (e.g., "python" → "Python")
2. Expand skills (e.g., "Python" → ["Python", "Python3", "Python Programming"])
3. Generate 2 embeddings:
   - Profile embedding (title + description)
   - Skills embedding (expanded skills)
4. Store in Qdrant `jobs_v1` collection
5. Cache in Redis (1-hour TTL)

**Why Separate Collection?**
- Jobs change less frequently than candidates
- Semantic matching compares job vectors vs candidate vectors

**Databases Used:**
- **Qdrant**: Write to `jobs_v1` collection (2 points per job)
- **Redis**: Cache embeddings

**File:** `backend/app/api/webhooks.py:108-257`

---

#### **Pipeline 4: Dummy Data Population** 🧪
**When:** Developer runs script manually
**Trigger:** `python populate_dummy_data.py`

**Flow:**
```
Create Jobs → Create Skills → Create Candidates → Generate Embeddings →
Upload Resumes → Create Job Embeddings → Create Applications
```

**What It Creates:**
- **PostgreSQL**: 6 jobs, 50 skills, 8 candidates, 30 applications
- **Qdrant**: 24 candidate vectors + 12 job vectors
- **MinIO**: 5 resume files (3 candidates without resumes for testing)

**Why Important?**
- Provides realistic test data
- Tests all integrations
- Verifies system health

**File:** `backend/populate_dummy_data.py`

---

### **Data Flow Across All Databases**

```
┌─────────────────────────────────────────────────────┐
│           INGESTION SOURCES                         │
├─────────────────────────────────────────────────────┤
│  • Portal Team Webhooks                             │
│  • Frontend API Calls                               │
│  • Manual Scripts                                   │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│           PROCESSING LAYER                          │
├─────────────────────────────────────────────────────┤
│  Parse → Extract → Normalize → Chunk → Embed       │
└──────────────┬──────────────────────────────────────┘
               │
       ────────┼─────────────────────────
       │       │           │            │
       ▼       ▼           ▼            ▼
  ┌────────┐ ┌────────┐ ┌──────┐ ┌──────────┐
  │Postgres│ │ Qdrant │ │Redis │ │  MinIO   │
  │        │ │        │ │      │ │          │
  │Struct- │ │Vector  │ │Cache │ │  Files   │
  │ured    │ │Search  │ │Queue │ │ (Resumes)│
  │Data    │ │        │ │      │ │          │
  └────────┘ └────────┘ └──────┘ └──────────┘
```

### **Database Roles**

**PostgreSQL** - Source of Truth
- Stores: Candidates, Jobs, Skills, Applications, Contact Info
- Used For: SQL filtering, data validation, relationships

**Qdrant** - Semantic Search Engine
- Stores: Embeddings (384-dim vectors)
- Used For: Finding similar candidates/jobs by meaning
- Collections:
  - `resumes`: Candidate vectors (profile + skills + chunks)
  - `jobs_v1`: Job vectors (profile + skills)

**Redis** - Speed Layer
- Stores: Job queues, cached results, temporary data
- Used For: Async processing, fast lookups, session data
- TTL: Usually 1 hour (3600 seconds)

**MinIO** - File Storage
- Stores: Resume files (PDF, DOCX, TXT)
- Used For: Source documents for parsing
- Format: `resumes/{candidate_id}/resume.{ext}`

### **Schema Consistency Across Pipelines**

All pipelines follow these rules:

1. **Skills**: Always `List[str]`, normalized through ontology
2. **Location**: PostgreSQL uses separate fields (city, region, country)
3. **IDs**: UUIDs in PostgreSQL, strings in Qdrant/Redis
4. **Timestamps**: ISO 8601 format in Qdrant/Redis
5. **Vectors**: Always 384 dimensions (sentence-transformers model)

### **Common Ingestion Pattern**

Most pipelines follow this pattern:

```python
# 1. Validate input
if not candidate_exists:
    raise HTTPException(404, "Not found")

# 2. Queue job (async processing)
job_data = {"job_id": ..., "candidate_id": ..., "mode": "full"}
await redis_client.lpush("ingestion_queue", json.dumps(job_data))

# 3. Return immediately (don't wait!)
return {"status": "accepted", "job_id": ...}

# 4. Background worker processes later
# Worker polls Redis → Downloads file → Parses → Embeds → Stores
```

**Why This Pattern?**
- **Fast response**: User doesn't wait 30+ seconds
- **Reliable**: Jobs are queued even if processing is slow
- **Scalable**: Can process many jobs concurrently
- **Resilient**: Failed jobs retry automatically (up to 5 times)

### **Testing Ingestion Pipelines**

**Quick Test:**
```bash
# Clear all data
cd backend
../venv/Scripts/python clear_all_data.py

# Populate test data (tests all pipelines!)
../venv/Scripts/python populate_dummy_data.py

# Verify data
../venv/Scripts/python check_database.py
```

**For detailed testing instructions**, see [TESTING_INGESTION_PIPELINES.md](./TESTING_INGESTION_PIPELINES.md)

---

## 🗄️ GROUP 2: Database Setup

### 📂 `database/scripts/` - Database Scripts 📜

This folder contains SQL scripts that set up your database.

#### **`01_schema.sql`** - Database Structure
**What it does:** Creates all the database tables and structure.

**Key concepts:**
- **Schema**: The structure of your database (what tables exist, what columns they have)
- **SQL**: Language for talking to databases

**Why it's needed:** Your database needs to know what tables to create!

---

#### **`02_seed_smoketest.sql`** - Test Data
**What it does:** Adds some test data to verify everything works.

**Why it's needed:** You need data to test with!

---

#### **`05_dummy_data.sql`** - Sample Data
**What it does:** Adds realistic sample data (candidates, jobs, etc.)

**Why it's needed:** For development and testing, you need sample data!

---

## 🐳 GROUP 3: Docker Configuration

### 📂 `docker/docker-compose.yml` - Container Setup 🐳

**What it does:** Defines all the services your application needs (databases, storage, etc.)

**Key concepts:**
- **Docker**: A tool that packages applications and their dependencies
- **Container**: A lightweight virtual machine
- **Docker Compose**: A tool to run multiple containers together

**Services defined:**
1. **PostgreSQL**: Your main database
2. **Qdrant**: Your vector database
3. **Redis**: Your cache and queue
4. **MinIO**: Your file storage

**Why it's needed:** Instead of installing all these services manually, Docker does it for you!

**Example:**
```yaml
postgres:
  image: postgres:18-alpine
  ports:
    - "5432:5432"
```
This says: "Run PostgreSQL, and make it accessible on port 5432"

---

## 💾 GROUP 4: Data Storage

### 📂 `data/` - Stored Data 💾

This folder contains all the data your services store.

**Subfolders:**
- **`postgres/`**: PostgreSQL data files
- **`qdrant/`**: Qdrant vector database files
- **`redis/`**: Redis cache files
- **`minio/`**: MinIO file storage

**Why it's needed:** All your databases need somewhere to store their data!

---

## 🧪 GROUP 5: Testing & Scripts

### 📂 `scripts/` - Helper Scripts 🔧

This folder contains utility scripts for maintenance tasks.

**Example scripts:**
- `clean_ingestion.py`: Cleans up ingestion data
- `fix_retry_logic.py`: Fixes retry logic issues
- `apply_retry_fix.py`: Applies retry logic fixes

**Why it's needed:** Sometimes you need to run one-off tasks. Scripts make it easy!

### 📂 `backend/` - Utility Scripts (Root Level) 🛠️

These are utility scripts located in the `backend/` folder root for development and debugging:

**Example scripts:**
- `check_database.py`: Checks database connection and schema
- `check_enum_schema.py`: Validates enum types in database
- `clear_all_data.py`: Clears all data from databases (use with caution!)
- `diagnose_all.py`: Comprehensive system diagnostics
- `populate_dummy_data.py`: Populates database with test data
- `test_api_quick.py`: Quick API testing script
- `test_day4_quick.py`: Quick Day 4 feature testing
- `test_day4_e2e_adaptive.py`: End-to-end adaptive testing

**Why they're needed:** These scripts help with development, debugging, and testing. They're not part of the main application but are useful tools!

---

## 📚 GROUP 6: Documentation

### 📂 `docs/` - Documentation 📖

This folder contains project documentation.

**Files:**
- `REORGANIZATION_SUMMARY.md`: Summary of project reorganization
- `TESTING-QUICK-START.md`: Quick guide for testing

**Why it's needed:** Documentation helps people understand your project!

---

## 🔄 How Everything Works Together

Now that you understand the pieces, let's see how they work together!

### **Scenario 1: A Candidate Uploads a Resume** 📄

```
1. Portal Team → Webhook → backend/app/api/webhooks.py
   "Hey! Candidate 123 just uploaded a resume!"

2. webhooks.py → Validates candidate exists → Queues job in Redis
   "Job queued! Processing will happen in background"

3. Background Worker (ingestion.py) → Polls Redis queue
   "I see a new job! Let me process it..."

4. Ingestion Pipeline:
   a. Fetch candidate from PostgreSQL (database.py)
   b. Download resume from MinIO (s3_client.py)
   c. Parse resume (parsers.py) → Extract text
   d. Extract skills (ontology.py) → Find skills in text
   e. Chunk text (parsers.py) → Split into pieces
   f. Generate embeddings (embeddings.py) → Convert to vectors
   g. Store in Qdrant (vector_store.py) → Save vectors

5. Done! Resume is now searchable!
```

### **Scenario 2: Someone Wants to Rank Candidates for a Job** 🎯

```
1. User → POST /api/v1/jobs/rank → backend/app/api/jobs.py
   "Find me candidates for job 456"

2. jobs.py → ranking_service.rank_candidates() → services/ranking.py
   "Starting complete ranking pipeline..."

3. ranking.py → Fetch job data from PostgreSQL
   "Job 456 requires: Python, 5+ years, Remote"

4. ranking.py → sql_filter.py → SQL Gating
   "Find all candidates with Python AND 5+ years AND Remote"
   → Returns eligible candidate IDs

5. ranking.py → job_embeddings.py → Generate Job Embeddings
   "Create embeddings for job description and skills"
   → Profile embedding + Skills embedding (cached in Redis)

6. ranking.py → retrieval.py → Dense Retrieval
   "Search for semantically similar candidates"
   → Searches profile, skills, and chunk vectors
   → Combines scores (50% profile + 30% skills + 20% chunks)
   → Returns candidates with evidence chunks

7. ranking.py → scoring.py → Structured Scoring
   "Calculate objective scores for each candidate"
   → Skills coverage (35%) + Experience (20%) + Recency (15%) + Domain (10%) + Location (20%)
   → Returns structured scores

8. ranking.py → Calculate Completeness Scores
   "Measure profile completeness"
   → Resume (25%) + Skills (20%) + Experience (20%) + Contact (15%) + Summary (20%)

9. ranking.py → Blend All Scores
   "Combine all scoring components"
   → Final = 40% dense + 35% structured + 25% completeness

10. ranking.py → Band Candidates
    "Group into confidence levels"
    → High (top 20%) / Medium (20-60%) / Low (bottom 40%)

11. ranking.py → explanation.py → Generate Explanations
    "Create human-readable explanations"
    → Summary + Reasons + Evidence snippets

12. ranking.py → Cache results in Redis
    "Save this ranking so we don't have to recalculate"

13. jobs.py → Return results
    "Here are the top candidates with explanations!"
```

### **Scenario 3: System Monitoring** 📊

```
1. Admin → GET /api/v1/admin/metrics → backend/app/api/admin.py
   "Show me system health"

2. admin.py → metrics.py → Get metrics
   "Jobs processed: 1000, Success rate: 98%"

3. admin.py → redis_client.py → Check DLQ depth
   "Failed jobs: 5"

4. admin.py → Return metrics
   "System is healthy!"
```

---

## 🎓 Key Concepts Explained

### **API (Application Programming Interface)**
Think of an API as a **menu** at a restaurant. The menu tells you what you can order (endpoints), and the kitchen (backend) prepares it for you.

**Example:**
- Endpoint: `GET /api/v1/jobs/rankings`
- This is like ordering "Show me job rankings"
- The API returns the data you requested

---

### **Database**
A database is like a **digital filing cabinet**. It stores data in an organized way.

**Types in your project:**
1. **PostgreSQL**: Relational database (stores candidates, jobs, skills)
2. **Qdrant**: Vector database (stores embeddings for semantic search)
3. **Redis**: In-memory database (stores cache and queues)

---

### **Queue**
A queue is like a **line at a coffee shop**. Jobs wait in line to be processed.

**In your project:**
- Jobs are added to Redis queue when webhooks arrive
- Background worker processes jobs one by one
- If a job fails, it retries (up to 5 times)
- If it still fails, it goes to DLQ (Dead Letter Queue)

---

### **Vector / Embedding**
A vector is a **list of numbers** that represents the meaning of text.

**Example:**
```
Text: "Python developer"
Vector: [0.123, -0.456, 0.789, ..., 0.012] (384 numbers)

Why? Computers can't understand words, but they can compare numbers!
Similar text → Similar vectors → Easy to find matches!
```

---

### **Semantic Search**
Semantic search finds results based on **meaning**, not just keywords.

**Example:**
```
Search: "software engineer"
Finds: "Python developer", "Backend engineer", "Full-stack dev"
(Even though they don't contain "software engineer"!)
```

---

### **Async / Asynchronous** ⚡
Async means **"don't wait"**. Your app can do multiple things at once, like a smart multitasker!

#### **The Real-World Analogy: Restaurant vs. Coffee Shop**

**Synchronous (Blocking) - Like a Restaurant:**
Imagine you're at a fancy restaurant where the waiter takes your order, then **stands there and waits** while the chef cooks your food. The waiter can't help other customers until your food is ready. This is slow and inefficient!

```
Waiter: "I'll take your order"
Chef: [Cooking for 30 minutes...]
Waiter: [Standing and waiting... doing nothing]
Other customers: [Waiting... frustrated]
Waiter: "Here's your food!" (30 minutes later)
```

**Asynchronous (Non-Blocking) - Like a Coffee Shop:**
Now imagine a busy coffee shop. The barista takes your order, gives you a ticket number, and immediately helps the next customer. While your coffee is being made, they're taking other orders, making other drinks, and handling multiple customers at once!

```
Barista: "Order #42! I'll make your latte"
Barista: [Starts making coffee, but also...]
Barista: "Next customer! What can I get you?"
Barista: [Making multiple drinks at once]
Barista: "Order #42 ready!" (while still helping others)
```

#### **In Programming Terms:**

**Synchronous Code (Blocking):**
```python
# This code waits for each step to finish before moving to the next
def process_resume():
    download_file()      # Wait 10 seconds...
    parse_file()        # Wait 5 seconds...
    generate_embedding() # Wait 15 seconds...
    save_to_database()  # Wait 2 seconds...
    return result       # Total: 32 seconds of waiting!
```

**Asynchronous Code (Non-Blocking):**
```python
# This code can do other things while waiting
async def process_resume():
    await download_file()      # Start downloading, but don't wait!
    # Can do other things here while file downloads
    await parse_file()         # Start parsing, but don't wait!
    # Can handle other requests while parsing
    await generate_embedding() # Start embedding, but don't wait!
    # Server stays responsive!
    await save_to_database()
    return result
```

#### **Why Async is Important in Your Project:**

**Example 1: Webhook Processing**
```
Synchronous (Bad):
1. Webhook arrives: "New resume uploaded!"
2. Server: "Let me process this..." [30 seconds of work]
3. User waits... and waits... and waits...
4. Server: "Done!" (30 seconds later)
5. User: "This is too slow!" 😤

Asynchronous (Good):
1. Webhook arrives: "New resume uploaded!"
2. Server: "Got it! I'll process this in the background" (0.1 seconds)
3. Server: "Here's your confirmation!" (immediate response)
4. Background worker: [Processing resume...]
5. User: "Great! Fast response!" 😊
```

**Example 2: Handling Multiple Requests**
```
Synchronous Server:
Request 1 → Process (30s) → Done
Request 2 → [Waiting...] → Process (30s) → Done
Request 3 → [Waiting...] → [Waiting...] → Process (30s) → Done
Total time: 90 seconds for 3 requests

Asynchronous Server:
Request 1 → Start processing → [Can handle others]
Request 2 → Start processing → [Can handle others]
Request 3 → Start processing → [Can handle others]
All finish around the same time!
Total time: ~30 seconds for 3 requests (3x faster!)
```

#### **Key Async Concepts:**

1. **`async def`**: Marks a function as asynchronous
   ```python
   async def my_function():
       # This function can be paused and resumed
   ```

2. **`await`**: Pauses execution until something completes, but allows other code to run
   ```python
   result = await download_file()
   # While waiting for download, other code can run!
   ```

3. **Event Loop**: The "manager" that coordinates all async tasks
   - Like a traffic controller at an intersection
   - Makes sure everything runs smoothly

#### **In Your RightStaff Project:**

**Where Async is Used:**
- **FastAPI routes**: Can handle multiple requests simultaneously
- **Database queries**: Don't block while waiting for database responses
- **File downloads**: Can download files while doing other work
- **Background workers**: Process jobs without blocking the main server

**Real Example from Your Code:**
```python
# From webhooks.py - This is async!
@router.post("/candidate-updated")
async def candidate_updated_webhook(payload: WebhookPayload):
    # Validate candidate (async database query)
    candidate = await db.execute(select(Candidate)...)
    
    # Queue job in Redis (async)
    await redis_client.lpush("ingestion_queue", job_data)
    
    # Return immediately - don't wait for processing!
    return {"status": "accepted"}  # Fast response!
```

**The Magic:**
- User gets instant response: "Job queued!"
- Background worker processes the job later
- Server stays fast and responsive
- Multiple users can be helped at once!

#### **Think of it Like This:**
- **Synchronous** = One person doing one task at a time (slow)
- **Asynchronous** = One person juggling multiple tasks (fast!)

**Bottom Line:** Async makes your application **fast, efficient, and able to handle many users at once!** 🚀

---

### **Cache**
A cache is like a **short-term memory**. It stores frequently accessed data for quick retrieval.

**Example:**
```
First request: Calculate ranking (takes 5 seconds) → Cache result
Second request: Get from cache (takes 0.01 seconds) → Super fast!
```

---

### **Docker**
Docker is like a **shipping container** for software. It packages everything your app needs to run.

**Benefits:**
- Works the same on any computer
- Easy to set up (just run `docker-compose up`)
- Isolates services (PostgreSQL, Redis, etc.)

---

## 🚀 How to Use This Project

### **Starting the Project:**
```bash
# 1. Start all services (PostgreSQL, Redis, Qdrant, MinIO)
make start

# 2. Start the backend server
cd backend
uvicorn app.main:app --reload
```

### **Accessing the API:**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### **Common Tasks:**
```bash
# View logs
make logs

# Run tests
make test

# Load dummy data
make db-dummy
```

---

## 🎯 Summary

Your RightStaff project is a **sophisticated AI-powered candidate ranking system**! Here's what makes it special:

1. **Modular Design**: Each piece has a specific job (models, services, API)
2. **Async Processing**: Fast responses using background workers
3. **AI-Powered**: Uses embeddings and semantic search
4. **Production-Ready**: Has retry logic, caching, monitoring, and tests
5. **Well-Organized**: Clear separation of concerns

**The Complete Flow:**
```
Resume Upload → Webhook → Queue → Parse → Extract Skills → Chunk → Embed → Store in Qdrant
                                                                              ↓
Job Posting → Generate Job Embeddings → SQL Gating → Dense Retrieval → Structured Scoring
                                                                              ↓
→ Score Blending → Banding → Explanation Generation → Return Ranked Results with Explanations
```

**Key Technologies:**
- **FastAPI**: Web framework
- **PostgreSQL**: Main database
- **Qdrant**: Vector database
- **Redis**: Cache and queue
- **MinIO**: File storage
- **sentence-transformers**: AI models

---

## 🎓 Next Steps

Now that you understand the structure:

1. **Explore the code**: Open files and read the comments
2. **Run the project**: Start it up and try the API
3. **Read the tests**: Tests show you how things are supposed to work
4. **Modify something**: Try adding a new endpoint or feature
5. **Ask questions**: When you're stuck, ask for help!

Remember: **Programming is a journey, not a destination!** Every expert was once a beginner. Keep learning, keep building, and most importantly - have fun! 🚀

---

**Happy Coding!** 💻✨

