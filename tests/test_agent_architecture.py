"""Tests for the new agent architecture.

Verifies registry, tool grouping, specialist factory, graph build, and prompts
without requiring the API server or LLM calls.
"""

import asyncio
import json
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from langchain.agents.middleware import ToolCallRequest
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import ValidationError
import pytest


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    """Verify registry entries are well-formed."""

    def test_registry_has_entries(self):
        from whoopdata.agent.registry import AGENT_REGISTRY

        assert len(AGENT_REGISTRY) >= 5

    def test_required_keys_present(self):
        from whoopdata.agent.registry import AGENT_REGISTRY

        required_keys = {"name", "description", "system_prompt", "boundary", "tools"}
        for agent_name, config in AGENT_REGISTRY.items():
            missing = required_keys - set(config.keys())
            assert not missing, f"{agent_name} missing keys: {missing}"

    def test_boundary_contracts_are_present(self):
        from whoopdata.agent.registry import AGENT_REGISTRY, SpecialistBoundary

        for agent_name, config in AGENT_REGISTRY.items():
            boundary = config["boundary"]
            assert isinstance(
                boundary, SpecialistBoundary
            ), f"{agent_name} boundary should be a SpecialistBoundary"
            assert len(boundary.delegate_when) >= 1, f"{agent_name} boundary missing routing cues"
            assert len(boundary.owns) >= 1, f"{agent_name} boundary missing owned scope"
            assert len(boundary.excludes) >= 1, f"{agent_name} boundary missing exclusions"

    def test_name_matches_key(self):
        from whoopdata.agent.registry import AGENT_REGISTRY

        for key, config in AGENT_REGISTRY.items():
            assert config["name"] == key, f"Registry key '{key}' != name '{config['name']}'"

    def test_descriptions_are_non_empty(self):
        from whoopdata.agent.registry import AGENT_REGISTRY

        for agent_name, config in AGENT_REGISTRY.items():
            assert len(config["description"]) > 20, f"{agent_name} description too short"

    def test_system_prompts_are_non_empty(self):
        from whoopdata.agent.registry import AGENT_REGISTRY

        for agent_name, config in AGENT_REGISTRY.items():
            assert (
                len(config["system_prompt"]) > 10
            ), f"{agent_name} system_prompt is empty or too short"

    def test_tool_lists_are_non_empty(self):
        from whoopdata.agent.registry import AGENT_REGISTRY

        for agent_name, config in AGENT_REGISTRY.items():
            assert len(config["tools"]) >= 1, f"{agent_name} has no tools"

    def test_all_tool_names_resolve(self):
        """Every tool name in registry must exist in TOOLS_BY_NAME."""
        from whoopdata.agent.registry import AGENT_REGISTRY
        from whoopdata.agent.tools import TOOLS_BY_NAME

        for agent_name, config in AGENT_REGISTRY.items():
            for tool_name in config["tools"]:
                assert tool_name in TOOLS_BY_NAME, (
                    f"{agent_name} references unknown tool '{tool_name}'. "
                    f"Available: {sorted(TOOLS_BY_NAME.keys())}"
                )

    def test_health_data_no_longer_owns_protein_recommendation(self):
        from whoopdata.agent.registry import AGENT_REGISTRY

        assert "get_protein_recommendation" not in AGENT_REGISTRY["health_data"]["tools"]

    def test_specialist_architecture_keeps_single_public_supervisor(self):
        from whoopdata.agent.registry import SPECIALIST_ARCHITECTURE

        assert SPECIALIST_ARCHITECTURE.public_interface == "health_coach"
        assert SPECIALIST_ARCHITECTURE.public_interface_owner == "single user-facing supervisor"
        assert SPECIALIST_ARCHITECTURE.final_response_owner == "supervisor"

    def test_deterministic_workflows_stay_outside_specialist_delegation(self):
        from whoopdata.agent.registry import SPECIALIST_ARCHITECTURE

        workflow_names = {
            workflow.name for workflow in SPECIALIST_ARCHITECTURE.deterministic_workflows
        }
        assert workflow_names == {
            "daily_plan",
            "scenario_prediction",
            "scenario_comparison",
            "weekly_coaching_report",
        }


# ---------------------------------------------------------------------------
# Tool grouping tests
# ---------------------------------------------------------------------------


