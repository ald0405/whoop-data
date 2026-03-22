from __future__ import annotations

from typing import Literal
from uuid import uuid4

from langchain.tools import ToolRuntime, tool

from whoopdata.agent.schemas import HealthContextSchema

MEMORY_CATEGORIES = ("profile", "goal", "constraint", "commitment", "observation")


def _validate_category(category: str) -> str:
    normalized = category.strip().lower()
    if normalized not in MEMORY_CATEGORIES:
        valid = ", ".join(MEMORY_CATEGORIES)
        raise ValueError(f"Invalid memory category '{category}'. Valid categories: {valid}")
    return normalized


def _namespace_for(user_id: str, category: str) -> tuple[str, str, str]:
    return ("memory", user_id, category)


@tool
async def search_memory(
    query: str,
    category: str | None = None,
    limit: int = 5,
    runtime: ToolRuntime[HealthContextSchema] = None,
) -> str:
    """Search durable user memory when personalized coaching context is relevant."""
    if runtime is None or runtime.store is None:
        return "Memory store is unavailable."

    user_id = runtime.context.user_id
    categories = [_validate_category(category)] if category else list(MEMORY_CATEGORIES)
    results: list[str] = []
    seen_ids: set[str] = set()

    for resolved_category in categories:
        items = await runtime.store.asearch(
            _namespace_for(user_id, resolved_category),
            query=query,
            limit=max(1, limit),
        )
        for item in items:
            if item.key in seen_ids:
                continue
            seen_ids.add(item.key)
            value = item.value or {}
            content = value.get("content", "")
            if not content:
                continue
            results.append(f"[{resolved_category}] id={item.key}: {content}")
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    if not results:
        return "No relevant memories found."

    return "\n".join(results)


@tool
async def manage_memory(
    action: Literal["create", "update", "delete"],
    category: Literal["profile", "goal", "constraint", "commitment", "observation"],
    content: str | None = None,
    memory_id: str | None = None,
    runtime: ToolRuntime[HealthContextSchema] = None,
) -> str:
    """Create, update, or delete durable coaching memory when the user shares stable information."""
    if runtime is None or runtime.store is None:
        return "Memory store is unavailable."

    resolved_category = _validate_category(category)
    user_id = runtime.context.user_id
    namespace = _namespace_for(user_id, resolved_category)
    key = memory_id or ("profile" if resolved_category == "profile" else str(uuid4()))

    if action == "delete":
        delete_method = getattr(runtime.store, "adelete", None)
        if delete_method is not None:
            await delete_method(namespace, key)
        else:
            await runtime.store.aput(namespace, key, {"deleted": True})
        return f"Deleted memory '{key}' in category '{resolved_category}'."

    if not content:
        return "content is required for create and update actions."

    payload = {
        "category": resolved_category,
        "content": content,
        "surface": runtime.context.surface,
        "user_id": user_id,
    }
    await runtime.store.aput(namespace, key, payload)
    return f"{action.title()}d memory '{key}' in category '{resolved_category}'."
