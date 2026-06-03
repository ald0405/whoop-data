"""Tests for pose analysis math utilities, activity detection, and overlay logic."""

from __future__ import annotations

from whoopdata.agent.pose_analysis import (
    AggregatedMetrics,
    EventWindow,
    RepMetrics,
    angle_between_three_points,
    find_peaks,
)
from whoopdata.agent.pose_overlay import _deviation_colour, _rotate_point


# ---------------------------------------------------------------------------
# angle_between_three_points
# ---------------------------------------------------------------------------


def test_angle_right_angle():
    """Three points forming a 90-degree angle at the vertex."""
    result = angle_between_three_points((0, 1), (0, 0), (1, 0))
    assert abs(result - 90.0) < 0.01


def test_angle_straight_line():
    """Three collinear points should produce 180 degrees."""
    result = angle_between_three_points((0, 0), (1, 0), (2, 0))
    assert abs(result - 180.0) < 0.01


def test_angle_zero_when_points_coincide():
    """Coincident points (zero-length vectors) should return 0 without raising."""
    result = angle_between_three_points((5, 5), (5, 5), (5, 5))
    assert result == 0.0


def test_angle_45_degrees():
    """Verify a 45-degree angle is computed correctly."""
    result = angle_between_three_points((1, 0), (0, 0), (1, 1))
    assert abs(result - 45.0) < 0.01


def test_angle_obtuse():
    """An obtuse angle (>90 degrees)."""
    result = angle_between_three_points((-1, 0), (0, 0), (1, 1))
    assert result > 90.0
    assert result < 180.0


# ---------------------------------------------------------------------------
# find_peaks
# ---------------------------------------------------------------------------


def test_find_peaks_basic():
    """Should find two peaks above threshold with minimum distance."""
    values = [0, 5, 10, 5, 0, 0, 5, 12, 5, 0]
    peaks = find_peaks(values, threshold=8, min_distance=3)
    assert peaks == [2, 7]


def test_find_peaks_none_values():
    """None values should be treated as 0.0."""
    values = [None, None, 10, None, 0, 0, None, 12, None, 0]
    peaks = find_peaks(values, threshold=8, min_distance=3)
    assert peaks == [2, 7]


def test_find_peaks_min_distance():
    """Peaks closer than min_distance should not both be detected."""
    values = [0, 10, 9, 10, 0]
    peaks = find_peaks(values, threshold=8, min_distance=5)
    assert len(peaks) == 1


def test_find_peaks_empty():
    """Empty input should return empty list."""
    assert find_peaks([], threshold=5) == []


def test_find_peaks_no_peaks_above_threshold():
    """No values above threshold should return empty list."""
    values = [1, 2, 3, 2, 1]
    assert find_peaks(values, threshold=10) == []


# ---------------------------------------------------------------------------
# AggregatedMetrics.format_for_prompt
# ---------------------------------------------------------------------------


def test_format_for_prompt_single_rep():
    """Single rep should format without SD or drift."""
    metrics = AggregatedMetrics(
        activity="serve",
        num_reps=1,
        per_rep=[
            RepMetrics(
                rep_number=1,
                event=EventWindow(0, 30, "serve", 15),
                key_angles={"peak": {"right_elbow_flexion": 42.0}},
            )
        ],
        mean_angles={"right_elbow_flexion": {"peak": 42.0}},
        std_angles={"right_elbow_flexion": {"peak": 0.0}},
    )
    text = metrics.format_for_prompt()
    assert "1 serve" in text
    assert "42.0" in text
    assert "SD" not in text


def test_format_for_prompt_multi_rep():
    """Multiple reps should include SD and key frame info."""
    metrics = AggregatedMetrics(
        activity="serve",
        num_reps=3,
        per_rep=[],
        mean_angles={"right_elbow_flexion": {"peak": 42.0}},
        std_angles={"right_elbow_flexion": {"peak": 4.2}},
        best_rep_idx=1,
        worst_rep_idx=2,
    )
    text = metrics.format_for_prompt()
    assert "3 serve" in text
    assert "SD 4.2" in text
    assert "rep 2 (most typical)" in text
    assert "rep 3 (largest deviation)" in text


# ---------------------------------------------------------------------------
# _deviation_colour (pose_overlay)
# ---------------------------------------------------------------------------


def test_deviation_colour_good():
    """Small deviation (<15 deg) should be dim white (context skeleton)."""
    colour = _deviation_colour(30.0, 35.0)
    assert colour == (180, 180, 180)