class TestToolGrouping:
    """Verify tool assignment across specialists."""

    def test_no_tool_in_multiple_data_specialists(self):
        """Data-retrieval specialists (health_data, analytics, environment) should not
        share tools. Exercise/behaviour_change may share some data tools by design."""
        from whoopdata.agent.registry import AGENT_REGISTRY

        data_specialists = ["health_data", "analytics", "environment"]
        seen: dict[str, str] = {}
        for name in data_specialists:
            if name not in AGENT_REGISTRY:
                continue
            for tool_name in AGENT_REGISTRY[name]["tools"]:
                if tool_name in seen:
                    pytest.fail(f"Tool '{tool_name}' in both '{seen[tool_name]}' and '{name}'")
                seen[tool_name] = name

    def test_all_api_tools_assigned(self):
        """All tools in AVAILABLE_TOOLS (except python_repl) should appear in at
        least one registry entry."""
        from whoopdata.agent.registry import AGENT_REGISTRY
        from whoopdata.agent.tools import AVAILABLE_TOOLS

        registry_tools: set[str] = set()
        for config in AGENT_REGISTRY.values():
            registry_tools.update(config["tools"])

        for tool in AVAILABLE_TOOLS:
            name = getattr(tool, "name", None)
            if name and name != "python_interpreter":
                assert name in registry_tools, f"Tool '{name}' not assigned to any specialist"


# ---------------------------------------------------------------------------
# Tools lookup tests
# ---------------------------------------------------------------------------


class TestToolsLookup:
    """Verify TOOLS_BY_NAME mapping."""

    def test_tools_by_name_populated(self):
        from whoopdata.agent.tools import TOOLS_BY_NAME

        assert len(TOOLS_BY_NAME) > 0

    def test_tools_by_name_matches_available_tools(self):
        from whoopdata.agent.tools import TOOLS_BY_NAME, AVAILABLE_TOOLS

        assert len(TOOLS_BY_NAME) == len(AVAILABLE_TOOLS)

    def test_python_repl_in_tools_by_name(self):
        from whoopdata.agent.tools import TOOLS_BY_NAME

        assert "python_interpreter" in TOOLS_BY_NAME


# ---------------------------------------------------------------------------
# Specialist factory tests
# ---------------------------------------------------------------------------


class TestSpecialistContracts:
    """Validate the typed specialist handoff/result contracts."""

    def test_handoff_supports_shared_and_extension_fields(self):
        from whoopdata.agent.specialist_contracts import SpecialistFact, SpecialistHandoff

        handoff = SpecialistHandoff(
            specialist="analytics",
            user_intent="Understand the recent recovery dip.",
            task_objective="Explain likely drivers using the analytics toolset.",
            relevant_facts=[
                SpecialistFact(
                    name="recent_recovery",
                    value="48% on 2026-03-14",
                    source="WHOOP",
                )
            ],
            allowed_tools=["analyze_recovery_factors"],
            specialist_context={"comparison_window": "30d"},
        )

        assert handoff.specialist_context["comparison_window"] == "30d"
        assert handoff.relevant_facts[0].source == "WHOOP"

    def test_render_specialist_contract_prompt_contains_handoff_and_schema(self):
        from whoopdata.agent.specialist_contracts import (
            SpecialistHandoff,
            render_specialist_contract_prompt,
        )

        prompt = render_specialist_contract_prompt(
            SpecialistHandoff(
                specialist="analytics",
                user_intent="Explain the recovery trend.",
                task_objective="Return the main analytical drivers for the latest dip.",
                allowed_tools=["analyze_recovery_factors"],
            )
        )

        assert "Application-owned specialist handoff" in prompt
        assert '"specialist": "analytics"' in prompt
        assert "Return your final answer as JSON" in prompt

    def test_render_specialist_result_returns_sorted_json(self):
        from whoopdata.agent.specialist_contracts import (
            SpecialistResult,
            render_specialist_result,
        )

        payload = render_specialist_result(
            SpecialistResult(
                specialist="analytics",
                summary="Recovery decline is most consistent with short sleep.",
            )
        )

        assert '"specialist": "analytics"' in payload
        assert '"summary": "Recovery decline is most consistent with short sleep."' in payload

    def test_parse_specialist_result_from_json_string(self):
        from whoopdata.agent.specialist_contracts import parse_specialist_result

        payload = json.dumps(
            {
                "specialist": "analytics",
                "summary": "Recovery decline looks linked to sleep compression.",
                "findings": [
                    {
                        "summary": "Short sleep is the strongest recent driver.",
                        "priority": "high",
                    }
                ],
                "recommendations": [
                    {
                        "action": "Protect an 8-hour sleep window for the next 3 nights.",
                        "priority": "high",
                    }
                ],
                "confidence": "high",
            }
        )

        result = parse_specialist_result(payload)

        assert result.specialist == "analytics"
        assert result.confidence == "high"
        assert result.findings[0].priority == "high"

    def test_specialist_result_requires_questions_when_clarification_is_requested(self):
        from whoopdata.agent.specialist_contracts import SpecialistResult

        with pytest.raises(ValidationError):
            SpecialistResult(
                specialist="analytics",
                status="needs_clarification",
                summary="Need more info before I can finish the analysis.",
                requires_clarification=True,
            )

    def test_specialist_result_rejects_self_suggestion(self):
        from whoopdata.agent.specialist_contracts import (
            SpecialistResult,
            SuggestedNextSpecialist,
        )

        with pytest.raises(ValidationError):
            SpecialistResult(
                specialist="analytics",
                summary="Analysis complete.",
                suggested_next_specialist=SuggestedNextSpecialist(
                    specialist="analytics",
                    reason="This should be a different specialist if present.",
                ),
            )


