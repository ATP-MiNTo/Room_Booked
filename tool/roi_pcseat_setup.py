import cv2
import os
import json
import pandas as pd
import numpy as np


# -------------------------------------Hardcoded Setup-------------------------------------------
# Change this mode at the top when running this script:
# - "seat": PC seat ROI polygons (PC1, PC2, ...)
# - "monitor": monitor ROI polygons aligned to seat PC names
# - "row_zone": full row polygons (ROW1, ROW2, ...)
SETUP_MODE = "seat"

CAM_INDEXES = [0, 1, 2, 3]
CAM_NAMES = {
    0: "Front_right",
    1: "Front_left",
    2: "Back_left",
    3: "Back_right",
}
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

REQUIRED_POINTS_PER_ROI = 4
ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
SEAT_CSV_SUFFIX = "_roi.csv"
MONITOR_CSV_SUFFIX = "_monitor_roi.csv"
ROW_ZONE_CSV_SUFFIX = "_row_zone_roi.csv"

WINDOW_PREFIX = "Unified ROI Setup"
TEXT_COLOR = (255, 255, 255)
POLY_COLOR = (0, 255, 0)
CURSOR_POLY_COLOR = (0, 200, 255)
# ----------------------------------------------------------------------------------------------


def to_safe_label(value):
    cleaned = "".join((c if c.isalnum() or c in ("-", "_") else "_") for c in str(value).strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "unknown"


def normalize_quad(points):
    pts = np.array(points, dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return [tl.astype(int).tolist(), tr.astype(int).tolist(), br.astype(int).tolist(), bl.astype(int).tolist()]


def csv_suffix_for_mode(mode):
    if mode == "seat":
        return SEAT_CSV_SUFFIX
    if mode == "monitor":
        return MONITOR_CSV_SUFFIX
    if mode == "row_zone":
        return ROW_ZONE_CSV_SUFFIX
    raise ValueError(f"Unsupported setup mode: {mode}")


def get_csv_path(cam_name, mode):
    cam_label = to_safe_label(cam_name)
    return os.path.join(ROI_CONFIG_DIR, f"{cam_label}{csv_suffix_for_mode(mode)}")


def load_pc_names_from_seat_roi(cam_name):
    seat_csv_path = get_csv_path(cam_name, "seat")
    if not os.path.exists(seat_csv_path):
        return []

    try:
        df = pd.read_csv(seat_csv_path)
        names = []
        seen = set()
        for _, row in df.iterrows():
            pc_name = str(row.get("pc_name", "")).strip()
            if pc_name and pc_name not in seen:
                names.append(pc_name)
                seen.add(pc_name)
        return names
    except Exception as e:
        print(f"{cam_name}: failed to load seat ROI names from {seat_csv_path}: {e}")
        return []


def default_name_for_mode(mode, index):
    if mode in ("seat", "monitor"):
        return f"PC{index}"
    if mode == "row_zone":
        return f"ROW{index}"
    return f"ROI{index}"


def save_rois(cam_name, mode, saved_rois):
    os.makedirs(ROI_CONFIG_DIR, exist_ok=True)
    csv_path = get_csv_path(cam_name, mode)

    rows = []
    for roi in saved_rois:
        ordered = normalize_quad(roi["points"])
        rows.append(
            {
                "pc_name": roi["pc_name"],
                "points_json": json.dumps(ordered),
            }
        )

    df = pd.DataFrame(rows, columns=["pc_name", "points_json"])
    df.to_csv(csv_path, index=False)
    return csv_path


def run_roi_for_camera(cam_idx, mode):
    cam_name = CAM_NAMES.get(cam_idx, f"Cam_{cam_idx}")
    window_name = f"{WINDOW_PREFIX} ({mode}) - {cam_name}"

    target_names = []
    if mode == "monitor":
        target_names = load_pc_names_from_seat_roi(cam_name)
        if target_names:
            print(f"{cam_name}: loaded {len(target_names)} seat names for monitor alignment")
        else:
            print(f"{cam_name}: seat ROI not found, monitor mode will use sequential PC names")

    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_idx)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        print(f"{cam_name}: cannot open camera, skipping.")
        return False, False

    state = {
        "current_points": [],
        "saved_rois": [],
        "next_index": 1,
        "target_index": 0,
        "finish_cam": False,
        "quit_all": False,
    }

    def current_target_name():
        if target_names:
            if state["target_index"] < len(target_names):
                return target_names[state["target_index"]]
            return None
        return default_name_for_mode(mode, state["next_index"])

    def on_mouse(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if len(state["current_points"]) < REQUIRED_POINTS_PER_ROI:
            state["current_points"].append((x, y))

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, on_mouse)

    print(f"\n--- {cam_name} {mode} ROI setup ---")
    print("Click 4 points on frame to define polygon")
    print("Keys: < Undo | c Clear | Enter Save ROI | n Skip target | s Next Cam | q Quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        canvas = frame.copy()
        target_name = current_target_name()

        status = (
            f"Camera: {cam_name} | Mode: {mode} | Target: {target_name or 'Done'} | "
            f"Saved: {len(state['saved_rois'])} | Points: {len(state['current_points'])}/4"
        )
        cv2.putText(canvas, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_COLOR, 2)
        cv2.putText(canvas, "Keys: < Undo | c Clear | Enter Save | n Skip | s Next Cam | q Quit", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        for roi in state["saved_rois"]:
            ordered = normalize_quad(roi["points"])
            poly = np.array(ordered, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [poly], True, POLY_COLOR, 2)
            cv2.putText(canvas, roi["pc_name"], tuple(ordered[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, POLY_COLOR, 2)

        if state["current_points"]:
            pts = np.array(state["current_points"], dtype=np.int32)
            for i, p in enumerate(pts):
                cv2.circle(canvas, tuple(p), 6, CURSOR_POLY_COLOR, -1)
                cv2.putText(canvas, str(i + 1), (p[0] + 10, p[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, CURSOR_POLY_COLOR, 2)
            if len(pts) > 1:
                cv2.polylines(canvas, [pts.reshape((-1, 1, 2))], False, CURSOR_POLY_COLOR, 2)

        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("<") and state["current_points"]:
            state["current_points"].pop()
        elif key == ord("c"):
            state["current_points"] = []
        elif key == ord("n"):
            if target_names and state["target_index"] < len(target_names):
                print(f"{cam_name}: skipped {target_names[state['target_index']]}")
                state["target_index"] += 1
                state["current_points"] = []
        elif key == 13 and len(state["current_points"]) == REQUIRED_POINTS_PER_ROI:
            if target_name is not None:
                state["saved_rois"].append({"pc_name": target_name, "points": list(state["current_points"])})
                state["current_points"] = []
                if target_names:
                    state["target_index"] += 1
                else:
                    state["next_index"] += 1
        elif key == ord("s"):
            state["finish_cam"] = True
        elif key == ord("q"):
            state["quit_all"] = True
            state["finish_cam"] = True

        if state["finish_cam"]:
            break
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

    if state["saved_rois"]:
        csv_path = save_rois(cam_name, mode, state["saved_rois"])
        print(f"{cam_name}: saved {len(state['saved_rois'])} ROI(s) -> {csv_path}")
    else:
        print(f"{cam_name}: no ROI saved.")

    cap.release()
    cv2.destroyWindow(window_name)
    return True, state["quit_all"]


def main(setup_mode=None):
    mode = (setup_mode or SETUP_MODE).strip().lower()
    if mode not in {"seat", "monitor", "row_zone"}:
        raise ValueError(f"Unsupported SETUP_MODE: {mode}")

    print("=== Unified ROI Setup Tool ===")
    print(f"Active mode: {mode}")
    print("- Opens cameras one-by-one")
    print("- Saves CSVs in tool/roi_config")
    print()

    for cam_idx in CAM_INDEXES:
        opened, quit_all = run_roi_for_camera(cam_idx, mode)
        if quit_all:
            break
        if not opened:
            continue

    cv2.destroyAllWindows()
    print("ROI setup finished.")


if __name__ == "__main__":
    main()
