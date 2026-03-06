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


# -------------------------------------Configuration--------------------------------------------
# Camera settings
CAM_INDEXES = [0, 1, 2, 3]
CAM_NAMES = {
    0: "Front_right",
    1: "Front_left",
    2: "Back_left",
    3: "Back_right",
}
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Window display settings
# lower resolution for better performance | Hide for best performance 
SHOW_WINDOWS = "Show" # Show or Hide
Windows_width,Windows_height = 960,540

# Detection settings
CONF_THRESHOLD = 0.4 # minimum confidence threshold for person detection
IOU_THRESHOLD = 0.4
SAVE_INTERVAL_SEC = 10 # seconds between saving ROIs of the same person

# Detection schedule settings (24-hour format, local time)
DETECTION_START_HOUR_24 = 8   # start detection at 08:00
DETECTION_END_HOUR_24 = 18    # stop detection at 18:00

# PC ROI settings
ENABLE_PC_ROI = True  # set to True to load ROI polygons and assign PCnum
ENABLE_MONITOR_ROI = True  # set to True to load monitor ROI polygons and estimate PC ON/OFF
PERSON_OVERLAP_DWELL_SEC = 10.0  # person overlap dwell threshold (seconds)
PC_ON_NO_PERSON_DWELL_SEC = 300.0  # PC ON + no person overlap dwell threshold (5 minutes)
LATEST_PERSON_FLAG_LOOKBACK_SEC = 900.0  # latest-person lookup window for reason "2" (15 minutes)
MONITOR_ON_MEAN_THRESHOLD = 70.0  # mean grayscale threshold for monitor ON heuristic
MONITOR_ON_STD_THRESHOLD = 12.0  # std-dev threshold for monitor ON heuristic
MONITOR_STATE_STABLE_FRAMES = 3  # consecutive frames to stabilize ON/OFF state
ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
CSV_SUFFIX = "_roi.csv"
MONITOR_CSV_SUFFIX = "_monitor_roi.csv"

# Tracking settings
ENABLE_RESOURCE_MONITOR = False # set to True to enable resource monitoring (requires resource_monitor.py)

# Realtime PC-state CSV settings
ENABLE_REALTIME_PC_STATE_CSV = True
REALTIME_PC_STATE_WRITE_INTERVAL_SEC = 1.0

# ----------------------------------------------------------------------------------------------

# Load model once
# choose device (use CUDA if available)
# Detect CUDA availability and select an explicit device string (cuda:0) when available.
cuda_available = torch.cuda.is_available()
device = "cuda:0" if cuda_available else "cpu"
print(f"CUDA available: {cuda_available}")
print(f"Device selected: {device}")

model = YOLO("yolov8n.pt")
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

LOG_BASE_DIR = "logs"
# store ROI images under the logs directory so all outputs live together
ROI_BASE_DIR = os.path.join(LOG_BASE_DIR, "roi_images")
PERF_SUMMARY_FILE = os.path.join(LOG_BASE_DIR, "performance_summary.csv")


def to_safe_label(value):
    """Convert a display label into a filesystem-safe name."""
    cleaned = "".join((c if c.isalnum() or c in ("-", "_") else "_") for c in str(value).strip())
    # collapse repeated underscores for cleaner paths
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "unknown"


def is_detection_time_active(current_time_struct=None):
    """Return True when local time is inside the configured detection window."""
    if current_time_struct is None:
        current_time_struct = time.localtime()

    current_hour = current_time_struct.tm_hour
    start_hour = int(DETECTION_START_HOUR_24) % 24
    end_hour = int(DETECTION_END_HOUR_24) % 24

    # same start/end means full-day detection
    if start_hour == end_hour:
        return True
    if start_hour < end_hour:
        return start_hour <= current_hour < end_hour
    return (current_hour >= start_hour) or (current_hour < end_hour)


def distance(box1, box2):
    """Calculate distance between centers of two boxes."""
    cx1 = (box1[0] + box1[2]) / 2
    cy1 = (box1[1] + box1[3]) / 2
    cx2 = (box2[0] + box2[2]) / 2
    cy2 = (box2[1] + box2[3]) / 2
    return ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5


