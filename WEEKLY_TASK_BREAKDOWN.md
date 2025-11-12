# 📅 RightStaff AI - 4-Week Task Breakdown

This document organizes all completed and incomplete tasks into a logical 4-week implementation timeline.

---

## Week 1: Foundation & Infrastructure Setup ✅ (COMPLETED)

**Goal:** Establish core infrastructure and basic data ingestion capabilities.

### Task 1: Docker Environment & Database Setup ✅
- **Sub-tasks:**
  - ✅ Docker Compose configuration (PostgreSQL, Qdrant, Redis, MinIO)
  - ✅ Database schema creation (`01_schema.sql`)
  - ✅ Database connection setup (async SQLAlchemy)
  - ✅ Environment configuration management (`config.py`)
  - ✅ Health check endpoints for all services
- **Status:** Fully completed
- **Dependencies:** None (foundation)

### Task 2: Core Service Infrastructure ✅
- **Sub-tasks:**
  - ✅ FastAPI application setup with CORS middleware
  - ✅ Structured logging system (`utils/logging.py`)
  - ✅ Database models (Candidate, Job, Skill, CandidateSkill)
  - ✅ Redis client setup (`services/redis_client.py`)
  - ✅ MinIO/S3 client setup (`services/s3_client.py`)
  - ✅ Qdrant vector store client setup (`services/vector_store.py`)
- **Status:** Fully completed
- **Dependencies:** Task 1

### Task 3: Basic Document Parsing & Chunking ✅
- **Sub-tasks:**
  - ✅ Document parser implementation (PDF, DOCX, TXT support)
  - ✅ Text extraction using Unstructured library
  - ✅ Sentence-aware chunking algorithm (400 chars, 50 overlap)
  - ✅ Metadata extraction (format, page count, char count)
- **Status:** Fully completed
- **Dependencies:** Task 2

### Task 4: Embedding Service Foundation ✅
- **Sub-tasks:**
  - ✅ Embedding service setup (`services/embeddings.py`)
  - ✅ Sentence-transformer model integration (all-MiniLM-L6-v2)
  - ✅ Lazy model loading with device detection (CUDA/MPS/CPU)
  - ✅ Batch embedding support
  - ✅ Vector normalization for cosine similarity
- **Status:** Fully completed
- **Dependencies:** Task 2

---

## Week 2: Advanced Ingestion & SQL Filtering ✅ (COMPLETED)

**Goal:** Complete the ingestion pipeline and implement SQL-based candidate filtering.

### Task 1: Complete 7-Stage Ingestion Pipeline ✅
- **Sub-tasks:**
  - ✅ Stage 1: Candidate data fetching from PostgreSQL
  - ✅ Stage 2: Resume download from MinIO
  - ✅ Stage 3: Document parsing (text extraction)
  - ✅ Stage 4: Skills extraction from resume text
  - ✅ Stage 5: Text chunking with overlap
  - ✅ Stage 6: Batch embedding generation
  - ✅ Stage 7: Vector storage in Qdrant with metadata
- **Status:** Fully completed
- **Dependencies:** Week 1, Task 3 & 4

### Task 2: Background Worker & Queue System ✅
- **Sub-tasks:**
  - ✅ Background ingestion worker implementation
  - ✅ Redis queue integration (LPUSH/BRPOP)
  - ✅ Automatic worker startup on FastAPI initialization
  - ✅ Continuous polling loop with timeout
  - ✅ Job tracking (processed/failed counters)
- **Status:** Fully completed
- **Dependencies:** Week 1, Task 2

### Task 3: Skills Extraction & Ontology System ✅
- **Sub-tasks:**
  - ✅ spaCy NER integration for entity extraction
  - ✅ Pattern matching for technical terms (languages, frameworks, cloud)
  - ✅ Skills taxonomy loading and normalization
  - ✅ Fuzzy matching for skill name variants
  - ✅ Graceful degradation (works without spaCy)
- **Status:** Fully completed
- **Dependencies:** Week 1, Task 3

### Task 4: SQL-Based Candidate Filtering (Ontology Gating) ✅
- **Sub-tasks:**
  - ✅ Must-have skills filtering (AND logic with GROUP BY + HAVING)
  - ✅ Years of experience filtering (min/max range)
  - ✅ Location filtering (case-insensitive city matching)
  - ✅ Combined SQL gates with intersection logic
  - ✅ Performance optimization with database indexes
- **Status:** Fully completed
- **Dependencies:** Week 1, Task 1 & 2

### Task 5: Webhook Integration ✅
- **Sub-tasks:**
  - ✅ Webhook endpoint (`POST /api/v1/webhooks/candidate-updated`)
  - ✅ Candidate validation in PostgreSQL
  - ✅ Job queuing in Redis
  - ✅ Async response (202 Accepted)
  - ✅ Event type handling (profile_created, profile_updated, resume_uploaded)
