"""Centralized supervisor routing policy for specialist orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import HumanMessage, ToolMessage

from .registry import AGENT_REGISTRY
from .specialist_contracts import (
    EscalationFlag,
    SpecialistResult,
    parse_specialist_result,
    render_specialist_result,
)


@dataclass(frozen=True)
class SupervisorRoutingPolicy:
    """Application-owned routing rules enforced at the supervisor boundary."""

    final_response_owner: str
    direct_specialist_handoffs_allowed: bool
    max_specialists_per_turn: int
    allow_repeat_specialist: bool
    clarification_blocks_follow_on_delegation: bool
    safety_blocks_follow_on_delegation: bool


SUPERVISOR_ROUTING_POLICY = SupervisorRoutingPolicy(
    final_response_owner="supervisor",
    direct_specialist_handoffs_allowed=False,
    max_specialists_per_turn=2,
    allow_repeat_specialist=False,
    clarification_blocks_follow_on_delegation=True,
    safety_blocks_follow_on_delegation=True,
)


def collect_consulted_specialists(messages: Sequence[Any]) -> tuple[str, ...]:
    """Return prior specialist tool names in consultation order for the current turn."""
    turn_start = 0
    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            turn_start = index + 1

    consulted: list[str] = []
    for message in messages[turn_start:]:
        if isinstance(message, ToolMessage) and message.name in AGENT_REGISTRY:
            consulted.append(str(message.name))
    return tuple(consulted)


def build_supervisor_routing_guidance(
    result: SpecialistResult,
    *,
    consulted_specialists: Sequence[str],
    policy: SupervisorRoutingPolicy = SUPERVISOR_ROUTING_POLICY,
) -> str:
    """Generate deterministic supervisor guidance from a specialist result."""

    consulted = ", ".join(consulted_specialists) if consulted_specialists else "none"
    remaining_budget = max(policy.max_specialists_per_turn - len(consulted_specialists), 0)
    lines = [
        f"Central routing policy: consulted specialists this turn: {consulted}.",
        "You remain the only component that speaks to the user.",
    ]

    if result.requires_clarification or result.status == "needs_clarification":
        lines.append(
            "Stop delegating now and ask only the clarification questions listed in "
            "clarification_needs."
        )
    elif result.status in {"unsafe", "out_of_scope"} or (
        policy.safety_blocks_follow_on_delegation
        and (result.safety_flags or result.escalation_flags)
    ):
        lines.append(
            "Do not delegate again unless another specialist is clearly required to manage the "
            "same safety concern. Address the safety or escalation flags in your response."
        )
    elif result.suggested_next_specialist is not None:
        suggested = result.suggested_next_specialist.specialist
        if suggested in consulted_specialists:
            lines.append(
                f"Do not call {suggested} because that specialist has already been consulted "
                "this turn. Synthesize the final response yourself."
            )
        elif remaining_budget > 0:
            lines.append(
                f"You may consult {suggested} next only if it materially helps answer the "
                "user's request. If you do, pass forward this specialist's summary, findings, "
                "recommendations, and any safety context as prior_findings."
            )
        else:
            lines.append(
                "Do not call another specialist because the per-turn specialist budget is "
                "exhausted. Synthesize the final response yourself."
            )
    elif result.confidence == "low":
        if remaining_budget > 0:
            lines.append(
                "This result is low confidence. Prefer one clarifying question or one clearly "
                "justified follow-on specialist if that would materially reduce uncertainty; "
                "otherwise explain the uncertainty yourself."
            )
        else:
            lines.append(
                "This result is low confidence and no specialist budget remains. Explain the "
                "uncertainty and respond without further delegation."
            )
    else:
        lines.append("No additional specialist is required. Synthesize the final response now.")

    lines.append("Never call the same specialist twice in one turn.")
    return " ".join(lines)


def apply_supervisor_routing_policy(
    result: SpecialistResult,
    *,
    consulted_specialists: Sequence[str],
    policy: SupervisorRoutingPolicy = SUPERVISOR_ROUTING_POLICY,
) -> SpecialistResult:
    """Attach deterministic routing guidance to a specialist result."""

    routing_guidance = build_supervisor_routing_guidance(
        result,
        consulted_specialists=consulted_specialists,
        policy=policy,
    )
    combined_guidance = (
        f"{result.supervisor_guidance.strip()}\n\n{routing_guidance}"
        if result.supervisor_guidance
        else routing_guidance
    )
    return result.model_copy(update={"supervisor_guidance": combined_guidance})


def _build_policy_block_result(
    *,
    specialist: str,
    summary: str,
    consulted_specialists: Sequence[str],
    policy: SupervisorRoutingPolicy = SUPERVISOR_ROUTING_POLICY,
) -> SpecialistResult:
    """Create a structured result when the supervisor routing policy blocks a call."""

    result = SpecialistResult(
        specialist=specialist,
        status="blocked",
        summary=summary,
        confidence="high",
        escalation_flags=[
            EscalationFlag(
                reason="Supervisor routing policy blocked an invalid specialist delegation.",
                priority="high",
            )
        ],
    )
    return apply_supervisor_routing_policy(
        result,
        consulted_specialists=consulted_specialists,
        policy=policy,
    )


def _render_tool_message(
    *,
    tool_call_id: str,
    tool_name: str,
    result: SpecialistResult,
    template: ToolMessage | None = None,
) -> ToolMessage:
    """Render a specialist result back into the tool-message surface."""

    payload = template.model_dump() if template is not None else {}
    payload.update(
        {
            "content": render_specialist_result(result),
            "tool_call_id": tool_call_id,
            "name": tool_name,
        }
    )
    return ToolMessage(**payload)


def _get_state_messages(state: Any) -> list[Any]:
    """Extract messages from either a dict-based or object-based agent state."""

    if isinstance(state, dict):
        return list(state.get("messages", []))
    return list(getattr(state, "messages", []) or [])


class SupervisorRoutingMiddleware(AgentMiddleware):
    """Enforce centralized supervisor routing rules around specialist tool calls."""

    def __init__(
        self,
        *,
        policy: SupervisorRoutingPolicy = SUPERVISOR_ROUTING_POLICY,
    ) -> None:
        self.policy = policy

    def wrap_tool_call(self, request, handler):
        tool_name = request.tool_call["name"]
        if tool_name not in AGENT_REGISTRY:
            return handler(request)

        prior_specialists = collect_consulted_specialists(_get_state_messages(request.state))
        blocked = self._maybe_block_call(
            tool_name=tool_name,
            tool_call_id=request.tool_call["id"],
            prior_specialists=prior_specialists,
        )
        if blocked is not None:
            return blocked

        result = handler(request)
        if not isinstance(result, ToolMessage):
            return result
        return self._apply_policy_to_tool_message(
            tool_name=tool_name,
            tool_call_id=request.tool_call["id"],
            tool_message=result,
            consulted_specialists=(*prior_specialists, tool_name),
        )

    async def awrap_tool_call(self, request, handler):
        tool_name = request.tool_call["name"]
        if tool_name not in AGENT_REGISTRY:
            return await handler(request)

        prior_specialists = collect_consulted_specialists(_get_state_messages(request.state))
        blocked = self._maybe_block_call(
            tool_name=tool_name,
            tool_call_id=request.tool_call["id"],
            prior_specialists=prior_specialists,
        )
        if blocked is not None:
            return blocked

        result = await handler(request)
        if not isinstance(result, ToolMessage):
            return result
        return self._apply_policy_to_tool_message(
            tool_name=tool_name,
            tool_call_id=request.tool_call["id"],
            tool_message=result,
            consulted_specialists=(*prior_specialists, tool_name),
        )

    def _maybe_block_call(
        self,
        *,
        tool_name: str,
        tool_call_id: str,
        prior_specialists: Sequence[str],
    ) -> ToolMessage | None:
        """Block invalid specialist calls before the tool executes."""

        if not self.policy.allow_repeat_specialist and tool_name in prior_specialists:
            result = _build_policy_block_result(
                specialist=tool_name,
                summary=(
                    f"Routing policy blocked a repeat consultation of {tool_name}. "
                    "The supervisor must not call the same specialist twice in one turn."
                ),
                consulted_specialists=prior_specialists,
                policy=self.policy,
            )
            return _render_tool_message(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                result=result,
            )

        if len(prior_specialists) >= self.policy.max_specialists_per_turn:
            result = _build_policy_block_result(
                specialist=tool_name,
                summary=(
                    "Routing policy blocked another specialist call because the per-turn "
                    "specialist budget is exhausted."
                ),
                consulted_specialists=prior_specialists,
                policy=self.policy,
            )
            return _render_tool_message(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                result=result,
            )

        return None

    def _apply_policy_to_tool_message(
        self,
        *,
        tool_name: str,
        tool_call_id: str,
        tool_message: ToolMessage,
        consulted_specialists: Sequence[str],
    ) -> ToolMessage:
        """Attach centralized routing guidance to a specialist tool result."""

        result = parse_specialist_result(tool_message.content)
        enriched = apply_supervisor_routing_policy(
            result,
            consulted_specialists=consulted_specialists,
            policy=self.policy,
        )
        return _render_tool_message(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            result=enriched,
            template=tool_message,
        )
