from __future__ import annotations

import asyncio

from langchain_core.messages import AIMessage, ToolMessage

from whoopdata.agent.conversation_service import ConversationService


class FakeGraph:
    def __init__(self, result: dict | None = None) -> None:
        self.calls: list[tuple[dict, dict]] = []
        self._result = result or {"messages": [AIMessage(content="Default response.")]}

    async def ainvoke(self, input: dict, config: dict) -> dict:
        self.calls.append((input, config))
        return self._result


def test_start_conversation_reuses_existing_session_thread_mapping():
    service = ConversationService(graph=FakeGraph())

    first = service.start_conversation()
    second = service.start_conversation(session_id=first.session_id)

    assert second.session_id == first.session_id
    assert second.thread_id == first.thread_id


def test_send_message_uses_existing_session_thread_and_shapes_response():
    graph = FakeGraph(
        {
            "messages": [
                AIMessage(
                    content="I'll generate a chart for you.",
                    tool_calls=[
                        {
                            "name": "python_interpreter",
                            "args": {"query": "print('chart')"},
                            "id": "tool-call-1",
                        }
                    ],
                ),
                ToolMessage(
                    content='{"images": [{"data": "abc123", "filename": "plot.png"}]}',
                    tool_call_id="tool-call-1",
                ),
                AIMessage(content="Here is your chart."),
            ]
        }
    )
    service = ConversationService(graph=graph)
    handle = service.start_conversation()

    response = asyncio.run(
        service.send_message(
            message="Show me a chart",
            session_id=handle.session_id,
        )
    )

    assert response.surface == "agent"
    assert response.session_id == handle.session_id
    assert response.thread_id == handle.thread_id
    assert response.assistant_message == "Here is your chart."
    assert response.messages[0].content == "Show me a chart"
    assert any(artifact.kind == "python_code" for artifact in response.artifacts)
    assert any(artifact.kind == "image" for artifact in response.artifacts)
    assert len(graph.calls) == 1
    call_input, call_config = graph.calls[0]
    assert call_config == {"configurable": {"thread_id": handle.thread_id}}
    assert call_input["messages"][0].content == "Show me a chart"


def test_send_message_respects_explicit_thread_id_without_existing_session():
    graph = FakeGraph({"messages": [AIMessage(content="Thread-scoped response.")]})
    service = ConversationService(graph=graph)

    response = asyncio.run(
        service.send_message(
            message="Hello",
            thread_id="thread-explicit",
        )
    )

    assert response.thread_id == "thread-explicit"
    assert response.session_id is not None
    assert graph.calls[0][1] == {"configurable": {"thread_id": "thread-explicit"}}