def match_box_to_person(box, tracked_persons):
    """Find closest tracked person to this box."""
    min_dist = 100  # threshold
    matched_id = None

    for pid, pdata in tracked_persons.items():
        if "last_box" in pdata:
            dist = distance(box, pdata["last_box"])
            if dist < min_dist:
                min_dist = dist
                matched_id = pid

    return matched_id


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
        "available": 0,
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
                state["available"] = 2
        elif prev_pc_on and (not state["pc_on"]):
            state["unattended_logged"] = False
            state["empty_since_time"] = None
            if not state.get("person_present"):
                state["available"] = 0

        state["last_update_time"] = now_ts


def update_pc_activity_events(cam_name, pc_states, pc_to_person, now_ts, pc_event_logs, pc_unattended_logs):
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))

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
                state["available"] = 2
                state["reason1_logged_person_id"] = None
            else:
                state["available"] = 1
                if state.get("reason1_logged_person_id") != person_id:
                    pc_unattended_logs.append(
                        {
                            "time": now_str,
                            "user": person_id,
                            "cam_name": cam_name,
                            "pc_name": pc_name,
                            "reason": "1",
                        }
                    )
                    state["reason1_logged_person_id"] = person_id

            dwell = now_ts - (state.get("overlap_start_time") or now_ts)
            if dwell >= PERSON_OVERLAP_DWELL_SEC and not state.get("person_event_logged"):
                if state.get("pc_on"):
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
                    state["available"] = 0
                    last_person_seen_time = state.get("last_person_seen_time")
                    has_recent_last_person = (
                        state.get("last_person_id")
                        and last_person_seen_time is not None
                        and (now_ts - last_person_seen_time) <= LATEST_PERSON_FLAG_LOOKBACK_SEC
                    )
                    if has_recent_last_person and not state.get("unattended_logged"):
                        pc_unattended_logs.append(
                            {
                                "time": now_str,
                                "user": state.get("last_person_id"),
                                "cam_name": cam_name,
                                "pc_name": pc_name,
                                "reason": "2",
                            }
                        )
                        state["unattended_logged"] = True
                else:
                    state["available"] = 2
            else:
                state["available"] = 0
                state["unattended_logged"] = False
                state["empty_since_time"] = None


def build_pc_state_rows(cam_idx, cam_name, cam_label, pc_states, now_ts):
    snapshot_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))
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
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(state["last_update_time"]))
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
            }

    ordered_pc_names = sorted(state_by_pc.keys(), key=pc_name_sort_key)
    return [state_by_pc[name] for name in ordered_pc_names]


def write_pc_state_csv(cams, csv_path):
    rows = build_all_pc_state_rows(cams)
    pc_state_df = pd.DataFrame(rows, columns=["pc_name", "pc_on", "availble"])
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

# Create base directories
os.makedirs(LOG_BASE_DIR, exist_ok=True)
os.makedirs(ROI_BASE_DIR, exist_ok=True)

# Per-camera state
cams = {}

for cam_idx in CAM_INDEXES:
    cap = cv2.VideoCapture(cam_idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cam_name = CAM_NAMES.get(cam_idx, f"Cam {cam_idx}")
    cam_label = to_safe_label(cam_name)
    
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
        "process_every_n_frames": 2,
        "frame_counter": 0,
        # cache last annotated frame to display when skipping inference
        "last_annotated_frame": None,
        "detection_active_last": None,
        # performance tracking
        "frames_seen": 0,
        "total_latency_ms": 0.0,
        "inference_runs": 0,
        "total_inference_time_ms": 0.0,
        "first_frame_time": None,
        "name": cam_name,
        "label": cam_label,
        "pc_rois": pc_rois,
        "monitor_rois": monitor_rois,
        "pc_states": pc_states,
        "pc_event_logs": [],
        "pc_unattended_logs": [],
    }
    os.makedirs(cams[cam_idx]["roi_dir"], exist_ok=True)
    os.makedirs(cams[cam_idx]["log_dir"], exist_ok=True)

# start resource monitor if enabled
monitor_stop = None
monitor_thread = None
if ENABLE_RESOURCE_MONITOR:
    try:
        from tool.resource_monitor import start_resource_monitor, stop_resource_monitor

        monitor_stop, monitor_thread = start_resource_monitor(cams, device=device, sample_interval=1.0)
        print("Resource monitor started")
    except Exception as e:
        print(f"Failed to start resource monitor: {e}")


