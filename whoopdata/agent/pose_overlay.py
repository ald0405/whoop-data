"""Visual annotation for biomechanics video frames.

Draws colour-coded skeleton overlays and reference ghost poses on
extracted video frames. The user receives annotated still photos via
Telegram showing where their joints are vs where they should be.

Colour scheme (following CourtCoach's proven UX):
    - Green: <15 degrees deviation from reference -- good
    - Yellow: 15-30 degrees deviation -- needs attention
    - Red: >30 degrees deviation -- priority fault
    - Dashed blue: reference ghost skeleton showing ideal pose
"""

from __future__ import annotations

import math

import cv2
import numpy as np

from .pose_analysis import (
    JOINT_ANGLES,
    Landmarks,
    POSE_CONNECTIONS,
    VISIBILITY_THRESHOLD,
)

# Colours in BGR (OpenCV convention)
_WHITE_DIM = (180, 180, 180)  # Thin context skeleton
_WHITE = (255, 255, 255)
_RED_FAULT = (0, 0, 240)  # Bold fault highlight
_YELLOW_WARN = (0, 200, 255)  # Warning highlight
_CYAN_GHOST = (255, 220, 100)  # Bright cyan-ish ghost -- high contrast on dark backgrounds
_BLACK_OUTLINE = (0, 0, 0)  # Text outline for readability
_SKELETON_THICKNESS = 1  # Thin context lines
_FAULT_THICKNESS = 4  # Bold fault segment
_GHOST_THICKNESS = 3  # Bold ghost line
_LANDMARK_RADIUS = 4
_LANDMARK_RADIUS_FAULT = 6  # Larger dot at fault joint
_FONT = cv2.FONT_HERSHEY_SIMPLEX

# Deviation thresholds (degrees)
_GOOD_THRESHOLD = 15.0
_WARN_THRESHOLD = 30.0


def _deviation_colour(measured: float | None, reference: float | None) -> tuple[int, int, int]:
    """Return a BGR colour based on the angular deviation from reference.

    Args:
        measured: Measured angle in degrees (``None`` if not available).
        reference: Target reference angle in degrees (``None`` if unknown).

    Returns:
        BGR colour tuple: dim white (ok), yellow (warning), or red (fault).

    Example:
        >>> _deviation_colour(45.0, 30.0)  # 15 deg off -> yellow
        (0, 200, 255)
    """
    if measured is None or reference is None:
        return _WHITE_DIM
    deviation = abs(measured - reference)
    if deviation < _GOOD_THRESHOLD:
        return _WHITE_DIM
    if deviation < _WARN_THRESHOLD:
        return _YELLOW_WARN
    return _RED_FAULT


def _get_pixel(
    landmarks: list,
    idx: int,
    width: int,
    height: int,
) -> tuple[int, int] | None:
    """Convert a normalised landmark to integer pixel coordinates.

    Args:
        landmarks: List of normalised landmark objects from MediaPipe.
        idx: Landmark index.
        width: Frame width in pixels.
        height: Frame height in pixels.

    Returns:
        ``(x, y)`` pixel coordinates, or ``None`` if below visibility threshold.

    Example:
        >>> _get_pixel(landmarks, Landmarks.LEFT_SHOULDER, 1920, 1080)
        (480, 540)
    """
    lm = landmarks[idx]
    if lm.visibility < VISIBILITY_THRESHOLD:
        return None
    return (int(lm.x * width), int(lm.y * height))


def _joint_for_connection(
    start_idx: int,
    end_idx: int,
) -> str | None:
    """Find the joint angle name associated with a skeleton connection.

    Looks up which configured joint angle has one of the connection
    endpoints as its vertex.

    Args:
        start_idx: Landmark index of the connection start.
        end_idx: Landmark index of the connection end.

    Returns:
        Joint angle name, or ``None`` if no matching joint is configured.
    """
    for name, (a, b, c) in JOINT_ANGLES.items():
        if b == start_idx or b == end_idx:
            return name
    return None


