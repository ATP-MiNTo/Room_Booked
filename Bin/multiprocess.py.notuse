import cv2
from ultralytics import YOLO
import time
import torch
import os
import pandas as pd
import random
import multiprocessing as mp
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
SHOW_WINDOWS = "Show"  # Show or Hide
Windows_width, Windows_height = 960, 540

# Detection settings
CONF_THRESHOLD = 0.4  # minimum confidence threshold for person detection
IOU_THRESHOLD = 0.4
SAVE_INTERVAL_SEC = 10  # seconds between saving ROIs of the same person

# Detection schedule settings (24-hour format, local time)
DETECTION_START_HOUR_24 = 8  # start detection at 08:00
DETECTION_END_HOUR_24 = 20  # stop detection at 20:00

# PC ROI settings
ENABLE_PC_ROI = True  # set to True to load ROI polygons and assign PCnum
ENABLE_MONITOR_ROI = True  # set to True to load monitor ROI polygons and estimate PC ON/OFF
PERSON_OVERLAP_DWELL_SEC = 10.0  # person overlap dwell threshold (seconds)
PC_ON_NO_PERSON_DWELL_SEC = 300.0  # PC ON + no person overlap dwell threshold (5 minutes)
MONITOR_ON_MEAN_THRESHOLD = 70.0  # mean grayscale threshold for monitor ON heuristic
MONITOR_ON_STD_THRESHOLD = 12.0  # std-dev threshold for monitor ON heuristic
MONITOR_STATE_STABLE_FRAMES = 3  # consecutive frames to stabilize ON/OFF state
ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
CSV_SUFFIX = "_roi.csv"
MONITOR_CSV_SUFFIX = "_monitor_roi.csv"

# Tracking settings
# NOTE: Resource monitor is disabled in multiprocessing mode by default, because it expects
# shared in-memory camera state. You can re-enable per-process monitoring if needed.
ENABLE_RESOURCE_MONITOR = False

# Realtime PC-state CSV settings (parent process writer)
ENABLE_REALTIME_PC_STATE_CSV = True
REALTIME_PC_STATE_WRITE_INTERVAL_SEC = 1.0

# ----------------------------------------------------------------------------------------------

LOG_BASE_DIR = "logs"
ROI_BASE_DIR = os.path.join(LOG_BASE_DIR, "roi_images")
PERF_SUMMARY_FILE = os.path.join(LOG_BASE_DIR, "performance_summary.csv")


def to_safe_label(value):
    """Convert a display label into a filesystem-safe name."""
    cleaned = "".join((c if c.isalnum() or c in ("-", "_") else "_") for c in str(value).strip())
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

# Create base directories
os.makedirs(LOG_BASE_DIR, exist_ok=True)
os.makedirs(ROI_BASE_DIR, exist_ok=True)


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
        "overlap_start_time": None,
        "empty_since_time": None,
        "person_event_logged": False,
        "unattended_logged": False,
        "available": True,
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
                state["available"] = False
        elif prev_pc_on and (not state["pc_on"]):
            state["unattended_logged"] = False
            state["empty_since_time"] = None
            if not state.get("person_present"):
                state["available"] = True

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

            state["person_present"] = True
            state["last_person_id"] = person_id
            state["empty_since_time"] = None
            state["unattended_logged"] = False
            state["available"] = False

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
            elif state.get("empty_since_time") is None:
                state["empty_since_time"] = now_ts

            if state.get("pc_on"):
                empty_dwell = now_ts - (state.get("empty_since_time") or now_ts)
                if empty_dwell >= PC_ON_NO_PERSON_DWELL_SEC:
                    state["available"] = True
                    if state.get("last_person_id") and not state.get("unattended_logged"):
                        pc_unattended_logs.append(
                            {
                                "time": now_str,
                                "cam_name": cam_name,
                                "pc_name": pc_name,
                                "last_person_id": state.get("last_person_id"),
                                "pc_on": True,
                                "empty_dwell_sec": round(empty_dwell, 2),
                                "reason": "PC_ON_NO_PERSON_OVERLAP_5MIN",
                            }
                        )
                        state["unattended_logged"] = True
                else:
                    state["available"] = False
            else:
                state["available"] = True
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


