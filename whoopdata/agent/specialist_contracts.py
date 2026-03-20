"""Typed contracts for specialist delegation.

These contracts are owned by the application layer rather than by prompt prose.
They define the deterministic handoff/render/parse boundary the current wrapper
layer can use today, while staying compatible with LangChain's structured
output support for later tickets.
"""

from __future__ import annotations

from functools import lru_cache
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator

SPECIALIST_CONTRACT_VERSION = "1.0"

SpecialistName = Literal[
    "health_data",
    "analytics",
    "environment",
    "exercise",
    "behaviour_change",
    "nutrition",
]
ConfidenceLevel = Literal["low", "medium", "high"]
PriorityLevel = Literal["low", "medium", "high"]
ConstraintType = Literal[
    "scope",
    "safety",
    "preference",
    "tooling",
    "time",
    "data_quality",
    "medical",
    "other",
]
ResultStatus = Literal[
    "completed",
    "needs_clarification",
    "blocked",
    "unsafe",
    "out_of_scope",
]
SafetySeverity = Literal["low", "medium", "high", "critical"]


class SpecialistContractModel(BaseModel):
    """Base model for deterministic specialist contract validation."""

    model_config = ConfigDict(extra="forbid")


class SpecialistFact(SpecialistContractModel):
    """Fact passed into a specialist handoff."""

    name: str = Field(description="Short label for the fact.")
    value: str = Field(description="Fact content rendered as a compact string.")
    source: str | None = Field(
        default=None,
        description="Optional provenance for the fact, such as WHOOP or a prior specialist.",
    )
    observed_at: str | None = Field(
        default=None,
        description="Optional date or timestamp associated with the fact.",
    )


class SpecialistConstraint(SpecialistContractModel):
    """Constraint the specialist should respect while working the task."""

    type: ConstraintType = Field(description="Constraint category.")
    detail: str = Field(description="What the specialist must respect or avoid.")
    hard: bool = Field(
        default=True,
        description="Whether the constraint is mandatory rather than advisory.",
    )


class SafetyNote(SpecialistContractModel):
    """Safety-related note attached to a handoff or result."""

    severity: SafetySeverity = Field(default="low", description="Safety severity level.")
    detail: str = Field(description="The safety note or concern.")


class OutputRequirement(SpecialistContractModel):
    """Specific output shape or content the supervisor expects back."""

    name: str = Field(description="Short label for the requirement.")
    description: str = Field(description="What the specialist should provide.")
    required: bool = Field(default=True, description="Whether this requirement is mandatory.")


class SpecialistFinding(SpecialistContractModel):
    """Key finding returned by a specialist."""

    summary: str = Field(description="The core finding.")
    evidence: str | None = Field(
        default=None,
        description="Optional evidence or context supporting the finding.",
    )
    priority: PriorityLevel = Field(
        default="medium",
        description="Relative importance of the finding to the supervisor.",
    )


class SpecialistRecommendation(SpecialistContractModel):
    """Action or recommendation returned by a specialist."""

    action: str = Field(description="Recommended action.")
    rationale: str | None = Field(
        default=None,
        description="Why this action follows from the findings.",
    )
    priority: PriorityLevel = Field(
        default="medium",
        description="Relative urgency or importance of the recommendation.",
    )
    time_horizon: str | None = Field(
        default=None,
        description="Optional time horizon such as today, this week, or next session.",
    )


class ClarificationNeed(SpecialistContractModel):
    """Clarification a specialist needs before it can finish reliably."""

    question: str = Field(description="Question the supervisor should ask the user.")
    reason: str = Field(description="Why this clarification is needed.")


class EscalationFlag(SpecialistContractModel):
    """Flag indicating the result should be elevated or handled carefully."""

    reason: str = Field(description="Why the supervisor should treat this result as escalated.")
    priority: PriorityLevel = Field(
        default="medium",
        description="How strongly the escalation should influence routing or tone.",
    )


class SuggestedNextSpecialist(SpecialistContractModel):
    """Optional follow-up specialist recommendation returned to the supervisor."""

    specialist: SpecialistName = Field(description="Suggested follow-up specialist.")
    reason: str = Field(description="Why a follow-up specialist could help.")


class SpecialistHandoff(SpecialistContractModel):
    """Deterministic supervisor-to-specialist handoff contract."""

    version: str = Field(
        default=SPECIALIST_CONTRACT_VERSION,
        description="Contract version for this handoff payload.",
    )
    specialist: SpecialistName = Field(description="The target specialist for this handoff.")
    user_intent: str = Field(description="What the user is trying to achieve.")
    task_objective: str = Field(
        description="What this specialist should accomplish for the supervisor."
    )
    user_context_summary: str | None = Field(
        default=None,
        description="Compact summary of user state or surrounding conversation context.",
    )
    relevant_facts: list[SpecialistFact] = Field(
        default_factory=list,
        description="Facts the specialist should treat as source-grounded context.",
    )
    constraints: list[SpecialistConstraint] = Field(
        default_factory=list,
        description="Task constraints the specialist must respect.",
    )
    safety_notes: list[SafetyNote] = Field(
        default_factory=list,
        description="Safety boundaries or caveats that apply before the specialist acts.",
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Tool names the wrapper intends this specialist to rely on.",
    )
    output_requirements: list[OutputRequirement] = Field(
        default_factory=list,
        description="Specific outputs the supervisor wants back.",
    )
    prior_findings: list[str] = Field(
        default_factory=list,
        description="Concise findings from prior work or prior specialists in the same turn.",
    )
    specialist_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Extension slot for specialist-specific fields that are not shared globally.",
    )

    @model_validator(mode="after")
    def validate_allowed_tools(self) -> "SpecialistHandoff":
        """Reject duplicate tools so the handoff stays deterministic."""

        if len(self.allowed_tools) != len(set(self.allowed_tools)):
            raise ValueError("allowed_tools must not contain duplicates")
        return self