def test_deviation_colour_yellow():
    """Moderate deviation (15-30 deg) should be yellow warning."""
    colour = _deviation_colour(45.0, 30.0)
    assert colour == (0, 200, 255)


def test_deviation_colour_red():
    """Large deviation (>30 deg) should be red fault."""
    colour = _deviation_colour(65.0, 30.0)
    assert colour == (0, 0, 240)


def test_deviation_colour_none_measured():
    """None measured should default to dim white."""
    colour = _deviation_colour(None, 30.0)
    assert colour == (180, 180, 180)


def test_deviation_colour_none_reference():
    """None reference should default to dim white."""
    colour = _deviation_colour(45.0, None)
    assert colour == (180, 180, 180)


# ---------------------------------------------------------------------------
# _rotate_point (pose_overlay)
# ---------------------------------------------------------------------------


def test_rotate_point_90_degrees():
    """Rotating (100, 0) by 90 degrees anticlockwise around origin."""
    result = _rotate_point((0, 0), (100, 0), 90)
    # In screen coordinates (Y down), 90 deg anticlockwise takes (100,0) to (0,-100)
    # but math.sin(90) = 1, so ry = 100*sin(90) = 100 -> pixel Y = 100
    assert abs(result[0] - 0) <= 1
    assert abs(result[1] - 100) <= 1


def test_rotate_point_zero_degrees():
    """Zero rotation should return the same point."""
    result = _rotate_point((50, 50), (100, 50), 0)
    assert result == (100, 50)


def test_rotate_point_180_degrees():
    """180 degree rotation should flip the point."""
    result = _rotate_point((0, 0), (100, 0), 180)
    assert abs(result[0] - (-100)) <= 1
    assert abs(result[1] - 0) <= 1


# ---------------------------------------------------------------------------
# Telegram integration: _preprocess_frames backward compat
# ---------------------------------------------------------------------------


def test_preprocess_frames_is_still_passthrough():
    """Legacy _preprocess_frames should still pass through unchanged."""
    from whoopdata.telegram_bot import _preprocess_frames

    frames = [b"frame-a", b"frame-b"]
    assert _preprocess_frames(frames) is frames


# ---------------------------------------------------------------------------
# reference_angles.get_phase_reference (phase-keyed bands, single source)
# ---------------------------------------------------------------------------


def test_get_phase_reference_forehand_contact_band():
    """Forehand contact returns the grip-spanning elbow band, mirrored L/R."""
    from whoopdata.agent.reference_angles import get_phase_reference

    refs = get_phase_reference("analyse my forehand", "contact")
    assert refs["right_elbow_flexion"] == (100.0, 130.0)
    assert refs["left_elbow_flexion"] == (100.0, 130.0)


def test_get_phase_reference_unknown_phase_falls_back_to_contact():
    """An unknown phase label falls back to the contact bands."""
    from whoopdata.agent.reference_angles import get_phase_reference

    refs = get_phase_reference("forehand", "nonsense")
    assert refs["right_elbow_flexion"] == (100.0, 130.0)


def test_get_phase_reference_non_groundstroke_empty():
    """Non-groundstroke activities (or empty) are not graded here."""
    from whoopdata.agent.reference_angles import get_phase_reference

    assert get_phase_reference("squat", "contact") == {}
    assert get_phase_reference("", "contact") == {}


def test_get_phase_reference_backhand_wider_band():
    """Backhand bands are wider (lower confidence) than forehand."""
    from whoopdata.agent.reference_angles import get_phase_reference

    refs = get_phase_reference("backhand", "contact")
    assert refs["right_elbow_flexion"] == (120.0, 175.0)


def test_telegram_no_longer_defines_reference_angles():
    """Reference angles now live only in reference_angles (no duplication)."""
    import whoopdata.telegram_bot as tb

    assert not hasattr(tb, "_REFERENCE_ANGLES")
    assert not hasattr(tb, "_get_reference_angles")


# ---------------------------------------------------------------------------
# _target_and_deviation / band-aware deviation colour (pose_overlay)
# ---------------------------------------------------------------------------


def test_target_and_deviation_inside_band():
    """A value inside the band has zero deviation; target is the value itself."""
    from whoopdata.agent.pose_overlay import _target_and_deviation

    target, dev = _target_and_deviation(118.0, (100.0, 130.0))
    assert target == 118.0
    assert dev == 0.0


def test_target_and_deviation_outside_band():
    """Outside the band, deviation is the distance to the nearest edge."""
    from whoopdata.agent.pose_overlay import _target_and_deviation

    assert _target_and_deviation(140.0, (100.0, 130.0)) == (130.0, 10.0)
    assert _target_and_deviation(80.0, (100.0, 130.0)) == (100.0, 20.0)