def _rotate_point(
    origin: tuple[int, int],
    point: tuple[int, int],
    angle_deg: float,
) -> tuple[int, int]:
    """Rotate a point around an origin by the given angle.

    Args:
        origin: Centre of rotation (x, y).
        point: Point to rotate (x, y).
        angle_deg: Rotation angle in degrees (positive = anticlockwise).

    Returns:
        Rotated point as integer (x, y).

    Example:
        >>> _rotate_point((0, 0), (100, 0), 90)
        (0, -100)
    """
    rad = math.radians(angle_deg)
    ox, oy = origin
    px, py = point
    dx, dy = px - ox, py - oy
    rx = dx * math.cos(rad) - dy * math.sin(rad)
    ry = dx * math.sin(rad) + dy * math.cos(rad)
    return (int(ox + rx), int(oy + ry))


def _find_worst_fault(
    measured_angles: dict[str, float | None],
    reference_angles: dict[str, float | None],
) -> tuple[str | None, float]:
    """Find the joint with the largest deviation from reference.

    Args:
        measured_angles: Measured joint angles.
        reference_angles: Reference target angles.

    Returns:
        Tuple of (joint_name, deviation_degrees). Returns (None, 0) if
        no faults exceed the good threshold.
    """
    worst_joint: str | None = None
    worst_dev = 0.0
    for joint_name, val in measured_angles.items():
        if val is None:
            continue
        ref = reference_angles.get(joint_name)
        if ref is None:
            continue
        dev = abs(val - ref)
        if dev > worst_dev:
            worst_dev = dev
            worst_joint = joint_name
    return worst_joint, worst_dev


def draw_form_diff(
    frame_bgr: np.ndarray,
    landmarks: list,
    measured_angles: dict[str, float | None],
    reference_angles: dict[str, float | None],
    phase_label: str = "",
) -> np.ndarray:
    """Draw a clean skeleton overlay focused on the single worst fault.

    Design principles (learned from user feedback):
    - Thin white skeleton for body context -- not distracting
    - Only the fault segment is highlighted in bold red/yellow
    - Ghost reference drawn only for the fault joint -- bold, high-contrast
    - No angle text on the frame -- numbers go in the text message
    - Phase label at top for orientation

    Args:
        frame_bgr: BGR numpy array of the video frame.
        landmarks: List of 33 normalised MediaPipe landmarks for this frame.
        measured_angles: Mapping of joint name to measured angle in degrees.
        reference_angles: Mapping of joint name to target reference angle.
        phase_label: Text label for the top of the frame.

    Returns:
        Annotated BGR numpy array.

    Example:
        >>> annotated = draw_form_diff(frame, landmarks, measured, reference, "Trophy Position")
        >>> annotated.shape == frame.shape
        True
    """
    h, w = frame_bgr.shape[:2]
    overlay = frame_bgr.copy()

    # Find the single worst fault -- always highlight even if within range,
    # because the user sent a video specifically for feedback
    worst_joint, worst_dev = _find_worst_fault(measured_angles, reference_angles)
    fault_joint_indices: set[int] = set()
    if worst_joint and worst_dev > 0:
        a, b, c = JOINT_ANGLES[worst_joint]
        fault_joint_indices = {a, b, c}

    # Layer 1: thin white context skeleton
    for start_idx, end_idx in POSE_CONNECTIONS:
        p1 = _get_pixel(landmarks, start_idx, w, h)
        p2 = _get_pixel(landmarks, end_idx, w, h)
        if p1 is None or p2 is None:
            continue

        # Check if this connection is part of the fault
        is_fault_segment = (
            start_idx in fault_joint_indices and end_idx in fault_joint_indices
        )

        if is_fault_segment:
            colour = _RED_FAULT if worst_dev >= _WARN_THRESHOLD else _YELLOW_WARN
            thickness = _FAULT_THICKNESS
        else:
            colour = _WHITE_DIM
            thickness = _SKELETON_THICKNESS

        cv2.line(overlay, p1, p2, colour, thickness, cv2.LINE_AA)

    # Draw landmark dots -- larger at the fault vertex
    all_landmarks = [
        Landmarks.LEFT_SHOULDER, Landmarks.RIGHT_SHOULDER,
        Landmarks.LEFT_ELBOW, Landmarks.RIGHT_ELBOW,
        Landmarks.LEFT_WRIST, Landmarks.RIGHT_WRIST,
        Landmarks.LEFT_HIP, Landmarks.RIGHT_HIP,
        Landmarks.LEFT_KNEE, Landmarks.RIGHT_KNEE,
        Landmarks.LEFT_ANKLE, Landmarks.RIGHT_ANKLE,
    ]
    for idx in all_landmarks:
        pt = _get_pixel(landmarks, idx, w, h)
        if pt is None:
            continue
        if idx in fault_joint_indices:
            cv2.circle(overlay, pt, _LANDMARK_RADIUS_FAULT, _WHITE, -1, cv2.LINE_AA)
        else:
            cv2.circle(overlay, pt, _LANDMARK_RADIUS, _WHITE_DIM, -1, cv2.LINE_AA)

    # Layer 2: ghost reference -- always show for the worst joint so the
    # user can see where they should be (they sent a video for feedback)
    if worst_joint and worst_dev > 0:
        a_idx, b_idx, c_idx = JOINT_ANGLES[worst_joint]
        vertex = _get_pixel(landmarks, b_idx, w, h)
        actual_end = _get_pixel(landmarks, c_idx, w, h)
        if vertex is not None and actual_end is not None:
            measured_val = measured_angles.get(worst_joint)
            ref_val = reference_angles.get(worst_joint)
            if measured_val is not None and ref_val is not None:
                rotation = ref_val - measured_val
                ghost_end = _rotate_point(vertex, actual_end, rotation)
                # Draw bold ghost with dark outline for contrast
                _draw_dashed_line(overlay, vertex, ghost_end, _BLACK_OUTLINE, _GHOST_THICKNESS + 2, dash_length=14, gap_length=8)
                _draw_dashed_line(overlay, vertex, ghost_end, _CYAN_GHOST, _GHOST_THICKNESS, dash_length=14, gap_length=8)

    # Phase label at top with dark background for readability
    if phase_label:
        # Dark background strip
        cv2.rectangle(overlay, (0, 0), (w, 45), (0, 0, 0), -1)
        cv2.putText(overlay, phase_label, (15, 30), _FONT, 0.7, _WHITE, 1, cv2.LINE_AA)

    return overlay


