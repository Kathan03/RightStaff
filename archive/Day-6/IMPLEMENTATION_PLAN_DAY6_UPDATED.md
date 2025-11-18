# 🚀 RightStaff Day-6 Implementation Plan (UPDATED)
## Enhanced Features + Frontend + Production Readiness

**Timeline:** 4-5 Days
**Prerequisites:** Day-5 complete (Prompts 1-3 implemented)
**Goal:** Production-ready application with frontend, AI enhancements, and guardrails

---

## 📊 EXECUTIVE SUMMARY

### What Day-5 Gave Us
- ✅ Application tracking (rank only applicants)
- ✅ Resume-first upload workflow
- ✅ Job embeddings optimization
- ✅ Core ranking pipeline working

### What Day-6 Adds (UPDATED)
- 🎯 **Enhanced Resume Parsing with Lightweight LLM** - Phi-3/Llama for better extraction
- 🎯 **Cross-Encoder Re-ranking** - 15% accuracy improvement
- 🎯 **RAG Chatbot with LangGraph** - Stateful, bias-protected conversation
- 🎯 **Email Drafting (Chatbot-Driven)** - AI-powered candidate outreach
- 🎯 **Complete Frontend** - Candidate portal + Recruiter dashboard
- 🎯 **Bias Guardrails** - Fair, compliant AI interactions
- 🎯 **Database Migrations** - Alembic for schema versioning
- 🎯 **Comprehensive Testing** - 90%+ code coverage

---

## 🎯 NEW 4-PROMPT STRUCTURE

| Prompt | Tasks | Time | Priority | Key Features |
|--------|-------|------|----------|--------------|
| **PROMPT 1** | Enhanced Parsing + Lightweight LLM | 6-8 hrs | 🔴 CRITICAL | Phi-3/Llama for resume parsing |
| **PROMPT 2** | Cross-Encoder + RAG with LangGraph | 8-10 hrs | 🔴 CRITICAL | LangGraph flows, bias guardrails, email drafting |
| **PROMPT 3** | Complete Frontend | 10-12 hrs | 🔴 CRITICAL | Candidate + Recruiter portals |
| **PROMPT 4** | Migrations + Testing | 6-8 hrs | 🟡 HIGH | Alembic, E2E tests |

**Total Time:** 30-38 hours (4-5 days)

---

## 📋 PROMPT 1: ENHANCED RESUME PARSING + LIGHTWEIGHT LLM

**Estimated Time:** 6-8 hours
**Priority:** 🔴 CRITICAL

### Objectives

1. **Replace regex-based parsing with lightweight LLM**
2. **Extract structured fields with high accuracy**
3. **Implement TASK 4 completely**

### Technical Approach

#### Option A: Phi-3-Mini (Recommended)
- **Model:** microsoft/Phi-3-mini-4k-instruct
- **Size:** 3.8B parameters (~8GB RAM)
- **Speed:** 50-100 tokens/sec on CPU
- **Accuracy:** 85-90% for field extraction

#### Option B: Llama-3.2-3B
- **Model:** meta-llama/Llama-3.2-3B-Instruct
- **Size:** 3B parameters (~6GB RAM)
- **Speed:** 60-120 tokens/sec on CPU
- **Accuracy:** 80-85% for field extraction

#### Option C: Mistral-7B-Instruct
- **Model:** mistralai/Mistral-7B-Instruct-v0.3
- **Size:** 7B parameters (~14GB RAM)
- **Speed:** 30-50 tokens/sec on CPU
- **Accuracy:** 90-95% for field extraction

**Recommendation:** Use **Phi-3-Mini** for best balance of speed, accuracy, and resource usage.

### Implementation Steps

**Step 1: Install Dependencies**
```bash
pip install transformers torch accelerate
```

**Step 2: Create LLM-Based Parser Service**