def update_shared_pc_state_map(shared_pc_state_map, pc_states):
    if shared_pc_state_map is None:
        return

    for pc_name, state in pc_states.items():
        shared_pc_state_map[pc_name] = {
            "pc_name": pc_name,
            "pc_on": bool(state.get("pc_on")),
            "availble": bool(state.get("available", False)),
        }


def write_pc_state_csv_from_map(shared_pc_state_map, csv_path):
    state_by_pc = dict(shared_pc_state_map or {})
    ordered_pc_names = sorted(state_by_pc.keys(), key=pc_name_sort_key)
    rows = [state_by_pc[name] for name in ordered_pc_names]
    pc_state_df = pd.DataFrame(rows, columns=["pc_name", "pc_on", "availble"])
    pc_state_df.to_csv(csv_path, index=False)


def realtime_pc_state_writer(shared_pc_state_map, csv_path, stop_event, interval_sec=1.0):
    while not stop_event.is_set():
        try:
            write_pc_state_csv_from_map(shared_pc_state_map, csv_path)
        except Exception as e:
            print(f"Failed to update realtime PC-state CSV: {e}")
        stop_event.wait(interval_sec)

    try:
        write_pc_state_csv_from_map(shared_pc_state_map, csv_path)
    except Exception as e:
        print(f"Failed to finalize realtime PC-state CSV: {e}")


def init_model(conf_threshold):
    """Initialize and return a YOLO model, moved to GPU if available."""
    cuda_available = torch.cuda.is_available()
    device = "cuda:0" if cuda_available else "cpu"
    print(f"CUDA available: {cuda_available}")
    print(f"Device selected: {device}")

    model = YOLO("yolov8n.pt")
    try:
        if cuda_available:
            try:
                model.to(torch.device(device))
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
        pass

    try:
        model.conf = conf_threshold
        model.iou = IOU_THRESHOLD
    except Exception:
        pass

    return model, device, cuda_available


