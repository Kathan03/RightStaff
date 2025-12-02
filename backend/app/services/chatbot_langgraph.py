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
from app.models.candidate import Job, Candidate, Application
from sqlalchemy import select, func, text
import re
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# ==================== STATE DEFINITION ====================

class ChatState(TypedDict):
    """State for chatbot flow."""
    job_id: str
    question: str
    history: List[Dict]
    job_context: Optional[Dict]  # Complete job + applicants context
    context: List[Dict]  # Semantic search results
    guardrail_passed: bool
    query_type: str  # "semantic" or "database"
    sql_result: Optional[str]
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

# ==================== NODE 1.5: CLASSIFY QUERY TYPE ====================

async def classify_query(state: ChatState) -> ChatState:
    """
    Classify if the question requires database queries or semantic search.

    Database queries: "How many...", "List all...", "Count...", "Show jobs..."
    Semantic queries: "Find candidates with...", "Who has Python skills..."
    """
    if not state['guardrail_passed']:
        return state

    question = state['question'].lower()

    # Database query indicators
    db_indicators = [
        r'\bhow many\b',
        r'\bcount\b',
        r'\btotal\b',
        r'\blist all\b',
        r'\bshow (all|me)\b',
        r'\bremote jobs?\b',
        r'\bjobs? (that|with)\b',
        r'\bapplicants?\b',
        r'\bapplications?\b',
        r'\bvisa sponsorship\b'
    ]

    for pattern in db_indicators:
        if re.search(pattern, question, re.IGNORECASE):
            state['query_type'] = 'database'
            logger.info("🗄️ Query classified as DATABASE query")
            return state

    # Default to semantic search
    state['query_type'] = 'semantic'
    logger.info("🔍 Query classified as SEMANTIC search")
    return state

# ==================== NODE 2: SQL EXECUTION ====================

async def execute_sql_query(state: ChatState) -> ChatState:
    """
    Answer database queries using job_context (no SQL generation).
    This ensures consistency with semantic search results.
    """
    if state['query_type'] != 'database':
        return state

    try:
        job_context = state.get('job_context', {})
        job = job_context.get('job', {})
        applicants = job_context.get('applicants', [])
        question = state['question'].lower()

        # Answer common database queries directly from context
        if 'how many' in question or 'count' in question:
            if 'applicant' in question or 'applied' in question or 'candidate' in question:
                sql_result = f"There are {len(applicants)} applicants for {job.get('title', 'this job')}."

                # List candidate names
                names = [app['full_name'] for app in applicants]
                if len(names) <= 10:
                    sql_result += f"\n\nCandidates: {', '.join(names)}"

            elif 'remote' in question:
                remote_jobs_count = 1 if job.get('is_remote') else 0
                sql_result = f"This job is {'remote' if job.get('is_remote') else 'not remote'}. (Query is job-scoped)"

            elif 'visa' in question:
                sql_result = f"Visa sponsorship: {'Available' if job.get('visa_sponsorship') else 'Not available'} for {job.get('title', 'this job')}"

            else:
                sql_result = f"I have information about {len(applicants)} applicants for this job."

        elif 'list' in question or 'show' in question or 'who' in question:
            if 'applicant' in question or 'candidate' in question or 'applied' in question:
                names = [app['full_name'] for app in applicants]
                if names:
                    sql_result = f"Applicants for {job.get('title', 'this job')}:\n" + "\n".join([f"- {name}" for name in names])
                else:
                    sql_result = "No applicants yet."

            elif 'skill' in question:
                # Extract skill from question
                skills_mentioned = []
                for app in applicants:
                    for skill in app.get('skills', []):
                        skill_name = skill['name']
                        if skill_name.lower() in question:
                            skills_mentioned.append(f"{app['full_name']} - {skill_name} ({skill.get('level', 'N/A')})")

                if skills_mentioned:
                    sql_result = "Candidates with mentioned skills:\n" + "\n".join(skills_mentioned)
                else:
                    sql_result = "No matches found. Try semantic search for skills."

            else:
                sql_result = f"Available data: {len(applicants)} applicants for {job.get('title', 'this job')}"

        else:
            # Fallback
            sql_result = f"I have complete data for {len(applicants)} applicants for {job.get('title', 'this job')}. Ask about specific candidates or use semantic search."

        state['sql_result'] = sql_result
        logger.info(f"✅ Database query answered from context")

    except Exception as e:
        logger.error(f"❌ Database query error: {e}")
        state['error'] = f"Database query failed: {str(e)}"

    return state