**File:** `backend/app/services/llm_parser.py` (NEW)

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class LLMResumeParser:
    """
    Lightweight LLM for resume parsing.

    Uses Phi-3-Mini for structured field extraction from resume text.
    """

    def __init__(self, model_name: str = "microsoft/Phi-3-mini-4k-instruct"):
        logger.info(f"🤖 Loading LLM parser: {model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )

        logger.info("✅ LLM parser loaded successfully")

    def parse_resume(self, resume_text: str) -> Dict:
        """
        Extract structured fields from resume using LLM.

        Args:
            resume_text: Raw resume text

        Returns:
            {
                "full_name": str,
                "email": str,
                "phone": str,
                "location": {"city": str, "state": str, "country": str},
                "years_experience": float,
                "professional_summary": str,
                "skills": List[str]
            }
        """
        prompt = f"""Extract the following information from this resume and return ONLY valid JSON:

Resume:
{resume_text[:2000]}

Extract:
1. full_name (string)
2. email (string)
3. phone (string)
4. location (object with city, state, country)
5. years_experience (number, calculated from employment dates)
6. professional_summary (string, 2-3 sentences)
7. skills (array of technical skills)

Return format (ONLY JSON, no explanation):
{{
    "full_name": "...",
    "email": "...",
    "phone": "...",
    "location": {{"city": "...", "state": "...", "country": "..."}},
    "years_experience": 5.5,
    "professional_summary": "...",
    "skills": ["Python", "AWS", ...]
}}

JSON:"""

        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=3000)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=500,
                temperature=0.1,  # Low temperature for deterministic extraction
                do_sample=False
            )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract JSON from response
        try:
            # Find JSON in response (between { and })
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]

            parsed_data = json.loads(json_str)
            logger.info(f"✅ Parsed resume: {parsed_data.get('full_name')}")

            return parsed_data

        except Exception as e:
            logger.error(f"❌ Failed to parse LLM response: {e}")
            logger.error(f"Response: {response}")

            # Fallback to empty structure
            return {
                "full_name": None,
                "email": None,
                "phone": None,
                "location": {"city": None, "state": None, "country": None},
                "years_experience": None,
                "professional_summary": None,
                "skills": []
            }

# Singleton instance
llm_parser = LLMResumeParser()
```

**Step 3: Update Ingestion Pipeline**

**File:** `backend/app/services/ingestion.py`

**FIND (parse-only mode):**
```python
if mode == "parse_only":
    # Existing regex-based parsing
    from app.services.parsers import parse_resume
    parsed_data = parse_resume(resume_bytes, file_type=".pdf")
```

**REPLACE WITH:**
```python
if mode == "parse_only":
    # ══════════════════════════════════════════════════════════════
    # STAGE 1-3: LLM-Based Resume Parsing
    # ══════════════════════════════════════════════════════════════

    # Download resume from MinIO
    resume_bytes = await s3_client.download_file(s3_url)

    # Extract text (PDF/DOCX → text)
    from app.services.parsers import extract_text
    resume_text = extract_text(resume_bytes, file_type=".pdf")

    # Parse using LLM
    from app.services.llm_parser import llm_parser
    parsed_data = llm_parser.parse_resume(resume_text)

    # Add raw text to parsed data
    parsed_data["text"] = resume_text

    # Cache in Redis with 1-hour TTL
    await redis_client.set(
        f"parsed_candidate:{candidate_id}",
        json.dumps(parsed_data, default=str),
        ex=3600
    )

    logger.info(f"✅ LLM parsing complete for {candidate_id}")
    logger.info(f"   Name: {parsed_data.get('full_name')}")
    logger.info(f"   Years: {parsed_data.get('years_experience')}")
    logger.info(f"   Skills: {len(parsed_data.get('skills', []))} found")

    return  # STOP HERE - no embeddings yet
```

**Step 4: Create Text Extraction Helper**

**File:** `backend/app/services/parsers.py`

**Add this function:**
```python
def extract_text(file_bytes: bytes, file_type: str) -> str:
    """
    Extract text from resume file (PDF, DOCX, or TXT).

    Args:
        file_bytes: Raw file bytes
        file_type: File extension (.pdf, .docx, .txt)

    Returns:
        Extracted text
    """
    if file_type.lower() == '.pdf':
        # Use PyPDF2 or pdfplumber
        import io
        import PyPDF2

        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text

    elif file_type.lower() in ['.docx', '.doc']:
        # Use python-docx
        import io
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

    else:  # .txt
        return file_bytes.decode('utf-8', errors='ignore')
