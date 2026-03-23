"""Recurring ETL job: refresh tokens if needed, then run incremental ETL.

Designed for launchd's StartInterval scheduling. The WHOOP client handles:
1. Loading the shared token file
2. Refreshing access tokens when expired and a refresh token exists
3. Persisting fresh token state back to disk

Running this every 45 minutes keeps the WHOOP token warm and the local data
store current for the API, Telegram bot, and agent workflows.
"""

from __future__ import annotations
import asyncio
import json

import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone

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
logger = logging.getLogger("scheduled_etl")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
AUDIT_LOG_PATH = os.path.join(LOGS_DIR, "etl-audit.log")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")[0].strip()
PROACTIVE_POST_ETL_EVALUATION = (
    os.getenv("PROACTIVE_POST_ETL_EVALUATION", "false").strip().lower() == "true"
)


def _build_audit_entry(
    *,
    started_at: float,
    finished_at: float,
    status: str,
    results: dict | None = None,
    error: str | None = None,
) -> dict:
    duration_seconds = round(finished_at - started_at, 3)
    per_source = {}
    total_success = 0
    total_errors = 0

    for source, stats in (results or {}).items():
        success = int(stats.get("success", 0))
        errors = int(stats.get("errors", 0))
        per_source[source] = {"success": success, "errors": errors}
        total_success += success
        total_errors += errors

    return {
        "timestamp": datetime.fromtimestamp(finished_at, tz=timezone.utc).isoformat(),
        "job": "scheduled_etl",
        "status": status,
        "duration_seconds": duration_seconds,
        "totals": {"success": total_success, "errors": total_errors},
        "sources": per_source,
        "error": error,
    }


def _append_audit_entry(entry: dict) -> None:
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as audit_log:
        audit_log.write(json.dumps(entry, sort_keys=True) + "\n")


def run_etl() -> bool:
    """Run incremental ETL and return True on success."""
    logger.info("Starting recurring incremental ETL run")
    started_at = time.time()
    try:
        from whoopdata.database.database import engine
        from whoopdata.models.models import Base

        Base.metadata.create_all(bind=engine)

        from whoopdata.etl import run_complete_etl
        results = run_complete_etl(incremental=True)
        finished_at = time.time()
        entry = _build_audit_entry(
            started_at=started_at,
            finished_at=finished_at,
            status="success",
            results=results,
        )
        _append_audit_entry(entry)
        logger.info(
            "Recurring ETL completed successfully in %.3fs (success=%s, errors=%s)",
            entry["duration_seconds"],
            entry["totals"]["success"],
            entry["totals"]["errors"],
        )
        logger.info("Recurring ETL completed successfully")
        return True
    except Exception as exc:
        finished_at = time.time()
        entry = _build_audit_entry(
            started_at=started_at,
            finished_at=finished_at,
            status="failed",
            error=str(exc),
        )
        _append_audit_entry(entry)
        logger.error("Recurring ETL failed:\n%s", traceback.format_exc())
        return False

async def run_post_etl_proactive_check() -> bool:
    """Optionally evaluate a proactive nudge immediately after ETL succeeds."""
    if not PROACTIVE_POST_ETL_EVALUATION:
        logger.info("Post-ETL proactive evaluation disabled")
        return True

    if not TELEGRAM_CHAT_ID:
        logger.warning("No TELEGRAM_ALLOWED_CHAT_IDS set — skipping post-ETL proactive evaluation")
        return True

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
            logger.info("Post-ETL proactive evaluation skipped send: %s", decision.reason)
            return True

        logger.info(
            "Post-ETL proactive push sent (intent=%s, message_id=%s): %s",
            decision.intent,
            result.telegram_message_id,
            result.assistant_message[:120],
        )
        return True
    except Exception:
        logger.error("Post-ETL proactive evaluation failed:\n%s", traceback.format_exc())
        return False


def main() -> int:
    etl_ok = run_etl()
    proactive_ok = True
    if etl_ok:
        proactive_ok = asyncio.run(run_post_etl_proactive_check())

    if etl_ok:
        if not proactive_ok:
            logger.warning("Recurring ETL succeeded but post-ETL proactive evaluation failed")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
