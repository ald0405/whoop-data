from __future__ import annotations

from langchain_core.messages import HumanMessage

from whoopdata.agent.conversation_service import ConversationService


def test_build_human_message_text_only():
    msg = ConversationService._build_human_message("Hello")
    assert isinstance(msg, HumanMessage)
    assert msg.content == "Hello"


def test_build_human_message_with_image():
    msg = ConversationService._build_human_message("What is this?", image_b64="abc123")
    assert isinstance(msg, HumanMessage)
    assert isinstance(msg.content, list)
    assert len(msg.content) == 2
    assert msg.content[0] == {"type": "text", "text": "What is this?"}
    assert msg.content[1]["type"] == "image_url"
    assert "data:image/jpeg;base64,abc123" in msg.content[1]["image_url"]["url"]


def test_build_human_message_none_image_returns_text():
    msg = ConversationService._build_human_message("Just text", image_b64=None)
    assert isinstance(msg.content, str)
    assert msg.content == "Just text"