```

### Files Modified
1. `backend/app/services/llm_parser.py` (NEW)
2. `backend/app/services/ingestion.py` (update parse-only mode)
3. `backend/app/services/parsers.py` (add text extraction)
4. `requirements.txt` (add transformers, torch, PyPDF2, python-docx)

### Validation

```bash
# Test LLM parser
python -c "
from app.services.llm_parser import llm_parser

text = '''
John Doe
Senior Software Engineer
john.doe@example.com | (555) 123-4567
San Francisco, CA

SUMMARY
10+ years of experience in Python development and cloud architecture.

EXPERIENCE
Google | Senior Engineer | Jan 2018 - Present
- Led microservices development

SKILLS
Python, AWS, Docker, Kubernetes
'''

result = llm_parser.parse_resume(text)
print(result)
"

# Expected output:
# {
#   "full_name": "John Doe",
#   "email": "john.doe@example.com",
#   "phone": "(555) 123-4567",
#   "years_experience": 7.0,
#   "skills": ["Python", "AWS", "Docker", "Kubernetes"],
#   ...
# }
```

### Success Criteria
- [ ] LLM parser loads in < 30 seconds
- [ ] Extraction accuracy > 85% (name, email, phone)
- [ ] Years calculation accuracy ± 1 year
- [ ] Skills extraction finds 80%+ of listed skills
- [ ] Parsing completes in < 10 seconds per resume

---

## 📋 PROMPT 2: CROSS-ENCODER + RAG WITH LANGGRAPH

**Estimated Time:** 8-10 hours
**Priority:** 🔴 CRITICAL

### Objectives

1. **Implement cross-encoder re-ranking (TASK 5)**
2. **Build RAG chatbot with LangGraph (TASK 6-7)**
3. **Add bias/fairness guardrails**
4. **Implement email drafting via chatbot (TASK 9)**
5. **WebSocket streaming (TASK 8)**

### Why LangGraph?

**Traditional Approach (Current):**
```
User Question → Retrieve Context → Call LLM → Stream Response
```
❌ No state management
❌ No conversation memory
❌ No tool integration
❌ Hard to add guardrails

**LangGraph Approach (New):**
```
User Question → StateGraph
                ├── Check Guardrails (bias detection)
                ├── Retrieve Context (Qdrant)
                ├── Call LLM (streaming)
                ├── Generate Citations
                └── Draft Email (if requested)
```
✅ Stateful conversation
✅ Built-in guardrails
✅ Tool calling (email drafting)
✅ Easy to extend

### Technical Approach

**Step 1: Install Dependencies**
```bash
pip install langgraph langchain langchain-openai sentence-transformers
```

**Step 2: Create LangGraph Chatbot**

**File:** `backend/app/services/chatbot_langgraph.py` (NEW)

```python
from typing import TypedDict, Annotated, List, Dict, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# State Definition
# ═══════════════════════════════════════════════════════════════

class ChatbotState(TypedDict):
    """State for RAG chatbot with guardrails."""
    job_id: str
    question: str
    chat_history: List[Dict]
    context_chunks: Optional[List[Dict]]
    response: Optional[str]
    citations: Optional[List[str]]
    email_draft: Optional[str]
    guardrail_passed: bool
    guardrail_reason: Optional[str]


# ═══════════════════════════════════════════════════════════════
# Node Functions
# ═══════════════════════════════════════════════════════════════

async def check_guardrails(state: ChatbotState) -> ChatbotState:
    """
    Check if question passes bias/fairness guardrails.

    Blocked patterns:
    - Asking about protected attributes (race, gender, age)
    - Discriminatory language
    - Requests to rank by non-job-related criteria
    """
    question = state["question"].lower()

    # Blocked keywords
    blocked_keywords = [
        "gender", "race", "ethnicity", "age", "religion",
        "male", "female", "man", "woman",
        "black", "white", "asian", "hispanic",
        "old", "young", "years old",
        "married", "single", "children", "pregnant",
        "disability", "disabled"
    ]

    # Discriminatory patterns
    discriminatory_patterns = [
        "prefer candidates who are",
        "only consider",
        "exclude candidates",
        "avoid candidates with"
    ]

    # Check blocked keywords
    for keyword in blocked_keywords:
        if keyword in question:
            state["guardrail_passed"] = False
            state["guardrail_reason"] = f"Question contains protected attribute: '{keyword}'"
            logger.warning(f"🚫 Guardrail blocked: {keyword}")
            return state

    # Check discriminatory patterns
    for pattern in discriminatory_patterns:
        if pattern in question:
            state["guardrail_passed"] = False
            state["guardrail_reason"] = f"Question contains discriminatory language: '{pattern}'"
            logger.warning(f"🚫 Guardrail blocked: {pattern}")
            return state

    # Passed all checks
    state["guardrail_passed"] = True
    logger.info("✅ Guardrail passed")
    return state


