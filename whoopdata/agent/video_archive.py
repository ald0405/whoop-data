"""Local archive for video analysis outputs.

Saves raw frames, annotated key frames, metrics JSON, and per-frame
landmark data to a timestamped directory under ``data/video_analyses/``.
The entire directory is gitignored. Useful for reviewing results on a
larger screen, comparing sessions over time, and debugging detection.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_ARCHIVE_ROOT = Path(__file__).parent.parent.parent / "data" / "video_analyses"


def save_analysis(
    *,
    activity: str,
    raw_frames: list[np.ndarray],
    annotated_frames: list[tuple[np.ndarray, str]],
    overlay_frames: list[np.ndarray | None] | None = None,
    metrics: dict[str, Any],
    landmarks_data: list[list[dict[str, float]] | None],
) -> Path:
    """Save a complete video analysis to a local timestamped directory.

    Directory structure::

        data/video_analyses/<timestamp>_<activity>/
            raw/          -- original extracted frames
            overlay/      -- every frame with skeleton overlay (where pose detected)
            annotated/    -- key frames with colour-coded skeleton + ghost reference
            metrics.json  -- aggregated metrics and per-rep breakdowns
            landmarks.json -- per-frame 33-point landmark data

    Args:
        activity: Activity name (e.g. ``"tennis"``, ``"squat"``).
        raw_frames: BGR numpy arrays of all extracted frames.
        annotated_frames: List of ``(annotated_bgr, label)`` tuples for
            key frames that were sent to the user.
        overlay_frames: Per-frame annotated BGR arrays with skeleton overlay.
            Same length as ``raw_frames``. Entries are ``None`` where no pose
            was detected. If the entire list is ``None``, the overlay directory
            is skipped.
        metrics: Aggregated metrics dictionary (serialisable to JSON).
        landmarks_data: Per-frame landmark data. Each entry is either a
            list of 33 dicts with ``x``, ``y``, ``z``, ``visibility``
            keys, or ``None`` if no pose was detected in that frame.

    Returns:
        Path to the created archive directory.

    Example:
        >>> path = save_analysis(
        ...     activity="tennis",
        ...     raw_frames=[frame1, frame2],
        ...     annotated_frames=[(ann1, "Trophy Position")],
        ...     metrics={"num_reps": 3},
        ...     landmarks_data=[None, [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.9}]],
        ... )
        >>> path.exists()
        True
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_activity = activity.replace(" ", "_").lower() or "unknown"
    archive_dir = _ARCHIVE_ROOT / f"{timestamp}_{clean_activity}"

    raw_dir = archive_dir / "raw"
    annotated_dir = archive_dir / "annotated"
    raw_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)

    # Save raw frames
    for i, frame in enumerate(raw_frames):
        path = raw_dir / f"frame_{i:04d}.jpg"
        cv2.imwrite(str(path), frame)

    # Save overlay frames (every frame with skeleton, where pose was detected)
    if overlay_frames:
        overlay_dir = archive_dir / "overlay"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        for i, frame in enumerate(overlay_frames):
            if frame is not None:
                path = overlay_dir / f"overlay_{i:04d}.jpg"
                cv2.imwrite(str(path), frame)

    # Save annotated key frames (colour-coded skeleton + ghost reference)
    for i, (frame, label) in enumerate(annotated_frames):
        clean_label = label.replace(" ", "_").replace("/", "-").lower()
        path = annotated_dir / f"key_{i:02d}_{clean_label}.jpg"
        cv2.imwrite(str(path), frame)

    # Save metrics JSON
    metrics_path = archive_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    # Save landmarks JSON
    landmarks_path = archive_dir / "landmarks.json"
    serialisable = []
    for frame_lms in landmarks_data:
        if frame_lms is None:
            serialisable.append(None)
        else:
            serialisable.append(frame_lms)
    with open(landmarks_path, "w") as f:
        json.dump(serialisable, f, indent=1, default=str)

    logger.info("Saved video analysis archive to %s", archive_dir)
    return archive_dir


def serialise_landmarks(landmarks: list | None) -> list[dict[str, float]] | None:
    """Convert MediaPipe landmark objects to JSON-serialisable dicts.

    Args:
        landmarks: List of normalised landmark objects, or ``None``.

    Returns:
        List of dicts with ``x``, ``y``, ``z``, ``visibility`` keys,
        or ``None`` if input is ``None``.

    Example:
        >>> serialise_landmarks(None) is None
        True
    """
    if landmarks is None:
        return None
    return [
        {
            "x": float(lm.x),
            "y": float(lm.y),
            "z": float(lm.z),
            "visibility": float(lm.visibility),
        }
        for lm in landmarks
    ]
