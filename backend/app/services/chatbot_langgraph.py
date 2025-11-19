"""
LangGraph-based RAG chatbot with EEOC compliance guardrails.
Implements state machine flow for candidate Q&A with bias protection.
"""

from typing import List, Dict, Optional, TypedDict
from langgraph.graph import StateGraph, END
import logging
from app.services.vector_store import vector_store
from app.services.embeddings import embedding_service
from app.services.ranking import ranking_service
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.candidate import Job, Candidate
from sqlalchemy import select
import re

logger = logging.getLogger(__name__)

# ==================== STATE DEFINITION ====================

class ChatState(TypedDict):
    """State for chatbot flow."""
    job_id: str
    question: str
    history: List[Dict]
    context: List[Dict]
    guardrail_passed: bool
    response: str
    citations: List[str]
    error: Optional[str]

# ==================== NODE 1: GUARDRAILS ====================

PROTECTED_ATTRIBUTES = [
    r'\b(race|racial|ethnicity|ethnic|black|white|asian|hispanic|latino)\b',
    r'\b(gender|male|female|man|woman|men|women|transgender|non-?binary)\b',
    r'\b(age|old|young|years? old|born in|birth year)\b',
    r'\b(religion|religious|christian|muslim|jewish|hindu|buddhist|atheist)\b',
    r'\b(disability|disabled|handicap|wheelchair|blind|deaf)\b',
    r'\b(marital|married|single|divorced|spouse|partner)\b',
    r'\b(pregnancy|pregnant|maternity|paternity)\b',
    r'\b(national origin|citizen|citizenship|immigrant|visa)\b'
]

async def check_guardrails(state: ChatState) -> ChatState:
    """
    Check if question violates EEOC guidelines.
    Blocks questions about protected attributes.
    """
    question = state['question'].lower()

    for pattern in PROTECTED_ATTRIBUTES:
        if re.search(pattern, question, re.IGNORECASE):
            logger.warning(f"🚨 Guardrail triggered: {pattern}")
            state['guardrail_passed'] = False
            state['response'] = (
                "I cannot answer questions about protected attributes such as "
                "race, gender, age, religion, disability, or marital status. "
                "Please focus on professional qualifications, skills, and experience."
            )
            state['error'] = "guardrail_violation"
            return state

    state['guardrail_passed'] = True
    logger.info("✅ Guardrail passed")
    return state

# ==================== NODE 2: RETRIEVE CONTEXT ====================

async def retrieve_context(state: ChatState) -> ChatState:
    """
    Retrieve relevant candidate information from vector store.
    """
    if not state['guardrail_passed']:
        return state  # Skip if guardrail failed

    job_id = state['job_id']
    question = state['question']

    try:
        # Get top candidates for this job
        ranked = await ranking_service.rank_candidates(job_id)
        top_candidate_ids = [c.candidate_id for c in ranked[:20]]

        # Encode question
        question_vec = await embedding_service.embed_text(question)

        # Search vector store
        results = vector_store.search(
            collection_name="candidates_v1",
            query_vector=question_vec,
            filter_dict={
                "must": [
                    {"key": "candidate_id", "match": {"any": top_candidate_ids}}
                ]
            },
            limit=5
        )

        # Extract context
        context = []
        for hit in results:
            context.append({
                "text": hit.payload.get("chunk_text", ""),
                "candidate_id": hit.payload.get("candidate_id", ""),
                "score": hit.score
            })

        state['context'] = context
        logger.info(f"📚 Retrieved {len(context)} context chunks")

    except Exception as e:
        logger.error(f"❌ Context retrieval error: {e}")
        state['error'] = str(e)

    return state

# ==================== NODE 3: GENERATE RESPONSE ====================

async def generate_response(state: ChatState) -> ChatState:
    """
    Generate LLM response using retrieved context.
    """
    if not state['guardrail_passed'] or state.get('error'):
        return state

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Format context
        context_text = "\n\n".join([
            f"Candidate {c['candidate_id']}: {c['text']}"
            for c in state['context']
        ])

        # Build messages
        system_msg = {
            "role": "system",
            "content": (
                "You are a recruitment assistant. Answer based on provided context. "
                "Cite candidates by ID. Be concise and professional."
            )
        }

        context_msg = {
            "role": "system",
            "content": f"Context:\n{context_text}"
        }

        messages = [system_msg, context_msg]

        # Add history
        if state.get('history'):
            messages.extend(state['history'])

        # Add current question
        messages.append({
            "role": "user",
            "content": state['question']
        })

        # Generate response
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        state['response'] = response.choices[0].message.content
        state['citations'] = [c['candidate_id'] for c in state['context']]

        logger.info("✅ Response generated")

    except Exception as e:
        logger.error(f"❌ Generation error: {e}")
        state['error'] = str(e)
        state['response'] = "Sorry, I encountered an error generating a response."

    return state

