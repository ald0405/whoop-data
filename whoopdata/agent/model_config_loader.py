"""Load and validate runtime model configuration for supervisor and specialists."""

from __future__ import annotations

from typing import Any

from . import settings

_VALID_PROVIDERS = {"openai"}
_VALID_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh"}
_REQUIRED_KEYS = {"provider", "model", "timeout_seconds", "max_retries"}


def _validate_entry(name: str, cfg: dict[str, Any]) -> None:
    missing = _REQUIRED_KEYS - set(cfg.keys())
    if missing:
        raise ValueError(f"LLM_CONFIG[{name!r}] missing required keys: {sorted(missing)}")

    provider = str(cfg["provider"]).strip().lower()
    if provider not in _VALID_PROVIDERS:
        raise ValueError(f"LLM_CONFIG[{name!r}] has unsupported provider: {provider!r}")

    model = str(cfg["model"]).strip()
    if not model:
        raise ValueError(f"LLM_CONFIG[{name!r}] model must be non-empty")

    reasoning_effort = cfg.get("reasoning_effort")
    if reasoning_effort is not None:
        if str(reasoning_effort).lower() not in _VALID_REASONING_EFFORTS:
            raise ValueError(
                f"LLM_CONFIG[{name!r}] reasoning_effort must be one of {sorted(_VALID_REASONING_EFFORTS)}"
            )


def _normalise_entry(cfg: dict[str, Any]) -> dict[str, Any]:
    norm = dict(cfg)
    norm["provider"] = str(norm["provider"]).strip().lower()
    norm["model"] = str(norm["model"]).strip()
    if "temperature" in norm and norm["temperature"] is not None:
        norm["temperature"] = float(norm["temperature"])
    if "max_output_tokens" in norm and norm["max_output_tokens"] is not None:
        norm["max_output_tokens"] = int(norm["max_output_tokens"])
    norm["timeout_seconds"] = float(norm["timeout_seconds"])
    norm["max_retries"] = int(norm["max_retries"])
    if "reasoning_effort" in norm and norm["reasoning_effort"] is not None:
        norm["reasoning_effort"] = str(norm["reasoning_effort"]).strip().lower()
    return norm


def get_supervisor_model_config() -> dict[str, Any]:
    """Return validated supervisor model configuration."""
    cfg = settings.get_supervisor_llm_config()
    _validate_entry("supervisor_agent", cfg)
    return _normalise_entry(cfg)


def get_specialist_model_config(agent_name: str) -> dict[str, Any]:
    """Return validated model configuration for a specialist."""
    cfg = settings.get_specialist_llm_config(agent_name)
    _validate_entry(agent_name, cfg)
    return _normalise_entry(cfg)
