"""Local biomechanics computation using MediaPipe Pose Landmarker.

Processes dense video frames to detect 33 body landmarks, compute joint
angles, detect activity-specific events (serves, squat reps, etc.),
and aggregate metrics across repetitions. The LLM receives structured
numbers and a few annotated key frames rather than raw pixels.

References:
    - Gao et al. 2025: Tennis Motion Correction with Ensemble Learning and MediaPipe
    - Sarma 2026: Building an AI Tennis Coach with MediaPipe and Claude
    - CourtCoach (gsarmaonline/tennis-coach): pluggable activity detection pattern
"""

from __future__ import annotations

import logging
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants and landmark indices
# ---------------------------------------------------------------------------

_MODELS_DIR = Path(__file__).parent.parent.parent / "data" / "models"
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
_MODEL_FILE = "pose_landmarker_lite.task"

VISIBILITY_THRESHOLD = 0.5
MAX_DENSE_FRAMES = 600
MAX_VIDEO_DURATION_SECONDS = 60


class Landmarks:
    """Zero-based indices for the 33 MediaPipe pose landmarks.

    Centralises magic numbers so they are not scattered across the codebase.
    Only the landmarks used for biomechanics analysis are listed.

    Example:
        >>> Landmarks.LEFT_SHOULDER
        11
    """

    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28


POSE_CONNECTIONS = [
    (Landmarks.LEFT_SHOULDER, Landmarks.RIGHT_SHOULDER),
    (Landmarks.LEFT_SHOULDER, Landmarks.LEFT_ELBOW),
    (Landmarks.LEFT_ELBOW, Landmarks.LEFT_WRIST),
    (Landmarks.RIGHT_SHOULDER, Landmarks.RIGHT_ELBOW),
    (Landmarks.RIGHT_ELBOW, Landmarks.RIGHT_WRIST),
    (Landmarks.LEFT_SHOULDER, Landmarks.LEFT_HIP),
    (Landmarks.RIGHT_SHOULDER, Landmarks.RIGHT_HIP),
    (Landmarks.LEFT_HIP, Landmarks.RIGHT_HIP),
    (Landmarks.LEFT_HIP, Landmarks.LEFT_KNEE),
    (Landmarks.LEFT_KNEE, Landmarks.LEFT_ANKLE),
    (Landmarks.RIGHT_HIP, Landmarks.RIGHT_KNEE),
    (Landmarks.RIGHT_KNEE, Landmarks.RIGHT_ANKLE),
]

# Joint angle definitions: (landmark_a, vertex_b, landmark_c)
JOINT_ANGLES = {
    "left_elbow_flexion": (Landmarks.LEFT_SHOULDER, Landmarks.LEFT_ELBOW, Landmarks.LEFT_WRIST),
    "right_elbow_flexion": (
        Landmarks.RIGHT_SHOULDER,
        Landmarks.RIGHT_ELBOW,
        Landmarks.RIGHT_WRIST,
    ),
    "left_shoulder_elevation": (Landmarks.LEFT_HIP, Landmarks.LEFT_SHOULDER, Landmarks.LEFT_ELBOW),
    "right_shoulder_elevation": (
        Landmarks.RIGHT_HIP,
        Landmarks.RIGHT_SHOULDER,
        Landmarks.RIGHT_ELBOW,
    ),
    "left_knee_flexion": (Landmarks.LEFT_HIP, Landmarks.LEFT_KNEE, Landmarks.LEFT_ANKLE),
    "right_knee_flexion": (Landmarks.RIGHT_HIP, Landmarks.RIGHT_KNEE, Landmarks.RIGHT_ANKLE),
    "trunk_tilt": (Landmarks.LEFT_SHOULDER, Landmarks.LEFT_HIP, Landmarks.LEFT_KNEE),
}


# ---------------------------------------------------------------------------
# Math utilities (pure functions, no project imports)
# ---------------------------------------------------------------------------


