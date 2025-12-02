"""
WebSocket chatbot endpoint for RAG-powered Q&A.
Job-scoped candidate assistant with streaming responses and EEOC guardrails.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import logging
import json

from app.services.chatbot_langgraph import chatbot

logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== WEBSOCKET ENDPOINT ====================

@router.websocket("/{job_id}")
async def chat_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time chatbot interaction.

    Client sends:
        {"question": "Who has Python?", "history": [...]}

    Server responds:
        {"type": "response", "content": "...", "citations": [...]}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()
    logger.info(f"🔌 WebSocket connected: job {job_id}")

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)

            question = message.get("question", "")
            history = message.get("history", [])

            if not question:
                await websocket.send_json({
                    "type": "error",
                    "message": "Question is required"
                })
                continue

            # Run chatbot
            result = await chatbot.chat(job_id, question, history)

            if result.get('error'):
                # Send error with the response message (for guardrails, etc.)
                await websocket.send_json({
                    "type": "error",
                    "error_code": result['error'],
                    "message": result.get('response', f"Error: {result['error']}")
                })
            else:
                # Send content as 'token' type (frontend expects this)
                await websocket.send_json({
                    "type": "token",
                    "content": result['response']
                })
                # Send 'done' to signal completion
                await websocket.send_json({
                    "type": "done",
                    "citations": result['citations']
                })

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: job {job_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        await websocket.close()


# ==================== EMAIL DRAFTING ENDPOINT ====================

class EmailRequest(BaseModel):
    email_type: str = "outreach"  # "outreach", "interview", "rejection"

@router.post("/{job_id}/email/{candidate_id}")
async def draft_email(job_id: str, candidate_id: str, request: EmailRequest):
    """
    Draft personalized email for candidate.

    Args:
        job_id: Job UUID
        candidate_id: Candidate UUID
        email_type: Type of email to draft
    """
    try:
        email = await chatbot.draft_email(job_id, candidate_id, request.email_type)
        return {"email": email}
    except Exception as e:
        logger.error(f"❌ Email draft error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
