import cv2
from ultralytics import YOLO
import time
import os
import pandas as pd
import random

# -----------------------
# Configuration
# -----------------------
CAM_INDEXES = [0, 1, 2, 3]
CAM_NAMES = {
    0: "Cam 0",
    1: "Cam 1",
    2: "Cam 2",
    3: "Cam 3",
}
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
CONF_THRESHOLD = 0.4
SAVE_INTERVAL_SEC = 10
ROI_BASE_DIR = "roi_images"

# Load model once
model = YOLO("yolov8n.pt")

# Create base ROI directory
os.makedirs(ROI_BASE_DIR, exist_ok=True)

# Per-camera state
cams = {}

for cam_idx in CAM_INDEXES:
    cap = cv2.VideoCapture(cam_idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cam_name = CAM_NAMES.get(cam_idx, f"Cam {cam_idx}")
    cams[cam_idx] = {
        "cap": cap,
        "tracked_persons": {},
        "person_id_counter": 0,
        "used_ids": set(),
        "logs": [],
        "window": f"YOLO Person Detection ({cam_name})",
        "roi_dir": os.path.join(ROI_BASE_DIR, f"cam{cam_idx}"),
        "last_frame_time": None,
        "fps": 0.0,
        "name": cam_name
    }
    os.makedirs(cams[cam_idx]["roi_dir"], exist_ok=True)


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


print("=== Auto ID Assignment (4 Cams) ===")
print("Each detected person gets a random 3-digit ID automatically")
print("ROIs saved every 10 seconds to roi_images/cam<idx>/<ID>/")
print("Press 'q' to quit")
print("===================================\n")

while True:
    any_frame = False

    for cam_idx, cam_data in cams.items():
        cap = cam_data["cap"]
        if not cap.isOpened():
            continue

        frame_start = time.time()
        ret, frame = cap.read()
        if not ret:
            continue

        any_frame = True

        results = model(frame, verbose=False)
        person_count = 0

        for box in results[0].boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])

            # class 0 = person
            if cls == 0 and conf > CONF_THRESHOLD:
                person_count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                current_box = (x1, y1, x2, y2)

                # Match with tracked person
                matched_id = match_box_to_person(current_box, cam_data["tracked_persons"])

                if matched_id is not None:
                    # Update box position
                    cam_data["tracked_persons"][matched_id]["last_box"] = current_box
                    person_name = cam_data["tracked_persons"][matched_id].get(
                        "name", f"Person {matched_id}"
                    )

                    # Check save interval
                    current_time = time.time()
                    last_save = cam_data["tracked_persons"][matched_id].get("last_save", 0)

                    if person_name != f"Person {matched_id}" and current_time - last_save >= SAVE_INTERVAL_SEC:
                        roi = frame[y1:y2, x1:x2]
                        if roi.size > 0:
                            person_folder = cam_data["tracked_persons"][matched_id]["folder"]
                            filename = f"ID{person_name}_{int(current_time)}.jpg"
                            filepath = os.path.join(person_folder, filename)
                            cv2.imwrite(filepath, roi)

                            cam_data["tracked_persons"][matched_id]["last_save"] = current_time

                            cam_data["logs"].append(
                                {
                                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "person_id": person_name,
                                    "confidence": round(conf, 3),
                                    "roi_file": filepath,
                                }
                            )
                            print(
                                f"{cam_data['name']}: Saved ID {person_name} at {time.strftime('%H:%M:%S')}"
                            )
                else:
                    # Create new person with random 3-digit ID
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
                    }
                    person_name = random_id
                    print(f"{cam_data['name']}: New person detected! Assigned ID: {random_id}")

                # Draw box
                color = (0, 255, 0)
                label = f"ID:{person_name} conf:{conf:.2f}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

        # Show count
        cv2.putText(
            frame,
            f"People: {person_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2,
        )

        # Compute FPS and latency (per-camera)
        frame_end = time.time()
        latency_ms = (frame_end - frame_start) * 1000.0
        if cam_data["last_frame_time"] is not None:
            dt = frame_end - cam_data["last_frame_time"]
            if dt > 0:
                cam_data["fps"] = 1.0 / dt
        cam_data["last_frame_time"] = frame_end

        cv2.putText(
            frame,
            f"FPS: {cam_data['fps']:.1f}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Latency: {latency_ms:.1f} ms",
            (20, 115),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2,
        )

        # Resize for display
        display_frame = cv2.resize(frame, (1280, 720))
        cv2.imshow(cam_data["window"], display_frame)

        # Check if window closed
        if cv2.getWindowProperty(cam_data["window"], cv2.WND_PROP_VISIBLE) < 1:
            any_frame = False

    # Exit if no cameras are producing frames
    if not any_frame:
        break

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

# Release cameras and close windows
for cam_data in cams.values():
    cap = cam_data["cap"]
    if cap:
        cap.release()

cv2.destroyAllWindows()

# Save logs per camera
for cam_idx, cam_data in cams.items():
    df = pd.DataFrame(cam_data["logs"])
    safe_name = "".join(c for c in cam_data["name"] if c.isalnum() or c in ("-", "_"))
    csv_name = f"people_with_conf_and_roi_{safe_name or f'cam{cam_idx}'}.csv"
    df.to_csv(csv_name, index=False)

    print(f"\n=== Session Summary ({cam_data['name']}) ===")
    print(f"Total unique persons detected: {len(cam_data['tracked_persons'])}")
    print(f"Logs saved to {csv_name}")
    print("===============================")
