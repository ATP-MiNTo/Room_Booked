
import cv2
from ultralytics import YOLO
import time
import torch
import os
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
SAVE_INTERVAL_SEC = float(_require_config_value(CONFIG, "SAVE_INTERVAL_SEC"))

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
    model.conf = CONF_THRESHOLD
    model.iou = IOU_THRESHOLD
except Exception:
    # ignore if attribute not present
    pass

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

        pc_states = init_pc_states(pc_rois, monitor_rois)

        cams[cam_idx] = {
            "cap": cap,
            "tracked_persons": {},
            "person_id_counter": 0,
            "used_ids": set(),
            "logs": [],
            "window": f"YOLO Person Detection ({cam_name})",
            "roi_dir": os.path.join(ROI_BASE_DIR, cam_label),
            "log_dir": os.path.join(LOG_BASE_DIR, cam_label),
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
            "pc_states": pc_states,
            "pc_event_logs": [],
            "pc_unattended_logs": [],
        }
        os.makedirs(cams[cam_idx]["roi_dir"], exist_ok=True)
        os.makedirs(cams[cam_idx]["log_dir"], exist_ok=True)

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
    print("Each detected person gets a random 3-digit ID automatically")
    print(f"ROIs saved every {SAVE_INTERVAL_SEC:.0f} seconds to roi_images/<CAM_NAME>/<ID>/")
    print(f"Video input directory: {VIDEO_INPUT_DIR}")
    print("Detection runs continuously (schedule disabled in video mode)")
    print(f"Person overlap dwell threshold: {PERSON_OVERLAP_DWELL_SEC:.0f}s")
    print(f"PC ON + no person unattended threshold: {PC_ON_NO_PERSON_DWELL_SEC/60:.0f} minutes")
    print(f"Smoothing window (mode): {SMOOTH_WINDOW_SEC:.1f}s")
    if FRAME_CAP_FPS > 0:
        print(f"Frame cap: {FRAME_CAP_FPS:.1f} FPS")
    print(f"Logs root: {LOG_BASE_DIR}")
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
            do_infer = detection_active and (
                (cam_data["frame_counter"] % cam_data["process_every_n_frames"] == 0)
                or (cam_data["last_annotated_frame"] is None)
            )

            person_count = 0

            if do_infer:
                # run inference (use AMP autocast if CUDA available)
                inf_start = time.time()
                try:
                    try:
                        if device.startswith("cuda") and cuda_available:
                            from torch import amp
                            with amp.autocast(device_type="cuda"):
                                results = model(frame, verbose=False, device=device)
                        else:
                            results = model(frame, verbose=False, device=device)
                    except Exception:
                        try:
                            results = model(frame, verbose=False)
                        except Exception:
                            raise
                except Exception:
                    results = model(frame, verbose=False)
                inf_end = time.time()
                cam_data["inference_runs"] += 1
                cam_data["total_inference_time_ms"] += (inf_end - inf_start) * 1000.0

                if cam_data["first_frame_time"] is None:
                    cam_data["first_frame_time"] = loop_wall_start

                pc_to_person = {}
                matched_track_ids = set()

                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    if cls == 0 and conf > CONF_THRESHOLD:
                        person_count += 1
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        current_box = (x1, y1, x2, y2)
                        
                        # determine which PC this person is in
                        current_pc = get_pc_for_box(current_box, cam_data["pc_rois"]) if ENABLE_PC_ROI else None
                        
                        matched_id = match_box_to_person(
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

                for pid, pdata in cam_data["tracked_persons"].items():
                    if pid in matched_track_ids:
                        continue
                    if pdata.get("missing_since_ts") is None:
                        pdata["missing_since_ts"] = frame_time_sec

                prune_stale_tracks(cam_data["tracked_persons"], frame_time_sec)

                pc_to_person_map = {pc_name: data[1] for pc_name, data in pc_to_person.items()}
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
                    cam_data["last_annotated_frame"] = frame.copy()
            else:
                update_smoothed_person_count(cam_data, 0, frame_time_sec)

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

    # Clean up empty log folders
    cleanup_empty_log_folders(LOG_BASE_DIR)

    if ENABLE_REALTIME_PC_STATE_CSV:
        print(f"Realtime all-PC state CSV saved to {pc_state_all_csv}")


def main():
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


if __name__ == "__main__":
    main()