async def retrieve_context(state: ChatbotState) -> ChatbotState:
    """Retrieve relevant candidate chunks from Qdrant."""
    from app.services.embeddings import embedding_service
    from app.services.vector_store import vector_store
    from app.services.ranking import ranking_service

    job_id = state["job_id"]
    question = state["question"]

    # Get top candidates for job
    ranked = await ranking_service.rank_candidates(job_id)
    top_candidate_ids = [c.candidate_id for c in ranked[:20]]

    # Encode question
    question_vector = await embedding_service.embed_text(question)

    # Search Qdrant
    results = vector_store.search(
        collection_name="candidates_v1",
        query_vector=question_vector,
        filter={"must": [{"key": "candidate_id", "match": {"any": top_candidate_ids}}]},
        limit=5
    )

    # Format context
    context_chunks = [
        {
            "text": hit.payload.get("text", ""),
            "candidate_id": hit.payload.get("candidate_id"),
            "score": hit.score
        }
        for hit in results
    ]

    state["context_chunks"] = context_chunks
    logger.info(f"📚 Retrieved {len(context_chunks)} context chunks")

    return state


async def generate_response(state: ChatbotState) -> ChatbotState:
    """Generate streaming response using LLM."""
    from app.config import settings

    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0.7,
        api_key=settings.openai_api_key,
        streaming=True
    )

    # Format prompt
    context_text = "\n\n".join([
        f"Candidate {chunk['candidate_id']}: {chunk['text']}"
        for chunk in state["context_chunks"]
    ])

    messages = [
        SystemMessage(content="""You are a fair and unbiased recruitment assistant.

CRITICAL RULES:
1. Only discuss job-related qualifications (skills, experience)
2. NEVER mention or consider: race, gender, age, religion, disability
3. Base recommendations ONLY on professional qualifications
4. If asked about protected attributes, refuse politely
5. Always cite candidate IDs when providing information

Context:
{context}""".format(context=context_text)),
        HumanMessage(content=state["question"])
    ]

    # Generate response
    response = ""
    async for chunk in llm.astream(messages):
        response += chunk.content

    state["response"] = response

    # Generate citations (extract candidate IDs mentioned)
    import re
    candidate_ids = re.findall(r'Candidate ([a-f0-9-]+)', response)
    state["citations"] = list(set(candidate_ids))

    logger.info(f"💬 Generated response ({len(response)} chars, {len(state['citations'])} citations)")

    return state


async def draft_email_tool(state: ChatbotState) -> ChatbotState:
    """
    Draft email if question requests it.

    Triggers:
    - "draft an email"
    - "write an email"
    - "send email to"
    """
    question = state["question"].lower()

    email_triggers = ["draft email", "write email", "send email", "email to"]

    if any(trigger in question for trigger in email_triggers):
        from app.database import AsyncSessionLocal
        from app.models.candidate import Job, Candidate

        # Extract candidate_id from context or question
        # For now, use first candidate from context
        if state["context_chunks"]:
            candidate_id = state["context_chunks"][0]["candidate_id"]

            async with AsyncSessionLocal() as db:
                job = await db.get(Job, state["job_id"])
                candidate = await db.get(Candidate, candidate_id)

            # Generate email using LLM
            from langchain_openai import ChatOpenAI
            from app.config import settings

            llm = ChatOpenAI(model="gpt-4", temperature=0.7, api_key=settings.openai_api_key)

            email_prompt = f"""Draft a professional recruitment email to {candidate.full_name} for the {job.title} position.

Candidate background: {state["context_chunks"][0]["text"][:500]}

Email type: Outreach (initial contact)

Requirements:
- Professional tone
- Personalized based on candidate's background
- Mention specific skills that match the role
- Include call-to-action (schedule call)
- Keep it concise (< 200 words)

Draft:"""

            email_draft = llm.predict(email_prompt)
            state["email_draft"] = email_draft

            logger.info(f"✉️ Drafted email to {candidate.full_name}")

    return state


