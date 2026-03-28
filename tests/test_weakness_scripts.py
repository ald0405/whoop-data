from __future__ import annotations

import asyncio
from pathlib import Path

import scripts.scheduled_weakness as scheduled_weakness
import scripts.telegram_weakness_preview as telegram_weakness_preview
import whoopdata.database.database as database_module
import whoopdata.models.models as models_module
import whoopdata.services.proactive_coach as proactive_module
import whoopdata.services.weakness_reminder as weakness_module
import whoopdata.telegram_push as telegram_push_module


class _FakeDB:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _patch_runner_dependencies(monkeypatch, *, decision, result):
    fake_db = _FakeDB()
    monkeypatch.setattr(database_module, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(database_module, "engine", object())
    monkeypatch.setattr(
        models_module.Base.metadata,
        "create_all",
        lambda bind=None: None,
    )
    monkeypatch.setattr(
        weakness_module,
        "WeaknessReminderPlanner",
        lambda db: object(),
    )

    async def _fake_dispatch(*, planner, chat_id, push_fn):
        return decision, result

    monkeypatch.setattr(
        weakness_module,
        "dispatch_weakness_reminder",
        _fake_dispatch,
    )
    return fake_db


def test_scheduled_weakness_returns_true_when_planner_skips(monkeypatch):
    monkeypatch.setattr(scheduled_weakness, "TELEGRAM_CHAT_ID", "7")
    fake_db = _patch_runner_dependencies(
        monkeypatch,
        decision=proactive_module.ProactiveDecision.skip(
            mode=weakness_module.WeaknessReminderMode.SCHEDULED,
            reason="Not due yet",
        ),
        result=None,
    )

    assert asyncio.run(scheduled_weakness.run_weakness_push()) is True
    assert fake_db.closed is True


def test_send_preview_pushes_selected_point(monkeypatch, tmp_path):
    weakness_file = tmp_path / "weakness.md"
    weakness_file.write_text(
        "- first point\n- second point\n",
        encoding="utf-8",
    )
    preview = weakness_module.WeaknessPreview(
        point="second point",
        point_number=2,
        prompt="preview prompt",
    )
    sent: dict[str, object] = {}

    async def _fake_push(*, chat_id: int, prompt: str, **kwargs):
        _ = kwargs
        sent["chat_id"] = chat_id
        sent["prompt"] = prompt
        return type(
            "FakePushResult",
            (),
            {"assistant_message": "preview text", "telegram_message_id": 99},
        )()

    monkeypatch.setattr(
        weakness_module,
        "build_preview",
        lambda path, point_number=None: preview,
    )
    monkeypatch.setattr(telegram_push_module, "push_to_telegram", _fake_push)

    returned_preview, result = asyncio.run(
        telegram_weakness_preview.send_preview(
            chat_id=7,
            weakness_file=Path(weakness_file),
            point_number=2,
            telegram_format="plain",
        )
    )

    assert returned_preview == preview
    assert sent["chat_id"] == 7
    assert sent["prompt"] == "preview prompt"
    assert result.telegram_message_id == 99
