"""Smoke test: push a weakness reminder preview to Telegram."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure the project root is on the path so "whoopdata" is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

load_dotenv()

TELEGRAM_CHAT_ID = (
    os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")[0].strip()
)
DEFAULT_WEAKNESS_FILE = (
    os.getenv("WEAKNESS_REMINDER_FILE", "weakness.md").strip()
    or "weakness.md"
)


async def send_preview(
    *,
    chat_id: int,
    weakness_file: str | Path = DEFAULT_WEAKNESS_FILE,
    point_number: int | None = None,
    telegram_format: str | None = None,
):
    """Send a manual weakness reminder preview without recording state."""
    from whoopdata.services.weakness_reminder import build_preview
    from whoopdata.telegram_push import push_to_telegram

    preview = build_preview(weakness_file, point_number=point_number)
    result = await push_to_telegram(
        chat_id=chat_id,
        prompt=preview.prompt,
        telegram_format=telegram_format,
    )
    return preview, result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push a weakness reminder preview to Telegram"
    )
    parser.add_argument(
        "--chat-id",
        default=TELEGRAM_CHAT_ID,
        help="Telegram chat ID",
    )
    parser.add_argument(
        "--point-number",
        type=int,
        default=None,
        help="Optional 1-based top-level bullet number from weakness.md",
    )
    parser.add_argument(
        "--weakness-file",
        default=DEFAULT_WEAKNESS_FILE,
        help="Path to the private weakness markdown file",
    )
    parser.add_argument(
        "--format",
        default=None,
        choices=["plain", "html"],
        help=(
            "Telegram formatting to use for this preview. "
            "Defaults to TELEGRAM_PROACTIVE_FORMAT or plain."
        ),
    )
    args = parser.parse_args()

    if not args.chat_id:
        raise RuntimeError(
            "No chat ID — set TELEGRAM_ALLOWED_CHAT_IDS in .env "
            "or pass --chat-id"
        )

    chat_id = int(args.chat_id)
    preview, result = asyncio.run(
        send_preview(
            chat_id=chat_id,
            weakness_file=args.weakness_file,
            point_number=args.point_number,
            telegram_format=args.format,
        )
    )
    print(
        "✅ Pushed weakness preview to "
        f"chat_id={chat_id}, message_id={result.telegram_message_id}"
    )
    print(f"Point {preview.point_number}: {preview.point}")
    print(f"Agent said: {result.assistant_message[:200]}")


if __name__ == "__main__":
    main()
