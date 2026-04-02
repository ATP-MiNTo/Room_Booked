import argparse
import json
import os
import time
import tkinter as tk
from tkinter import filedialog

import cv2
import numpy as np
import pandas as pd

CONFIG_FILE_PATH = os.path.join("tool", "threaded_config.yaml")


def parse_args():
    parser = argparse.ArgumentParser(description="Groundtruth labeler for seat occupancy")
    parser.add_argument("--video", default="", help="Video file path. If omitted, opens file picker")
    parser.add_argument("--cam-label", default="", help="Override camera label used for ROI/groundtruth naming")
    parser.add_argument("--sample-sec", type=float, default=1.0, help="Sampling interval in seconds")
    parser.add_argument(
        "--groundtruth-dir",
        default=os.path.join("tool", "groundtruth"),
        help="Groundtruth output directory",
    )
    return parser.parse_args()


def load_runtime_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    import yaml

    with open(config_path, "r", encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Invalid config format in {config_path}")
    return loaded


def to_safe_label(value):
    cleaned = "".join((c if c.isalnum() or c in ("-", "_") else "_") for c in str(value).strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "unknown"


def pick_video_file():
    root = tk.Tk()
    root.withdraw()
    root.update()
    path = filedialog.askopenfilename(
        title="Select video for groundtruth labeling",
        filetypes=[
            ("Video files", "*.mp4 *.avi *.mov *.mkv"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return path


def load_rois(roi_csv_path):
    if not os.path.exists(roi_csv_path):
        raise FileNotFoundError(f"ROI file not found: {roi_csv_path}")

    df = pd.read_csv(roi_csv_path)
    rois = []
    for _, row in df.iterrows():
        pc_name = str(row.get("pc_name", "")).strip()
        points = json.loads(row.get("points_json", "[]"))
        if not pc_name or not isinstance(points, list) or len(points) < 3:
            continue
        polygon = np.array(points, dtype=np.int32)
        rois.append({"pc_name": pc_name, "polygon": polygon})

    if not rois:
        raise ValueError(f"No valid ROI rows in {roi_csv_path}")
    return rois


def point_in_polygon(point, polygon):
    return cv2.pointPolygonTest(polygon, point, False) >= 0


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


def draw_overlay(frame, rois, states, selected_pc_name, sec_cursor, frame_idx, total_frames, fps):
    canvas = frame.copy()

    for roi in rois:
        pc_name = roi["pc_name"]
        state = states.get(pc_name, {"occupied": 0, "people_count": 0, "video_count": 0})
        occupied = int(state.get("occupied", 0))
        people_count = int(state.get("people_count", 0))
        video_count = int(state.get("video_count", 0))

        color = (0, 255, 0) if occupied else (0, 0, 255)
        if pc_name == selected_pc_name:
            color = (0, 255, 255)

        poly = roi["polygon"].reshape((-1, 1, 2))
        cv2.polylines(canvas, [poly], True, color, 2)

        anchor = tuple(roi["polygon"][0])
        text = f"{pc_name} occ={occupied} cnt={video_count}"
        cv2.putText(canvas, text, anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    timeline = f"t={format_video_clock(sec_cursor)} ({sec_cursor:.1f}s) | frame={frame_idx}/{total_frames} | fps={fps:.2f}"
    cv2.putText(canvas, timeline, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    help_text_1 = "Mouse click ROI: select+toggle occupied | +/-: people_count | c: capture second | space: play/pause"
    help_text_2 = "a/d: -/+1 sec | j/l: -/+5 sec | s: save CSV | q: quit"
    cv2.putText(canvas, help_text_1, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    cv2.putText(canvas, help_text_2, (20, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    return canvas


def main():
    args = parse_args()
    config = load_runtime_config(CONFIG_FILE_PATH)

    video_path = str(args.video).strip() or pick_video_file()
    if not video_path:
        print("No video selected. Exit.")
        return
    if not os.path.exists(video_path):
        print(f"Video not found: {video_path}")
        return

    video_stem = os.path.splitext(os.path.basename(video_path))[0]
    cam_label = to_safe_label(args.cam_label.strip() or video_stem)
    cam_name = cam_label

    roi_config_dir = os.path.normpath(str(config.get("ROI_CONFIG_DIR", os.path.join("tool", "roi_config"))))
    roi_csv_path = os.path.join(roi_config_dir, f"{cam_label}_roi.csv")

    try:
        rois = load_rois(roi_csv_path)
    except Exception as e:
        print(f"Failed to load ROIs: {e}")
        return

    os.makedirs(args.groundtruth_dir, exist_ok=True)
    gt_csv_path = os.path.join(os.path.normpath(args.groundtruth_dir), f"{cam_label}_gt.csv")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Cannot open video: {video_path}")
        return

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    sample_sec = max(0.1, float(args.sample_sec))
    sec_states = {}
    current_states = {
        roi["pc_name"]: {"occupied": 0, "people_count": 0, "video_count": 0, "user_ids": set()}
        for roi in rois
    }

    play_mode = False
    selected_pc_name = ""
    sec_cursor = 0.0

    window_name = "Groundtruth Labeler"
    cv2.namedWindow(window_name)

    def capture_current_second():
        sec_key = int(round(sec_cursor))
        for roi in rois:
            pc_name = roi["pc_name"]
            seat_state = current_states.get(pc_name, {"occupied": 0, "people_count": 0})
            occupied = 1 if int(seat_state.get("occupied", 0)) > 0 else 0
            people_count = max(0, int(seat_state.get("video_count", 0)))
            sec_states[(sec_key, pc_name)] = {
                "occupied_gt": occupied,
                "people_count_gt": people_count,
            }

    def on_mouse(event, x, y, flags, param):
        nonlocal selected_pc_name
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        for roi in rois:
            if point_in_polygon((x, y), roi["polygon"]):
                pc_name = roi["pc_name"]
                selected_pc_name = pc_name
                prev_occ = int(current_states[pc_name].get("occupied", 0))
                new_occ = 0 if prev_occ == 1 else 1
                current_states[pc_name]["occupied"] = new_occ
                capture_current_second()
                break

    cv2.setMouseCallback(window_name, on_mouse)

    print("Groundtruth labeler started")
    print(f"Video: {video_path}")
    print(f"ROI: {roi_csv_path}")
    print(f"Groundtruth output: {gt_csv_path}")

    while True:
        frame_idx = int(round(sec_cursor * fps))
        frame_idx = max(0, min(frame_idx, max(0, total_frames - 1)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            break

        if play_mode:
            capture_current_second()
            sec_cursor += sample_sec
            max_sec = (total_frames / fps) if fps > 0 else sec_cursor
            if sec_cursor > max_sec:
                sec_cursor = max_sec
                play_mode = False

        canvas = draw_overlay(frame, rois, current_states, selected_pc_name, sec_cursor, frame_idx, total_frames, fps)
        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(20 if play_mode else 0) & 0xFF

        if key == ord("q"):
            break
        if key == ord(" "):
            play_mode = not play_mode
        elif key == ord("a"):
            play_mode = False
            sec_cursor = max(0.0, sec_cursor - 1.0)
        elif key == ord("d"):
            play_mode = False
            sec_cursor += 1.0
        elif key == ord("j"):
            play_mode = False
            sec_cursor = max(0.0, sec_cursor - 5.0)
        elif key == ord("l"):
            play_mode = False
            sec_cursor += 5.0
        elif key == ord("c"):
            capture_current_second()
        elif key in (ord("+"), ord("=")) and selected_pc_name:
            val = int(current_states[selected_pc_name].get("video_count", 0)) + 1
            current_states[selected_pc_name]["video_count"] = max(0, val)
            current_states[selected_pc_name]["occupied"] = 1
            capture_current_second()
        elif key in (ord("-"), ord("_")) and selected_pc_name:
            val = int(current_states[selected_pc_name].get("video_count", 0)) - 1
            val = max(0, val)
            current_states[selected_pc_name]["video_count"] = val
            current_states[selected_pc_name]["occupied"] = 1 if val > 0 else 0
            capture_current_second()
        elif key == ord("s"):
            rows = []
            for (sec_key, pc_name), gt in sorted(sec_states.items(), key=lambda item: (item[0][0], item[0][1])):
                rows.append(
                    {
                        "time": format_video_timestamp(sec_key),
                        "cam_name": cam_name,
                        "pc_name": pc_name,
                        "occupied_gt": int(gt.get("occupied_gt", 0)),
                        "people_count_gt": int(gt.get("people_count_gt", 0)),
                    }
                )

            cols = ["time", "cam_name", "pc_name", "occupied_gt", "people_count_gt"]
            pd.DataFrame(rows, columns=cols).to_csv(gt_csv_path, index=False)
            print(f"Saved groundtruth rows: {len(rows)} -> {gt_csv_path}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
