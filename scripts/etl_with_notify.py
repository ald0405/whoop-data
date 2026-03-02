#!/usr/bin/env python3
"""Run the ETL pipeline and notify your active LangGraph Studio thread.

Workflow:
  - Terminal 1: make langgraph-dev  (chat in Studio)
  - Terminal 2: make etl-notify     (runs ETL, then posts summary to Studio)

Usage: uv run python scripts/etl_with_notify.py [--full]
"""

import asyncio
import sys

import httpx
from langgraph_sdk import get_client

DEPLOYMENT_URL = "http://127.0.0.1:2024"
ASSISTANT_ID = "health_agent"


async def notify_studio(message: str):
    """Send a message to the most recent active thread in Studio."""
    # Check if server is running
    try:
        async with httpx.AsyncClient() as http:
            r = await http.get(f"{DEPLOYMENT_URL}/ok")
            if r.status_code != 200:
                print("⚠️  LangGraph server not healthy, skipping notification.")
                return
    except httpx.ConnectError:
        print("⚠️  LangGraph server not running, skipping notification.")
        return

    client = get_client(url=DEPLOYMENT_URL)

    # Find the most recent thread
    threads = await client.threads.search()
    if not threads:
        print("⚠️  No threads found in Studio, skipping notification.")
        return

    latest = sorted(threads, key=lambda t: t["created_at"], reverse=True)[0]
    thread_id = latest["thread_id"]
    print(f"📨 Notifying thread: {thread_id}")

    await client.runs.create(
        thread_id,
        ASSISTANT_ID,
        input={
            "messages": [
                {
                    "role": "assistant",
                    "content": message,
                }
            ]
        },
    )
    print("✅ Notification sent to Studio!")


def run_etl(incremental: bool = True) -> dict:
    """Run the ETL pipeline and return results."""
    from whoopdata.database.database import engine
    from whoopdata.models.models import Base

    Base.metadata.create_all(bind=engine)

    from whoopdata.etl import run_complete_etl

    return run_complete_etl(incremental=incremental)


def build_summary(results: dict) -> str:
    """Build a human-readable ETL summary message."""
    total_success = sum(r["success"] for r in results.values())
    total_errors = sum(r["errors"] for r in results.values())

    lines = ["📊 **ETL Pipeline Complete!**", ""]

    for source, stats in results.items():
        name = source.replace("_", " ").title()
        status = "✅" if stats["errors"] == 0 else "⚠️"
        lines.append(f"{status} {name}: {stats['success']} rows loaded")

    lines.append("")
    lines.append(
        f"**Total: {total_success} rows extracted successfully"
        f"{f', {total_errors} errors' if total_errors else ''}.**"
    )

    return "\n".join(lines)


async def main():
    incremental = "--full" not in sys.argv

    mode = "incremental" if incremental else "full"
    print(f"🚀 Running ETL pipeline ({mode} load)...\n")

    results = run_etl(incremental=incremental)

    if results:
        summary = build_summary(results)
        print(f"\n{summary}\n")
        await notify_studio(summary)
    else:
        print("❌ ETL returned no results.")


if __name__ == "__main__":
    asyncio.run(main())
