import cv2
from ultralytics import YOLO
import time
import torch
import os
import pandas as pd
import random
import multiprocessing as mp
import json
import numpy as np


# -------------------------------------Configuration--------------------------------------------
# Camera settings
CAM_INDEXES = [0, 1, 2, 3]
CAM_NAMES = {
    0: "Cam 0",
    1: "Cam 1",
    2: "Cam 2",
    3: "Cam 3",
}
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Window display settings
# lower resolution for better performance | Hide for best performance
SHOW_WINDOWS = "Show"  # Show or Hide
Windows_width, Windows_height = 960, 540

# Detection settings
CONF_THRESHOLD = 0.4  # minimum confidence threshold for person detection
SAVE_INTERVAL_SEC = 10  # seconds between saving ROIs of the same person

# PC ROI settings
ENABLE_PC_ROI = True  # set to True to load ROI polygons and assign PCnum
PC_DWELL_TIME_SEC = 3.0  # seconds a person must stay in PC area before tagging PCnum
ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
CSV_SUFFIX = "_roi.csv"

# Tracking settings
# NOTE: Resource monitor is disabled in multiprocessing mode by default, because it expects
# shared in-memory camera state. You can re-enable per-process monitoring if needed.
ENABLE_RESOURCE_MONITOR = False

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
    except Exception:
        pass

    return model, device, cuda_available


def camera_process_fn(cam_idx, stop_event):
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

    tracked_persons = {}
    person_id_counter = 0
    used_ids = set()
    logs = []

    last_frame_time = None
    fps = 0.0
    process_every_n_frames = 2
    frame_counter = 0
    last_annotated_frame = None

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

            frame_counter += 1
            do_infer = (frame_counter % process_every_n_frames == 0) or (last_annotated_frame is None)
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
                                if dwell_time >= PC_DWELL_TIME_SEC and pdata.get("assigned_pc") is None:
                                    pdata["assigned_pc"] = current_pc
                                    print(f"{cam_name}: ID {person_name} tagged as {current_pc} (dwell {dwell_time:.1f}s)")
                            else:
                                # outside all PCs
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
                cv2.putText(frame, f"People: {person_count}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                last_annotated_frame = frame.copy()
            else:
                if last_annotated_frame is not None:
                    frame = last_annotated_frame.copy()
                cv2.putText(frame, f"People: {len(tracked_persons)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

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
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    csv_filename = f"people_with_conf_and_roi_{safe_name or f'cam{cam_idx}'}_{timestamp}.csv"
    csv_path = os.path.join(log_dir, csv_filename)
    df.to_csv(csv_path, index=False)

    print(f"\n=== Session Summary ({cam_name}) ===")
    print(f"Total unique persons detected: {len(tracked_persons)}")
    print(f"Logs saved to {csv_path}")

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

    print("=== Auto ID Assignment (4 Cams) ===")
    print("Each detected person gets a random 3-digit ID automatically")
    print("ROIs saved every 10 seconds to roi_images/<CAM_NAME>/<ID>/")
    print("Press 'q' to quit")
    print("===================================\n")

    stop_event = mp.Event()
    processes = []

    for cam_idx in CAM_INDEXES:
        p = mp.Process(target=camera_process_fn, args=(cam_idx, stop_event), daemon=True)
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
