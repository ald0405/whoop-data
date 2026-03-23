from __future__ import annotations

from functools import lru_cache
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid4, uuid5

from langchain_core.messages import HumanMessage
from langgraph.constants import CONFIG_KEY_CHECKPOINTER

from whoopdata.agent import settings
from whoopdata.agent.graph import CONFIG_KEY_STORE, build_graph
from whoopdata.agent.persistence import get_agent_persistence
from whoopdata.agent.public_response import (
    AgentConversationHandle,
    AgentConversationResponse,
    build_agent_conversation_response,
)
from whoopdata.agent.schemas import HealthContextSchema


class SupportsAsyncInvoke(Protocol):
    async def ainvoke(
        self,
        input: dict[str, Any],
        config: dict[str, Any],
        *,
        context: HealthContextSchema | None = None,
    ) -> dict[str, Any]: ...


class ConversationService:
    """Shared user-facing conversation boundary for the public agent surface."""

    def __init__(
        self,
        *,
        graph: SupportsAsyncInvoke | None = None,
    ) -> None:
        self._session_threads: dict[str, str] = {}
        self._graph = graph
        self._graph_name = "health_agent"

    @property
    def graph_name(self) -> str:
        return self._graph_name

    def start_conversation(
        self,
        *,
        session_id: str | None = None,
        thread_id: str | None = None,
        user_id: str | None = None,
    ) -> AgentConversationHandle:
        resolved_session_id, resolved_thread_id = self._resolve_conversation(
            session_id=session_id,
            thread_id=thread_id,
            user_id=user_id,
        )
        return AgentConversationHandle(
            session_id=resolved_session_id,
            thread_id=resolved_thread_id,
        )

    async def send_message(
        self,
        *,
        message: str,
        session_id: str | None = None,
        thread_id: str | None = None,
        image_b64: str | None = None,
        user_id: str | None = None,
        surface: str = "api",
    ) -> AgentConversationResponse:
        graph = await self._ensure_graph()
        resolved_user_id = user_id or settings.DEFAULT_USER_ID
        handle = self.start_conversation(
            session_id=session_id,
            thread_id=thread_id,
            user_id=resolved_user_id,
        )
        human_message = self._build_human_message(message, image_b64=image_b64)
        result = await graph.ainvoke(
            {"messages": [human_message]},
            {"configurable": {"thread_id": handle.thread_id}},
            context=HealthContextSchema(
                user_id=resolved_user_id,
                health_api_base_url=settings.HEALTH_API_BASE_URL,
                surface=surface,
            ),
        )
        return build_agent_conversation_response(
            result,
            thread_id=handle.thread_id,
            session_id=handle.session_id,
            user_message=message,
        )

    @staticmethod
    def _build_human_message(
        text: str,
        *,
        image_b64: str | None = None,
    ) -> HumanMessage:
        """Build a HumanMessage, optionally with an embedded image."""
        if image_b64 is None:
            return HumanMessage(content=text)

        return HumanMessage(
            content=[
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}",
                    },
                },
            ]
        )

    def _resolve_conversation(
        self,
        *,
        session_id: str | None,
        thread_id: str | None,
        user_id: str | None,
    ) -> tuple[str, str]:
        if session_id and session_id in self._session_threads:
            return session_id, self._session_threads[session_id]
        resolved_session_id = session_id or self._new_session_id(user_id=user_id)
        resolved_thread_id = thread_id or self._thread_id_for_session(resolved_session_id)
        self._session_threads[resolved_session_id] = resolved_thread_id
        return resolved_session_id, resolved_thread_id

    @staticmethod
    def _new_session_id(*, user_id: str | None = None) -> str:
        suffix = uuid4().hex[:12]
        if not user_id:
            return f"session_{suffix}"
        return f"session_{user_id.replace(':', '_')}_{suffix}"

    @staticmethod
    def _thread_id_for_session(session_id: str) -> str:
        return f"thread_{uuid5(NAMESPACE_URL, session_id).hex[:12]}"

    async def _ensure_graph(self) -> SupportsAsyncInvoke:
        if self._graph is not None:
            return self._graph

        checkpointer, store = await get_agent_persistence()
        self._graph = build_graph(
            {
                "configurable": {
                    CONFIG_KEY_CHECKPOINTER: checkpointer,
                    CONFIG_KEY_STORE: store,
                }
            }
        )
        return self._graph


@lru_cache(maxsize=1)
def get_conversation_service() -> ConversationService:
    return ConversationService()