# ═══════════════════════════════════════════════════════════════
# Build Graph
# ═══════════════════════════════════════════════════════════════

def build_chatbot_graph():
    """Build LangGraph state machine for RAG chatbot."""

    workflow = StateGraph(ChatbotState)

    # Add nodes
    workflow.add_node("check_guardrails", check_guardrails)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("draft_email", draft_email_tool)

    # Define edges
    workflow.set_entry_point("check_guardrails")

    # Conditional: Pass guardrails?
    def should_continue(state: ChatbotState) -> str:
        if state["guardrail_passed"]:
            return "retrieve_context"
        else:
            return END

    workflow.add_conditional_edges(
        "check_guardrails",
        should_continue,
        {
            "retrieve_context": "retrieve_context",
            END: END
        }
    )

    workflow.add_edge("retrieve_context", "generate_response")
    workflow.add_edge("generate_response", "draft_email")
    workflow.add_edge("draft_email", END)

    return workflow.compile()


# Global chatbot instance
chatbot_graph = build_chatbot_graph()


# ═══════════════════════════════════════════════════════════════
# Public Interface
# ═══════════════════════════════════════════════════════════════

async def chat(job_id: str, question: str, chat_history: List[Dict] = None) -> Dict:
    """
    Main chatbot interface.

    Args:
        job_id: Job UUID
        question: User question
        chat_history: Previous messages

    Returns:
        {
            "response": str,
            "citations": List[str],
            "email_draft": Optional[str],
            "guardrail_passed": bool,
            "guardrail_reason": Optional[str]
        }
    """
    # Initialize state
    initial_state = {
        "job_id": job_id,
        "question": question,
        "chat_history": chat_history or [],
        "context_chunks": None,
        "response": None,
        "citations": None,
        "email_draft": None,
        "guardrail_passed": True,
        "guardrail_reason": None
    }

    # Run graph
    final_state = await chatbot_graph.ainvoke(initial_state)

    # Return result
    if not final_state["guardrail_passed"]:
        return {
            "response": f"I cannot answer that question. Reason: {final_state['guardrail_reason']}\n\nPlease ask about candidates' professional qualifications, skills, or experience.",
            "citations": [],
            "email_draft": None,
            "guardrail_passed": False,
            "guardrail_reason": final_state["guardrail_reason"]
        }

    return {
        "response": final_state["response"],
        "citations": final_state["citations"],
        "email_draft": final_state["email_draft"],
        "guardrail_passed": True,
        "guardrail_reason": None
    }
```

**Step 3: Implement Cross-Encoder**

**File:** `backend/app/services/reranker.py` (NEW)

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
        """Re-rank candidates using pairwise scoring."""
        pairs = [(job_description, c.get('professional_summary', '')) for c in candidates]
        scores = self.model.predict(pairs)

        for candidate, score in zip(candidates, scores):
            candidate['pairwise_score'] = float(score)

        ranked = sorted(candidates, key=lambda x: x['pairwise_score'], reverse=True)
        return ranked[:top_k]

reranker_service = RerankerService()
```

**Step 4: Update Ranking Pipeline**

**File:** `backend/app/services/ranking.py`

**Add after dense retrieval (Step 3):**
```python
# Step 3.5: Cross-encoder re-ranking
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

    logger.info(f"🔄 Re-ranked {len(reranked)} candidates")
```

**Update score weights:**
```python
WEIGHTS = {
    'dense': 0.30,
    'structured': 0.30,
    'pairwise': 0.25,  # NEW!
    'completeness': 0.15
}
```

**Step 5: Create WebSocket Handler**

**File:** `backend/app/api/chat.py` (UPDATE)

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json
from app.services.chatbot_langgraph import chat

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/{job_id}")
async def chat_websocket(websocket: WebSocket, job_id: str):
    """WebSocket chatbot with LangGraph."""
    await websocket.accept()
    logger.info(f"🔌 Connected: job {job_id}")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            question = message.get("question", "")
            history = message.get("history", [])

            # Run chatbot graph
            result = await chat(job_id, question, history)

            # Send response
            await websocket.send_json({
                "type": "message",
                "response": result["response"],
                "citations": result["citations"],
                "email_draft": result["email_draft"],
                "guardrail_passed": result["guardrail_passed"]
            })

    except WebSocketDisconnect:
        logger.info(f"🔌 Disconnected: job {job_id}")
