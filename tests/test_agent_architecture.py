"""Tests for the new agent architecture.

Verifies registry, tool grouping, specialist factory, graph build, and prompts
without requiring the API server or LLM calls.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage


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
        required_keys = {"name", "description", "system_prompt", "tools"}
        for agent_name, config in AGENT_REGISTRY.items():
            missing = required_keys - set(config.keys())
            assert not missing, f"{agent_name} missing keys: {missing}"

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
            assert len(config["system_prompt"]) > 10, f"{agent_name} system_prompt is empty or too short"

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
                    pytest.fail(
                        f"Tool '{tool_name}' in both '{seen[tool_name]}' and '{name}'"
                    )
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
                assert name in registry_tools, (
                    f"Tool '{name}' not assigned to any specialist"
                )


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

class TestSpecialistFactory:
    """Test build_specialist_tools with mocked create_agent."""

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


# ---------------------------------------------------------------------------
# Extract final response tests
# ---------------------------------------------------------------------------

class TestExtractFinalResponse:
    """Test _extract_final_response helper."""

    def test_extracts_last_ai_message(self):
        from whoopdata.agent.specialists import _extract_final_response

        result = {
            "messages": [
                AIMessage(content="thinking...", tool_calls=[{"name": "foo", "args": {}, "id": "1"}]),
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

    def test_supervisor_prompt_exists(self):
        from whoopdata.agent.prompts import SUPERVISOR_SYSTEM_PROMPT
        assert len(SUPERVISOR_SYSTEM_PROMPT) > 100

    def test_supervisor_prompt_mentions_specialists(self):
        from whoopdata.agent.prompts import SUPERVISOR_SYSTEM_PROMPT
        assert "health data" in SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "analytics" in SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "environment" in SUPERVISOR_SYSTEM_PROMPT.lower()

    def test_exercise_prompt_file_exists(self):
        path = Path(__file__).parent.parent / "data" / "prompts" / "agents" / "exercise_sub_agent.md"
        assert path.exists(), f"Exercise prompt not found at {path}"
        content = path.read_text()
        assert len(content) > 100

    def test_behaviour_change_prompt_file_exists(self):
        path = Path(__file__).parent.parent / "data" / "prompts" / "agents" / "behaviour_change_sub_agent.md"
        assert path.exists(), f"Behaviour change prompt not found at {path}"
        content = path.read_text()
        assert len(content) > 100


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
    def test_build_graph_supervisor_gets_specialist_tools_plus_repl(
        self, mock_graph_create, mock_spec_create
    ):
        """Supervisor should receive specialist tools + python_repl."""
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

        # Should have N specialist tools + 1 python_repl
        expected_count = len(AGENT_REGISTRY) + 1
        assert len(tools) == expected_count, (
            f"Expected {expected_count} tools, got {len(tools)}"
        )
