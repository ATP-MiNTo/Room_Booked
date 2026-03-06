Room_Booked — YOLOv8 Multi-Camera Room/PC Usage Tracking
=========================================================

YOLOv8-based multi-camera person detection and workstation usage tracking.

## Maintenance Status

- **Actively maintained runtime:** `threaded.py`
- **Legacy (not maintained):** `multiprocess.py`

As the project scope increased, maintaining both threading and multiprocessing pipelines became too costly and inconsistent. We now standardize on `threaded.py` because it is the version currently validated and efficient for this project workflow.

---

## Current Capabilities

- Multi-camera person detection (default: 4 cameras)
- Auto 3-digit person ID assignment
- Seat ROI overlap tracking with dwell threshold
- Monitor ROI ON/OFF heuristic per PC
- PC activity events (`USING_PC` / `NON_PC_ACTIVITY`)
- Unattended/person-flag detection (`PC ON + no person overlap` over threshold)
- Realtime compact all-PC state CSV (`pc_name,pc_on,availble`)
- Detection schedule gating (YOLO inference only)
- Session performance summary logging

---

## Project Structure

```text
Room_Booked/
├── threaded.py
├── multiprocess.py                 # legacy / not maintained
├── yolov8n.pt
├── README.md
├── note.txt
├── logs/
│   ├── performance_summary.csv
│   ├── pc_state_all_YYYYMMDD_HHMMSS.csv
│   ├── pc_unattended_flags_YYYYMMDD_HHMMSS.csv
│   ├── {CameraName}/
│   │   ├── people_with_conf_and_roi_{CameraName}_{session}.csv
│   │   └── pc_activity_events_{CameraName}_{session}.csv
│   └── roi_images/{CameraName}/{PersonID}/...
└── tool/
    ├── install_deps.py
    ├── requirements.txt
    ├── requirements-optional.txt
    ├── resource_monitor.py
    ├── roi_pcseat_setup.py
    ├── roi_monitor_setup.py
    ├── roi_edit_setup.py
    ├── see_roi_conf.py
    └── roi_config/
        ├── Front_right_roi.csv
        ├── Front_right_monitor_roi.csv
        └── ...
```

---

## Quick Start (Windows PowerShell)

### 1) Create and activate environment

```powershell
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

Recommended:

```powershell
python tool\install_deps.py
```

Manual:

```powershell
pip install -r tool\requirements.txt
# Optional monitoring extras:
# pip install -r tool\requirements-optional.txt
```

### 3) Configure ROIs

Seat ROI setup:

```powershell
python tool\roi_pcseat_setup.py
```

Monitor ROI setup:

```powershell
python tool\roi_monitor_setup.py
```

Unified ROI editor:

```powershell
python tool\roi_edit_setup.py
```

Mode for `roi_edit_setup.py` is hardcoded at the top of the file using `EDIT_MODE` (`"pcseat"` or `"monitor"`; typo `"moniter"` is tolerated).

ROI viewer (seat + monitor overlay):

```powershell
python tool\see_roi_conf.py
```

### 4) Run detection (maintained pipeline)

```powershell
python threaded.py
```

Stop with `q` (window) or `Ctrl+C` (terminal).

---

## Key Configuration (`threaded.py`)

Important values are at the top of `threaded.py`.

- Camera:
  - `CAM_INDEXES = [0, 1, 2, 3]`
  - `CAM_NAMES = {0: "Front_right", 1: "Front_left", 2: "Back_left", 3: "Back_right"}`
- Detection:
  - `CONF_THRESHOLD = 0.4`
  - `IOU_THRESHOLD = 0.4`
  - `SAVE_INTERVAL_SEC = 10`
- Detection schedule:
  - `DETECTION_START_HOUR_24 = 8`
  - `DETECTION_END_HOUR_24 = 18`
- ROI / PC state:
  - `ENABLE_PC_ROI = True`
  - `ENABLE_MONITOR_ROI = True`
  - `PERSON_OVERLAP_DWELL_SEC = 10.0`
  - `PC_ON_NO_PERSON_DWELL_SEC = 300.0`
  - `MONITOR_ON_MEAN_THRESHOLD = 70.0`
  - `MONITOR_ON_STD_THRESHOLD = 12.0`
  - `MONITOR_STATE_STABLE_FRAMES = 3`
- Realtime all-PC file:
  - `ENABLE_REALTIME_PC_STATE_CSV = True`
  - `REALTIME_PC_STATE_WRITE_INTERVAL_SEC = 1.0`

Detection schedule gates YOLO inference only; camera capture and display loop still continue.

---

## Output Files

### Per-camera detection log

`logs/{CameraName}/people_with_conf_and_roi_{CameraName}_{session}.csv`

Main columns: `time`, `person_id`, `confidence`, `roi_file`, `PCnum`

### Per-camera PC activity events

`logs/{CameraName}/pc_activity_events_{CameraName}_{session}.csv`

Main columns include: `time`, `cam_name`, `pc_name`, `event_type`, `person_id`, `pc_on`, `dwell_sec`, `PCnum`

### Combined unattended/person-flag log (all cameras)

`logs/pc_unattended_flags_{session}.csv`

Columns: `time`, `cam_name`, `pc_name`, `last_person_id`, `pc_on`, `empty_dwell_sec`, `reason`

### Realtime compact all-PC state (all cameras)

`logs/pc_state_all_{session}.csv`

Current schema: `pc_name`, `pc_on`, `availble`

### ROI image crops

`logs/roi_images/{CameraName}/{PersonID}/ID{PersonID}_{timestamp}.jpg`

### Performance summary

`logs/performance_summary.csv`

---

## ROI Configuration Reference

This section merges the previous `tool/roi_config/README.txt` content.

### Directory

`tool/roi_config/`

### Naming

- Seat ROI: `{CameraName}_roi.csv`
- Monitor ROI: `{CameraName}_monitor_roi.csv`

Example files:

- `Front_right_roi.csv`
- `Front_left_roi.csv`
- `Back_left_roi.csv`
- `Back_right_roi.csv`
- `Front_right_monitor_roi.csv`
- `Front_left_monitor_roi.csv`
- `Back_left_monitor_roi.csv`
- `Back_right_monitor_roi.csv`

### CSV format (seat and monitor)

```csv
pc_name,points_json
PC1,"[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"
PC2,"[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"
```

Monitor ROI should reuse the same `pc_name` values as seat ROI to keep PC mapping consistent.

### ROI editor controls (`tool/roi_edit_setup.py`)

- `<` / `>` : rotate selected ROI row
- `c` : clear selected ROI points
- `n` / `m` : next / previous camera
- `s` : save current camera CSV
- `q` : exit editor
- Mouse left click: place 4 points to replace selected ROI polygon

---

## Notes

- `multiprocess.py` remains in the repository as legacy reference only.
- For all active development and deployment, use `threaded.py`.
- Keep `CAM_NAMES` and ROI CSV filenames aligned.
