from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from whoopdata.models.models import Base, ProactiveMessageLog


def _module():
    return importlib.import_module("whoopdata.services.weakness_reminder")


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session()


def _write_weakness_file(tmp_path: Path) -> Path:
    path = tmp_path / "weakness.md"
    path.write_text(
        "### Areas for Improvement and Growth\n"
        "\n"
        "- **Stronger storytelling that lands on business and patient "
        "value**: Keep linking platform work to business outcomes.\n"
        "- **Own outcomes more proactively**: "
        "Be bolder in defining the outcome you are driving.\n"
        "  - Nested support bullet that should be ignored\n"
        "\n"
        "---\n"
        "\n"
        "### Future Growth and Development\n"
        "\n"
        "- **Stronger cross functional partnership**: "
        "Bring ops stakeholders in earlier and communicate changes clearly.\n",
        encoding="utf-8",
    )
    return path


def _make_planner(db, *, tmp_path: Path, now: datetime):
    module = _module()
    return module.WeaknessReminderPlanner(
        db,
        weakness_file=_write_weakness_file(tmp_path),
        config=module.WeaknessReminderConfig(
            enabled=True,
            window_start_hour=9,
            window_end_hour=15,
        ),
        now_fn=lambda: now,
    )


@dataclass
class StubPushResult:
    assistant_message: str
    telegram_message_id: int | None


def test_parse_weakness_points_ignores_non_top_level_items(tmp_path):
    module = _module()

    points = module.parse_weakness_points(_write_weakness_file(tmp_path))

    assert points == [
        "**Stronger storytelling that lands on business and patient value**: "
        "Keep linking platform work to business outcomes.",
        "**Own outcomes more proactively**: "
        "Be bolder in defining the outcome you are driving.",
        "**Stronger cross functional partnership**: "
        "Bring ops stakeholders in earlier and communicate changes clearly.",
    ]


def test_weekday_evaluation_uses_stable_point_and_due_slot(tmp_path):
    module = _module()
    db = _make_session()
    now = datetime(2026, 3, 23, 14, 59, 0)
    planner = _make_planner(db, tmp_path=tmp_path, now=now)

    decision = planner.evaluate(chat_id=7)
    repeat = planner.evaluate(chat_id=7)
    target_send_at = datetime.fromisoformat(
        decision.evidence["target_send_at"]
    )

    assert decision.should_send is True
    assert decision.intent == module.WeaknessReminderIntent.WEAKNESS_REFLECTION
    assert (
        decision.evidence["selected_point"]
        == repeat.evidence["selected_point"]
    )
    assert (
        decision.evidence["target_send_at"]
        == repeat.evidence["target_send_at"]
    )
    assert target_send_at.date() == now.date()
    assert target_send_at.weekday() < 5
    assert 9 <= target_send_at.hour <= 15


def test_weekend_evaluation_skips_send(tmp_path):
    db = _make_session()
    now = datetime(2026, 3, 28, 11, 0, 0)
    planner = _make_planner(db, tmp_path=tmp_path, now=now)

    decision = planner.evaluate(chat_id=7)

    assert decision.should_send is False
    assert "weekend" in (decision.reason or "").lower()


def test_recorded_send_skips_later_attempts_on_the_same_workday(tmp_path):
    db = _make_session()
    now = datetime(2026, 3, 23, 14, 59, 0)
    planner = _make_planner(db, tmp_path=tmp_path, now=now)

    first_decision = planner.evaluate(chat_id=7)
    planner.record_sent(chat_id=7, decision=first_decision, sent_at=now)

    repeat_planner = _make_planner(
        db,
        tmp_path=tmp_path,
        now=now + timedelta(minutes=1),
    )
    repeat_decision = repeat_planner.evaluate(chat_id=7)

    assert first_decision.should_send is True
    assert repeat_decision.should_send is False
    assert "today" in (repeat_decision.reason or "").lower()


def test_internal_prompt_locks_point_and_rewording_contract(tmp_path):
    db = _make_session()
    now = datetime(2026, 3, 23, 14, 59, 0)
    planner = _make_planner(db, tmp_path=tmp_path, now=now)

    decision = planner.evaluate(chat_id=7)
    prompt = decision.internal_prompt or ""

    assert decision.evidence["selected_point"] in prompt
    assert "lightly reword" in prompt.lower()
    assert "keep the original wording" in prompt.lower()
    assert "Telegram supports basic formatting" in prompt
    assert "one point" in prompt.lower()


def test_build_preview_can_target_a_specific_top_level_point(tmp_path):
    module = _module()

    preview = module.build_preview(
        _write_weakness_file(tmp_path),
        point_number=2,
    )

    assert preview.point_number == 2
    assert "Own outcomes more proactively" in preview.point
    assert preview.point in preview.prompt


def test_dispatch_records_sent_message_for_the_selected_point(tmp_path):
    module = _module()
    db = _make_session()
    now = datetime(2026, 3, 23, 14, 59, 0)
    planner = _make_planner(db, tmp_path=tmp_path, now=now)

    async def _push_fn(*, chat_id: int, prompt: str):
        assert chat_id == 7
        assert "lightly reword" in prompt.lower()
        return StubPushResult(
            assistant_message=(
                "Keep the focus on business outcomes "
                "in the story you tell."
            ),
            telegram_message_id=222,
        )

    decision, result = asyncio.run(
        module.dispatch_weakness_reminder(
            planner=planner,
            chat_id=7,
            push_fn=_push_fn,
        )
    )

    assert decision.intent == module.WeaknessReminderIntent.WEAKNESS_REFLECTION
    assert result is not None

    logs = db.query(ProactiveMessageLog).all()
    assert len(logs) == 1
    assert logs[0].intent == module.WeaknessReminderIntent.WEAKNESS_REFLECTION
    assert logs[0].telegram_message_id == 222
