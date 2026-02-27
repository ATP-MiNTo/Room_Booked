Room_Booked — YOLOv8 Multi-Camera Person Detection with PC Tracking
====================================================================

YOLOv8-based multi-camera person detection system with automatic ID assignment, PC area tracking, and performance monitoring. Supports up to 4 cameras simultaneously with optional polygon ROI (Region of Interest) tracking to identify which PC/workstation each person is using.

## Features

- **Multi-camera detection** (up to 4 cameras, easily configurable)
- **Auto ID assignment** (random 3-digit IDs per person)
- **PC area tracking** with dwell-time threshold (person must stay in area ≥3s before PCnum assigned)
- **Polygon ROI support** (define custom PC boundaries per camera)
- **Threading & multiprocessing** implementations for optimal performance
- **ROI image saving** with configurable intervals
- **CSV logging** with detection metadata (time, ID, confidence, PCnum)
- **Performance monitoring** (FPS, latency, inference time, optional CPU/GPU tracking)
- **GPU acceleration** (CUDA support if available)

---

## Project Structure

```
Room_Booked/
├── threading.py                    # Threading-based detection (recommended)
├── multiprocess.py                 # Multiprocessing-based detection
├── yolov8n.pt                      # YOLOv8 nano model weights
├── README.md                       # This file
├── tool/                           # Utility scripts & configuration
│   ├── roi_pc_setup.py            # Interactive ROI/PC area setup tool
│   ├── resource_monitor.py        # CPU/RAM/GPU monitoring (optional)
│   ├── install_deps.py            # Adaptive dependency installer
│   ├── requirements.txt           # Core dependencies
│   ├── requirements-optional.txt  # Optional monitoring packages
│   └── roi_config/                # PC ROI polygon definitions (CSV)
│       ├── Front_right_roi.csv
│       ├── Front_left_roi.csv
│       ├── Back_left_roi.csv
│       └── Back_right_roi.csv
├── logs/                           # All output data
│   ├── Front_right/               # Per-camera logs
│   │   └── people_with_conf_and_roi_Front_right_YYYYMMDD_HHMMSS.csv
│   ├── Front_left/
│   ├── Back_left/
│   ├── Back_right/
│   ├── roi_images/                # ROI images by camera and person ID
│   │   ├── Front_right/
│   │   │   ├── 001/
│   │   │   ├── 042/
│   │   │   └── ...
│   │   ├── Front_left/
│   │   └── ...
│   └── performance_summary.csv    # Aggregated performance metrics
└── Bin/                            # Archived/unused scripts
```

---

## Quick Start

### 1. Setup Environment (Windows PowerShell)

Create and activate virtual environment:
```powershell
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

**Recommended** (auto-detects monitoring needs):
```powershell
python tool\install_deps.py
```

**Manual**:
```powershell
pip install -r tool\requirements.txt
# Optional: pip install -r tool\requirements-optional.txt
```

### 3. (Optional) Define PC Areas

Run the interactive ROI setup tool to define PC boundaries:
```powershell
python tool\roi_pc_setup.py
```

**Instructions:**
- Opens each camera sequentially
- Click 4 points on the video frame to define each PC polygon boundary
- Press **Enter** to save the current polygon
- Press **s** to save and proceed to next camera
- Press **<** to undo last point
- Press **c** to clear draft points
- Press **q** to quit

**Output:** Saves polygon coordinates to `tool/roi_config/{CameraName}_roi.csv`

### 4. Run Detection

**Threading version** (recommended for I/O-bound workloads):
```powershell
python threading.py
```

**Multiprocessing version** (better CPU isolation):
```powershell
python multiprocess.py
```

Press `q` in any window or `Ctrl+C` to stop.

---

## Configuration

All configuration is at the top of `threading.py` and `multiprocess.py`:

### Camera Settings
```python
CAM_INDEXES = [0, 1, 2, 3]          # Camera device indices
CAM_NAMES = {
    0: "Front_right",
    1: "Front_left",
    2: "Back_left",
    3: "Back_right",
}
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
```

### Display Settings
```python
SHOW_WINDOWS = "Show"               # "Show" or "Hide" (Hide = better performance)
Windows_width, Windows_height = 960, 540
```

### Detection Settings
```python
CONF_THRESHOLD = 0.4                # Min confidence for person detection
SAVE_INTERVAL_SEC = 10              # Seconds between ROI image saves
```

### PC ROI Settings
```python
ENABLE_PC_ROI = True                # Enable PC area tracking
PC_DWELL_TIME_SEC = 3.0             # Dwell time before PCnum assigned
ROI_CONFIG_DIR = os.path.join("tool", "roi_config")
CSV_SUFFIX = "_roi.csv"
```

### Performance Settings
```python
process_every_n_frames = 2          # Process every N frames (1=all, 2=half, etc.)
ENABLE_RESOURCE_MONITOR = False     # CPU/GPU monitoring (requires tool/resource_monitor.py)
```

---

## Output Files

### Detection Logs
**Location:** `logs/{CameraName}/people_with_conf_and_roi_{CameraName}_{timestamp}.csv`

**Columns:**
- `time` — Detection timestamp
- `person_id` — Unique 3-digit ID
- `confidence` — Detection confidence score
- `roi_file` — Path to saved ROI image
- `PCnum` — PC identifier (e.g., "PC1", "PC2", or `None` if outside all PCs or dwell threshold not met)

**Example:**
```csv
time,person_id,confidence,roi_file,PCnum
2026-02-24 14:07:45,066,0.899,logs\roi_images\Back_left\066\ID066_1771916865.jpg,PC1
2026-02-24 14:07:55,066,0.912,logs\roi_images\Back_left\066\ID066_1771916875.jpg,PC1
2026-02-24 14:08:10,042,0.856,logs\roi_images\Back_left\042\ID042_1771916890.jpg,
```

### ROI Images
**Location:** `logs/roi_images/{CameraName}/{PersonID}/ID{PersonID}_{timestamp}.jpg`

Saved every `SAVE_INTERVAL_SEC` seconds (default: 10s) when person is detected.

### Performance Summary
**Location:** `logs/performance_summary.csv`

Aggregated per-camera performance metrics appended after each session:
- Session timestamp, camera name/index
- Frames processed, total runtime
- Average FPS, latency, inference time
- Unique persons detected
- Optional: CPU/RAM/GPU usage (if `ENABLE_RESOURCE_MONITOR = True`)

### ROI Configuration
**Location:** `tool/roi_config/{CameraName}_roi.csv`

Stores PC polygon definitions created by `tool/roi_pc_setup.py`:
- `pc_name` — PC identifier (PC1, PC2, etc.)
- `points_json` — JSON array of 4 polygon points `[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]`

---

## PC Area Tracking Logic

1. **ROI Loading:** At startup, if `ENABLE_PC_ROI = True`, detection scripts load polygon definitions from `tool/roi_config/{CameraName}_roi.csv`

2. **Position Tracking:** For each detected person, the script calculates the bounding box center and checks if it falls inside any PC polygon

3. **Dwell Threshold:** Person must remain in the same PC area for ≥ `PC_DWELL_TIME_SEC` (default 3.0s) before `PCnum` is assigned

4. **Logging:** `PCnum` is recorded in CSV logs only after threshold is met. Value is `None` if:
   - Person is outside all PC areas
   - Person hasn't stayed in PC area long enough
   - No ROI config exists for that camera

---

## GPU/CUDA Support

Scripts auto-detect CUDA and use GPU if available. Check availability:
```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

