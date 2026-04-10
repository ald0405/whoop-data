"""Agent configuration settings."""

import os
from typing import Any
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LangSmith Configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "whoop-health-agent")

# Health Data API Configuration
HEALTH_API_BASE_URL = os.getenv("HEALTH_API_BASE_URL", "http://localhost:8000")
DEFAULT_USER_ID = "default_user"

# Weather API Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
# Location used for weather queries and day-of briefings.
# Settable via DEFAULT_LOCATION in .env; falls back to Canary Wharf for existing deployments.
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Canary Wharf")
# ISO 3166-1 alpha-2 country code (e.g. "GB", "US", "DE").  Used to disambiguate geocoding.
DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "GB")

# Transport API Configuration
TFL_API_BASE_URL = "https://api.tfl.gov.uk"
# Feature flag: enable TFL (Transport for London) integration.
# Only meaningful when the user is in the Greater London area.
TFL_ENABLED: bool = os.getenv("ENABLE_TFL", "false").strip().lower() == "true"
# Comma-separated TfL lines to monitor (used when TFL_ENABLED=true).
_tfl_lines_env = os.getenv("TFL_KEY_LINES", "Jubilee,DLR,Elizabeth line")
TFL_KEY_LINES: list[str] = [ln.strip() for ln in _tfl_lines_env.split(",") if ln.strip()]

# Feature flag: enable Thames tidal data (Environment Agency Flood Monitoring API).
# Only meaningful when the user is in the Greater London / Thames Estuary area.
THAMES_TIDES_ENABLED: bool = os.getenv("ENABLE_THAMES_TIDES", "false").strip().lower() == "true"

# Agent Configuration
AGENT_TIMEOUT_SECONDS = 30.0
MAX_ITERATIONS = 10
AGENT_POSTGRES_URL = os.getenv("AGENT_POSTGRES_URL")
AGENT_PERSISTENCE_AUTO_SETUP = (
    os.getenv("AGENT_PERSISTENCE_AUTO_SETUP", "true").strip().lower() == "true"
)
# Proactive coach configuration (settings-only single source of truth)
# Used by: whoopdata/services/proactive_coach.py
PROACTIVE_COACH_ENABLED = True
PROACTIVE_WINDOW_START_HOUR = 8
PROACTIVE_WINDOW_END_HOUR = 14
PROACTIVE_GLOBAL_COOLDOWN_HOURS = 4
PROACTIVE_DUPLICATE_COOLDOWN_HOURS = 24
PROACTIVE_MORNING_COOLDOWN_HOURS = 8
PROACTIVE_HIDDEN_LOAD_STRAIN_THRESHOLD = 10.0
PROACTIVE_RUN_GAP_DAYS = 7
PROACTIVE_RUN_HISTORY_DAYS = 90
PROACTIVE_MIN_RUNS_FOR_HABIT_SIGNAL = 3
PROACTIVE_WEIGHT_STALE_DAYS = 7
PROACTIVE_ESCALATION_DELAY_DAYS = 3
# Used by: scripts/scheduled_etl.py
PROACTIVE_POST_ETL_EVALUATION = False
# Canonical per-agent LLM configuration (single source of truth for runtime agent models)
LLM_CONFIG: dict[str, dict[str, Any]] = {
    "supervisor_agent": {
        "provider": "openai",
        "model": "gpt-5.4-mini",
        "temperature": 0.1,
        "max_output_tokens": 1500,
        "timeout_seconds": 30.0,
        "max_retries": 2,
        "reasoning_effort": "low",
    },
    "specialist_default": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_output_tokens": 1000,
        "timeout_seconds": 30.0,
        "max_retries": 2,
    },
    "health_data": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_output_tokens": 1000,
        "timeout_seconds": 30.0,
        "max_retries": 2,
    },
    "analytics": {
        "provider": "openai",
        "model": "gpt-5.2",
        "temperature": 0.1,
        "max_output_tokens": 1200,
        "timeout_seconds": 30.0,
        "max_retries": 2,
        "reasoning_effort": "medium",
    },
    "environment": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_output_tokens": 1000,
        "timeout_seconds": 30.0,
        "max_retries": 2,
    },
    "exercise": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_output_tokens": 1000,
        "timeout_seconds": 30.0,
        "max_retries": 2,
    },
    "behaviour_change": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_output_tokens": 1000,
        "timeout_seconds": 30.0,
        "max_retries": 2,
    },
    "nutrition": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_output_tokens": 1000,
        "timeout_seconds": 30.0,
        "max_retries": 2,
    },
    "biomechanics": {
        "provider": "openai",
        "model": "gpt-5.4-mini",
        "temperature": 0.2,
        "max_output_tokens": 1500,
        "timeout_seconds": 45.0,
        "max_retries": 2,
    },
}


def get_supervisor_llm_config() -> dict[str, Any]:
    """Return the configured supervisor model settings."""
    return dict(LLM_CONFIG["supervisor_agent"])


def get_specialist_llm_config(name: str) -> dict[str, Any]:
    """Return model settings for a specialist, falling back to specialist_default."""
    return dict(LLM_CONFIG.get(name, LLM_CONFIG["specialist_default"]))
SPECIALIST_MODEL = "openai:gpt-4o-mini"

# Voice transcription (Whisper)
WHISPER_MODEL = "whisper-1"

# Text-to-Speech
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = os.getenv("TTS_VOICE", "nova")
TTS_INSTRUCTIONS = (
    "Speak in a direct, energetic coaching tone. Be concise and sharp — "
    "like a personal trainer who's also a data scientist with the whit and Charm of Hannah Fry "
    "Keep it conversational and natural, not robotic."
)

