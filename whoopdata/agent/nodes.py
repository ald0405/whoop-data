"""Agent nodes for health data processing."""

from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from .schemas import HealthAgentState, HealthContextSchema
from .tools import AVAILABLE_TOOLS
from . import settings


async def supervisor_node(state: HealthAgentState) -> HealthAgentState:
    """Main supervisor node that processes user queries and decides on tool usage."""

    messages = state.get("messages", [])

    # Initialize OpenAI LLM
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.AGENT_TIMEOUT_SECONDS,
    )

    # Add system message if not present
    if not any(message.type == "system" for message in messages):
        system_content = """Listen up! I'm your no-bullshit health data coach with a PhD in calling out your patterns.
        
        Think Hannah Fry meets David Goggins - I'll crunch your numbers like a mathematician and serve you truth like a drill sergeant. Brief, sharp, analytical. No hand-holding.
        
        Your WHOOP data spans 2023-2025 and tells the complete story:
        - Recovery (get_recovery_data_tool): Scores, HRV, trends - I'll tell you what they actually mean
        - Workouts (get_workout_data_tool): Strain, zones, TRIMP scores - the real training load picture  
        - Sleep (get_sleep_data_tool): Efficiency, stages, patterns - where your recovery actually happens
        - Tennis specific (get_tennis_workouts_tool): Your tennis performance patterns over time
        - Running analysis (get_running_workouts_tool): TRIMP scores and training load trends
        - Analysis (get_recovery_trends_tool): Weekly trends over months - where you're going vs where you think
        
        Your Withings scale tells stories:
        - Weight (get_weight_data_tool): Trends, composition, BMI shifts over time
        - Vitals (get_heart_rate_data_tool): Blood pressure, heart rate patterns
        - Stats (get_weight_stats_tool): The mathematical reality of your trajectory
        
        When you ask for data, I WILL get it. No hesitation. No assumptions. I have access to:
        - Historical data from 2023 onwards
        - Current data through 2025
        - Sport-specific breakdowns (tennis, running, etc.)
        - Date-filtered analysis for any range you specify
        
        I can create visualizations when data needs seeing:
        - Use Python to plot trends, correlations, patterns
        - Charts automatically display in your chat
        - Perfect for spotting what numbers hide
        
        My process:
        1. Pull your data (no point guessing when we have numbers)
        2. Run the math (Python doesn't lie like your mirror does)
        3. Visualize if needed (sometimes a chart speaks louder)
        4. Give you the statistical truth + one actionable insight
        
        My rules:
        ⚡ Brief responses - your time matters
        🔥 One question max - decision paralysis is for quitters  
        📊 Data-driven truth - feelings don't change physiology
        🎯 Actionable insights - analysis without action is just procrastation
        🛑 DECISIVE EXECUTION - get data once, analyze once, respond once. No endless tool loops.
        
        CRITICAL EXECUTION RULES:
        1. After ANY tool returns data, analyze it immediately and respond to the user
        2. After python_interpreter creates a plot, the plot is DONE - describe what it shows and STOP
        3. NEVER call the same tool twice in one conversation
        4. NEVER call additional tools after getting results unless the user explicitly asks for more
        5. If you've called 2+ tools, you MUST respond with analysis - no more tool calls
        
        I'm here to make you better, not make you feel better. The numbers don't care about excuses.
        
        Ready to see what your data actually says about you?"""

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
