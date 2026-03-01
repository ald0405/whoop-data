"""LangGraph assembly for the health data agent.

Builds a supervisor agent using create_agent with specialist subagents
wrapped as tools. All user-visible responses come from the supervisor.
"""

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from .prompts import SUPERVISOR_SYSTEM_PROMPT
from .schemas import AgentConfig
from .specialists import build_specialist_tools
from .tools import python_repl_tool, get_protein_recommendation_tool
from . import settings


def build_graph():
    """Build the health data agent graph.

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
    graph = create_agent(
        model=settings.SUPERVISOR_MODEL,
        tools=all_tools,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        name="health_coach",
    )

    return graph


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
