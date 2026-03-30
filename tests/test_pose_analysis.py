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


def test_get_reference_angles_tennis():
    """Tennis activity should return reference angles."""
    from whoopdata.telegram_bot import _get_reference_angles

    refs = _get_reference_angles("tennis serve")
    assert refs.get("right_elbow_flexion") == 30.0


def test_get_reference_angles_squat():
    """Squat activity should return knee reference angles."""
    from whoopdata.telegram_bot import _get_reference_angles

    refs = _get_reference_angles("squat")
    assert refs.get("right_knee_flexion") == 100.0


def test_get_reference_angles_unknown():
    """Unknown activity should return empty dict."""
    from whoopdata.telegram_bot import _get_reference_angles

    refs = _get_reference_angles("cricket")
    assert refs == {}
