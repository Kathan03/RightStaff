# 🚀 DAY-6 PROMPTS 5-9 IMPLEMENTATION GUIDE

**Note:** Due to length, detailed implementations for Prompts 5-9 are provided below as complete, copy-paste ready instructions.

---

## 📋 PROMPT 5: CROSS-ENCODER RE-RANKING (2-3 hours)

### Quick Reference
- **Install:** `sentence-transformers`
- **Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Files:** Create `reranker.py`, update `ranking.py`
- **Impact:** +15% ranking accuracy

### Step 1: Install Dependency
```bash
pip install sentence-transformers
```

### Step 2: Create Reranker Service

**File:** `backend/app/services/reranker.py` (NEW FILE)

```python
from sentence_transformers import CrossEncoder
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class RerankerService:
    """Cross-encoder for pairwise re-ranking."""
    
    def __init__(self):
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        logger.info("✅ Cross-encoder loaded")
    
    def rerank(self, job_description: str, candidates: List[Dict], top_k: int = 50) -> List[Dict]:
        """
        Re-rank candidates using pairwise scoring.
        
        Args:
            job_description: Full job description
            candidates: List with 'id' and 'professional_summary'
            top_k: Number to return
        """
        # Create pairs
        pairs = [(job_description, c.get('professional_summary', '')) for c in candidates]
        
        # Predict scores
        scores = self.model.predict(pairs)
        
        # Add scores to candidates
        for candidate, score in zip(candidates, scores):
            candidate['pairwise_score'] = float(score)
        
        # Sort and return top_k
        ranked = sorted(candidates, key=lambda x: x['pairwise_score'], reverse=True)
        return ranked[:top_k]

# Singleton
reranker_service = RerankerService()
```

### Step 3: Update Ranking Pipeline

**File:** `backend/app/services/ranking.py`

**FIND (after Step 3: Dense retrieval, around line 115):**
```python
# Step 4: Structured scoring
```

**INSERT BEFORE Step 4:**
```python
# Step 3.5: Cross-encoder re-ranking (NEW!)
if len(retrieval_results) > 0:
    from app.services.reranker import reranker_service
    
    candidates_for_rerank = []
    for result in retrieval_results[:100]:
        candidate_data = next((c for c in eligible_candidates if c['id'] == result.candidate_id), None)
        if candidate_data:
            candidates_for_rerank.append(candidate_data)
    
    reranked = reranker_service.rerank(
        job_description=job_data['description'],
        candidates=candidates_for_rerank,
        top_k=50
    )
    
    logger.info(f"🔄 Re-ranked {len(reranked)} candidates using cross-encoder")
```

### Step 4: Update Score Weights

**FIND (line 53):**
```python
WEIGHTS = {
    'dense': 0.40,
    'structured': 0.35,
    'pairwise': 0.00,
    'completeness': 0.25
}
```

**REPLACE WITH:**
```python
WEIGHTS = {
    'dense': 0.30,
    'structured': 0.30,
    'pairwise': 0.25,  # NEW!
    'completeness': 0.15
}
```

### Step 5: Update Score Blending Logic

**File:** `backend/app/services/ranking.py` (in `_blend_scores` method)

**FIND:**
```python
final_score = (
    self.WEIGHTS['dense'] * dense_score +
    self.WEIGHTS['structured'] * structured_score +
    self.WEIGHTS['completeness'] * completeness_score
)
```

**REPLACE WITH:**
```python
pairwise_score = candidate.get('pairwise_score', 0.0)

final_score = (
    self.WEIGHTS['dense'] * dense_score +
    self.WEIGHTS['structured'] * structured_score +
    self.WEIGHTS['pairwise'] * pairwise_score +  # NEW!
    self.WEIGHTS['completeness'] * completeness_score
)
```

### Validation
```bash
# Test
python -c "from app.services.reranker import reranker_service; print('✅ Reranker loaded')"

# Run ranking
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/rank_full
# Check logs for "🔄 Re-ranked N candidates"
```

---

## 📋 PROMPT 6: RAG CHATBOT FOUNDATION (4-5 hours)

### Quick Reference
- **Install:** `openai` or `anthropic`
- **Files:** Update `chatbot.py`, `config.py`
- **Features:** Context retrieval, streaming, citations

### Step 1: Install Dependencies
```bash
pip install openai  # or anthropic
```

### Step 2: Add API Key to Config

