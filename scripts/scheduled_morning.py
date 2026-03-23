"""Scheduled morning job: incremental ETL then proactive Telegram push.

Designed to be invoked by launchd (or cron). Runs two steps:
1. Incremental ETL — pull latest WHOOP + Withings data
2. Morning push  — send a health summary to Telegram via the agent

Each step is independent: if the ETL fails, the push still fires
(with slightly stale data).  Logs go to stdout/stderr for launchd
to capture.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import traceback

from dotenv import load_dotenv

# Ensure the project root is on the path so "whoopdata" is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scheduled_morning")

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")[0].strip()
MORNING_PROMPT = (
    "Good morning! Please give me a concise morning health briefing based on "
    "my latest WHOOP and Withings data. Include recovery score, sleep quality, "
    "and any notable trends or recommendations for today."
)


def run_etl() -> bool:
    """Run incremental ETL. Returns True on success."""
    logger.info("Starting incremental ETL...")
    try:
        from whoopdata.database.database import engine
        from whoopdata.models.models import Base

        Base.metadata.create_all(bind=engine)

        from whoopdata.etl import run_complete_etl

        run_complete_etl(incremental=True)
        logger.info("ETL completed successfully")
        return True
    except Exception:
        logger.error("ETL failed:\n%s", traceback.format_exc())
        return False


async def run_morning_push() -> bool:
    """Push morning summary to Telegram. Returns True on success."""
    if not TELEGRAM_CHAT_ID:
        logger.error("No TELEGRAM_ALLOWED_CHAT_IDS set — skipping push")
        return False

    logger.info("Sending morning summary to chat_id=%s", TELEGRAM_CHAT_ID)
    try:
        from whoopdata.telegram_push import push_to_telegram

        result = await push_to_telegram(
            chat_id=int(TELEGRAM_CHAT_ID),
            prompt=MORNING_PROMPT,
        )
        logger.info(
            "Morning push sent (message_id=%s): %s",
            result.telegram_message_id,
            result.assistant_message[:120],
        )
        return True
    except Exception:
        logger.error("Morning push failed:\n%s", traceback.format_exc())
        return False


def main() -> int:
    etl_ok = run_etl()
    push_ok = asyncio.run(run_morning_push())

    if etl_ok and push_ok:
        logger.info("Scheduled morning job completed successfully")
        return 0
    elif push_ok:
        logger.warning("Morning push succeeded but ETL had errors")
        return 0  # Still exit 0 — the user got their summary
    else:
        logger.error("Morning push failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