class TestSpecialistFactory:
    """Test build_specialist_tools with mocked create_agent."""

    def test_specialist_delegation_standard_is_explicit(self):
        from whoopdata.agent.specialists import SPECIALIST_DELEGATION

        assert SPECIALIST_DELEGATION.agent_factory == "create_agent"
        assert SPECIALIST_DELEGATION.specialist_wrapper == "StructuredTool"
        assert SPECIALIST_DELEGATION.graph_handoffs_allowed is False
        assert SPECIALIST_DELEGATION.middleware_strategy == "specialist_tool_guard_middleware"

    def test_specialist_contract_strategy_is_explicit(self):
        from whoopdata.agent.specialist_contracts import SpecialistHandoff, SpecialistResult
        from whoopdata.agent.specialists import SPECIALIST_CONTRACTS

        assert SPECIALIST_CONTRACTS.handoff_model is SpecialistHandoff
        assert SPECIALIST_CONTRACTS.result_model is SpecialistResult
        assert SPECIALIST_CONTRACTS.handoff_render_strategy == "sorted_json_message_block"
        assert SPECIALIST_CONTRACTS.result_render_strategy == "pydantic_json_schema_prompt"

    def test_specialist_runtime_guardrails_are_explicit(self):
        from whoopdata.agent.specialists import SPECIALIST_RUNTIME_GUARDRAILS

        assert SPECIALIST_RUNTIME_GUARDRAILS.max_tool_calls_per_run == 6
        assert SPECIALIST_RUNTIME_GUARDRAILS.block_duplicate_tool_calls is True
        assert SPECIALIST_RUNTIME_GUARDRAILS.recursion_limit == 12

    @patch("whoopdata.agent.specialists.create_agent")
    def test_build_specialist_delegation_tools_returns_one_tool_per_registry_entry(
        self, mock_create_agent
    ):
        mock_create_agent.return_value = MagicMock()

        from whoopdata.agent.specialists import build_specialist_delegation_tools
        from whoopdata.agent.registry import AGENT_REGISTRY

        tools = build_specialist_delegation_tools()
        assert len(tools) == len(AGENT_REGISTRY)

    @patch("whoopdata.agent.specialists.create_agent")
    def test_specialist_tools_expose_typed_handoff_fields(self, mock_create_agent):
        mock_create_agent.return_value = MagicMock()

        from whoopdata.agent.specialists import build_specialist_delegation_tools

        tool = next(t for t in build_specialist_delegation_tools() if t.name == "analytics")
        schema = tool.get_input_schema().model_json_schema()

        assert "user_intent" in schema["properties"]
        assert "task_objective" in schema["properties"]
        assert "allowed_tools" in schema["properties"]

    @patch("whoopdata.agent.specialists.create_agent")
    def test_specialist_tools_return_structured_result_json(self, mock_create_agent):
        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={
                "structured_response": {
                    "specialist": "analytics",
                    "summary": "Recovery decline is primarily sleep-driven.",
                    "confidence": "high",
                },
                "messages": [],
            }
        )
        mock_create_agent.return_value = mock_agent

        from whoopdata.agent.specialists import build_specialist_delegation_tools

        tool = next(t for t in build_specialist_delegation_tools() if t.name == "analytics")
        result = asyncio.run(
            tool.ainvoke(
                {
                    "user_intent": "Understand the recovery dip.",
                    "task_objective": "Explain the main analytical drivers.",
                }
            )
        )

        assert '"specialist": "analytics"' in result
        assert '"confidence": "high"' in result
        mock_agent.ainvoke.assert_awaited_once()
        await_args = mock_agent.ainvoke.await_args
        assert await_args.kwargs["config"]["recursion_limit"] == 12

    @patch("whoopdata.agent.specialists.create_agent")
    def test_returns_tools_for_each_registry_entry(self, mock_create_agent):
        """Should return one tool per registry entry."""
        mock_create_agent.return_value = MagicMock()

        from whoopdata.agent.specialists import build_specialist_tools
        from whoopdata.agent.registry import AGENT_REGISTRY

        tools = build_specialist_tools()
        assert len(tools) == len(AGENT_REGISTRY)

    @patch("whoopdata.agent.specialists.create_agent")
    def test_tools_are_base_tool_instances(self, mock_create_agent):
        mock_create_agent.return_value = MagicMock()

        from whoopdata.agent.specialists import build_specialist_tools

        tools = build_specialist_tools()
        for t in tools:
            assert isinstance(t, BaseTool), f"{t} is not a BaseTool"

    @patch("whoopdata.agent.specialists.create_agent")
    def test_tool_names_match_registry(self, mock_create_agent):
        mock_create_agent.return_value = MagicMock()

        from whoopdata.agent.specialists import build_specialist_tools
        from whoopdata.agent.registry import AGENT_REGISTRY

        tools = build_specialist_tools()
        tool_names = {t.name for t in tools}
        registry_names = set(AGENT_REGISTRY.keys())
        assert tool_names == registry_names

    @patch("whoopdata.agent.specialists.create_agent")
    def test_tool_descriptions_non_empty(self, mock_create_agent):
        mock_create_agent.return_value = MagicMock()

        from whoopdata.agent.specialists import build_specialist_tools

        tools = build_specialist_tools()
        for t in tools:
            assert len(t.description) > 20, f"Tool '{t.name}' has short description"

    @patch("whoopdata.agent.specialists.create_agent")
    def test_create_agent_called_for_each_specialist(self, mock_create_agent):
        mock_create_agent.return_value = MagicMock()

        from whoopdata.agent.specialists import build_specialist_tools
        from whoopdata.agent.registry import AGENT_REGISTRY

        build_specialist_tools()
        assert mock_create_agent.call_count == len(AGENT_REGISTRY)

    @patch("whoopdata.agent.specialists.create_agent")
    def test_create_agent_receives_runtime_aligned_system_prompt(self, mock_create_agent):
        mock_create_agent.return_value = MagicMock()

        from whoopdata.agent.specialists import build_specialist_delegation_tools

        build_specialist_delegation_tools()

        prompts_by_specialist = {
            call.kwargs["name"]: call.kwargs["system_prompt"]
            for call in mock_create_agent.call_args_list
        }

        exercise_prompt = prompts_by_specialist["exercise"]
        assert "## Runtime contract" in exercise_prompt
        assert "Use the structured handoff as your source of truth" in exercise_prompt
        assert "Available runtime tools:" in exercise_prompt
        assert "- get_weight_data" in exercise_prompt
        assert "- get_workout_data" in exercise_prompt
        assert "- get_recovery_data" in exercise_prompt
        assert "requires_clarification=true" in exercise_prompt

    @patch("whoopdata.agent.specialists.create_agent")
    def test_create_agent_receives_specialist_tool_guard_middleware(self, mock_create_agent):
        mock_create_agent.return_value = MagicMock()

        from whoopdata.agent.specialists import (
            SpecialistToolGuardMiddleware,
            build_specialist_delegation_tools,
        )

        build_specialist_delegation_tools()

        analytics_call = next(
            call for call in mock_create_agent.call_args_list if call.kwargs["name"] == "analytics"
        )
        middleware = analytics_call.kwargs["middleware"]
        assert len(middleware) == 1
        assert isinstance(middleware[0], SpecialistToolGuardMiddleware)


