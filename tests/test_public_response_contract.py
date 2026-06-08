from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage

from whoopdata.agent.public_response import build_agent_conversation_response
from whoopdata.api.public_response_contract import PUBLIC_RESPONSE_CONTRACT


def test_response_contracts_cover_all_public_surfaces():
    assert set(PUBLIC_RESPONSE_CONTRACT.keys()) == {"data", "insights", "agent", "web"}
    assert "record-oriented" in PUBLIC_RESPONSE_CONTRACT["data"].summary.lower()
    assert "interpreted" in PUBLIC_RESPONSE_CONTRACT["insights"].summary.lower()
    assert "thread_id" in " ".join(PUBLIC_RESPONSE_CONTRACT["agent"].invariants)
    assert "html" in PUBLIC_RESPONSE_CONTRACT["web"].summary.lower()


def test_agent_conversation_response_hides_raw_langgraph_state():
    result = {
        "messages": [
            AIMessage(
                content="Let me pull your recovery data.",
                tool_calls=[
                    {
                        "name": "get_recovery_data_tool",
                        "args": {"latest": True},
                        "id": "tool-call-1",
                    }
                ],
            ),
            ToolMessage(
                content='{"recovery_score": 65}',
                tool_call_id="tool-call-1",
            ),
            AIMessage(content="Here is your chart."),
        ]
    }

    response = build_agent_conversation_response(
        result,
        thread_id="thread-123",
        user_message="Show me a chart",
    )

    assert response.surface == "agent"
    assert response.thread_id == "thread-123"
    assert response.session_id is None
    assert response.assistant_message == "Here is your chart."
    assert [message.role for message in response.messages] == ["user", "assistant"]
    assert response.messages[0].content == "Show me a chart"
    assert response.messages[1].content == "Here is your chart."
