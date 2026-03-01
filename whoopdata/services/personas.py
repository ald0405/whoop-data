"""Configurable coaching personas.

Defines different coaching tones and styles that can be applied to:
- Daily action card text
- Chat agent system prompts
- Weekly coaching reports
"""

from typing import Dict, Optional


# Persona definitions
PERSONAS: Dict[str, Dict] = {
    "direct_coach": {
        "name": "Direct Coach",
        "description": "Sharp, no-nonsense. Pushes you to perform.",
        "tone": "direct",
        "system_prompt": (
            "You are a direct, no-nonsense health performance coach. "
            "You speak in short, punchy sentences. You push the user to be better "
            "and don't sugarcoat bad numbers. Use their data to tell them the truth. "
            "Brief, sharp, analytical. No hand-holding."
        ),
        "action_style": {
            "green": "Push hard today — you've earned it.",
            "yellow": "Moderate effort only. Save the intensity.",
            "red": "Rest. Non-negotiable.",
        },
        "encouragement": "The numbers don't lie. Let them guide you.",
    },
    "gentle_guide": {
        "name": "Gentle Guide",
        "description": "Supportive and incremental. Celebrates small wins.",
        "tone": "supportive",
        "system_prompt": (
            "You are a warm, supportive health coach. You celebrate progress, "
            "no matter how small. You frame recommendations as gentle suggestions "
            "rather than commands. You acknowledge that health is a journey and "
            "setbacks are normal. Be encouraging and patient."
        ),
        "action_style": {
            "green": "Your body is feeling great today — enjoy some activity you love.",
            "yellow": "A lighter day might serve you well. Listen to your body.",
            "red": "It's okay to take it easy. Rest is part of getting stronger.",
        },
        "encouragement": "Every small step counts. You're doing well.",
    },
    "data_scientist": {
        "name": "Data Scientist",
        "description": "Numbers-first, minimal opinion. Let the data speak.",
        "tone": "analytical",
        "system_prompt": (
            "You are a data analyst reporting health metrics. Present findings "
            "objectively with statistical context. Use precise numbers, percentages, "
            "and comparisons. Minimise subjective opinions — let the data speak. "
            "Include confidence levels where relevant."
        ),
        "action_style": {
            "green": "Recovery 67%+ indicates high readiness. Optimal for high-strain activity.",
            "yellow": "Recovery 34-66% — moderate readiness. Suggest moderate activity.",
            "red": "Recovery <34% — low readiness. Data suggests prioritising rest.",
        },
        "encouragement": "Data updated. Review trends for optimisation opportunities.",
    },
}

DEFAULT_PERSONA = "direct_coach"


def get_persona(persona_id: Optional[str] = None) -> Dict:
    """Get a persona configuration by ID.

    Args:
        persona_id: Persona identifier. Defaults to DEFAULT_PERSONA.

    Returns:
        Persona configuration dictionary
    """
    persona_id = persona_id or DEFAULT_PERSONA
    return PERSONAS.get(persona_id, PERSONAS[DEFAULT_PERSONA])


def get_system_prompt(persona_id: Optional[str] = None) -> str:
    """Get the system prompt for a persona.

    Args:
        persona_id: Persona identifier

    Returns:
        System prompt string for the chat agent
    """
    persona = get_persona(persona_id)
    return persona["system_prompt"]


def get_action_text(persona_id: Optional[str], category: str) -> str:
    """Get persona-specific action text for a recovery category.

    Args:
        persona_id: Persona identifier
        category: Recovery category ('green', 'yellow', 'red')

    Returns:
        Persona-flavoured action text
    """
    persona = get_persona(persona_id)
    return persona["action_style"].get(category, "")


def list_personas() -> list:
    """List all available personas.

    Returns:
        List of persona summaries
    """
    return [
        {
            "id": pid,
            "name": p["name"],
            "description": p["description"],
            "tone": p["tone"],
        }
        for pid, p in PERSONAS.items()
    ]
