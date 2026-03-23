from __future__ import annotations

import asyncio
import base64

from whoopdata.agent.public_response import AgentArtifact, AgentConversationResponse, AgentConversationTurn
from whoopdata.telegram_bot import TelegramConversationGateway, format_text_for_telegram_plain


class StubConversationService:
    def __init__(self, responses: list[AgentConversationResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

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
        self.calls.append(
            {
                "message": message,
                "session_id": session_id,
                "thread_id": thread_id,
                "image_b64": image_b64,
                "user_id": user_id,
                "surface": surface,
            }
        )
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
    assert service.calls[0]["message"] == "hello"
    assert service.calls[0]["session_id"] == "telegram-chat-7"
    assert service.calls[0]["thread_id"] == "telegram-thread-7"
    assert service.calls[0]["user_id"] == "telegram:1"
    assert service.calls[1]["message"] == "again"
    assert service.calls[1]["session_id"] == "session-1"


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


def test_gateway_photo_message_sends_image_b64():
    """Photo handler should base64-encode the image and pass it to the conversation service."""
    service = StubConversationService(
        [_response(assistant_message="Looks like a healthy meal!")]
    )
    gateway = TelegramConversationGateway(conversation_service=service)

    photo_bytes = b"fake-jpeg-bytes"
    messages = asyncio.run(
        gateway.handle_photo_message(
            photo_bytes=photo_bytes,
            caption="What do you think of this meal?",
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    assert len(messages) == 1
    assert "healthy meal" in messages[0].text
    assert service.calls[0]["message"] == "What do you think of this meal?"
    assert service.calls[0]["image_b64"] == base64.b64encode(photo_bytes).decode("utf-8")


def test_gateway_photo_message_uses_default_caption_when_none():
    """Photo without caption should use a default prompt."""
    service = StubConversationService(
        [_response(assistant_message="I see an image.")]
    )
    gateway = TelegramConversationGateway(conversation_service=service)

    messages = asyncio.run(
        gateway.handle_photo_message(
            photo_bytes=b"img",
            caption=None,
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    assert len(messages) == 1
    assert "What's in this image?" in service.calls[0]["message"]


def test_gateway_photo_message_rejected_for_unauthorized_user():
    service = StubConversationService([])
    gateway = TelegramConversationGateway(
        conversation_service=service, allowed_user_ids=[999]
    )

    messages = asyncio.run(
        gateway.handle_photo_message(
            photo_bytes=b"img",
            caption=None,
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    assert messages == []
    assert service.calls == []


def test_gateway_voice_message_returns_error_on_transcription_failure(monkeypatch):
    """When transcription returns None, the gateway should return an error message."""
    import whoopdata.telegram_bot as tb

    async def _mock_transcribe(voice_bytes: bytes):
        return None

    monkeypatch.setattr(tb, "_transcribe_voice", _mock_transcribe)

    service = StubConversationService([])
    gateway = TelegramConversationGateway(conversation_service=service)

    messages = asyncio.run(
        gateway.handle_voice_message(
            voice_bytes=b"fake-ogg",
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    assert len(messages) == 1
    assert "couldn't understand" in messages[0].text
    assert service.calls == []


def test_gateway_voice_message_transcribes_and_delegates(monkeypatch):
    """Successful voice transcription should feed text into the text pipeline and attach voice replies."""
    import whoopdata.telegram_bot as tb

    async def _mock_transcribe(voice_bytes: bytes):
        return "How is my recovery today?"

    async def _mock_tts(text: str):
        return b"fake-opus-audio"

    monkeypatch.setattr(tb, "_transcribe_voice", _mock_transcribe)
    monkeypatch.setattr(tb, "_text_to_speech", _mock_tts)

    service = StubConversationService(
        [_response(assistant_message="Your recovery is 82%. Green zone.")]
    )
    gateway = TelegramConversationGateway(conversation_service=service)

    messages = asyncio.run(
        gateway.handle_voice_message(
            voice_bytes=b"fake-ogg",
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    # Should have voice reply + text fallback
    assert len(messages) == 2
    assert messages[0].voice_bytes == b"fake-opus-audio"
    assert messages[1].text is not None
    assert "82%" in messages[1].text
    assert service.calls[0]["message"] == "How is my recovery today?"


def test_gateway_voice_message_rejected_for_unauthorized_user(monkeypatch):
    service = StubConversationService([])
    gateway = TelegramConversationGateway(
        conversation_service=service, allowed_user_ids=[999]
    )

    messages = asyncio.run(
        gateway.handle_voice_message(
            voice_bytes=b"fake-ogg",
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    assert messages == []


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


def test_plain_formatter_flattens_markdown_tables_for_chat_style_delivery():
    formatted = format_text_for_telegram_plain(
        "# Morning check-in\n"
        "| Metric | Value |\n"
        "| --- | --- |\n"
        "| Strain | 11.2 |\n"
        "| Action | 10 min walk |\n"
        "\n"
        "**Today:** keep it easy.\n"
        "*Energy later?*"
    )

    assert formatted == (
        "Morning check-in\n"
        "Strain: 11.2\n"
        "Action: 10 min walk\n"
        "Today: keep it easy.…"
    )


def test_plain_formatter_limits_length_and_line_count():
    formatted = format_text_for_telegram_plain(
        "\n".join(
            [
                "Line one with plenty of extra words for truncation",
                "Line two with plenty of extra words for truncation",
                "Line three with plenty of extra words for truncation",
                "Line four with plenty of extra words for truncation",
                "Line five with plenty of extra words for truncation",
            ]
        ),
        max_chars=90,
        max_lines=3,
    )

    assert formatted.count("\n") <= 2
    assert len(formatted) <= 90
    assert formatted.endswith("…")
