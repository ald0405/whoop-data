from __future__ import annotations

import asyncio
import base64

from whoopdata.agent.public_response import (
    AgentConversationResponse,
    AgentConversationTurn,
)
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
) -> AgentConversationResponse:
    return AgentConversationResponse(
        session_id=session_id,
        thread_id=thread_id,
        assistant_message=assistant_message,
        messages=[
            AgentConversationTurn(role="user", content="hi"),
            AgentConversationTurn(role="assistant", content=assistant_message),
        ],
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
    service = StubConversationService([_response(assistant_message="Looks like a healthy meal!")])
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
    service = StubConversationService([_response(assistant_message="I see an image.")])
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
    gateway = TelegramConversationGateway(conversation_service=service, allowed_user_ids=[999])

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
    gateway = TelegramConversationGateway(conversation_service=service, allowed_user_ids=[999])

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
        "Morning check-in\n" "Strain: 11.2\n" "Action: 10 min walk\n" "Today: keep it easy.…"
    )


def test_gateway_video_message_extracts_frames_and_routes_through_supervisor(monkeypatch):
    """Video handler should extract frames, call biomechanics agent, then feed analysis to supervisor."""
    import whoopdata.telegram_bot as tb

    # Mock the dense extraction to return fake BGR frames + fps
    import numpy as np
    fake_frames = [np.zeros((100, 100, 3), dtype=np.uint8)] * 2
    monkeypatch.setattr(tb, "_extract_video_frames_dense", lambda vb, **kw: (fake_frames, 30.0))
    # Mock the legacy path extraction too
    monkeypatch.setattr(tb, "_extract_video_frames", lambda vb, **kw: [b"frame1", b"frame2"])

    async def _mock_analyze(images_b64, prompt, *, user_id="default_user"):
        return f"Analysis of {len(images_b64)} frames: good form!"

    service = StubConversationService(
        [_response(assistant_message="Great serve technique! Keep that knee bend.")]
    )
    gateway = TelegramConversationGateway(
        conversation_service=service,
        analyze_video_fn=_mock_analyze,
    )

    messages = asyncio.run(
        gateway.handle_video_message(
            video_bytes=b"fake-mp4",
            caption="Check my tennis serve",
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    # Supervisor should receive the biomechanics analysis as text
    assert len(service.calls) == 1
    assert "biomechanics analysis" in service.calls[0]["message"].lower()
    assert "good form" in service.calls[0]["message"]
    # Final response comes from the supervisor
    assert any("knee bend" in (m.text or "") for m in messages)


def test_gateway_video_message_uses_default_prompt_when_no_caption(monkeypatch):
    """Video without caption should use the default biomechanics prompt."""
    import whoopdata.telegram_bot as tb

    import numpy as np
    fake_frames = [np.zeros((100, 100, 3), dtype=np.uint8)]
    monkeypatch.setattr(tb, "_extract_video_frames_dense", lambda vb, **kw: (fake_frames, 30.0))
    monkeypatch.setattr(tb, "_extract_video_frames", lambda vb, **kw: [b"frame1"])

    captured_prompts = []

    async def _mock_analyze(images_b64, prompt, *, user_id="default_user"):
        captured_prompts.append(prompt)
        return "Analysis done."

    service = StubConversationService(
        [_response(assistant_message="Here's what I found.")]
    )
    gateway = TelegramConversationGateway(
        conversation_service=service,
        analyze_video_fn=_mock_analyze,
    )

    asyncio.run(
        gateway.handle_video_message(
            video_bytes=b"fake-mp4",
            caption=None,
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    assert len(captured_prompts) >= 1
    assert "biomechanics" in captured_prompts[0].lower() or "overlays" in captured_prompts[0].lower()


def test_gateway_video_message_rejected_for_unauthorized_user():
    """Video from unauthorized user should be silently rejected."""
    async def _mock_analyze(images_b64, prompt, *, user_id="default_user"):
        raise AssertionError("Should not be called")

    gateway = TelegramConversationGateway(
        conversation_service=StubConversationService([]),
        allowed_user_ids=[999],
        analyze_video_fn=_mock_analyze,
    )

    messages = asyncio.run(
        gateway.handle_video_message(
            video_bytes=b"fake-mp4",
            caption=None,
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    assert messages == []


def test_gateway_video_message_returns_error_on_no_frames(monkeypatch):
    """When frame extraction fails, gateway should return a user-friendly error."""
    import whoopdata.telegram_bot as tb

    # Mock dense extraction to fail, and legacy to return empty
    monkeypatch.setattr(
        tb, "_extract_video_frames_dense",
        lambda vb, **kw: (None, "Could not open the video file."),
    )
    monkeypatch.setattr(tb, "_extract_video_frames", lambda vb, **kw: [])

    gateway = TelegramConversationGateway(
        conversation_service=StubConversationService([]),
    )

    messages = asyncio.run(
        gateway.handle_video_message(
            video_bytes=b"bad-video",
            caption=None,
            user_id=1,
            chat_id=10,
            chat_type="private",
        )
    )

    assert len(messages) == 1
    assert "could not" in messages[0].text.lower() or "couldn't" in messages[0].text.lower()


def test_preprocess_frames_is_passthrough():
    """The preprocessing stub should return frames unchanged."""
    from whoopdata.telegram_bot import _preprocess_frames

    frames = [b"frame-a", b"frame-b", b"frame-c"]
    assert _preprocess_frames(frames) is frames


def test_build_application_registers_video_filter(monkeypatch):
    """build_application should register a VIDEO | VIDEO_NOTE handler."""
    import whoopdata.telegram_bot as tb

    monkeypatch.setattr(tb, "TELEGRAM_BOT_TOKEN", "fake-token")
    app = tb.build_application(gateway=TelegramConversationGateway(
        conversation_service=StubConversationService([]),
    ))

    from telegram.ext import filters

    handler_filters = [h.filters for h in app.handlers[0] if hasattr(h, "filters")]
    video_registered = any(
        filters.VIDEO in (getattr(f, "_filters", set()) | {f})
        or "video" in str(f).lower()
        for f in handler_filters
    )
    assert video_registered, f"No VIDEO filter found among: {handler_filters}"


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
