"""Specialist subagent factory.

Builds create_agent instances for each registry entry and wraps them
as tools for the supervisor to call. Each specialist runs in an isolated
context and returns only its final text response.
"""

from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_core.messages import AIMessage

from .tools import TOOLS_BY_NAME
from .registry import AGENT_REGISTRY
from . import settings


def _get_specialist_tools(tool_names: list[str]) -> list:
    """Resolve tool names to tool instances from TOOLS_BY_NAME."""
    tools = []
    for name in tool_names:
        if name in TOOLS_BY_NAME:
            tools.append(TOOLS_BY_NAME[name])
    return tools


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


def build_specialist_tools(
    registry: dict[str, dict] | None = None,
    model_override: str | None = None,
) -> list:
    """Build specialist wrapper tools from the agent registry.

    Each registry entry becomes a compiled create_agent wrapped in a @tool
    that the supervisor can call. The tool description is the routing signal.

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

        # Determine model for this specialist
        model = model_override or settings.SPECIALIST_CONFIG.get(
            agent_name, {}
        ).get("model", settings.SPECIALIST_MODEL)

        # Create the subagent
        agent = create_agent(
            model=model,
            tools=domain_tools,
            system_prompt=system_prompt,
            name=agent_name,
        )

        # Wrap as a tool — closure captures agent_name, agent, description
        def _make_tool(name: str, desc: str, compiled_agent):
            async def specialist_fn(query: str) -> str:
                """Delegate a query to a specialist subagent."""
                result = await compiled_agent.ainvoke(
                    {"messages": [{"role": "user", "content": query}]}
                )
                return _extract_final_response(result)

            return StructuredTool.from_function(
                coroutine=specialist_fn,
                name=name,
                description=desc,
            )

        specialist_tools.append(_make_tool(agent_name, description, agent))

    return specialist_tools
