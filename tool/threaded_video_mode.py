
import cv2
from ultralytics import YOLO
import time
import torch
import os
import argparse
import pandas as pd
import random
import threading
import json
import numpy as np
import glob
from collections import Counter, deque


# -------------------------------------Configuration--------------------------------------------
# Configuration is loaded from YAML only.
# Missing file/keys are treated as configuration errors.

CONFIG_FILE_PATH = os.path.join("tool", "threaded_config.yaml")


def _to_cam_name_map(raw_map):
    mapped = {}
    if not isinstance(raw_map, dict):
        return mapped
    for key, value in raw_map.items():
        try:
            mapped[int(key)] = str(value)
        except Exception:
            continue
    return mapped


def _require_config_value(config, key):
    if key not in config:
        raise KeyError(f"Missing required config key '{key}' in {CONFIG_FILE_PATH}")
    return config[key]


def _normalize_pc_conf_threshold_map(raw_map):
    normalized = {}
    if not isinstance(raw_map, dict):
        return normalized

    for key, value in raw_map.items():
        pc_name = str(key).strip()
        if not pc_name:
            continue
        try:
            threshold = float(value)
        except Exception:
            continue
        normalized[pc_name] = max(0.0, min(1.0, threshold))
    return normalized


def _normalize_pc_iou_threshold_map(raw_map):
    normalized = {}
    if not isinstance(raw_map, dict):
        return normalized

    for key, value in raw_map.items():
        pc_name = str(key).strip()
        if not pc_name:
            continue
        try:
            threshold = float(value)
        except Exception:
            continue
        normalized[pc_name] = max(0.0, min(1.0, threshold))
    return normalized


def _normalize_threshold_mode(raw_mode, default_mode="dynamic"):
    mode_text = str(raw_mode).strip().lower()
    if mode_text in ("dynamic", "fixed"):
        return mode_text
    return str(default_mode).strip().lower()


def load_runtime_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as config_file:
            loaded = yaml.safe_load(config_file) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Invalid config format in {config_path}; expected a YAML mapping")
    except Exception as e:
        raise RuntimeError(f"Failed to load config from {config_path}: {e}") from e

    print(f"Loaded config from {config_path}")
    return loaded


CONFIG = load_runtime_config(CONFIG_FILE_PATH)


def parse_cli_args():
    parser = argparse.ArgumentParser(description="Threaded video mode with optional eval mode")
    parser.add_argument("--eval", dest="eval_mode", action="store_true", help="Enable evaluation mode")
    parser.add_argument("--eval-tag", default="", help="Custom tag for eval outputs")
    parser.add_argument("--eval-sample-sec", type=float, default=1.0, help="Eval sample period in seconds")
    parser.add_argument(
        "--groundtruth-dir",
        default=os.path.join("tool", "groundtruth"),
        help="Groundtruth CSV directory",
    )
    parser.add_argument(
        "--eval-log-dir",
        default="",
        help="Eval output root directory (default: <VIDEO_LOG_BASE_DIR>/eval)",
    )
    parser.add_argument("--video-input-dir", default="", help="Override VIDEO_INPUT_DIR for this run")
    parser.add_argument("--eval-only", dest="eval_only", action="store_true", help="Re-evaluate existing eval outputs using duration-based metrics (no video processing)")
    args, _ = parser.parse_known_args()
    return args


CLI_ARGS = parse_cli_args()

# Camera settings
CAM_INDEXES = [int(idx) for idx in _require_config_value(CONFIG, "CAM_INDEXES")]
CAM_NAMES = _to_cam_name_map(_require_config_value(CONFIG, "CAM_NAMES"))
if not CAM_NAMES:
    raise ValueError(f"'CAM_NAMES' must be a non-empty map in {CONFIG_FILE_PATH}")
FRAME_WIDTH = int(_require_config_value(CONFIG, "FRAME_WIDTH"))
FRAME_HEIGHT = int(_require_config_value(CONFIG, "FRAME_HEIGHT"))

# Window display settings
SHOW_WINDOWS = str(_require_config_value(CONFIG, "SHOW_WINDOWS")).strip().lower()
Windows_width = int(_require_config_value(CONFIG, "WINDOWS_WIDTH"))
Windows_height = int(_require_config_value(CONFIG, "WINDOWS_HEIGHT"))

# Detection settings
CONF_THRESHOLD = float(_require_config_value(CONFIG, "CONF_THRESHOLD"))
IOU_THRESHOLD = float(_require_config_value(CONFIG, "IOU_THRESHOLD"))
CONF_THRESHOLD_MODE = _normalize_threshold_mode(CONFIG.get("CONF_THRESHOLD_MODE", "dynamic"), "dynamic")
IOU_THRESHOLD_MODE = _normalize_threshold_mode(CONFIG.get("IOU_THRESHOLD_MODE", "dynamic"), "dynamic")
SAVE_INTERVAL_SEC = float(_require_config_value(CONFIG, "SAVE_INTERVAL_SEC"))
PC_CONF_THRESHOLD_OVERRIDES = _normalize_pc_conf_threshold_map(CONFIG.get("PC_CONF_THRESHOLD_OVERRIDES", {}))
PC_IOU_THRESHOLD_OVERRIDES = _normalize_pc_iou_threshold_map(CONFIG.get("PC_IOU_THRESHOLD_OVERRIDES", {}))
MIN_CONF_THRESHOLD = (
    min([CONF_THRESHOLD] + list(PC_CONF_THRESHOLD_OVERRIDES.values()))
    if (CONF_THRESHOLD_MODE == "dynamic" and PC_CONF_THRESHOLD_OVERRIDES)
    else CONF_THRESHOLD
)

# Detection schedule settings
DETECTION_START_HOUR_24 = int(_require_config_value(CONFIG, "DETECTION_START_HOUR_24"))
DETECTION_END_HOUR_24 = int(_require_config_value(CONFIG, "DETECTION_END_HOUR_24"))

# PC ROI settings
ENABLE_PC_ROI = bool(_require_config_value(CONFIG, "ENABLE_PC_ROI"))
ENABLE_MONITOR_ROI = bool(_require_config_value(CONFIG, "ENABLE_MONITOR_ROI"))
PERSON_OVERLAP_DWELL_SEC = float(_require_config_value(CONFIG, "PERSON_OVERLAP_DWELL_SEC"))
PC_ON_NO_PERSON_DWELL_SEC = float(_require_config_value(CONFIG, "PC_ON_NO_PERSON_DWELL_SEC"))
LATEST_PERSON_FLAG_LOOKBACK_SEC = float(_require_config_value(CONFIG, "LATEST_PERSON_FLAG_LOOKBACK_SEC"))
MONITOR_ON_MEAN_THRESHOLD = float(_require_config_value(CONFIG, "MONITOR_ON_MEAN_THRESHOLD"))
MONITOR_ON_STD_THRESHOLD = float(_require_config_value(CONFIG, "MONITOR_ON_STD_THRESHOLD"))
MONITOR_STATE_STABLE_FRAMES = int(_require_config_value(CONFIG, "MONITOR_STATE_STABLE_FRAMES"))
ROI_CONFIG_DIR = os.path.normpath(str(_require_config_value(CONFIG, "ROI_CONFIG_DIR")))
CSV_SUFFIX = str(_require_config_value(CONFIG, "CSV_SUFFIX"))
MONITOR_CSV_SUFFIX = str(_require_config_value(CONFIG, "MONITOR_CSV_SUFFIX"))
GATE_ROI_CSV_SUFFIX = str(_require_config_value(CONFIG, "GATE_ROI_CSV_SUFFIX"))

# Tracking and smoothing settings
ENABLE_RESOURCE_MONITOR = bool(_require_config_value(CONFIG, "ENABLE_RESOURCE_MONITOR"))
PROCESS_EVERY_N_FRAMES = max(1, int(_require_config_value(CONFIG, "PROCESS_EVERY_N_FRAMES")))
FRAME_CAP_FPS = max(0.0, float(_require_config_value(CONFIG, "FRAME_CAP_FPS")))
FRAME_CAP_INTERVAL_SEC = (1.0 / FRAME_CAP_FPS) if FRAME_CAP_FPS > 0 else 0.0
TRACK_MATCH_DISTANCE_PX = max(
    1.0,
    float(_require_config_value(CONFIG, "TRACK_MATCH_DISTANCE_PX")),
)
TRACK_REID_EXPAND_PX_PER_SEC = max(
    0.0,
    float(_require_config_value(CONFIG, "TRACK_REID_EXPAND_PX_PER_SEC")),
)
TRACK_MAX_MISSING_SEC = max(
    0.0,
    float(_require_config_value(CONFIG, "TRACK_MAX_MISSING_SEC_VIDEO")),
)
TRACK_STALE_FORGET_SEC = max(
    TRACK_MAX_MISSING_SEC,
    float(_require_config_value(CONFIG, "TRACK_STALE_FORGET_SEC")),
)
TRACK_VELOCITY_SMOOTHING = min(
    0.99,
    max(0.0, float(_require_config_value(CONFIG, "TRACK_VELOCITY_SMOOTHING"))),
)
TRACK_MAX_PREDICTION_SPEED_PX_PER_SEC = max(
    1.0,
    float(_require_config_value(CONFIG, "TRACK_MAX_PREDICTION_SPEED_PX_PER_SEC")),
)
SMOOTH_WINDOW_SEC = max(0.0, float(_require_config_value(CONFIG, "SMOOTH_WINDOW_SEC")))

# Motion gating settings
ENABLE_MOTION_GATING = bool(_require_config_value(CONFIG, "ENABLE_MOTION_GATING"))
MOTION_SUBTRACTOR_METHOD = str(_require_config_value(CONFIG, "MOTION_SUBTRACTOR_METHOD"))
MOTION_DETECT_SHADOWS = bool(_require_config_value(CONFIG, "MOTION_DETECT_SHADOWS"))
MOTION_MIN_AREA_RATIO = float(_require_config_value(CONFIG, "MOTION_MIN_AREA_RATIO"))
MOTION_MORPH_KERNEL = int(_require_config_value(CONFIG, "MOTION_MORPH_KERNEL"))
MOTION_BLUR_KERNEL = int(_require_config_value(CONFIG, "MOTION_BLUR_KERNEL"))
MOTION_WARMUP_FRAMES = int(_require_config_value(CONFIG, "MOTION_WARMUP_FRAMES"))
PERIODIC_INFER_SEC = float(_require_config_value(CONFIG, "PERIODIC_INFER_SEC"))

# Realtime PC-state CSV settings
ENABLE_REALTIME_PC_STATE_CSV = bool(_require_config_value(CONFIG, "ENABLE_REALTIME_PC_STATE_CSV"))
REALTIME_PC_STATE_WRITE_INTERVAL_SEC = float(_require_config_value(CONFIG, "REALTIME_PC_STATE_WRITE_INTERVAL_SEC"))

# Paths
MODEL_PATH = str(_require_config_value(CONFIG, "MODEL_PATH"))
VIDEO_INPUT_DIR = os.path.normpath(str(_require_config_value(CONFIG, "VIDEO_INPUT_DIR")))
VIDEO_GLOB_PATTERNS = _require_config_value(CONFIG, "VIDEO_GLOB_PATTERNS")
VIDEO_MAX_SOURCES = max(1, int(_require_config_value(CONFIG, "VIDEO_MAX_SOURCES")))
VIDEO_LOG_BASE_DIR = os.path.normpath(str(_require_config_value(CONFIG, "VIDEO_LOG_BASE_DIR")))
VIDEO_ROI_IMAGES_SUBDIR = str(_require_config_value(CONFIG, "VIDEO_ROI_IMAGES_SUBDIR"))
VIDEO_PERF_SUMMARY_FILENAME = str(_require_config_value(CONFIG, "VIDEO_PERF_SUMMARY_FILENAME"))
VIDEO_REALTIME_PC_STATE_FILENAME = str(_require_config_value(CONFIG, "VIDEO_REALTIME_PC_STATE_FILENAME"))
VIDEO_TIME_FALLBACK_FPS = float(_require_config_value(CONFIG, "VIDEO_TIME_FALLBACK_FPS"))

LOG_BASE_DIR = VIDEO_LOG_BASE_DIR
ROI_BASE_DIR = os.path.join(LOG_BASE_DIR, VIDEO_ROI_IMAGES_SUBDIR)
PERF_SUMMARY_FILE = os.path.join(
    LOG_BASE_DIR,
    VIDEO_PERF_SUMMARY_FILENAME,
)

if CLI_ARGS.video_input_dir:
    VIDEO_INPUT_DIR = os.path.normpath(str(CLI_ARGS.video_input_dir))

EVAL_MODE = bool(CLI_ARGS.eval_mode)
EVAL_SAMPLE_SEC = max(0.1, float(CLI_ARGS.eval_sample_sec))
EVAL_TAG = str(CLI_ARGS.eval_tag).strip() or time.strftime("eval_%Y%m%d_%H%M%S", time.localtime())
GROUNDTRUTH_DIR = os.path.normpath(str(CLI_ARGS.groundtruth_dir))
EVAL_LOG_ROOT = os.path.normpath(str(CLI_ARGS.eval_log_dir)) if str(CLI_ARGS.eval_log_dir).strip() else os.path.join(LOG_BASE_DIR, "eval")
MODEL_NAME_FOR_LOG = os.path.basename(MODEL_PATH)
# Delay seat people-count accumulation until person stays inside the same ROI.
PEOPLE_COUNT_DWELL_SEC = 2.0
# Avoid showing hold box for a single-frame miss.
HOLD_VISUAL_MIN_SEC = max(0.0, float(_require_config_value(CONFIG, "HOLD_VISUAL_MIN_SEC")))
# Consider a person "near corner" if the center is inside this ratio box from any corner.
SUDDEN_DISAPPEAR_CORNER_MARGIN_RATIO = max(
    0.05,
    min(0.5, float(_require_config_value(CONFIG, "SUDDEN_DISAPPEAR_CORNER_MARGIN_RATIO"))),
)

# ----------------------------------------------------------------------------------------------

# Load model once
# choose device (use CUDA if available)
# Detect CUDA availability and select an explicit device string (cuda:0) when available.
cuda_available = torch.cuda.is_available()
device = "cuda:0" if cuda_available else "cpu"
print(f"CUDA available: {cuda_available}")
print(f"Device selected: {device}")

model = YOLO(MODEL_PATH)
# move model to GPU if available
try:
    if cuda_available:
        try:
            # prefer explicit torch.device
            model.to(torch.device(device))
            # if multiple GPUs are present, print device info
            try:
                print(f"torch.cuda.device_count() = {torch.cuda.device_count()}")
                if torch.cuda.device_count() > 0:
                    try:
                        print(f"CUDA device name: {torch.cuda.get_device_name(0)}")
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception as e:
            print(f"Warning: failed to move model to {device}: {e}")
except Exception:
    # if anything unexpected happens, continue — model may still run on CPU
    pass

# set model confidence threshold globally to reduce post-processing
try:
    # some ultralytics versions expose a conf attribute
    model.conf = MIN_CONF_THRESHOLD
    model.iou = IOU_THRESHOLD
