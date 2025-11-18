# 🚀 DAY-6 QUICK REFERENCE GUIDE

**Complete Implementation: 4 Prompts | 30-40 hours total**

---

## 📋 PROMPT OVERVIEW

| Prompt | Focus | Time | Difficulty | Key Tech |
|--------|-------|------|------------|----------|
| **PROMPT 1** | LLM Resume Parsing | 6-8 hrs | Intermediate | Phi-3-Mini, PyPDF2 |
| **PROMPT 2** | Cross-Encoder + RAG | 8-10 hrs | Advanced | LangGraph, OpenAI |
| **PROMPT 3** | Complete Frontend | 10-12 hrs | Advanced | React, TypeScript |
| **PROMPT 4** | Migrations + Testing | 6-8 hrs | Intermediate | Alembic, Pytest |

---

## 🎯 PROMPT 1: LLM RESUME PARSING (6-8 hours)

### What You'll Build
- Replace regex parsing with Phi-3-Mini LLM (3.8B params)
- Extract: name, email, phone, location, years, summary, skills
- 85%+ accuracy on diverse resume formats
- < 5s processing time per resume

### Key Files Created
```
backend/app/services/llm_parser.py          (NEW - 400+ lines)
backend/app/services/parsers.py             (UPDATE - text extraction)
backend/app/services/ingestion.py           (UPDATE - use LLM in parse_only)
backend/tests/test_llm_parser.py            (NEW - unit tests)
```

### Quick Start Command
```bash
pip install transformers torch PyPDF2 python-docx
python -c "from app.services.llm_parser import get_llm_parser; print('✅ LLM loaded')"
```

### Success Criteria
- ✅ Phi-3-Mini loads without errors
- ✅ Extracts all 7 fields correctly
- ✅ Handles PDF/DOCX/TXT formats
- ✅ < 5s per resume
- ✅ 85%+ field extraction accuracy

### Troubleshooting
- **OOM Error:** Reduce max_length or use CPU
- **Slow parsing:** Check torch.cuda.is_available()
- **JSON parse error:** Increase temperature to 0.1

---

## 🤖 PROMPT 2: CROSS-ENCODER + RAG + LANGGRAPH (8-10 hours)

### What You'll Build
- Cross-encoder re-ranking (ms-marco-MiniLM-L-6-v2)
- LangGraph chatbot with 3 nodes: Guardrails → Retrieve → Generate
- Bias protection (EEOC compliance)
- Email drafting tool
- WebSocket streaming

### Key Files Created
```
backend/app/services/reranker.py            (NEW - cross-encoder)
backend/app/services/chatbot_langgraph.py   (NEW - 400+ lines)
backend/app/api/chat.py                     (NEW - WebSocket handler)
backend/app/services/ranking.py             (UPDATE - add pairwise scores)
backend/tests/test_reranker.py              (NEW)
backend/tests/test_chatbot.py               (NEW)
```

### Quick Start Commands
```bash
pip install sentence-transformers langgraph openai
python -c "from app.services.reranker import get_reranker; print('✅ Cross-encoder loaded')"
```

### LangGraph Flow
```
User Question
    ↓
[Check Guardrails] → Blocks: race, gender, age, religion
    ↓ (if passed)
[Retrieve Context] → Search Qdrant for top 5 chunks
    ↓
[Generate Response] → OpenAI GPT-4 with context
    ↓
Response + Citations
```

### Success Criteria
- ✅ Cross-encoder loads and reranks
- ✅ Guardrails block all protected questions
- ✅ Chatbot retrieves relevant context
- ✅ WebSocket streaming works
- ✅ Email drafting generates 3 types
- ✅ Ranking accuracy +15%

### Troubleshooting
- **Guardrail not triggering:** Check regex patterns
- **WebSocket fails:** Verify router registered
- **OpenAI rate limit:** Add exponential backoff

---

## 🎨 PROMPT 3: COMPLETE FRONTEND (10-12 hours)

### What You'll Build
- **Candidate Portal:** Resume upload → Form pre-fill → Job application
- **Recruiter Dashboard:** Job creation → Ranked candidates → Chatbot
- React 18 + TypeScript + Tailwind CSS
- Real-time WebSocket chatbot
- Form validation with Zod

