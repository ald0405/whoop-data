"""System prompts for the agent architecture."""

from pathlib import Path
from datetime import datetime

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "data" / "prompts" / "agents"


def _load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    path = _PROMPTS_DIR / filename
    if path.exists():
        return path.read_text()
    return ""


def _get_supervisor_prompt() -> str:
    """Get supervisor prompt with current date injected."""
    base_prompt = _load_prompt("supervisor.md")
    now = datetime.now()
    date_line = f"\n**Today is {now.strftime('%A, %d %B %Y')}** (use YYYY-MM-DD format for date filters)\n"
    return date_line + base_prompt


SUPERVISOR_SYSTEM_PROMPT = _get_supervisor_prompt()
