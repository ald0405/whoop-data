"""Scheduled morning job: incremental ETL then planner-driven Telegram push.

Designed to be invoked by launchd (or cron). Runs two steps:
1. Incremental ETL — pull latest WHOOP + Withings data
2. Morning push  — let the proactive planner decide the morning nudge

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
    """Push planner-driven morning message to Telegram. Returns True on success."""
    if not TELEGRAM_CHAT_ID:
        logger.error("No TELEGRAM_ALLOWED_CHAT_IDS set — skipping push")
        return False
    logger.info("Evaluating morning proactive nudge for chat_id=%s", TELEGRAM_CHAT_ID)
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
                mode=ProactiveMode.MORNING,
                push_fn=push_to_telegram,
            )
        finally:
            db.close()

        if result is None:
            logger.info("Morning planner skipped send: %s", decision.reason)
            return True
        logger.info(
            "Morning push sent (intent=%s, message_id=%s): %s",
            decision.intent,
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
