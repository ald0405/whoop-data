"""Smoke test: push a proactive agent message to Telegram.

Usage:
    # Standalone — runs the full agent, needs Postgres up:
    uv run python scripts/telegram_hello.py

    # Via API — hit the running FastAPI server instead:
    uv run python scripts/telegram_hello.py --api

    # Custom prompt:
    uv run python scripts/telegram_hello.py --prompt "How did I sleep last night?"
"""

import argparse
import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")[0].strip()
DEFAULT_PROMPT = "Give me a brief morning health summary based on my latest data."
API_BASE = "http://localhost:8000"


async def push_standalone(chat_id: int, prompt: str) -> None:
    """Send directly through the agent (no FastAPI needed, but Postgres must be up)."""
    from whoopdata.telegram_push import push_to_telegram

    result = await push_to_telegram(chat_id=chat_id, prompt=prompt)
    print(f"\u2705 Pushed to chat_id={chat_id}, message_id={result.telegram_message_id}")
    print(f"Agent said: {result.assistant_message[:200]}")


async def push_via_api(chat_id: int, prompt: str) -> None:
    """Hit the running FastAPI endpoint (all servers must be up via make dev-full)."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{API_BASE}/api/v1/agent/telegram/push",
            json={"chat_id": chat_id, "prompt": prompt},
        )
        resp.raise_for_status()
        data = resp.json()
    print(
        f"\u2705 Pushed via API to chat_id={chat_id}, message_id={data.get('telegram_message_id')}"
    )
    print(f"Agent said: {data['assistant_message'][:200]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Push a proactive agent message to Telegram")
    parser.add_argument("--api", action="store_true", help="Use the running FastAPI server")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt for the agent")
    parser.add_argument("--chat-id", default=TELEGRAM_CHAT_ID, help="Telegram chat ID")
    args = parser.parse_args()

    if not args.chat_id:
        raise RuntimeError("No chat ID — set TELEGRAM_ALLOWED_CHAT_IDS in .env or pass --chat-id")

    chat_id = int(args.chat_id)

    if args.api:
        asyncio.run(push_via_api(chat_id, args.prompt))
    else:
        asyncio.run(push_standalone(chat_id, args.prompt))


if __name__ == "__main__":
    main()
