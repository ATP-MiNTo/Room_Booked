import csv
import glob
import json
import os

import cv2
import numpy as np


ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
SEAT_CSV_SUFFIX = "_roi.csv"
MONITOR_CSV_SUFFIX = "_monitor_roi.csv"
WINDOW_NAME = "ROI Config Viewer"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

CAM_NAME_TO_INDEX = {
    "Front_right": 0,
    "Front_left": 1,
    "Back_left": 2,
    "Back_right": 3,
}

TEXT_COLOR = (255, 255, 255)
TITLE_COLOR = (0, 255, 255)
SEAT_POLY_COLOR = (0, 255, 0)
MONITOR_POLY_COLOR = (255, 0, 255)


def normalize_quad(points):
    pts = np.array(points, dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return [tl.astype(int).tolist(), tr.astype(int).tolist(), br.astype(int).tolist(), bl.astype(int).tolist()]


def parse_cam_name_and_type(csv_path):
    name = os.path.basename(csv_path)
    if name.endswith(MONITOR_CSV_SUFFIX):
        return name[: -len(MONITOR_CSV_SUFFIX)], "monitor"
    if name.endswith(SEAT_CSV_SUFFIX):
        return name[: -len(SEAT_CSV_SUFFIX)], "seat"
    return os.path.splitext(name)[0], "unknown"


def load_roi_csv(csv_path):
    rois = []
    with open(csv_path, "r", encoding="utf-8", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            pc_name = (row.get("pc_name") or "").strip()
            points_json = row.get("points_json") or "[]"
            try:
                points = json.loads(points_json)
            except json.JSONDecodeError:
                continue
            if not isinstance(points, list) or len(points) < 3:
                continue
            rois.append({"pc_name": pc_name or "PC", "points": points})
    return rois


def discover_roi_setups():
    seat_files = sorted(glob.glob(os.path.join(ROI_CONFIG_DIR, f"*{SEAT_CSV_SUFFIX}")))
    monitor_files = sorted(glob.glob(os.path.join(ROI_CONFIG_DIR, f"*{MONITOR_CSV_SUFFIX}")))

    # monitor files also match *{SEAT_CSV_SUFFIX}, remove them from seat list
    monitor_file_set = set(monitor_files)
    seat_files = [path for path in seat_files if path not in monitor_file_set]

    setups = {}

    for csv_path in seat_files:
        cam_name, _ = parse_cam_name_and_type(csv_path)
        rois = load_roi_csv(csv_path)
        if cam_name not in setups:
            setups[cam_name] = {
                "cam_name": cam_name,
                "seat_rois": [],
                "monitor_rois": [],
                "seat_csv": None,
                "monitor_csv": None,
            }
        setups[cam_name]["seat_rois"] = rois
        setups[cam_name]["seat_csv"] = csv_path

    for csv_path in monitor_files:
        cam_name, _ = parse_cam_name_and_type(csv_path)
        rois = load_roi_csv(csv_path)
        if cam_name not in setups:
            setups[cam_name] = {
                "cam_name": cam_name,
                "seat_rois": [],
                "monitor_rois": [],
                "seat_csv": None,
                "monitor_csv": None,
            }
        setups[cam_name]["monitor_rois"] = rois
        setups[cam_name]["monitor_csv"] = csv_path

    ordered = list(setups.values())

    def setup_sort_key(item):
        cam_name = item["cam_name"]
        if cam_name in CAM_NAME_TO_INDEX:
            return (0, CAM_NAME_TO_INDEX[cam_name])
        return (1, cam_name)

    ordered.sort(key=setup_sort_key)
    return ordered


def open_camera(cam_name, fallback_index=0):
    cam_index = CAM_NAME_TO_INDEX.get(cam_name, fallback_index)
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


def draw_no_camera_screen(cam_name):
    canvas = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    cv2.putText(canvas, f"Camera: {cam_name}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, TITLE_COLOR, 2)
    cv2.putText(canvas, "Camera cannot be opened.", (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, TEXT_COLOR, 2)
    return canvas


def draw_overlay(frame, setup, cam_idx, total):
    canvas = frame.copy()
    cam_name = setup["cam_name"]
    seat_rois = setup.get("seat_rois", [])
    monitor_rois = setup.get("monitor_rois", [])

    cam_index = CAM_NAME_TO_INDEX.get(cam_name, "?")
    header = (
        f"Camera {cam_idx + 1}/{total}: {cam_name} (index {cam_index}) | "
        f"Seat ROI: {len(seat_rois)} | Monitor ROI: {len(monitor_rois)}"
    )
    cv2.putText(canvas, header, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TITLE_COLOR, 2)

    help_text = "Keys: < Prev | > Next | q Quit"
    cv2.putText(canvas, help_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_COLOR, 2)

    y = 90
    if seat_rois:
        cv2.putText(canvas, "Seat ROI (green)", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, SEAT_POLY_COLOR, 2)
        y += 24
        for roi in seat_rois:
            ordered = normalize_quad(roi["points"])
            poly = np.array(ordered, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [poly], True, SEAT_POLY_COLOR, 2)

            label_anchor = tuple(ordered[0])
            cv2.putText(canvas, roi["pc_name"], label_anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.65, SEAT_POLY_COLOR, 2)

            cv2.putText(canvas, roi["pc_name"], (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)
            y += 20

    if monitor_rois:
        y += 10
        cv2.putText(canvas, "Monitor ROI (magenta)", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, MONITOR_POLY_COLOR, 2)
        y += 24
        for roi in monitor_rois:
            ordered = normalize_quad(roi["points"])
            poly = np.array(ordered, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [poly], True, MONITOR_POLY_COLOR, 2)

            label_anchor = tuple(ordered[0])
            cv2.putText(canvas, roi["pc_name"], label_anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.65, MONITOR_POLY_COLOR, 2)

            cv2.putText(canvas, roi["pc_name"], (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 255), 1)
            y += 20

    if not seat_rois and not monitor_rois:
        cv2.putText(canvas, "No ROI found for this camera.", (10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)

    return canvas


def is_prev_key(key):
    return key in (ord(","), ord("<"), 2424832)


def is_next_key(key):
    return key in (ord("."), ord(">"), 2555904)


def main():
    setups = discover_roi_setups()
    if not setups:
        print(f"No ROI CSV found in: {ROI_CONFIG_DIR}")
        return

    print("Loaded ROI setups:")
    for i, setup in enumerate(setups, start=1):
        seat_count = len(setup.get("seat_rois", []))
        monitor_count = len(setup.get("monitor_rois", []))
        print(
            f"  {i}. {setup['cam_name']} | seat={seat_count} monitor={monitor_count} "
            f"| seat_csv={setup.get('seat_csv')} | monitor_csv={setup.get('monitor_csv')}"
        )

    active_idx = 0
    cap = open_camera(setups[active_idx]["cam_name"], active_idx)
    cv2.namedWindow(WINDOW_NAME)

    while True:
        setup = setups[active_idx]

        if cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                frame = draw_no_camera_screen(setup["cam_name"])
        else:
            frame = draw_no_camera_screen(setup["cam_name"])

        canvas = draw_overlay(frame, setup, active_idx, len(setups))
        cv2.imshow(WINDOW_NAME, canvas)

        key = cv2.waitKeyEx(1)

        if key in (ord("q"), ord("Q"), 27):
            break

        if is_prev_key(key):
            active_idx = (active_idx - 1) % len(setups)
            cap.release()
            cap = open_camera(setups[active_idx]["cam_name"], active_idx)
            continue

        if is_next_key(key):
            active_idx = (active_idx + 1) % len(setups)
            cap.release()
            cap = open_camera(setups[active_idx]["cam_name"], active_idx)
            continue

        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