def camera_process_fn(cam_idx, stop_event, session_tag, shared_pc_state_map, shared_unattended_logs):
    """Run detection loop for a single camera in its own process."""
    cam_name = CAM_NAMES.get(cam_idx, f"Cam {cam_idx}")
    cam_label = to_safe_label(cam_name)

    cap = cv2.VideoCapture(cam_idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    roi_dir = os.path.join(ROI_BASE_DIR, cam_label)
    log_dir = os.path.join(LOG_BASE_DIR, cam_label)
    os.makedirs(roi_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
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
    update_shared_pc_state_map(shared_pc_state_map, pc_states)

    tracked_persons = {}
    person_id_counter = 0
    used_ids = set()
    logs = []
    pc_event_logs = []
    pc_unattended_logs = []

    last_frame_time = None
    fps = 0.0
    process_every_n_frames = 2
    frame_counter = 0
    last_annotated_frame = None
    detection_active_last = None

    frames_seen = 0
    total_latency_ms = 0.0
    inference_runs = 0
    total_inference_time_ms = 0.0
    first_frame_time = None

    if not cap.isOpened():
        print(f"{cam_name}: Failed to open camera")
        return

    model, device, cuda_available = init_model(CONF_THRESHOLD)

    # start resource monitor if enabled (per-process)
    monitor_stop = None
    monitor_thread = None
    if ENABLE_RESOURCE_MONITOR:
        try:
            from tool.resource_monitor import start_resource_monitor, stop_resource_monitor

            monitor_stop, monitor_thread = start_resource_monitor(
                {cam_idx: {"name": cam_name}}, device=device, sample_interval=1.0
            )
            print(f"{cam_name}: Resource monitor started")
        except Exception as e:
            print(f"{cam_name}: Failed to start resource monitor: {e}")

    print(f"{cam_name}: Process started")

    try:
        while not stop_event.is_set():
            frame_start = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            detection_active = is_detection_time_active()
            if detection_active_last is None or detection_active_last != detection_active:
                state = "ON" if detection_active else "OFF"
                print(
                    f"{cam_name}: YOLO detection {state} "
                    f"({DETECTION_START_HOUR_24:02d}:00-{DETECTION_END_HOUR_24:02d}:00)"
                )
                detection_active_last = detection_active
                if not detection_active:
                    last_annotated_frame = None

            frame_counter += 1
            do_infer = detection_active and ((frame_counter % process_every_n_frames == 0) or (last_annotated_frame is None))
            person_count = 0

            if do_infer:
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
                inference_runs += 1
                total_inference_time_ms += (inf_end - inf_start) * 1000.0

                if first_frame_time is None:
                    first_frame_time = frame_start

                pc_to_person = {}

                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    if cls == 0 and conf > CONF_THRESHOLD:
                        person_count += 1
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        current_box = (x1, y1, x2, y2)
                        
                        # determine which PC this person is in
                        current_pc = get_pc_for_box(current_box, pc_rois) if ENABLE_PC_ROI else None
                        
                        matched_id = match_box_to_person(current_box, tracked_persons)
                        if matched_id is not None:
                            pdata = tracked_persons[matched_id]
                            pdata["last_box"] = current_box
                            person_name = pdata.get("name", f"Person {matched_id}")
                            
                            # PC dwell-time tracking
                            if current_pc:
                                if pdata.get("current_pc") == current_pc:
                                    # still in same PC
                                    pass
                                else:
                                    # entered new PC, start timer
                                    pdata["current_pc"] = current_pc
                                    pdata["pc_enter_time"] = frame_start
                                
                                # check if threshold met
                                dwell_time = frame_start - pdata.get("pc_enter_time", frame_start)
                                if dwell_time >= PERSON_OVERLAP_DWELL_SEC:
                                    pc_state = pc_states.get(current_pc, {})
                                    if pc_state.get("pc_on"):
                                        pdata["assigned_pc"] = current_pc
                                    else:
                                        pdata["assigned_pc"] = None
                            else:
                                # outside all PCs
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
                                    logs.append(
                                        {
                                            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                            "person_id": person_name,
                                            "confidence": round(conf, 3),
                                            "roi_file": filepath,
                                            "PCnum": pdata.get("assigned_pc"),
                                        }
                                    )
                                    print(f"{cam_name}: Saved ID {person_name} at {time.strftime('%H:%M:%S')}")
                        else:
                            matched_id = person_id_counter
                            person_id_counter += 1
                            while True:
                                random_id = f"{random.randint(0, 999):03d}"
                                if random_id not in used_ids:
                                    used_ids.add(random_id)
                                    break
                            person_folder = os.path.join(roi_dir, random_id)
                            os.makedirs(person_folder, exist_ok=True)
                            tracked_persons[matched_id] = {
                                "name": random_id,
                                "last_box": current_box,
                                "last_save": 0,
                                "folder": person_folder,
                                "current_pc": current_pc,
                                "pc_enter_time": frame_start if current_pc else None,
                                "assigned_pc": None,
                            }
                            person_name = random_id
                            print(f"{cam_name}: New person detected! Assigned ID: {random_id}")
                        color = (0, 255, 0)
                        label = f"ID:{person_name} conf:{conf:.2f}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                        if current_pc:
                            prev = pc_to_person.get(current_pc)
                            if prev is None or conf > prev[0]:
                                pc_to_person[current_pc] = (conf, person_name)

                pc_to_person_map = {pc_name: data[1] for pc_name, data in pc_to_person.items()}
                update_pc_states_from_monitor(frame, monitor_rois, pc_states, frame_start)
                update_pc_activity_events(
                    cam_name,
                    pc_states,
                    pc_to_person_map,
                    frame_start,
                    pc_event_logs,
                    pc_unattended_logs,
                )
                cv2.putText(frame, f"People: {person_count}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                last_annotated_frame = frame.copy()
            else:
                if detection_active:
                    if last_annotated_frame is not None:
                        frame = last_annotated_frame.copy()
                    cv2.putText(frame, f"People: {len(tracked_persons)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
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

            update_shared_pc_state_map(shared_pc_state_map, pc_states)

            frame_end = time.time()
            latency_ms = (frame_end - frame_start) * 1000.0
            frames_seen += 1
            total_latency_ms += latency_ms
            if last_frame_time is not None:
                dt = frame_end - last_frame_time
                if dt > 0:
                    fps = 1.0 / dt
            last_frame_time = frame_end
            cv2.putText(frame, f"FPS: {fps:.1f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            cv2.putText(frame, f"Latency: {latency_ms:.1f} ms", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

            if SHOW_WINDOWS == "Show":
                display_frame = cv2.resize(frame, (Windows_width, Windows_height))
                cv2.imshow(f"YOLO Person Detection ({cam_name})", display_frame)
                if cv2.getWindowProperty(f"YOLO Person Detection ({cam_name})", cv2.WND_PROP_VISIBLE) < 1:
                    break
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    stop_event.set()
                    break

    except KeyboardInterrupt:
        print(f"\nInterrupted by user (KeyboardInterrupt) in {cam_name}")

    update_shared_pc_state_map(shared_pc_state_map, pc_states)

    cap.release()
    cv2.destroyAllWindows()

    # stop resource monitor if it was started
    if ENABLE_RESOURCE_MONITOR and monitor_stop is not None and monitor_thread is not None:
        try:
            from tool.resource_monitor import stop_resource_monitor

            stop_resource_monitor(monitor_stop, monitor_thread, timeout=2.0)
            print(f"{cam_name}: Resource monitor stopped")
        except Exception:
            try:
                monitor_stop.set()
                monitor_thread.join(timeout=2.0)
            except Exception:
                pass

    # Save logs per camera
    df = pd.DataFrame(logs)
    safe_name = cam_label
    csv_filename = f"people_with_conf_and_roi_{safe_name or f'cam{cam_idx}'}_{session_tag}.csv"
    csv_path = os.path.join(log_dir, csv_filename)
    df.to_csv(csv_path, index=False)

    # PC activity event log (USING_PC / NON_PC_ACTIVITY)
    pc_event_df = pd.DataFrame(pc_event_logs)
    pc_event_csv = os.path.join(
        log_dir,
        f"pc_activity_events_{safe_name or f'cam{cam_idx}'}_{session_tag}.csv",
    )
    pc_event_df.to_csv(pc_event_csv, index=False)

    unattended_count = len(pc_unattended_logs)
    if shared_unattended_logs is not None and unattended_count > 0:
        try:
            shared_unattended_logs.extend(pc_unattended_logs)
        except Exception:
            for row in pc_unattended_logs:
                shared_unattended_logs.append(row)

    print(f"\n=== Session Summary ({cam_name}) ===")
    print(f"Total unique persons detected: {len(tracked_persons)}")
    print(f"Logs saved to {csv_path}")
    print(f"PC activity events saved to {pc_event_csv}")
    print(f"Unattended/person flags captured: {unattended_count}")

    frames = frames_seen
    total_latency_ms = total_latency_ms
    inference_runs = inference_runs
    total_inference_time_ms = total_inference_time_ms
    first_t = first_frame_time
    last_t = last_frame_time
    total_runtime_s = None
    if first_t is not None and last_t is not None and last_t > first_t:
        total_runtime_s = last_t - first_t

    avg_latency = (total_latency_ms / frames) if frames > 0 else 0.0
    avg_inference = (total_inference_time_ms / inference_runs) if inference_runs > 0 else 0.0
    avg_fps = (frames / total_runtime_s) if total_runtime_s and total_runtime_s > 0 else fps

    print(f"Frames processed: {frames}")
    if total_runtime_s:
        print(f"Total runtime: {total_runtime_s:.2f} s")
    print(f"Average FPS: {avg_fps:.2f}")
    print(f"Average latency/frame: {avg_latency:.1f} ms")
    print(f"Inference runs: {inference_runs} (avg {avg_inference:.1f} ms per inference)")
    print("===============================")

    # append a per-camera summary row to a global performance CSV (create if missing)
    try:
        perf_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(first_frame_time or time.time()))
        perf_row = {
            "session_timestamp": perf_timestamp,
            "cam_idx": cam_idx,
            "cam_name": cam_name,
            "frames": frames,
            "total_runtime_s": total_runtime_s if total_runtime_s is not None else 0.0,
            "avg_fps": float(f"{avg_fps:.2f}"),
            "avg_latency_ms": float(f"{avg_latency:.1f}"),
            "inference_runs": inference_runs,
            "avg_inference_ms": float(f"{avg_inference:.1f}"),
            "total_inference_ms": float(f"{total_inference_time_ms:.1f}"),
            "unique_persons": len(tracked_persons),
            "log_csv": csv_path,
            "roi_dir": roi_dir,
        }

        perf_df = pd.DataFrame([perf_row])
        write_header = not os.path.exists(PERF_SUMMARY_FILE)
        perf_df.to_csv(PERF_SUMMARY_FILE, mode="a", index=False, header=write_header)
        print(f"Performance summary appended to {PERF_SUMMARY_FILE}")
    except Exception as e:
        print(f"Failed to write performance summary for {cam_name}: {e}")


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    session_tag = time.strftime("%Y%m%d_%H%M%S")
    pc_state_all_csv = os.path.join(LOG_BASE_DIR, f"pc_state_all_{session_tag}.csv")
    all_unattended_csv = os.path.join(LOG_BASE_DIR, f"pc_unattended_flags_{session_tag}.csv")

    shared_manager = mp.Manager()
    shared_unattended_logs = shared_manager.list()

    shared_pc_state_map = None
    pc_state_writer_stop = None
    pc_state_writer_thread = None

    if ENABLE_REALTIME_PC_STATE_CSV:
        shared_pc_state_map = shared_manager.dict()
        pc_state_writer_stop = threading.Event()

        # create file immediately so downstream readers can open it before first update cycle
        write_pc_state_csv_from_map(shared_pc_state_map, pc_state_all_csv)
        pc_state_writer_thread = threading.Thread(
            target=realtime_pc_state_writer,
            args=(shared_pc_state_map, pc_state_all_csv, pc_state_writer_stop, REALTIME_PC_STATE_WRITE_INTERVAL_SEC),
            daemon=True,
        )
        pc_state_writer_thread.start()
        print(f"Realtime PC-state CSV started: {pc_state_all_csv}")

    print("=== Auto ID Assignment (4 Cams) ===")
    print("Each detected person gets a random 3-digit ID automatically")
    print("ROIs saved every 10 seconds to roi_images/<CAM_NAME>/<ID>/")
    print(f"YOLO detection schedule: {DETECTION_START_HOUR_24:02d}:00-{DETECTION_END_HOUR_24:02d}:00 (local time)")
    print(f"Person overlap dwell threshold: {PERSON_OVERLAP_DWELL_SEC:.0f}s")
    print(f"PC ON + no person unattended threshold: {PC_ON_NO_PERSON_DWELL_SEC/60:.0f} minutes")
    print("Press 'q' to quit")
    print("===================================\n")

    stop_event = mp.Event()
    processes = []

    for cam_idx in CAM_INDEXES:
        p = mp.Process(
            target=camera_process_fn,
            args=(cam_idx, stop_event, session_tag, shared_pc_state_map, shared_unattended_logs),
            daemon=True,
        )
        p.start()
        processes.append(p)

    try:
        while any(p.is_alive() for p in processes):
            if stop_event.is_set():
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user (KeyboardInterrupt)")
        stop_event.set()

    for p in processes:
        p.join()

    if ENABLE_REALTIME_PC_STATE_CSV and pc_state_writer_thread is not None:
        pc_state_writer_stop.set()
        pc_state_writer_thread.join(timeout=2.0)
        write_pc_state_csv_from_map(shared_pc_state_map, pc_state_all_csv)
        print(f"Realtime all-PC state CSV saved to {pc_state_all_csv}")

    all_unattended_df = pd.DataFrame(
        list(shared_unattended_logs),
        columns=["time", "cam_name", "pc_name", "last_person_id", "pc_on", "empty_dwell_sec", "reason"],
    )
    all_unattended_df.to_csv(all_unattended_csv, index=False)
    print(f"Combined unattended/person-flag CSV saved to {all_unattended_csv}")

    try:
        shared_manager.shutdown()
    except Exception:
        pass
