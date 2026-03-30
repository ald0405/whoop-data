from __future__ import annotations

from whoopdata.agent.model_config_loader import (
    get_specialist_model_config,
    get_supervisor_model_config,
)
from whoopdata.agent.model_factory import build_chat_model


def test_supervisor_model_config_is_present_and_normalised():
    cfg = get_supervisor_model_config()
    assert cfg["provider"] == "openai"
    assert isinstance(cfg["model"], str) and cfg["model"]
    assert isinstance(cfg["timeout_seconds"], float)
    assert isinstance(cfg["max_retries"], int)


def test_specialist_model_config_falls_back_to_default():
    cfg = get_specialist_model_config("unknown_specialist")
    assert cfg["provider"] == "openai"
    assert cfg["model"] == "gpt-4o-mini"


def test_model_factory_passes_expected_kwargs(monkeypatch):
    captured: dict = {}

    def _fake_init_chat_model(model: str, **kwargs):
        captured["model"] = model
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr("whoopdata.agent.model_factory.init_chat_model", _fake_init_chat_model)

    model = build_chat_model(
        {
            "provider": "openai",
            "model": "gpt-5.2",
            "temperature": 0.1,
            "max_output_tokens": 1200,
            "timeout_seconds": 30.0,
            "max_retries": 2,
            "reasoning_effort": "medium",
        }
    )

    assert model is not None
    assert captured["model"] == "openai:gpt-5.2"
    assert captured["kwargs"]["temperature"] == 0.1
    assert captured["kwargs"]["max_tokens"] == 1200
    assert captured["kwargs"]["timeout"] == 30.0
    assert captured["kwargs"]["max_retries"] == 2
    assert captured["kwargs"]["use_responses_api"] is False
