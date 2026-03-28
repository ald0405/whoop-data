from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from whoopdata.models.models import Base, Cycle, ProactiveMessageLog, Workout, WithingsWeight
from whoopdata.services.proactive_coach import (
    ProactiveCoachConfig,
    ProactiveCoachPlanner,
    ProactiveIntent,
    ProactiveMode,
    dispatch_proactive_message,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session()


def _make_planner(db, *, now: datetime) -> ProactiveCoachPlanner:
    return ProactiveCoachPlanner(
        db,
        config=ProactiveCoachConfig(
            enabled=True,
            window_start_hour=8,
            window_end_hour=14,
            global_cooldown_hours=4,
            duplicate_cooldown_hours=24,
            morning_cooldown_hours=8,
            hidden_load_strain_threshold=10.0,
            run_gap_days=7,
            run_history_days=90,
            min_runs_for_habit_signal=3,
            weight_stale_days=7,
            escalation_delay_days=3,
        ),
        now_fn=lambda: now,
    )


@dataclass
class StubPushResult:
    assistant_message: str
    telegram_message_id: int | None


def test_hidden_load_trigger_fires_for_high_strain_with_only_walking_workouts():
    db = _make_session()
    now = datetime(2026, 3, 23, 9, 0, 0)

    db.add(
        Cycle(
            id=1,
            user_id="default_user",
            start=now - timedelta(hours=2),
            created_at=now - timedelta(hours=2),
            strain=12.4,
        )
    )
    db.add(
        Workout(
            whoop_id="walk-1",
            user_id="default_user",
            cycle_id=1,
            start=now - timedelta(hours=1),
            created_at=now - timedelta(hours=1),
            sport_id=63,
            strain=3.1,
        )
    )
    db.commit()

    decision = _make_planner(db, now=now).evaluate(mode=ProactiveMode.WINDOW, chat_id=7)

    assert decision.should_send is True
    assert decision.intent == ProactiveIntent.STRESS_CHECK_IN
    assert decision.evidence["cycle_strain"] == 12.4
    assert decision.evidence["workout_sports"] == ["Walking"]
    assert "mismatch in the data" in decision.internal_prompt


def test_running_gap_trigger_uses_activity_adherence_first():
    db = _make_session()
    now = datetime(2026, 3, 23, 10, 0, 0)

    run_days_ago = [9, 20, 35]
    for index, days_ago in enumerate(run_days_ago, start=1):
        run_at = now - timedelta(days=days_ago)
        db.add(
            Workout(
                whoop_id=f"run-{index}",
                user_id="default_user",
                start=run_at,
                created_at=run_at,
                sport_id=0,
                strain=8.0,
            )
        )
    db.commit()

    decision = _make_planner(db, now=now).evaluate(mode=ProactiveMode.WINDOW, chat_id=7)

    assert decision.should_send is True
    assert decision.intent == ProactiveIntent.ACTIVITY_ADHERENCE
    assert decision.evidence["days_since_last_run"] == 9
    assert "tiny next step" in decision.internal_prompt


def test_stale_weight_trigger_fires_when_measurement_is_old():
    db = _make_session()
    now = datetime(2026, 3, 23, 11, 0, 0)
    measured_at = now - timedelta(days=10)

    db.add(
        WithingsWeight(
            id=1,
            user_id="default_user",
            datetime=measured_at,
            weight_kg=82.4,
        )
    )
    db.commit()

    decision = _make_planner(db, now=now).evaluate(mode=ProactiveMode.WINDOW, chat_id=7)

    assert decision.should_send is True
    assert decision.intent == ProactiveIntent.MEASUREMENT_FRESHNESS
    assert decision.evidence["days_since_last_weight_measurement"] == 10
    assert "fresh weight measurement" in decision.internal_prompt


def test_repeated_gap_escalates_to_barrier_resolution():
    db = _make_session()
    now = datetime(2026, 3, 23, 12, 0, 0)

    for index, days_ago in enumerate([9, 20, 35], start=1):
        run_at = now - timedelta(days=days_ago)
        db.add(
            Workout(
                whoop_id=f"run-{index}",
                user_id="default_user",
                start=run_at,
                created_at=run_at,
                sport_id=0,
                strain=7.5,
            )
        )
    db.commit()

    planner = _make_planner(db, now=now)
    first_decision = planner.evaluate(mode=ProactiveMode.WINDOW, chat_id=7)
    planner.record_sent(
        chat_id=7,
        decision=first_decision,
        sent_at=now - timedelta(days=4),
    )

    escalated = planner.evaluate(mode=ProactiveMode.WINDOW, chat_id=7)

    assert escalated.should_send is True
    assert escalated.intent == ProactiveIntent.BARRIER_RESOLUTION
    assert "behaviour_change specialist" in escalated.internal_prompt
    assert "COM-B informed" in escalated.internal_prompt


def test_morning_mode_falls_back_to_briefing_when_no_other_trigger_fires():
    db = _make_session()
    now = datetime(2026, 3, 23, 7, 30, 0)

    decision = _make_planner(db, now=now).evaluate(mode=ProactiveMode.MORNING, chat_id=7)

    assert decision.should_send is True
    assert decision.intent == ProactiveIntent.MORNING_BRIEFING
    assert "one priority for today" in decision.internal_prompt
    assert "plain chat text" in decision.internal_prompt
    assert "Do not use markdown headings, markdown tables" in decision.internal_prompt
    assert "under 450 characters" in decision.internal_prompt


def test_dispatch_records_sent_message():
    db = _make_session()
    now = datetime(2026, 3, 23, 7, 30, 0)
    planner = _make_planner(db, now=now)

    async def _push_fn(*, chat_id: int, prompt: str):
        assert chat_id == 7
        assert "proactive Telegram coaching message" in prompt
        return StubPushResult(
            assistant_message="Morning briefing sent",
            telegram_message_id=321,
        )

    decision, result = __import__("asyncio").run(
        dispatch_proactive_message(
            planner=planner,
            chat_id=7,
            mode=ProactiveMode.MORNING,
            push_fn=_push_fn,
        )
    )

    assert decision.intent == ProactiveIntent.MORNING_BRIEFING
    assert result is not None

    logs = db.query(ProactiveMessageLog).all()
    assert len(logs) == 1
    assert logs[0].intent == ProactiveIntent.MORNING_BRIEFING
    assert logs[0].telegram_message_id == 321
