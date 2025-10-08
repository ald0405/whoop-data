"""Agent configuration settings."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"  # Cost-effective for development
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 1000

# LangSmith Configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "whoop-health-agent")

# Health Data API Configuration
HEALTH_API_BASE_URL = os.getenv("HEALTH_API_BASE_URL", "http://localhost:8000")
DEFAULT_USER_ID = "default_user"

# Agent Configuration
AGENT_TIMEOUT_SECONDS = 30.0
MAX_ITERATIONS = 10