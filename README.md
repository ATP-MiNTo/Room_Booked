Room_Booked — YOLOv8 Room/PC Usage Tracking
===========================================

YOLOv8-based people detection with PC/seat usage logic for both live cameras and offline videos.

## Current Status

- Active live pipeline: `threaded.py`
- Active offline pipeline: `tool/threaded_video_mode.py`
- Active API service (log/data export): `api.py`
- Main config source: `tool/threaded_config.yaml`
- Legacy reference scripts are kept under `Bin/*.notuse`

---

## What Is Implemented

- Multi-source person detection (default up to 4 sources)
- Runtime currently uses local person IDs for tracking/ROI snapshots
- API supports strict external 10-digit user ID issuing (preferred or pool)
- Seat ROI overlap tracking and dwell-based usage classification
- Monitor ROI ON/OFF heuristic with stabilization frames
- PC activity event logs (`USING_PC` / `NON_PC_ACTIVITY`)
- Unattended/person-flag logic (`reason=1` / `reason=2`)
- Realtime all-PC compact state CSV (`pc_name,pc_on,availble`)
- Offline eval mode with per-seat accuracy and count-error reporting
- Groundtruth CSV workflow under `tool/groundtruth/`
- Groundtruth labeling helper for manual seat labeling from video
- REST API endpoints for booking website integration (local network)
- WebSocket stream for realtime all-PC status push
- Smoothed people counter (mode over time window)
- Smoothed PC availability state (same mode-window idea)
- Detection schedule gating (live mode)
- Session performance summary logging
- Simplified eval summary schema with occupied/count accuracy percent
- Unified ROI setup/view-edit tooling (`tool/roi_setup.py`, `tool/roi_conf.py`)

---

## Project Layout (Relevant Files)

```text
Room_Booked/
├── api.py
├── threaded.py
├── yolov8n.pt
├── README.md
├── logs/
├── logs_video_mode/
├── test_vid/
└── tool/
    ├── threaded_video_mode.py
    ├── threaded_config.yaml
    ├── requirements.txt
    ├── install_deps.py
    ├── roi_setup.py
    ├── roi_conf.py
    └── roi_config/
```

---

## Setup (Windows PowerShell)

### 1) Create and activate venv

```powershell
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r tool\requirements.txt
```

`tool/requirements.txt` includes `PyYAML` (required for config loading).

For API service:

```powershell
pip install fastapi uvicorn
```

Optional helper installer:

```powershell
python tool\install_deps.py
```

### 3) Configure ROIs

```powershell
python tool\roi_setup.py
python tool\roi_conf.py
```

Notes:

- In `tool/roi_setup.py`, set `SETUP_MODE` to one of: `seat`, `monitor`, `gate`.
- In `tool/roi_conf.py`, set `MODE` to `edit` or `view`.

### 4) Label groundtruth for eval

```powershell
python tool\groundtruth_labeler.py
```

If you omit `--video`, a file picker opens. The helper saves per-camera groundtruth CSV files under `tool\groundtruth\` using the camera label, for example `Front_left_gt.csv`.

### 5) Optional ngrok mode for `api.py`

Open `api.py` and change the hardcoded block near the top:

- `USE_NGROK = True`
- Set `NGROK_AUTHTOKEN` if your ngrok account requires one

When enabled, the same FastAPI app is exposed through one ngrok HTTP tunnel, which also supports WebSocket clients via the matching `wss://` URL.

---

## Configuration

All runtime settings are managed in:

- `tool/threaded_config.yaml`

Main groups inside config:

- Source/camera mapping
- Frame/display settings
- Detection thresholds
- Live schedule hours
- PC/monitor ROI thresholds
- Smoothing and performance controls
- Output/log paths
- Video mode options

Important smoothing key:

- `SMOOTH_WINDOW_SEC` (default `5.0`)

---

## Run Live Camera Mode

```powershell
python threaded.py
```

Notes:

- Uses local-time schedule (`DETECTION_START_HOUR_24` → `DETECTION_END_HOUR_24`)
- Stop with `q` (window) or `Ctrl+C` (terminal)
- Outputs go under `LOG_BASE_DIR` (default `logs`)

---

## Run Offline Video Mode

```powershell
python tool\threaded_video_mode.py
```

Notes:

