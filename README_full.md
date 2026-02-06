Room_Booked — YOLOv8 Multi-Camera Person Detection
=================================================

This repository provides examples for running YOLOv8 person detection on single or multiple cameras (up to 4). It includes simple per-camera ROI saving, auto-assigned IDs, optional resource monitoring, and adaptive dependency installation.

Files of interest
- `yolo8.py` — single-camera detection example
- `yolo8_4cam.py` — 4-camera detection with ROI saving, per-camera CSV logs and aggregated performance summary
- `resource_monitor.py` — optional background resource (CPU/RAM/GPU) monitor (disabled by default)
- `install_deps.py` — adaptive installer that conditionally installs optional monitoring packages
- `requirements.txt` — core dependencies
- `requirements-optional.txt` — optional dependencies for resource monitoring (psutil, pynvml)

Quick start (Windows PowerShell)
1. Create and activate a virtual environment:

```powershell
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1
```

2. Install dependencies (recommended using the adaptive installer):

```powershell
python install_deps.py
```

Notes:
- `install_deps.py` reads the `ENABLE_RESOURCE_MONITOR` flag in `yolo8_4cam.py`. If True, it installs optional monitoring packages from `requirements-optional.txt`. If False, it will attempt to uninstall them.
- If you prefer manual installation:

```powershell
pip install -r requirements.txt
# optional: pip install -r requirements-optional.txt
```

Run the examples

Single camera:
```powershell
.venv\Scripts\python.exe yolo8.py
```

4-camera (ensure cameras are connected and accessible by the indices in `yolo8_4cam.py`):
```powershell
.venv\Scripts\python.exe yolo8_4cam.py
```

Configuration highlights
- `yolo8_4cam.py` top section exposes a few variables to tune behavior:
  - `CAM_INDEXES`, `CAM_NAMES` — which capture devices to open
  - `FRAME_WIDTH`, `FRAME_HEIGHT` — capture resolution (default 1920x1080)
  - `CONF_THRESHOLD` — detection confidence threshold
  - `process_every_n_frames` (per camera) — skip inference on some frames to improve throughput
  - `ENABLE_RESOURCE_MONITOR` — enable/disable background resource monitoring

Outputs
- ROI images: `logs/roi_images/cam<idx>/<personID>/...`
- Per-camera detection logs: `logs/cam<idx>/people_with_conf_and_roi_<name>_<timestamp>.csv`
- Aggregated performance summary (appended each run): `logs/performance_summary.csv`

GPU/CUDA
- If you have a CUDA-enabled PyTorch, the script will attempt to use the GPU. Check with:

```powershell
python -c "import torch; print('cuda available', torch.cuda.is_available())"
```

Troubleshooting & notes
- Always run `install_deps.py` from the activated venv or call the venv python explicitly to avoid modifying the system Python.
- The uninstall step in `install_deps.py` is best-effort; if you share environments across projects you may want to avoid automatic uninstall. I can add a confirmation prompt if you prefer.
- If `pynvml` import fails for GPU monitoring, confirm NVIDIA drivers are installed and that `pynvml` is installed into the same venv.

Want changes?
- I can add a `--yes` prompt before uninstalling optional packages, convert perf numbers to MB in the CSV, or rearrange output folders (e.g., `logs/cam0/{roi,logs}`).

Original quick notes were moved to `note.txt`.
