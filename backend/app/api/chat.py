"""
WebSocket chatbot endpoint for RAG-powered Q&A.
Job-scoped candidate assistant with streaming responses.

TODO: Implement for Days 11-12 (MVP FEATURE - WebSocket + RAG)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import logging
import json

from app.services.chatbot import chatbot

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/{job_id}")
async def chat_websocket(websocket: WebSocket, job_id: int):
    """
    WebSocket endpoint for job-scoped chatbot.

    Protocol:
    1. Client connects to /api/chat/{job_id}
    2. Client sends: {"question": "Who has React experience?", "history": [...]}
    3. Server streams response tokens
    4. Server sends: {"type": "token", "content": "token"}
    5. Server sends: {"type": "done", "citations": [...]}

    Args:
        websocket: WebSocket connection
        job_id: Job ID (scope chatbot to this job's candidates)

    TODO: Implement for Days 11-12
    WebSocket flow:
    1. Accept connection
    2. Receive question from client
    3. Call chatbot.stream_response()
    4. Stream tokens back to client
    5. Send citations when done
    6. Handle disconnections gracefully
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for job {job_id}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            question = message.get("question", "")
            chat_history = message.get("history", [])

            logger.info(f"Received question for job {job_id}: {question}")

            # TODO: Stream response using chatbot.stream_response()
            # For now, send placeholder
            await websocket.send_json({
                "type": "token",
                "content": "Chatbot not yet implemented. "
            })
            await websocket.send_json({
                "type": "token",
                "content": "This will be a RAG-powered assistant for candidate Q&A. "
            })
            await websocket.send_json({
                "type": "token",
                "content": "Coming in Days 11-12!"
            })
            await websocket.send_json({
                "type": "done",
                "citations": []
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        await websocket.close()


@router.post("/{job_id}/email/{candidate_id}")
async def draft_candidate_email(
    job_id: int,
    candidate_id: str,
    email_type: str = "outreach"
):
    """
    Draft personalized email to candidate.

    Args:
        job_id: Job ID
        candidate_id: Candidate ID
        email_type: Email type (outreach, interview, rejection)

    Returns:
        Generated email text

    TODO: Implement for Days 11-12
    """
    logger.info(f"Drafting {email_type} email for candidate {candidate_id}, job {job_id}")

    # TODO: Call chatbot.draft_email()

    return {
        "job_id": job_id,
        "candidate_id": candidate_id,
        "email_type": email_type,
        "status": "not_implemented",
        "message": "Email drafting will be implemented in Days 11-12",
        "email_content": ""
    }
