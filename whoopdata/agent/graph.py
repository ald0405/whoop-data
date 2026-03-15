"""LangGraph assembly for the health data agent.

Builds a supervisor agent using create_agent with specialist subagents
wrapped as tools. All user-visible responses come from the supervisor.
"""
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langgraph.constants import CONFIG_KEY_CHECKPOINTER

from .prompts import SUPERVISOR_SYSTEM_PROMPT
from .schemas import AgentConfig
from .specialists import build_specialist_tools
from .tools import python_repl_tool, get_protein_recommendation_tool
from . import settings

def _resolve_checkpointer(
    config: dict[str, Any] | None,
) -> Any | None:
    if not isinstance(config, dict):
        return None
    configurable = config.get("configurable")
    if not isinstance(configurable, dict):
        return None
    return configurable.get(CONFIG_KEY_CHECKPOINTER)

def _create_graph(*, checkpointer: Any | None = None):
    """Build the compiled health data agent graph.

    Creates a supervisor agent (via create_agent) that delegates to
    specialist subagents wrapped as tools. The supervisor always
    produces the final user-facing response.

    Returns:
        Compiled LangGraph graph ready for .invoke() / .ainvoke()
    """
    # Build specialist wrapper tools from registry
    specialist_tools = build_specialist_tools()

    # Supervisor gets specialist tools + python REPL + protein tool for direct use
    all_tools = specialist_tools + [python_repl_tool, get_protein_recommendation_tool]

    # Create the supervisor agent
    # create_agent returns a compiled LangGraph graph that handles
    # the tool-calling loop internally
    graph_kwargs = {
        "model": settings.SUPERVISOR_MODEL,
        "tools": all_tools,
        "system_prompt": SUPERVISOR_SYSTEM_PROMPT,
        "name": "health_coach",
    }
    if checkpointer is not None:
        graph_kwargs["checkpointer"] = checkpointer

    graph = create_agent(
        **graph_kwargs,
    )

    return graph


def build_graph(config: dict[str, Any] | None = None):
    """Build the health data agent graph from a LangGraph config.

    This factory intentionally exposes a single positional config
    argument because LangGraph validates graph factory signatures while
    loading `langgraph.json`.

    Returns:
        Compiled LangGraph graph ready for .invoke() / .ainvoke()
    """
    return _create_graph(checkpointer=_resolve_checkpointer(config))


async def run_agent(message: str, thread_id: str = "default") -> dict:
    """Run the agent with a user message.

    Args:
        message: User's message/query
        thread_id: Unique thread ID for conversation

    Returns:
        Final state after processing
    """
    # Build the compiled graph
    app = build_graph()

    # Create config
    config = AgentConfig(thread_id=thread_id).to_dict()

    # Run the graph
    result = await app.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    return result