- Reads files from `VIDEO_INPUT_DIR` (default `test_vid`)
- Discovers videos by `VIDEO_GLOB_PATTERNS`
- Uses video-time timestamps for event/state logs
- Uses video filename stem for source label + per-source log naming
- Outputs go under `VIDEO_LOG_BASE_DIR` (default `logs_video_mode`)
- Default run mode is unchanged if `--eval` is not passed
- **Session banner** displays: model in use, eval mode config (if enabled), video sources, and quit instruction
- To change model for testing: update `MODEL_PATH` in `tool/threaded_config.yaml` and restart the script

For ROI reuse, keep video filenames aligned with ROI camera labels (example: `Front_right.mp4`, `Back_left.mp4`).

### Eval Mode

```powershell
python tool\threaded_video_mode.py --eval
```

Eval mode runs inference on videos and loads groundtruth from `tool\groundtruth\{CameraLabel}_gt.csv` for comparison. Writes:

- per-camera detailed eval logs with predictions vs. groundtruth
- per-camera user-seat session intervals
- per-camera detection snapshots (timestamp, occupancy, people count)
- eval summary CSV with metrics:
    - `pc_name`, `cam_name`, `model_name`
    - `samples`, `tp`, `tn`, `fp`, `fn`
    - `accuracy`, `precision`, `recall`, `f1`
    - `mae_people_count`, `match_rate_people_count_exact`
    - `occupied_time_pred_sec`, `occupied_time_gt_sec`, `occupied_time_abs_error_sec`

Optional eval arguments:

- `--eval-tag <name>` to tag output files (default: `eval_YYYYMMDD_HHMMSS`)
- `--eval-sample-sec <seconds>` to change the sampling interval (default: `1.0`)
- `--groundtruth-dir <path>` to point to another groundtruth folder
- `--eval-log-dir <path>` to change the eval output root
- `--video-input-dir <path>` to override the video folder for one run
- `--eval-only` to re-evaluate existing eval outputs without re-running inference (for duration-based analysis)

**Testing different models**: change `MODEL_PATH` in `tool/threaded_config.yaml`, use `--eval-tag` to distinguish eval runs.

---

## Run API Service (Local Network)

Start API server on port `8000`:

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

Alternative:

```powershell
python api.py
```

Open API docs:

- `http://<SERVER_IP>:8000/docs`

---

## API Endpoints (api.py)

- `GET /api/pc-status`
    - Current all-PC compact state from `logs/pc_state_all.csv`.
- `POST /api/user-ids/issue`
    - Issues one 10-digit user ID.
    - If `preferred_user_id` is provided, it must be exactly 10 digits and is returned with strategy `preferred`.
    - If no preferred ID is provided, the API pops from preloaded pool with strategy `pool`.
    - Returns HTTP `409` when pool is empty and no preferred ID is provided.
- `POST /api/user-ids/pool`
    - Preloads or updates the available 10-digit ID pool.
    - `replace=true` overwrites pool; `replace=false` appends unique valid IDs.
    - Invalid IDs (not exactly 10 digits) are rejected with HTTP `400`.
- `WS /ws/pc-updates`
    - Realtime push stream of all-PC status.
    - **Behavior**: sends full status immediately on client connect, then sends updates only when status changes (delta approach).
    - **Connection logging**: console prints `[WS] Client connected: (IP, PORT)` and `[WS] Client disconnected: (IP, PORT)`.
    - Polling interval: 1 second (checks for changes; only sends when detected).

ID policy note:

- No automatic fallback ID generation is used.
- IDs are expected to be supplied by external systems (direct preferred ID or preloaded pool).
- Issued IDs are persisted to `logs/user_id_state.json` (`pool` and `issued`).

WebSocket notes:

- Normal `GET` API: website requests data each time (polling).
- WebSocket API: website keeps one open connection and receives initial state immediately on connect, then receives updates only when status changes.
- **Initial sync + delta updates**: clients always get baseline on connect (no waiting for first change), then only network traffic for actual changes (bandwidth efficient).
- Logs connection events to console for debugging.

---

## Output Files

Per-source logs (live and video mode follow same structure under different root dirs):

- `{LOG_ROOT}/{SourceName}/people_with_conf_and_roi_{SourceName}_YYYYMMDD.csv`
- `{LOG_ROOT}/{SourceName}/pc_activity_events_{SourceName}_YYYYMMDD.csv`
- `{LOG_ROOT}/pc_unattended_flags_YYYYMMDD.csv`
- `{LOG_ROOT}/pc_state_all.csv` (realtime overwrite)
- `{LOG_ROOT}/roi_images/{SourceName}/{PersonID}/...`
- `{LOG_ROOT}/performance_summary.csv`