```

### Files Modified
1. `backend/app/services/chatbot_langgraph.py` (NEW)
2. `backend/app/services/reranker.py` (NEW)
3. `backend/app/services/ranking.py` (update)
4. `backend/app/api/chat.py` (update)
5. `requirements.txt` (add langgraph, langchain)

### Success Criteria
- [ ] Cross-encoder re-ranks top 100 candidates in < 500ms
- [ ] Guardrails block protected attribute questions
- [ ] RAG retrieves relevant context chunks
- [ ] Email drafting works via chatbot
- [ ] WebSocket streams responses

---

## 📋 PROMPT 3: COMPLETE FRONTEND IMPLEMENTATION

**Estimated Time:** 10-12 hours
**Priority:** 🔴 CRITICAL

### Objectives

1. **Build candidate portal** (upload resume, fill form, apply)
2. **Build recruiter dashboard** (create jobs, view rankings, chat)
3. **Integrate with backend APIs**

### Technology Stack

- **Framework:** React 18 with TypeScript
- **UI Library:** Tailwind CSS + shadcn/ui
- **State Management:** Zustand
- **API Client:** Axios
- **WebSocket:** native WebSocket API
- **Forms:** React Hook Form + Zod validation

### Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── candidate/
│   │   │   ├── ResumeUpload.tsx
│   │   │   ├── CandidateForm.tsx
│   │   │   └── JobList.tsx
│   │   ├── recruiter/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── JobCreate.tsx
│   │   │   ├── RankedCandidates.tsx
│   │   │   ├── Chatbot.tsx
│   │   │   └── EmailDraft.tsx
│   │   └── shared/
│   │       ├── Header.tsx
│   │       └── LoadingSpinner.tsx
│   ├── pages/
│   │   ├── CandidatePortal.tsx
│   │   └── RecruiterDashboard.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   └── useApi.ts
│   ├── types/
│   │   └── index.ts
│   └── App.tsx
├── package.json
└── tsconfig.json
```

### Implementation

**Step 1: Initialize React Project**

```bash
# Create React app with TypeScript
npx create-react-app frontend --template typescript

cd frontend

# Install dependencies
npm install axios zustand react-hook-form zod @hookform/resolvers
npm install -D tailwindcss postcss autoprefixer
npm install @radix-ui/react-dialog @radix-ui/react-select

# Initialize Tailwind
npx tailwindcss init -p
```

**Step 2: Candidate Portal Components**

**File:** `frontend/src/components/candidate/ResumeUpload.tsx`

```typescript
import React, { useState } from 'react';
import axios from 'axios';

interface ParsedData {
  full_name: string;
  email: string;
  phone: string;
  years_experience: number;
  location: {
    city: string;
    state: string;
    country: string;
  };
  professional_summary: string;
  skills: string[];
}

export const ResumeUpload: React.FC<{
  onParseComplete: (tempId: string, data: ParsedData) => void;
}> = ({ onParseComplete }) => {
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        'http://localhost:8000/api/v1/candidates/upload-resume',
        formData
      );

      const { temp_id, parsed_data } = response.data;
      onParseComplete(temp_id, parsed_data);
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Failed to upload resume');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Upload Your Resume</h2>

      <input
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
        className="mb-4 w-full"
      />

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
      >
        {uploading ? 'Uploading...' : 'Upload Resume'}
      </button>

      <p className="text-sm text-gray-600 mt-2">
        Supported formats: PDF, DOCX, TXT
      </p>
    </div>
  );
};
```

**File:** `frontend/src/components/candidate/CandidateForm.tsx`

