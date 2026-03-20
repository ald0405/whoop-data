"""Specialist delegation layer.

Standardizes internal specialist delegation on LangChain's subagents pattern:
one ``create_agent`` specialist per registry entry, wrapped as a
``StructuredTool`` for the public supervisor. Specialists stay stateless and
never hand off directly to one another. The wrapper boundary now accepts typed
handoffs, renders them deterministically into specialist context, and returns
validated ``SpecialistResult`` payloads serialized as JSON for the supervisor.
Specialist-side runtime guardrails also prevent runaway internal tool loops.
"""

from dataclasses import dataclass
import json
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import StructuredTool
from .specialist_contracts import (
    SpecialistHandoff,
    SpecialistResult,
    build_specialist_handoff_schema,
    parse_specialist_result,
    render_specialist_contract_prompt,
    render_specialist_result,
)

from .tools import TOOLS_BY_NAME
from .registry import AGENT_REGISTRY
from . import settings


@dataclass(frozen=True)
class SpecialistDelegationMechanism:
    """Chosen LangChain-aligned delegation mechanism for internal specialists."""

    agent_factory: str
    routing_surface: str
    specialist_wrapper: str
    context_model: str
    middleware_strategy: str
    graph_handoffs_allowed: bool


SPECIALIST_DELEGATION = SpecialistDelegationMechanism(
    agent_factory="create_agent",
    routing_surface="supervisor_calls_specialists_as_tools",
    specialist_wrapper="StructuredTool",
    context_model="stateless_context_isolation",
    middleware_strategy="specialist_tool_guard_middleware",
    graph_handoffs_allowed=False,
)


@dataclass(frozen=True)
class SpecialistContractStrategy:
    """Typed contract strategy wired through the current specialist runtime."""

    handoff_model: type[SpecialistHandoff]
    result_model: type[SpecialistResult]
    handoff_render_strategy: str
    result_render_strategy: str
    result_parse_strategy: str


SPECIALIST_CONTRACTS = SpecialistContractStrategy(
    handoff_model=SpecialistHandoff,
    result_model=SpecialistResult,
    handoff_render_strategy="sorted_json_message_block",
    result_render_strategy="pydantic_json_schema_prompt",
    result_parse_strategy="pydantic_model_validate_json_or_dict",
)


@dataclass(frozen=True)
class SpecialistRuntimeGuardrails:
    """Execution guardrails for internal specialist subagents."""

    max_tool_calls_per_run: int
    block_duplicate_tool_calls: bool
    recursion_limit: int


SPECIALIST_RUNTIME_GUARDRAILS = SpecialistRuntimeGuardrails(
    max_tool_calls_per_run=6,
    block_duplicate_tool_calls=True,
    recursion_limit=12,
)


def _get_specialist_tools(tool_names: list[str]) -> list:
    """Resolve tool names to tool instances from TOOLS_BY_NAME."""
    tools = []
    for name in tool_names:
        if name in TOOLS_BY_NAME:
            tools.append(TOOLS_BY_NAME[name])
    return tools


def _get_state_messages(state: Any) -> list[Any]:
    """Extract messages from a middleware state payload."""

    if isinstance(state, dict):
        return list(state.get("messages", []))
    return list(getattr(state, "messages", []) or [])


def _iter_executed_tool_calls(messages: list[Any]) -> list[dict[str, Any]]:
    """Return tool calls that have already produced tool messages in this run."""

    completed_ids = {
        message.tool_call_id
        for message in messages
        if isinstance(message, ToolMessage) and message.tool_call_id
    }
    executed_calls: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        for tool_call in getattr(message, "tool_calls", []) or []:
            if tool_call.get("id") in completed_ids:
                executed_calls.append(tool_call)
    return executed_calls


def _tool_call_signature(tool_call: dict[str, Any]) -> str:
    """Build a stable signature for a tool call name and its arguments."""

    rendered_args = json.dumps(tool_call.get("args", {}), sort_keys=True, default=str)
    return f"{tool_call.get('name')}:{rendered_args}"


class SpecialistToolGuardMiddleware(AgentMiddleware):
    """Prevent runaway fetch loops inside a specialist subagent run."""

    def __init__(
        self,
        *,
        specialist_name: str,
        guardrails: SpecialistRuntimeGuardrails = SPECIALIST_RUNTIME_GUARDRAILS,
    ) -> None:
        self.specialist_name = specialist_name
        self.guardrails = guardrails

    def _build_blocked_tool_message(
        self,
        *,
        request: ToolCallRequest,
        reason: str,
    ) -> ToolMessage:
        """Return an error tool message that nudges the specialist to finish."""

        return ToolMessage(
            content=(
                "Specialist runtime guard blocked this tool call. "
                f"{reason} Use the evidence you already retrieved, stop calling tools, "
                "and finish with the structured specialist result."
            ),
            tool_call_id=request.tool_call["id"],
            name=request.tool_call["name"],
            status="error",
        )

    def _maybe_block_tool_call(self, request: ToolCallRequest) -> ToolMessage | None:
        """Block duplicate or excessive tool calls before they execute."""

        messages = _get_state_messages(request.state)
        executed_calls = _iter_executed_tool_calls(messages)
        if len(executed_calls) >= self.guardrails.max_tool_calls_per_run:
            return self._build_blocked_tool_message(
                request=request,
                reason=(
                    f"{self.specialist_name} has already executed "
                    f"{len(executed_calls)} tool calls in this run."
                ),
            )

        if self.guardrails.block_duplicate_tool_calls:
            current_signature = _tool_call_signature(request.tool_call)
            prior_signatures = {_tool_call_signature(tool_call) for tool_call in executed_calls}
            if current_signature in prior_signatures:
                return self._build_blocked_tool_message(
                    request=request,
                    reason="This is a duplicate fetch with the same tool arguments.",
                )

        return None

    def wrap_tool_call(self, request, handler):
        blocked = self._maybe_block_tool_call(request)
        if blocked is not None:
            return blocked
        return handler(request)

    async def awrap_tool_call(self, request, handler):
        blocked = self._maybe_block_tool_call(request)
        if blocked is not None:
            return blocked
        return await handler(request)