except Exception:
    # ignore if attribute not present
    pass


# Shared YOLO model is used by multiple camera threads.
# Serialize inference calls to avoid thread-race behavior in ultralytics/torch runtime.
INFERENCE_LOCK = threading.Lock()


def resolve_person_class_ids(yolo_model):
    """Return class ids that represent person/human for current model labels."""
    try:
        names = getattr(yolo_model, "names", None)
        if isinstance(names, dict):
            person_ids = {
                int(class_id)
                for class_id, class_name in names.items()
                if "person" in str(class_name).strip().lower()
                or "human" in str(class_name).strip().lower()
            }
            if person_ids:
                return person_ids
        elif isinstance(names, (list, tuple)):
            person_ids = {
                idx
                for idx, class_name in enumerate(names)
                if "person" in str(class_name).strip().lower()
                or "human" in str(class_name).strip().lower()
            }
            if person_ids:
                return person_ids
    except Exception:
        pass

    # Fallback for standard COCO-style models.
    return {0}


PERSON_CLASS_IDS = resolve_person_class_ids(model)
print(f"Person class ids: {sorted(PERSON_CLASS_IDS)}")


def run_model_inference(frame):
    """Run one inference pass with safe fallback paths and serialized model access."""
    with INFERENCE_LOCK:
        try:
            if device.startswith("cuda") and cuda_available:
                from torch import amp

                with amp.autocast(device_type="cuda"):
                    return model(frame, verbose=False, device=device)
            return model(frame, verbose=False, device=device)
        except Exception:
            try:
                return model(frame, verbose=False)
            except Exception:
                raise


def _make_motion_subtractor():
    """Create background subtractor for motion detection."""
    history = 500
    if MOTION_SUBTRACTOR_METHOD == "KNN":
        return cv2.createBackgroundSubtractorKNN(
            history=history,
            dist2Threshold=400.0,
            detectShadows=MOTION_DETECT_SHADOWS,
        )
    return cv2.createBackgroundSubtractorMOG2(
        history=history,
        varThreshold=16.0,
        detectShadows=MOTION_DETECT_SHADOWS,
    )


def compute_motion_foreground(gray_frame, subtractor):
    """Return binary foreground mask and global foreground area ratio."""
    if subtractor is None:
        h, w = gray_frame.shape[:2]
        return np.zeros((h, w), dtype=np.uint8), 0.0

    blur_k = MOTION_BLUR_KERNEL if (MOTION_BLUR_KERNEL % 2 == 1) else (MOTION_BLUR_KERNEL + 1)
    blur_k = max(1, blur_k)
    if blur_k > 1:
        gray_frame = cv2.GaussianBlur(gray_frame, (blur_k, blur_k), 0)

    fg_mask = subtractor.apply(gray_frame)
    _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)

    kernel = np.ones((MOTION_MORPH_KERNEL, MOTION_MORPH_KERNEL), dtype=np.uint8)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

    fg_pixels = float(np.count_nonzero(fg_mask))
    total_pixels = float(fg_mask.shape[0] * fg_mask.shape[1]) if fg_mask.size else 1.0
    motion_ratio = fg_pixels / max(1.0, total_pixels)
    return fg_mask, motion_ratio


def get_conf_threshold_for_pc(pc_name):
    if CONF_THRESHOLD_MODE == "fixed":
        return float(CONF_THRESHOLD)
    if not pc_name:
        return float(CONF_THRESHOLD)
    return float(PC_CONF_THRESHOLD_OVERRIDES.get(str(pc_name).strip(), CONF_THRESHOLD))


def get_iou_threshold_for_pc(pc_name):
    if IOU_THRESHOLD_MODE == "fixed":
        return float(IOU_THRESHOLD)
    if not pc_name:
        return float(IOU_THRESHOLD)
    return float(PC_IOU_THRESHOLD_OVERRIDES.get(str(pc_name).strip(), IOU_THRESHOLD))


def box_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = [float(v) for v in box_a[:4]]
    bx1, by1, bx2, by2 = [float(v) for v in box_b[:4]]

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0.0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = area_a + area_b - inter_area
    if denom <= 0.0:
        return 0.0
    return inter_area / denom


def apply_pc_nms_candidates(candidates, iou_threshold, conf_threshold):
    sorted_candidates = sorted(candidates, key=lambda item: float(item[4]), reverse=True)
    kept = []
    for candidate in sorted_candidates:
        conf = float(candidate[4])
        if conf <= float(conf_threshold):
            continue
        suppressed = False
        for kept_candidate in kept:
            if box_iou(candidate, kept_candidate) > float(iou_threshold):
                suppressed = True
                break
        if not suppressed:
            kept.append(candidate)
    return kept

def to_safe_label(value):
    """Convert a display label into a filesystem-safe name."""
    cleaned = "".join((c if c.isalnum() or c in ("-", "_") else "_") for c in str(value).strip())
    # collapse repeated underscores for cleaner paths
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "unknown"


def format_video_timestamp(video_seconds):
    safe_seconds = max(0.0, float(video_seconds))
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(safe_seconds))


