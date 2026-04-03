import csv
import glob
import json
import os
import statistics
import time
from datetime import datetime

import cv2
import numpy as np


ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
GROUNDTRUTH_DIR = os.path.join("tool", "groundtruth")
SEAT_CSV_SUFFIX = "_roi.csv"
MONITOR_CSV_SUFFIX = "_monitor_roi.csv"
GT_CSV_SUFFIX = "_gt.csv"
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


def parse_time_to_seconds(time_text):
    try:
        dt = datetime.strptime(str(time_text).strip(), "%Y-%m-%d %H:%M:%S")
        return (
            dt.toordinal() * 86400
            + dt.hour * 3600
            + dt.minute * 60
            + dt.second
        )
    except Exception:
        return None


def infer_sample_sec(sorted_seconds):
    if len(sorted_seconds) < 2:
        return 1.0

    deltas = []
    for i in range(1, len(sorted_seconds)):
        delta = sorted_seconds[i] - sorted_seconds[i - 1]
        if delta > 0:
            deltas.append(delta)

    if not deltas:
        return 1.0

    try:
        return float(max(1, int(round(statistics.median(deltas)))))
    except Exception:
        return 1.0


def load_groundtruth_summary(csv_path):
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)

    if not rows:
        return {
            "sample_sec": 1.0,
            "by_pc": {},
        }

    times = []
    for row in rows:
        sec = parse_time_to_seconds(row.get("time", ""))
        if sec is not None:
            times.append(sec)

    sample_sec = infer_sample_sec(sorted(set(times)))
    by_pc = {}
    timeline_by_pc = {}

    for row in rows:
        pc_name = (row.get("pc_name") or "").strip()
        if not pc_name:
            continue

        occupied_raw = row.get("occupied_gt", 0)
        try:
            occupied = 1 if int(float(occupied_raw)) > 0 else 0
        except Exception:
            occupied = 0

        if pc_name not in by_pc:
            by_pc[pc_name] = {
                "total_rows": 0,
                "occupied_rows": 0,
                "occupied_time_sec": 0.0,
            }
            timeline_by_pc[pc_name] = {}

        by_pc[pc_name]["total_rows"] += 1
        by_pc[pc_name]["occupied_rows"] += occupied
        sec = parse_time_to_seconds(row.get("time", ""))
        if sec is not None:
            # Last write wins for duplicate (pc_name, second).
            timeline_by_pc[pc_name][sec] = occupied

    for pc_name in by_pc:
        points = sorted(timeline_by_pc.get(pc_name, {}).items(), key=lambda item: item[0])
        occupied_time = 0.0

        if points:
            for i in range(len(points) - 1):
                cur_sec, cur_occ = points[i]
                next_sec, _ = points[i + 1]
                delta = max(0.0, float(next_sec - cur_sec))
                if int(cur_occ) > 0:
                    occupied_time += delta

            # Include a tail interval for the last state using inferred sample interval.
            if int(points[-1][1]) > 0:
                occupied_time += float(sample_sec)

        by_pc[pc_name]["occupied_time_sec"] = occupied_time

    return {
        "sample_sec": sample_sec,
        "by_pc": by_pc,
    }


def discover_groundtruth_summaries():
    gt_files = sorted(glob.glob(os.path.join(GROUNDTRUTH_DIR, f"*{GT_CSV_SUFFIX}")))
    summaries = {}

    for path in gt_files:
        cam_name = os.path.basename(path)[: -len(GT_CSV_SUFFIX)]
        try:
            summary = load_groundtruth_summary(path)
            summary["csv_path"] = path
            summaries[cam_name] = summary
        except Exception:
            continue

    return summaries


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

    gt_summaries = discover_groundtruth_summaries()
    for cam_name, setup in setups.items():
        gt = gt_summaries.get(cam_name)
        setup["gt_summary"] = gt

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
    gt_summary = setup.get("gt_summary")
    gt_by_pc = gt_summary.get("by_pc", {}) if gt_summary else {}

    cam_index = CAM_NAME_TO_INDEX.get(cam_name, "?")
    header = (
        f"Camera {cam_idx + 1}/{total}: {cam_name} (index {cam_index}) | "
        f"Seat ROI: {len(seat_rois)} | Monitor ROI: {len(monitor_rois)}"
    )
    cv2.putText(canvas, header, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TITLE_COLOR, 2)

    help_text = "Keys: < Prev | > Next | q Quit"
    cv2.putText(canvas, help_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_COLOR, 2)

    if gt_summary:
        gt_header = f"GT loaded | sample={gt_summary.get('sample_sec', 1.0):.1f}s"
    else:
        gt_header = "GT not found"
    cv2.putText(canvas, gt_header, (10, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)

    y = 112
    if seat_rois:
        cv2.putText(canvas, "Seat ROI (green)", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, SEAT_POLY_COLOR, 2)
        y += 24
        for roi in seat_rois:
            ordered = normalize_quad(roi["points"])
            poly = np.array(ordered, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [poly], True, SEAT_POLY_COLOR, 2)

            label_anchor = tuple(ordered[0])
            cv2.putText(canvas, roi["pc_name"], label_anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.65, SEAT_POLY_COLOR, 2)

            gt_text = ""
            if roi["pc_name"] in gt_by_pc:
                sec = float(gt_by_pc[roi["pc_name"]].get("occupied_time_sec", 0.0))
                gt_text = f" | GT {sec:.0f}s"
            cv2.putText(canvas, f"{roi['pc_name']}{gt_text}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)
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
        gt_summary = setup.get("gt_summary")
        gt_info = "gt=none"
        if gt_summary:
            gt_info = f"gt=loaded sample={gt_summary.get('sample_sec', 1.0):.1f}s"
        print(
            f"  {i}. {setup['cam_name']} | seat={seat_count} monitor={monitor_count} "
            f"| seat_csv={setup.get('seat_csv')} | monitor_csv={setup.get('monitor_csv')} | {gt_info}"
        )
        if gt_summary:
            gt_by_pc = gt_summary.get("by_pc", {})
            for pc_name in sorted(gt_by_pc.keys()):
                sec = float(gt_by_pc[pc_name].get("occupied_time_sec", 0.0))
                print(f"      - {pc_name}: GT occupied {sec:.0f}s")

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
