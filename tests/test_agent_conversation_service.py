from __future__ import annotations

import asyncio

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.constants import CONFIG_KEY_CHECKPOINTER

from whoopdata.agent.conversation_service import ConversationService
from whoopdata.agent.graph import CONFIG_KEY_STORE


class FakeGraph:
    def __init__(self, result: dict | None = None) -> None:
        self.calls: list[tuple[dict, dict, object | None]] = []
        self._result = result or {"messages": [AIMessage(content="Default response.")]}

    async def ainvoke(self, input: dict, config: dict, *, context=None) -> dict:
        self.calls.append((input, config, context))
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
    call_input, call_config, call_context = graph.calls[0]
    assert call_config == {"configurable": {"thread_id": handle.thread_id}}
    assert call_input["messages"][0].content == "Show me a chart"
    assert call_context.user_id == "default_user"


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


def test_send_message_reuses_same_thread_for_session_resume():
    graph = FakeGraph({"messages": [AIMessage(content="Resumed response.")]})
    service = ConversationService(graph=graph)

    first_response = asyncio.run(service.send_message(message="First message"))
    second_response = asyncio.run(
        service.send_message(
            message="Follow-up message",
            session_id=first_response.session_id,
        )
    )

    assert second_response.session_id == first_response.session_id
    assert second_response.thread_id == first_response.thread_id
    assert graph.calls[0][1] == graph.calls[1][1]


def test_send_message_isolates_distinct_conversations_by_thread():
    graph = FakeGraph({"messages": [AIMessage(content="Isolated response.")]})
    service = ConversationService(graph=graph)

    first_response = asyncio.run(service.send_message(message="Conversation one"))
    second_response = asyncio.run(service.send_message(message="Conversation two"))

    assert first_response.session_id != second_response.session_id
    assert first_response.thread_id != second_response.thread_id
    assert graph.calls[0][1] != graph.calls[1][1]


def test_ensure_graph_passes_checkpointer_and_store_with_langgraph_keys(monkeypatch):
    captured: dict[str, object] = {}

    async def _fake_get_agent_persistence():
        return "checkpointer", "store"

    def _fake_build_graph(config):
        captured["config"] = config
        return FakeGraph()

    monkeypatch.setattr(
        "whoopdata.agent.conversation_service.get_agent_persistence",
        _fake_get_agent_persistence,
    )
    monkeypatch.setattr(
        "whoopdata.agent.conversation_service.build_graph",
        _fake_build_graph,
    )

    service = ConversationService()

    asyncio.run(service._ensure_graph())

    assert captured["config"] == {
        "configurable": {
            CONFIG_KEY_CHECKPOINTER: "checkpointer",
            CONFIG_KEY_STORE: "store",
        }
    }
