from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

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
        user_id=request.user_id,
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
            user_id=payload.user_id,
            surface="api",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error processing agent message: {str(exc)}")


class TelegramPushRequest(BaseModel):
    chat_id: int
    prompt: str = Field(
        default="Give me a brief morning health summary based on my latest data.",
        description="Internal prompt sent to the agent. The user only sees the agent's response.",
    )


class TelegramPushResponse(BaseModel):
    assistant_message: str
    telegram_message_id: int | None = None


@router.post("/telegram/push", response_model=TelegramPushResponse)
async def telegram_push(
    payload: TelegramPushRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """Push a proactive agent message to a Telegram chat.

    The prompt is routed through the shared ConversationService so the
    exchange is checkpointed in the same thread the Telegram bot uses.
    When the user replies in Telegram, the conversation continues seamlessly.
    """
    from whoopdata.telegram_push import push_to_telegram

    try:
        result = await push_to_telegram(
            chat_id=payload.chat_id,
            prompt=payload.prompt,
            conversation_service=conversation_service,
        )
        return TelegramPushResponse(
            assistant_message=result.assistant_message,
            telegram_message_id=result.telegram_message_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Telegram push failed: {str(exc)}")