class SpecialistResult(SpecialistContractModel):
    """Deterministic specialist-to-supervisor result contract."""

    version: str = Field(
        default=SPECIALIST_CONTRACT_VERSION,
        description="Contract version for this result payload.",
    )
    specialist: SpecialistName = Field(description="The specialist producing this result.")
    status: ResultStatus = Field(
        default="completed",
        description="Whether the specialist completed, blocked, or needs clarification.",
    )
    summary: str = Field(description="Compact summary the supervisor can reason over.")
    findings: list[SpecialistFinding] = Field(
        default_factory=list,
        description="Key findings from the specialist's work.",
    )
    recommendations: list[SpecialistRecommendation] = Field(
        default_factory=list,
        description="Recommended next actions from this specialist.",
    )
    confidence: ConfidenceLevel = Field(
        default="medium",
        description="Overall confidence in the result.",
    )
    requires_clarification: bool = Field(
        default=False,
        description="Whether the specialist needs more information before proceeding reliably.",
    )
    clarification_needs: list[ClarificationNeed] = Field(
        default_factory=list,
        description="Clarification questions the supervisor can ask the user.",
    )
    safety_flags: list[SafetyNote] = Field(
        default_factory=list,
        description="Safety warnings or boundaries surfaced by the specialist.",
    )
    escalation_flags: list[EscalationFlag] = Field(
        default_factory=list,
        description="Escalation markers the supervisor should consider while routing.",
    )
    suggested_next_specialist: SuggestedNextSpecialist | None = Field(
        default=None,
        description="Optional follow-up specialist recommendation for the supervisor.",
    )
    supervisor_guidance: str | None = Field(
        default=None,
        description="Compact note on how the supervisor should interpret or use this result.",
    )
    specialist_output: dict[str, Any] = Field(
        default_factory=dict,
        description="Extension slot for specialist-specific structured output.",
    )

    @model_validator(mode="after")
    def validate_result_consistency(self) -> "SpecialistResult":
        """Enforce consistency across clarification and routing flags."""

        if self.requires_clarification and not self.clarification_needs:
            raise ValueError(
                "clarification_needs must be populated when requires_clarification is true"
            )
        if not self.requires_clarification and self.clarification_needs:
            raise ValueError(
                "clarification_needs must be empty when requires_clarification is false"
            )
        if self.status == "needs_clarification" and not self.requires_clarification:
            raise ValueError(
                "status='needs_clarification' requires requires_clarification to be true"
            )
        if (
            self.suggested_next_specialist is not None
            and self.suggested_next_specialist.specialist == self.specialist
        ):
            raise ValueError("suggested_next_specialist must differ from the current specialist")
        return self


def render_specialist_handoff(handoff: SpecialistHandoff) -> str:
    """Render a typed handoff into the current text-based specialist boundary."""

    payload = handoff.model_dump(mode="json", exclude_none=True)
    return (
        "Application-owned specialist handoff. Treat the JSON below as the full task contract.\n"
        "If required data is missing, return a structured clarification request instead of inventing facts.\n"
        f"{json.dumps(payload, indent=2, sort_keys=True)}"
    )


def render_specialist_result_instructions() -> str:
    """Render deterministic instructions for the specialist result schema."""

    schema = SpecialistResult.model_json_schema()
    return (
        "Return your final answer as JSON that matches this schema exactly.\n"
        "Do not wrap the JSON in markdown fences.\n"
        f"{json.dumps(schema, indent=2, sort_keys=True)}"
    )


def render_specialist_result(result: SpecialistResult) -> str:
    """Render a validated specialist result as deterministic JSON."""

    payload = result.model_dump(mode="json", exclude_none=True)
    return json.dumps(payload, indent=2, sort_keys=True)


def render_specialist_contract_prompt(handoff: SpecialistHandoff) -> str:
    """Render the full prompt payload for the current wrapper layer."""

    return f"{render_specialist_handoff(handoff)}\n\n" f"{render_specialist_result_instructions()}"


def parse_specialist_result(
    payload: SpecialistResult | dict[str, Any] | str,
) -> SpecialistResult:
    """Parse a specialist result from a model, dict, or raw JSON string."""

    if isinstance(payload, SpecialistResult):
        return payload
    if isinstance(payload, str):
        return SpecialistResult.model_validate_json(payload)
    return SpecialistResult.model_validate(payload)


@lru_cache(maxsize=None)
def build_specialist_handoff_schema(specialist_name: str) -> type[SpecialistHandoff]:
    """Build a tool-facing handoff schema with the specialist defaulted per tool."""

    model_name = "".join(part.capitalize() for part in specialist_name.split("_")) + "Handoff"
    return create_model(
        model_name,
        __base__=SpecialistHandoff,
        specialist=(
            str,
            Field(
                default=specialist_name,
                description=(
                    "Target specialist for this tool call. "
                    "Defaults to the current specialist tool."
                ),
            ),
        ),
    )