class TestSpecialistRuntimeGuardrails:
    """Test middleware that prevents runaway specialist tool loops."""

    def test_tool_call_signature_is_stable_for_name_and_args(self):
        from whoopdata.agent.specialists import _tool_call_signature

        signature = _tool_call_signature(
            {"name": "get_recovery_data", "args": {"latest": True, "limit": 1}}
        )

        assert signature == 'get_recovery_data:{"latest": true, "limit": 1}'

    def test_iter_executed_tool_calls_only_returns_completed_calls(self):
        from whoopdata.agent.specialists import _iter_executed_tool_calls

        executed = _iter_executed_tool_calls(
            [
                AIMessage(
                    content="tool step",
                    tool_calls=[
                        {"name": "get_weight_data", "args": {"latest": True}, "id": "call-1"},
                        {"name": "get_workout_data", "args": {"latest": True}, "id": "call-2"},
                    ],
                ),
                ToolMessage(content="ok", tool_call_id="call-1", name="get_weight_data"),
            ]
        )

        assert [call["name"] for call in executed] == ["get_weight_data"]

    def test_specialist_tool_guard_blocks_duplicate_tool_calls(self):
        from whoopdata.agent.specialists import SpecialistToolGuardMiddleware

        middleware = SpecialistToolGuardMiddleware(specialist_name="exercise")
        request = ToolCallRequest(
            tool_call={
                "name": "get_recovery_data",
                "args": {"latest": True},
                "id": "call-2",
            },
            tool=MagicMock(),
            state={
                "messages": [
                    AIMessage(
                        content="Fetch the latest recovery.",
                        tool_calls=[
                            {
                                "name": "get_recovery_data",
                                "args": {"latest": True},
                                "id": "call-1",
                            }
                        ],
                    ),
                    ToolMessage(
                        content="done",
                        tool_call_id="call-1",
                        name="get_recovery_data",
                    ),
                ]
            },
            runtime=None,
        )
        handler = AsyncMock()

        response = asyncio.run(middleware.awrap_tool_call(request, handler))

        assert response.status == "error"
        assert "duplicate fetch with the same tool arguments" in response.content.lower()
        handler.assert_not_awaited()

    def test_specialist_tool_guard_blocks_after_max_tool_calls(self):
        from whoopdata.agent.specialists import SpecialistToolGuardMiddleware

        middleware = SpecialistToolGuardMiddleware(specialist_name="exercise")
        prior_messages: list = []
        for index in range(6):
            call_id = f"call-{index}"
            prior_messages.append(
                AIMessage(
                    content="tool step",
                    tool_calls=[
                        {
                            "name": "get_workout_data",
                            "args": {"window": index},
                            "id": call_id,
                        }
                    ],
                )
            )
            prior_messages.append(
                ToolMessage(content="done", tool_call_id=call_id, name="get_workout_data")
            )

        request = ToolCallRequest(
            tool_call={
                "name": "get_workout_data",
                "args": {"window": 99},
                "id": "call-over",
            },
            tool=MagicMock(),
            state={"messages": prior_messages},
            runtime=None,
        )
        handler = AsyncMock()

        response = asyncio.run(middleware.awrap_tool_call(request, handler))

        assert response.status == "error"
        assert "already executed 6 tool calls in this run" in response.content.lower()
        handler.assert_not_awaited()


