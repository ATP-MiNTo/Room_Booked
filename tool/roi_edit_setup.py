import json
import os

import cv2
import numpy as np
import pandas as pd


# -------------------------------------Configuration--------------------------------------------
CAM_INDEXES = [0, 1, 2, 3]
CAM_NAMES = {
    0: "Front_right",
    1: "Front_left",
    2: "Back_left",
    3: "Back_right",
}
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
SEAT_CSV_SUFFIX = "_roi.csv"
MONITOR_CSV_SUFFIX = "_monitor_roi.csv"
REQUIRED_POINTS_PER_ROI = 4

WINDOW_NAME = "ROI Edit Setup"
TEXT_COLOR = (255, 255, 255)
TITLE_COLOR = (0, 255, 255)
SEAT_COLOR = (0, 255, 0)
MONITOR_COLOR = (255, 0, 255)
SELECTED_COLOR = (0, 255, 255)
DRAFT_COLOR = (0, 200, 255)

# Hardcoded edit mode: "pcseat" or "monitor" (also accepts typo "moniter")
EDIT_MODE = "pcseat"

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
    return [
        tl.astype(int).tolist(),
        tr.astype(int).tolist(),
        br.astype(int).tolist(),
        bl.astype(int).tolist(),
    ]


def get_csv_suffix(mode):
    return MONITOR_CSV_SUFFIX if mode == "monitor" else SEAT_CSV_SUFFIX


def get_roi_csv_path(cam_name, mode):
    cam_label = to_safe_label(cam_name)
    return os.path.join(ROI_CONFIG_DIR, f"{cam_label}{get_csv_suffix(mode)}")


def load_rows_from_csv(csv_path):
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


def open_camera(cam_idx):
    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


def draw_no_camera_screen(cam_name):
    canvas = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    cv2.putText(canvas, f"Camera: {cam_name}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, TITLE_COLOR, 2)
    cv2.putText(canvas, "Camera cannot be opened.", (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, TEXT_COLOR, 2)
    return canvas


def is_prev_roi_key(key):
    return key in (ord(","), ord("<"), 2424832)


def is_next_roi_key(key):
    return key in (ord("."), ord(">"), 2555904)


def get_hardcoded_mode():
    mode = str(EDIT_MODE).strip().lower()
    if mode == "moniter":
        mode = "monitor"

    if mode not in ("pcseat", "monitor"):
        print(f"Invalid EDIT_MODE='{EDIT_MODE}', fallback to 'pcseat'")
        return "pcseat"

    return mode


def main():
    mode = get_hardcoded_mode()

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

    cap = open_camera(app_state["cam_order"][app_state["active_cam_pos"]])

    print("=== ROI Edit Setup ===")
    print(f"Mode (hardcoded): {mode}")
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
            ret, frame = cap.read()
            if not ret:
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

        if is_prev_roi_key(key):
            if rows:
                state["selected_idx"] = (state["selected_idx"] - 1) % len(rows)
                app_state["draft_points"] = []
            continue

        if is_next_roi_key(key):
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
            cap = open_camera(app_state["cam_order"][app_state["active_cam_pos"]])
            continue

        if key in (ord("m"), ord("M")):
            app_state["active_cam_pos"] = (app_state["active_cam_pos"] - 1) % len(cam_order)
            app_state["draft_points"] = []
            cap.release()
            cap = open_camera(app_state["cam_order"][app_state["active_cam_pos"]])
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


if __name__ == "__main__":
    main()
