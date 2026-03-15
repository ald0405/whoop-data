#!/usr/bin/env python3
"""
Health Data Agent Chat Interface

A Gradio-powered chat interface to interact with your WHOOP and Withings health data.
Ask questions about your workouts, sleep, recovery, weight trends, and more!
"""

import uuid
import logging
import re
from typing import List, Tuple

import gradio as gr

from whoopdata.agent.conversation_service import get_conversation_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_thread_id() -> str:
    """Generate a unique thread ID for conversation tracking."""
    return f"chat_{uuid.uuid4().hex[:8]}"


async def chat_with_agent(
    message: str,
    history: List[Tuple[str, str]],
    session_id: str | None = None,
    thread_id: str | None = None,
) -> Tuple[List[Tuple[str, str]], str, str | None, str]:
    """
    Send a message to the health data agent and get a response.

    Args:
        message: User's message
        history: Chat history as list of (user_msg, agent_msg) tuples
        session_id: Stable session ID for the public conversation boundary
        thread_id: Unique conversation thread ID

    Returns:
        Updated history, empty string for input box, and persisted conversation IDs
    """
    if not thread_id:
        thread_id = get_thread_id()

    try:
        # Add user message to history
        history = history or []
        logger.info(f"User message: {message}")

        conversation_service = get_conversation_service()
        conversation_response = await conversation_service.send_message(
            message=message,
            session_id=session_id,
            thread_id=thread_id,
        )
        session_id = conversation_response.session_id
        thread_id = conversation_response.thread_id
        agent_response = conversation_response.assistant_message

        for artifact in conversation_response.artifacts:
            if artifact.kind == "image" and artifact.mime_type == "image/png":
                img_html = f'<img src="data:{artifact.mime_type};base64,{artifact.content}" style="max-width: 600px; border-radius: 8px; margin: 10px 0;"/>'
                agent_response += f"\n\n{img_html}"

        python_artifact = next(
            (artifact for artifact in conversation_response.artifacts if artifact.kind == "python_code"),
            None,
        )
        if python_artifact and python_artifact.content:
            code_block = f"\n\n**Generated Python Code:**\n```python\n{python_artifact.content}\n```\n\n"
            agent_response = code_block + agent_response

        # Convert markdown image syntax to HTML for Gradio
        # Pattern: ![alt text](data:image/png;base64,...)
        markdown_image_pattern = r'!\[([^\]]*)\]\((data:image/[^;]+;base64,[^)]+)\)'

        def replace_markdown_image(match):
            alt_text = match.group(1)
            data_url = match.group(2)
            return f'<img src="{data_url}" alt="{alt_text}" style="max-width: 600px; border-radius: 8px; margin: 10px 0;"/>'

        agent_response = re.sub(markdown_image_pattern, replace_markdown_image, agent_response)
        logger.info(f"Converted markdown images to HTML")

        logger.info(f"Agent response length: {len(agent_response)}")

        # Add to history
        history.append((message, agent_response))

        return history, "", session_id, thread_id

    except Exception as e:
        error_msg = f"Sorry, I encountered an error: {str(e)}"
        logger.error(f"Chat error: {e}")
        history.append((message, error_msg))
        return history, "", session_id, thread_id


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

        # Conversation state (hidden)
        session_id_state = gr.State(value=None)
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
        async def handle_message(message, history, session_id, thread_id):
            """Handle message submission with async support."""
            if not message.strip():
                return history, "", session_id, thread_id
            return await chat_with_agent(message, history, session_id, thread_id)

        # Submit on button click
        send_btn.click(
            fn=handle_message,
            inputs=[msg_input, chatbot, session_id_state, thread_id_state],
            outputs=[chatbot, msg_input, session_id_state, thread_id_state],
            show_progress=True,
        )

        # Submit on Enter key
        msg_input.submit(
            fn=handle_message,
            inputs=[msg_input, chatbot, session_id_state, thread_id_state],
            outputs=[chatbot, msg_input, session_id_state, thread_id_state],
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