# ---------------------------------------------------------------------------
# Supervisor routing tests
# ---------------------------------------------------------------------------


class TestSupervisorRouting:
    """Test the centralized supervisor routing policy and middleware."""

    def test_supervisor_routing_policy_is_explicit(self):
        from whoopdata.agent.routing import SUPERVISOR_ROUTING_POLICY

        assert SUPERVISOR_ROUTING_POLICY.final_response_owner == "supervisor"
        assert SUPERVISOR_ROUTING_POLICY.direct_specialist_handoffs_allowed is False
        assert SUPERVISOR_ROUTING_POLICY.max_specialists_per_turn == 2
        assert SUPERVISOR_ROUTING_POLICY.allow_repeat_specialist is False

    def test_collect_consulted_specialists_reads_prior_specialist_tool_messages(self):
        from whoopdata.agent.routing import collect_consulted_specialists

        consulted = collect_consulted_specialists(
            [
                ToolMessage(content="{}", tool_call_id="1", name="analytics"),
                ToolMessage(content="{}", tool_call_id="2", name="python_interpreter"),
                ToolMessage(content="{}", tool_call_id="3", name="exercise"),
            ]
        )

        assert consulted == ("analytics", "exercise")

    def test_collect_consulted_specialists_only_counts_the_latest_turn(self):
        from whoopdata.agent.routing import collect_consulted_specialists

        consulted = collect_consulted_specialists(
            [
                ToolMessage(content="{}", tool_call_id="1", name="analytics"),
                HumanMessage(content="What should I do this week?"),
                ToolMessage(content="{}", tool_call_id="2", name="exercise"),
            ]
        )

        assert consulted == ("exercise",)

    def test_apply_supervisor_routing_policy_prioritizes_clarification(self):
        from whoopdata.agent.routing import apply_supervisor_routing_policy
        from whoopdata.agent.specialist_contracts import ClarificationNeed, SpecialistResult

        result = apply_supervisor_routing_policy(
            SpecialistResult(
                specialist="nutrition",
                status="needs_clarification",
                summary="Need the user's activity level before calculating protein guidance.",
                requires_clarification=True,
                clarification_needs=[
                    ClarificationNeed(
                        question="Which activity level fits you best: normal, endurance training, or resistance/strength training?",
                        reason="Protein targets depend on training type.",
                    )
                ],
            ),
            consulted_specialists=["nutrition"],
        )

        assert "Stop delegating now and ask only the clarification questions" in (
            result.supervisor_guidance or ""
        )

    def test_apply_supervisor_routing_policy_allows_one_follow_on_specialist(self):
        from whoopdata.agent.routing import apply_supervisor_routing_policy
        from whoopdata.agent.specialist_contracts import (
            SpecialistResult,
            SuggestedNextSpecialist,
        )

        result = apply_supervisor_routing_policy(
            SpecialistResult(
                specialist="exercise",
                summary="A minimal programme is ready, but adherence support would help.",
                suggested_next_specialist=SuggestedNextSpecialist(
                    specialist="behaviour_change",
                    reason="The user needs help sticking to the plan.",
                ),
            ),
            consulted_specialists=["exercise"],
        )

        assert "You may consult behaviour_change next only if it materially helps" in (
            result.supervisor_guidance or ""
        )

    def test_apply_supervisor_routing_policy_blocks_follow_on_when_budget_is_spent(self):
        from whoopdata.agent.routing import apply_supervisor_routing_policy
        from whoopdata.agent.specialist_contracts import (
            SpecialistResult,
            SuggestedNextSpecialist,
        )

        result = apply_supervisor_routing_policy(
            SpecialistResult(
                specialist="analytics",
                summary="The recovery dip is real and behaviour support may help adherence.",
                suggested_next_specialist=SuggestedNextSpecialist(
                    specialist="behaviour_change",
                    reason="There are clear habit barriers.",
                ),
            ),
            consulted_specialists=["health_data", "analytics"],
        )

        assert (
            "Do not call another specialist because the per-turn specialist budget is exhausted"
            in (result.supervisor_guidance or "")
        )

    def test_routing_middleware_blocks_repeat_specialist_calls(self):
        from whoopdata.agent.routing import SupervisorRoutingMiddleware
        from whoopdata.agent.specialist_contracts import parse_specialist_result

        middleware = SupervisorRoutingMiddleware()
        request = ToolCallRequest(
            tool_call={"name": "analytics", "args": {}, "id": "call-1"},
            tool=MagicMock(),
            state={
                "messages": [ToolMessage(content="{}", tool_call_id="previous", name="analytics")]
            },
            runtime=None,
        )
        handler = AsyncMock()

        response = asyncio.run(middleware.awrap_tool_call(request, handler))
        result = parse_specialist_result(response.content)

        assert result.status == "blocked"
        assert "repeat consultation of analytics" in result.summary.lower()
        handler.assert_not_awaited()

    def test_routing_middleware_enriches_specialist_tool_results(self):
        from whoopdata.agent.routing import SupervisorRoutingMiddleware
        from whoopdata.agent.specialist_contracts import (
            SpecialistResult,
            SuggestedNextSpecialist,
            parse_specialist_result,
            render_specialist_result,
        )

        middleware = SupervisorRoutingMiddleware()
        request = ToolCallRequest(
            tool_call={"name": "exercise", "args": {}, "id": "call-2"},
            tool=MagicMock(),
            state={"messages": []},
            runtime=None,
        )
        handler = AsyncMock(
            return_value=ToolMessage(
                content=render_specialist_result(
                    SpecialistResult(
                        specialist="exercise",
                        summary="The user needs a simple training plan plus adherence support.",
                        suggested_next_specialist=SuggestedNextSpecialist(
                            specialist="behaviour_change",
                            reason="Consistency is the limiting factor.",
                        ),
                    )
                ),
                tool_call_id="call-2",
                name="exercise",
            )
        )

        response = asyncio.run(middleware.awrap_tool_call(request, handler))
        result = parse_specialist_result(response.content)

        assert "consult behaviour_change next" in (result.supervisor_guidance or "").lower()
        handler.assert_awaited_once()


