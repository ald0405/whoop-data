from __future__ import annotations

import asyncio
import base64

from whoopdata.agent.public_response import AgentArtifact, AgentConversationResponse, AgentConversationTurn
from whoopdata.telegram_bot import TelegramConversationGateway


class StubConversationService:
    def __init__(self, responses: list[AgentConversationResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str | None, str | None]] = []

    async def send_message(
        self,
        *,
        message: str,
        session_id: str | None = None,
        thread_id: str | None = None,
    ) -> AgentConversationResponse:
        self.calls.append((message, session_id, thread_id))
        return self._responses.pop(0)


def _response(
    *,
    assistant_message: str,
    session_id: str = "session-1",
    thread_id: str = "thread-1",
    artifacts: list[AgentArtifact] | None = None,
) -> AgentConversationResponse:
    return AgentConversationResponse(
        session_id=session_id,
        thread_id=thread_id,
        assistant_message=assistant_message,
        messages=[
            AgentConversationTurn(role="user", content="hi"),
            AgentConversationTurn(role="assistant", content=assistant_message),
        ],
        artifacts=artifacts or [],
    )


def test_gateway_rejects_group_messages_even_without_allowlists():
    gateway = TelegramConversationGateway(conversation_service=StubConversationService([]))

    assert gateway.is_authorized(user_id=1, chat_id=2, chat_type="group") is False
    assert gateway.is_authorized(user_id=1, chat_id=2, chat_type="private") is True


def test_gateway_reuses_conversation_binding_per_chat():
    service = StubConversationService(
        [
            _response(assistant_message="First", session_id="session-1", thread_id="thread-1"),
            _response(assistant_message="Second", session_id="session-1", thread_id="thread-1"),
        ]
    )
    gateway = TelegramConversationGateway(conversation_service=service)

    first = asyncio.run(
        gateway.handle_text_message(text="hello", user_id=1, chat_id=7, chat_type="private")
    )
    second = asyncio.run(
        gateway.handle_text_message(text="again", user_id=1, chat_id=7, chat_type="private")
    )

    assert first[0].text == "First"
    assert second[0].text == "Second"
    assert service.calls == [
        ("hello", None, None),
        ("again", "session-1", "thread-1"),
    ]


def test_gateway_formats_code_and_image_artifacts_for_telegram():
    png_bytes = b"fake-png"
    service = StubConversationService(
        [
            _response(
                assistant_message="Here you go.",
                artifacts=[
                    AgentArtifact(kind="python_code", content="print('hello')", title="code"),
                    AgentArtifact(
                        kind="image",
                        content=base64.b64encode(png_bytes).decode("utf-8"),
                        title="plot.png",
                        mime_type="image/png",
                    ),
                ],
            )
        ]
    )
    gateway = TelegramConversationGateway(conversation_service=service)

    messages = asyncio.run(
        gateway.handle_text_message(text="show me", user_id=1, chat_id=9, chat_type="private")
    )

    assert messages[0].text == "Here you go."
    assert messages[0].parse_mode == "HTML"
    assert "Generated Python Code" in messages[1].text
    assert "<pre>print('hello')</pre>" in messages[1].text
    assert messages[1].parse_mode == "HTML"
    assert messages[2].photo_bytes == png_bytes
    assert messages[2].caption == "plot.png"


def test_whoami_message_includes_ids_for_first_run_setup():
    gateway = TelegramConversationGateway(conversation_service=StubConversationService([]))

    messages = gateway.build_whoami_messages(user_id=123, chat_id=456, chat_type="private")

    assert len(messages) == 1
    assert "123" in messages[0].text
    assert "456" in messages[0].text
    assert "TELEGRAM_ALLOWED_USER_IDS" in messages[0].text
    assert messages[0].parse_mode is None


def test_gateway_formats_markdownish_assistant_text_for_telegram_html():
    service = StubConversationService(
        [
            _response(
                assistant_message="# Summary\n**Great** work.\nUse `make server` next.\n*Italic note*"
            )
        ]
    )
    gateway = TelegramConversationGateway(conversation_service=service)

    messages = asyncio.run(
        gateway.handle_text_message(text="format this", user_id=1, chat_id=11, chat_type="private")
    )

    assert messages[0].parse_mode == "HTML"
    assert "<b>Summary</b>" in messages[0].text
    assert "<b>Great</b>" in messages[0].text
    assert "<code>make server</code>" in messages[0].text
    assert "<i>Italic note</i>" in messages[0].text