```typescript
import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import axios from 'axios';

const candidateSchema = z.object({
  temp_id: z.string(),
  full_name: z.string().min(2, 'Name is required'),
  email: z.string().email('Invalid email'),
  phone: z.string().optional(),
  years_experience: z.number().min(0).optional(),
  professional_summary: z.string().optional(),
  location: z.string().optional(),
});

type CandidateFormData = z.infer<typeof candidateSchema>;

export const CandidateForm: React.FC<{
  tempId: string;
  initialData: any;
  onSubmitSuccess: (candidateId: string) => void;
}> = ({ tempId, initialData, onSubmitSuccess }) => {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<CandidateFormData>({
    resolver: zodResolver(candidateSchema),
    defaultValues: {
      temp_id: tempId,
      full_name: initialData.full_name || '',
      email: initialData.email || '',
      phone: initialData.phone || '',
      years_experience: initialData.years_experience || 0,
      professional_summary: initialData.professional_summary || '',
      location: `${initialData.location?.city || ''}, ${initialData.location?.state || ''}`,
    },
  });

  const onSubmit = async (data: CandidateFormData) => {
    try {
      const response = await axios.post(
        'http://localhost:8000/api/v1/candidates/',
        data
      );

      const { candidate_id } = response.data;
      onSubmitSuccess(candidate_id);
    } catch (error) {
      console.error('Submission failed:', error);
      alert('Failed to create candidate profile');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-6">Complete Your Profile</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Full Name *</label>
        <input
          {...register('full_name')}
          className="w-full border rounded px-3 py-2"
        />
        {errors.full_name && <p className="text-red-500 text-sm">{errors.full_name.message}</p>}
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Email *</label>
        <input
          {...register('email')}
          type="email"
          className="w-full border rounded px-3 py-2"
        />
        {errors.email && <p className="text-red-500 text-sm">{errors.email.message}</p>}
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Phone</label>
        <input
          {...register('phone')}
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Years of Experience</label>
        <input
          {...register('years_experience', { valueAsNumber: true })}
          type="number"
          step="0.5"
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Location</label>
        <input
          {...register('location')}
          placeholder="City, State"
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Professional Summary</label>
        <textarea
          {...register('professional_summary')}
          rows={4}
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 disabled:bg-gray-400"
      >
        {isSubmitting ? 'Creating Profile...' : 'Create Profile & Apply'}
      </button>
    </form>
  );
};
```

**Step 3: Recruiter Dashboard Components**

