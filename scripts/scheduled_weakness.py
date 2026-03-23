"""Periodic evaluator for weekday weakness reminders."""

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
logger = logging.getLogger("scheduled_weakness")

TELEGRAM_CHAT_ID = (
    os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")[0].strip()
)


async def run_weakness_push() -> bool:
    """Evaluate and optionally send a scheduled weakness reminder."""
    if not TELEGRAM_CHAT_ID:
        logger.error(
            "No TELEGRAM_ALLOWED_CHAT_IDS set — "
            "skipping weakness reminder evaluation"
        )
        return False

    try:
        from whoopdata.database.database import SessionLocal, engine
        from whoopdata.models.models import Base
        from whoopdata.services.weakness_reminder import (
            WeaknessReminderPlanner,
            dispatch_weakness_reminder,
        )
        from whoopdata.telegram_push import push_to_telegram

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            planner = WeaknessReminderPlanner(db)
            decision, result = await dispatch_weakness_reminder(
                planner=planner,
                chat_id=int(TELEGRAM_CHAT_ID),
                push_fn=push_to_telegram,
            )
        finally:
            db.close()

        if result is None:
            logger.info("Weakness reminder skipped send: %s", decision.reason)
            return True

        logger.info(
            "Weakness reminder sent (intent=%s, message_id=%s): %s",
            decision.intent,
            result.telegram_message_id,
            result.assistant_message[:120],
        )
        return True
    except Exception:
        logger.error("Weakness reminder failed:\n%s", traceback.format_exc())
        return False


def main() -> int:
    return 0 if asyncio.run(run_weakness_push()) else 1


if __name__ == "__main__":
    sys.exit(main())