Performance benefits:
- 2-5x faster inference on GPU vs CPU
- Lower latency per frame
- Better multi-camera throughput

---

## Troubleshooting

### Cameras not detected
- Verify camera indices with Device Manager (Windows)
- Try `cv2.VideoCapture(idx, cv2.CAP_DSHOW)` for better Windows compatibility
- Check if another application is using the camera

### Slow startup
- First YOLO model load downloads weights (~6MB)
- First CUDA initialization can take 5-10 seconds
- Use `cv2.CAP_DSHOW` backend for faster camera opening on Windows

### Missing PCnum in logs
- Verify ROI CSV exists in `tool/roi_config/{CameraName}_roi.csv`
- Check `ENABLE_PC_ROI = True` in script
- Ensure person stays in PC area ≥ `PC_DWELL_TIME_SEC` seconds
- Run `tool/roi_pc_setup.py` to create/verify ROI definitions

### Import errors for resource_monitor
- This is optional; set `ENABLE_RESOURCE_MONITOR = False` if not needed
- Install optional dependencies: `pip install -r requirements-optional.txt`

---

## Advanced Usage

### Multiple PC areas per camera
The setup tool supports multiple PC polygons per camera. Just keep clicking **Save ROI** for each area.

### Customizing camera names
Edit `CAM_NAMES` dictionary at the top of detection scripts. Names affect:
- Log folder names (`logs/{CameraName}/`)
- CSV filenames
- ROI config filenames (`tool/roi_config/{CameraName}_roi.csv`)
- Window titles

### Adjusting performance
- **Increase throughput:** Set `process_every_n_frames = 3` or higher (skips inference on more frames)
- **Hide windows:** Set `SHOW_WINDOWS = "Hide"` for 10-20% FPS improvement
- **Lower resolution:** Reduce `FRAME_WIDTH` / `FRAME_HEIGHT` for faster capture/inference
- **Use multiprocessing:** Better CPU core utilization for multi-camera setups

### Frame skipping strategy
- `process_every_n_frames = 1` → Process every frame (max accuracy, slowest)
- `process_every_n_frames = 2` → Process every 2nd frame (balanced, default)
- `process_every_n_frames = 3` → Process every 3rd frame (high throughput, may miss fast movement)

---

## Dependencies

**Core** (tool/requirements.txt):
- `ultralytics` — YOLOv8 framework
- `opencv-python` — Computer vision & camera capture
- `torch` — Deep learning backend
- `pandas` — CSV logging
- `numpy` — Numerical operations

**Optional** (tool/requirements-optional.txt):
- `psutil` — CPU/RAM monitoring
- `pynvml` — NVIDIA GPU monitoring

---

## Original Notes

See `note.txt` for original development notes and archived information.

---

## License & Credits

Built with [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics).
