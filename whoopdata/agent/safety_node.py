"""Graph-internal safety node for the biomarker analyser (Phase 0 prototype).

This is the deterministic enforcement of the intended-purpose "does NOT" list
(docs/features/BIOMARKER_INTENDED_PURPOSE.md). It runs on the final assistant
text *inside the compiled graph*, so BOTH user-facing surfaces are covered:
the LangGraph/LangSmith UI (which loads the graph directly via
``langgraph.json``) and Telegram (which calls the same graph through the
ConversationService boundary).

Scope of the prototype net: regex over the assistant's text. It catches the
verdict/interpretation/trend/consequence patterns the intended purpose forbids.
It does NOT understand paraphrase — an accepted prototype trade-off recorded in
the plan. If it fires, the model output is replaced with a fixed safe fallback.

Important false-positive guard: bare "high"/"low" are NOT blocked (otherwise
"low-density lipoprotein" / "high-density lipoprotein" in legitimate generic
education would trip). Only verdict *constructions* (a result described as
high/low/normal/in-range) and interpretation/condition/treatment/trend language
are blocked.
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage

FALLBACK_TEXT = (
    "I can show you your biomarker values and the testing lab's own reference ranges, "
    "and explain in general terms what a biomarker is and does. I can't tell you how "
    "your result compares to the range or what it means for you personally. For any "
    "interpretation of your results, please speak with a clinician."
)

# Each pattern is paired with a short reason for the audit log.
_BLOCK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # --- Verdict: a result described as high/low/normal/abnormal/optimal ---
    (re.compile(
        r"\b(is|are|looks?|seems?|appears?|reads?|coming in|came back|comes back|"
        r"result is|results are|reading is|levels? (?:is|are))\s+"
        r"(?:a (?:little|bit) )?(?:slightly |somewhat |quite |very |too |"
        r"borderline |mildly |markedly )?"
        r"(high|low|elevated|raised|reduced|deficient|abnormal|normal|optimal)\b",
        re.IGNORECASE), "verdict: result described as high/low/normal"),
    (re.compile(
        r"\b(elevated|raised|reduced|deficient|abnormal|optimal)\s+"
        r"(level|result|reading|value|amount|count)s?\b",
        re.IGNORECASE), "verdict: high/low qualifier on a level/result"),
    # --- Range judgements (above/below/within/out of range) ---
    (re.compile(
        r"\b(above|below|outside|within|under|over)\s+(the\s+)?"
        r"(normal\s+|reference\s+|healthy\s+|lab'?s?\s+)?(range|limits?)\b",
        re.IGNORECASE), "verdict: above/below/within range"),
    (re.compile(r"\bout[\s-]of[\s-]range\b", re.IGNORECASE), "verdict: out of range"),
    (re.compile(r"\b(in|within)\s+(the\s+)?normal\s+(range|limits?)\b",
                re.IGNORECASE), "verdict: within normal range"),
    # --- Interpretation / consequence-of-abnormal ---
    (re.compile(
        r"\b(indicat(?:e|es|ing|ed)|suggest(?:s|ing|ed)|implies|implying|"
        r"consistent with|a sign of|symptom|risk of|at (?:increased |elevated |higher )?risk|"
        r"linked to|associated with|can cause|may cause|could cause|"
        r"leads? to|could lead to|puts? you at|results? in)\b",
        re.IGNORECASE), "interpretation: links result to a meaning/consequence"),
    # --- Named conditions / diagnoses ---
    (re.compile(
        r"\b(deficiency|an(?:ae|e)mia|diabet(?:es|ic)|pre[\s-]?diabet(?:es|ic)|"
        r"cardiovascular|heart disease|fatty liver|kidney disease|"
        r"hypothyroid\w*|hyperthyroid\w*|gout|malabsorption|arrhythmia|"
        r"deficien(?:t|cy))\b",
        re.IGNORECASE), "condition: names a disease/condition"),
    (re.compile(
        r"\b(diagnos(?:e|es|ed|is|ing)|you have|you'?ve got|you are (?:likely |probably )?"
        r"(?:suffering|developing|at risk))\b",
        re.IGNORECASE), "diagnosis"),
    # --- Treatment / dosing / medication decisions ---
    (re.compile(
        r"\b(prescrib\w+|supplement(?:s|ation|ing)?|medication|dosage|dose\b|"
        r"taper\w*|come off|stop taking|able to stop|you should (?:take|start|stop)|"
        r"start (?:taking|supplement))\b",
        re.IGNORECASE), "treatment/dosing recommendation"),
    # --- Trend / longitudinal monitoring ---
    (re.compile(
        r"\b(trend\w*|over time|compared to (?:your )?(?:last|previous|earlier|prior)|"
        r"since your (?:last|previous|earlier)|declin\w+|"
        r"(?:increas|ris|fall|drop)\w*\s+(?:over|since)|been (?:rising|falling)|"
        r"monitor\w*)\b",
        re.IGNORECASE), "trend/longitudinal monitoring"),
    # --- Numeric risk claims (not bare %, which appears in real results) ---
    (re.compile(r"\b\d+(?:\.\d+)?\s?%\s+(?:risk|chance|likelihood|probability)\b",
                re.IGNORECASE), "numeric risk claim"),
    (re.compile(r"\brisk score\b", re.IGNORECASE), "risk score"),
]


def evaluate_text(text: str) -> tuple[str, str | None]:
    """Evaluate assistant text against the intended-purpose 'does NOT' list.

    Returns ``("pass", None)`` or ``("blocked", reason)``.
    """
    if not text:
        return "pass", None
    for pattern, reason in _BLOCK_PATTERNS:
        if pattern.search(text):
            return "blocked", reason
    return "pass", None


def _log_audit(surface: str, verdict: str, reason: str | None) -> None:
    """Best-effort write to safety_audit. Never raises into the response path."""
    try:
        from whoopdata.crud import biomarker  # noqa: F401  (ensures package import)
        from whoopdata.database.database import SessionLocal
        from whoopdata.models.models import SafetyAudit

        db = SessionLocal()
        try:
            db.add(SafetyAudit(surface=surface, verdict=verdict, reason=reason))
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def _last_ai_text(messages: list[Any]) -> tuple[int, str] | None:
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content.strip():
            return idx, msg.content
    return None


async def safety_node(state: dict, runtime: Any = None) -> dict:
    """Inspect the final assistant message; replace it if it breaks the boundary.

    On a block, append a fresh AIMessage carrying the fixed fallback text so the
    *last* AIMessage (what every surface extracts) is the safe one.
    """
    messages = state.get("messages", []) if isinstance(state, dict) else []
    found = _last_ai_text(messages)

    surface = "unknown"
    if runtime is not None and getattr(runtime, "context", None) is not None:
        surface = getattr(runtime.context, "surface", "unknown") or "unknown"

    if found is None:
        return {}

    _idx, text = found
    verdict, reason = evaluate_text(text)
    _log_audit(surface, verdict, reason)

    if verdict == "blocked":
        return {"messages": [AIMessage(content=FALLBACK_TEXT)]}
    return {}
