"""Standalone biomechanics agent for direct video frame analysis.

This module provides the video-path biomechanics agent that is invoked
directly by the Telegram gateway (bypassing the supervisor). It shares
the same system prompt and model config as the supervisor-routed
biomechanics specialist registered in AGENT_REGISTRY, but receives
multi-image HumanMessages containing extracted video frames.

The text-path (follow-up questions) is handled by the supervisor routing
to the biomechanics specialist tool — both paths share memory.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from .memory_tools import manage_memory, search_memory
from .model_config_loader import get_specialist_model_config
from .model_factory import build_chat_model
from .schemas import HealthContextSchema

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "data" / "prompts" / "agents"
_BIOMECHANICS_PROMPT_FILE = "biomechanics_sub_agent.md"

# Module-level cache for the compiled agent
_cached_agent = None


def _load_system_prompt() -> str:
    """Load the biomechanics specialist system prompt from disk.

    Returns:
        The system prompt text, or an empty string if the file is missing.

    Example:
        >>> prompt = _load_system_prompt()
        >>> "Biomechanics" in prompt
        True
    """
    path = _PROMPTS_DIR / _BIOMECHANICS_PROMPT_FILE
    if path.exists():
        return path.read_text()
    logger.warning("Biomechanics prompt file not found at %s", path)
    return ""


def build_biomechanics_agent():
    """Build and cache the standalone biomechanics create_agent instance.

    The agent is compiled once and reused across invocations. It uses the
    ``biomechanics`` entry from ``LLM_CONFIG`` (gpt-5.4-mini, vision-capable)
    and has access to ``search_memory`` and ``manage_memory`` tools.

    Returns:
        A compiled LangGraph agent ready for ``.ainvoke()``.

    Example:
        >>> agent = build_biomechanics_agent()
        >>> hasattr(agent, "ainvoke")
        True
    """
    global _cached_agent
    if _cached_agent is not None:
        return _cached_agent

    model = build_chat_model(get_specialist_model_config("biomechanics"))
    system_prompt = _load_system_prompt()

    _cached_agent = create_agent(
        model=model,
        tools=[search_memory, manage_memory],
        system_prompt=system_prompt,
        name="biomechanics",
    )
    return _cached_agent


def build_multiimage_human_message(
    images_b64: list[str],
    text: str,
) -> HumanMessage:
    """Build a HumanMessage with text and multiple base64-encoded images.

    Each image is included as an ``image_url`` content block with
    ``detail: high`` so the model can clearly see joint overlay markers.

    Args:
        images_b64: List of base64-encoded JPEG image strings.
        text: The user's prompt text accompanying the images.

    Returns:
        A ``HumanMessage`` with multi-image content blocks.

    Example:
        >>> msg = build_multiimage_human_message(["abc123=="], "Analyse my serve")
        >>> len(msg.content)
        2
        >>> msg.content[0]["type"]
        'text'
        >>> msg.content[1]["type"]
        'image_url'
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for img_b64 in images_b64:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_b64}",
                    "detail": "high",
                },
            }
        )
    return HumanMessage(content=content)


def _extract_final_text(result: dict) -> str:
    """Extract the final text response from a create_agent invocation result.

    Walks backwards through the message list to find the last ``AIMessage``
    without tool calls, which is the agent's final response.

    Args:
        result: The dict returned by ``agent.ainvoke()``.

    Returns:
        The assistant's final text response.

    Example:
        >>> _extract_final_text({"messages": [AIMessage(content="Good form!")]})
        'Good form!'
    """
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            return msg.content if isinstance(msg.content, str) else msg.text
    if messages:
        last = messages[-1]
        return last.content if hasattr(last, "content") else str(last)
    return "No response from biomechanics agent."


async def analyze_video(
    images_b64: list[str],
    prompt: str,
    *,
    user_id: str = "default_user",
) -> str:
    """Analyse video frames using the standalone biomechanics agent.

    Builds a multi-image ``HumanMessage``, invokes the biomechanics agent,
    and returns the final text analysis. The agent will auto-save the
    analysis to memory via ``manage_memory`` (instructed in its prompt).

    Args:
        images_b64: List of base64-encoded JPEG frame strings extracted
            from the video.
        prompt: Text prompt accompanying the frames (user caption or
            default biomechanics analysis request).
        user_id: User identifier for the memory store context.

    Returns:
        The agent's biomechanics analysis as plain text.

    Raises:
        Exception: Propagated from the underlying agent invocation if
            the model call fails.

    Example:
        >>> # In an async context:
        >>> result = await analyze_video(
        ...     images_b64=["<b64-frame-1>", "<b64-frame-2>"],
        ...     prompt="Analyse my tennis serve form",
        ...     user_id="telegram:12345",
        ... )
        >>> isinstance(result, str)
        True
    """
    agent = build_biomechanics_agent()
    human_message = build_multiimage_human_message(images_b64, prompt)
    context = HealthContextSchema(user_id=user_id, surface="telegram")

    result = await agent.ainvoke(
        {"messages": [human_message]},
        context=context,
    )
    return _extract_final_text(result)
