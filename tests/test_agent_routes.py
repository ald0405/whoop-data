from __future__ import annotations

from fastapi.testclient import TestClient

from whoopdata.agent.public_response import (
    AgentConversationHandle,
    AgentConversationResponse,
    AgentConversationTurn,
)
from whoopdata.api.agent_routes import get_conversation_service
from whoopdata.api.app_factory import create_app


class StubConversationService:
    def __init__(self) -> None:
        self.started_with: tuple[str | None, str | None] | None = None
        self.sent_with: tuple[str, str | None, str | None] | None = None

    def start_conversation(
        self,
        *,
        session_id: str | None = None,
        thread_id: str | None = None,
    ) -> AgentConversationHandle:
        self.started_with = (session_id, thread_id)
        return AgentConversationHandle(
            session_id=session_id or "session-test",
            thread_id=thread_id or "thread-test",
        )

    async def send_message(
        self,
        *,
        message: str,
        session_id: str | None = None,
        thread_id: str | None = None,
    ) -> AgentConversationResponse:
        self.sent_with = (message, session_id, thread_id)
        return AgentConversationResponse(
            thread_id=thread_id or "thread-test",
            session_id=session_id or "session-test",
            assistant_message="Stubbed response",
            messages=[
                AgentConversationTurn(role="user", content=message),
                AgentConversationTurn(role="assistant", content="Stubbed response"),
            ],
        )


class FailingConversationService(StubConversationService):
    async def send_message(
        self,
        *,
        message: str,
        session_id: str | None = None,
        thread_id: str | None = None,
    ) -> AgentConversationResponse:
        raise RuntimeError("boom")


def test_create_conversation_route_uses_shared_service_dependency():
    app = create_app()
    stub = StubConversationService()
    app.dependency_overrides[get_conversation_service] = lambda: stub
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/conversations",
        json={"session_id": "session-1", "thread_id": "thread-1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "surface": "agent",
        "session_id": "session-1",
        "thread_id": "thread-1",
    }
    assert stub.started_with == ("session-1", "thread-1")


def test_send_message_route_returns_conversation_response():
    app = create_app()
    stub = StubConversationService()
    app.dependency_overrides[get_conversation_service] = lambda: stub
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/messages",
        json={
            "message": "Hello",
            "session_id": "session-1",
            "thread_id": "thread-1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "surface": "agent",
        "thread_id": "thread-1",
        "session_id": "session-1",
        "assistant_message": "Stubbed response",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Stubbed response"},
        ],
        "artifacts": [],
    }
    assert stub.sent_with == ("Hello", "session-1", "thread-1")


def test_send_message_route_maps_service_errors_to_http_500():
    app = create_app()
    app.dependency_overrides[get_conversation_service] = lambda: FailingConversationService()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/agent/messages",
        json={"message": "Hello"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Error processing agent message: boom"}
