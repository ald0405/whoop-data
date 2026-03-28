"""Planner and dispatcher for proactive coaching nudges."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from whoopdata.models.models import Cycle, ProactiveMessageLog, Workout, WithingsWeight
from whoopdata.utils.sport_mapping import get_sport_name

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class ProactiveMode:
    MORNING = "morning"
    WINDOW = "window"


class ProactiveIntent:
    MORNING_BRIEFING = "morning_briefing"
    STRESS_CHECK_IN = "stress_hidden_load_check_in"
    ACTIVITY_ADHERENCE = "activity_adherence_nudge"
    MEASUREMENT_FRESHNESS = "measurement_freshness_reminder"
    BARRIER_RESOLUTION = "barrier_resolution_coaching"


@dataclass(frozen=True)
class ProactiveCoachConfig:
    enabled: bool = True
    window_start_hour: int = 8
    window_end_hour: int = 14
    global_cooldown_hours: int = 4
    duplicate_cooldown_hours: int = 24
    morning_cooldown_hours: int = 8
    hidden_load_strain_threshold: float = 10.0
    run_gap_days: int = 7
    run_history_days: int = 90
    min_runs_for_habit_signal: int = 3
    weight_stale_days: int = 7
    escalation_delay_days: int = 3

    @classmethod
    def from_env(cls) -> "ProactiveCoachConfig":
        return cls(
            enabled=_env_bool("PROACTIVE_COACH_ENABLED", True),
            window_start_hour=_env_int("PROACTIVE_WINDOW_START_HOUR", 8),
            window_end_hour=_env_int("PROACTIVE_WINDOW_END_HOUR", 14),
            global_cooldown_hours=_env_int("PROACTIVE_GLOBAL_COOLDOWN_HOURS", 4),
            duplicate_cooldown_hours=_env_int("PROACTIVE_DUPLICATE_COOLDOWN_HOURS", 24),
            morning_cooldown_hours=_env_int("PROACTIVE_MORNING_COOLDOWN_HOURS", 8),
            hidden_load_strain_threshold=_env_float("PROACTIVE_HIDDEN_LOAD_STRAIN_THRESHOLD", 10.0),
            run_gap_days=_env_int("PROACTIVE_RUN_GAP_DAYS", 7),
            run_history_days=_env_int("PROACTIVE_RUN_HISTORY_DAYS", 90),
            min_runs_for_habit_signal=_env_int("PROACTIVE_MIN_RUNS_FOR_HABIT_SIGNAL", 3),
            weight_stale_days=_env_int("PROACTIVE_WEIGHT_STALE_DAYS", 7),
            escalation_delay_days=_env_int("PROACTIVE_ESCALATION_DELAY_DAYS", 3),
        )


@dataclass(frozen=True)
class ProactiveDecision:
    should_send: bool
    mode: str
    intent: str | None = None
    reason: str | None = None
    trigger_fingerprint: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    internal_prompt: str | None = None

    @classmethod
    def skip(cls, *, mode: str, reason: str) -> "ProactiveDecision":
        return cls(should_send=False, mode=mode, reason=reason)


class ProactiveMessageRepository:
    """Persistence helper for proactive message cooldowns and escalation."""

    def __init__(self, db: Session):
        self.db = db

    def has_recent_event(self, *, chat_id: int, since: datetime) -> bool:
        return (
            self.db.query(ProactiveMessageLog)
            .filter(ProactiveMessageLog.chat_id == chat_id, ProactiveMessageLog.sent_at >= since)
            .first()
            is not None
        )

    def latest_for_intent(self, *, chat_id: int, intent: str) -> ProactiveMessageLog | None:
        return (
            self.db.query(ProactiveMessageLog)
            .filter(ProactiveMessageLog.chat_id == chat_id, ProactiveMessageLog.intent == intent)
            .order_by(ProactiveMessageLog.sent_at.desc())
            .first()
        )

    def latest_for_fingerprint(
        self,
        *,
        chat_id: int,
        trigger_fingerprint: str,
    ) -> ProactiveMessageLog | None:
        return (
            self.db.query(ProactiveMessageLog)
            .filter(
                ProactiveMessageLog.chat_id == chat_id,
                ProactiveMessageLog.trigger_fingerprint == trigger_fingerprint,
            )
            .order_by(ProactiveMessageLog.sent_at.desc())
            .first()
        )

    def record_sent(
        self,
        *,
        chat_id: int,
        decision: ProactiveDecision,
        telegram_message_id: int | None = None,
        sent_at: datetime | None = None,
    ) -> ProactiveMessageLog:
        record = ProactiveMessageLog(
            chat_id=chat_id,
            mode=decision.mode,
            intent=decision.intent or "unknown",
            trigger_fingerprint=decision.trigger_fingerprint,
            reason=decision.reason,
            evidence_json=json.dumps(decision.evidence, sort_keys=True, default=str),
            prompt=decision.internal_prompt or "",
            telegram_message_id=telegram_message_id,
            sent_at=sent_at or datetime.utcnow(),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record


class ProactiveCoachPlanner:
    """Deterministic planner for proactive coaching nudges."""

    def __init__(
        self,
        db: Session,
        *,
        config: ProactiveCoachConfig | None = None,
        now_fn: Callable[[], datetime] | None = None,
        repository: ProactiveMessageRepository | None = None,
    ) -> None:
        self.db = db
        self.config = config or ProactiveCoachConfig.from_env()
        self.now_fn = now_fn or datetime.utcnow
        self.repository = repository or ProactiveMessageRepository(db)

    def evaluate(self, *, mode: str, chat_id: int) -> ProactiveDecision:
        now = self.now_fn()

        if not self.config.enabled:
            return ProactiveDecision.skip(mode=mode, reason="Proactive coaching is disabled")

        if mode == ProactiveMode.WINDOW and not self._within_window(now):
            return ProactiveDecision.skip(mode=mode, reason="Outside configured proactive window")

        if self.repository.has_recent_event(
            chat_id=chat_id,
            since=now - timedelta(hours=self.config.global_cooldown_hours),
        ):
            return ProactiveDecision.skip(
                mode=mode, reason="Recent proactive message still cooling down"
            )

        for builder in (
            self._build_hidden_load_decision,
            self._build_run_gap_decision,
            self._build_weight_stale_decision,
        ):
            decision = builder(chat_id=chat_id, now=now, mode=mode)
            if decision is not None:
                return decision

        if mode == ProactiveMode.MORNING:
            latest_morning = self.repository.latest_for_intent(
                chat_id=chat_id,
                intent=ProactiveIntent.MORNING_BRIEFING,
            )
            if latest_morning and latest_morning.sent_at >= now - timedelta(
                hours=self.config.morning_cooldown_hours
            ):
                return ProactiveDecision.skip(
                    mode=mode,
                    reason="Recent morning briefing still cooling down",
                )
            return self._build_morning_briefing(now=now, mode=mode)

        return ProactiveDecision.skip(mode=mode, reason="No proactive trigger fired")

    def record_sent(
        self,
        *,
        chat_id: int,
        decision: ProactiveDecision,
        telegram_message_id: int | None = None,
        sent_at: datetime | None = None,
    ) -> ProactiveMessageLog:
        return self.repository.record_sent(
            chat_id=chat_id,
            decision=decision,
            telegram_message_id=telegram_message_id,
            sent_at=sent_at,
        )

    @staticmethod
    def default_chat_id() -> int | None:
        raw = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")[0].strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def _within_window(self, now: datetime) -> bool:
        return self.config.window_start_hour <= now.hour <= self.config.window_end_hour

    def _build_morning_briefing(self, *, now: datetime, mode: str) -> ProactiveDecision:
        evidence = {
            "generated_at": now.isoformat(),
            "mode": mode,
        }

        # Add persisted actionability thresholds when available so the message can
        # say "keep strain under X and bedtime before Y".
        try:
            from whoopdata.analytics.results_loader import results_loader

            actionability = results_loader.load_result("recovery_actionability", days_back=365)
            if actionability and isinstance(actionability, dict):
                best = actionability.get("best_thresholds") or {}
                strain_max = best.get("strain_3d_sum_max")
                bedtime_before = best.get("bedtime_before")
                if strain_max is not None or bedtime_before:
                    evidence["recovery_actionability"] = {
                        "strain_3d_sum_max": strain_max,
                        "bedtime_before": bedtime_before,
                    }
        except Exception:
            pass
        return ProactiveDecision(
            should_send=True,
            mode=mode,
            intent=ProactiveIntent.MORNING_BRIEFING,
            reason="Scheduled morning briefing",
            trigger_fingerprint=f"morning:{now.date().isoformat()}",
            evidence=evidence,
            internal_prompt=self._build_internal_prompt(
                intent=ProactiveIntent.MORNING_BRIEFING,
                evidence=evidence,
                ux_contract=(
                    "Start with a short state summary based on the latest WHOOP and Withings data.",
                    "Give exactly one priority for today.",
                    "Optionally ask one short follow-up question.",
                    "Keep the message concise and grounded in the latest data.",
                ),
            ),
        )

    def _build_hidden_load_decision(
        self,
        *,
        chat_id: int,
        now: datetime,
        mode: str,
    ) -> ProactiveDecision | None:
        latest_cycle = (
            self.db.query(Cycle).order_by(Cycle.start.desc(), Cycle.created_at.desc()).first()
        )
        if latest_cycle is None or latest_cycle.strain is None:
            return None
        if latest_cycle.strain <= self.config.hidden_load_strain_threshold:
            return None

        workouts = (
            self.db.query(Workout)
            .filter(Workout.cycle_id == latest_cycle.id)
            .order_by(Workout.start.desc(), Workout.created_at.desc())
            .all()
        )
        workout_sports = [get_sport_name(workout.sport_id) for workout in workouts]
        if workouts and not all(workout.sport_id == 63 for workout in workouts):
            return None

        cycle_anchor = latest_cycle.start or latest_cycle.created_at or now
        fingerprint = f"hidden-load:{cycle_anchor.date().isoformat()}"
        latest_event = self.repository.latest_for_fingerprint(
            chat_id=chat_id,
            trigger_fingerprint=fingerprint,
        )
        if latest_event and latest_event.sent_at >= now - timedelta(
            hours=self.config.duplicate_cooldown_hours
        ):
            return None

        reason = (
            "High daily strain with only walking workouts suggests hidden load or stress"
            if workouts
            else "High daily strain without a matching workout suggests hidden load or stress"
        )
        evidence = {
            "cycle_date": cycle_anchor.date().isoformat(),
            "cycle_strain": round(float(latest_cycle.strain), 2),
            "workout_count_for_cycle": len(workouts),
            "workout_sports": workout_sports,
        }
        return ProactiveDecision(
            should_send=True,
            mode=mode,
            intent=ProactiveIntent.STRESS_CHECK_IN,
            reason=reason,
            trigger_fingerprint=fingerprint,
            evidence=evidence,
            internal_prompt=self._build_internal_prompt(
                intent=ProactiveIntent.STRESS_CHECK_IN,
                evidence=evidence,
                ux_contract=(
                    "Explicitly name the mismatch in the data.",
                    "Validate that non-exercise stress or hidden load may explain it.",
                    "Ask one short check-in question.",
                    "Offer one or two low-friction recovery options.",
                    "Keep it concise and avoid sounding alarmist.",
                ),
            ),
        )

    def _build_run_gap_decision(
        self,
        *,
        chat_id: int,
        now: datetime,
        mode: str,
    ) -> ProactiveDecision | None:
        history_cutoff = now - timedelta(days=self.config.run_history_days)
        run_history_count = (
            self.db.query(Workout)
            .filter(
                Workout.sport_id == 0,
                Workout.start.isnot(None),
                Workout.start >= history_cutoff,
            )
            .count()
        )
        if run_history_count < self.config.min_runs_for_habit_signal:
            return None

        last_run = (
            self.db.query(Workout)
            .filter(Workout.sport_id == 0, Workout.start.isnot(None))
            .order_by(Workout.start.desc())
            .first()
        )
        if last_run is None or last_run.start is None:
            return None

        days_since_last_run = (now.date() - last_run.start.date()).days
        if days_since_last_run < self.config.run_gap_days:
            return None

        fingerprint = f"run-gap:{last_run.start.date().isoformat()}"
        latest_event = self.repository.latest_for_fingerprint(
            chat_id=chat_id,
            trigger_fingerprint=fingerprint,
        )
        if latest_event and latest_event.sent_at >= now - timedelta(
            hours=self.config.duplicate_cooldown_hours
        ):
            return None

        escalating = bool(
            latest_event
            and latest_event.sent_at <= now - timedelta(days=self.config.escalation_delay_days)
        )
        intent = (
            ProactiveIntent.BARRIER_RESOLUTION if escalating else ProactiveIntent.ACTIVITY_ADHERENCE
        )
        reason = (
            "Running gap persists after an earlier reminder"
            if escalating
            else "Running habit appears to have gone quiet"
        )
        evidence = {
            "days_since_last_run": days_since_last_run,
            "last_run_at": last_run.start.isoformat(),
            "run_history_days": self.config.run_history_days,
            "recent_run_history_count": run_history_count,
            "target_behaviour": "running",
        }
        return ProactiveDecision(
            should_send=True,
            mode=mode,
            intent=intent,
            reason=reason,
            trigger_fingerprint=fingerprint,
            evidence=evidence,
            internal_prompt=self._build_internal_prompt(
                intent=intent,
                evidence=evidence,
                ux_contract=self._ux_contract_for_running(intent=intent),
            ),
        )

    def _build_weight_stale_decision(
        self,
        *,
        chat_id: int,
        now: datetime,
        mode: str,
    ) -> ProactiveDecision | None:
        latest_weight = (
            self.db.query(WithingsWeight)
            .filter(WithingsWeight.weight_kg.isnot(None), WithingsWeight.datetime.isnot(None))
            .order_by(WithingsWeight.datetime.desc())
            .first()
        )
        if latest_weight is None or latest_weight.datetime is None:
            return None

        days_since_weight = (now.date() - latest_weight.datetime.date()).days
        if days_since_weight < self.config.weight_stale_days:
            return None

        fingerprint = f"weight-stale:{latest_weight.datetime.date().isoformat()}"
        latest_event = self.repository.latest_for_fingerprint(
            chat_id=chat_id,
            trigger_fingerprint=fingerprint,
        )
        if latest_event and latest_event.sent_at >= now - timedelta(
            hours=self.config.duplicate_cooldown_hours
        ):
            return None

        escalating = bool(
            latest_event
            and latest_event.sent_at <= now - timedelta(days=self.config.escalation_delay_days)
        )
        intent = (
            ProactiveIntent.BARRIER_RESOLUTION
            if escalating
            else ProactiveIntent.MEASUREMENT_FRESHNESS
        )
        reason = (
            "Weight-measurement gap persists after an earlier reminder"
            if escalating
            else "Withings weight data has gone stale"
        )
        evidence = {
            "days_since_last_weight_measurement": days_since_weight,
            "last_weight_at": latest_weight.datetime.isoformat(),
            "target_behaviour": "capture a fresh Withings weight measurement",
        }
        return ProactiveDecision(
            should_send=True,
            mode=mode,
            intent=intent,
            reason=reason,
            trigger_fingerprint=fingerprint,
            evidence=evidence,
            internal_prompt=self._build_internal_prompt(
                intent=intent,
                evidence=evidence,
                ux_contract=self._ux_contract_for_weight(intent=intent),
            ),
        )

    @staticmethod
    def _ux_contract_for_running(*, intent: str) -> tuple[str, ...]:
        if intent == ProactiveIntent.BARRIER_RESOLUTION:
            return (
                "Acknowledge that the same running gap is still unresolved.",
                "Use the behaviour_change specialist for a COM-B informed response before replying.",
                "Frame the likely blocker, then give one micro-action, two or three options, one barrier-buster, and one follow-up question.",
                "Do not repeat the earlier reminder verbatim.",
            )
        return (
            "Remind the user of the running habit or goal without sounding punitive.",
            "State the gap plainly and suggest one tiny next step or a reschedule option.",
            "Ask at most one short follow-up question.",
            "Keep the message concise and action-oriented.",
        )

    @staticmethod
    def _ux_contract_for_weight(*, intent: str) -> tuple[str, ...]:
        if intent == ProactiveIntent.BARRIER_RESOLUTION:
            return (
                "Treat this as a recurring measurement gap, not a one-off reminder.",
                "Use the behaviour_change specialist for a COM-B informed response before replying.",
                "Frame the likely blocker, then give one micro-action, two or three options, one barrier-buster, and one follow-up question.",
                "Keep the tone practical and low-friction.",
            )
        return (
            "Explain briefly why a fresh weight measurement would help.",
            "Suggest the easiest moment to do it today.",
            "Ask for only one simple action.",
            "Keep the message concise and practical.",
        )

    @staticmethod
    def _build_internal_prompt(
        *,
        intent: str,
        evidence: dict[str, Any],
        ux_contract: tuple[str, ...],
    ) -> str:
        lines = [
            "You are sending a proactive Telegram coaching message.",
            "The user did not type a new message; you are initiating the conversation.",
            f"Intent: {intent}",
            "Ground the reply in the evidence below.",
            "Write for Telegram as plain chat text, not an email, memo, or report.",
            "Do not use markdown headings, markdown tables, or multi-section templates.",
            "Use at most 4 short lines and keep the final message under 450 characters.",
            "Keep the message concise, personalised, evidence-linked, and limited to one primary action request.",
            "Ask at most one follow-up question.",
            "If relevant, search memory or use the appropriate specialist before drafting the final reply.",
        ]
        if intent == ProactiveIntent.BARRIER_RESOLUTION:
            lines.append(
                "IMPORTANT: Use the behaviour_change specialist so the reply is COM-B informed and helps the user overcome likely blockers."
            )
        lines.append("UX contract:")
        lines.extend(f"- {rule}" for rule in ux_contract)
        lines.append("Evidence:")
        lines.append(json.dumps(evidence, indent=2, sort_keys=True, default=str))
        return "\n".join(lines)


async def dispatch_proactive_message(
    *,
    planner: ProactiveCoachPlanner,
    chat_id: int,
    mode: str,
    push_fn: Callable[..., Any],
) -> tuple[ProactiveDecision, Any | None]:
    """Evaluate a proactive decision, send it if needed, and record the send."""
    decision = planner.evaluate(mode=mode, chat_id=chat_id)
    if not decision.should_send or not decision.internal_prompt:
        return decision, None

    result = await push_fn(
        chat_id=chat_id,
        prompt=decision.internal_prompt,
    )
    planner.record_sent(
        chat_id=chat_id,
        decision=decision,
        telegram_message_id=result.telegram_message_id,
    )
    return decision, result
