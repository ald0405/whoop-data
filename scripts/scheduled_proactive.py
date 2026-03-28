"""Periodic proactive evaluator for in-window JITAI nudges.

Designed to be invoked by launchd on a fixed interval. The script itself
enforces the configured proactive window and only sends when the planner
finds a trigger that survives cooldown checks.
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
logger = logging.getLogger("scheduled_proactive")

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")[0].strip()


async def run_proactive_push() -> bool:
    """Evaluate and optionally send an in-window proactive nudge."""
    if not TELEGRAM_CHAT_ID:
        logger.error("No TELEGRAM_ALLOWED_CHAT_IDS set — skipping proactive evaluation")
        return False

    try:
        from whoopdata.database.database import SessionLocal, engine
        from whoopdata.models.models import Base
        from whoopdata.services.proactive_coach import (
            ProactiveCoachPlanner,
            ProactiveMode,
            dispatch_proactive_message,
        )
        from whoopdata.telegram_push import push_to_telegram

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            planner = ProactiveCoachPlanner(db)
            decision, result = await dispatch_proactive_message(
                planner=planner,
                chat_id=int(TELEGRAM_CHAT_ID),
                mode=ProactiveMode.WINDOW,
                push_fn=push_to_telegram,
            )
        finally:
            db.close()

        if result is None:
            logger.info("Window evaluator skipped send: %s", decision.reason)
            return True

        logger.info(
            "Proactive push sent (intent=%s, message_id=%s): %s",
            decision.intent,
            result.telegram_message_id,
            result.assistant_message[:120],
        )
        return True
    except Exception:
        logger.error("Proactive push failed:\n%s", traceback.format_exc())
        return False


def main() -> int:
    return 0 if asyncio.run(run_proactive_push()) else 1


if __name__ == "__main__":
    sys.exit(main())
