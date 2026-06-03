"""Phase-keyed reference angle bands for tennis groundstroke analysis.

Single source of truth for the reference angles used by BOTH the visual
overlay (``pose_overlay.draw_form_diff``) and the LLM prompt text
(``pose_analysis.AggregatedMetrics.format_for_prompt``). Previously these
lived in two places (``telegram_bot._REFERENCE_ANGLES`` and the prompt
markdown) and could diverge.

Design notes (read before changing the numbers):

- **Bands, not points.** Joint angles vary with grip and stroke style
  (e.g. forehand contact elbow flexion is ~130 deg with an Eastern grip vs
  ~100 deg with a Western grip [PMC3761830]). A point target would flag
  correct technique as a fault, so each entry is a ``(min, max)`` band.
- **2D side-on measurability.** Single-camera markerless pose is reliable for
  *camera-side, in-plane flexion* (elbow, knee) but unreliable for the
  occluded far side (~2x error) and for *rotations* (shoulder-hip separation,
  shoulder internal/external rotation) [PLoS One PMC10635560]. We therefore
  only grade in-plane flexion here; rotation faults are left to qualitative
  LLM comment and are NOT encoded as measured bands.
- **Contact frame is approximate.** Ball contact lasts ~5 ms; at 30 fps a
  frame is 33 ms, so the captured "contact" frame is near-impact, not impact.
  Contact bands are deliberately widened to absorb this.
- **PROVISIONAL — flagged for SME review.** Forehand is anchored to the
  literature above; backhand joint angles are barely quantified in the
  literature (only separation angle, a rotation we cannot measure), so
  backhand grades fewer joints with wider bands and lower confidence.

Joint-name convention matches ``pose_analysis.JOINT_ANGLES``: ``*_flexion``
is the interior joint angle (180 deg = straight limb, lower = more bent);
``*_shoulder_elevation`` is the hip-shoulder-elbow angle (higher = arm raised).

Sources:
    - Forehand review: https://pmc.ncbi.nlm.nih.gov/articles/PMC3761830/
    - Backhand kinematics: https://pmc.ncbi.nlm.nih.gov/articles/PMC3588639/
    - 2D markerless validity: https://pmc.ncbi.nlm.nih.gov/articles/PMC10635560/
"""

from __future__ import annotations

Band = tuple[float, float]

# Ordered groundstroke phase labels (also used by pose_analysis.segment_stroke_phases).
PHASE_LABELS: tuple[str, ...] = (
    "preparation",
    "backswing",
    "forward_swing",
    "contact",
    "follow_through",
)

GROUNDSTROKE_ACTIVITIES: frozenset[str] = frozenset(
    {"forehand", "backhand", "groundstroke", "swing", "tennis"}
)

# Right-handed reference bands, by activity -> phase -> joint -> (min, max) | None.
# ``None`` means "not graded for this phase" (e.g. trunk_tilt, whose
# shoulder-hip-knee definition is ambiguous from a single 2D view).
# Values are mirrored to the left side by ``get_phase_reference``.
_FOREHAND: dict[str, dict[str, Band | None]] = {
    # confidence: low — settle before the backswing
    "preparation": {
        "right_elbow_flexion": (90.0, 150.0),
        "right_shoulder_elevation": (20.0, 60.0),
        "right_knee_flexion": (140.0, 170.0),
        "trunk_tilt": None,
    },
    # confidence: medium — loading; meaningful knee bend, racket taken back
    "backswing": {
        "right_elbow_flexion": (90.0, 140.0),
        "right_shoulder_elevation": (30.0, 80.0),
        "right_knee_flexion": (120.0, 155.0),
        "trunk_tilt": None,
    },
    # confidence: low — interpolated rising swing
    "forward_swing": {
        "right_elbow_flexion": (90.0, 140.0),
        "right_shoulder_elevation": (60.0, 110.0),
        "right_knee_flexion": (130.0, 165.0),
        "trunk_tilt": None,
    },
    # confidence: high (elbow) — grip-dependent 100–130 deg [PMC3761830]
    "contact": {
        "right_elbow_flexion": (100.0, 130.0),
        "right_shoulder_elevation": (80.0, 130.0),
        "right_knee_flexion": (140.0, 175.0),
        "trunk_tilt": None,
    },
    # confidence: low — arm folds across the body, leg extended
    "follow_through": {
        "right_elbow_flexion": (40.0, 100.0),
        "right_shoulder_elevation": (90.0, 140.0),
        "right_knee_flexion": (150.0, 180.0),
        "trunk_tilt": None,
    },
}