def _draw_dashed_line(
    img: np.ndarray,
    pt1: tuple[int, int],
    pt2: tuple[int, int],
    colour: tuple[int, int, int],
    thickness: int,
    dash_length: int = 10,
    gap_length: int = 8,
) -> None:
    """Draw a dashed line between two points on an image.

    Args:
        img: Image to draw on (modified in place).
        pt1: Start point (x, y).
        pt2: End point (x, y).
        colour: BGR colour tuple.
        thickness: Line thickness in pixels.
        dash_length: Length of each dash in pixels.
        gap_length: Length of each gap in pixels.
    """
    dx = pt2[0] - pt1[0]
    dy = pt2[1] - pt1[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return

    step = dash_length + gap_length
    num_segments = int(length / step)
    ux, uy = dx / length, dy / length

    for i in range(num_segments + 1):
        start_dist = i * step
        end_dist = min(start_dist + dash_length, length)
        sx = int(pt1[0] + ux * start_dist)
        sy = int(pt1[1] + uy * start_dist)
        ex = int(pt1[0] + ux * end_dist)
        ey = int(pt1[1] + uy * end_dist)
        cv2.line(img, (sx, sy), (ex, ey), colour, thickness, cv2.LINE_AA)


def encode_annotated_frame(frame_bgr: np.ndarray) -> bytes:
    """Encode an annotated BGR frame as JPEG bytes.

    Args:
        frame_bgr: BGR numpy array.

    Returns:
        JPEG-encoded bytes suitable for Telegram ``reply_photo``.

    Example:
        >>> data = encode_annotated_frame(np.zeros((100, 100, 3), dtype=np.uint8))
        >>> data[:2]
        b'\\xff\\xd8'
    """
    _, buffer = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buffer.tobytes()