Eval outputs:

- `tool/groundtruth/{CameraLabel}_gt.csv`
- `{EVAL_LOG_ROOT}/{CameraLabel}/eval_detail_{CameraLabel}_{EvalTag}.csv`
- `{EVAL_LOG_ROOT}/{CameraLabel}/eval_sessions_{CameraLabel}_{EvalTag}.csv`
- `{EVAL_LOG_ROOT}/eval_summary_{EvalTag}.csv`

Realtime compact state schema:

- `pc_name`, `pc_on`, `availble`

`availble` mapping:

- `0` = Available
- `1` = Not available (`person + pc_off`)
- `2` = Not available (`person + pc_on` / transitional state before unattended timeout)

> Note: column name is currently `availble` (kept for compatibility with existing consumers).

---

## ROI Config Reference

Directory:

- `tool/roi_config/`

Naming:

- Seat ROI: `{CameraOrSourceLabel}_roi.csv`
- Monitor ROI: `{CameraOrSourceLabel}_monitor_roi.csv`
- Gate ROI: `{CameraOrSourceLabel}_gate_roi.csv`

CSV format:

```csv
pc_name,points_json
PC1,"[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"
PC2,"[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"
```

Use matching `pc_name` values between seat and monitor ROI files.

Groundtruth files use the same camera label naming convention and should include these columns:

- `time`
- `cam_name`
- `pc_name`
- `occupied_gt`
- `people_count_gt`

`user_ids_gt` is not used by the current eval flow.

---

## Quick Notes

- For active work, use `threaded.py` and `tool/threaded_video_mode.py`.
- Keep source labels and ROI filenames aligned.
- Adjust behavior primarily through `tool/threaded_config.yaml`.
- Use `tool/groundtruth_labeler.py` to build eval CSVs before running `--eval`.
- For API-based user IDs, preload pool via `POST /api/user-ids/pool` before calling `POST /api/user-ids/issue`.
- Current detection runtime is not yet wired to consume `/api/user-ids/issue` automatically.

---

## Implementation Summary (Merged Notes)

### Eval Summary CSV Schema (Simplified)

- Removed columns:
    - `overlap_sec`, `coverage`, `duration_error_sec`, `duration_error_ratio`
    - `over_occupancy_sec`, `missed_occupancy_sec`, `gt_intervals`, `pred_intervals`
- Retained columns:
    - `pc_name`, `cam_name`, `model_name`
    - `gt_occupied_sec`, `pred_occupied_sec`
    - `occupied_accuracy_percent` (coverage * 100)
    - `count_accuracy_percent` (people count accuracy)
- Summary location:
    - `logs_video_mode/eval/eval_summary_duration_based.csv`

### Gate ROI Logic

Added in `tool/threaded_video_mode.py` with config keys in `tool/threaded_config.yaml`:

```yaml
GATE_ROI_CSV_SUFFIX: _gate_roi.csv
```

Behavior:

- Gate ROI marks camera entrance/exit regions.
- If a tracked person reaches gate ROI and then disappears, it is treated as a normal exit.
- Normal exit via gate suppresses hold boxes and disappearance snapshots for that track.

### Detection Pipeline Integration

`camera_thread_fn` now:

- Loads gate ROIs when available
- Uses gate-hit disappearance rule for normal exits
- Skips hold/snapshot reporting for gate exits

### How To Use Gate ROI

1. Define gate zones:

```powershell
python tool\roi_setup.py
```

Set `SETUP_MODE = "gate"` in `tool/roi_setup.py`, then click 4 points per camera.

2. Configure suffix in `tool/threaded_config.yaml`:

```yaml
GATE_ROI_CSV_SUFFIX: _gate_roi.csv
```

3. Run video mode:

```powershell
python tool\threaded_video_mode.py --eval-only
```

### Output Files Added/Updated

- Updated eval summary:
    - `logs_video_mode/eval/eval_summary_duration_based.csv`

### Configuration Parameters

| Key | Default | Purpose |
|-----|---------|---------|
| `GATE_ROI_CSV_SUFFIX` | `_gate_roi.csv` | File suffix for gate ROI CSVs |
