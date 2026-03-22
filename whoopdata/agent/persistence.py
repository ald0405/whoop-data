from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from whoopdata.agent import settings

try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.store.postgres.aio import AsyncPostgresStore
except Exception:  # pragma: no cover - optional dependency in tests/dev
    AsyncPostgresSaver = None
    AsyncPostgresStore = None


class AgentPersistence:
    """Shared persistence resources for the agent graph."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._checkpointer: Any | None = None
        self._store: Any | None = None
        self._checkpointer_cm: AbstractAsyncContextManager[Any] | None = None
        self._store_cm: AbstractAsyncContextManager[Any] | None = None

    async def get_resources(self) -> tuple[Any, Any]:
        if self._checkpointer is not None and self._store is not None:
            return self._checkpointer, self._store

        async with self._lock:
            if self._checkpointer is not None and self._store is not None:
                return self._checkpointer, self._store

            if settings.AGENT_POSTGRES_URL and AsyncPostgresSaver and AsyncPostgresStore:
                self._checkpointer_cm = AsyncPostgresSaver.from_conn_string(
                    settings.AGENT_POSTGRES_URL
                )
                self._store_cm = AsyncPostgresStore.from_conn_string(settings.AGENT_POSTGRES_URL)
                self._checkpointer = await self._checkpointer_cm.__aenter__()
                self._store = await self._store_cm.__aenter__()
                if settings.AGENT_PERSISTENCE_AUTO_SETUP:
                    await self._checkpointer.setup()
                    await self._store.setup()
            else:
                self._checkpointer = InMemorySaver()
                self._store = InMemoryStore()

            return self._checkpointer, self._store


_PERSISTENCE = AgentPersistence()


async def get_agent_persistence() -> tuple[Any, Any]:
    return await _PERSISTENCE.get_resources()