### Project Structure
```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts          (Axios config)
│   │   ├── candidates.ts      (Upload, create, apply)
│   │   ├── jobs.ts            (Create, rank)
│   │   └── chat.ts            (WebSocket client)
│   ├── components/
│   │   ├── candidate/
│   │   │   ├── ResumeUpload.tsx
│   │   │   ├── CandidateForm.tsx
│   │   │   └── JobList.tsx
│   │   └── recruiter/
│   │       ├── JobForm.tsx
│   │       ├── CandidateRanking.tsx
│   │       └── Chatbot.tsx
│   ├── pages/
│   │   ├── CandidatePortal.tsx
│   │   └── RecruiterDashboard.tsx
│   ├── store/
│   │   ├── candidateStore.ts  (Zustand)
│   │   └── recruiterStore.ts
│   └── App.tsx
```

### Quick Start Commands
```bash
npx create-react-app frontend --template typescript
cd frontend
npm install react-router-dom zustand axios react-hook-form zod tailwindcss react-dropzone
npx tailwindcss init -p
npm start
```

### Key Features
- Drag-and-drop resume upload
- Auto-populated form from LLM parsing
- Real-time candidate rankings with scores
- WebSocket chatbot with streaming
- Responsive design (mobile + desktop)

### Success Criteria
- ✅ Candidate flow: upload → form → apply
- ✅ Recruiter flow: create job → view rankings → chat
- ✅ WebSocket connects and streams
- ✅ Form validation works
- ✅ UI responsive on all devices

### Troubleshooting
- **CORS error:** Add middleware in FastAPI main.py
- **Form not pre-filling:** Check Zustand store
- **WebSocket disconnect:** Verify backend route

---

## 🧪 PROMPT 4: MIGRATIONS + TESTING (6-8 hours)

### What You'll Build
- Alembic database migrations (async PostgreSQL)
- Comprehensive test suite (90%+ coverage)
- Performance benchmarks
- CI/CD pipeline (GitHub Actions)

### Key Files Created
```
backend/alembic/                    (NEW - migration framework)
├── env.py                          (Async config)
├── versions/
│   └── xxxxx_initial_schema.py
backend/tests/
├── conftest.py                     (Test fixtures)
├── test_llm_parser.py             (Parser tests)
├── test_reranker.py               (Reranker tests)
├── test_chatbot.py                (Chatbot tests)
├── test_integration.py            (E2E tests)
└── test_performance.py            (Benchmarks)
docs/MIGRATIONS.md                  (NEW - migration guide)
.github/workflows/test.yml          (NEW - CI/CD)
```

### Quick Start Commands
```bash
pip install alembic pytest pytest-asyncio pytest-cov
alembic init -t async alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
pytest --cov=app --cov-report=html
```

### Test Coverage Targets
| Module | Target | Critical |
|--------|--------|----------|
| llm_parser.py | 95%+ | ✅ |
| reranker.py | 92%+ | ✅ |
| chatbot_langgraph.py | 88%+ | ✅ |
| API endpoints | 90%+ | ✅ |
| **Overall** | **90%+** | ✅ |

### Performance Benchmarks
| Operation | Target | Test Command |
|-----------|--------|--------------|
| LLM parsing | < 5s | `pytest tests/test_performance.py::test_llm_parsing_performance` |
| Cross-encoder | < 500ms | `pytest tests/test_performance.py::test_reranking_performance` |
| Chatbot response | < 3s | Manual WebSocket test |
| Full ranking | < 3s | `curl POST /api/v1/jobs/{id}/rank` |

### Success Criteria
- ✅ Alembic migrations work (up/down)
- ✅ All tests pass
- ✅ 90%+ code coverage
- ✅ Performance benchmarks met
- ✅ CI/CD pipeline configured

### Troubleshooting
- **Migration not detected:** Import all models in env.py
- **Async tests hang:** Check event_loop fixture
- **Low coverage:** Add tests for edge cases

---

## 🎯 IMPLEMENTATION ORDER

### Week 1: Backend AI Features (14-18 hours)
**Day 1-2:** PROMPT 1 - LLM Parsing (6-8 hrs)
- Install Phi-3-Mini
- Create llm_parser.py
- Update ingestion pipeline
- Test with sample resumes

**Day 3-4:** PROMPT 2 - Cross-Encoder + RAG (8-10 hrs)
- Install LangGraph + cross-encoder
- Create reranker.py
- Build LangGraph chatbot
- Implement WebSocket handler
- Test guardrails

### Week 2: Frontend + Testing (16-20 hours)
**Day 5-7:** PROMPT 3 - Complete Frontend (10-12 hrs)
- Set up React + TypeScript
- Build candidate portal
- Build recruiter dashboard
- Integrate WebSocket chatbot
- Test full workflows

