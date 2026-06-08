from __future__ import annotations

import asyncio

from whoopdata.agent.public_response import (
    AgentConversationResponse,
    AgentConversationTurn,
)
from whoopdata.telegram_push import push_to_telegram


class _StubConversationService:
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
        return AgentConversationResponse(
            session_id=session_id,
            thread_id=thread_id or "thread-1",
            assistant_message=(
                "# Morning check-in\n"
                "| Metric | Value |\n"
                "| --- | --- |\n"
                "| Strain | 11.2 |\n"
                "\n"
                "**Today:** keep it easy and just get 10 minutes outside."
            ),
            messages=[
                AgentConversationTurn(role="user", content=message),
                AgentConversationTurn(role="assistant", content="reply"),
            ],
        )


def test_push_to_telegram_sends_compact_plain_text(monkeypatch):
    sent: dict[str, object] = {}

    class _FakeBot:
        def __init__(self, *, token: str) -> None:
            sent["token"] = token

        async def send_message(
            self,
            *,
            chat_id: int,
            text: str,
            parse_mode=None,
        ):
            sent["chat_id"] = chat_id
            sent["text"] = text
            sent["parse_mode"] = parse_mode
            return type("FakeMessage", (), {"message_id": 42})()

    monkeypatch.setattr("telegram.Bot", _FakeBot)

    result = asyncio.run(
        push_to_telegram(
            chat_id=7,
            prompt="internal prompt",
            conversation_service=_StubConversationService(),
            bot_token="test-token",
        )
    )

    assert sent["token"] == "test-token"
    assert sent["chat_id"] == 7
    assert sent["text"] == (
        "Morning check-in\n" "Strain: 11.2\n" "Today: keep it easy and just get 10 minutes outside."
    )
    assert sent["parse_mode"] is None
    assert result.assistant_message == sent["text"]
    assert result.telegram_message_id == 42
