# Quick Start Guide

## Prerequisites

### 1. Python Environment
- Python 3.8 or higher
- Virtual environment already set up in `.venv/`

### 2. GPU & CUDA Compatibility
**Important:** Check `tool/requirements.txt` to verify that your CUDA version matches the PyTorch/YOLO dependencies.

If using GPU:
- NVIDIA GPU with CUDA support
- CUDA Toolkit installed and matching the version in `tool/requirements.txt`
- cuDNN installed (if required by your CUDA version)

If CPU-only, the script will automatically fall back to CPU mode.

## Installation

### 1. Activate Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r tool/requirements.txt
```

## Running the Application

### Offline Video Mode (Test Videos)
Process pre-recorded videos from `test_vid` directory:
```powershell
.\.venv\Scripts\python.exe tool\threaded_video_mode.py --video-input-dir test_vid
```

### Live Camera Mode
Capture from live cameras (indexes 0-3 by default):
```powershell
.\.venv\Scripts\python.exe threaded.py
```

### Configuration
Edit `tool/threaded_config.yaml` to adjust:
- Camera indexes and names
- Detection thresholds (confidence, IOU)
- PC ROI settings
- Detection schedule
- Output directories
- BG subtraction / motion gating: `ENABLE_MOTION_GATING: true` or `false`

If you want to test model performance with and without background subtraction, change that value and rerun the script.

## Output Locations

### Video Mode
- **Logs:** `logs_video_mode/<camera_name>/`
- **Reports:** `logs_video_mode/report/<camera_name>/opti_report/`
- **Summary:** `logs_video_mode/daily_summary_YYYYMMDD.csv`
- **PC State:** `logs_video_mode/pc_state_all.csv`

### Live Mode
- **Logs:** `logs/<camera_name>/`
- **Reports:** `logs/report/<camera_name>/opti_report/`
- **Summary:** `logs/daily_summary_YYYYMMDD.csv`

## Dynamic vs Fixed Threshold Comparison

The application captures comparison images when **dynamic (per-PC) thresholds detect people but fixed (global) thresholds would drop them**.

Saved to: `report_dir/opti_report/comparison_<pc>_<timestamp>_<index>.jpg`

**Layout:**
- **Left panel:** Dynamic mode result (green boxes, red outline for inspection)
- **Right panel:** Fixed mode result (red boxes, or "fixed: no detections")
- **Footer:** Source video and frame timestamp (bottom-right)

## Troubleshooting

### CUDA/GPU Issues
1. Verify CUDA version in `tool/requirements.txt` matches your system
2. Check GPU availability: `python -c "import torch; print(torch.cuda.is_available())"`
3. If GPU unavailable, the app will fall back to CPU automatically

### Missing Dependencies
Re-install requirements:
```powershell
pip install --upgrade -r tool/requirements.txt
```

### Config Errors
Ensure `tool/threaded_config.yaml` exists and contains all required keys. Missing or invalid keys will be reported as configuration errors at startup.

### No Camera/Video Found
- Verify camera indexes in config match your system
- For video mode, ensure video files exist in `--video-input-dir` path
- Check file extensions (`.mp4`, `.avi`, `.mov`, `.mkv`)

## Common Commands

| Task | Command |
|------|---------|
| Process test videos | `.\.venv\Scripts\python.exe tool\threaded_video_mode.py --video-input-dir test_vid` |
| Live camera capture | `.\.venv\Scripts\python.exe tool\threaded_video_mode.py` |
| Custom video dir | `.\.venv\Scripts\python.exe tool\threaded_video_mode.py --video-input-dir <path>` |
| Eval mode (offline) | `.\.venv\Scripts\python.exe tool\threaded_video_mode.py --eval --video-input-dir test_vid` |
| Stop (interactive) | Press `q` during execution |

## Key Features

- **Real-time person detection** using YOLO
- **Dynamic per-PC thresholds** for optimized detection per workstation
- **PC/Monitor ROI tracking** with state inference
- **Comparison reporting** showing dynamic vs fixed threshold differences
- **Multi-camera support** with parallel processing
- **GPU acceleration** (CUDA) with automatic CPU fallback
