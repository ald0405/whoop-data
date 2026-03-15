from __future__ import annotations

import asyncio
from unittest.mock import patch

from whoopdata.agent.public_response import (
    AgentArtifact,
    AgentConversationResponse,
    AgentConversationTurn,
)

import chat_app


class StubConversationService:
    def __init__(self, response: AgentConversationResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, str | None, str | None]] = []

    async def send_message(
        self,
        *,
        message: str,
        session_id: str | None = None,
        thread_id: str | None = None,
    ) -> AgentConversationResponse:
        self.calls.append((message, session_id, thread_id))
        return self.response


def test_chat_app_defers_conversation_id_creation_to_shared_boundary():
    response = AgentConversationResponse(
        thread_id="thread-123",
        session_id="session-123",
        assistant_message="Hello back.",
        messages=[
            AgentConversationTurn(role="user", content="Hello"),
            AgentConversationTurn(role="assistant", content="Hello back."),
        ],
    )
    service = StubConversationService(response)

    with patch("chat_app.get_conversation_service", return_value=service):
        history, cleared_input, session_id, thread_id = asyncio.run(
            chat_app.chat_with_agent("Hello", [], None, None)
        )

    assert service.calls == [("Hello", None, None)]
    assert history == [("Hello", "Hello back.")]
    assert cleared_input == ""
    assert session_id == "session-123"
    assert thread_id == "thread-123"


def test_chat_app_reuses_existing_conversation_ids_on_follow_up_messages():
    response = AgentConversationResponse(
        thread_id="thread-123",
        session_id="session-123",
        assistant_message="Follow-up response.",
        messages=[
            AgentConversationTurn(role="user", content="How about now?"),
            AgentConversationTurn(role="assistant", content="Follow-up response."),
        ],
    )
    service = StubConversationService(response)

    with patch("chat_app.get_conversation_service", return_value=service):
        history, cleared_input, session_id, thread_id = asyncio.run(
            chat_app.chat_with_agent(
                "How about now?",
                [("Hello", "Hello back.")],
                "session-123",
                "thread-123",
            )
        )

    assert service.calls == [("How about now?", "session-123", "thread-123")]
    assert history[-1] == ("How about now?", "Follow-up response.")
    assert cleared_input == ""
    assert session_id == "session-123"
    assert thread_id == "thread-123"


def test_chat_app_formats_boundary_artifacts_for_gradio():
    response = AgentConversationResponse(
        thread_id="thread-123",
        session_id="session-123",
        assistant_message="Here you go.",
        messages=[
            AgentConversationTurn(role="user", content="Show me something"),
            AgentConversationTurn(role="assistant", content="Here you go."),
        ],
        artifacts=[
            AgentArtifact(
                kind="python_code",
                title="Generated Python Code",
                content="print('hello')",
            ),
            AgentArtifact(
                kind="image",
                title="plot.png",
                mime_type="image/png",
                content="abc123",
            ),
        ],
    )
    service = StubConversationService(response)

    with patch("chat_app.get_conversation_service", return_value=service):
        history, _, _, _ = asyncio.run(
            chat_app.chat_with_agent("Show me something", [], None, None)
        )

    rendered_response = history[0][1]
    assert "**Generated Python Code:**" in rendered_response
    assert "print('hello')" in rendered_response
    assert '<img src="data:image/png;base64,abc123"' in rendered_response
