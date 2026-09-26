"""Checkpointer and store persistence for the agent graph."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from whoopdata.agent import settings

try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.store.postgres.aio import AsyncPostgresStore
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool
except Exception:  # pragma: no cover - optional dependency in tests/dev
    AsyncPostgresSaver = None
    AsyncPostgresStore = None
    AsyncConnectionPool = None
    dict_row = None

logger = logging.getLogger(__name__)

# How long to wait for Postgres on first connect before degrading to in-memory.
POSTGRES_CONNECT_TIMEOUT_SECONDS = 5.0
# How long to stay on the in-memory fallback before trying Postgres again.
POSTGRES_RETRY_COOLDOWN_SECONDS = 60.0


class AgentPersistence:
    """Shared persistence resources for the agent graph.

    Uses a Postgres connection pool when ``AGENT_POSTGRES_URL`` is set. The pool
    health-checks connections on checkout, so a Postgres restart does not leave a
    dead connection behind. If Postgres is unreachable, falls back to in-memory
    resources (conversation memory is not persisted) and retries Postgres after a
    cooldown instead of failing every request.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._checkpointer: Any | None = None
        self._store: Any | None = None
        self._pool: Any | None = None
        self._degraded_since: float | None = None

    @property
    def is_degraded(self) -> bool:
        """True when running on the in-memory fallback despite Postgres being configured."""
        return self._degraded_since is not None

    def _postgres_configured(self) -> bool:
        return bool(
            settings.AGENT_POSTGRES_URL
            and AsyncPostgresSaver
            and AsyncPostgresStore
            and AsyncConnectionPool
        )

    def _should_retry_postgres(self) -> bool:
        return (
            self._degraded_since is not None
            and time.monotonic() - self._degraded_since >= POSTGRES_RETRY_COOLDOWN_SECONDS
        )

    async def _open_postgres(self) -> tuple[Any, Any]:
        pool = AsyncConnectionPool(
            settings.AGENT_POSTGRES_URL,
            min_size=1,
            max_size=5,
            open=False,
            check=AsyncConnectionPool.check_connection,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        )
        try:
            await pool.open(wait=True, timeout=POSTGRES_CONNECT_TIMEOUT_SECONDS)
            checkpointer = AsyncPostgresSaver(conn=pool)
            store = AsyncPostgresStore(conn=pool)
            if settings.AGENT_PERSISTENCE_AUTO_SETUP:
                await checkpointer.setup()
                await store.setup()
        except BaseException:
            await pool.close()
            raise
        self._pool = pool
        return checkpointer, store

    async def get_resources(self) -> tuple[Any, Any]:
        """Return the (checkpointer, store) pair, connecting on first use."""
        if self._checkpointer is not None and not self._should_retry_postgres():
            return self._checkpointer, self._store

        async with self._lock:
            if self._checkpointer is not None and not self._should_retry_postgres():
                return self._checkpointer, self._store

            if not self._postgres_configured():
                self._checkpointer = InMemorySaver()
                self._store = InMemoryStore()
                return self._checkpointer, self._store

            try:
                self._checkpointer, self._store = await self._open_postgres()
                if self._degraded_since is not None:
                    logger.info("Agent persistence reconnected to Postgres")
                self._degraded_since = None
            except Exception as exc:
                logger.warning(
                    "Agent Postgres unreachable (%s); using in-memory persistence, "
                    "retrying in %.0fs. Conversation memory will not be persisted.",
                    exc,
                    POSTGRES_RETRY_COOLDOWN_SECONDS,
                )
                self._degraded_since = time.monotonic()
                if self._checkpointer is None:
                    self._checkpointer = InMemorySaver()
                    self._store = InMemoryStore()

            return self._checkpointer, self._store


_PERSISTENCE = AgentPersistence()


async def get_agent_persistence() -> tuple[Any, Any]:
    """Return the process-wide (checkpointer, store) pair."""
    return await _PERSISTENCE.get_resources()
