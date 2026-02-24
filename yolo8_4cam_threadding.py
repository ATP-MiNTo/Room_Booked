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
SAVE_INTERVAL_SEC = 10 # seconds between saving ROIs of the same person

# PC ROI settings
ENABLE_PC_ROI = True  # set to True to load ROI polygons and assign PCnum
PC_DWELL_TIME_SEC = 3.0  # seconds a person must stay in PC area before tagging PCnum
ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
CSV_SUFFIX = "_roi.csv"

# Tracking settings
ENABLE_RESOURCE_MONITOR = False # set to True to enable resource monitoring (requires resource_monitor.py)

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


def load_camera_rois(cam_label):
    """Load PC ROI polygons from CSV for the given camera label."""
    csv_path = os.path.join(ROI_CONFIG_DIR, f"{cam_label}{CSV_SUFFIX}")
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
        # performance tracking
        "frames_seen": 0,
        "total_latency_ms": 0.0,
        "inference_runs": 0,
        "total_inference_time_ms": 0.0,
        "first_frame_time": None,
        "name": cam_name,
        "label": cam_label,
        "pc_rois": pc_rois
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

            # increment per-camera frame counter and decide whether to run inference
            cam_data["frame_counter"] += 1
            do_infer = (
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
                                if dwell_time >= PC_DWELL_TIME_SEC and pdata.get("assigned_pc") is None:
                                    pdata["assigned_pc"] = current_pc
                                    print(f"{cam_data['name']}: ID {person_name} tagged as {current_pc} (dwell {dwell_time:.1f}s)")
                            else:
                                # outside all PCs, reset
                                pdata["current_pc"] = None
                                pdata["pc_enter_time"] = None
                            
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
                cv2.putText(frame, f"People: {person_count}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cam_data["last_annotated_frame"] = frame.copy()
            else:
                if cam_data["last_annotated_frame"] is not None:
                    frame = cam_data["last_annotated_frame"].copy()
                cv2.putText(frame, f"People: {len(cam_data['tracked_persons'])}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

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
for cam_idx, cam_data in cams.items():
    df = pd.DataFrame(cam_data["logs"])
    safe_name = cam_data.get("label") or to_safe_label(cam_data.get("name", f"cam{cam_idx}"))
    # add a timestamp to the filename so multiple sessions are preserved
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    csv_filename = f"people_with_conf_and_roi_{safe_name or f'cam{cam_idx}'}_{timestamp}.csv"
    csv_path = os.path.join(cam_data.get("log_dir", LOG_BASE_DIR), csv_filename)
    df.to_csv(csv_path, index=False)

    print(f"\n=== Session Summary ({cam_data['name']}) ===")
    print(f"Total unique persons detected: {len(cam_data['tracked_persons'])}")
    print(f"Logs saved to {csv_path}")
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
            "log_csv": csv_path,
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
