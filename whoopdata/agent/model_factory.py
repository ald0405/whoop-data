"""Build LangChain chat model instances from validated agent model config."""

from __future__ import annotations

from typing import Any

from langchain.chat_models import init_chat_model


def _model_identifier(provider: str, model: str) -> str:
    if ":" in model:
        return model
    return f"{provider}:{model}"


def build_chat_model(cfg: dict[str, Any]):
    """Build a chat model instance from normalised config."""
    provider = cfg["provider"]
    model = cfg["model"]
    kwargs: dict[str, Any] = {
        "timeout": cfg.get("timeout_seconds"),
        "max_retries": cfg.get("max_retries"),
    }
    if provider == "openai":
        # Keep the agent runtime on chat completions for stable tool-call loops.
        kwargs["use_responses_api"] = False
    if cfg.get("temperature") is not None:
        kwargs["temperature"] = cfg["temperature"]
    if cfg.get("max_output_tokens") is not None:
        kwargs["max_tokens"] = cfg["max_output_tokens"]

    return init_chat_model(_model_identifier(provider, model), **kwargs)
