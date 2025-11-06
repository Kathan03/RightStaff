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
- FastAPI, PostgreSQL 15, Qdrant v1.7.0, Redis 7.2, MinIO
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