def _build_specialist_system_prompt(base_prompt: str, tool_names: list[str]) -> str:
    """Append runtime-alignment instructions to a specialist system prompt."""

    tool_lines = "\n".join(f"- {name}" for name in tool_names) if tool_names else "- None"
    runtime_suffix = (
        "\n\n## Runtime contract\n"
        "You are an internal stateless specialist working for the supervisor.\n"
        "Use the structured handoff as your source of truth for intent, facts, constraints, "
        "safety notes, allowed tools, and required outputs.\n"
        "Only use the runtime tools listed below. Do not refer to memory, knowledge, transfer, "
        "handoff, or other tools unless they are explicitly listed.\n"
        "If critical information is missing, do not ask the user directly. Instead, return "
        "requires_clarification=true with clarification_needs explaining exactly what the "
        "supervisor should ask.\n"
        "Return supervisor-facing structured content, not a direct user reply. Put your main "
        "takeaway in summary, key considerations in findings, concrete next steps in "
        "recommendations, routing hints in suggested_next_specialist, and any domain-specific "
        "structured content in specialist_output.\n"
        "Surface safety concerns in safety_flags and escalation_flags when needed.\n"
        "Available runtime tools:\n"
        f"{tool_lines}"
    )
    return (
        f"{base_prompt.strip()}{runtime_suffix}" if base_prompt.strip() else runtime_suffix.strip()
    )


def _extract_final_response(result: dict) -> str:
    """Extract the final text response from a create_agent invocation result."""
    messages = result.get("messages", [])
    # Walk backwards to find the last AIMessage without tool calls
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            return msg.content if isinstance(msg.content, str) else msg.text
    # Fallback: return last message content
    if messages:
        last = messages[-1]
        return last.content if hasattr(last, "content") else str(last)
    return "No response from specialist."


def _extract_structured_result(result: dict) -> SpecialistResult:
    """Extract the validated structured result from a specialist invocation."""

    structured = result.get("structured_response")
    if structured is not None:
        return parse_contract_result(structured)
    return parse_contract_result(_extract_final_response(result))


def render_contract_prompt(handoff: SpecialistHandoff) -> str:
    """Render a typed handoff into the current text-based specialist boundary."""

    return render_specialist_contract_prompt(handoff)


def parse_contract_result(
    payload: SpecialistResult | dict[str, Any] | str,
) -> SpecialistResult:
    """Parse a typed specialist result from a future structured wrapper."""

    return parse_specialist_result(payload)


def build_specialist_delegation_tools(
    registry: dict[str, dict] | None = None,
    model_override: str | None = None,
) -> list:
    """Build the standardized specialist delegation tools from the registry.

    Each registry entry becomes a compiled ``create_agent`` instance wrapped in
    a ``StructuredTool`` that the supervisor can call. This keeps delegation
    aligned with LangChain's subagents pattern while preserving an
    application-owned wrapper boundary that can move from ``query: str`` to
    ``SpecialistHandoff`` / ``SpecialistResult`` without changing the
    supervisor's higher-level routing model.

    Args:
        registry: Agent registry dict. Defaults to AGENT_REGISTRY.
        model_override: Optional model string to use for all specialists.

    Returns:
        List of tool instances for the supervisor.
    """
    if registry is None:
        registry = AGENT_REGISTRY

    specialist_tools = []

    for agent_name, config in registry.items():
        domain_tools = _get_specialist_tools(config["tools"])
        system_prompt = config.get("system_prompt", "")
        description = config["description"]
        handoff_schema = build_specialist_handoff_schema(agent_name)
        composed_system_prompt = _build_specialist_system_prompt(
            str(system_prompt),
            list(config["tools"]),
        )

        # Determine model for this specialist
        model = model_override or settings.SPECIALIST_CONFIG.get(agent_name, {}).get(
            "model", settings.SPECIALIST_MODEL
        )

        # Create the subagent
        agent = create_agent(
            model=model,
            tools=domain_tools,
            system_prompt=composed_system_prompt,
            middleware=[SpecialistToolGuardMiddleware(specialist_name=agent_name)],
            response_format=ToolStrategy(SpecialistResult),
            name=agent_name,
        )

        # Wrap as a tool — closure captures agent_name, agent, description
        def _make_tool(name: str, desc: str, compiled_agent, args_schema):
            async def specialist_fn(**handoff_payload) -> str:
                """Delegate a typed handoff to a specialist subagent."""

                handoff = args_schema.model_validate({**handoff_payload, "specialist": name})
                result = await compiled_agent.ainvoke(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": render_contract_prompt(handoff),
                            }
                        ]
                    },
                    config={"recursion_limit": SPECIALIST_RUNTIME_GUARDRAILS.recursion_limit},
                )
                return render_specialist_result(_extract_structured_result(result))

            return StructuredTool.from_function(
                coroutine=specialist_fn,
                name=name,
                description=desc,
                args_schema=args_schema,
            )

        specialist_tools.append(_make_tool(agent_name, description, agent, handoff_schema))

    return specialist_tools


def build_specialist_tools(
    registry: dict[str, dict] | None = None,
    model_override: str | None = None,
) -> list:
    """Backward-compatible alias for the standardized delegation builder."""

    return build_specialist_delegation_tools(
        registry=registry,
        model_override=model_override,
    )