# ==================== NODE 3: LOAD COMPREHENSIVE JOB CONTEXT ====================

async def load_job_context(state: ChatState) -> ChatState:
    """
    Load COMPLETE context for a job session:
    1. ALL candidates who applied to the job (from PostgreSQL)
    2. Full candidate metadata (name, skills, experience, resume)
    3. Job details (title, description, requirements)

    This ensures consistency between SQL and semantic queries.
    """
    if not state['guardrail_passed']:
        return state

    job_id = state['job_id']

    try:
        async with AsyncSessionLocal() as db:
            # ============================================
            # STEP 1: Load Job Details
            # ============================================
            job_result = await db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = job_result.scalar_one_or_none()

            if not job:
                state['error'] = f"Job {job_id} not found"
                return state

            job_info = {
                "job_id": str(job.id),
                "title": job.title,
                "description": job.description,
                "required_skills": job.required_skills_json or [],
                "must_have_skills": job.must_have_skills_json or [],
                "location": job.location,
                "is_remote": job.is_remote,
                "visa_sponsorship": job.visa_sponsorship_available
            }

            # ============================================
            # STEP 2: Load ALL Applicants
            # ============================================
            from app.models.candidate import CandidateSkill, Skill

            applicants_result = await db.execute(
                select(Application, Candidate)
                .join(Candidate, Application.candidate_id == Candidate.id)
                .where(Application.job_id == job_id)
            )

            applicants_data = []
            for application, candidate in applicants_result.all():
                # Get candidate skills
                skills_result = await db.execute(
                    select(Skill.name, CandidateSkill.level, CandidateSkill.years)
                    .join(CandidateSkill, Skill.id == CandidateSkill.skill_id)
                    .where(CandidateSkill.candidate_id == candidate.id)
                )
                skills = [
                    {
                        "name": name,
                        "level": level,
                        "years": float(years) if years else None
                    }
                    for name, level, years in skills_result.all()
                ]

                # Build comprehensive candidate record
                applicants_data.append({
                    "candidate_id": str(candidate.id),
                    "full_name": candidate.full_name,
                    "years_experience": float(candidate.years_experience) if candidate.years_experience else 0,
                    "professional_summary": candidate.professional_summary or "",
                    "skills": skills,
                    "application_status": application.status.value,
                    "applied_at": application.applied_at.isoformat()
                })

            # Store in state
            state['job_context'] = {
                "job": job_info,
                "applicants": applicants_data,
                "total_applicants": len(applicants_data)
            }

            logger.info(f"📊 Loaded job context: {job.title} with {len(applicants_data)} applicants")

    except Exception as e:
        logger.error(f"❌ Context loading error: {e}")
        state['error'] = str(e)

    return state


# ==================== NODE 4: RETRIEVE SEMANTIC CONTEXT ====================

async def retrieve_context(state: ChatState) -> ChatState:
    """
    Retrieve semantic matches from vector store for semantic queries.
    Uses candidates from job_context to ensure consistency.
    """
    if not state['guardrail_passed'] or state['query_type'] != 'semantic':
        return state

    question = state['question']

    try:
        # Get candidate IDs from job context
        job_context = state.get('job_context', {})
        applicants = job_context.get('applicants', [])

        if not applicants:
            state['context'] = []
            return state

        candidate_ids = [app['candidate_id'] for app in applicants]

        # Encode question
        question_vec = await embedding_service.embed_text(question)

        # Search vector store for relevant chunks
        results = vector_store.search(
            collection_name="candidates_v1",
            query_vector=question_vec,
            filter_dict={
                "must": [
                    {"key": "candidate_id", "match": {"any": candidate_ids}}
                ]
            },
            top_k=10  # Increased from 5
        )

        # Match with full candidate data from job_context
        context = []
        for hit in results:
            cand_id = hit.payload.get("candidate_id", "")

            # Find full candidate record
            candidate_data = next(
                (app for app in applicants if app['candidate_id'] == cand_id),
                None
            )

            if candidate_data:
                context.append({
                    "text": hit.payload.get("chunk_text", hit.payload.get("text", "")),
                    "candidate_id": cand_id,
                    "full_name": candidate_data['full_name'],
                    "skills": [s['name'] for s in candidate_data['skills']],
                    "years_experience": candidate_data['years_experience'],
                    "professional_summary": candidate_data['professional_summary'],
                    "score": hit.score
                })

        state['context'] = context
        logger.info(f"📚 Retrieved {len(context)} semantic matches")

    except Exception as e:
        logger.error(f"❌ Context retrieval error: {e}")
        state['error'] = str(e)

    return state

