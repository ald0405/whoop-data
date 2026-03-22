from __future__ import annotations

import asyncio
from dataclasses import dataclass

from whoopdata.agent.memory_tools import manage_memory, search_memory
from whoopdata.agent.schemas import HealthContextSchema


@dataclass
class StoreItem:
    key: str
    value: dict


class FakeAsyncStore:
    def __init__(self) -> None:
        self.data: dict[tuple[str, str, str], dict[str, dict]] = {}

    async def aput(self, namespace: tuple[str, str, str], key: str, value: dict) -> None:
        self.data.setdefault(namespace, {})[key] = value

    async def asearch(
        self,
        namespace: tuple[str, str, str],
        *,
        query: str,
        limit: int,
    ) -> list[StoreItem]:
        results: list[StoreItem] = []
        for key, value in self.data.get(namespace, {}).items():
            if value.get("deleted"):
                continue
            if query.lower() in value.get("content", "").lower():
                results.append(StoreItem(key=key, value=value))
            if len(results) >= limit:
                break
        return results

    async def adelete(self, namespace: tuple[str, str, str], key: str) -> None:
        self.data.get(namespace, {}).pop(key, None)


@dataclass
class FakeRuntime:
    context: HealthContextSchema
    store: FakeAsyncStore


def test_manage_memory_create_update_delete_and_search():
    async def scenario() -> None:
        store = FakeAsyncStore()
        runtime = FakeRuntime(
            context=HealthContextSchema(user_id="telegram:1", surface="telegram"),
            store=store,
        )

        created = await manage_memory.coroutine(
            action="create",
            category="goal",
            content="Complete three strength sessions this week.",
            runtime=runtime,
        )
        assert "Created memory" in created

        memory_namespace = ("memory", "telegram:1", "goal")
        stored_items = store.data[memory_namespace]
        assert len(stored_items) == 1
        memory_id = next(iter(stored_items))

        updated = await manage_memory.coroutine(
            action="update",
            category="goal",
            memory_id=memory_id,
            content="Complete four strength sessions this week.",
            runtime=runtime,
        )
        assert "Updated memory" in updated
        assert store.data[memory_namespace][memory_id]["content"] == "Complete four strength sessions this week."

        found = await search_memory.coroutine(
            query="four strength",
            category="goal",
            runtime=runtime,
        )
        assert memory_id in found
        assert "four strength sessions" in found

        deleted = await manage_memory.coroutine(
            action="delete",
            category="goal",
            memory_id=memory_id,
            runtime=runtime,
        )
        assert "Deleted memory" in deleted
        assert store.data[memory_namespace] == {}

        not_found = await search_memory.coroutine(
            query="four strength",
            category="goal",
            runtime=runtime,
        )
        assert not_found == "No relevant memories found."

    asyncio.run(scenario())


def test_manage_memory_uses_canonical_profile_key():
    async def scenario() -> None:
        store = FakeAsyncStore()
        runtime = FakeRuntime(
            context=HealthContextSchema(user_id="api:user-1", surface="api"),
            store=store,
        )

        await manage_memory.coroutine(
            action="create",
            category="profile",
            content="Prefers direct, analytical coaching.",
            runtime=runtime,
        )

        profile_namespace = ("memory", "api:user-1", "profile")
        assert list(store.data[profile_namespace].keys()) == ["profile"]

    asyncio.run(scenario())
