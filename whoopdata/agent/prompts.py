"""System prompts for the agent architecture."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "data" / "prompts" / "agents"


def load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory, or "" if the file is missing."""
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text()
    logger.warning("Prompt file not found at %s", path)
    return ""


def build_supervisor_prompt(now: datetime | None = None) -> str:
    """Build the supervisor prompt with the current date injected.

    Called per model call (see ``graph.supervisor_prompt``) rather than once at
    import, so the long-running Telegram bot never reports a stale date.
    """
    now = now or datetime.now()
    date_line = (
        f"\n**Today is {now.strftime('%A, %d %B %Y')}** (use YYYY-MM-DD format for date filters)\n"
    )
    return date_line + load_prompt("supervisor.md")