# ==================== NODE 4: GENERATE RESPONSE ====================

async def generate_response(state: ChatState) -> ChatState:
    """
    Generate LLM response using retrieved context or SQL results.
    Handles both semantic and database queries.
    """
    if not state['guardrail_passed'] or state.get('error'):
        return state

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Get job context
        job_context = state.get('job_context', {})
        job = job_context.get('job', {})
        applicants = job_context.get('applicants', [])

        # Build comprehensive context
        job_info = f"""Job: {job.get('title', 'Unknown')}
Location: {job.get('location', 'N/A')}
Remote: {'Yes' if job.get('is_remote') else 'No'}
Visa Sponsorship: {'Available' if job.get('visa_sponsorship') else 'Not available'}
Required Skills: {', '.join(job.get('required_skills', [])[:5])}
Total Applicants: {len(applicants)}
"""

        # Build messages based on query type
        if state['query_type'] == 'database':
            # Database query response
            system_msg = {
                "role": "system",
                "content": (
                    "You are a recruitment assistant. Answer the user's question "
                    "using the provided data. Always use candidate NAMES. Be concise and professional."
                )
            }

            context_msg = {
                "role": "system",
                "content": f"{job_info}\n\nQuery Result:\n{state.get('sql_result', 'No results')}"
            }
        else:
            # Semantic search response
            if state['context']:
                # Use semantic matches
                context_text = "\n\n".join([
                    f"**{c['full_name']}**\n"
                    f"Experience: {c.get('years_experience', 0)} years\n"
                    f"Top Skills: {', '.join(c['skills'][:5]) if c['skills'] else 'N/A'}\n"
                    f"Summary: {c.get('professional_summary', 'N/A')[:200]}\n"
                    f"Relevant Info: {c['text'][:300]}"
                    for c in state['context'][:5]
                ])
            else:
                # Use all applicants if no semantic matches
                context_text = "\n\n".join([
                    f"**{app['full_name']}**\n"
                    f"Experience: {app.get('years_experience', 0)} years\n"
                    f"Top Skills: {', '.join([s['name'] for s in app.get('skills', [])[:5]])}\n"
                    f"Summary: {app.get('professional_summary', 'N/A')[:200]}"
                    for app in applicants[:10]
                ])

            system_msg = {
                "role": "system",
                "content": (
                    "You are a recruitment assistant for a specific job. Answer based on provided context. "
                    "ALWAYS use candidate FULL NAMES (not IDs or 'candidate X'). Reference their specific "
                    "skills and experience. Be concise and professional."
                )
            }

            context_msg = {
                "role": "system",
                "content": f"{job_info}\n\nCandidate Information:\n{context_text}"
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
    """
    Create LangGraph state machine for chatbot with Agentic RAG routing.

    Flow:
    1. Check guardrails
    2. Load comprehensive job context (ALL applicants + job details)
    3. Classify query type (database vs semantic)
    4. Route to either SQL query or semantic retrieval
    5. Generate response using full context
    """

    # Create graph
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("check_guardrails", check_guardrails)
    workflow.add_node("load_job_context", load_job_context)
    workflow.add_node("classify_query", classify_query)
    workflow.add_node("execute_sql", execute_sql_query)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("generate_response", generate_response)

    # Define edges
    workflow.set_entry_point("check_guardrails")

    # Route from guardrails to context loader or END
    def route_after_guardrails(state: ChatState) -> str:
        if state['guardrail_passed']:
            return "load_job_context"
        else:
            return END

    workflow.add_conditional_edges(
        "check_guardrails",
        route_after_guardrails,
        {
            "load_job_context": "load_job_context",
            END: END
        }
    )

    # After loading context, classify query
    workflow.add_edge("load_job_context", "classify_query")

    # Route from classifier to SQL or semantic retrieval
    def route_by_query_type(state: ChatState) -> str:
        if state['query_type'] == 'database':
            return "execute_sql"
        else:
            return "retrieve_context"

    workflow.add_conditional_edges(
        "classify_query",
        route_by_query_type,
        {
            "execute_sql": "execute_sql",
            "retrieve_context": "retrieve_context"
        }
    )

    # Both SQL and retrieval go to response generation
    workflow.add_edge("execute_sql", "generate_response")
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
            'job_context': None,  # Will be loaded
            'context': [],
            'guardrail_passed': False,
            'query_type': 'semantic',  # Default, will be updated by classifier
            'sql_result': None,
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