def test_target_and_deviation_scalar_and_none():
    """Scalar references still work; None inputs yield (None, 0.0)."""
    from whoopdata.agent.pose_overlay import _target_and_deviation

    assert _target_and_deviation(45.0, 30.0) == (30.0, 15.0)
    assert _target_and_deviation(None, (1.0, 2.0)) == (None, 0.0)
    assert _target_and_deviation(50.0, None) == (None, 0.0)


def test_deviation_colour_band():
    """Band-aware colour: inside is white, far outside is red."""
    assert _deviation_colour(115.0, (100.0, 130.0)) == (180, 180, 180)
    assert _deviation_colour(170.0, (100.0, 130.0)) == (0, 0, 240)


# ---------------------------------------------------------------------------
# segment_stroke_phases
# ---------------------------------------------------------------------------


def _triangular_speeds(n: int, peak: int) -> list[float]:
    return [max(0.0, 10.0 - abs(peak - i)) for i in range(n)]


def test_segment_phases_contact_is_peak_and_ordered():
    """Contact equals the peak frame; indices are strictly increasing."""
    from whoopdata.agent.pose_analysis import segment_stroke_phases

    n = 21
    ev = EventWindow(0, n - 1, "forehand", 12)
    phases = segment_stroke_phases(ev, _triangular_speeds(n, 12), [float(i) for i in range(n)])
    labels = [p for p, _ in phases]
    idxs = [i for _, i in phases]
    assert "contact" in labels
    assert dict(phases)["contact"] == 12
    assert idxs == sorted(idxs)
    assert len(set(idxs)) == len(idxs)
    assert 4 <= len(phases) <= 6


def test_segment_phases_backswing_is_x_extreme():
    """Backswing is the wrist horizontal extreme before contact."""
    from whoopdata.agent.pose_analysis import segment_stroke_phases

    n = 21
    wrist_xs = [0.0] * n
    wrist_xs[4] = 100.0  # clear pre-contact extreme
    ev = EventWindow(0, n - 1, "forehand", 12)
    phases = dict(segment_stroke_phases(ev, _triangular_speeds(n, 12), wrist_xs))
    assert phases["backswing"] == 4


def test_segment_phases_missing_xs_fallback():
    """Missing wrist positions still yield ordered, in-window phases."""
    from whoopdata.agent.pose_analysis import segment_stroke_phases

    n = 11
    ev = EventWindow(0, n - 1, "forehand", 5)
    phases = segment_stroke_phases(ev, [None] * n, [None] * n)
    idxs = [i for _, i in phases]
    assert 4 <= len(phases) <= 6
    assert all(0 <= i <= n - 1 for i in idxs)
    assert idxs == sorted(idxs)


def test_segment_phases_tiny_window():
    """A tiny window degrades gracefully (ordered, unique, in-window)."""
    from whoopdata.agent.pose_analysis import segment_stroke_phases

    ev = EventWindow(0, 2, "forehand", 1)
    phases = segment_stroke_phases(ev, [1.0, 2.0, 1.0], [0.0, 1.0, 2.0])
    idxs = [i for _, i in phases]
    assert all(0 <= i <= 2 for i in idxs)
    assert idxs == sorted(idxs)
    assert len(set(idxs)) == len(idxs)


# ---------------------------------------------------------------------------
# _kinetic_chain_order
# ---------------------------------------------------------------------------


def _spike(peak: int, n: int = 10) -> list[float]:
    return [1.0 if i == peak else 0.0 for i in range(n)]


def test_kinetic_chain_in_sequence():
    """Proximal->distal peak timing is in sequence."""
    from whoopdata.agent.pose_analysis import _kinetic_chain_order

    speeds = {"hip": _spike(1), "shoulder": _spike(3), "elbow": _spike(5), "wrist": _spike(7)}
    order, ok = _kinetic_chain_order(speeds, 0, 9)
    assert order == ["hip", "shoulder", "elbow", "wrist"]
    assert ok is True


def test_kinetic_chain_out_of_sequence():
    """Wrist-first (arm-led) timing is flagged out of sequence."""
    from whoopdata.agent.pose_analysis import _kinetic_chain_order

    speeds = {"hip": _spike(7), "shoulder": _spike(5), "elbow": _spike(3), "wrist": _spike(1)}
    _order, ok = _kinetic_chain_order(speeds, 0, 9)
    assert ok is False


