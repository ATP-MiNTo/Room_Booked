"""
Unified ROI Configuration Tool
Supports both interactive editing and visualization of ROI configurations.
"""

import csv
import glob
import json
import os
import statistics
import time
from datetime import datetime

import cv2
import numpy as np
import pandas as pd


# ==============================================Configuration=====================================================

# ===== MODE SELECTOR (hardcoded at top) =====
# Choose "edit" for interactive ROI polygon editing, or "view" for visualization
MODE = "view"

# Source mode:
# - "camera": read from physical cameras using CAM_INDEXES
# - "video": read from video files resolved by camera name
SOURCE_MODE = "video"

# Used when SOURCE_MODE == "video"
VIDEO_INPUT_DIR = "test_vid"
VIDEO_EXTENSIONS = [".mp4", ".avi", ".mov", ".mkv", ".m4v"]
VIDEO_SOURCE_OVERRIDES = {
    # "Front_right": "test_vid/Front_right.mp4",
}
VIDEO_USE_SINGLE_FRAME = True

# ===== Camera Configuration =====
CAM_INDEXES = [0, 1, 2, 3]
CAM_NAMES = {
    0: "Front_right",
    1: "Front_left",
    2: "Back_left",
    3: "Back_right",
}

CAM_NAME_TO_INDEX = {
    "Front_right": 0,
    "Front_left": 1,
    "Back_left": 2,
    "Back_right": 3,
}

# ===== ROI and Display Settings =====
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
GROUNDTRUTH_DIR = os.path.join("tool", "groundtruth")

SEAT_CSV_SUFFIX = "_roi.csv"
MONITOR_CSV_SUFFIX = "_monitor_roi.csv"
ROW_ZONE_CSV_SUFFIX = "_row_zone_roi.csv"
GT_CSV_SUFFIX = "_gt.csv"
REQUIRED_POINTS_PER_ROI = 4

# ===== Colors =====
TEXT_COLOR = (255, 255, 255)
TITLE_COLOR = (0, 255, 255)
SEAT_COLOR = (0, 255, 0)
MONITOR_COLOR = (255, 0, 255)
SELECTED_COLOR = (0, 255, 255)
DRAFT_COLOR = (0, 200, 255)
SEAT_POLY_COLOR = (0, 255, 0)
MONITOR_POLY_COLOR = (255, 0, 255)
SEAT_LABEL_SEAT_COLOR = (255, 255, 0)   # cyan
SEAT_LABEL_PC_COLOR = (0, 255, 0)       # green
SEAT_LABEL_ZONE_COLOR = (0, 0, 255)     # red
SEAT_LABEL_GT_COLOR = (0, 0, 255)       # red

WINDOW_NAME = "ROI Configuration Tool"

# ===== Edit Mode Settings =====
EDIT_MODE = "pcseat"  # Default for edit mode: "pcseat" or "monitor" (also accepts typo "moniter")

# =====================================================================================================================


