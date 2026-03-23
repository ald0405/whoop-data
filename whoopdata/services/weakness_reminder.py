"""Planner and preview helpers for weakness reminder nudges."""

from __future__ import annotations

import hashlib
import os
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from whoopdata.services.proactive_coach import (
    ProactiveDecision,
    ProactiveMessageRepository,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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


class WeaknessReminderMode:
    SCHEDULED = "weakness_scheduled"


class WeaknessReminderIntent:
    WEAKNESS_REFLECTION = "weakness_reflection_nudge"


@dataclass(frozen=True)
class WeaknessReminderConfig:
    enabled: bool = True
    window_start_hour: int = 9
    window_end_hour: int = 15

    @classmethod
    def from_env(cls) -> "WeaknessReminderConfig":
        return cls(
            enabled=_env_bool("WEAKNESS_REMINDER_ENABLED", True),
            window_start_hour=_env_int(
                "WEAKNESS_REMINDER_WINDOW_START_HOUR", 9
            ),
            window_end_hour=_env_int(
                "WEAKNESS_REMINDER_WINDOW_END_HOUR", 15
            ),
        )


@dataclass(frozen=True)
class WeaknessPreview:
    point: str
    point_number: int
    prompt: str


def default_weakness_file() -> Path:
    raw = (
        os.getenv("WEAKNESS_REMINDER_FILE", "weakness.md").strip()
        or "weakness.md"
    )
    path = Path(raw)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def parse_weakness_points(path: str | Path) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    points: list[str] = []
    current_parts: list[str] = []

    def _flush() -> None:
        if current_parts:
            points.append(" ".join(current_parts).strip())
            current_parts.clear()

    for line in lines:
        if line.startswith("- ") or line.startswith("* "):
            _flush()
            current_parts.append(line[2:].strip())
            continue

        stripped = line.strip()
        if not stripped:
            _flush()
            continue

        if line.startswith((" ", "\t")):
            if current_parts and not stripped.startswith(("- ", "* ")):
                current_parts.append(stripped)
            continue

        _flush()

    _flush()
    return [point for point in points if point]


def _stable_random(*parts: str) -> random.Random:
    seed_input = "::".join(parts).encode("utf-8")
    seed = int(hashlib.sha256(seed_input).hexdigest()[:16], 16)
    return random.Random(seed)


def _select_index_for_day(points: list[str], *, day: date) -> int:
    rng = _stable_random("weakness-point", day.isoformat())
    return rng.randrange(len(points))


def _target_send_at_for_day(
    *,
    day: date,
    config: WeaknessReminderConfig,
) -> datetime:
    start_minutes = max(0, config.window_start_hour) * 60
    end_minutes = max(start_minutes + 1, config.window_end_hour * 60)
    rng = _stable_random("weakness-send-slot", day.isoformat())
    minute_offset = rng.randrange(end_minutes - start_minutes)
    return datetime.combine(day, datetime.min.time()) + timedelta(
        minutes=start_minutes + minute_offset
    )


def _coach_name() -> str:
    return os.getenv("COACH_NAME", "Coach").strip() or "Coach"


def _build_prompt(*, point: str) -> str:
    coach_name = _coach_name()
    lines = [
        f"You are {coach_name}.",
        "Send a proactive Telegram coaching message.",
        (
            "The user did not type a new message; "
            "you are initiating the conversation."
        ),
        (
            "This reminder comes from the user's annual review "
            "and should keep one growth point salient."
        ),
        "Use exactly one point from the annual review context below.",
        (
            "Lightly reword if that makes the message feel more natural; "
            "if rewording would distort the meaning or make it complicated, "
            "keep the original wording."
        ),
        (
            "Telegram supports basic formatting. You may use a short header, "
            "bold, italics, and bullet points, plus an occasional emoji."
        ),
        (
            "Keep it concise: at most 6 short lines and under 700 characters."
        ),
        (
            "Focus on one point, one reflection, and at most one small action "
            "or one short question."
        ),
        "Annual review point:",
        point,
    ]
    return "\n".join(lines)


def build_preview(
    weakness_file: str | Path,
    *,
    day: date | None = None,
    point_number: int | None = None,
) -> WeaknessPreview:
    points = parse_weakness_points(weakness_file)
    if not points:
        raise RuntimeError("No top-level weakness reminder points found")

    if point_number is None:
        current_day = day or datetime.utcnow().date()
        index = _select_index_for_day(points, day=current_day)
    else:
        if point_number < 1 or point_number > len(points):
            raise ValueError(
                f"point_number must be between 1 and {len(points)}"
            )
        index = point_number - 1

    point = points[index]
    return WeaknessPreview(
        point=point,
        point_number=index + 1,
        prompt=_build_prompt(point=point),
    )


class WeaknessReminderPlanner:
    """Deterministic planner for weekday weakness reminders."""

    def __init__(
        self,
        db: Session,
        *,
        weakness_file: str | Path | None = None,
        config: WeaknessReminderConfig | None = None,
        now_fn: Callable[[], datetime] | None = None,
        repository: ProactiveMessageRepository | None = None,
    ) -> None:
        self.db = db
        self.weakness_file = (
            Path(weakness_file)
            if weakness_file is not None
            else default_weakness_file()
        )
        self.config = config or WeaknessReminderConfig.from_env()
        self.now_fn = now_fn or datetime.utcnow
        self.repository = repository or ProactiveMessageRepository(db)

    def evaluate(self, *, chat_id: int) -> ProactiveDecision:
        now = self.now_fn()

        if not self.config.enabled:
            return ProactiveDecision.skip(
                mode=WeaknessReminderMode.SCHEDULED,
                reason="Weakness reminder is disabled",
            )

        if now.weekday() >= 5:
            return ProactiveDecision.skip(
                mode=WeaknessReminderMode.SCHEDULED,
                reason=(
                    "Weekend — weakness reminder only runs Monday to Friday"
                ),
            )

        if not self._within_window(now):
            return ProactiveDecision.skip(
                mode=WeaknessReminderMode.SCHEDULED,
                reason="Outside configured weakness reminder window",
            )

        try:
            preview = build_preview(self.weakness_file, day=now.date())
        except FileNotFoundError:
            return ProactiveDecision.skip(
                mode=WeaknessReminderMode.SCHEDULED,
                reason=f"Weakness file not found: {self.weakness_file}",
            )
        except RuntimeError as exc:
            return ProactiveDecision.skip(
                mode=WeaknessReminderMode.SCHEDULED,
                reason=str(exc),
            )

        fingerprint = f"weakness-reflection:{now.date().isoformat()}"
        existing = self.repository.latest_for_fingerprint(
            chat_id=chat_id,
            trigger_fingerprint=fingerprint,
        )
        if existing is not None:
            return ProactiveDecision.skip(
                mode=WeaknessReminderMode.SCHEDULED,
                reason="Weakness reminder already sent today",
            )

        target_send_at = _target_send_at_for_day(
            day=now.date(),
            config=self.config,
        )
        evidence = {
            "selected_point": preview.point,
            "selected_point_number": preview.point_number,
            "target_send_at": target_send_at.isoformat(),
            "source_file": str(self.weakness_file),
        }

        if now < target_send_at:
            return ProactiveDecision.skip(
                mode=WeaknessReminderMode.SCHEDULED,
                reason="Today's weakness reminder is not due yet",
            )

        return ProactiveDecision(
            should_send=True,
            mode=WeaknessReminderMode.SCHEDULED,
            intent=WeaknessReminderIntent.WEAKNESS_REFLECTION,
            reason="Scheduled annual-review weakness reminder",
            trigger_fingerprint=fingerprint,
            evidence=evidence,
            internal_prompt=preview.prompt,
        )

    def record_sent(
        self,
        *,
        chat_id: int,
        decision: ProactiveDecision,
        telegram_message_id: int | None = None,
        sent_at: datetime | None = None,
    ):
        return self.repository.record_sent(
            chat_id=chat_id,
            decision=decision,
            telegram_message_id=telegram_message_id,
            sent_at=sent_at,
        )

    def _within_window(self, now: datetime) -> bool:
        return (
            self.config.window_start_hour
            <= now.hour
            <= self.config.window_end_hour
        )


async def dispatch_weakness_reminder(
    *,
    planner: WeaknessReminderPlanner,
    chat_id: int,
    push_fn: Callable[..., Any],
) -> tuple[ProactiveDecision, Any | None]:
    """Evaluate, optionally send, and then record a weakness reminder."""
    decision = planner.evaluate(chat_id=chat_id)
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