# ---------------------------------------------------------------------------
# Aggregation: phase strips + flattened key frames
# ---------------------------------------------------------------------------


def test_aggregate_builds_best_and_worst_phase_strips():
    """Three reps with distinct contact angles yield best + worst strips."""
    from whoopdata.agent.pose_analysis import FrameAngles, PoseAnalyser

    n = 33

    def fa(i: int) -> FrameAngles:
        elbow = 110.0
        if i == 15:
            elbow = 112.0
        elif i == 27:
            elbow = 140.0
        return FrameAngles(i, {"right_elbow_flexion": elbow, "right_knee_flexion": 150.0})

    all_angles = [fa(i) for i in range(n)]
    wrist_speeds = [1.0] * n
    wrist_xs = [float(i) for i in range(n)]
    speed_series = {k: [0.0] * n for k in ("hip", "shoulder", "elbow", "wrist")}
    events = [
        EventWindow(0, 9, "forehand", 5),
        EventWindow(11, 20, "forehand", 15),
        EventWindow(22, 32, "forehand", 27),
    ]

    analyser = PoseAnalyser(activity="forehand")
    per_rep = analyser._compute_per_rep_metrics(
        events, all_angles, wrist_speeds, wrist_xs, speed_series
    )
    metrics = analyser._aggregate_metrics(per_rep)

    assert len(metrics.key_phase_strips) == 2
    assert {s.role for s in metrics.key_phase_strips} == {"best", "worst"}
    assert metrics.key_frame_indices == sorted(set(metrics.key_frame_indices))
    assert all(0 <= i < n for i in metrics.key_frame_indices)
    assert len(metrics.key_frame_indices) <= 12


# ---------------------------------------------------------------------------
# Orientation gate + warnings + phase-aware prompt text
# ---------------------------------------------------------------------------


class _FakeLandmark:
    def __init__(self, visibility: float) -> None:
        self.visibility = visibility
        self.x = 0.0
        self.y = 0.0


def _fake_pose(right_vis: float, left_vis: float) -> list:
    from whoopdata.agent.pose_analysis import Landmarks

    lms = [_FakeLandmark(0.9) for _ in range(33)]
    for i in (Landmarks.RIGHT_SHOULDER, Landmarks.RIGHT_ELBOW, Landmarks.RIGHT_WRIST):
        lms[i] = _FakeLandmark(right_vis)
    for i in (Landmarks.LEFT_SHOULDER, Landmarks.LEFT_ELBOW, Landmarks.LEFT_WRIST):
        lms[i] = _FakeLandmark(left_vis)
    return lms


def test_orientation_warning_when_racket_arm_occluded():
    """Right (racket) arm hidden -> orientation warning."""
    from whoopdata.agent.pose_analysis import _orientation_warning

    assert _orientation_warning([_fake_pose(0.2, 0.9)]) is not None


def test_orientation_warning_none_when_visible():
    """Both arms visible -> no orientation warning."""
    from whoopdata.agent.pose_analysis import _orientation_warning

    assert _orientation_warning([_fake_pose(0.9, 0.9)]) is None


def test_format_for_prompt_phase_block():
    """Phase strips render grouped phase lines with target bands + chain."""
    from whoopdata.agent.pose_analysis import KeyPhaseStrip

    rep = RepMetrics(
        rep_number=1,
        event=EventWindow(0, 20, "forehand", 10),
        key_angles={
            "backswing": {"right_elbow_flexion": 120.0, "right_knee_flexion": 140.0},
            "contact": {"right_elbow_flexion": 118.0},
        },
        phase_frames=[("backswing", 4), ("contact", 10)],
        chain_order=["hip", "shoulder", "elbow", "wrist"],
        chain_ok=True,
    )
    metrics = AggregatedMetrics(
        activity="forehand",
        num_reps=1,
        per_rep=[rep],
        key_phase_strips=[
            KeyPhaseStrip(
                rep_number=1,
                role="best",
                event_type="forehand",
                phases=[("backswing", 4), ("contact", 10)],
            )
        ],
    )
    text = metrics.format_for_prompt()
    assert "forehand -- best rep" in text
    assert "contact:" in text
    assert "(target 100-130)" in text
    assert "kinetic chain" in text


def test_format_for_prompt_includes_warnings():
    """Soft warnings surface as NOTE lines so the model can hedge."""
    metrics = AggregatedMetrics(
        activity="forehand", num_reps=1, per_rep=[], warnings=["low tracking"]
    )
    assert "NOTE: low tracking" in metrics.format_for_prompt()