**File:** `frontend/src/components/recruiter/RankedCandidates.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Candidate {
  candidate_id: string;
  rank: number;
  score: number;
  band: string;
  full_name: string;
  years_experience: number;
  skills: string[];
  explanation: string;
}

export const RankedCandidates: React.FC<{ jobId: string }> = ({ jobId }) => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRankings = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `http://localhost:8000/api/v1/jobs/${jobId}/rank_full`,
        { use_cache: false }
      );

      setCandidates(response.data.candidates);
    } catch (error) {
      console.error('Failed to load rankings:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRankings();
  }, [jobId]);

  if (loading) return <div>Loading rankings...</div>;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Ranked Candidates</h2>

      <div className="space-y-4">
        {candidates.map((candidate) => (
          <div key={candidate.candidate_id} className="border rounded p-4 bg-white shadow">
            <div className="flex justify-between items-start mb-2">
              <div>
                <h3 className="font-bold text-lg">#{candidate.rank} - {candidate.full_name}</h3>
                <p className="text-sm text-gray-600">{candidate.years_experience} years experience</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-blue-600">{(candidate.score * 100).toFixed(0)}%</div>
                <div className={`text-sm font-medium ${
                  candidate.band === 'high' ? 'text-green-600' :
                  candidate.band === 'medium' ? 'text-yellow-600' :
                  'text-gray-600'
                }`}>
                  {candidate.band.toUpperCase()}
                </div>
              </div>
            </div>

            <div className="mb-2">
              <strong>Skills:</strong> {candidate.skills.join(', ')}
            </div>

            <div className="text-sm text-gray-700">
              <strong>Why:</strong> {candidate.explanation}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

**File:** `frontend/src/components/recruiter/Chatbot.tsx`

```typescript
import React, { useState, useEffect, useRef } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  email_draft?: string;
}

export const Chatbot: React.FC<{ jobId: string }> = ({ jobId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [currentResponse, setCurrentResponse] = useState('');

  useEffect(() => {
    // Connect WebSocket
    const websocket = new WebSocket(`ws://localhost:8000/api/v1/chat/${jobId}`);

    websocket.onopen = () => {
      console.log('✅ WebSocket connected');
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'message') {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.response,
            citations: data.citations,
            email_draft: data.email_draft,
          },
        ]);
        setCurrentResponse('');
      }
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [jobId]);

  const sendMessage = () => {
    if (!input.trim() || !ws) return;

    const userMessage = { role: 'user' as const, content: input };
    setMessages((prev) => [...prev, userMessage]);

    ws.send(
      JSON.stringify({
        question: input,
        history: messages,
      })
    );

    setInput('');
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 rounded-lg shadow">
      <div className="p-4 border-b bg-white">
        <h3 className="font-bold text-lg">AI Assistant</h3>
        <p className="text-sm text-gray-600">Ask about candidates</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-md rounded-lg p-3 ${
                msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border'
              }`}
            >
              <p>{msg.content}</p>

              {msg.email_draft && (
                <div className="mt-2 p-2 bg-gray-100 rounded text-black">
                  <strong>Email Draft:</strong>
                  <pre className="text-sm whitespace-pre-wrap mt-1">{msg.email_draft}</pre>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask about candidates..."
            className="flex-1 border rounded px-3 py-2"
          />
          <button
            onClick={sendMessage}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Try: "Who has Python experience?" or "Draft an email to the top candidate"
        </p>
      </div>
    </div>
  );
};
```

### Files Created
1. Complete React frontend with TypeScript
2. Candidate portal (3 components)
3. Recruiter dashboard (5 components)
4. WebSocket integration
5. Form validation with Zod

### Success Criteria
- [ ] Resume upload works and shows parsed data
- [ ] Form pre-fills from parsed resume
- [ ] Candidate profile creation succeeds
- [ ] Recruiter can view ranked candidates
- [ ] Chatbot streams responses in real-time
- [ ] Email drafting works via chat

---

## 📋 PROMPT 4: MIGRATIONS + COMPREHENSIVE TESTING

**Estimated Time:** 6-8 hours
**Priority:** 🟡 HIGH

### Objectives

1. **Setup Alembic migrations (TASK 10)**
2. **Unit tests for all new features (TASK 11)**
3. **E2E integration tests (TASK 12)**
4. **Performance benchmarks**

### Implementation

**Step 1: Alembic Setup**

```bash
pip install alembic
alembic init -t async alembic
```

**Configure `alembic/env.py`:**
```python
from app.config import settings
from app.database import Base
from app.models.candidate import *

config.set_main_option("sqlalchemy.url", settings.async_database_url)
target_metadata = Base.metadata
```

**Generate migration:**
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

**Step 2: Test Files**

Create comprehensive tests:
1. `test_llm_parser.py` - LLM parsing accuracy
2. `test_reranker.py` - Cross-encoder re-ranking
3. `test_chatbot_langgraph.py` - Guardrails, RAG, email drafting
4. `test_frontend_e2e.py` - Selenium tests for UI
5. `test_performance.py` - Latency benchmarks

**Step 3: Run All Tests**

```bash
pytest backend/tests/ -v --cov=backend/app --cov-report=html
```

### Success Criteria
- [ ] Migrations work bidirectionally
- [ ] 90%+ test coverage
- [ ] All tests pass
- [ ] Performance benchmarks met

---

## ✅ FINAL VALIDATION CHECKLIST

### Functional Requirements
- [ ] LLM-based parsing extracts fields with 85%+ accuracy
- [ ] Cross-encoder improves ranking quality
- [ ] RAG chatbot answers questions accurately
- [ ] Guardrails block biased questions
- [ ] Email drafting generates personalized content
- [ ] Frontend allows resume upload and job application
- [ ] Recruiter can view rankings and chat

### Performance Requirements
- [ ] LLM parsing: < 10s per resume
- [ ] Cross-encoder: < 500ms for 100 candidates
- [ ] Chatbot response: < 2s
- [ ] Frontend loads: < 3s

### Code Quality
- [ ] All functions typed
- [ ] All functions documented
- [ ] No critical bugs
- [ ] 90%+ test coverage

---

**Document Version:** 2.0 (Updated)
**Created:** 2025-11-17
**Status:** Ready for Implementation

**Let's build the complete production-ready MVP! 🚀**
