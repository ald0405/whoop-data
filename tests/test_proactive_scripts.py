from __future__ import annotations

import asyncio

import scripts.scheduled_etl as scheduled_etl
import scripts.scheduled_morning as scheduled_morning
import scripts.scheduled_proactive as scheduled_proactive
import whoopdata.database.database as database_module
import whoopdata.models.models as models_module
import whoopdata.services.proactive_coach as proactive_module


class _FakeDB:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _patch_runner_dependencies(monkeypatch, *, decision, result):
    fake_db = _FakeDB()
    monkeypatch.setattr(database_module, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(database_module, "engine", object())
    monkeypatch.setattr(models_module.Base.metadata, "create_all", lambda bind=None: None)
    monkeypatch.setattr(proactive_module, "ProactiveCoachPlanner", lambda db: object())

    async def _fake_dispatch(*, planner, chat_id, mode, push_fn):
        return decision, result

    monkeypatch.setattr(proactive_module, "dispatch_proactive_message", _fake_dispatch)
    return fake_db


def test_scheduled_proactive_returns_true_when_planner_skips(monkeypatch):
    monkeypatch.setattr(scheduled_proactive, "TELEGRAM_CHAT_ID", "7")
    fake_db = _patch_runner_dependencies(
        monkeypatch,
        decision=proactive_module.ProactiveDecision.skip(
            mode=proactive_module.ProactiveMode.WINDOW,
            reason="No trigger fired",
        ),
        result=None,
    )

    assert asyncio.run(scheduled_proactive.run_proactive_push()) is True
    assert fake_db.closed is True


def test_scheduled_morning_returns_true_when_planner_skips(monkeypatch):
    monkeypatch.setattr(scheduled_morning, "TELEGRAM_CHAT_ID", "7")
    fake_db = _patch_runner_dependencies(
        monkeypatch,
        decision=proactive_module.ProactiveDecision.skip(
            mode=proactive_module.ProactiveMode.MORNING,
            reason="Cooling down",
        ),
        result=None,
    )

    assert asyncio.run(scheduled_morning.run_morning_push()) is True
    assert fake_db.closed is True


def test_post_etl_hook_returns_true_when_disabled(monkeypatch):
    monkeypatch.setattr(scheduled_etl, "PROACTIVE_POST_ETL_EVALUATION", False)
    assert asyncio.run(scheduled_etl.run_post_etl_proactive_check()) is True


def test_post_etl_hook_uses_window_dispatch_when_enabled(monkeypatch):
    monkeypatch.setattr(scheduled_etl, "PROACTIVE_POST_ETL_EVALUATION", True)
    monkeypatch.setattr(scheduled_etl, "TELEGRAM_CHAT_ID", "7")
    fake_result = type(
        "FakeResult",
        (),
        {"assistant_message": "sent", "telegram_message_id": 123},
    )()
    fake_db = _patch_runner_dependencies(
        monkeypatch,
        decision=proactive_module.ProactiveDecision(
            should_send=True,
            mode=proactive_module.ProactiveMode.WINDOW,
            intent=proactive_module.ProactiveIntent.ACTIVITY_ADHERENCE,
            reason="running gap",
            trigger_fingerprint="run-gap:2026-03-10",
            evidence={"days_since_last_run": 13},
            internal_prompt="internal prompt",
        ),
        result=fake_result,
    )

    assert asyncio.run(scheduled_etl.run_post_etl_proactive_check()) is True
    assert fake_db.closed is True