def to_safe_label(value):
    """Convert value to safe label for file naming."""
    cleaned = "".join((c if c.isalnum() or c in ("-", "_") else "_") for c in str(value).strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "unknown"


def normalize_quad(points):
    """Normalize 4-point quad to consistent order: TL, TR, BR, BL."""
    pts = np.array(points, dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return [
        tl.astype(int).tolist(),
        tr.astype(int).tolist(),
        br.astype(int).tolist(),
        bl.astype(int).tolist(),
    ]


def get_csv_suffix(mode):
    """Get CSV suffix for given mode."""
    return MONITOR_CSV_SUFFIX if mode == "monitor" else SEAT_CSV_SUFFIX


def get_roi_csv_path(cam_name, mode):
    """Get ROI CSV path for given camera and mode."""
    cam_label = to_safe_label(cam_name)
    return os.path.join(ROI_CONFIG_DIR, f"{cam_label}{get_csv_suffix(mode)}")


def resolve_video_path(cam_name):
    """Resolve video path for a camera label in video source mode."""
    override_path = VIDEO_SOURCE_OVERRIDES.get(cam_name)
    if override_path and os.path.exists(override_path):
        return override_path

    safe_name = to_safe_label(cam_name)
    candidates = [
        cam_name,
        safe_name,
        cam_name.lower(),
        safe_name.lower(),
    ]

    for name in candidates:
        for ext in VIDEO_EXTENSIONS:
            path = os.path.join(VIDEO_INPUT_DIR, f"{name}{ext}")
            if os.path.exists(path):
                return path

    return None


def load_rows_from_csv(csv_path):
    """Load ROI rows from CSV file."""
    rows = []
    if not os.path.exists(csv_path):
        return rows

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return rows

    for i, row in df.iterrows():
        pc_name = str(row.get("pc_name", "")).strip() or f"PC{i + 1}"

        parsed_points = []
        raw_points_json = row.get("points_json", "[]")
        try:
            points = json.loads(raw_points_json) if pd.notna(raw_points_json) else []
            if isinstance(points, list):
                for point in points:
                    if isinstance(point, (list, tuple)) and len(point) >= 2:
                        try:
                            parsed_points.append([int(point[0]), int(point[1])])
                        except Exception:
                            pass
        except Exception:
            parsed_points = []

        if len(parsed_points) >= 3:
            parsed_points = normalize_quad(parsed_points)
        else:
            parsed_points = []

        rows.append({"pc_name": pc_name, "points": parsed_points})

    return rows


def load_seat_pc_names(cam_name):
    """Load PC names from seat ROI CSV."""
    seat_path = get_roi_csv_path(cam_name, "pcseat")
    seat_rows = load_rows_from_csv(seat_path)
    names = []
    seen = set()

    for row in seat_rows:
        pc_name = row.get("pc_name", "").strip()
        if pc_name and pc_name not in seen:
            names.append(pc_name)
            seen.add(pc_name)

    return names


def build_camera_rows(cam_name, mode):
    """Build ROI rows for given camera and mode."""
    csv_path = get_roi_csv_path(cam_name, mode)
    rows = load_rows_from_csv(csv_path)

    if mode == "monitor":
        seat_names = load_seat_pc_names(cam_name)
        if seat_names:
            row_map = {}
            for row in rows:
                row_map[row["pc_name"]] = row

            aligned = []
            for pc_name in seat_names:
                aligned.append({
                    "pc_name": pc_name,
                    "points": row_map.get(pc_name, {"points": []}).get("points", []),
                })

            extras = [row for row in rows if row["pc_name"] not in set(seat_names)]
            rows = aligned + extras

    if not rows:
        rows = [{"pc_name": "PC1", "points": []}]

    return rows


def save_camera_rows(cam_name, mode, rows):
    """Save ROI rows to CSV file."""
    os.makedirs(ROI_CONFIG_DIR, exist_ok=True)
    csv_path = get_roi_csv_path(cam_name, mode)

    output_rows = []
    for row in rows:
        pc_name = str(row.get("pc_name", "")).strip()
        if not pc_name:
            continue

        points = row.get("points", []) or []
        if len(points) >= 3:
            points = normalize_quad(points)
        else:
            points = []

        output_rows.append(
            {
                "pc_name": pc_name,
                "points_json": json.dumps(points),
            }
        )

    pd.DataFrame(output_rows, columns=["pc_name", "points_json"]).to_csv(csv_path, index=False)
    return csv_path


def open_input_source(cam_idx_or_name, source_mode):
    """Open input source as camera or video and return (capture, source_label)."""
    mode = str(source_mode).strip().lower()
    cam_name = None
    cam_idx = 0

    if isinstance(cam_idx_or_name, str):
        cam_name = cam_idx_or_name
        cam_idx = CAM_NAME_TO_INDEX.get(cam_idx_or_name, 0)
    else:
        cam_idx = cam_idx_or_name
        cam_name = CAM_NAMES.get(cam_idx, f"Cam_{cam_idx}")

    if mode == "video":
        video_path = resolve_video_path(cam_name)
        if not video_path:
            return None, None
        cap = cv2.VideoCapture(video_path)
        return cap, video_path

    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap, f"camera:{cam_idx}"


def draw_no_camera_screen(cam_name):
    """Draw placeholder screen when input source is not available."""
    canvas = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    cv2.putText(canvas, f"Source: {cam_name}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, TITLE_COLOR, 2)
    cv2.putText(canvas, "Input source cannot be opened.", (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, TEXT_COLOR, 2)
    return canvas


def is_prev_key(key):
    """Check if key is 'previous' navigation key."""
    return key in (ord(","), ord("<"), 2424832)


def is_next_key(key):
    """Check if key is 'next' navigation key."""
    return key in (ord("."), ord(">"), 2555904)


# ===== Groundtruth / View Mode Functions =====

def parse_time_to_seconds(time_text):
    """Parse time string to seconds since epoch."""
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
    """Infer sampling interval from time points."""
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
    """Load groundtruth summary from CSV."""
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

            if int(points[-1][1]) > 0:
                occupied_time += float(sample_sec)

        by_pc[pc_name]["occupied_time_sec"] = occupied_time

    return {
        "sample_sec": sample_sec,
        "by_pc": by_pc,
    }


def discover_groundtruth_summaries():
    """Discover all groundtruth CSV files and load summaries."""
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


def parse_cam_name_and_type(csv_path):
    """Parse camera name and ROI type from CSV path."""
    name = os.path.basename(csv_path)
    if name.endswith(ROW_ZONE_CSV_SUFFIX):
        return name[: -len(ROW_ZONE_CSV_SUFFIX)], "row_zone"
    if name.endswith(MONITOR_CSV_SUFFIX):
        return name[: -len(MONITOR_CSV_SUFFIX)], "monitor"
    if name.endswith(SEAT_CSV_SUFFIX):
        return name[: -len(SEAT_CSV_SUFFIX)], "seat"
    return os.path.splitext(name)[0], "unknown"


def infer_row_label_for_pc(pc_name, seat_index):
    """Map each 3 pc seats into one row label (ROW1, ROW2, ...)."""
    digits = "".join(ch for ch in str(pc_name) if ch.isdigit())
    if digits:
        pc_num = int(digits)
        if pc_num > 0:
            return f"ROW{((pc_num - 1) // 3) + 1}"
    return f"ROW{(seat_index // 3) + 1}"


def build_pc_to_row_map(seat_rois):
    mapping = {}
    for i, roi in enumerate(seat_rois):
        pc_name = roi.get("pc_name", "").strip()
        if not pc_name:
            continue
        mapping[pc_name] = infer_row_label_for_pc(pc_name, i)
    return mapping


def zone_label_from_row(row_label):
    text = str(row_label or "").strip().upper()
    if text.startswith("ROW"):
        suffix = text[3:]
        if suffix.isdigit():
            return f"Zone{int(suffix)}"
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return f"Zone{int(digits)}"
    return "Zone?"


def format_seat_display(seat_index, pc_name, row_label, gt_seconds):
    zone_label = zone_label_from_row(row_label)
    gt_text = "---" if gt_seconds is None else f"{float(gt_seconds):.0f}"
    return f"Seat{seat_index} | {pc_name} | {zone_label} (gt={gt_text}s)"


def seat_display_segments(seat_index, pc_name, row_label, gt_seconds):
    zone_label = zone_label_from_row(row_label)
    gt_text = "---" if gt_seconds is None else f"{float(gt_seconds):.0f}"
    return [
        (f"Seat{seat_index}", SEAT_LABEL_SEAT_COLOR),
        (" | ", TEXT_COLOR),
        (str(pc_name), SEAT_LABEL_PC_COLOR),
        (" | ", TEXT_COLOR),
        (zone_label, SEAT_LABEL_ZONE_COLOR),
        (f" (gt={gt_text}s)", SEAT_LABEL_GT_COLOR),
    ]


def draw_text_segments(canvas, origin, segments, font, scale, thickness):
    x, y = int(origin[0]), int(origin[1])
    for text, color in segments:
        if not text:
            continue
        cv2.putText(canvas, text, (x, y), font, scale, color, thickness)
        (w, _), _ = cv2.getTextSize(text, font, scale, thickness)
        x += w


def load_roi_csv(csv_path):
    """Load ROI data from CSV file."""
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
    """Discover all ROI setups from CSV files."""
    seat_files = sorted(glob.glob(os.path.join(ROI_CONFIG_DIR, f"*{SEAT_CSV_SUFFIX}")))
    monitor_files = sorted(glob.glob(os.path.join(ROI_CONFIG_DIR, f"*{MONITOR_CSV_SUFFIX}")))
    row_zone_files = sorted(glob.glob(os.path.join(ROI_CONFIG_DIR, f"*{ROW_ZONE_CSV_SUFFIX}")))

    # *_monitor_roi.csv and *_row_zone_roi.csv also match *_roi.csv glob,
    # so keep only true seat files here.
    seat_files = [
        path for path in seat_files
        if (not path.endswith(MONITOR_CSV_SUFFIX) and not path.endswith(ROW_ZONE_CSV_SUFFIX))
    ]

    setups = {}

    for csv_path in seat_files:
        cam_name, _ = parse_cam_name_and_type(csv_path)
        rois = load_roi_csv(csv_path)
        if cam_name not in setups:
            setups[cam_name] = {
                "cam_name": cam_name,
                "seat_rois": [],
                "monitor_rois": [],
                "row_zone_rois": [],
                "seat_csv": None,
                "monitor_csv": None,
                "row_zone_csv": None,
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
                "row_zone_rois": [],
                "seat_csv": None,
                "monitor_csv": None,
                "row_zone_csv": None,
            }
        setups[cam_name]["monitor_rois"] = rois
        setups[cam_name]["monitor_csv"] = csv_path

    for csv_path in row_zone_files:
        cam_name, _ = parse_cam_name_and_type(csv_path)
        rois = load_roi_csv(csv_path)
        if cam_name not in setups:
            setups[cam_name] = {
                "cam_name": cam_name,
                "seat_rois": [],
                "monitor_rois": [],
                "row_zone_rois": [],
                "seat_csv": None,
                "monitor_csv": None,
                "row_zone_csv": None,
            }
        setups[cam_name]["row_zone_rois"] = rois
        setups[cam_name]["row_zone_csv"] = csv_path

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


def draw_overlay(frame, setup, cam_idx, total):
    """Draw ROI and GT overlay on frame."""
    canvas = frame.copy()
    cam_name = setup["cam_name"]
    seat_rois = setup.get("seat_rois", [])
    monitor_rois = setup.get("monitor_rois", [])
    row_zone_rois = setup.get("row_zone_rois", [])
    gt_summary = setup.get("gt_summary")
    gt_by_pc = gt_summary.get("by_pc", {}) if gt_summary else {}
    pc_to_row = build_pc_to_row_map(seat_rois)

    cam_index = CAM_NAME_TO_INDEX.get(cam_name, "?")
    header = (
        f"Camera {cam_idx + 1}/{total}: {cam_name} (index {cam_index}) | "
        f"Seat ROI: {len(seat_rois)} | Monitor ROI: {len(monitor_rois)} | Row Zone: {len(row_zone_rois)}"
    )
    cv2.putText(canvas, header, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TITLE_COLOR, 2)

    help_text = "Keys: < Prev | > Next | q Quit"
    cv2.putText(canvas, help_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_COLOR, 2)

    if gt_summary:
        gt_header = f"GT loaded | sample={gt_summary.get('sample_sec', 1.0):.1f}s"
    else:
        gt_header = "GT not found"
    cv2.putText(canvas, gt_header, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_COLOR, 2)

    y = 112
    if seat_rois:
        cv2.putText(canvas, "Seat ROI (green)", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, SEAT_POLY_COLOR, 2)
        y += 24
        for seat_index, roi in enumerate(seat_rois, start=1):
            ordered = normalize_quad(roi["points"])
            poly = np.array(ordered, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [poly], True, SEAT_POLY_COLOR, 2)

            label_anchor = tuple(ordered[0])
            row_label = pc_to_row.get(roi["pc_name"], "ROW?")
            gt_seconds = None
            if roi["pc_name"] in gt_by_pc:
                gt_seconds = float(gt_by_pc[roi["pc_name"]].get("occupied_time_sec", 0.0))

            seat_only_text = f"Seat{seat_index}"
            cv2.putText(canvas, seat_only_text, label_anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.6, SEAT_POLY_COLOR, 2)

            segments = seat_display_segments(seat_index, roi["pc_name"], row_label, gt_seconds)
            draw_text_segments(canvas, (10, y), segments, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            y += 20

    if monitor_rois:
        y += 24
        for roi in monitor_rois:
            ordered = normalize_quad(roi["points"])
            poly = np.array(ordered, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [poly], True, MONITOR_POLY_COLOR, 2)

            label_anchor = tuple(ordered[0])
            label_text = f"Monitor | {roi['pc_name']}"
            cv2.putText(canvas, label_text, label_anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.6, MONITOR_POLY_COLOR, 2)
            y += 20

    if row_zone_rois:
        zone_color = (255, 255, 0)
        y += 24
        for roi in row_zone_rois:
            ordered = normalize_quad(roi["points"])
            poly = np.array(ordered, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [poly], True, zone_color, 2)

            label_anchor = tuple(ordered[0])
            label_text = f"Zone | {roi['pc_name']}"
            cv2.putText(canvas, label_text, label_anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.6, zone_color, 2)
            y += 20

    if not seat_rois and not monitor_rois and not row_zone_rois:
        cv2.putText(canvas, "No ROI found for this camera.", (10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)

    return canvas


# ===== Main Functions (Mode-Specific) =====

def main_edit(source_mode):
    """Interactive ROI polygon editing mode."""
    mode = EDIT_MODE.strip().lower()
    if mode == "moniter":
        mode = "monitor"
    if mode not in ("pcseat", "monitor"):
        print(f"Invalid EDIT_MODE='{EDIT_MODE}', fallback to 'pcseat'")
        mode = "pcseat"

    cam_order = list(CAM_INDEXES)
    cam_states = {}
    for cam_idx in cam_order:
        cam_name = CAM_NAMES.get(cam_idx, f"Cam_{cam_idx}")
        rows = build_camera_rows(cam_name, mode)
        cam_states[cam_idx] = {
            "cam_idx": cam_idx,
            "cam_name": cam_name,
            "rows": rows,
            "selected_idx": 0,
            "dirty": False,
        }

    app_state = {
        "mode": mode,
        "cam_order": cam_order,
        "cam_states": cam_states,
        "active_cam_pos": 0,
        "draft_points": [],
    }

    def current_cam_state():
        cam_idx = app_state["cam_order"][app_state["active_cam_pos"]]
        return app_state["cam_states"][cam_idx]

    def on_mouse(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        state = current_cam_state()
        rows = state["rows"]
        if not rows:
            return

        draft = app_state["draft_points"]
        if len(draft) < REQUIRED_POINTS_PER_ROI:
            draft.append([x, y])

        if len(draft) == REQUIRED_POINTS_PER_ROI:
            selected_idx = state["selected_idx"]
            rows[selected_idx]["points"] = normalize_quad(draft)
            state["dirty"] = True
            app_state["draft_points"] = []
            print(f"{state['cam_name']}: updated {rows[selected_idx]['pc_name']}")

    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    cap, source_label = open_input_source(app_state["cam_order"][app_state["active_cam_pos"]], source_mode)
    if cap is None:
        print("Unable to open first input source.")
        return

    frozen_frame = None
    if source_mode == "video" and VIDEO_USE_SINGLE_FRAME:
        ret, first_frame = cap.read()
        if not ret:
            print("Unable to read first frame from first video source.")
            cap.release()
            return
        frozen_frame = first_frame

    print("=== ROI Edit Mode ===")
    print(f"Mode (hardcoded): {mode}")
    print(f"Source mode: {source_mode}")
    if source_label:
        print(f"Source: {source_label}")
    print("Controls:")
    print("  <, > : rotate between existing ROI rows")
    print("  c    : clear current ROI points")
    print("  n, m : rotate camera (next, prev)")
    print("  s    : save current camera ROI CSV")
    print("  q    : exit")
    print("  Mouse left click: place 4 points to replace current ROI")

    while True:
        state = current_cam_state()
        cam_name = state["cam_name"]
        rows = state["rows"]

        if cap.isOpened():
            if source_mode == "video" and VIDEO_USE_SINGLE_FRAME and frozen_frame is not None:
                frame = frozen_frame.copy()
            else:
                ret, frame = cap.read()
                if not ret:
                    if source_mode == "video":
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if not ret:
                            frame = draw_no_camera_screen(cam_name)
                    else:
                        frame = draw_no_camera_screen(cam_name)
        else:
            frame = draw_no_camera_screen(cam_name)

        canvas = frame.copy()

        base_poly_color = MONITOR_COLOR if mode == "monitor" else SEAT_COLOR
        selected_idx = state["selected_idx"]

        for i, row in enumerate(rows):
            points = row.get("points", [])
            if len(points) < 3:
                continue

            poly = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
            color = SELECTED_COLOR if i == selected_idx else base_poly_color
            thickness = 3 if i == selected_idx else 2
            cv2.polylines(canvas, [poly], True, color, thickness)
            cv2.putText(canvas, row["pc_name"], tuple(points[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        draft_points = app_state["draft_points"]
        if draft_points:
            pts = np.array(draft_points, dtype=np.int32)
            for i, point in enumerate(pts):
                cv2.circle(canvas, tuple(point), 6, DRAFT_COLOR, -1)
                cv2.putText(canvas, str(i + 1), (point[0] + 10, point[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, DRAFT_COLOR, 2)
            if len(pts) > 1:
                cv2.polylines(canvas, [pts.reshape((-1, 1, 2))], False, DRAFT_COLOR, 2)

        selected_row = rows[selected_idx]
        selected_name = selected_row["pc_name"]
        selected_has_points = len(selected_row.get("points", [])) >= 3

        status_top = (
            f"Mode: {mode} | Cam: {cam_name} ({app_state['active_cam_pos'] + 1}/{len(cam_order)}) "
            f"| ROI: {selected_idx + 1}/{len(rows)} [{selected_name}] "
            f"| Dirty: {'YES' if state['dirty'] else 'NO'}"
        )
        cv2.putText(canvas, status_top, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, TITLE_COLOR, 2)

        status_mid = "Keys: < > rotate ROI | c clear | n next cam | m prev cam | s save | q exit"
        cv2.putText(canvas, status_mid, (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_COLOR, 2)

        if selected_has_points:
            status_bottom = f"Selected {selected_name}: ACTIVE | Click 4 points to replace"
            color = (0, 255, 0)
        else:
            status_bottom = f"Selected {selected_name}: EMPTY | Click 4 points to set"
            color = (0, 165, 255)
        cv2.putText(canvas, status_bottom, (10, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow(WINDOW_NAME, canvas)
        key = cv2.waitKeyEx(1)

        if key in (ord("q"), ord("Q"), 27):
            unsaved = [s["cam_name"] for s in app_state["cam_states"].values() if s.get("dirty")]
            if unsaved:
                print(f"Unsaved cameras: {', '.join(unsaved)}")
            break

        if is_prev_key(key):
            if rows:
                state["selected_idx"] = (state["selected_idx"] - 1) % len(rows)
                app_state["draft_points"] = []
            continue

        if is_next_key(key):
            if rows:
                state["selected_idx"] = (state["selected_idx"] + 1) % len(rows)
                app_state["draft_points"] = []
            continue

        if key in (ord("c"), ord("C")):
            if rows:
                rows[state["selected_idx"]]["points"] = []
                state["dirty"] = True
                app_state["draft_points"] = []
                print(f"{cam_name}: cleared {rows[state['selected_idx']]['pc_name']}")
            continue

        if key in (ord("n"), ord("N")):
            app_state["active_cam_pos"] = (app_state["active_cam_pos"] + 1) % len(cam_order)
            app_state["draft_points"] = []
            cap.release()
            cap, _ = open_input_source(app_state["cam_order"][app_state["active_cam_pos"]], source_mode)
            if cap is None:
                print("Unable to open selected input source.")
                break
            if source_mode == "video" and VIDEO_USE_SINGLE_FRAME:
                ret, first_frame = cap.read()
                if not ret:
                    print("Unable to read first frame from selected video source.")
                    break
                frozen_frame = first_frame
            else:
                frozen_frame = None
            continue

        if key in (ord("m"), ord("M")):
            app_state["active_cam_pos"] = (app_state["active_cam_pos"] - 1) % len(cam_order)
            app_state["draft_points"] = []
            cap.release()
            cap, _ = open_input_source(app_state["cam_order"][app_state["active_cam_pos"]], source_mode)
            if cap is None:
                print("Unable to open selected input source.")
                break
            if source_mode == "video" and VIDEO_USE_SINGLE_FRAME:
                ret, first_frame = cap.read()
                if not ret:
                    print("Unable to read first frame from selected video source.")
                    break
                frozen_frame = first_frame
            else:
                frozen_frame = None
            continue

        if key in (ord("s"), ord("S")):
            save_path = save_camera_rows(cam_name, mode, rows)
            state["dirty"] = False
            print(f"Saved {cam_name} ({mode}) -> {save_path}")
            continue

        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    cv2.destroyAllWindows()


def main_view(source_mode):
    """ROI visualization mode with groundtruth overlay."""
    setups = discover_roi_setups()
    if not setups:
        print(f"No ROI CSV found in: {ROI_CONFIG_DIR}")
        return

    print("Loaded ROI setups:")
    for i, setup in enumerate(setups, start=1):
        seat_count = len(setup.get("seat_rois", []))
        gt_summary = setup.get("gt_summary")
        gt_info = "gt=none"
        if gt_summary:
            gt_info = f"gt=loaded sample={gt_summary.get('sample_sec', 1.0):.1f}s"
        print(
            f"  {i}. {setup['cam_name']} | seat={seat_count} "
            f"| seat_csv={setup.get('seat_csv')} | {gt_info}"
        )
        if gt_summary:
            gt_by_pc = gt_summary.get("by_pc", {})
            for pc_name in sorted(gt_by_pc.keys()):
                sec = float(gt_by_pc[pc_name].get("occupied_time_sec", 0.0))
                print(f"      - {pc_name}: GT occupied {sec:.0f}s")

    active_idx = 0
    cap, source_label = open_input_source(setups[active_idx]["cam_name"], source_mode)
    if cap is None:
        print("Unable to open first input source.")
        return

    frozen_frame = None
    if source_mode == "video" and VIDEO_USE_SINGLE_FRAME:
        ret, first_frame = cap.read()
        if not ret:
            print("Unable to read first frame from first video source.")
            cap.release()
            return
        frozen_frame = first_frame
    cv2.namedWindow(WINDOW_NAME)
    print(f"Source mode: {source_mode}")
    if source_label:
        print(f"Source: {source_label}")

    while True:
        setup = setups[active_idx]

        if cap.isOpened():
            if source_mode == "video" and VIDEO_USE_SINGLE_FRAME and frozen_frame is not None:
                frame = frozen_frame.copy()
            else:
                ret, frame = cap.read()
                if not ret:
                    if source_mode == "video":
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if not ret:
                            frame = draw_no_camera_screen(setup["cam_name"])
                    else:
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
            cap, _ = open_input_source(setups[active_idx]["cam_name"], source_mode)
            if cap is None:
                print("Unable to open selected input source.")
                break
            if source_mode == "video" and VIDEO_USE_SINGLE_FRAME:
                ret, first_frame = cap.read()
                if not ret:
                    print("Unable to read first frame from selected video source.")
                    break
                frozen_frame = first_frame
            else:
                frozen_frame = None
            continue

        if is_next_key(key):
            active_idx = (active_idx + 1) % len(setups)
            cap.release()
            cap, _ = open_input_source(setups[active_idx]["cam_name"], source_mode)
            if cap is None:
                print("Unable to open selected input source.")
                break
            if source_mode == "video" and VIDEO_USE_SINGLE_FRAME:
                ret, first_frame = cap.read()
                if not ret:
                    print("Unable to read first frame from selected video source.")
                    break
                frozen_frame = first_frame
            else:
                frozen_frame = None
            continue

        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    cv2.destroyAllWindows()


def main():
    """Main entry point with mode selector."""
    mode = str(MODE).strip().lower()
    source_mode = str(SOURCE_MODE).strip().lower()
    if source_mode not in ("camera", "video"):
        print(f"Invalid SOURCE_MODE='{SOURCE_MODE}'. Set to 'camera' or 'video'.")
        return
    
    print(f"ROI Configuration Tool - Mode: {mode.upper()}")
    print(f"Input source mode: {source_mode.upper()}")
    
    if mode == "edit":
        main_edit(source_mode)
    elif mode == "view":
        main_view(source_mode)
    else:
        print(f"Invalid MODE='{MODE}'. Set to 'edit' or 'view'.")


if __name__ == "__main__":
    main()