- **Status:** Fully completed
- **Dependencies:** Week 2, Task 2

### Task 6: Retry Logic & Error Handling ✅
- **Sub-tasks:**
  - ✅ Exponential backoff retry mechanism (2s, 4s, 8s, 16s)
  - ✅ Max retry attempts (5 total)
  - ✅ Retriable vs permanent error detection
  - ✅ Dead Letter Queue (DLQ) implementation
  - ✅ DLQ management endpoints (replay, clear, status)
- **Status:** Fully completed
- **Dependencies:** Week 2, Task 1 & 2

### Task 7: Metrics & Monitoring System ✅
- **Sub-tasks:**
  - ✅ Metrics collector service (counters, timings, gauges)
  - ✅ Pipeline stage timing tracking
  - ✅ Success/failure job counters
  - ✅ Admin metrics endpoint (`GET /api/v1/admin/metrics`)
  - ✅ Detailed health check endpoint
- **Status:** Fully completed
- **Dependencies:** Week 2, Task 1

### Task 8: Job Management Endpoints ✅
- **Sub-tasks:**
  - ✅ Create job endpoint (`POST /api/v1/jobs/`)
  - ✅ Rank candidates endpoint (`POST /api/v1/jobs/rank`) - SQL gating only
  - ✅ Get rankings endpoint (`GET /api/v1/jobs/{job_id}/rankings`)
  - ✅ Redis caching for ranking results (1-hour TTL)
- **Status:** Partially completed (SQL gating done, semantic ranking pending)
- **Dependencies:** Week 2, Task 4

---

## Week 3: Semantic Search & Ranking Foundation 🔄 (PARTIALLY COMPLETED)

**Goal:** Implement vector-based semantic search and integrate it with SQL filtering.

### Task 1: Vector Search Implementation 🔄
- **Sub-tasks:**
  - ⏳ Implement `search()` method in `vector_store.py`
  - ⏳ Job description embedding generation
  - ⏳ Semantic similarity search in Qdrant
  - ⏳ Top-K candidate retrieval with similarity scores
  - ⏳ Metadata filtering (by candidate_id, skills, etc.)
  - ⏳ Score threshold filtering
- **Status:** Not started
- **Dependencies:** Week 1, Task 4; Week 2, Task 1

### Task 2: Dense Retrieval Integration 🔄
- **Sub-tasks:**
  - ⏳ Implement `_dense_retrieval()` in `ranking.py`
  - ⏳ Encode job description to vector
  - ⏳ Search Qdrant for top 50-100 candidates
  - ⏳ Combine with SQL-gated candidate IDs (intersection)
  - ⏳ Return candidates with similarity scores
- **Status:** Not started
- **Dependencies:** Week 3, Task 1; Week 2, Task 4

### Task 3: Structured Scoring System 🔄
- **Sub-tasks:**
  - ⏳ Implement `_structured_scoring()` in `ranking.py`
  - ⏳ Years of experience scoring (linear match)
  - ⏳ Location preference scoring (exact match or distance-based)
  - ⏳ Resume recency scoring (newer = better)
  - ⏳ Education level matching (if available)
  - ⏳ Combine scores with semantic similarity
- **Status:** Not started
- **Dependencies:** Week 3, Task 2

### Task 4: Basic Ranking Pipeline Integration 🔄
- **Sub-tasks:**
  - ⏳ Integrate semantic search into `rank_candidates()` endpoint
  - ⏳ Combine SQL gating + dense retrieval + structured scoring
  - ⏳ Return top candidates with combined scores
  - ⏳ Update caching to include semantic search results
  - ⏳ Testing with sample jobs and candidates
- **Status:** Not started
- **Dependencies:** Week 3, Task 2 & 3

### Task 5: Vector Store Search Testing ✅
- **Sub-tasks:**
  - ✅ Qdrant collection verification
  - ✅ Vector storage validation
  - ✅ Basic search functionality testing
- **Status:** Partially completed (infrastructure ready, search method pending)
- **Dependencies:** Week 1, Task 2

---

## Week 4: Advanced Ranking & Chatbot Features ⏳ (INCOMPLETE)

**Goal:** Implement cross-encoder re-ranking, explanations, and RAG-powered chatbot.

### Task 1: Cross-Encoder Re-Ranking ⏳
- **Sub-tasks:**
  - ⏳ Load bge-reranker-base model
  - ⏳ Implement `_cross_encoder_rerank()` in `ranking.py`
  - ⏳ Create job-candidate pairs for pairwise scoring
  - ⏳ Batch scoring for efficiency
  - ⏳ Re-sort candidates by cross-encoder scores
  - ⏳ Return top 20 re-ranked candidates
- **Status:** Not started
- **Dependencies:** Week 3, Task 4

### Task 2: Explanation Generation with Citations ⏳
- **Sub-tasks:**
  - ⏳ Implement `_generate_explanations()` in `ranking.py`
  - ⏳ Extract top matching chunks for each candidate
  - ⏳ Generate skills match summary
  - ⏳ Create experience match summary
  - ⏳ Build overall reasoning text
  - ⏳ Include citations to source resume chunks