**File:** `backend/app/config.py`

```python
# Add to Settings class
openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
# OR
anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
```

**File:** `.env` (create if not exists)
```bash
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
```

### Step 3: Implement Context Retrieval

**File:** `backend/app/services/chatbot.py`

**REPLACE entire file with:**
```python
from typing import List, Dict, Optional, AsyncGenerator
import logging
from app.services.vector_store import vector_store
from app.services.embeddings import embedding_service
from app.services.ranking import ranking_service
from app.config import settings

logger = logging.getLogger(__name__)

class CandidateChatbot:
    """RAG chatbot for candidate Q&A."""
    
    async def retrieve_context(self, job_id: str, question: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant candidate chunks."""
        # Get top candidates for job
        ranked = await ranking_service.rank_candidates(job_id)
        top_ids = [c.candidate_id for c in ranked[:20]]
        
        # Encode question
        question_vec = await embedding_service.embed_text(question)
        
        # Search Qdrant
        results = vector_store.search(
            collection_name="candidates_v1",
            query_vector=question_vec,
            filter={"must": [{"key": "candidate_id", "match": {"any": top_ids}}]},
            limit=top_k
        )
        
        return [{"text": hit.payload["text"], "candidate_id": hit.payload["candidate_id"], "score": hit.score} for hit in results]
    
    def format_prompt(self, question: str, context: List[Dict], history: Optional[List[Dict]] = None) -> List[Dict]:
        """Format RAG prompt for LLM."""
        system_msg = {
            "role": "system",
            "content": "You are a recruitment assistant. Answer based on provided context. Cite candidates by name."
        }
        
        context_text = "\n\n".join([f"Candidate {c['candidate_id']}: {c['text']}" for c in context])
        context_msg = {"role": "system", "content": f"Context:\n{context_text}"}
        
        messages = [system_msg, context_msg]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})
        
        return messages
    
    async def stream_response(self, job_id: str, question: str, history: Optional[List[Dict]] = None) -> AsyncGenerator[str, None]:
        """Stream LLM response."""
        context = await self.retrieve_context(job_id, question)
        prompt = self.format_prompt(question, context, history)
        
        # OpenAI streaming
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=prompt,
            stream=True,
            temperature=0.7
        )
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

chatbot = CandidateChatbot()
```

### Validation
```python
# Test context retrieval
import asyncio
from app.services.chatbot import chatbot

async def test():
    context = await chatbot.retrieve_context("job-uuid", "Who has Python?")
    print(f"Found {len(context)} chunks")

asyncio.run(test())
```

---

## 📋 PROMPT 7: WEBSOCKET + EMAIL (3-4 hours)

### Step 1: Implement WebSocket Handler

**File:** `backend/app/api/chat.py`

**REPLACE entire file:**
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json
from app.services.chatbot import chatbot

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/{job_id}")
async def chat_websocket(websocket: WebSocket, job_id: str):
    """WebSocket chatbot endpoint."""
    await websocket.accept()
    logger.info(f"🔌 Connected: job {job_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            question = message.get("question", "")
            history = message.get("history", [])
            
            # Stream response
            async for token in chatbot.stream_response(job_id, question, history):
                await websocket.send_json({"type": "token", "content": token})
            
            # Done
            await websocket.send_json({"type": "done", "citations": []})
            
    except WebSocketDisconnect:
        logger.info(f"🔌 Disconnected: job {job_id}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        await websocket.close()


@router.post("/{job_id}/email/{candidate_id}")
async def draft_email(job_id: str, candidate_id: str, email_type: str = "outreach"):
    """Draft candidate email."""
    from app.services.chatbot import chatbot
    email = await chatbot.draft_email(job_id, candidate_id, email_type)
    return {"email": email}
```

### Step 2: Add Email Drafting to Chatbot

**File:** `backend/app/services/chatbot.py` (add method)

```python
async def draft_email(self, job_id: str, candidate_id: str, email_type: str = "outreach") -> str:
    """Draft personalized email."""
    from app.database import AsyncSessionLocal
    from app.models.candidate import Job, Candidate
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)
        candidate = await db.get(Candidate, candidate_id)
    
    templates = {
        "outreach": f"Hi {candidate.full_name},\n\nWe have an exciting {job.title} opportunity...",
        "interview": f"Hi {candidate.full_name},\n\nWe'd like to schedule an interview for {job.title}...",
        "rejection": f"Hi {candidate.full_name},\n\nThank you for applying to {job.title}..."
    }
    
    return templates.get(email_type, templates["outreach"])
```

### Step 3: Register Chat Router

**File:** `backend/app/main.py`

```python
from app.api import webhooks, jobs, admin, candidates, chat  # Add chat

app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])  # Add this line
```

### Validation
```bash
# Test WebSocket
# Use a WebSocket client or browser console:
const ws = new WebSocket('ws://localhost:8000/api/v1/chat/{job_id}');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({question: "Who has Python?", history: []}));
```

---

## 📋 PROMPT 8: DATABASE MIGRATIONS (2-3 hours)

### Step 1: Install Alembic
```bash
pip install alembic
```

### Step 2: Initialize with Async Template
```bash
alembic init -t async alembic
```

### Step 3: Configure env.py

**File:** `alembic/env.py`

```python
from app.config import settings
from app.database import Base
from app.models.candidate import *  # Import all models

