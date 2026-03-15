"""Stable public response contract for conversational interactions."""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field


class AgentArtifact(BaseModel):
    kind: Literal["image", "python_code"]
    title: str | None = None
    mime_type: str | None = None
    content: str

class AgentConversationCreateRequest(BaseModel):
    session_id: str | None = None
    thread_id: str | None = None


class AgentConversationHandle(BaseModel):
    surface: Literal["agent"] = "agent"
    thread_id: str
    session_id: str


class AgentConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class AgentMessageRequest(BaseModel):
    message: str = Field(min_length=1)
    thread_id: str | None = None
    session_id: str | None = None


class AgentConversationResponse(BaseModel):
    surface: Literal["agent"] = "agent"
    thread_id: str
    session_id: str | None = None
    assistant_message: str
    messages: list[AgentConversationTurn]
    artifacts: list[AgentArtifact] = Field(default_factory=list)


def _extract_assistant_message(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and isinstance(message.content, str) and message.content:
            return message.content

    return "I processed your request, but didn't generate a response. Please try rephrasing your question."


def _extract_artifacts(messages: list[Any]) -> list[AgentArtifact]:
    artifacts: list[AgentArtifact] = []

    for message in messages:
        content = getattr(message, "content", None)
        if isinstance(content, str) and '{"images"' in content:
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                payload = None

            if isinstance(payload, dict):
                for image in payload.get("images", []):
                    image_data = image.get("data")
                    if not image_data:
                        continue

                    artifacts.append(
                        AgentArtifact(
                            kind="image",
                            title=image.get("filename"),
                            mime_type="image/png",
                            content=image_data,
                        )
                    )

        tool_calls = getattr(message, "tool_calls", None) or ()
        for tool_call in tool_calls:
            name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)
            if name != "python_interpreter":
                continue

            args = tool_call.get("args", {}) if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
            code = args.get("query", "")
            if not code:
                continue

            artifacts.append(
                AgentArtifact(
                    kind="python_code",
                    title="Generated Python Code",
                    content=code,
                )
            )

    return artifacts


def build_agent_conversation_response(
    result: dict[str, Any] | None,
    *,
    thread_id: str,
    user_message: str,
    session_id: str | None = None,
) -> AgentConversationResponse:
    messages = list(result.get("messages", [])) if isinstance(result, dict) else []
    assistant_message = _extract_assistant_message(messages)

    return AgentConversationResponse(
        thread_id=thread_id,
        session_id=session_id,
        assistant_message=assistant_message,
        messages=[
            AgentConversationTurn(role="user", content=user_message),
            AgentConversationTurn(role="assistant", content=assistant_message),
        ],
        artifacts=_extract_artifacts(messages),
    )