def angle_between_three_points(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> float:
    """Compute the angle at vertex *b* formed by rays towards *a* and *c*.

    Args:
        a: (x, y) coordinates of the first point.
        b: (x, y) coordinates of the vertex.
        c: (x, y) coordinates of the third point.

    Returns:
        Angle in degrees (0-180).

    Example:
        >>> angle_between_three_points((0, 1), (0, 0), (1, 0))
        90.0
    """
    ba = np.array(a) - np.array(b)
    bc = np.array(c) - np.array(b)
    denominator = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denominator == 0:
        return 0.0
    cos_angle = np.dot(ba, bc) / denominator
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def find_peaks(
    values: list[float | None],
    threshold: float,
    min_distance: int = 10,
) -> list[int]:
    """Find local maxima in a 1-D signal above a threshold.

    Args:
        values: Signal values (None entries are treated as 0.0).
        threshold: Minimum value for a peak to be considered.
        min_distance: Minimum frame gap between consecutive peaks to
            prevent double-counting at the top of a single event.

    Returns:
        List of frame indices where peaks were detected.

    Example:
        >>> find_peaks([0, 5, 10, 5, 0, 0, 5, 12, 5, 0], threshold=8, min_distance=3)
        [2, 7]
    """
    filled = [v if v is not None else 0.0 for v in values]
    peaks: list[int] = []
    last_peak = -min_distance - 1
    for i in range(1, len(filled) - 1):
        if (
            filled[i] > threshold
            and filled[i] >= filled[i - 1]
            and filled[i] >= filled[i + 1]
            and (i - last_peak) >= min_distance
        ):
            peaks.append(i)
            last_peak = i
    return peaks


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EventWindow:
    """A detected action window within the video.

    Attributes:
        start_frame: First frame index of the event.
        end_frame: Last frame index of the event.
        event_type: Activity-specific label (e.g. ``"serve"``, ``"squat_rep"``).
        peak_frame: Frame index of the peak action (e.g. ball contact).
    """

    start_frame: int
    end_frame: int
    event_type: str
    peak_frame: int


@dataclass
class FrameAngles:
    """Joint angles computed for a single frame.

    Attributes:
        frame_idx: Index of the frame in the extracted sequence.
        angles: Mapping of joint name to angle in degrees.
            ``None`` if the required landmarks were not visible.
    """

    frame_idx: int
    angles: dict[str, float | None]


@dataclass
class RepMetrics:
    """Metrics for a single detected repetition.

    Attributes:
        rep_number: 1-based rep index.
        event: The detected event window.
        key_angles: Angles at key positions (e.g. ``{"trophy": {...}, "contact": {...}}``).
        peak_wrist_speed: Maximum wrist displacement between frames (pixels/frame).
    """

    rep_number: int
    event: EventWindow
    key_angles: dict[str, dict[str, float | None]]
    peak_wrist_speed: float | None = None


@dataclass
class AggregatedMetrics:
    """Cross-rep aggregated metrics for the LLM prompt.

    Attributes:
        activity: Detected or declared activity name.
        num_reps: Number of repetitions detected.
        per_rep: Individual rep metrics.
        mean_angles: Mean angle at each key position across reps.
        std_angles: Standard deviation of angles across reps.
        worst_rep_idx: 0-based index of the rep with largest deviation from reference.
        best_rep_idx: 0-based index of the most representative rep.
        fatigue_drift: Change in key angles from first to last rep.
        key_frame_indices: Frame indices selected for annotation and LLM submission.
    """

    activity: str
    num_reps: int
    per_rep: list[RepMetrics]
    mean_angles: dict[str, dict[str, float]] = field(default_factory=dict)
    std_angles: dict[str, dict[str, float]] = field(default_factory=dict)
    worst_rep_idx: int = 0
    best_rep_idx: int = 0
    fatigue_drift: dict[str, float] = field(default_factory=dict)
    key_frame_indices: list[int] = field(default_factory=list)

    def format_for_prompt(self, reference_angles: dict[str, float | None] | None = None) -> str:
        """Format metrics as a structured text block for the biomechanics agent prompt.

        Includes an alignment summary showing how many joints are within
        acceptable range vs how many need attention.

        Args:
            reference_angles: Optional reference angles for computing the
                alignment summary. If ``None``, the summary is omitted.

        Returns:
            Multi-line string suitable for inclusion in an LLM prompt.

        Example:
            >>> metrics.format_for_prompt()
            'Across 3 serves:\\n  ...'
        """
        lines = [f"Across {self.num_reps} {self.activity} rep(s):"]
        for joint_name, mean_vals in self.mean_angles.items():
            for position, mean_val in mean_vals.items():
                std_val = self.std_angles.get(joint_name, {}).get(position, 0.0)
                drift = self.fatigue_drift.get(f"{joint_name}_{position}", 0.0)
                line = f"  {joint_name} at {position}: mean {mean_val:.1f} deg"
                if self.num_reps > 1:
                    line += f", SD {std_val:.1f} deg"
                if abs(drift) > 1.0:
                    line += f", drift {drift:+.1f} deg rep1->repN"
                lines.append(line)

        # Alignment summary: how many joints are within range
        if reference_angles and self.mean_angles:
            in_range = 0
            total_checked = 0
            for joint_name, mean_vals in self.mean_angles.items():
                ref = reference_angles.get(joint_name)
                if ref is None:
                    continue
                for position, mean_val in mean_vals.items():
                    total_checked += 1
                    if abs(mean_val - ref) < 15.0:
                        in_range += 1
            if total_checked > 0:
                lines.append(
                    f"Alignment: {in_range}/{total_checked} joints within acceptable range"
                )

        if self.num_reps > 1:
            lines.append(
                f"Key frames: rep {self.best_rep_idx + 1} (most typical), "
                f"rep {self.worst_rep_idx + 1} (largest deviation)"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Activity detection protocols
# ---------------------------------------------------------------------------


class ActivityDetector(Protocol):
    """Protocol for pluggable activity-specific event detection."""

    def detect_events(
        self,
        all_angles: list[FrameAngles],
        wrist_speeds: list[float | None],
        shoulder_speeds: list[float | None],
        fps: float,
    ) -> list[EventWindow]:
        """Detect activity-specific events from per-frame data.

        Args:
            all_angles: Per-frame joint angles.
            wrist_speeds: Per-frame wrist displacement (pixels/frame).
            shoulder_speeds: Per-frame shoulder elevation speed.
            fps: Video frames per second.

        Returns:
            List of detected event windows.
        """
        ...


class TennisDetector:
    """Detect tennis strokes using wrist and shoulder speed peaks.

    When the user's caption specifies a shot type (e.g. "forehand",
    "backhand", "serve"), all detected events are labelled with that
    type. Otherwise, shoulder speed peaks are classified as serves
    and wrist speed peaks as groundstrokes.

    Args:
        label_override: If set, all detected events use this label
            instead of auto-classification. Derived from the user's caption.

    Example:
        >>> detector = TennisDetector(label_override="forehand")
        >>> events = detector.detect_events(angles, wrist_speeds, shoulder_speeds, 30.0)
    """

    def __init__(self, label_override: str | None = None) -> None:
        """Initialise with optional label override from user caption.

        Args:
            label_override: Shot type label to apply to all events.
        """
        self._label_override = label_override

    def detect_events(
        self,
        all_angles: list[FrameAngles],
        wrist_speeds: list[float | None],
        shoulder_speeds: list[float | None],
        fps: float,
    ) -> list[EventWindow]:
        """Detect tennis strokes from speed profiles.

        Args:
            all_angles: Per-frame joint angles.
            wrist_speeds: Per-frame wrist displacement.
            shoulder_speeds: Per-frame shoulder elevation speed.
            fps: Video frames per second.

        Returns:
            List of detected event windows.
        """
        min_dist = max(int(fps * 0.8), 5)
        wrist_threshold = _auto_threshold(wrist_speeds, factor=1.5)
        shoulder_threshold = _auto_threshold(shoulder_speeds, factor=1.5)

        wrist_peaks = find_peaks(wrist_speeds, wrist_threshold, min_distance=min_dist)
        shoulder_peaks = find_peaks(shoulder_speeds, shoulder_threshold, min_distance=min_dist)

        events: list[EventWindow] = []
        used_frames: set[int] = set()
        window = int(fps * 1.0)

        # Combine all peaks, prioritise shoulder peaks
        for peak in shoulder_peaks:
            if any(abs(peak - u) < min_dist for u in used_frames):
                continue
            start = max(0, peak - window)
            end = min(len(all_angles) - 1, peak + window)
            label = self._label_override or "serve"
            events.append(EventWindow(start, end, label, peak))
            used_frames.add(peak)

        for peak in wrist_peaks:
            if any(abs(peak - u) < min_dist for u in used_frames):
                continue
            start = max(0, peak - window)
            end = min(len(all_angles) - 1, peak + window)
            label = self._label_override or "groundstroke"
            events.append(EventWindow(start, end, label, peak))
            used_frames.add(peak)

        events.sort(key=lambda e: e.start_frame)
        return events


class GymDetector:
    """Detect gym exercise repetitions using joint angle valleys.

    Uses knee angle valleys for squats/deadlifts and elbow angle valleys
    for pressing movements.

    Example:
        >>> detector = GymDetector()
        >>> events = detector.detect_events(angles, wrist_speeds, shoulder_speeds, 30.0)
    """

    def detect_events(
        self,
        all_angles: list[FrameAngles],
        wrist_speeds: list[float | None],
        shoulder_speeds: list[float | None],
        fps: float,
    ) -> list[EventWindow]:
        """Detect gym reps from joint angle valleys.

        Args:
            all_angles: Per-frame joint angles.
            wrist_speeds: Per-frame wrist displacement (unused for gym).
            shoulder_speeds: Per-frame shoulder speed (unused for gym).
            fps: Video frames per second.

        Returns:
            List of detected rep event windows.
        """
        # Extract knee angles (use right knee as primary, fall back to left)
        knee_angles: list[float | None] = []
        for fa in all_angles:
            val = fa.angles.get("right_knee_flexion") or fa.angles.get("left_knee_flexion")
            knee_angles.append(val)

        # Invert to find valleys as peaks
        inverted = [(-v if v is not None else None) for v in knee_angles]
        threshold = _auto_threshold(inverted, factor=0.8)
        min_dist = max(int(fps * 1.0), 10)
        valley_peaks = find_peaks(inverted, threshold, min_distance=min_dist)

        events: list[EventWindow] = []
        window = int(fps * 1.5)
        for peak in valley_peaks:
            start = max(0, peak - window)
            end = min(len(all_angles) - 1, peak + window)
            events.append(EventWindow(start, end, "squat_rep", peak))

        return events


def _build_activity_detectors() -> dict[str, ActivityDetector]:
    """Build the activity detector registry with caption-aware labels.

    Returns:
        Mapping of caption keywords to detector instances.
    """
    return {
        "tennis": TennisDetector(),
        "serve": TennisDetector(label_override="serve"),
        "forehand": TennisDetector(label_override="forehand"),
        "backhand": TennisDetector(label_override="backhand"),
        "swing": TennisDetector(label_override="swing"),
        "volley": TennisDetector(label_override="volley"),
        "squat": GymDetector(),
        "deadlift": GymDetector(),
        "gym": GymDetector(),
        "workout": GymDetector(),
    }


ACTIVITY_DETECTORS: dict[str, ActivityDetector] = _build_activity_detectors()


def _auto_threshold(values: list[float | None], factor: float = 1.5) -> float:
    """Compute a dynamic threshold as factor * median of non-None positive values.

    Args:
        values: Signal values.
        factor: Multiplier applied to the median.

    Returns:
        Threshold value, or 0.0 if no valid values exist.
    """
    valid = [v for v in values if v is not None and v > 0]
    if not valid:
        return 0.0
    return float(np.median(valid) * factor)


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------


def _ensure_model() -> str:
    """Ensure the MediaPipe pose landmarker model is available locally.

    Downloads the lite model from Google Storage on first use. Returns
    the absolute path to the ``.task`` file.

    Returns:
        Path to the downloaded model file.

    Raises:
        FileNotFoundError: If the download fails and no cached model exists.

    Example:
        >>> path = _ensure_model()
        >>> path.endswith(".task")
        True
    """
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = _MODELS_DIR / _MODEL_FILE
    if not model_path.exists():
        logger.info("Downloading MediaPipe pose landmarker model to %s", model_path)
        try:
            urllib.request.urlretrieve(_MODEL_URL, str(model_path))
        except Exception:
            logger.exception("Failed to download pose landmarker model")
            raise FileNotFoundError(
                f"Pose landmarker model not found at {model_path} and download failed. "
                "Run 'make download-models' to fetch it manually."
            )
    return str(model_path)


# ---------------------------------------------------------------------------
# PoseAnalyser
# ---------------------------------------------------------------------------


def _get_point(
    landmarks: list, idx: int, width: int, height: int
) -> tuple[float, float] | None:
    """Extract pixel coordinates for a landmark if visibility is sufficient.

    Args:
        landmarks: List of normalised landmark objects from MediaPipe.
        idx: Landmark index.
        width: Frame width in pixels.
        height: Frame height in pixels.

    Returns:
        ``(x, y)`` pixel coordinates, or ``None`` if below visibility threshold.
    """
    lm = landmarks[idx]
    if lm.visibility < VISIBILITY_THRESHOLD:
        return None
    return (lm.x * width, lm.y * height)


def _compute_frame_angles(
    landmarks: list, width: int, height: int
) -> dict[str, float | None]:
    """Compute all configured joint angles for a single frame.

    Args:
        landmarks: List of 33 normalised landmark objects.
        width: Frame width in pixels.
        height: Frame height in pixels.

    Returns:
        Mapping of joint name to angle in degrees (``None`` if landmarks missing).
    """
    angles: dict[str, float | None] = {}
    for name, (a_idx, b_idx, c_idx) in JOINT_ANGLES.items():
        a = _get_point(landmarks, a_idx, width, height)
        b = _get_point(landmarks, b_idx, width, height)
        c = _get_point(landmarks, c_idx, width, height)
        if a is None or b is None or c is None:
            angles[name] = None
        else:
            angles[name] = angle_between_three_points(a, b, c)
    return angles


def _compute_speed(
    prev_landmarks: list | None,
    curr_landmarks: list,
    idx: int,
    width: int,
    height: int,
) -> float | None:
    """Compute pixel displacement of a landmark between consecutive frames.

    Args:
        prev_landmarks: Previous frame's landmarks (``None`` for first frame).
        curr_landmarks: Current frame's landmarks.
        idx: Landmark index to track.
        width: Frame width in pixels.
        height: Frame height in pixels.

    Returns:
        Euclidean pixel displacement, or ``None`` if either frame lacks the landmark.
    """
    if prev_landmarks is None:
        return None
    prev = _get_point(prev_landmarks, idx, width, height)
    curr = _get_point(curr_landmarks, idx, width, height)
    if prev is None or curr is None:
        return None
    return float(np.sqrt((curr[0] - prev[0]) ** 2 + (curr[1] - prev[1]) ** 2))


class PoseAnalyser:
    """Analyse dense video frames for biomechanics metrics.

    Wraps MediaPipe PoseLandmarker in ``VIDEO`` mode with temporal tracking,
    computes per-frame joint angles and speeds, detects activity-specific
    events, and aggregates metrics across repetitions.

    Args:
        activity: Activity name (e.g. ``"tennis"``, ``"squat"``). Used to
            select the appropriate event detector. If ``None``, defaults
            to treating the entire clip as a single event.

    Example:
        >>> analyser = PoseAnalyser(activity="tennis")
        >>> result = analyser.analyse_frames(frames, fps=30.0)
        >>> result.metrics.num_reps
        5
    """

    def __init__(self, activity: str | None = None) -> None:
        """Initialise the analyser with an optional activity hint.

        Scans the caption for known keywords (e.g. "forehand", "squat")
        to select the right detector. A caption like "analyse my tennis
        forehand" will match the "forehand" detector, not the generic
        "tennis" one.

        Args:
            activity: Free-text caption or activity name.
        """
        self._activity = (activity or "").strip().lower()
        self._detector = self._resolve_detector(self._activity)

    @staticmethod
    def _resolve_detector(caption: str) -> ActivityDetector | None:
        """Find the best-matching detector by scanning for keywords in the caption.

        More specific keywords (e.g. "forehand") are checked before generic
        ones (e.g. "tennis") so the label override takes effect.

        Args:
            caption: Normalised lower-case caption text.

        Returns:
            Matching detector, or ``None`` if no keywords found.
        """
        # Check specific shot types first, then generic activity names
        priority_order = [
            "forehand", "backhand", "volley", "serve", "swing",
            "squat", "deadlift",
            "tennis", "gym", "workout",
        ]
        for keyword in priority_order:
            if keyword in caption:
                return ACTIVITY_DETECTORS.get(keyword)
        return None

    def analyse_frames(
        self,
        frames: list[np.ndarray],
        fps: float,
    ) -> AnalysisResult:
        """Run the full analysis pipeline on a batch of BGR frames.

        Args:
            frames: List of BGR numpy arrays (from OpenCV).
            fps: Original video frame rate.

        Returns:
            ``AnalysisResult`` containing per-frame landmarks, computed angles,
            detected events, aggregated metrics, and key frame indices.

        Raises:
            ImportError: If mediapipe is not installed.
            FileNotFoundError: If the model file cannot be obtained.
        """
        import mediapipe as mp

        model_path = _ensure_model()
        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarker = mp.tasks.vision.PoseLandmarker
        PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
        RunningMode = mp.tasks.vision.RunningMode

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        all_landmarks: list[list | None] = []
        all_angles: list[FrameAngles] = []
        wrist_speeds: list[float | None] = []
        shoulder_speeds: list[float | None] = []
        timestamp_ms = 0
        interval_ms = int(1000 / fps) if fps > 0 else 33
        prev_landmarks: list | None = None

        with PoseLandmarker.create_from_options(options) as landmarker:
            for i, frame_bgr in enumerate(frames):
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                result = landmarker.detect_for_video(mp_image, timestamp_ms)
                timestamp_ms += interval_ms

                h, w = frame_bgr.shape[:2]

                if result.pose_landmarks and len(result.pose_landmarks) > 0:
                    lms = result.pose_landmarks[0]
                    all_landmarks.append(lms)
                    angles = _compute_frame_angles(lms, w, h)
                    all_angles.append(FrameAngles(frame_idx=i, angles=angles))

                    ws = _compute_speed(prev_landmarks, lms, Landmarks.RIGHT_WRIST, w, h)
                    ss = _compute_speed(
                        prev_landmarks, lms, Landmarks.RIGHT_SHOULDER, w, h
                    )
                    wrist_speeds.append(ws)
                    shoulder_speeds.append(ss)
                    prev_landmarks = lms
                else:
                    all_landmarks.append(None)
                    all_angles.append(FrameAngles(frame_idx=i, angles={}))
                    wrist_speeds.append(None)
                    shoulder_speeds.append(None)
                    prev_landmarks = None

        # Validate detection
        detected_count = sum(1 for lm in all_landmarks if lm is not None)
        if detected_count == 0:
            logger.warning(
                "No pose detected in %d frames -- check video content and model file",
                len(frames),
            )

        # Detect events
        if self._detector:
            events = self._detector.detect_events(
                all_angles, wrist_speeds, shoulder_speeds, fps
            )
        else:
            events = []

        # Fallback: treat entire clip as one event
        if not events and len(frames) > 0:
            events = [
                EventWindow(0, len(frames) - 1, self._activity or "unknown", len(frames) // 2)
            ]

        # Per-rep metrics and aggregation
        per_rep = self._compute_per_rep_metrics(events, all_angles, wrist_speeds)
        metrics = self._aggregate_metrics(per_rep)

        return AnalysisResult(
            all_landmarks=all_landmarks,
            all_angles=all_angles,
            events=events,
            metrics=metrics,
            wrist_speeds=wrist_speeds,
            shoulder_speeds=shoulder_speeds,
        )

    def _compute_per_rep_metrics(
        self,
        events: list[EventWindow],
        all_angles: list[FrameAngles],
        wrist_speeds: list[float | None],
    ) -> list[RepMetrics]:
        """Compute metrics for each detected repetition.

        Args:
            events: Detected event windows.
            all_angles: Per-frame joint angles.
            wrist_speeds: Per-frame wrist speeds.

        Returns:
            List of per-rep metrics.
        """
        reps: list[RepMetrics] = []
        for rep_num, event in enumerate(events, start=1):
            # Find key angles at the peak frame
            peak_idx = event.peak_frame
            if 0 <= peak_idx < len(all_angles):
                peak_angles = all_angles[peak_idx].angles
            else:
                peak_angles = {}

            # Peak wrist speed within event window
            event_wrist = wrist_speeds[event.start_frame : event.end_frame + 1]
            valid_speeds = [s for s in event_wrist if s is not None]
            peak_ws = max(valid_speeds) if valid_speeds else None

            reps.append(
                RepMetrics(
                    rep_number=rep_num,
                    event=event,
                    key_angles={"peak": peak_angles},
                    peak_wrist_speed=peak_ws,
                )
            )
        return reps

    def _aggregate_metrics(self, per_rep: list[RepMetrics]) -> AggregatedMetrics:
        """Aggregate per-rep metrics into cross-rep summaries.

        Args:
            per_rep: Individual rep metrics.

        Returns:
            Aggregated metrics ready for LLM prompt formatting.
        """
        activity = self._activity or "unknown"
        if not per_rep:
            return AggregatedMetrics(activity=activity, num_reps=0, per_rep=[])

        # Collect angle values per joint per position across reps
        joint_position_values: dict[str, dict[str, list[float]]] = {}
        for rep in per_rep:
            for position, angles in rep.key_angles.items():
                for joint_name, val in angles.items():
                    if val is None:
                        continue
                    joint_position_values.setdefault(joint_name, {}).setdefault(
                        position, []
                    ).append(val)

        mean_angles: dict[str, dict[str, float]] = {}
        std_angles: dict[str, dict[str, float]] = {}
        for joint_name, positions in joint_position_values.items():
            mean_angles[joint_name] = {}
            std_angles[joint_name] = {}
            for position, vals in positions.items():
                mean_angles[joint_name][position] = float(np.mean(vals))
                std_angles[joint_name][position] = float(np.std(vals)) if len(vals) > 1 else 0.0

        # Fatigue drift: first rep vs last rep
        fatigue_drift: dict[str, float] = {}
        if len(per_rep) >= 2:
            first = per_rep[0].key_angles.get("peak", {})
            last = per_rep[-1].key_angles.get("peak", {})
            for joint_name in first:
                if first[joint_name] is not None and last.get(joint_name) is not None:
                    fatigue_drift[f"{joint_name}_peak"] = last[joint_name] - first[joint_name]

        # Best and worst rep (by total deviation from mean)
        deviations = []
        for rep in per_rep:
            total_dev = 0.0
            count = 0
            for joint_name, val in rep.key_angles.get("peak", {}).items():
                if val is not None and joint_name in mean_angles:
                    mean_val = mean_angles[joint_name].get("peak", val)
                    total_dev += abs(val - mean_val)
                    count += 1
            deviations.append(total_dev / max(count, 1))

        worst_idx = int(np.argmax(deviations)) if deviations else 0
        best_idx = int(np.argmin(deviations)) if deviations else 0

        # Key frame indices
        key_frames = []
        if per_rep:
            key_frames.append(per_rep[best_idx].event.peak_frame)
            if worst_idx != best_idx:
                key_frames.append(per_rep[worst_idx].event.peak_frame)

        return AggregatedMetrics(
            activity=activity,
            num_reps=len(per_rep),
            per_rep=per_rep,
            mean_angles=mean_angles,
            std_angles=std_angles,
            worst_rep_idx=worst_idx,
            best_rep_idx=best_idx,
            fatigue_drift=fatigue_drift,
            key_frame_indices=key_frames,
        )


@dataclass
class AnalysisResult:
    """Complete output from PoseAnalyser.analyse_frames().

    Attributes:
        all_landmarks: Per-frame landmark lists (``None`` if no pose detected).
        all_angles: Per-frame joint angles.
        events: Detected event windows.
        metrics: Aggregated cross-rep metrics.
        wrist_speeds: Per-frame wrist displacement.
        shoulder_speeds: Per-frame shoulder displacement.
    """

    all_landmarks: list[list | None]
    all_angles: list[FrameAngles]
    events: list[EventWindow]
    metrics: AggregatedMetrics
    wrist_speeds: list[float | None]
    shoulder_speeds: list[float | None]