print("=== Auto ID Assignment (4 Cams) ===")
print("Each detected person gets a random 3-digit ID automatically")
print("ROIs saved every 10 seconds to roi_images/<CAM_NAME>/<ID>/")
print(f"YOLO detection schedule: {DETECTION_START_HOUR_24:02d}:00-{DETECTION_END_HOUR_24:02d}:00 (local time)")
print(f"Person overlap dwell threshold: {PERSON_OVERLAP_DWELL_SEC:.0f}s")
print(f"PC ON + no person unattended threshold: {PC_ON_NO_PERSON_DWELL_SEC/60:.0f} minutes")
print("Press 'q' to quit")
print("===================================\n")


# --- Threaded camera processing ---
def camera_thread_fn(cam_idx, cam_data, stop_event):
    try:
        while not stop_event.is_set():
            cap = cam_data["cap"]
            if not cap.isOpened():
                break

            frame_start = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            detection_active = is_detection_time_active()
            last_detection_active = cam_data.get("detection_active_last")
            if last_detection_active is None or last_detection_active != detection_active:
                state = "ON" if detection_active else "OFF"
                print(
                    f"{cam_data['name']}: YOLO detection {state} "
                    f"({DETECTION_START_HOUR_24:02d}:00-{DETECTION_END_HOUR_24:02d}:00)"
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
                    cam_data["first_frame_time"] = frame_start

                pc_to_person = {}

                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    if cls == 0 and conf > CONF_THRESHOLD:
                        person_count += 1
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        current_box = (x1, y1, x2, y2)
                        
                        # determine which PC this person is in
                        current_pc = get_pc_for_box(current_box, cam_data["pc_rois"]) if ENABLE_PC_ROI else None
                        
                        matched_id = match_box_to_person(current_box, cam_data["tracked_persons"])
                        if matched_id is not None:
                            pdata = cam_data["tracked_persons"][matched_id]
                            pdata["last_box"] = current_box
                            person_name = pdata.get("name", f"Person {matched_id}")
                            
                            # PC dwell-time tracking
                            if current_pc:
                                if pdata.get("current_pc") == current_pc:
                                    # still in same PC, accumulate time
                                    pass
                                else:
                                    # entered new PC, start timer
                                    pdata["current_pc"] = current_pc
                                    pdata["pc_enter_time"] = frame_start
                                
                                # check if threshold met
                                dwell_time = frame_start - pdata.get("pc_enter_time", frame_start)
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
                            
                            current_time = time.time()
                            last_save = pdata.get("last_save", 0)
                            if person_name != f"Person {matched_id}" and current_time - last_save >= SAVE_INTERVAL_SEC:
                                roi = frame[y1:y2, x1:x2]
                                if roi.size > 0:
                                    person_folder = pdata["folder"]
                                    filename = f"ID{person_name}_{int(current_time)}.jpg"
                                    filepath = os.path.join(person_folder, filename)
                                    cv2.imwrite(filepath, roi)
                                    pdata["last_save"] = current_time
                                    cam_data["logs"].append({
                                        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "person_id": person_name,
                                        "confidence": round(conf, 3),
                                        "roi_file": filepath,
                                        "PCnum": pdata.get("assigned_pc"),
                                    })
                                    print(f"{cam_data['name']}: Saved ID {person_name} at {time.strftime('%H:%M:%S')}")
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
                                "pc_enter_time": frame_start if current_pc else None,
                                "assigned_pc": None,
                            }
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

                pc_to_person_map = {pc_name: data[1] for pc_name, data in pc_to_person.items()}
                update_pc_states_from_monitor(frame, cam_data.get("monitor_rois", []), cam_data.get("pc_states", {}), frame_start)
                update_pc_activity_events(
                    cam_data["name"],
                    cam_data.get("pc_states", {}),
                    pc_to_person_map,
                    frame_start,
                    cam_data.get("pc_event_logs", []),
                    cam_data.get("pc_unattended_logs", []),
                )
                cv2.putText(frame, f"People: {person_count}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cam_data["last_annotated_frame"] = frame.copy()
            else:
                if detection_active:
                    if cam_data["last_annotated_frame"] is not None:
                        frame = cam_data["last_annotated_frame"].copy()
                    cv2.putText(frame, f"People: {len(cam_data['tracked_persons'])}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
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

            frame_end = time.time()
            latency_ms = (frame_end - frame_start) * 1000.0
            cam_data["frames_seen"] += 1
            cam_data["total_latency_ms"] += latency_ms
            if cam_data["last_frame_time"] is not None:
                dt = frame_end - cam_data["last_frame_time"]
                if dt > 0:
                    cam_data["fps"] = 1.0 / dt
            cam_data["last_frame_time"] = frame_end
            cv2.putText(frame, f"FPS: {cam_data['fps']:.1f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            cv2.putText(frame, f"Latency: {latency_ms:.1f} ms", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            if SHOW_WINDOWS == "Show":
                display_frame = cv2.resize(frame, (Windows_width, Windows_height))
                cv2.imshow(cam_data["window"], display_frame)
                if cv2.getWindowProperty(cam_data["window"], cv2.WND_PROP_VISIBLE) < 1:
                    break
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    stop_event.set()
                    break
            elif SHOW_WINDOWS == "Hide":
                pass
    except KeyboardInterrupt:
        print(f"\nInterrupted by user (KeyboardInterrupt) in {cam_data['name']}")

# --- Start threads for each camera ---
stop_event = threading.Event()
run_start_day_tag = current_day_tag()
pc_state_all_csv = os.path.join(LOG_BASE_DIR, "pc_state_all.csv")

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

threads = []
for cam_idx, cam_data in cams.items():
    t = threading.Thread(target=camera_thread_fn, args=(cam_idx, cam_data, stop_event), daemon=True)
    t.start()
    threads.append(t)

# Wait for all threads to finish (or until any window is closed or 'q' is pressed)
try:
    while any(t.is_alive() for t in threads):
        if stop_event.is_set():
            break
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nInterrupted by user (KeyboardInterrupt)")
    stop_event.set()
for t in threads:
    t.join()

# ensure writer thread exits and final state is flushed
stop_event.set()
if ENABLE_REALTIME_PC_STATE_CSV and pc_state_writer_thread is not None:
    pc_state_writer_thread.join(timeout=2.0)
    write_pc_state_csv(cams, pc_state_all_csv)

# Release cameras and close windows
for cam_data in cams.values():
    cap = cam_data["cap"]
    if cap:
        cap.release()

cv2.destroyAllWindows()

# stop resource monitor if it was started
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

# Save logs per camera
all_unattended_logs = []
for cam_idx, cam_data in cams.items():
    safe_name = cam_data.get("label") or to_safe_label(cam_data.get("name", f"cam{cam_idx}"))
    people_file_prefix = f"people_with_conf_and_roi_{safe_name or f'cam{cam_idx}'}"
    people_csv_paths = append_rows_to_daily_csv(
        cam_data.get("logs", []),
        ["time", "person_id", "confidence", "roi_file", "PCnum"],
        cam_data.get("log_dir", LOG_BASE_DIR),
        people_file_prefix,
        run_start_day_tag,
    )
    primary_people_csv = people_csv_paths[-1] if people_csv_paths else ""

    # PC activity event log (USING_PC / NON_PC_ACTIVITY)
    event_file_prefix = f"pc_activity_events_{safe_name or f'cam{cam_idx}'}"
    pc_event_csv_paths = append_rows_to_daily_csv(
        cam_data.get("pc_event_logs", []),
        ["time", "cam_name", "pc_name", "event_type", "person_id", "pc_on", "dwell_sec", "PCnum"],
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
        perf_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cam_data.get("first_frame_time") or time.time()))
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

        perf_df = pd.DataFrame([perf_row])
        write_header = not os.path.exists(PERF_SUMMARY_FILE)
        perf_df.to_csv(PERF_SUMMARY_FILE, mode="a", index=False, header=write_header)
        print(f"Performance summary appended to {PERF_SUMMARY_FILE}")
    except Exception as e:
        print(f"Failed to write performance summary for {cam_data.get('name')}: {e}")

# write one combined person-flag CSV for all cameras under logs/
all_unattended_csv_paths = append_rows_to_daily_csv(
    all_unattended_logs,
    ["time", "user", "pc_name", "cam_name", "reason"],
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

if ENABLE_REALTIME_PC_STATE_CSV:
    print(f"Realtime all-PC state CSV saved to {pc_state_all_csv}")
