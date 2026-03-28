"""Agent configuration settings."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # 128K context, good balance of cost and performance
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 1000

# LangSmith Configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "whoop-health-agent")

# Health Data API Configuration
HEALTH_API_BASE_URL = os.getenv("HEALTH_API_BASE_URL", "http://localhost:8000")
DEFAULT_USER_ID = "default_user"

# Weather API Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DEFAULT_LOCATION = "Canary Wharf"  # Default location for weather queries

# Transport API Configuration
TFL_API_BASE_URL = "https://api.tfl.gov.uk"
TFL_KEY_LINES = ["Jubilee", "DLR", "Elizabeth line", "Northern"]  # Lines near South Quay DLR

# Agent Configuration
AGENT_TIMEOUT_SECONDS = 30.0
MAX_ITERATIONS = 10
AGENT_POSTGRES_URL = os.getenv("AGENT_POSTGRES_URL")
AGENT_PERSISTENCE_AUTO_SETUP = (
    os.getenv("AGENT_PERSISTENCE_AUTO_SETUP", "true").strip().lower() == "true"
)

# Supervisor model (delegates to specialists)
SUPERVISOR_MODEL = "openai:gpt-5.2"

# Default specialist model
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

# Per-specialist overrides (model, temperature, etc.)
SPECIALIST_CONFIG: dict = {
    # "analytics": {"model": "openai:gpt-4o"},  # Example: use stronger model for analytics
}