# ==================== TOOL: EMAIL DRAFTING ====================

async def draft_email_tool(job_id: str, candidate_id: str, email_type: str = "outreach") -> str:
    """
    Draft personalized email for candidate.

    Args:
        job_id: Job UUID
        candidate_id: Candidate UUID
        email_type: One of "outreach", "interview", "rejection"
    """
    try:
        async with AsyncSessionLocal() as db:
            job = await db.get(Job, job_id)
            candidate = await db.get(Candidate, candidate_id)

        if not job or not candidate:
            return "Error: Job or candidate not found."

        # Get candidate skills for personalization
        async with AsyncSessionLocal() as db:
            from app.models.candidate import CandidateSkill, Skill
            skills_result = await db.execute(
                select(Skill.name)
                .join(CandidateSkill)
                .where(CandidateSkill.candidate_id == candidate_id)
                .limit(3)
            )
            skills = [row[0] for row in skills_result.all()]

        templates = {
            "outreach": (
                f"Subject: Exciting Opportunity - {job.title}\n\n"
                f"Hi {candidate.full_name},\n\n"
                f"We came across your profile and were impressed by your background in "
                f"{', '.join(skills) if skills else 'your field'}. "
                f"We have an exciting {job.title} opportunity "
                f"that aligns with your experience.\n\n"
                f"Key responsibilities include: {job.description[:200] if job.description else 'see job description'}...\n\n"
                f"Would you be interested in discussing this further?\n\n"
                f"Best regards,\n"
                f"Recruitment Team"
            ),
            "interview": (
                f"Subject: Interview Invitation - {job.title}\n\n"
                f"Hi {candidate.full_name},\n\n"
                f"Thank you for your interest in the {job.title} position. "
                f"We'd like to invite you for an interview to discuss your qualifications further.\n\n"
                f"Please let us know your availability for a 30-minute video call.\n\n"
                f"Best regards,\n"
                f"Recruitment Team"
            ),
            "rejection": (
                f"Subject: Update on Your Application - {job.title}\n\n"
                f"Hi {candidate.full_name},\n\n"
                f"Thank you for your interest in the {job.title} position. "
                f"After careful consideration, we've decided to move forward with other candidates "
                f"whose backgrounds more closely align with our current needs.\n\n"
                f"We appreciate your time and wish you success in your job search.\n\n"
                f"Best regards,\n"
                f"Recruitment Team"
            )
        }

        email = templates.get(email_type, templates["outreach"])
        logger.info(f"📧 Drafted {email_type} email for candidate {candidate_id}")
        return email

    except Exception as e:
        logger.error(f"❌ Email draft error: {e}")
        return f"Error drafting email: {str(e)}"

# ==================== GRAPH CONSTRUCTION ====================

def create_chatbot_graph():
    """Create LangGraph state machine for chatbot."""

    # Create graph
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("check_guardrails", check_guardrails)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("generate_response", generate_response)

    # Define edges
    workflow.set_entry_point("check_guardrails")

    # Conditional edge from guardrails
    def route_after_guardrails(state: ChatState) -> str:
        if state['guardrail_passed']:
            return "retrieve_context"
        else:
            return END

    workflow.add_conditional_edges(
        "check_guardrails",
        route_after_guardrails,
        {
            "retrieve_context": "retrieve_context",
            END: END
        }
    )

    workflow.add_edge("retrieve_context", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()

# ==================== CHATBOT SERVICE ====================

class CandidateChatbot:
    """RAG chatbot with LangGraph flow control."""

    def __init__(self):
        self.graph = create_chatbot_graph()
        logger.info("✅ Chatbot graph initialized")

    async def chat(
        self,
        job_id: str,
        question: str,
        history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Run chatbot flow.

        Returns:
            Dict with 'response', 'citations', 'error'
        """
        initial_state: ChatState = {
            'job_id': job_id,
            'question': question,
            'history': history or [],
            'context': [],
            'guardrail_passed': False,
            'response': '',
            'citations': [],
            'error': None
        }

        # Run graph
        final_state = await self.graph.ainvoke(initial_state)

        return {
            'response': final_state['response'],
            'citations': final_state['citations'],
            'error': final_state.get('error')
        }

    async def draft_email(
        self,
        job_id: str,
        candidate_id: str,
        email_type: str = "outreach"
    ) -> str:
        """Draft email for candidate."""
        return await draft_email_tool(job_id, candidate_id, email_type)

# Singleton
chatbot = CandidateChatbot()