# Backhand: low confidence throughout (literature is thin). One- vs two-handed
# cannot be distinguished from pose alone, so elbow bands are wide.
_BACKHAND: dict[str, dict[str, Band | None]] = {
    "preparation": {
        "right_elbow_flexion": (80.0, 150.0),
        "right_knee_flexion": (140.0, 170.0),
        "trunk_tilt": None,
    },
    "backswing": {
        "right_elbow_flexion": (70.0, 140.0),
        "right_knee_flexion": (120.0, 155.0),
        "trunk_tilt": None,
    },
    "forward_swing": {
        "right_elbow_flexion": (90.0, 160.0),
        "right_knee_flexion": (130.0, 165.0),
        "trunk_tilt": None,
    },
    "contact": {
        "right_elbow_flexion": (120.0, 175.0),
        "right_knee_flexion": (140.0, 175.0),
        "trunk_tilt": None,
    },
    "follow_through": {
        "right_elbow_flexion": (90.0, 175.0),
        "right_knee_flexion": (150.0, 180.0),
        "trunk_tilt": None,
    },
}

GROUNDSTROKE_REFERENCE: dict[str, dict[str, dict[str, Band | None]]] = {
    "forehand": _FOREHAND,
    "backhand": _BACKHAND,
    # Generic tennis / swing fall back to forehand bands (most common stroke).
    "swing": _FOREHAND,
    "groundstroke": _FOREHAND,
    "tennis": _FOREHAND,
}


def _resolve_activity(activity: str) -> str | None:
    """Map a free-text caption/activity to a known groundstroke key.

    Args:
        activity: Caption text or activity label (any case).

    Returns:
        A key into ``GROUNDSTROKE_REFERENCE``, or ``None`` for non-groundstroke
        activities (serve, squat, etc.).
    """
    text = (activity or "").strip().lower()
    if not text:
        return None
    # Most specific first so "forehand" wins over "tennis".
    for key in ("forehand", "backhand", "groundstroke", "swing", "tennis"):
        if key in text:
            return key
    return None


def get_phase_reference(activity: str, phase_label: str) -> dict[str, Band | None]:
    """Resolve reference angle bands for an activity + stroke phase.

    Fills both ``left_*`` and ``right_*`` joint keys from the tracked-arm
    (right-handed reference) value so both sides resolve during overlay.

    Args:
        activity: Caption/activity text (e.g. ``"analyse my forehand"``).
        phase_label: One of ``PHASE_LABELS``; unknown phases fall back to
            ``"contact"``.

    Returns:
        Mapping of joint name to ``(min, max)`` band or ``None``. Empty dict
        for non-groundstroke activities.

    Example:
        >>> band = get_phase_reference("forehand", "contact")["right_elbow_flexion"]
        >>> band
        (100.0, 130.0)
    """
    key = _resolve_activity(activity)
    if key is None:
        return {}
    phases = GROUNDSTROKE_REFERENCE[key]
    phase = phases.get(phase_label) or phases.get("contact", {})

    resolved: dict[str, Band | None] = {}
    for joint, band in phase.items():
        resolved[joint] = band
        # Mirror right_* -> left_* (and vice versa) so both sides are graded.
        if joint.startswith("right_"):
            resolved[joint.replace("right_", "left_", 1)] = band
        elif joint.startswith("left_"):
            resolved[joint.replace("left_", "right_", 1)] = band
    return resolved
