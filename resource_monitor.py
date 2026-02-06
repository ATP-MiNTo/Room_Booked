import threading
import time
import os

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except Exception:
    psutil = None
    _PSUTIL_AVAILABLE = False

try:
    import pynvml
    pynvml.nvmlInit()
    _NVML_AVAILABLE = True
except Exception:
    pynvml = None
    _NVML_AVAILABLE = False

try:
    import torch
    _TORCH_AVAILABLE = True
except Exception:
    torch = None
    _TORCH_AVAILABLE = False


def start_resource_monitor(cams, device="cpu", sample_interval=1.0):
    """
    Start a background thread that periodically samples process and GPU resource usage
    and appends samples into each cam dict under keys: mem_samples, cpu_proc_samples,
    gpu_mem_samples, ts_samples.

    Returns (stop_event, thread)
    """

    stop_event = threading.Event()

    process = None
    if _PSUTIL_AVAILABLE:
        try:
            process = psutil.Process(os.getpid())
            # warm up cpu_percent
            process.cpu_percent(interval=None)
        except Exception:
            process = None

    def monitor_loop():
        while not stop_event.is_set():
            ts = time.time()
            rss = None
            cpu_proc = None
            gpu_mem_used = None

            if process is not None:
                try:
                    mi = process.memory_info()
                    rss = mi.rss
                except Exception:
                    rss = None
                try:
                    cpu_proc = process.cpu_percent(interval=None)
                except Exception:
                    cpu_proc = None

            # GPU memory via NVML if available
            if _NVML_AVAILABLE:
                try:
                    # sample all GPUs sum
                    total_used = 0
                    device_count = pynvml.nvmlDeviceGetCount()
                    for i in range(device_count):
                        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                        meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        total_used += int(meminfo.used)
                    gpu_mem_used = total_used
                except Exception:
                    gpu_mem_used = None
            else:
                # fallback to torch (if available and device is cuda)
                if _TORCH_AVAILABLE and device == "cuda":
                    try:
                        if torch.cuda.is_available():
                            # sum allocated across devices if multiple
                            total = 0
                            for i in range(torch.cuda.device_count()):
                                total += int(torch.cuda.memory_allocated(i))
                            gpu_mem_used = total
                    except Exception:
                        gpu_mem_used = None

            # write samples into each cam entry
            for cam in cams.values():
                cam.setdefault("mem_samples", []).append(rss)
                cam.setdefault("cpu_proc_samples", []).append(cpu_proc)
                cam.setdefault("gpu_mem_samples", []).append(gpu_mem_used)
                cam.setdefault("ts_samples", []).append(ts)

            # wait with timeout to allow quick stop
            stop_event.wait(sample_interval)

    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    return stop_event, thread


def stop_resource_monitor(stop_event, thread, timeout=2.0):
    stop_event.set()
    thread.join(timeout=timeout)


# Expose availability flags for callers
__all__ = [
    "start_resource_monitor",
    "stop_resource_monitor",
    "_PSUTIL_AVAILABLE",
    "_NVML_AVAILABLE",
    "_TORCH_AVAILABLE",
]
