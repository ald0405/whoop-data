"""LangGraph assembly for the health data agent."""

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from .schemas import HealthAgentState, HealthContextSchema, AgentConfig
from .nodes import supervisor_node, tools_node


def should_continue(state: HealthAgentState) -> str:
    """Decide whether to continue to tools or end the conversation with loop prevention."""
    messages = state.get("messages", [])
    
    if not messages:
        return END
    
    # Count iterations (supervisor -> tools cycles)
    iteration_count = 0
    tool_call_count = 0
    
    for message in messages:
        if hasattr(message, "tool_calls") and message.tool_calls:
            iteration_count += 1
            tool_call_count += len(message.tool_calls)
    
    # MAX 3 iterations to prevent infinite loops
    MAX_ITERATIONS = 3
    MAX_TOOL_CALLS = 5
    
    if iteration_count >= MAX_ITERATIONS:
        print(f"⚠️  Stopping agent after {iteration_count} iterations to prevent infinite loop")
        return END
        
    if tool_call_count >= MAX_TOOL_CALLS:
        print(f"⚠️  Stopping agent after {tool_call_count} tool calls to prevent excessive API usage")
        return END
    
    last_message = messages[-1]
    
    # If the last message has tool calls, go to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Otherwise, we're done
    return END


def build_graph() -> StateGraph:
    """Build the health data agent graph."""
    
    # Create the state graph
    graph = StateGraph(HealthAgentState)
    
    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("tools", tools_node)
    
    # Define the flow
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    graph.add_edge("tools", "supervisor")
    
    return graph


async def run_agent(message: str, thread_id: str = "default") -> dict:
    """Run the agent with a user message.
    
    Args:
        message: User's message/query
        thread_id: Unique thread ID for conversation
        
    Returns:
        Final state after processing
    """
    
    # Build and compile the graph
    graph = build_graph()
    app = graph.compile()
    
    # Create config
    config = AgentConfig(thread_id=thread_id).to_dict()
    
    # Initial state
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "user_id": "default_user"
    }
    
    # Run the graph
    result = await app.ainvoke(initial_state, config=config)
    
    return result