"""System prompts for the agent architecture."""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "data" / "prompts" / "agents"


def _load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    path = _PROMPTS_DIR / filename
    if path.exists():
        return path.read_text()
    return ""


SUPERVISOR_SYSTEM_PROMPT = _load_prompt("supervisor.md")