def format_video_clock(video_seconds):
    safe_seconds = max(0.0, float(video_seconds))
    total = int(safe_seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_compact_video_clock(video_seconds):
    safe_seconds = max(0.0, float(video_seconds))
    total = int(safe_seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def get_video_frame_time_seconds(cap, cam_data):
    pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
    if pos_msec and pos_msec > 0:
        video_seconds = float(pos_msec) / 1000.0
    else:
        frame_idx = float(cap.get(cv2.CAP_PROP_POS_FRAMES) or 0.0)
        fps = float(cam_data.get("video_fps") or VIDEO_TIME_FALLBACK_FPS)
        video_seconds = (frame_idx / fps) if fps > 0 else float(cam_data.get("video_last_ts", 0.0))

    last_ts = cam_data.get("video_last_ts")
    if last_ts is not None and video_seconds < last_ts:
        video_seconds = float(last_ts)

    cam_data["video_last_ts"] = float(video_seconds)
    return float(video_seconds)


def is_box_far_from_camera_corners(box, frame_shape, corner_margin_ratio=SUDDEN_DISAPPEAR_CORNER_MARGIN_RATIO):
    if box is None or frame_shape is None or len(frame_shape) < 2:
        return False

    frame_h, frame_w = int(frame_shape[0]), int(frame_shape[1])
    if frame_h <= 0 or frame_w <= 0:
        return False

    cx, cy = box_center(box)
    margin_x = max(1.0, float(frame_w) * float(corner_margin_ratio))
    margin_y = max(1.0, float(frame_h) * float(corner_margin_ratio))

    near_top_left = (cx <= margin_x) and (cy <= margin_y)
    near_top_right = (cx >= (frame_w - margin_x)) and (cy <= margin_y)
    near_bottom_left = (cx <= margin_x) and (cy >= (frame_h - margin_y))
    near_bottom_right = (cx >= (frame_w - margin_x)) and (cy >= (frame_h - margin_y))
    near_corner = near_top_left or near_top_right or near_bottom_left or near_bottom_right
    return not near_corner


def save_zone_roi_fallback_report_frame(
    cam_data,
    frame,
    frame_time_sec,
    fallback_assignments,
    reason="no_person_detected_zone_roi_fallback",
):
    report_dir = cam_data.get("report_dir")
    if not report_dir:
        return

    frame_second = int(max(0.0, float(frame_time_sec)))
    last_saved_second = cam_data.get("zone_roi_report_last_sec")
    if last_saved_second == frame_second:
        return

    os.makedirs(report_dir, exist_ok=True)
    filename = f"zone_roi_no_detect_{frame_second:08d}.jpg"
    image_path = os.path.join(report_dir, filename)

    assignment_parts = []
    for item in fallback_assignments or []:
        person_id = str(item.get("person_id", "")).strip()
        pc_name = str(item.get("pc_name", "")).strip()
        if person_id and pc_name:
            assignment_parts.append(f"{person_id}->{pc_name}")
    assignment_text = ";".join(assignment_parts)

    # Stamp precise video timestamp onto the image so it is self-contained.
    overlay = frame.copy()
    safe_ts = max(0.0, float(frame_time_sec))
    whole_sec = int(safe_ts)
    frac_4 = int((safe_ts - whole_sec) * 10000.0)
    ts_label = f"t:{format_video_clock(safe_ts)}.{frac_4:04d}"
    assignment_label = assignment_text if assignment_text else "none"
    if len(assignment_label) > 90:
        assignment_label = assignment_label[:87] + "..."
    fallback_label = f"zone_roi:{assignment_label}"
    box_w = min(max(360, (len(fallback_label) * 9)), max(360, overlay.shape[1] - 24))
    cv2.rectangle(overlay, (12, 12), (12 + int(box_w), 86), (0, 0, 0), -1)
    cv2.putText(overlay, ts_label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
    cv2.putText(overlay, fallback_label, (20, 73), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 80), 2)

    if not cv2.imwrite(image_path, overlay):
        return

    cam_data["zone_roi_report_last_sec"] = frame_second
    cam_data.setdefault("zone_roi_report_rows", []).append(
        {
            "time": format_video_timestamp(frame_time_sec),
            "clock": format_video_clock(frame_time_sec),
            "t_sec": round(float(frame_time_sec), 3),
            "image_file": image_path,
            "fallback_count": len(fallback_assignments or []),
            "fallback_assignments": assignment_text,
            "reason": str(reason or "no_person_detected_zone_roi_fallback"),
            "person_id": "",
            "pc_name": "",
            "frame_type": "single",
        }
    )


def _draw_detection_boxes(overlay, boxes, color, prefix, text_color=None):
    if text_color is None:
        text_color = color
    for b in boxes or []:
        x1, y1, x2, y2, cf = int(b[0]), int(b[1]), int(b[2]), int(b[3]), float(b[4])
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            overlay,
            f"{prefix}:{cf:.2f}",
            (x1, max(12, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            text_color,
            1,
        )


def _draw_red_outline(overlay, boxes, thickness=3):
    for b in boxes or []:
        x1, y1, x2, y2 = int(b[0]), int(b[1]), int(b[2]), int(b[3])
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), thickness)


def save_dynamic_fixed_comparison_report_frame(
    cam_data,
    frame,
    frame_time_sec,
    pc_name,
    dynamic_boxes,
    fixed_boxes,
    dynamic_conf,
    fixed_conf,
    dynamic_iou,
    fixed_iou,
):
    report_dir = cam_data.get("report_dir")
    if not report_dir:
        return None

    opti_dir = os.path.join(report_dir, "opti_report")
    os.makedirs(opti_dir, exist_ok=True)

    ts = max(0.0, float(frame_time_sec))
    safe_pc = to_safe_label(pc_name)
    entry_idx = len(cam_data.setdefault("dynamic_only_detections", []))
    base_name = f"{safe_pc}_{int(ts)}_{entry_idx}"
    image_path = os.path.join(opti_dir, f"comparison_{base_name}.jpg")

    left = frame.copy()
    right = frame.copy()

    # Left panel: dynamic result, with fixed-kept boxes highlighted for contrast.
    _draw_detection_boxes(left, dynamic_boxes, (0, 255, 0), "dyn", (0, 255, 0))
    _draw_red_outline(left, dynamic_boxes, 3)
    _draw_detection_boxes(left, fixed_boxes, (255, 0, 0), "fix", (255, 0, 0))
    cv2.putText(left, f"Comparison | dynamic", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(
        left,
        f"PC:{pc_name}  dyn_conf={dynamic_conf:.2f}  fix_conf={fixed_conf:.2f}",
        (12, 56),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (240, 240, 240),
        1,
    )
    cv2.putText(
        left,
        f"dyn_iou={dynamic_iou:.2f}  fix_iou={fixed_iou:.2f}  t={format_video_clock(ts)}",
        (12, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (240, 240, 240),
        1,
    )

    # Right panel: fixed result only.
    _draw_detection_boxes(right, fixed_boxes, (255, 0, 0), "fix", (255, 0, 0))
    _draw_red_outline(right, fixed_boxes, 3)
    if not fixed_boxes:
        cv2.putText(right, "fixed: no detections", (12, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(right, "Comparison | fixed", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(
        right,
        f"PC:{pc_name}  t={format_video_clock(ts)}",
        (12, 56),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (240, 240, 240),
        1,
    )

    gap = np.full((left.shape[0], 24, 3), 25, dtype=np.uint8)
    merged = np.hstack([left, gap, right])
    footer = f"source={os.path.basename(str(cam_data.get('source_path', '')))}  reason=dynamic-kept/fixed-dropped"
    footer_y = merged.shape[0] - 14
    ts_label = f"t:{format_video_clock(ts)}"
    ts_size, _ = cv2.getTextSize(ts_label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
    ts_x = max(12, merged.shape[1] - ts_size[0] - 16)
    cv2.rectangle(
        merged,
        (max(8, ts_x - 8), max(0, footer_y - 22)),
        (merged.shape[1] - 8, footer_y + 6),
        (0, 0, 0),
        -1,
    )
    cv2.putText(merged, footer, (12, footer_y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
    cv2.putText(merged, ts_label, (ts_x, footer_y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 1)
    cv2.imwrite(image_path, merged)
    return image_path


def save_sudden_disappear_report_frames(
    cam_data,
    frame_before,
    frame_after,
    frame_time_sec,
    person_id,
    pc_name,
    missing_box=None,
):
    report_dir = cam_data.get("report_dir")
    if not report_dir:
        return
    if frame_before is None or frame_after is None:
        return

    os.makedirs(report_dir, exist_ok=True)
    safe_ts = max(0.0, float(frame_time_sec))
    person_text = str(person_id or "").strip() or "unknown"
    pc_text = str(pc_name or "").strip() or "unknown"
    reason = "sudden_disappear_far_from_corner"

    # Track disappear count per person to keep pairs numbered.
    disappear_counters = cam_data.setdefault("disappear_person_counters", {})
    disappear_counters[person_text] = disappear_counters.get(person_text, 0) + 1
    pair_num = disappear_counters[person_text]
    pair_label = f"{pair_num:02d}"

    rows_to_append = []
    for frame_type, img in (("before", frame_before), ("disappear", frame_after)):
        overlay = img.copy()

        # Draw the last known person box on the pre-disappear frame for easier visual debugging.
        if frame_type == "before" and missing_box is not None:
            try:
                x1, y1, x2, y2 = map(int, missing_box)
                x1 = max(0, min(x1, overlay.shape[1] - 1))
                x2 = max(0, min(x2, overlay.shape[1] - 1))
                y1 = max(0, min(y1, overlay.shape[0] - 1))
                y2 = max(0, min(y2, overlay.shape[0] - 1))
                if x2 > x1 and y2 > y1:
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(
                        overlay,
                        "missing_box",
                        (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 0, 255),
                        2,
                    )
            except Exception:
                pass

        whole_sec = int(safe_ts)
        frac_4 = int((safe_ts - whole_sec) * 10000.0)
        ts_label = f"t:{format_video_clock(safe_ts)}.{frac_4:04d}"
        meta_label = f"{reason}:{person_text}->{pc_text} [{frame_type}]"
        if len(meta_label) > 96:
            meta_label = meta_label[:93] + "..."

        box_w = min(max(420, (len(meta_label) * 8)), max(420, overlay.shape[1] - 24))
        cv2.rectangle(overlay, (12, 12), (12 + int(box_w), 88), (0, 0, 0), -1)
        cv2.putText(overlay, ts_label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
        cv2.putText(overlay, meta_label, (20, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (120, 255, 120), 2)

        filename = f"sudden_disappear_{person_text}_{pair_label}_{frame_type}.jpg"
        image_path = os.path.join(report_dir, filename)
        if not cv2.imwrite(image_path, overlay):
            continue

        rows_to_append.append(
            {
                "time": format_video_timestamp(frame_time_sec),
                "clock": format_video_clock(frame_time_sec),
                "t_sec": round(float(frame_time_sec), 3),
                "image_file": image_path,
                "fallback_count": 1,
                "fallback_assignments": f"{person_text}->{pc_text}",
                "reason": reason,
                "person_id": person_text,
                "pc_name": pc_text,
                "frame_type": frame_type,
            }
        )

    if rows_to_append:
        cam_data.setdefault("zone_roi_report_rows", []).extend(rows_to_append)


def discover_video_paths(video_dir, patterns, max_sources):
    unique_paths = set()
    patterns_to_use = patterns if isinstance(patterns, list) and patterns else ["*.mp4", "*.avi", "*.mov", "*.mkv"]

    for pattern in patterns_to_use:
        for path in glob.glob(os.path.join(video_dir, str(pattern))):
            if os.path.isfile(path):
                unique_paths.add(os.path.normpath(path))

    ordered = sorted(unique_paths)
    return ordered[:max_sources]


def update_mode_value(history, value, now_ts, window_sec):
    value_int = int(value)
    if window_sec <= 0:
        history.clear()
        history.append((now_ts, value_int))
        return value_int

    history.append((now_ts, value_int))
    cutoff = now_ts - window_sec
    while history and history[0][0] < cutoff:
        history.popleft()

    counts = Counter(sample_value for _, sample_value in history)
    max_count = max(counts.values()) if counts else 0
    top_values = {sample_value for sample_value, count in counts.items() if count == max_count}

    for _, sample_value in reversed(history):
        if sample_value in top_values:
            return int(sample_value)

    return value_int


def set_pc_available_state(state, raw_available, now_ts):
    state["raw_available"] = int(raw_available)
    available_history = state.setdefault("available_history", deque())
    state["available"] = update_mode_value(available_history, state["raw_available"], now_ts, SMOOTH_WINDOW_SEC)


def update_smoothed_person_count(cam_data, raw_count, now_ts):
    person_history = cam_data.setdefault("person_count_history", deque())
    smoothed = update_mode_value(person_history, int(raw_count), now_ts, SMOOTH_WINDOW_SEC)
    cam_data["person_count_raw"] = int(raw_count)
    cam_data["person_count_smoothed"] = int(smoothed)
    return int(smoothed)


def is_detection_time_active(current_time_struct=None):
    return True


def distance(box1, box2):
    """Calculate distance between centers of two boxes."""
    cx1 = (box1[0] + box1[2]) / 2
    cy1 = (box1[1] + box1[3]) / 2
    cx2 = (box2[0] + box2[2]) / 2
    cy2 = (box2[1] + box2[3]) / 2
    return ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5


def box_center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def polygon_center(polygon):
    arr = np.asarray(polygon, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] == 0:
        return (0.0, 0.0)
    return (float(np.mean(arr[:, 0])), float(np.mean(arr[:, 1])))


def predict_track_box(last_box, velocity, dt_sec):
    if dt_sec <= 0:
        return last_box

    vx, vy = velocity or (0.0, 0.0)
    max_shift = TRACK_MAX_PREDICTION_SPEED_PX_PER_SEC * dt_sec
    dx = max(-max_shift, min(max_shift, vx * dt_sec))
    dy = max(-max_shift, min(max_shift, vy * dt_sec))
    return (
        last_box[0] + dx,
        last_box[1] + dy,
        last_box[2] + dx,
        last_box[3] + dy,
    )


def match_box_to_person(box, tracked_persons, now_ts, unavailable_ids=None):
    """Find the best tracked person using momentum-aware position prediction."""
    blocked_ids = unavailable_ids or set()
    best_score = float("inf")
    matched_id = None

    for pid, pdata in tracked_persons.items():
        if pid in blocked_ids:
            continue

        last_box = pdata.get("last_box")
        if not last_box:
            continue

        last_seen_ts = float(pdata.get("last_seen_ts", now_ts))
        missing_sec = max(0.0, float(now_ts) - last_seen_ts)
        if missing_sec > TRACK_MAX_MISSING_SEC:
            continue

        predicted_box = predict_track_box(last_box, pdata.get("velocity"), missing_sec)
        dist = distance(box, predicted_box)
        allowed_dist = TRACK_MATCH_DISTANCE_PX + (TRACK_REID_EXPAND_PX_PER_SEC * missing_sec)

        if dist <= allowed_dist and dist < best_score:
            best_score = dist
            matched_id = pid

    return matched_id


def match_box_to_recent_hold_track(box, tracked_persons, now_ts, unavailable_ids=None):
    """Fallback matcher: reuse a nearby recently-missing track before creating a new ID."""
    blocked_ids = unavailable_ids or set()
    best_score = float("inf")
    matched_id = None

    for pid, pdata in tracked_persons.items():
        if pid in blocked_ids:
            continue

        last_box = pdata.get("last_box")
        if not last_box:
            continue

        last_seen_ts = float(pdata.get("last_seen_ts", now_ts))
        missing_sec = max(0.0, float(now_ts) - last_seen_ts)
        if missing_sec <= 0.0 or missing_sec > TRACK_MAX_MISSING_SEC:
            continue

        # Use the most recently seen box with a slightly wider gate for short re-acquisition windows.
        dist = distance(box, last_box)
        allowed_dist = max(TRACK_MATCH_DISTANCE_PX * 1.5, TRACK_MATCH_DISTANCE_PX + 30.0)
        if dist <= allowed_dist and dist < best_score:
            best_score = dist
            matched_id = pid

    return matched_id


def prune_stale_tracks(tracked_persons, now_ts):
    stale_ids = []
    for pid, pdata in tracked_persons.items():
        last_seen_ts = pdata.get("last_seen_ts")
        if last_seen_ts is None:
            continue

        missing_sec = max(0.0, float(now_ts) - float(last_seen_ts))
        if missing_sec > TRACK_STALE_FORGET_SEC:
            stale_ids.append(pid)

    for pid in stale_ids:
        tracked_persons.pop(pid, None)


def load_camera_rois(cam_label, csv_suffix=CSV_SUFFIX):
    """Load ROI polygons from CSV for the given camera label and suffix."""
    csv_path = os.path.join(ROI_CONFIG_DIR, f"{cam_label}{csv_suffix}")
    if not os.path.exists(csv_path):
        return []
    try:
        df = pd.read_csv(csv_path)
        rois = []
        for _, row in df.iterrows():
            pc_name = row["pc_name"]
            points = json.loads(row["points_json"])
            rois.append({"pc_name": pc_name, "polygon": np.array(points, dtype=np.int32)})
        return rois
    except Exception as e:
        print(f"Failed to load ROI from {csv_path}: {e}")
        return []


def point_in_polygon(point, polygon):
    """Check if point is inside polygon using cv2.pointPolygonTest."""
    return cv2.pointPolygonTest(polygon, point, False) >= 0


def get_pc_for_box(box, rois):
    """Return PC name if box center is inside any ROI polygon, else None."""
    cx = (box[0] + box[2]) / 2
    cy = (box[1] + box[3]) / 2
    for roi in rois:
        if point_in_polygon((cx, cy), roi["polygon"]):
            return roi["pc_name"]
    return None


def new_pc_state(pc_name):
    return {
        "pc_name": pc_name,
        "pc_on": False,
        "raw_pc_on": False,
        "on_streak": 0,
        "off_streak": 0,
        "monitor_mean": 0.0,
        "monitor_std": 0.0,
        "person_present": False,
        "current_person_id": None,
        "last_person_id": None,
        "last_person_seen_time": None,
        "overlap_start_time": None,
        "empty_since_time": None,
        "person_event_logged": False,
        "unattended_logged": False,
        "reason1_logged_person_id": None,
        # availability state: 0=available, 1=person+pc_off, 2=person+pc_on (or waiting while pc_on and empty<threshold)
        "raw_available": 0,
        "available": 0,
        "available_history": deque(),
        "last_update_time": None,
    }


def init_pc_states(pc_rois, monitor_rois):
    pc_states = {}
    for roi in list(pc_rois) + list(monitor_rois):
        pc_name = str(roi.get("pc_name", "")).strip()
        if not pc_name:
            continue
        if pc_name not in pc_states:
            pc_states[pc_name] = new_pc_state(pc_name)
    return pc_states


def compute_polygon_gray_stats(gray_frame, polygon):
    mask = np.zeros(gray_frame.shape, dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 255)
    pixels = gray_frame[mask == 255]
    if pixels.size == 0:
        return 0.0, 0.0
    return float(np.mean(pixels)), float(np.std(pixels))


def update_pc_states_from_monitor(frame, monitor_rois, pc_states, now_ts):
    if not monitor_rois:
        return

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    for roi in monitor_rois:
        pc_name = roi.get("pc_name")
        if not pc_name:
            continue

        if pc_name not in pc_states:
            pc_states[pc_name] = new_pc_state(pc_name)

        state = pc_states[pc_name]
        prev_pc_on = bool(state.get("pc_on", False))
        mean_val, std_val = compute_polygon_gray_stats(gray, roi["polygon"])
        raw_on = (mean_val >= MONITOR_ON_MEAN_THRESHOLD) and (std_val >= MONITOR_ON_STD_THRESHOLD)

        if raw_on:
            state["on_streak"] += 1
            state["off_streak"] = 0
        else:
            state["off_streak"] += 1
            state["on_streak"] = 0

        if state["on_streak"] >= MONITOR_STATE_STABLE_FRAMES:
            state["pc_on"] = True
        elif state["off_streak"] >= MONITOR_STATE_STABLE_FRAMES:
            state["pc_on"] = False

        state["raw_pc_on"] = raw_on
        state["monitor_mean"] = round(mean_val, 2)
        state["monitor_std"] = round(std_val, 2)

        # transition handling for correct availability timing
        if (not prev_pc_on) and state["pc_on"]:
            state["unattended_logged"] = False
            if not state.get("person_present"):
                state["empty_since_time"] = now_ts
                set_pc_available_state(state, 2, now_ts)
        elif prev_pc_on and (not state["pc_on"]):
            state["unattended_logged"] = False
            state["empty_since_time"] = None
            if not state.get("person_present"):
                set_pc_available_state(state, 0, now_ts)

        state["last_update_time"] = now_ts


def update_pc_activity_events(cam_name, pc_states, pc_to_person, now_ts, pc_event_logs, pc_unattended_logs):
    now_str = format_video_timestamp(now_ts)

    for pc_name, state in pc_states.items():
        person_id = pc_to_person.get(pc_name)

        if person_id:
            if state.get("current_person_id") != person_id:
                state["current_person_id"] = person_id
                state["overlap_start_time"] = now_ts
                state["person_event_logged"] = False
                state["reason1_logged_person_id"] = None

            state["person_present"] = True
            state["last_person_id"] = person_id
            state["last_person_seen_time"] = now_ts
            state["empty_since_time"] = None
            state["unattended_logged"] = False

            if state.get("pc_on"):
                set_pc_available_state(state, 2, now_ts)
                state["reason1_logged_person_id"] = None
            else:
                set_pc_available_state(state, 1, now_ts)
                if state.get("available") == 1 and state.get("reason1_logged_person_id") != person_id:
                    pc_unattended_logs.append(
                        {
                            "time": now_str,
                            "user": person_id,
                            "cam_name": cam_name,
                            "pc_name": pc_name,
                            "reason": "1",
                            "model_name": "yolov8s",
                        }
                    )
                    state["reason1_logged_person_id"] = person_id

            dwell = now_ts - (state.get("overlap_start_time") or now_ts)
            if dwell >= PERSON_OVERLAP_DWELL_SEC and not state.get("person_event_logged"):
                if state.get("pc_on") and state.get("available") == 2:
                    event_type = "USING_PC"
                    event_pcnum = pc_name
                else:
                    event_type = "NON_PC_ACTIVITY"
                    event_pcnum = "None"

                pc_event_logs.append(
                    {
                        "time": now_str,
                        "cam_name": cam_name,
                        "pc_name": pc_name,
                        "event_type": event_type,
                        "person_id": person_id,
                        "pc_on": bool(state.get("pc_on")),
                        "dwell_sec": round(dwell, 2),
                        "PCnum": event_pcnum,
                        "model_name": "yolov8s",
                    }
                )
                state["person_event_logged"] = True
        else:
            if state.get("person_present"):
                state["person_present"] = False
                state["current_person_id"] = None
                state["overlap_start_time"] = None
                state["empty_since_time"] = now_ts
                state["person_event_logged"] = False
                state["reason1_logged_person_id"] = None
            elif state.get("empty_since_time") is None:
                state["empty_since_time"] = now_ts

            if state.get("pc_on"):
                empty_dwell = now_ts - (state.get("empty_since_time") or now_ts)
                if empty_dwell >= PC_ON_NO_PERSON_DWELL_SEC:
                    set_pc_available_state(state, 0, now_ts)
                    last_person_seen_time = state.get("last_person_seen_time")
                    has_recent_last_person = (
                        state.get("last_person_id")
                        and last_person_seen_time is not None
                        and (now_ts - last_person_seen_time) <= LATEST_PERSON_FLAG_LOOKBACK_SEC
                    )
                    if state.get("available") == 0 and has_recent_last_person and not state.get("unattended_logged"):
                        pc_unattended_logs.append(
                            {
                                "time": now_str,
                                "user": state.get("last_person_id"),
                                "cam_name": cam_name,
                                "pc_name": pc_name,
                                "reason": "2",
                                "model_name": "yolov8s",
                            }
                        )
                        state["unattended_logged"] = True
                else:
                    set_pc_available_state(state, 2, now_ts)
            else:
                set_pc_available_state(state, 0, now_ts)
                state["unattended_logged"] = False
                state["empty_since_time"] = None


def build_pc_state_rows(cam_idx, cam_name, cam_label, pc_states, now_ts):
    snapshot_time = format_video_timestamp(now_ts)
    rows = []
    for pc_name in sorted(pc_states.keys()):
        state = pc_states[pc_name]
        overlap_start = state.get("overlap_start_time")
        empty_since = state.get("empty_since_time")
        overlap_dwell = (now_ts - overlap_start) if overlap_start else 0.0
        empty_dwell = (now_ts - empty_since) if empty_since else 0.0

        rows.append(
            {
                "time": snapshot_time,
                "cam_idx": cam_idx,
                "cam_name": cam_name,
                "cam_label": cam_label,
                "pc_name": pc_name,
                "pc_on": bool(state.get("pc_on")),
                "raw_pc_on": bool(state.get("raw_pc_on")),
                "person_present": bool(state.get("person_present")),
                "current_person_id": state.get("current_person_id"),
                "last_person_id": state.get("last_person_id"),
                "overlap_dwell_sec": round(overlap_dwell, 2),
                "empty_dwell_sec": round(empty_dwell, 2),
                "monitor_mean": state.get("monitor_mean", 0.0),
                "monitor_std": state.get("monitor_std", 0.0),
                "last_update_time": (
                    format_video_timestamp(state["last_update_time"])
                    if state.get("last_update_time")
                    else ""
                ),
            }
        )
    return rows


def pc_name_sort_key(pc_name):
    text = str(pc_name)
    digits = "".join(ch for ch in text if ch.isdigit())
    number = int(digits) if digits else 10**9
    return (number, text)


def build_all_pc_state_rows(cams):
    state_by_pc = {}
    for cam_data in cams.values():
        for pc_name, state in cam_data.get("pc_states", {}).items():
            state_by_pc[pc_name] = {
                "pc_name": pc_name,
                "pc_on": bool(state.get("pc_on")),
                "availble": int(state.get("available", 0)),
                "model_name": "yolov8s",
            }

    ordered_pc_names = sorted(state_by_pc.keys(), key=pc_name_sort_key)
    return [state_by_pc[name] for name in ordered_pc_names]


def write_pc_state_csv(cams, csv_path):
    rows = build_all_pc_state_rows(cams)
    pc_state_df = pd.DataFrame(rows, columns=["pc_name", "pc_on", "availble", "model_name"])
    pc_state_df.to_csv(csv_path, index=False)


def current_day_tag(now_ts=None):
    if now_ts is None:
        now_ts = time.time()
    return time.strftime("%Y%m%d", time.localtime(now_ts))


def day_tag_from_time_text(time_text, fallback_day_tag):
    text = str(time_text or "").strip()
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        y, m, d = text[0:4], text[5:7], text[8:10]
        if y.isdigit() and m.isdigit() and d.isdigit():
            return f"{y}{m}{d}"
    return fallback_day_tag


def get_groundtruth_csv_path(cam_label):
    return os.path.join(GROUNDTRUTH_DIR, f"{cam_label}_gt.csv")


def load_groundtruth_for_camera(cam_name, cam_label):
    csv_path = get_groundtruth_csv_path(cam_label)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Eval mode requires groundtruth file: {csv_path} (camera: {cam_name})"
        )

    df = pd.read_csv(csv_path)
    required_cols = {"time", "cam_name", "pc_name", "occupied_gt", "people_count_gt"}
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Groundtruth file missing columns {missing}: {csv_path}")

    lookup = {}
    for _, row in df.iterrows():
        time_text = str(row.get("time", "")).strip()
        pc_name = str(row.get("pc_name", "")).strip()
        if not time_text or not pc_name:
            continue

        occupied_raw = row.get("occupied_gt", 0)
        people_raw = row.get("people_count_gt", 0)

        try:
            occupied_val = int(float(occupied_raw))
        except Exception:
            occupied_val = 0
        occupied_val = 1 if occupied_val > 0 else 0

        try:
            people_count_val = max(0, int(float(people_raw)))
        except Exception:
            people_count_val = 0

        lookup[(time_text, pc_name)] = {
            "occupied_gt": occupied_val,
            "people_count_gt": people_count_val,
            "user_ids_gt": str(row.get("user_ids_gt", "")).strip(),
        }

    if not lookup:
        raise ValueError(f"Groundtruth file has no usable rows: {csv_path}")

    return {
        "path": csv_path,
        "lookup": lookup,
    }


def update_eval_sessions(cam_data, pc_name, current_person_id, now_ts):
    active = cam_data.setdefault("eval_active_sessions", {})
    sessions = cam_data.setdefault("eval_user_sessions", [])

    current_person = str(current_person_id).strip() if current_person_id else ""
    existing = active.get(pc_name)

    if current_person:
        if not existing:
            active[pc_name] = {
                "person_id_pred": current_person,
                "start_ts": float(now_ts),
                "start_time": format_video_timestamp(now_ts),
            }
        elif existing.get("person_id_pred") != current_person:
            sessions.append(
                {
                    "pc_name": pc_name,
                    "person_id_pred": existing.get("person_id_pred", ""),
                    "start_time": existing.get("start_time", ""),
                    "end_time": format_video_timestamp(now_ts),
                    "duration_sec": round(max(0.0, float(now_ts) - float(existing.get("start_ts", now_ts))), 2),
                }
            )
            active[pc_name] = {
                "person_id_pred": current_person,
                "start_ts": float(now_ts),
                "start_time": format_video_timestamp(now_ts),
            }
    elif existing:
        sessions.append(
            {
                "pc_name": pc_name,
                "person_id_pred": existing.get("person_id_pred", ""),
                "start_time": existing.get("start_time", ""),
                "end_time": format_video_timestamp(now_ts),
                "duration_sec": round(max(0.0, float(now_ts) - float(existing.get("start_ts", now_ts))), 2),
            }
        )
        active.pop(pc_name, None)


def collect_detection_rows(cam_idx, cam_data, sample_ts):
    sample_time_text = format_video_timestamp(sample_ts)
    sample_clock = format_video_clock(sample_ts)
    pc_states = cam_data.get("pc_states", {})
    pc_people_counts = cam_data.get("last_pc_people_counts", {})
    pc_model_only_presence = cam_data.get("last_pc_model_only_presence", {})
    pc_raw_conf_candidates = cam_data.get("last_pc_raw_conf_candidates", {})
    pc_raw_box_candidates = cam_data.get("last_pc_raw_box_candidates", {})
    source_video = os.path.basename(str(cam_data.get("source_path", "")))
    raw_people_total = int(cam_data.get("person_count_raw", 0))

    for pc_name in sorted(pc_states.keys(), key=pc_name_sort_key):
        state = pc_states.get(pc_name, {})
        pred_occupied = 1 if bool(state.get("person_present")) else 0
        pred_occupied_model_only = int(pc_model_only_presence.get(pc_name, 0))
        pred_people_count = int(pc_people_counts.get(pc_name, 0))
        raw_conf_list = [float(v) for v in pc_raw_conf_candidates.get(pc_name, [])]
        raw_box_list = [list(v) for v in pc_raw_box_candidates.get(pc_name, [])]
        current_person_id = state.get("current_person_id")
        current_person_text = str(current_person_id) if current_person_id else ""

        cam_data.setdefault("detection_detail_rows", []).append(
            {
                "run_tag": EVAL_TAG,
                "model_name": MODEL_NAME_FOR_LOG,
                "source_video": source_video,
                "time": sample_time_text,
                "clock": sample_clock,
                "t_sec": round(float(sample_ts), 2),
                "cam_idx": cam_idx,
                "cam_name": cam_data.get("name", ""),
                "pc_name": pc_name,
                "occupied_pred": pred_occupied,
                "occupied_pred_model_only": pred_occupied_model_only,
                "people_count_pred": pred_people_count,
                "pc_raw_conf_count": len(raw_conf_list),
                "pc_raw_conf_list_json": json.dumps(raw_conf_list, separators=(",", ":")),
                "pc_conf_threshold_applied": round(get_conf_threshold_for_pc(pc_name), 4),
                "pc_raw_box_count": len(raw_box_list),
                "pc_raw_box_list_json": json.dumps(raw_box_list, separators=(",", ":")),
                "pc_iou_threshold_applied": round(get_iou_threshold_for_pc(pc_name), 4),
                "raw_people_count_pred": raw_people_total,
                "current_person_ids_pred": current_person_text,
            }
        )


def collect_eval_rows(cam_idx, cam_data, sample_ts):
    if not EVAL_MODE:
        return

    gt_lookup = cam_data.get("eval_groundtruth", {}).get("lookup", {})
    if not gt_lookup:
        return

    sample_time_text = format_video_timestamp(sample_ts)
    sample_clock = format_video_clock(sample_ts)
    pc_states = cam_data.get("pc_states", {})
    pc_people_counts = cam_data.get("last_pc_people_counts", {})
    pc_model_only_presence = cam_data.get("last_pc_model_only_presence", {})
    pc_raw_conf_candidates = cam_data.get("last_pc_raw_conf_candidates", {})
    pc_raw_box_candidates = cam_data.get("last_pc_raw_box_candidates", {})
    source_video = os.path.basename(str(cam_data.get("source_path", "")))

    for pc_name in sorted(pc_states.keys(), key=pc_name_sort_key):
        state = pc_states.get(pc_name, {})
        pred_occupied = 1 if bool(state.get("person_present")) else 0
        pred_occupied_model_only = int(pc_model_only_presence.get(pc_name, 0))
        pred_people_count = int(pc_people_counts.get(pc_name, 0))
        raw_conf_list = [float(v) for v in pc_raw_conf_candidates.get(pc_name, [])]
        raw_box_list = [list(v) for v in pc_raw_box_candidates.get(pc_name, [])]
        current_person_id = state.get("current_person_id")
        current_person_text = str(current_person_id) if current_person_id else ""

        gt = gt_lookup.get((sample_time_text, pc_name), {})
        occupied_gt = gt.get("occupied_gt", "")
        people_count_gt = gt.get("people_count_gt", "")

        match_occupied = ""
        abs_people_count_error = ""
        if occupied_gt != "":
            match_occupied = int(pred_occupied == int(occupied_gt))
        if people_count_gt != "":
            abs_people_count_error = abs(int(pred_people_count) - int(people_count_gt))

        cam_data.setdefault("eval_detail_rows", []).append(
            {
                "eval_tag": EVAL_TAG,
                "model_name": MODEL_NAME_FOR_LOG,
                "source_video": source_video,
                "time": sample_time_text,
                "clock": sample_clock,
                "t_sec": round(float(sample_ts), 2),
                "cam_idx": cam_idx,
                "cam_name": cam_data.get("name", ""),
                "pc_name": pc_name,
                "occupied_pred": pred_occupied,
                "occupied_pred_model_only": pred_occupied_model_only,
                "people_count_pred": pred_people_count,
                "pc_raw_conf_count": len(raw_conf_list),
                "pc_raw_conf_list_json": json.dumps(raw_conf_list, separators=(",", ":")),
                "pc_conf_threshold_applied": round(get_conf_threshold_for_pc(pc_name), 4),
                "pc_raw_box_count": len(raw_box_list),
                "pc_raw_box_list_json": json.dumps(raw_box_list, separators=(",", ":")),
                "pc_iou_threshold_applied": round(get_iou_threshold_for_pc(pc_name), 4),
                "current_person_ids_pred": current_person_text,
                "occupied_gt": occupied_gt,
                "people_count_gt": people_count_gt,
                "match_occupied": match_occupied,
                "abs_people_count_error": abs_people_count_error,
            }
        )

        update_eval_sessions(cam_data, pc_name, current_person_id, sample_ts)


def write_detection_outputs(cams):
    os.makedirs(EVAL_LOG_ROOT, exist_ok=True)
    for cam_idx, cam_data in cams.items():
        cam_label = cam_data.get("label", to_safe_label(cam_data.get("name", f"cam{cam_idx}")))
        cam_name = cam_data.get("name", cam_label)
        cam_eval_dir = os.path.join(EVAL_LOG_ROOT, cam_label)
        os.makedirs(cam_eval_dir, exist_ok=True)

        detail_rows = cam_data.get("detection_detail_rows", [])
        detail_path = os.path.join(cam_eval_dir, f"detection_detail_{cam_label}_{EVAL_TAG}.csv")
        detail_columns = [
            "run_tag", "model_name", "source_video", "time", "clock", "t_sec", "cam_idx", "cam_name",
            "pc_name", "occupied_pred", "occupied_pred_model_only", "people_count_pred", "pc_raw_conf_count",
            "pc_raw_conf_list_json", "pc_conf_threshold_applied", "pc_raw_box_count", "pc_raw_box_list_json",
            "pc_iou_threshold_applied", "raw_people_count_pred", "current_person_ids_pred",
        ]
        pd.DataFrame(detail_rows, columns=detail_columns).to_csv(detail_path, index=False)

        print(f"Detection snapshot CSV saved to {detail_path}")


def flush_eval_active_sessions(cam_data, end_ts):
    if not EVAL_MODE:
        return

    active = cam_data.get("eval_active_sessions", {})
    if not active:
        return

    sessions = cam_data.setdefault("eval_user_sessions", [])
    for pc_name, existing in list(active.items()):
        sessions.append(
            {
                "pc_name": pc_name,
                "person_id_pred": existing.get("person_id_pred", ""),
                "start_time": existing.get("start_time", ""),
                "end_time": format_video_timestamp(end_ts),
                "duration_sec": round(max(0.0, float(end_ts) - float(existing.get("start_ts", end_ts))), 2),
            }
        )
    active.clear()


def compute_eval_metrics_for_rows(rows, sample_interval_sec=EVAL_SAMPLE_SEC):
    scored_rows = [
        row for row in rows
        if row.get("occupied_gt", "") != "" and row.get("people_count_gt", "") != ""
    ]
    if not scored_rows:
        return None

    tp = tn = fp = fn = 0
    people_abs_errors = []
    people_exact_matches = 0
    occupied_pred_samples = 0
    occupied_gt_samples = 0

    for row in scored_rows:
        pred = int(row.get("occupied_pred", 0))
        gt = int(row.get("occupied_gt", 0))
        pred_people = int(row.get("people_count_pred", 0))
        gt_people = int(row.get("people_count_gt", 0))

        occupied_pred_samples += pred
        occupied_gt_samples += gt

        if pred == 1 and gt == 1:
            tp += 1
        elif pred == 0 and gt == 0:
            tn += 1
        elif pred == 1 and gt == 0:
            fp += 1
        elif pred == 0 and gt == 1:
            fn += 1

        err = abs(pred_people - gt_people)
        people_abs_errors.append(err)
        if err == 0:
            people_exact_matches += 1

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    mae_people_count = (sum(people_abs_errors) / len(people_abs_errors)) if people_abs_errors else 0.0
    match_rate_people_count_exact = (people_exact_matches / len(people_abs_errors)) if people_abs_errors else 0.0
    occupied_time_pred_sec = float(occupied_pred_samples) * float(sample_interval_sec)
    occupied_time_gt_sec = float(occupied_gt_samples) * float(sample_interval_sec)
    occupied_time_abs_error_sec = abs(occupied_time_pred_sec - occupied_time_gt_sec)

    return {
        "samples": total,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "mae_people_count": round(mae_people_count, 4),
        "match_rate_people_count_exact": round(match_rate_people_count_exact, 4),
        "occupied_time_pred_sec": round(occupied_time_pred_sec, 4),
        "occupied_time_gt_sec": round(occupied_time_gt_sec, 4),
        "occupied_time_abs_error_sec": round(occupied_time_abs_error_sec, 4),
    }


def build_occupancy_intervals_from_detail(
    detail_rows,
    pc_name,
    debounce_sec=2.0,
    sample_interval_sec=1.0,
    cam_name=None,
):
    """
    Build continuous occupancy intervals from per-second detail samples.
    Filters for given pc_name and groups consecutive occupied_pred=1 samples.
    Debounce: ignore bursts shorter than debounce_sec.
    Returns list of (start_ts, end_ts) tuples in seconds.
    """
    pc_rows = []
    for row in detail_rows:
        if row.get("pc_name") != pc_name:
            continue
        if cam_name is not None and str(row.get("cam_name", "")) != str(cam_name):
            continue
        pc_rows.append(row)
    if not pc_rows:
        return []
    
    # Sort by t_sec
    pc_rows_sorted = sorted(pc_rows, key=lambda r: float(r.get("t_sec", 0)))
    
    intervals = []
    in_interval = False
    interval_start = None
    last_occupied = None
    
    for row in pc_rows_sorted:
        occupied_pred = int(row.get("occupied_pred", 0))
        t_sec = float(row.get("t_sec", 0))
        
        if occupied_pred == 1:
            if not in_interval:
                interval_start = t_sec
                in_interval = True
            last_occupied = t_sec
        else:
            if in_interval and last_occupied is not None:
                duration = last_occupied - interval_start
                if duration >= debounce_sec:
                    intervals.append((interval_start, last_occupied + float(sample_interval_sec)))
                in_interval = False
                last_occupied = None
    
    # Close any open interval at end
    if in_interval and last_occupied is not None:
        duration = last_occupied - interval_start
        if duration >= debounce_sec:
            intervals.append((interval_start, last_occupied + float(sample_interval_sec)))
    
    return sorted(intervals)


def build_gt_occupancy_intervals(gt_lookup, pc_name, video_end_ts=None):
    """
    Build continuous occupancy intervals from sparse GT snapshots using forward-fill.
    Consecutive occupied samples are merged into one interval, matching see_roi_conf.py.
    Returns list of (start_ts, end_ts) tuples in seconds.
    """
    if not gt_lookup or not pc_name:
        return []
    
    # Get all GT rows for this PC, sorted by time
    gt_rows = [(time_text, gt_info) for (time_text, pc), gt_info in gt_lookup.items() if pc == pc_name]
    if not gt_rows:
        return []
    
    try:
        gt_rows_sorted = sorted(gt_rows, key=lambda x: time.mktime(time.strptime(x[0], "%Y-%m-%d %H:%M:%S")))
    except Exception:
        return []
    
    timeline = {}
    for time_text, gt_info in gt_rows_sorted:
        try:
            ts = time.mktime(time.strptime(time_text, "%Y-%m-%d %H:%M:%S"))
        except Exception:
            continue
        timeline[ts] = 1 if int(gt_info.get("occupied_gt", 0)) > 0 else 0

    points = sorted(timeline.items(), key=lambda item: item[0])
    if not points:
        return []

    intervals = []
    in_interval = False
    interval_start = None

    for i, (cur_sec, cur_occupied) in enumerate(points[:-1]):
        next_sec, next_occupied = points[i + 1]

        if cur_occupied == 1 and not in_interval:
            interval_start = cur_sec
            in_interval = True

        if in_interval and next_occupied == 0:
            intervals.append((interval_start, next_sec))
            in_interval = False
            interval_start = None

    last_sec, last_occupied = points[-1]
    if last_occupied == 1:
        if not in_interval:
            interval_start = last_sec
        tail_end = video_end_ts if video_end_ts else (last_sec + 900)
        intervals.append((interval_start, tail_end))
    
    return sorted(intervals)


def compute_interval_overlap_sec(interval1, interval2):
    """Compute overlap in seconds between two (start, end) intervals."""
    start = max(interval1[0], interval2[0])
    end = min(interval1[1], interval2[1])
    return max(0, end - start)


def compute_duration_metrics(detail_rows, gt_lookup, pc_name, video_end_ts=None):
    """
    Compute seat-time efficiency metrics: coverage, duration error, missed sessions.
    detail_rows: list of eval detail dicts with occupied_pred
    gt_lookup: dict (time_text, pc_name) -> {occupied_gt, people_count_gt, ...}
    pc_name: PC to evaluate
    video_end_ts: unix timestamp of video end (for GT interval closure)
    """
    pred_intervals = build_occupancy_intervals_from_detail(
        detail_rows,
        pc_name,
        debounce_sec=2.0,
        sample_interval_sec=EVAL_SAMPLE_SEC,
    )
    gt_intervals = build_gt_occupancy_intervals(gt_lookup, pc_name, video_end_ts)
    
    if not gt_intervals:
        return None
    
    # Compute GT total occupied time
    gt_total_sec = sum(end - start for start, end in gt_intervals)
    
    # Compute predicted total occupied time
    pred_total_sec = sum(end - start for start, end in pred_intervals)
    
    # Compute coverage: overlap / gt_total
    total_overlap_sec = 0
    for pred_interval in pred_intervals:
        for gt_interval in gt_intervals:
            total_overlap_sec += compute_interval_overlap_sec(pred_interval, gt_interval)
    
    coverage = total_overlap_sec / gt_total_sec if gt_total_sec > 0 else 0.0
    
    # Duration error
    duration_error_sec = abs(pred_total_sec - gt_total_sec)
    duration_error_ratio = duration_error_sec / gt_total_sec if gt_total_sec > 0 else 0.0
    accuracy_percent = coverage * 100.0
    
    # Over-occupancy: predicted but not in GT
    over_occupancy_sec = pred_total_sec - total_overlap_sec
    
    # Missed occupancy: GT but not predicted
    missed_occupancy_sec = gt_total_sec - total_overlap_sec
    
    return {
        "gt_occupied_sec": round(gt_total_sec, 2),
        "pred_occupied_sec": round(pred_total_sec, 2),
        "overlap_sec": round(total_overlap_sec, 2),
        "coverage": round(coverage, 4),
        "accuracy_percent": round(accuracy_percent, 2),
        "duration_error_sec": round(duration_error_sec, 2),
        "duration_error_ratio": round(duration_error_ratio, 4),
        "over_occupancy_sec": round(over_occupancy_sec, 2),
        "missed_occupancy_sec": round(missed_occupancy_sec, 2),
        "gt_intervals": len(gt_intervals),
        "pred_intervals": len(pred_intervals),
    }


def build_eval_detection_period_rows(cams):
    rows = []
    for cam_idx, cam_data in cams.items():
        detail_rows = cam_data.get("eval_detail_rows", [])
        if not detail_rows:
            continue

        cam_name = str(cam_data.get("name", ""))
        source_video = os.path.basename(str(cam_data.get("source_path", "")))
        model_name = MODEL_NAME_FOR_LOG
        pc_names = sorted(
            {str(row.get("pc_name", "")).strip() for row in detail_rows if str(row.get("pc_name", "")).strip()},
            key=pc_name_sort_key,
        )

        for pc_name in pc_names:
            periods = build_occupancy_intervals_from_detail(
                detail_rows,
                pc_name,
                debounce_sec=0.0,
                sample_interval_sec=EVAL_SAMPLE_SEC,
                cam_name=cam_name,
            )
            for start_ts, end_ts in periods:
                start_clock = format_compact_video_clock(start_ts)
                end_clock = format_compact_video_clock(end_ts)
                rows.append(
                    {
                        "eval_tag": EVAL_TAG,
                        "model_name": model_name,
                        "source_video": source_video,
                        "cam_idx": cam_idx,
                        "cam_name": cam_name,
                        "pc_name": pc_name,
                        "start_clock": start_clock,
                        "end_clock": end_clock,
                        "period": f"{start_clock} - {end_clock}",
                        "start_t_sec": round(float(start_ts), 2),
                        "end_t_sec": round(float(end_ts), 2),
                        "duration_sec": round(max(0.0, float(end_ts) - float(start_ts)), 2),
                    }
                )

    rows.sort(
        key=lambda row: (
            pc_name_sort_key(row.get("pc_name", "")),
            str(row.get("cam_name", "")),
            float(row.get("start_t_sec", 0.0)),
        )
    )
    return rows


def run_eval_only_mode(eval_log_root, groundtruth_dir):
    """
    Re-evaluate existing eval outputs using duration-based metrics.
    This delegates to the standalone duration evaluator so eval-only and the
    standalone tool share the same CSV discovery and summary output.
    """
    print("\n=== Eval-Only Mode (Duration-Based Metrics) ===")
    print(f"Eval log root: {eval_log_root}")
    print(f"Groundtruth dir: {groundtruth_dir}")
    print(f"Config path: {CONFIG_FILE_PATH}")

    try:
        import importlib.util

        module_path = os.path.join(os.path.dirname(__file__), "eval_duration_based.py")
        spec = importlib.util.spec_from_file_location("eval_duration_based", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load evaluator from {module_path}")

        evaluator_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(evaluator_module)
        run_eval_only_duration = evaluator_module.run_eval_only_duration

        success = run_eval_only_duration(eval_log_root, groundtruth_dir, CONFIG_FILE_PATH)
        if success:
            print("Eval-only duration summary completed.")
        return
    except Exception as e:
        print(f"Failed to run shared duration evaluator: {e}")

    print("No metrics computed.")


def write_eval_outputs(cams):
    if not EVAL_MODE:
        return

    os.makedirs(EVAL_LOG_ROOT, exist_ok=True)
    summary_rows = []
    all_detail_rows = []

    for cam_idx, cam_data in cams.items():
        cam_label = cam_data.get("label", to_safe_label(cam_data.get("name", f"cam{cam_idx}")))
        cam_name = cam_data.get("name", cam_label)
        cam_eval_dir = os.path.join(EVAL_LOG_ROOT, cam_label)
        os.makedirs(cam_eval_dir, exist_ok=True)

        final_ts = float(cam_data.get("last_video_time", 0.0))
        flush_eval_active_sessions(cam_data, final_ts)

        detail_rows = cam_data.get("eval_detail_rows", [])
        all_detail_rows.extend(detail_rows)
        detail_path = os.path.join(cam_eval_dir, f"eval_detail_{cam_label}_{EVAL_TAG}.csv")
        detail_columns = [
            "eval_tag", "model_name", "source_video", "time", "clock", "t_sec", "cam_idx", "cam_name",
            "pc_name", "occupied_pred", "occupied_pred_model_only", "people_count_pred", "pc_raw_conf_count",
            "pc_raw_conf_list_json", "pc_conf_threshold_applied", "pc_raw_box_count", "pc_raw_box_list_json",
            "pc_iou_threshold_applied", "current_person_ids_pred",
            "occupied_gt", "people_count_gt", "match_occupied", "abs_people_count_error",
        ]
        pd.DataFrame(detail_rows, columns=detail_columns).to_csv(detail_path, index=False)

        session_rows = []
        for session in cam_data.get("eval_user_sessions", []):
            session_rows.append(
                {
                    "eval_tag": EVAL_TAG,
                    "model_name": MODEL_NAME_FOR_LOG,
                    "source_video": os.path.basename(str(cam_data.get("source_path", ""))),
                    "cam_name": cam_name,
                    "pc_name": session.get("pc_name", ""),
                    "person_id_pred": session.get("person_id_pred", ""),
                    "start_time": session.get("start_time", ""),
                    "end_time": session.get("end_time", ""),
                    "duration_sec": session.get("duration_sec", 0.0),
                }
            )

        session_path = os.path.join(cam_eval_dir, f"eval_sessions_{cam_label}_{EVAL_TAG}.csv")
        session_columns = [
            "eval_tag", "model_name", "source_video", "cam_name", "pc_name", "person_id_pred",
            "start_time", "end_time", "duration_sec",
        ]
        pd.DataFrame(session_rows, columns=session_columns).to_csv(session_path, index=False)

        if detail_rows:
            cam_df = pd.DataFrame(detail_rows)
            for pc_name, group in cam_df.groupby("pc_name"):
                metrics = compute_eval_metrics_for_rows(group.to_dict("records"))
                if metrics is None:
                    continue
                summary_rows.append(
                    {
                        "model_name": MODEL_NAME_FOR_LOG,
                        "cam_name": cam_name,
                        "pc_name": pc_name,
                        **metrics,
                    }
                )

            cam_metrics = compute_eval_metrics_for_rows(detail_rows)
            if cam_metrics is not None:
                summary_rows.append(
                    {
                        "model_name": MODEL_NAME_FOR_LOG,
                        "cam_name": cam_name,
                        "pc_name": "ALL",
                        **cam_metrics,
                    }
                )

    global_metrics = compute_eval_metrics_for_rows(all_detail_rows)
    if global_metrics is not None:
        summary_rows.append(
            {
                "model_name": MODEL_NAME_FOR_LOG,
                "cam_name": "ALL",
                "pc_name": "ALL",
                **global_metrics,
            }
        )

    summary_rows.sort(
        key=lambda row: (
            str(row.get("cam_name", "")) == "ALL",
            str(row.get("cam_name", "")),
            str(row.get("pc_name", "")) == "ALL",
            pc_name_sort_key(row.get("pc_name", "")),
        )
    )

    summary_path = os.path.join(EVAL_LOG_ROOT, f"eval_summary_{EVAL_TAG}.csv")
    summary_columns = [
        "pc_name", "cam_name", "samples", "tp", "tn", "fp", "fn",
        "accuracy", "precision", "recall", "f1", "mae_people_count", "match_rate_people_count_exact",
        "occupied_time_pred_sec", "occupied_time_gt_sec", "occupied_time_abs_error_sec",
        "model_name",
    ]
    pd.DataFrame(summary_rows, columns=summary_columns).to_csv(summary_path, index=False)

    periods_rows = build_eval_detection_period_rows(cams)
    periods_path = os.path.join(EVAL_LOG_ROOT, f"eval_pc_detection_periods_{EVAL_TAG}.csv")
    periods_columns = [
        "pc_name", "cam_name", "start_clock", "end_clock", "period", "duration_sec",
        "start_t_sec", "end_t_sec", "source_video", "model_name", "eval_tag", "cam_idx",
    ]
    pd.DataFrame(periods_rows, columns=periods_columns).to_csv(periods_path, index=False)

    print("\n=== Eval Summary ===")
    print(f"Eval tag: {EVAL_TAG}")
    print(f"Model: {MODEL_NAME_FOR_LOG}")
    print(f"Eval outputs root: {EVAL_LOG_ROOT}")
    print(f"Summary CSV: {summary_path}")
    print(f"Detection periods CSV: {periods_path}")
    for row in summary_rows:
        if row.get("pc_name") in ("ALL", ""):
            continue
        print(
            f"{row['cam_name']} {row['pc_name']}: acc={row['accuracy']:.4f}, "
            f"prec={row['precision']:.4f}, rec={row['recall']:.4f}, f1={row['f1']:.4f}"
        )


def append_rows_to_daily_csv(rows, columns, output_dir, file_prefix, default_day_tag):
    grouped_rows = {}
    for row in rows or []:
        row_time = row.get("time") if isinstance(row, dict) else None
        day_tag = day_tag_from_time_text(row_time, default_day_tag)
        grouped_rows.setdefault(day_tag, []).append(row)

    if not grouped_rows:
        grouped_rows[default_day_tag] = []

    written_paths = []
    os.makedirs(output_dir, exist_ok=True)

    for day_tag in sorted(grouped_rows.keys()):
        file_path = os.path.join(output_dir, f"{file_prefix}_{day_tag}.csv")
        day_df = pd.DataFrame(grouped_rows[day_tag], columns=columns)
        write_header = not os.path.exists(file_path)
        day_df.to_csv(file_path, mode="a", index=False, header=write_header)
        written_paths.append(file_path)

    return written_paths


def realtime_pc_state_writer(cams, csv_path, stop_event, interval_sec=1.0):
    while not stop_event.is_set():
        try:
            write_pc_state_csv(cams, csv_path)
        except Exception as e:
            print(f"Failed to update realtime PC-state CSV: {e}")
        stop_event.wait(interval_sec)

    # final flush
    try:
        write_pc_state_csv(cams, csv_path)
    except Exception as e:
        print(f"Failed to finalize realtime PC-state CSV: {e}")


def cleanup_empty_log_folders(log_dir):
    """Delete empty folders in the log directory and their empty parent directories."""
    if not os.path.exists(log_dir):
        return
    
    try:
        # Walk through all subdirectories bottom-up
        for root, dirs, files in os.walk(log_dir, topdown=False):
            for folder in dirs:
                folder_path = os.path.join(root, folder)
                try:
                    # Check if directory is empty
                    if not os.listdir(folder_path):
                        os.rmdir(folder_path)
                        print(f"Deleted empty log folder: {folder_path}")
                except Exception as e:
                    # Silently ignore errors for individual folders
                    pass
        
        # Check if the main log directory is also empty and delete if it is
        if os.path.exists(log_dir) and not os.listdir(log_dir):
            os.rmdir(log_dir)
            print(f"Deleted empty log directory: {log_dir}")
    except Exception as e:
        print(f"Error during cleanup of empty log folders: {e}")


def build_session_config_string(cams):
    """Build session configuration string for logging: file | hardware | PC ROI | Monitor ROI | SHOW_WINDOWS"""
    # Determine hardware
    hardware = "gpu" if device.startswith("cuda") else "cpu"
    
    # Determine if PC ROIs were loaded in any camera
    pc_roi_loaded = any(len(cam_data.get("pc_rois", [])) > 0 for cam_data in cams.values())
    pc_roi_status = "PC roi loaded" if pc_roi_loaded else "PC roi not loaded"
    
    # Determine if Monitor ROIs were loaded in any camera
    monitor_roi_loaded = any(len(cam_data.get("monitor_rois", [])) > 0 for cam_data in cams.values())
    monitor_roi_status = "Monitor roi loaded" if monitor_roi_loaded else "Monitor roi not loaded"
    
    # Get SHOW_WINDOWS setting
    show_windows_status = SHOW_WINDOWS
    
    return f"threaded_video_mode.py | {hardware} | {pc_roi_status} | {monitor_roi_status} | {show_windows_status}"


def create_daily_summary_report(cams, day_tag, output_dir):
    """Create a daily summary report aggregating person detection and PC usage data"""
    try:
        summary_rows = []
        
        # Collect all person data from daily CSV files
        all_persons = set()
        all_pc_usage = {}
        
        for cam_idx, cam_data in cams.items():
            cam_label = cam_data.get("label", to_safe_label(cam_data.get("name", f"cam{cam_idx}")))
            
            # Read people CSV
            people_csv = os.path.join(cam_data.get("log_dir", LOG_BASE_DIR), 
                                      f"people_with_conf_and_roi_{cam_label}_{day_tag}.csv")
            if os.path.exists(people_csv):
                try:
                    people_df = pd.read_csv(people_csv)
                    for _, row in people_df.iterrows():
                        all_persons.add(str(row.get("person_id", "unknown")))
                        pc = row.get("PCnum")
                        if pc and str(pc).lower() not in ["none", "nan", ""]:
                            pc_key = str(pc)
                            if pc_key not in all_pc_usage:
                                all_pc_usage[pc_key] = {"persons": set(), "event_count": 0}
                            all_pc_usage[pc_key]["persons"].add(str(row.get("person_id", "unknown")))
                except Exception as e:
                    print(f"Warning: Failed to read people CSV {people_csv}: {e}")
            
            # Read PC activity events CSV
            event_csv = os.path.join(cam_data.get("log_dir", LOG_BASE_DIR),
                                    f"pc_activity_events_{cam_label}_{day_tag}.csv")
            if os.path.exists(event_csv):
                try:
                    event_df = pd.read_csv(event_csv)
                    for _, row in event_df.iterrows():
                        pc = row.get("pc_name")
                        if pc and str(pc).lower() not in ["none", "nan", ""]:
                            pc_key = str(pc)
                            if pc_key not in all_pc_usage:
                                all_pc_usage[pc_key] = {"persons": set(), "event_count": 0}
                            all_pc_usage[pc_key]["event_count"] += 1
                            all_pc_usage[pc_key]["persons"].add(str(row.get("person_id", "unknown")))
                except Exception as e:
                    print(f"Warning: Failed to read activity CSV {event_csv}: {e}")
        
        # Build summary rows
        date_str = f"{day_tag[0:4]}-{day_tag[4:6]}-{day_tag[6:8]}"
        
        summary_rows.append({
            "date": date_str,
            "day_tag": day_tag,
            "total_unique_persons": len(all_persons),
            "persons_list": ", ".join(sorted(all_persons)) if all_persons else "None",
            "model_name": "yolov8s",
        })
        
        # Add per-PC usage summary
        for pc_name in sorted(all_pc_usage.keys()):
            summary_rows.append({
                "date": date_str,
                "day_tag": day_tag,
                "pc_name": pc_name,
                "pc_usage_count": all_pc_usage[pc_name]["event_count"],
                "pc_users": ", ".join(sorted(all_pc_usage[pc_name]["persons"])) if all_pc_usage[pc_name]["persons"] else "None",
                "model_name": "yolov8s",
            })
        
        # Write summary CSV
        if summary_rows:
            os.makedirs(output_dir, exist_ok=True)
            summary_file = os.path.join(output_dir, f"daily_summary_{day_tag}.csv")
            summary_df = pd.DataFrame(summary_rows)
            summary_df.to_csv(summary_file, index=False)
            print(f"Daily summary report created: {summary_file}")
            return summary_file
        return None
    except Exception as e:
        print(f"Failed to create daily summary report: {e}")
        return None

# Create base directories
def build_camera_states():
    # Create base directories
    os.makedirs(LOG_BASE_DIR, exist_ok=True)
    os.makedirs(ROI_BASE_DIR, exist_ok=True)

    cams = {}
    video_paths = discover_video_paths(VIDEO_INPUT_DIR, VIDEO_GLOB_PATTERNS, VIDEO_MAX_SOURCES)
    if not video_paths:
        raise RuntimeError(f"No video files found in {VIDEO_INPUT_DIR} using patterns {VIDEO_GLOB_PATTERNS}")

    for cam_idx, video_path in enumerate(video_paths):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Skipping unreadable video: {video_path}")
            continue

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        cam_name = os.path.splitext(os.path.basename(video_path))[0]
        cam_label = to_safe_label(cam_name)
        video_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if video_fps <= 0:
            video_fps = VIDEO_TIME_FALLBACK_FPS

        # load PC ROI polygons if enabled
        pc_rois = []
        if ENABLE_PC_ROI:
            pc_rois = load_camera_rois(cam_label)
            if pc_rois:
                print(f"{cam_name}: loaded {len(pc_rois)} PC ROI(s)")

        # load monitor ROI polygons if enabled
        monitor_rois = []
        if ENABLE_MONITOR_ROI:
            monitor_rois = load_camera_rois(cam_label, MONITOR_CSV_SUFFIX)
            if monitor_rois:
                print(f"{cam_name}: loaded {len(monitor_rois)} monitor ROI(s)")

        gate_rois = load_camera_rois(cam_label, GATE_ROI_CSV_SUFFIX)
        if gate_rois:
            print(f"{cam_name}: loaded {len(gate_rois)} gate ROI(s)")

        pc_states = init_pc_states(pc_rois, monitor_rois)
        eval_groundtruth = None
        if EVAL_MODE:
            eval_groundtruth = load_groundtruth_for_camera(cam_name, cam_label)
            print(f"{cam_name}: loaded groundtruth -> {eval_groundtruth['path']}")

        cams[cam_idx] = {
            "cap": cap,
            "tracked_persons": {},
            "person_id_counter": 0,
            "used_ids": set(),
            "logs": [],
            "window": f"YOLO Person Detection ({cam_name})",
            "roi_dir": os.path.join(ROI_BASE_DIR, cam_label),
            "log_dir": os.path.join(LOG_BASE_DIR, cam_label),
            "report_dir": os.path.join(LOG_BASE_DIR, "report", cam_label),
            "last_frame_time": None,
            "fps": 0.0,
            # process every N frames (1 = every frame). Increase to 2 or 3 to reduce inference load.
            "process_every_n_frames": PROCESS_EVERY_N_FRAMES,
            "frame_counter": 0,
            # cache last annotated frame to display when skipping inference
            "last_annotated_frame": None,
            "person_count_history": deque(),
            "person_count_raw": 0,
            "person_count_smoothed": 0,
            "detection_active_last": None,
            # performance tracking
            "frames_seen": 0,
            "total_latency_ms": 0.0,
            "inference_runs": 0,
            "total_inference_time_ms": 0.0,
            "first_frame_time": None,
            "first_video_time": None,
            "last_video_time": None,
            "name": cam_name,
            "label": cam_label,
            "source_path": video_path,
            "video_fps": video_fps,
            "video_last_ts": 0.0,
            "pc_rois": pc_rois,
            "monitor_rois": monitor_rois,
            "gate_rois": gate_rois,
            "pc_states": pc_states,
            "pc_event_logs": [],
            "pc_unattended_logs": [],
            "last_pc_people_counts": {},
            "last_pc_model_only_presence": {},
            "last_pc_raw_conf_candidates": {},
            "last_pc_raw_box_candidates": {},
            "eval_groundtruth": eval_groundtruth,
            "eval_detail_rows": [],
            "detection_detail_rows": [],
            "eval_user_sessions": [],
            "eval_active_sessions": {},
            "next_detection_sample_ts": 0.0,
            "zone_roi_report_rows": [],
            "zone_roi_report_last_sec": None,
            "last_raw_frame": None,
            "disappear_person_counters": {},
            "motion_subtractor": _make_motion_subtractor() if ENABLE_MOTION_GATING else None,
            "motion_warmup_done": False,
            "motion_warmup_frames": 0,
            "last_motion_ratio": 0.0,
            "motion_ratio_buffer": deque(),  # Store (timestamp, motion_ratio) for 2-sec averaging
        }
        os.makedirs(cams[cam_idx]["roi_dir"], exist_ok=True)
        os.makedirs(cams[cam_idx]["log_dir"], exist_ok=True)
        os.makedirs(cams[cam_idx]["report_dir"], exist_ok=True)

    if not cams:
        raise RuntimeError(f"No readable videos found in {VIDEO_INPUT_DIR}")

    return cams


def start_resource_monitor_if_enabled(cams):
    monitor_stop = None
    monitor_thread = None
    if ENABLE_RESOURCE_MONITOR:
        try:
            from tool.resource_monitor import start_resource_monitor

            monitor_stop, monitor_thread = start_resource_monitor(cams, device=device, sample_interval=1.0)
            print("Resource monitor started")
        except Exception as e:
            print(f"Failed to start resource monitor: {e}")

    return monitor_stop, monitor_thread


def print_session_banner(cams):
    print("=== Auto ID Assignment (Video Mode) ===")
    print(f"Model in use: {MODEL_NAME_FOR_LOG}")
    print(
        "Confidence threshold: "
        f"default={CONF_THRESHOLD:.2f}, mode={CONF_THRESHOLD_MODE}, "
        f"min_inference={MIN_CONF_THRESHOLD:.2f}, overrides={len(PC_CONF_THRESHOLD_OVERRIDES)}"
    )
    print(
        "IOU threshold: "
        f"default={IOU_THRESHOLD:.2f}, mode={IOU_THRESHOLD_MODE}, "
        f"overrides={len(PC_IOU_THRESHOLD_OVERRIDES)}"
    )
    if EVAL_MODE:
        print(f"Eval mode: ON | sample={EVAL_SAMPLE_SEC:.1f}s | groundtruth={GROUNDTRUTH_DIR}")
        print(f"Eval output root: {EVAL_LOG_ROOT}")
    for cam_data in cams.values():
        print(f"- {cam_data['name']} <= {cam_data['source_path']}")
    print("Press 'q' to quit")
    print("===================================\n")


# --- Threaded camera processing ---
def camera_thread_fn(cam_idx, cam_data, stop_event):
    try:
        while not stop_event.is_set():
            cap = cam_data["cap"]
            if not cap.isOpened():
                break

            loop_wall_start = time.time()
            ret, frame = cap.read()
            if not ret:
                break
            raw_frame = frame.copy()

            frame_time_sec = get_video_frame_time_seconds(cap, cam_data)
            if cam_data.get("first_video_time") is None:
                cam_data["first_video_time"] = frame_time_sec
            cam_data["last_video_time"] = frame_time_sec

            detection_active = is_detection_time_active()
            last_detection_active = cam_data.get("detection_active_last")
            if last_detection_active is None or last_detection_active != detection_active:
                state = "ON" if detection_active else "OFF"
                print(
                    f"{cam_data['name']}: YOLO detection {state} (video-time mode)"
                )
                cam_data["detection_active_last"] = detection_active
                if not detection_active:
                    cam_data["last_annotated_frame"] = None

            # increment per-camera frame counter and decide whether to run inference
            cam_data["frame_counter"] += 1
            frame_due = (
                (cam_data["frame_counter"] % cam_data["process_every_n_frames"] == 0)
                or (cam_data["last_annotated_frame"] is None)
            )

            motion_detected = True
            if detection_active and ENABLE_MOTION_GATING:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                fg_mask, motion_ratio = compute_motion_foreground(gray, cam_data.get("motion_subtractor"))
                cam_data["last_motion_ratio"] = motion_ratio

                # Add motion ratio to 2-second buffer
                motion_buffer = cam_data.setdefault("motion_ratio_buffer", deque())
                motion_buffer.append((frame_time_sec, motion_ratio))
                
                # Remove entries older than 2 seconds
                while motion_buffer and (frame_time_sec - motion_buffer[0][0]) > 2.0:
                    motion_buffer.popleft()
                
                # Calculate 2-second average motion ratio
                if motion_buffer:
                    avg_motion_ratio = sum(ratio for _, ratio in motion_buffer) / len(motion_buffer)
                else:
                    avg_motion_ratio = 0.0

                motion_detected = avg_motion_ratio >= MOTION_MIN_AREA_RATIO

            do_infer = detection_active and (
                frame_due and ((not ENABLE_MOTION_GATING) or motion_detected)
            )

            person_count = 0
            cache_frame_no_hold = None

            if do_infer:
                # run inference (use AMP autocast if CUDA available)
                inf_start = time.time()
                results = run_model_inference(frame)
                inf_end = time.time()
                cam_data["inference_runs"] += 1
                cam_data["total_inference_time_ms"] += (inf_end - inf_start) * 1000.0

                if cam_data["first_frame_time"] is None:
                    cam_data["first_frame_time"] = loop_wall_start

                pc_to_person = {}
                pc_people_counts = {}
                pc_raw_conf_candidates = {pc_name: [] for pc_name in cam_data.get("pc_states", {}).keys()}
                pc_raw_box_candidates = {pc_name: [] for pc_name in cam_data.get("pc_states", {}).keys()}
                matched_track_ids = set()
                detected_person_boxes = []

                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    if cls in PERSON_CLASS_IDS:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        current_box = (x1, y1, x2, y2)

                        # determine which PC this person is in
                        current_pc = get_pc_for_box(current_box, cam_data["pc_rois"]) if ENABLE_PC_ROI else None
                        if current_pc and current_pc in pc_raw_conf_candidates:
                            pc_raw_conf_candidates[current_pc].append(float(conf))
                            pc_raw_box_candidates[current_pc].append((x1, y1, x2, y2, float(conf)))
                        conf_threshold = get_conf_threshold_for_pc(current_pc)
                        if conf <= conf_threshold:
                            continue

                        person_count += 1
                        detected_person_boxes.append(current_box)

                        matched_id = match_box_to_person(
                            current_box,
                            cam_data["tracked_persons"],
                            frame_time_sec,
                            unavailable_ids=matched_track_ids,
                        )
                        if matched_id is None:
                            matched_id = match_box_to_recent_hold_track(
                                current_box,
                                cam_data["tracked_persons"],
                                frame_time_sec,
                                unavailable_ids=matched_track_ids,
                            )
                        if matched_id is not None:
                            matched_track_ids.add(matched_id)
                            pdata = cam_data["tracked_persons"][matched_id]
                            prev_box = pdata.get("last_box", current_box)
                            prev_seen_ts = float(pdata.get("last_seen_ts", frame_time_sec))
                            dt_track = max(1e-6, frame_time_sec - prev_seen_ts)
                            prev_cx, prev_cy = box_center(prev_box)
                            curr_cx, curr_cy = box_center(current_box)
                            measured_vx = (curr_cx - prev_cx) / dt_track
                            measured_vy = (curr_cy - prev_cy) / dt_track
                            old_vx, old_vy = pdata.get("velocity", (0.0, 0.0))
                            keep = TRACK_VELOCITY_SMOOTHING
                            add = 1.0 - keep
                            pdata["velocity"] = (
                                (old_vx * keep) + (measured_vx * add),
                                (old_vy * keep) + (measured_vy * add),
                            )
                            pdata["last_box"] = current_box
                            pdata["last_seen_ts"] = frame_time_sec
                            pdata["missing_since_ts"] = None
                            person_name = pdata.get("name", f"Person {matched_id}")

                            counted_pc = None
                            # PC dwell-time tracking
                            if current_pc:
                                if pdata.get("current_pc") == current_pc:
                                    # still in same PC, accumulate time
                                    pass
                                else:
                                    # entered new PC, start timer
                                    pdata["current_pc"] = current_pc
                                    pdata["pc_enter_time"] = frame_time_sec

                                # check if threshold met
                                dwell_time = frame_time_sec - pdata.get("pc_enter_time", frame_time_sec)
                                if dwell_time >= PEOPLE_COUNT_DWELL_SEC:
                                    counted_pc = current_pc
                                if dwell_time >= PERSON_OVERLAP_DWELL_SEC:
                                    pc_state = cam_data.get("pc_states", {}).get(current_pc, {})
                                    if pc_state.get("pc_on"):
                                        pdata["assigned_pc"] = current_pc
                                    else:
                                        pdata["assigned_pc"] = None
                            else:
                                # outside all PCs, reset
                                pdata["current_pc"] = None
                                pdata["pc_enter_time"] = None
                                pdata["assigned_pc"] = None

                            if counted_pc:
                                pc_people_counts[counted_pc] = pc_people_counts.get(counted_pc, 0) + 1

                            current_time = frame_time_sec
                            last_save = pdata.get("last_save", 0)
                            if person_name != f"Person {matched_id}" and current_time - last_save >= SAVE_INTERVAL_SEC:
                                roi = frame[y1:y2, x1:x2]
                                if roi.size > 0:
                                    person_folder = pdata["folder"]
                                    filename = f"ID{person_name}_{int(current_time * 1000)}.jpg"
                                    filepath = os.path.join(person_folder, filename)
                                    cv2.imwrite(filepath, roi)
                                    pdata["last_save"] = current_time
                                    cam_data["logs"].append({
                                        "time": format_video_timestamp(frame_time_sec),
                                        "person_id": person_name,
                                        "confidence": round(conf, 3),
                                        "roi_file": filepath,
                                        "PCnum": pdata.get("assigned_pc"),
                                        "model_name": "yolov8s",
                                    })
                                    print(f"{cam_data['name']}: Saved ID {person_name} at {format_video_clock(current_time)}")
                        else:
                            matched_id = cam_data["person_id_counter"]
                            cam_data["person_id_counter"] += 1
                            while True:
                                random_id = f"{random.randint(0, 999):03d}"
                                if random_id not in cam_data["used_ids"]:
                                    cam_data["used_ids"].add(random_id)
                                    break
                            person_folder = os.path.join(cam_data["roi_dir"], random_id)
                            os.makedirs(person_folder, exist_ok=True)
                            cam_data["tracked_persons"][matched_id] = {
                                "name": random_id,
                                "last_box": current_box,
                                "last_save": 0,
                                "folder": person_folder,
                                "current_pc": current_pc,
                                "pc_enter_time": frame_time_sec if current_pc else None,
                                "assigned_pc": None,
                                "velocity": (0.0, 0.0),
                                "last_seen_ts": frame_time_sec,
                                "missing_since_ts": None,
                            }
                            matched_track_ids.add(matched_id)
                            person_name = random_id
                            print(f"{cam_data['name']}: New person detected! Assigned ID: {random_id}")
                        color = (0, 255, 0)
                        label = f"ID:{person_name} conf:{conf:.2f}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                        if current_pc:
                            prev = pc_to_person.get(current_pc)
                            if prev is None or conf > prev[0]:
                                pc_to_person[current_pc] = (conf, person_name)

                # Cache a clean annotated frame before drawing hold overlays.
                cache_frame_no_hold = frame.copy()

                for pid, pdata in cam_data["tracked_persons"].items():
                    if pid in matched_track_ids:
                        continue
                    if pdata.get("missing_since_ts") is None:
                        pdata["missing_since_ts"] = frame_time_sec

                        # Report sudden disappear event when person vanishes away from camera corners.
                        last_box = pdata.get("last_box")
                        prev_raw_frame = cam_data.get("last_raw_frame")
                        gate_name = get_pc_for_box(last_box, cam_data.get("gate_rois", [])) if last_box else None
                        if (
                            last_box
                            and prev_raw_frame is not None
                            and not gate_name
                            and is_box_far_from_camera_corners(last_box, raw_frame.shape)
                        ):
                            person_name_for_report = str(pdata.get("name", f"Person {pid}"))
                            pc_name_for_report = (
                                pdata.get("assigned_pc")
                                or pdata.get("current_pc")
                                or "unknown"
                            )
                            save_sudden_disappear_report_frames(
                                cam_data,
                                prev_raw_frame,
                                raw_frame,
                                frame_time_sec,
                                person_name_for_report,
                                pc_name_for_report,
                                missing_box=last_box,
                            )

                    # Keep a short visual hold during brief detection dropouts.
                    last_box = pdata.get("last_box")
                    if last_box:
                        missing_sec = max(0.0, frame_time_sec - float(pdata.get("last_seen_ts", frame_time_sec)))
                        gate_name = get_pc_for_box(last_box, cam_data.get("gate_rois", []))
                        if gate_name:
                            # Leaving through gate ROI is normal: no hold and no snapshot.
                            continue
                        if HOLD_VISUAL_MIN_SEC <= missing_sec <= TRACK_MAX_MISSING_SEC:
                            # Suppress hold box when a fresh detection is near this track's last position.
                            near_fresh_detection = False
                            for det_box in detected_person_boxes:
                                if distance(last_box, det_box) <= max(TRACK_MATCH_DISTANCE_PX * 1.5, TRACK_MATCH_DISTANCE_PX + 30.0):
                                    near_fresh_detection = True
                                    break
                            if near_fresh_detection:
                                continue

                            x1, y1, x2, y2 = map(int, last_box)
                            hold_color = (0, 165, 255)
                            hold_name = str(pdata.get("name", f"Person {pid}"))
                            hold_label = f"ID:{hold_name} hold:{missing_sec:.1f}s"
                            cv2.rectangle(frame, (x1, y1), (x2, y2), hold_color, 2)
                            cv2.putText(frame, hold_label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, hold_color, 2)

                prune_stale_tracks(cam_data["tracked_persons"], frame_time_sec)

                # Use active tracks for displayed people count so brief misses do not flicker to zero.
                person_count = sum(
                    1
                    for pdata in cam_data["tracked_persons"].values()
                    if max(0.0, frame_time_sec - float(pdata.get("last_seen_ts", frame_time_sec))) <= TRACK_MAX_MISSING_SEC
                )

                pc_to_person_map = {pc_name: data[1] for pc_name, data in pc_to_person.items()}
                pc_model_only_presence = {pc_name: 0 for pc_name in cam_data.get("pc_states", {}).keys()}
                pc_people_counts = {pc_name: 0 for pc_name in cam_data.get("pc_states", {}).keys()}
                for pc_name, candidates in pc_raw_box_candidates.items():
                    conf_threshold = get_conf_threshold_for_pc(pc_name)
                    iou_threshold = get_iou_threshold_for_pc(pc_name)
                    kept_candidates = apply_pc_nms_candidates(candidates, iou_threshold, conf_threshold)
                    kept_count = len(kept_candidates)
                    pc_people_counts[pc_name] = kept_count
                    pc_model_only_presence[pc_name] = 1 if kept_count > 0 else 0
                    try:
                        fixed_kept = apply_pc_nms_candidates(candidates, IOU_THRESHOLD, CONF_THRESHOLD)
                        if len(kept_candidates) > 0 and len(fixed_kept) == 0:
                            log = cam_data.setdefault("dynamic_only_detections", [])
                            ts = frame_time_sec if 'frame_time_sec' in locals() else time.time()
                            image_path = None
                            try:
                                image_path = save_dynamic_fixed_comparison_report_frame(
                                    cam_data,
                                    frame,
                                    ts,
                                    pc_name,
                                    kept_candidates,
                                    fixed_kept,
                                    conf_threshold,
                                    CONF_THRESHOLD,
                                    iou_threshold,
                                    IOU_THRESHOLD,
                                )
                            except Exception:
                                image_path = None
                            log.append(
                                {
                                    "time": format_video_timestamp(ts),
                                    "clock": format_video_clock(ts),
                                    "pc_name": pc_name,
                                    "source": os.path.basename(str(cam_data.get("source_path", ""))),
                                    "dynamic_conf_threshold": round(conf_threshold, 4),
                                    "fixed_conf_threshold": round(CONF_THRESHOLD, 4),
                                    "dynamic_iou_threshold": round(iou_threshold, 4),
                                    "fixed_iou_threshold": round(IOU_THRESHOLD, 4),
                                    "kept_dynamic": [
                                        [int(b[0]), int(b[1]), int(b[2]), int(b[3]), round(float(b[4]), 4)]
                                        for b in kept_candidates
                                    ],
                                    "kept_fixed": [
                                        [int(b[0]), int(b[1]), int(b[2]), int(b[3]), round(float(b[4]), 4)]
                                        for b in fixed_kept
                                    ],
                                    "image_file": image_path or "",
                                }
                            )
                    except Exception:
                        pass

                cam_data["last_pc_model_only_presence"] = pc_model_only_presence
                cam_data["last_pc_raw_conf_candidates"] = {
                    pc_name: sorted([round(float(v), 4) for v in conf_list], reverse=True)
                    for pc_name, conf_list in pc_raw_conf_candidates.items()
                }
                cam_data["last_pc_raw_box_candidates"] = {
                    pc_name: [
                        [int(b[0]), int(b[1]), int(b[2]), int(b[3]), round(float(b[4]), 4)]
                        for b in sorted(candidates, key=lambda item: float(item[4]), reverse=True)
                    ]
                    for pc_name, candidates in pc_raw_box_candidates.items()
                }

                # Report track-hold losses so debugging snapshots are produced.
                hold_assignments_used = []
                for pid, pdata in cam_data["tracked_persons"].items():
                    if pid in matched_track_ids:
                        continue

                    missing_sec = max(0.0, frame_time_sec - float(pdata.get("last_seen_ts", frame_time_sec)))
                    if missing_sec > TRACK_MAX_MISSING_SEC:
                        continue

                    person_name = str(pdata.get("name", "")).strip()
                    if not person_name:
                        continue

                    last_box = pdata.get("last_box")
                    gate_name = get_pc_for_box(last_box, cam_data.get("gate_rois", [])) if last_box else None
                    if gate_name:
                        continue

                    guessed_pc = (
                        pdata.get("assigned_pc")
                        or pdata.get("current_pc")
                        or "unknown"
                    )
                    hold_assignments_used.append(
                        {
                            "person_id": person_name,
                            "pc_name": str(guessed_pc),
                        }
                    )

                if person_count == 0 and hold_assignments_used:
                    save_zone_roi_fallback_report_frame(
                        cam_data,
                        frame,
                        frame_time_sec,
                        hold_assignments_used,
                        reason="no_person_detected_track_hold",
                    )

                cam_data["last_pc_people_counts"] = pc_people_counts
                update_pc_states_from_monitor(frame, cam_data.get("monitor_rois", []), cam_data.get("pc_states", {}), frame_time_sec)
                update_pc_activity_events(
                    cam_data["name"],
                    cam_data.get("pc_states", {}),
                    pc_to_person_map,
                    frame_time_sec,
                    cam_data.get("pc_event_logs", []),
                    cam_data.get("pc_unattended_logs", []),
                )
            else:
                if detection_active:
                    if cam_data["last_annotated_frame"] is not None:
                        frame = cam_data["last_annotated_frame"].copy()
                else:
                    cv2.putText(frame, "Detection: OFF (schedule)", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                    cv2.putText(
                        frame,
                        f"Active hours: {DETECTION_START_HOUR_24:02d}:00-{DETECTION_END_HOUR_24:02d}:00",
                        (20, 72),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )

            if detection_active:
                raw_people_for_smoothing = person_count if do_infer else cam_data.get("person_count_raw", 0)
                smoothed_people = update_smoothed_person_count(cam_data, raw_people_for_smoothing, frame_time_sec)
                cv2.putText(frame, f"People: {smoothed_people}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                if do_infer:
                    cam_data["last_annotated_frame"] = cache_frame_no_hold.copy() if cache_frame_no_hold is not None else frame.copy()
            else:
                update_smoothed_person_count(cam_data, 0, frame_time_sec)

            # Motion detection status for overlay (video mode: always True since no motion gating)
            motion_detected = True
            if ENABLE_MOTION_GATING:
                motion_status = "YES" if detection_active and motion_detected else "NO" if detection_active else "N/A"
                cv2.putText(
                    frame,
                    f"BG Sub: ON | Motion: {motion_status} | YOLO: {'RUN' if do_infer else 'SKIP'}",
                    (20, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )
            else:
                cv2.putText(
                    frame,
                    f"BG Sub: OFF | YOLO: {'RUN' if do_infer else 'SKIP'}",
                    (20, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            next_sample_ts = float(cam_data.get("next_detection_sample_ts", 0.0))
            if next_sample_ts <= 0.0:
                next_sample_ts = float(frame_time_sec)
            while frame_time_sec >= next_sample_ts:
                collect_detection_rows(cam_idx, cam_data, next_sample_ts)
                if EVAL_MODE:
                    collect_eval_rows(cam_idx, cam_data, next_sample_ts)
                next_sample_ts += EVAL_SAMPLE_SEC
            cam_data["next_detection_sample_ts"] = next_sample_ts
            cam_data["last_raw_frame"] = raw_frame

            frame_end = time.time()
            latency_ms = (frame_end - loop_wall_start) * 1000.0
            prev_latency_ms = float(cam_data.get("last_latency_ms", latency_ms))
            display_latency_ms = (prev_latency_ms + latency_ms) / 2.0
            cam_data["last_latency_ms"] = latency_ms

            prev_fps = float(cam_data.get("fps", 0.0))
            current_fps = prev_fps
            cam_data["frames_seen"] += 1
            cam_data["total_latency_ms"] += latency_ms
            if cam_data["last_frame_time"] is not None:
                dt = frame_end - cam_data["last_frame_time"]
                if dt > 0:
                    current_fps = 1.0 / dt
            cam_data["fps"] = current_fps
            display_fps = (prev_fps + current_fps) / 2.0
            cam_data["last_frame_time"] = frame_end
            cv2.putText(frame, f"FPS: {display_fps:.1f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            cv2.putText(frame, f"Latency: {display_latency_ms:.1f} ms", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            if SHOW_WINDOWS == "show":
                display_frame = cv2.resize(frame, (Windows_width, Windows_height))
                cv2.imshow(cam_data["window"], display_frame)
                if cv2.getWindowProperty(cam_data["window"], cv2.WND_PROP_VISIBLE) < 1:
                    break
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    stop_event.set()
                    break
            elif SHOW_WINDOWS == "hide":
                pass

            if FRAME_CAP_INTERVAL_SEC > 0:
                remaining_sleep = FRAME_CAP_INTERVAL_SEC - (time.time() - loop_wall_start)
                if remaining_sleep > 0:
                    time.sleep(remaining_sleep)
    except KeyboardInterrupt:
        print(f"\nInterrupted by user (KeyboardInterrupt) in {cam_data['name']}")

def start_realtime_pc_state_writer(cams, stop_event):
    pc_state_all_csv = os.path.join(LOG_BASE_DIR, VIDEO_REALTIME_PC_STATE_FILENAME)
    pc_state_writer_thread = None
    if ENABLE_REALTIME_PC_STATE_CSV:
        # create file immediately so downstream readers can open it before first update cycle
        write_pc_state_csv(cams, pc_state_all_csv)
        pc_state_writer_thread = threading.Thread(
            target=realtime_pc_state_writer,
            args=(cams, pc_state_all_csv, stop_event, REALTIME_PC_STATE_WRITE_INTERVAL_SEC),
            daemon=True,
        )
        pc_state_writer_thread.start()
        print(f"Realtime PC-state CSV started: {pc_state_all_csv}")

    return pc_state_all_csv, pc_state_writer_thread


def run_camera_threads(cams, stop_event):
    threads = []
    for cam_idx, cam_data in cams.items():
        thread = threading.Thread(target=camera_thread_fn, args=(cam_idx, cam_data, stop_event), daemon=True)
        thread.start()
        threads.append(thread)

    # Wait for all threads to finish (or until any window is closed or 'q' is pressed)
    try:
        while any(thread.is_alive() for thread in threads):
            if stop_event.is_set():
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user (KeyboardInterrupt)")
        stop_event.set()

    for thread in threads:
        thread.join()


def stop_realtime_pc_state_writer(cams, stop_event, pc_state_writer_thread, pc_state_all_csv):
    # ensure writer thread exits and final state is flushed
    stop_event.set()
    if ENABLE_REALTIME_PC_STATE_CSV and pc_state_writer_thread is not None:
        pc_state_writer_thread.join(timeout=2.0)
        write_pc_state_csv(cams, pc_state_all_csv)


def release_camera_resources(cams):
    for cam_data in cams.values():
        cap = cam_data["cap"]
        if cap:
            cap.release()

    cv2.destroyAllWindows()


def stop_resource_monitor_if_enabled(monitor_stop, monitor_thread):
    if ENABLE_RESOURCE_MONITOR and monitor_stop is not None and monitor_thread is not None:
        try:
            # stop_resource_monitor is provided by resource_monitor module
            from tool.resource_monitor import stop_resource_monitor

            stop_resource_monitor(monitor_stop, monitor_thread, timeout=2.0)
            print("Resource monitor stopped")
        except Exception:
            try:
                monitor_stop.set()
                monitor_thread.join(timeout=2.0)
            except Exception:
                pass


def save_session_outputs(cams, run_start_day_tag, pc_state_all_csv):
    all_unattended_logs = []
    write_detection_outputs(cams)
    for cam_idx, cam_data in cams.items():
        source_name = os.path.splitext(os.path.basename(str(cam_data.get("source_path") or "")))[0]
        safe_name = cam_data.get("label") or to_safe_label(source_name) or to_safe_label(cam_data.get("name", "video"))
        people_file_prefix = f"people_with_conf_and_roi_{safe_name}"
        people_csv_paths = append_rows_to_daily_csv(
            cam_data.get("logs", []),
            ["time", "person_id", "confidence", "roi_file", "PCnum", "model_name"],
            cam_data.get("log_dir", LOG_BASE_DIR),
            people_file_prefix,
            run_start_day_tag,
        )
        primary_people_csv = people_csv_paths[-1] if people_csv_paths else ""

        # PC activity event log (USING_PC / NON_PC_ACTIVITY)
        event_file_prefix = f"pc_activity_events_{safe_name}"
        pc_event_csv_paths = append_rows_to_daily_csv(
            cam_data.get("pc_event_logs", []),
            ["time", "cam_name", "pc_name", "event_type", "person_id", "pc_on", "dwell_sec", "PCnum", "model_name"],
            cam_data.get("log_dir", LOG_BASE_DIR),
            event_file_prefix,
            run_start_day_tag,
        )
        primary_event_csv = pc_event_csv_paths[-1] if pc_event_csv_paths else ""

        # collect unattended/person-flag logs for one combined file in logs/
        all_unattended_logs.extend(cam_data.get("pc_unattended_logs", []))

        report_rows = cam_data.get("zone_roi_report_rows", [])
        report_dir = cam_data.get("report_dir", os.path.join(LOG_BASE_DIR, "report", safe_name))
        if report_rows:
            report_csv_path = os.path.join(report_dir, "timestamp.csv")
            report_columns = [
                "time",
                "clock",
                "t_sec",
                "image_file",
                "fallback_count",
                "fallback_assignments",
                "reason",
                "person_id",
                "pc_name",
                "frame_type",
            ]
            pd.DataFrame(report_rows, columns=report_columns).to_csv(report_csv_path, index=False)
            print(f"Disappearance report saved to {report_csv_path}")

        print(f"\n=== Session Summary ({cam_data['name']}) ===")
        print(f"Total unique persons detected: {len(cam_data['tracked_persons'])}")
        if len(people_csv_paths) == 1:
            print(f"Logs saved to {primary_people_csv}")
        else:
            print(f"Logs saved to {len(people_csv_paths)} daily file(s): {people_csv_paths[0]} -> {people_csv_paths[-1]}")

        if len(pc_event_csv_paths) == 1:
            print(f"PC activity events saved to {primary_event_csv}")
        else:
            print(
                f"PC activity events saved to {len(pc_event_csv_paths)} daily file(s): "
                f"{pc_event_csv_paths[0]} -> {pc_event_csv_paths[-1]}"
            )
        if report_rows:
            print(f"Zone ROI no-detect snapshots: {len(report_rows)} frame(s) in {report_dir}")
        # performance summary
        frames = cam_data.get("frames_seen", 0)
        total_latency_ms = cam_data.get("total_latency_ms", 0.0)
        inference_runs = cam_data.get("inference_runs", 0)
        total_inference_time_ms = cam_data.get("total_inference_time_ms", 0.0)
        first_t = cam_data.get("first_frame_time")
        last_t = cam_data.get("last_frame_time")
        total_runtime_s = None
        if first_t is not None and last_t is not None and last_t > first_t:
            total_runtime_s = last_t - first_t

        avg_latency = (total_latency_ms / frames) if frames > 0 else 0.0
        avg_inference = (total_inference_time_ms / inference_runs) if inference_runs > 0 else 0.0
        avg_fps = (frames / total_runtime_s) if total_runtime_s and total_runtime_s > 0 else cam_data.get("fps", 0.0)

        print(f"Frames processed: {frames}")
        if total_runtime_s:
            print(f"Total runtime: {total_runtime_s:.2f} s")
        print(f"Average FPS: {avg_fps:.2f}")
        print(f"Average latency/frame: {avg_latency:.1f} ms")
        print(f"Inference runs: {inference_runs} (avg {avg_inference:.1f} ms per inference)")
        print("===============================")
        # append a per-camera summary row to a global performance CSV (create if missing)
        try:
            perf_timestamp = format_video_timestamp(cam_data.get("first_video_time") or 0.0)
            session_config = build_session_config_string(cams)
            perf_row = {
                "session_timestamp": perf_timestamp,
                "cam_idx": cam_idx,
                "cam_name": cam_data.get("name"),
                "frames": frames,
                "total_runtime_s": total_runtime_s if total_runtime_s is not None else 0.0,
                "avg_fps": float(f"{avg_fps:.2f}"),
                "avg_latency_ms": float(f"{avg_latency:.1f}"),
                "inference_runs": inference_runs,
                "avg_inference_ms": float(f"{avg_inference:.1f}"),
                "total_inference_ms": float(f"{total_inference_time_ms:.1f}"),
                "unique_persons": len(cam_data.get("tracked_persons", {})),
                "log_csv": primary_people_csv,
                "roi_dir": cam_data.get("roi_dir"),
            }

            # resource usage summary (if monitor collected samples)
            try:
                mem_samples = [m for m in cam_data.get("mem_samples", []) if m]
                cpu_samples = [c for c in cam_data.get("cpu_proc_samples", []) if c is not None]
                gpu_samples = [g for g in cam_data.get("gpu_mem_samples", []) if g]

                perf_row["avg_proc_rss_bytes"] = int(sum(mem_samples) / len(mem_samples)) if mem_samples else 0
                perf_row["peak_proc_rss_bytes"] = int(max(mem_samples)) if mem_samples else 0
                perf_row["avg_proc_cpu_percent"] = float(f"{(sum(cpu_samples)/len(cpu_samples)) if cpu_samples else 0:.2f}")
                perf_row["avg_gpu_mem_bytes"] = int(sum(gpu_samples) / len(gpu_samples)) if gpu_samples else 0
                perf_row["peak_gpu_mem_bytes"] = int(max(gpu_samples)) if gpu_samples else 0
            except Exception:
                perf_row["avg_proc_rss_bytes"] = 0
                perf_row["peak_proc_rss_bytes"] = 0
                perf_row["avg_proc_cpu_percent"] = 0.0
                perf_row["avg_gpu_mem_bytes"] = 0
                perf_row["peak_gpu_mem_bytes"] = 0

            # Add config as last column
            perf_row["config"] = session_config
            perf_row["model_name"] = "yolov8s"

            perf_df = pd.DataFrame([perf_row])
            write_header = not os.path.exists(PERF_SUMMARY_FILE)
            perf_df.to_csv(PERF_SUMMARY_FILE, mode="a", index=False, header=write_header)
            print(f"Performance summary appended to {PERF_SUMMARY_FILE}")
        except Exception as e:
            print(f"Failed to write performance summary for {cam_data.get('name')}: {e}")

    # write one combined person-flag CSV for all cameras under logs/
    all_unattended_csv_paths = append_rows_to_daily_csv(
        all_unattended_logs,
        ["time", "user", "pc_name", "cam_name", "reason", "model_name"],
        LOG_BASE_DIR,
        "pc_unattended_flags",
        run_start_day_tag,
    )
    if len(all_unattended_csv_paths) == 1:
        print(f"Combined unattended/person-flag CSV saved to {all_unattended_csv_paths[0]}")
    else:
        print(
            "Combined unattended/person-flag CSV saved to "
            f"{len(all_unattended_csv_paths)} daily file(s): "
            f"{all_unattended_csv_paths[0]} -> {all_unattended_csv_paths[-1]}"
        )

    # create daily summary report
    create_daily_summary_report(cams, run_start_day_tag, LOG_BASE_DIR)

    if EVAL_MODE:
        write_eval_outputs(cams)

    # Clean up empty log folders
    cleanup_empty_log_folders(LOG_BASE_DIR)

    if ENABLE_REALTIME_PC_STATE_CSV:
        print(f"Realtime all-PC state CSV saved to {pc_state_all_csv}")


def main():
    # Check for eval-only mode
    if CLI_ARGS.eval_only:
        eval_log_root = os.path.normpath(str(CLI_ARGS.eval_log_dir)) if str(CLI_ARGS.eval_log_dir).strip() else os.path.join(VIDEO_LOG_BASE_DIR, "eval")
        groundtruth_dir = os.path.normpath(str(CLI_ARGS.groundtruth_dir))
        run_eval_only_mode(eval_log_root, groundtruth_dir)
        return
    
    cams = build_camera_states()
    monitor_stop, monitor_thread = start_resource_monitor_if_enabled(cams)
    print_session_banner(cams)

    stop_event = threading.Event()
    run_start_day_tag = current_day_tag()
    pc_state_all_csv, pc_state_writer_thread = start_realtime_pc_state_writer(cams, stop_event)

    try:
        run_camera_threads(cams, stop_event)
    finally:
        stop_realtime_pc_state_writer(cams, stop_event, pc_state_writer_thread, pc_state_all_csv)
        release_camera_resources(cams)
        stop_resource_monitor_if_enabled(monitor_stop, monitor_thread)
        save_session_outputs(cams, run_start_day_tag, pc_state_all_csv)
        
        # Auto-run duration-based evaluation if EVAL_MODE enabled
        if EVAL_MODE:
            eval_log_root = os.path.normpath(str(CLI_ARGS.eval_log_dir)) if str(CLI_ARGS.eval_log_dir).strip() else os.path.join(VIDEO_LOG_BASE_DIR, "eval")
            groundtruth_dir = os.path.normpath(str(CLI_ARGS.groundtruth_dir))
            print("\n=== Auto-Running Duration-Based Evaluation ===")
            run_eval_only_mode(eval_log_root, groundtruth_dir)


if __name__ == "__main__":
    main()