# ---------------------------------------------------------------------------
# Extract final response tests
# ---------------------------------------------------------------------------


class TestExtractFinalResponse:
    """Test _extract_final_response helper."""

    def test_extracts_last_ai_message(self):
        from whoopdata.agent.specialists import _extract_final_response

        result = {
            "messages": [
                AIMessage(
                    content="thinking...", tool_calls=[{"name": "foo", "args": {}, "id": "1"}]
                ),
                AIMessage(content="Here is the answer."),
            ]
        }
        assert _extract_final_response(result) == "Here is the answer."

    def test_returns_fallback_for_empty_messages(self):
        from whoopdata.agent.specialists import _extract_final_response

        result = {"messages": []}
        assert "No response" in _extract_final_response(result)


# ---------------------------------------------------------------------------
# Prompt tests
# ---------------------------------------------------------------------------


class TestPrompts:
    """Verify prompts exist and are well-formed."""

    @staticmethod
    def _read_prompt(filename: str) -> str:
        path = Path(__file__).parent.parent / "data" / "prompts" / "agents" / filename
        assert path.exists(), f"Prompt not found at {path}"
        return path.read_text()

    def test_supervisor_prompt_exists(self):
        from whoopdata.agent.prompts import SUPERVISOR_SYSTEM_PROMPT

        assert len(SUPERVISOR_SYSTEM_PROMPT) > 100

    def test_supervisor_prompt_mentions_specialists(self):
        from whoopdata.agent.prompts import SUPERVISOR_SYSTEM_PROMPT

        assert "health data" in SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "analytics" in SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "environment" in SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "nutrition" in SUPERVISOR_SYSTEM_PROMPT.lower()

    def test_supervisor_prompt_mentions_structured_specialist_contracts(self):
        from whoopdata.agent.prompts import SUPERVISOR_SYSTEM_PROMPT

        assert "structured handoff" in SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "json" in SUPERVISOR_SYSTEM_PROMPT.lower()

    def test_supervisor_prompt_mentions_centralized_routing_rules(self):
        from whoopdata.agent.prompts import SUPERVISOR_SYSTEM_PROMPT

        lowered = SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "supervisor_guidance" in lowered
        assert "never call the same specialist twice in one turn" in lowered
        assert "only chain a second specialist" in lowered

    def test_supervisor_prompt_mentions_bluf_and_progressive_disclosure(self):
        from whoopdata.agent.prompts import SUPERVISOR_SYSTEM_PROMPT

        lowered = SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "bluf" in lowered
        assert "bottom line up front" in lowered
        assert "progressive disclosure" in lowered
        assert "short paragraphs" in lowered
        assert "well-formatted markdown" in lowered
        assert "start with the answer" in lowered

    def test_exercise_prompt_file_exists(self):
        content = self._read_prompt("exercise_sub_agent.md")
        assert len(content) > 100

    def test_behaviour_change_prompt_file_exists(self):
        content = self._read_prompt("behaviour_change_sub_agent.md")
        assert len(content) > 100

    def test_exercise_prompt_matches_runtime_tools_and_contract(self):
        content = self._read_prompt("exercise_sub_agent.md")
        lowered = content.lower()

        assert "get_weight_data" in content
        assert "get_workout_data" in content
        assert "get_recovery_data" in content
        assert "structured handoff" in lowered
        assert "structured specialist result contract" in lowered
        assert "clarification need" in lowered

        for stale_reference in [
            "analyse_weight",
            "get_knowledge",
            "search_memory",
            "get_daily_protein_target",
            "transfer_back_to_supervisor",
            "previous messages",
            "provide plain text",
        ]:
            assert stale_reference not in lowered

    def test_behaviour_change_prompt_matches_runtime_tools_and_contract(self):
        content = self._read_prompt("behaviour_change_sub_agent.md")
        lowered = content.lower()

        assert "get_recovery_data" in content
        assert "get_weight_data" in content
        assert "get_workout_data" in content
        assert "structured handoff" in lowered
        assert "structured specialist result contract" in lowered
        assert "clarification need" in lowered

        for stale_reference in [
            "get_knowledge",
            "search_memory",
            "get_daily_protein_target",
            "transfer_back_to_supervisor",
            "review conversation history",
            "provide plain text",
            "ask conversationally",
        ]:
            assert stale_reference not in lowered

    def test_nutrition_prompt_mentions_clarification_contract(self):
        from whoopdata.agent.registry import AGENT_REGISTRY

        prompt = AGENT_REGISTRY["nutrition"]["system_prompt"].lower()

        assert "return a clarification need" in prompt
        assert "structured result fields" in prompt


