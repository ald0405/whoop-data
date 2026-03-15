from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from whoopdata.agent.conversation_service import ConversationService, get_conversation_service
from whoopdata.agent.public_response import (
    AgentConversationCreateRequest,
    AgentConversationHandle,
    AgentConversationResponse,
    AgentMessageRequest,
)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/conversations", response_model=AgentConversationHandle)
async def create_conversation(
    payload: AgentConversationCreateRequest | None = Body(default=None),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    request = payload or AgentConversationCreateRequest()
    return conversation_service.start_conversation(
        session_id=request.session_id,
        thread_id=request.thread_id,
    )


@router.post("/messages", response_model=AgentConversationResponse)
async def send_message(
    payload: AgentMessageRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    try:
        return await conversation_service.send_message(
            message=payload.message,
            session_id=payload.session_id,
            thread_id=payload.thread_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error processing agent message: {str(exc)}")