**Day 8-9:** PROMPT 4 - Migrations + Testing (6-8 hrs)
- Configure Alembic
- Write comprehensive tests
- Run performance benchmarks
- Set up CI/CD

---

## 📊 FINAL DELIVERABLES

### Features Delivered
✅ **AI-Powered Parsing** - 85%+ accuracy with Phi-3-Mini
✅ **Advanced Ranking** - Dense + Structured + Pairwise + Completeness
✅ **Bias-Protected Chatbot** - EEOC-compliant guardrails
✅ **Real-Time Communication** - WebSocket streaming
✅ **Complete UI** - Candidate portal + Recruiter dashboard
✅ **Production-Ready** - Migrations + 90%+ test coverage

### Tech Stack
**Backend:** FastAPI, PostgreSQL, Qdrant, Phi-3-Mini, LangGraph, OpenAI
**Frontend:** React 18, TypeScript, Tailwind CSS, Zustand
**DevOps:** Docker, Alembic, Pytest, GitHub Actions

### Performance Metrics
- Resume parsing: **< 5s**
- Candidate ranking: **< 3s** for 100 candidates
- Chatbot response: **< 3s** with context
- Cross-encoder: **< 500ms** for 100 candidates

### Quality Metrics
- Test coverage: **90%+**
- Ranking accuracy: **+15%** vs baseline
- LLM extraction: **85%+** field accuracy
- Zero critical bugs

---

## 🚀 DEPLOYMENT CHECKLIST

### Environment Setup
- [ ] PostgreSQL 15+ running
- [ ] Qdrant vector database running
- [ ] Redis for caching (optional)
- [ ] OpenAI API key configured
- [ ] MinIO for file storage

### Backend Deployment
- [ ] Run Alembic migrations: `alembic upgrade head`
- [ ] Start FastAPI: `uvicorn app.main:app`
- [ ] Verify health: `curl http://localhost:8000/api/v1/admin/health-detailed`
- [ ] Run tests: `pytest --cov=app`

### Frontend Deployment
- [ ] Build production: `npm run build`
- [ ] Configure API URL: Set `REACT_APP_API_URL`
- [ ] Deploy to hosting (Vercel/Netlify/S3)
- [ ] Test candidate flow
- [ ] Test recruiter flow

### Monitoring
- [ ] Set up logging (ELK stack)
- [ ] Configure metrics (Prometheus)
- [ ] Add error tracking (Sentry)
- [ ] Set up alerts

---

## 📚 DOCUMENTATION

### For Developers
- **README.md** - Project overview and setup
- **TESTING_GUIDE.md** - Complete API testing guide (Day-5)
- **MIGRATIONS.md** - Database migration guide (PROMPT 4)
- **IMPLEMENTATION_PLAN_DAY6_UPDATED.md** - Detailed 4-prompt plan

### For Each Prompt
- **PROMPT_1_LLM_PARSING.md** - Step-by-step LLM parser implementation
- **PROMPT_2_CROSS_ENCODER_RAG_LANGGRAPH.md** - Reranking + chatbot guide
- **PROMPT_3_FRONTEND.md** - Complete React frontend guide
- **PROMPT_4_MIGRATIONS_TESTING.md** - Testing + migrations guide

---

## 🎉 SUCCESS!

You've built a **production-grade AI recruiting platform** with:
- ✅ State-of-the-art NLP (Phi-3-Mini, cross-encoders)
- ✅ Advanced RAG chatbot with bias protection
- ✅ Complete candidate and recruiter workflows
- ✅ Real-time WebSocket communication
- ✅ Comprehensive test coverage (90%+)
- ✅ Database migrations and CI/CD

**Total Investment:** 30-40 hours
**Lines of Code:** ~5,000+
**Test Coverage:** 90%+
**Production Ready:** ✅

---

## 🔗 QUICK LINKS

- [Day-6 Implementation Plan](IMPLEMENTATION_PLAN_DAY6_UPDATED.md)
- [PROMPT 1: LLM Parsing](PROMPT_1_LLM_PARSING.md)
- [PROMPT 2: Cross-Encoder + RAG](PROMPT_2_CROSS_ENCODER_RAG_LANGGRAPH.md)
- [PROMPT 3: Frontend](PROMPT_3_FRONTEND.md)
- [PROMPT 4: Testing](PROMPT_4_MIGRATIONS_TESTING.md)
- [Testing Guide](../TESTING_GUIDE.md)

---

**Ready to transform recruiting with AI! 🚀**
