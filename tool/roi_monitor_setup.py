import cv2
import os
import json
import pandas as pd
import numpy as np


# -------------------------------------Configuration--------------------------------------------
# Camera settings (kept aligned with threaded.py)
CAM_INDEXES = [0, 1, 2, 3]
CAM_NAMES = {
    0: "Front_right",
    1: "Front_left",
    2: "Back_left",
    3: "Back_right",
}
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# ROI setup settings
REQUIRED_POINTS_PER_MONITOR = 4  # fixed to 4: TL, TR, BR, BL by click order
ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
SEAT_CSV_SUFFIX = "_roi.csv"
MONITOR_CSV_SUFFIX = "_monitor_roi.csv"

# UI settings
WINDOW_PREFIX = "Monitor ROI Setup"
TEXT_COLOR = (255, 255, 255)
POLY_COLOR = (255, 0, 255)
CURSOR_POLY_COLOR = (0, 200, 255)

# ----------------------------------------------------------------------------------------------


def to_safe_label(value):
    cleaned = "".join((c if c.isalnum() or c in ("-", "_") else "_") for c in str(value).strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "unknown"


def get_roi_csv_path(cam_name, suffix):
    cam_label = to_safe_label(cam_name)
    return os.path.join(ROI_CONFIG_DIR, f"{cam_label}{suffix}")


def normalize_quad(points):
    """Return points as TL, TR, BR, BL based on geometry."""
    pts = np.array(points, dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return [tl.astype(int).tolist(), tr.astype(int).tolist(), br.astype(int).tolist(), bl.astype(int).tolist()]


def load_pc_names_from_seat_roi(cam_name):
    """Load PC names from seat ROI CSV so monitor ROI names stay aligned."""
    seat_csv_path = get_roi_csv_path(cam_name, SEAT_CSV_SUFFIX)
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


def save_monitor_rois(cam_name, saved_rois):
    os.makedirs(ROI_CONFIG_DIR, exist_ok=True)
    csv_path = get_roi_csv_path(cam_name, MONITOR_CSV_SUFFIX)

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


def run_monitor_roi_for_camera(cam_idx):
    cam_name = CAM_NAMES.get(cam_idx, f"Cam_{cam_idx}")
    window_name = f"{WINDOW_PREFIX} ({cam_name})"

    target_pc_names = load_pc_names_from_seat_roi(cam_name)
    if target_pc_names:
        print(f"{cam_name}: loaded {len(target_pc_names)} seat ROI PC name(s) for monitor mapping")
    else:
        print(f"{cam_name}: seat ROI CSV not found, fallback to sequential PC names")

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
        "next_index": 0,
        "next_dynamic_pc_num": 1,
        "finish_cam": False,
        "quit_all": False,
    }

    def get_current_pc_name():
        if target_pc_names:
            if state["next_index"] < len(target_pc_names):
                return target_pc_names[state["next_index"]]
            return None
        return f"PC{state['next_dynamic_pc_num']}"

    def on_mouse(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if len(state["current_points"]) < REQUIRED_POINTS_PER_MONITOR:
            state["current_points"].append((x, y))

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, on_mouse)

    print(f"\n--- {cam_name} monitor ROI setup ---")
    print("Click 4 points on frame to define each monitor polygon")
    print("Keyboard shortcuts:")
    print("  < = Undo last point")
    print("  c = Clear draft points")
    print("  Enter = Save current monitor polygon")
    print("  n = Skip current target PC (only when seat ROI names exist)")
    print("  s = Save & go to next camera")
    print("  q = Quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        canvas = frame.copy()
        current_pc_name = get_current_pc_name()

        if target_pc_names:
            status_line2 = (
                f"Target PC: {current_pc_name or 'Done'} | "
                f"Progress: {state['next_index']}/{len(target_pc_names)} | "
                f"Points: {len(state['current_points'])}/4"
            )
        else:
            status_line2 = (
                f"Target PC: {current_pc_name} | "
                f"Saved: {len(state['saved_rois'])} | "
                f"Points: {len(state['current_points'])}/4"
            )

        cv2.putText(canvas, f"Camera: {cam_name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)
        cv2.putText(canvas, status_line2, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(
            canvas,
            "Keys: < Undo | c Clear | Enter Save | n Skip target | s Next Cam | q Quit",
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 0),
            1,
        )

        y_text = 120
        for roi in state["saved_rois"]:
            ordered = normalize_quad(roi["points"])
            poly = np.array(ordered, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [poly], True, POLY_COLOR, 2)
            cv2.putText(canvas, roi["pc_name"], tuple(ordered[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, POLY_COLOR, 2)
            cv2.putText(canvas, roi["pc_name"], (10, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 210, 255), 1)
            y_text += 22

        if state["current_points"]:
            pts = np.array(state["current_points"], dtype=np.int32)
            for i, p in enumerate(pts):
                cv2.circle(canvas, tuple(p), 6, CURSOR_POLY_COLOR, -1)
                cv2.putText(canvas, str(i + 1), (p[0] + 10, p[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, CURSOR_POLY_COLOR, 2)
            if len(pts) > 1:
                cv2.polylines(canvas, [pts.reshape((-1, 1, 2))], False, CURSOR_POLY_COLOR, 2)

        if target_pc_names and state["next_index"] >= len(target_pc_names):
            cv2.putText(canvas, "All target PCs done. Press 's' to save and continue.", (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("<") and state["current_points"]:
            state["current_points"].pop()
        elif key == ord("c"):
            state["current_points"] = []
        elif key == ord("n") and target_pc_names and state["next_index"] < len(target_pc_names):
            skipped_pc = target_pc_names[state["next_index"]]
            print(f"{cam_name}: skipped monitor ROI for {skipped_pc}")
            state["next_index"] += 1
            state["current_points"] = []
        elif key == 13 and len(state["current_points"]) == REQUIRED_POINTS_PER_MONITOR:
            pc_name = get_current_pc_name()
            if pc_name is None:
                print(f"{cam_name}: all target PCs are already completed")
            else:
                state["saved_rois"].append({"pc_name": pc_name, "points": list(state["current_points"])})
                state["current_points"] = []
                if target_pc_names:
                    state["next_index"] += 1
                else:
                    state["next_dynamic_pc_num"] += 1
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
        csv_path = save_monitor_rois(cam_name, state["saved_rois"])
        print(f"{cam_name}: saved {len(state['saved_rois'])} monitor ROI(s) -> {csv_path}")
    else:
        print(f"{cam_name}: no monitor ROI saved.")

    cap.release()
    cv2.destroyWindow(window_name)

    return True, state["quit_all"]


def main():
    print("=== Monitor ROI Setup Tool ===")
    print("- Opens cameras one-by-one")
    print("- Creates monitor ROI CSV under tool/roi_config")
    print("- If seat ROI exists, it uses the same PC names for alignment")
    print()

    for cam_idx in CAM_INDEXES:
        opened, quit_all = run_monitor_roi_for_camera(cam_idx)
        if quit_all:
            break
        if not opened:
            continue

    cv2.destroyAllWindows()
    print("Monitor ROI setup finished.")


if __name__ == "__main__":
    main()
