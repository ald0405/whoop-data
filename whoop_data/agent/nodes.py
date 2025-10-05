"""Agent nodes for health data processing."""

from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from .schemas import HealthAgentState, HealthContextSchema
from .tools import AVAILABLE_TOOLS
from . import settings


async def supervisor_node(state: HealthAgentState) -> HealthAgentState:
    """Main supervisor node that processes user queries and decides on tool usage."""
    
    # Initialize OpenAI LLM
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.AGENT_TIMEOUT_SECONDS
    )
    
    messages = state.get("messages", [])
    
    # Add system message if not present
    if not any(message.type == "system" for message in messages):
        system_content = """You are a comprehensive WHOOP and Withings health data assistant.
        
        You have access to tools that can retrieve detailed health and fitness data from WHOOP devices and Withings scales/monitors.
        When users ask about their health metrics, provide helpful insights by using the appropriate tools.
        
        Available WHOOP tools:
        - get_latest_recovery: Latest recovery score, HRV, and resting heart rate
        - get_top_recoveries: Highest recovery scores to identify patterns
        - get_recovery_trends: Weekly recovery trends over time
        - get_latest_sleep: Latest sleep data including stages and efficiency
        - get_latest_workout: Latest workout with strain and heart rate zones
        - get_running_workouts: Running workouts with TRIMP training load scores
        - get_tennis_workouts: Tennis-specific workout data
        
        Available Withings tools:
        - get_latest_weight: Latest weight with BMI and body composition
        - get_weight_stats: Weight trends and statistics over time
        - get_latest_heart_rate: Latest heart rate and blood pressure
        - get_withings_summary: Complete Withings health data summary
        
        Code Analysis Tool:
        - python_interpreter: Execute Python code for advanced data analysis, visualizations, and statistical computations
        
        When users ask for data analysis, correlations, trends, or visualizations:
        1. First retrieve the relevant health data using the appropriate tools
        2. Then use the Python interpreter to analyze, visualize, or calculate insights
        3. Provide clear explanations of your analysis and findings
        
        Always provide context and actionable insights. Help users understand:
        - What the numbers mean for their health and fitness
        - Trends and patterns in their data through analysis and charts
        - How different metrics relate to each other (correlations, relationships)
        - Practical recommendations based on statistical analysis of their data
        
        Be encouraging and supportive while being scientifically accurate.
        Use Python code to create meaningful visualizations and perform statistical analysis when appropriate."""
        
        system_message = SystemMessage(content=system_content)
        messages = [system_message] + messages
    
    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(AVAILABLE_TOOLS)
    
    # Get response from LLM
    response = await llm_with_tools.ainvoke(messages)
    
    # Return updated state
    if any(message.type == "system" for message in state.get("messages", [])):
        return {"messages": [response]}
    else:
        return {"messages": [messages[0], response]}  # Include system message


async def tools_node(state: HealthAgentState) -> HealthAgentState:
    """Execute tool calls and return results."""
    
    tool_executor = ToolNode(AVAILABLE_TOOLS)
    result = await tool_executor.ainvoke(state)
    
    return result