# ---------------------------------------------------------------------------
# Graph build tests
# ---------------------------------------------------------------------------


class TestGraphBuild:
    """Test that graph builds and compiles without errors."""

    @patch("whoopdata.agent.specialists.create_agent")
    @patch("whoopdata.agent.graph.create_agent")
    def test_build_graph_returns_compiled_graph(self, mock_graph_create, mock_spec_create):
        """build_graph() should return a compiled graph object."""
        # Mock specialist create_agent
        mock_spec_create.return_value = MagicMock()

        # Mock supervisor create_agent to return a mock compiled graph
        mock_compiled = MagicMock()
        mock_graph_create.return_value = mock_compiled

        from whoopdata.agent.graph import build_graph

        graph = build_graph()
        assert graph is not None
        mock_graph_create.assert_called_once()

    @patch("whoopdata.agent.specialists.create_agent")
    @patch("whoopdata.agent.graph.create_agent")
    def test_build_graph_supervisor_gets_specialist_tools_plus_direct_tools(
        self, mock_graph_create, mock_spec_create
    ):
        """Supervisor should receive specialist tools plus direct supervisor tools."""
        mock_spec_create.return_value = MagicMock()
        mock_graph_create.return_value = MagicMock()

        from whoopdata.agent.graph import build_graph
        from whoopdata.agent.registry import AGENT_REGISTRY

        build_graph()

        call_kwargs = mock_graph_create.call_args
        tools = call_kwargs.kwargs.get("tools") or call_kwargs[1].get("tools")
        if tools is None:
            # Positional args
            tools = call_kwargs[0][1] if len(call_kwargs[0]) > 1 else []

        # Should have N specialist tools + python_repl
        expected_count = len(AGENT_REGISTRY) + 1
        assert len(tools) == expected_count, f"Expected {expected_count} tools, got {len(tools)}"

    @patch("whoopdata.agent.specialists.create_agent")
    @patch("whoopdata.agent.graph.create_agent")
    def test_build_graph_adds_supervisor_routing_middleware(
        self, mock_graph_create, mock_spec_create
    ):
        mock_spec_create.return_value = MagicMock()
        mock_graph_create.return_value = MagicMock()

        from whoopdata.agent.graph import build_graph
        from whoopdata.agent.routing import SupervisorRoutingMiddleware

        build_graph()

        call_kwargs = mock_graph_create.call_args
        middleware = call_kwargs.kwargs.get("middleware") or call_kwargs[1].get("middleware")
        assert middleware is not None
        assert len(middleware) == 1
        assert isinstance(middleware[0], SupervisorRoutingMiddleware)

    def test_build_graph_has_single_langgraph_config_parameter(self):

        from whoopdata.agent.graph import build_graph

        parameters = list(inspect.signature(build_graph).parameters.values())
        assert len(parameters) == 1
        assert parameters[0].name == "config"

    @patch("whoopdata.agent.specialists.create_agent")
    @patch("whoopdata.agent.graph.create_agent")
    def test_build_graph_accepts_langgraph_config_and_uses_its_checkpointer(
        self, mock_graph_create, mock_spec_create
    ):
        mock_spec_create.return_value = MagicMock()
        mock_graph_create.return_value = MagicMock()

        from langgraph.constants import CONFIG_KEY_CHECKPOINTER

        from whoopdata.agent.graph import build_graph

        checkpointer = object()
        build_graph({"configurable": {CONFIG_KEY_CHECKPOINTER: checkpointer}})

        call_kwargs = mock_graph_create.call_args
        kwargs = call_kwargs.kwargs or call_kwargs[1]
        assert kwargs["checkpointer"] is checkpointer