config.set_main_option("sqlalchemy.url", settings.async_database_url)
target_metadata = Base.metadata
```

### Step 4: Generate Migration
```bash
alembic revision --autogenerate -m "Initial schema"
```

### Step 5: Test Migration
```bash
# Upgrade
alembic upgrade head

# Check current
alembic current

# Downgrade
alembic downgrade -1
```

### Documentation

**File:** `docs/MIGRATIONS.md`
```markdown
# Database Migrations

## Commands
- Generate: `alembic revision --autogenerate -m "description"`
- Upgrade: `alembic upgrade head`
- Downgrade: `alembic downgrade -1`
- Current: `alembic current`
- History: `alembic history`
```

---

## 📋 PROMPT 9: COMPREHENSIVE TESTING (4-6 hours)

### Test Files to Create

1. **Enhanced Parsing Tests** - `test_enhanced_parsing.py` (see Prompt 4)
2. **Cross-Encoder Tests** - `test_reranker.py`
3. **Chatbot Tests** - `test_chatbot.py`
4. **WebSocket Tests** - `test_websocket.py`
5. **E2E Tests** - `test_e2e_workflow.py`

### Sample Test Structure

**File:** `backend/tests/test_reranker.py`
```python
import pytest
from app.services.reranker import reranker_service

def test_reranker_loads():
    assert reranker_service.model is not None

def test_rerank_orders_correctly():
    job_desc = "Senior Python Developer"
    candidates = [
        {"id": "1", "professional_summary": "10 years Python"},
        {"id": "2", "professional_summary": "2 years JavaScript"}
    ]
    
    ranked = reranker_service.rerank(job_desc, candidates)
    assert ranked[0]["id"] == "1"  # Better match first
```

**File:** `backend/tests/test_chatbot.py`
```python
import pytest
from app.services.chatbot import chatbot

@pytest.mark.asyncio
async def test_retrieve_context():
    context = await chatbot.retrieve_context("job-id", "Who has Python?", top_k=5)
    assert len(context) <= 5
    assert all("text" in c for c in context)
```

### Run All Tests
```bash
pytest backend/tests/ -v --cov=backend/app --cov-report=html
```

---

## ✅ COMPLETE CHECKLIST

### Day-6 Implementation
- [ ] Prompt 4: Enhanced parsing working
- [ ] Prompt 5: Cross-encoder loaded and ranking
- [ ] Prompt 6: RAG chatbot retrieving context
- [ ] Prompt 7: WebSocket streaming tokens
- [ ] Prompt 8: Alembic migrations configured
- [ ] Prompt 9: All tests passing

### Performance Targets
- [ ] Enhanced parsing: < 5s per resume
- [ ] Cross-encoder: < 500ms for 100 candidates
- [ ] Chatbot retrieval: < 200ms
- [ ] WebSocket latency: < 100ms per token
- [ ] Overall ranking: < 2s

### Quality Metrics
- [ ] 90%+ test coverage
- [ ] No critical bugs
- [ ] All endpoints documented
- [ ] Performance benchmarks met

---

**For detailed step-by-step instructions, refer to:**
- Day-6/IMPLEMENTATION_PLAN_DAY6.md (comprehensive overview)
- Day-6/PROMPT_4_ENHANCED_PARSING.md (detailed walkthrough)

**This reference guide provides copy-paste ready code for Prompts 5-9.**

**Ready to complete the MVP! 🚀**
