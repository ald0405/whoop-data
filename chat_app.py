#!/usr/bin/env python3
"""
Health Data Agent Chat Interface

A Gradio-powered chat interface to interact with your WHOOP and Withings health data.
Ask questions about your workouts, sleep, recovery, weight trends, and more!
"""

import asyncio
import gradio as gr
from whoopdata.agent.graph import run_agent
import uuid
from datetime import datetime
from typing import List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global conversation state
conversations = {}


def get_thread_id() -> str:
    """Generate a unique thread ID for conversation tracking."""
    return f"chat_{uuid.uuid4().hex[:8]}"


async def chat_with_agent(
    message: str, history: List[Tuple[str, str]], thread_id: str = None
) -> Tuple[List[Tuple[str, str]], str]:
    """
    Send a message to the health data agent and get a response.

    Args:
        message: User's message
        history: Chat history as list of (user_msg, agent_msg) tuples
        thread_id: Unique conversation thread ID

    Returns:
        Updated history and empty string for input box
    """
    if not thread_id:
        thread_id = get_thread_id()

    try:
        # Add user message to history
        history = history or []
        logger.info(f"User message: {message}")

        # Call the agent
        result = await run_agent(message, thread_id)

        # Extract the agent's response from the final message
        if result and "messages" in result:
            final_message = result["messages"][-1]
            if hasattr(final_message, "content") and final_message.content:
                agent_response = final_message.content
            else:
                agent_response = "I processed your request, but didn't generate a response. Please try rephrasing your question."
        else:
            agent_response = (
                "I'm having trouble processing your request right now. Please try again."
            )

        logger.info(f"Agent response length: {len(agent_response)}")

        # Add to history
        history.append((message, agent_response))

        return history, ""  # Return updated history and clear input box

    except Exception as e:
        error_msg = f"Sorry, I encountered an error: {str(e)}"
        logger.error(f"Chat error: {e}")
        history.append((message, error_msg))
        return history, ""


def create_chat_interface():
    """Create and configure the Gradio chat interface."""

    # Custom CSS for better styling
    custom_css = """
    .gradio-container {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .chatbot {
        height: 600px !important;
        overflow-y: auto;
    }
    .chat-message {
        margin: 10px 0;
        padding: 12px;
        border-radius: 8px;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    .bot-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }
    """

    with gr.Blocks(title="Health Data Agent", theme=gr.themes.Soft(), css=custom_css) as interface:

        # Header
        gr.Markdown(
            """
        # 🏥 Health Data Agent Chat
        
        **Your AI-powered health data assistant!** Ask me anything about:
        
        - 🎾 **Tennis workouts** - performance analysis, heart rate zones, strain patterns
        - 🏃‍♂️ **Running data** - TRIMP scores, training load, pace analysis  
        - 😴 **Sleep patterns** - efficiency, stages, recovery impact
        - 📊 **Recovery trends** - HRV, resting heart rate, weekly patterns
        - ⚖️ **Weight trends** - body composition, BMI changes over time
        - 💓 **Heart rate & BP** - cardiovascular health patterns
        
        **Example questions:**
        - "Show me my tennis workouts from 2025"
        - "What's my weight trend over the last 30 days?"
        - "How has my recovery been this month?"
        - "Get my latest sleep data and analyze my patterns"
        """
        )

        # Chat interface
        chatbot = gr.Chatbot(
            label="Health Data Conversation",
            height=600,
            show_label=True,
            container=True,
            type="tuples",  # Use tuples format for compatibility
        )

        # Input components
        with gr.Row():
            msg_input = gr.Textbox(
                placeholder="Ask me about your health data...",
                label="Your message",
                scale=4,
                lines=1,
            )
            send_btn = gr.Button("Send 💬", variant="primary", scale=1)

        # Thread ID state (hidden)
        thread_id_state = gr.State(value=get_thread_id())

        # Examples
        gr.Examples(
            examples=[
                "Show me my recent tennis workouts",
                "What's my weight trend for 2025?",
                "Get my latest recovery data",
                "How has my sleep been this week?",
                "Show me my running performance with TRIMP scores",
                "What are my cardiovascular trends?",
            ],
            inputs=msg_input,
            label="💡 Try these example questions:",
        )

        # Event handlers
        async def handle_message(message, history, thread_id):
            """Handle message submission with async support."""
            if not message.strip():
                return history, ""
            return await chat_with_agent(message, history, thread_id)

        # Submit on button click
        send_btn.click(
            fn=handle_message,
            inputs=[msg_input, chatbot, thread_id_state],
            outputs=[chatbot, msg_input],
            show_progress=True,
        )

        # Submit on Enter key
        msg_input.submit(
            fn=handle_message,
            inputs=[msg_input, chatbot, thread_id_state],
            outputs=[chatbot, msg_input],
            show_progress=True,
        )

        # Info section
        with gr.Accordion("ℹ️ About Your Health Data", open=False):
            gr.Markdown(
                """
            ### Data Sources
            - **WHOOP**: Recovery, workouts, sleep data (2023-2025)
            - **Withings**: Weight, body composition, heart rate, blood pressure
            
            ### Agent Capabilities
            - 📈 **Statistical Analysis**: Trends, averages, patterns over time
            - 🎯 **Personalized Insights**: AI-powered recommendations based on your data
            - 📋 **Data Filtering**: Filter by date ranges, specific metrics, activity types
            - 🔍 **Deep Dives**: Detailed breakdowns of specific workouts or periods
            
            ### Tips for Best Results
            - Be specific with your questions (e.g., "tennis workouts in October 2025")
            - Ask for trends over specific time periods
            - Request actionable insights for better health outcomes
            """
            )

    return interface


def main():
    """Launch the chat interface."""
    print("🚀 Starting Health Data Agent Chat Interface...")
    print("📊 Your health data is ready for analysis!")

    # Create and launch interface
    interface = create_chat_interface()

    # Launch with public sharing disabled for security
    interface.launch(
        server_name="0.0.0.0", server_port=7860, share=False, inbrowser=True  # Auto-open in browser
    )


if __name__ == "__main__":
    main()
