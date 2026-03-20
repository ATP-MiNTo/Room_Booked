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
- Auto 3-digit person ID assignment and ROI image snapshots
- Seat ROI overlap tracking and dwell-based usage classification
- Monitor ROI ON/OFF heuristic with stabilization frames
- PC activity event logs (`USING_PC` / `NON_PC_ACTIVITY`)
- Unattended/person-flag logic (`reason=1` / `reason=2`)
- Realtime all-PC compact state CSV (`pc_name,pc_on,availble`)
- REST API endpoints for booking website integration (local network)
- WebSocket stream for realtime all-PC status push
- Smoothed people counter (mode over time window)
- Smoothed PC availability state (same mode-window idea)
- Detection schedule gating (live mode)
- Session performance summary logging

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
    ├── roi_pcseat_setup.py
    ├── roi_monitor_setup.py
    ├── roi_edit_setup.py
    ├── see_roi_conf.py
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
python tool\roi_pcseat_setup.py
python tool\roi_monitor_setup.py
python tool\roi_edit_setup.py
python tool\see_roi_conf.py
```

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

For ROI reuse, keep video filenames aligned with ROI camera labels (example: `Front_right.mp4`, `Back_left.mp4`).

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
- `GET /api/people?camera=&date=&person_id=&limit=`
    - Person snapshot/detection logs from per-camera daily CSVs.
- `GET /api/pc-activity?camera=&pc_name=&date=&event_type=&limit=`
    - PC activity events (`USING_PC`, `NON_PC_ACTIVITY`).
- `GET /api/unattended?date=&pc_name=&reason=&limit=`
    - Combined unattended/person-flag logs (`reason=1` / `reason=2`).
- `GET /api/performance?date=`
    - Session performance summary rows.
- `GET /api/cameras`
    - Camera/source summary + latest known performance row.
- `GET /api/dates`
    - Available date list with cameras that have data.
- `WS /ws/pc-updates`
    - Realtime push stream (about once per second) of all-PC status.

WebSocket note:

- Normal `GET` API: website requests data each time (polling).
- WebSocket API: website keeps one open connection and receives pushed updates instantly.

---

## Output Files

Per-source logs (live and video mode follow same structure under different root dirs):

- `{LOG_ROOT}/{SourceName}/people_with_conf_and_roi_{SourceName}_YYYYMMDD.csv`
- `{LOG_ROOT}/{SourceName}/pc_activity_events_{SourceName}_YYYYMMDD.csv`
- `{LOG_ROOT}/pc_unattended_flags_YYYYMMDD.csv`
- `{LOG_ROOT}/pc_state_all.csv` (realtime overwrite)
- `{LOG_ROOT}/roi_images/{SourceName}/{PersonID}/...`
- `{LOG_ROOT}/performance_summary.csv`

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

CSV format:

```csv
pc_name,points_json
PC1,"[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"
PC2,"[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"
```

Use matching `pc_name` values between seat and monitor ROI files.

---

## Quick Notes

- For active work, use `threaded.py` and `tool/threaded_video_mode.py`.
- Keep source labels and ROI filenames aligned.
- Adjust behavior primarily through `tool/threaded_config.yaml`.