- **Status:** Not started
- **Dependencies:** Week 4, Task 1

### Task 3: Complete Ranking Pipeline Integration ⏳
- **Sub-tasks:**
  - ⏳ Integrate cross-encoder re-ranking into main pipeline
  - ⏳ Add explanation generation to final results
  - ⏳ Update `rank_candidates()` to return full pipeline results
  - ⏳ Include citations in API response
  - ⏳ Update caching to store explanations
- **Status:** Not started
- **Dependencies:** Week 4, Task 1 & 2

### Task 4: RAG Chatbot - Context Retrieval ⏳
- **Sub-tasks:**
  - ⏳ Implement `retrieve_context()` in `chatbot.py`
  - ⏳ Encode user questions to vectors
  - ⏳ Search Qdrant with job-scoped filters
  - ⏳ Retrieve top-K relevant chunks
  - ⏳ Format context for LLM prompt
- **Status:** Not started
- **Dependencies:** Week 3, Task 1

### Task 5: RAG Chatbot - LLM Integration & Streaming ⏳
- **Sub-tasks:**
  - ⏳ Integrate OpenAI API (or local LLM)
  - ⏳ Implement `format_prompt()` with RAG context
  - ⏳ Implement `stream_response()` for token-by-token streaming
  - ⏳ Handle chat history for context
  - ⏳ Include citations in responses
- **Status:** Not started
- **Dependencies:** Week 4, Task 4

### Task 6: WebSocket Chatbot Endpoint ⏳
- **Sub-tasks:**
  - ⏳ Complete WebSocket handler in `chat.py`
  - ⏳ Connect to chatbot streaming service
  - ⏳ Handle client messages and disconnections
  - ⏳ Stream tokens back to client
  - ⏳ Send citations when response completes
  - ⏳ Error handling and graceful degradation
- **Status:** Partially completed (endpoint exists, functionality pending)
- **Dependencies:** Week 4, Task 5

### Task 7: Email Drafting Functionality ⏳
- **Sub-tasks:**
  - ⏳ Implement `draft_email()` in `chatbot.py`
  - ⏳ Retrieve candidate resume chunks
  - ⏳ Retrieve job description
  - ⏳ Generate personalized email using LLM
  - ⏳ Support multiple email types (outreach, interview, rejection)
  - ⏳ Include relevant candidate details (skills, experience)
- **Status:** Not started
- **Dependencies:** Week 4, Task 4 & 5

### Task 8: Email Drafting Endpoint ⏳
- **Sub-tasks:**
  - ⏳ Complete `POST /api/v1/chat/{job_id}/email/{candidate_id}` endpoint
  - ⏳ Integrate with `chatbot.draft_email()`
  - ⏳ Return formatted email content
  - ⏳ Error handling and validation
- **Status:** Partially completed (endpoint exists, functionality pending)
- **Dependencies:** Week 4, Task 7

### Task 9: Comprehensive Testing & Documentation ⏳
- **Sub-tasks:**
  - ⏳ Unit tests for ranking pipeline
  - ⏳ Integration tests for full ranking flow
  - ⏳ Chatbot functionality tests
  - ⏳ Fairness testing (bias detection)
  - ⏳ API documentation updates
  - ⏳ Performance benchmarking
- **Status:** Partially completed (some tests exist, comprehensive coverage pending)
- **Dependencies:** Week 4, Task 3, 6, 8

---

## Summary

### ✅ Completed (Weeks 1-2, some Week 3):
- **Infrastructure:** Docker, databases, core services
- **Ingestion Pipeline:** Complete 7-stage pipeline
- **SQL Filtering:** Ontology gating with must-have skills, years, location
- **Background Processing:** Worker, queues, retry logic, DLQ
- **Monitoring:** Metrics, health checks, admin endpoints
- **Skills Extraction:** spaCy + patterns + taxonomy

### 🔄 In Progress / Partially Complete (Week 3):
- **Vector Search:** Infrastructure ready, search method pending
- **Ranking Integration:** SQL gating done, semantic search pending

### ⏳ Not Started (Week 4):
- **Cross-Encoder Re-Ranking:** Model integration and pairwise scoring
- **Explanation Generation:** Citations and reasoning
- **RAG Chatbot:** Context retrieval, LLM integration, streaming
- **Email Drafting:** Personalized email generation
- **Comprehensive Testing:** Full test coverage for new features

---

## Next Steps

1. **Week 3 Priority:** Implement vector search and integrate with existing SQL filtering
2. **Week 4 Priority:** Complete ranking pipeline, then move to chatbot features
3. **Testing:** Add tests as features are implemented (don't wait until end)

---

**Last Updated:** Based on current codebase analysis
**Completion Status:** ~70-75% of MVP complete

