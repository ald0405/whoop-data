from __future__ import annotations

from functools import lru_cache
from typing import Any, Protocol
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from whoopdata.agent.graph import build_graph
from whoopdata.agent.public_response import (
    AgentConversationHandle,
    AgentConversationResponse,
    build_agent_conversation_response,
)


class SupportsAsyncInvoke(Protocol):
    async def ainvoke(self, input: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]: ...


class ConversationService:
    """Shared user-facing conversation boundary for the public agent surface."""

    def __init__(
        self,
        *,
        graph: SupportsAsyncInvoke | None = None,
    ) -> None:
        self._session_threads: dict[str, str] = {}
        self._checkpointer = InMemorySaver()
        self._graph = graph or build_graph(checkpointer=self._checkpointer)
        self._graph_name = "health_agent"

    @property
    def graph_name(self) -> str:
        return self._graph_name

    def start_conversation(
        self,
        *,
        session_id: str | None = None,
        thread_id: str | None = None,
    ) -> AgentConversationHandle:
        resolved_session_id, resolved_thread_id = self._resolve_conversation(
            session_id=session_id,
            thread_id=thread_id,
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
    ) -> AgentConversationResponse:
        handle = self.start_conversation(session_id=session_id, thread_id=thread_id)
        result = await self._graph.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            {"configurable": {"thread_id": handle.thread_id}},
        )
        return build_agent_conversation_response(
            result,
            thread_id=handle.thread_id,
            session_id=handle.session_id,
            user_message=message,
        )

    def _resolve_conversation(
        self,
        *,
        session_id: str | None,
        thread_id: str | None,
    ) -> tuple[str, str]:
        if session_id and session_id in self._session_threads:
            return session_id, self._session_threads[session_id]

        resolved_thread_id = thread_id or self._new_thread_id()
        resolved_session_id = session_id or self._new_session_id()
        self._session_threads[resolved_session_id] = resolved_thread_id
        return resolved_session_id, resolved_thread_id

    @staticmethod
    def _new_session_id() -> str:
        return f"session_{uuid4().hex[:12]}"

    @staticmethod
    def _new_thread_id() -> str:
        return f"thread_{uuid4().hex[:12]}"


@lru_cache(maxsize=1)
def get_conversation_service() -> ConversationService:
    return ConversationService()
