import asyncio

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from whoopdata.agent import persistence
from whoopdata.agent.persistence import AgentPersistence


def test_unset_url_uses_in_memory(monkeypatch):
    monkeypatch.setattr(persistence.settings, "AGENT_POSTGRES_URL", None)
    p = AgentPersistence()

    checkpointer, store = asyncio.run(p.get_resources())

    assert isinstance(checkpointer, InMemorySaver)
    assert isinstance(store, InMemoryStore)
    assert not p.is_degraded


def test_unreachable_postgres_falls_back_to_in_memory(monkeypatch):
    # Port 1 on localhost refuses connections immediately.
    monkeypatch.setattr(
        persistence.settings,
        "AGENT_POSTGRES_URL",
        "postgresql://postgres:postgres@127.0.0.1:1/whoop_agent",
    )
    monkeypatch.setattr(persistence, "POSTGRES_CONNECT_TIMEOUT_SECONDS", 1.0)
    p = AgentPersistence()

    checkpointer, store = asyncio.run(p.get_resources())

    assert isinstance(checkpointer, InMemorySaver)
    assert isinstance(store, InMemoryStore)
    assert p.is_degraded


def test_degraded_persistence_reconnects_after_cooldown(monkeypatch):
    monkeypatch.setattr(persistence.settings, "AGENT_POSTGRES_URL", "postgresql://x")
    monkeypatch.setattr(persistence, "POSTGRES_RETRY_COOLDOWN_SECONDS", 0.0)
    attempts = {"n": 0}

    async def _flaky_open(self):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ConnectionError("connection refused")
        return "pg_checkpointer", "pg_store"

    monkeypatch.setattr(AgentPersistence, "_open_postgres", _flaky_open)
    p = AgentPersistence()

    async def _run():
        first = await p.get_resources()
        second = await p.get_resources()
        third = await p.get_resources()
        return first, second, third

    first, second, third = asyncio.run(_run())

    assert isinstance(first[0], InMemorySaver)
    assert second == ("pg_checkpointer", "pg_store")
    assert third == second
    assert attempts["n"] == 2
    assert not p.is_degraded


def test_degraded_persistence_keeps_same_fallback_between_failed_retries(monkeypatch):
    monkeypatch.setattr(persistence.settings, "AGENT_POSTGRES_URL", "postgresql://x")
    monkeypatch.setattr(persistence, "POSTGRES_RETRY_COOLDOWN_SECONDS", 0.0)

    async def _always_fail(self):
        raise ConnectionError("connection refused")

    monkeypatch.setattr(AgentPersistence, "_open_postgres", _always_fail)
    p = AgentPersistence()

    async def _run():
        return await p.get_resources(), await p.get_resources()

    first, second = asyncio.run(_run())

    # Same in-memory objects, so in-flight threads survive repeated retries.
    assert first[0] is second[0]
    assert first[1] is second[1]
