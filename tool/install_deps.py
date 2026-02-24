"""
install_deps.py

Simple helper to install project dependencies.
It inspects `yolo8_4cam_threadding.py` to see if `ENABLE_RESOURCE_MONITOR` is True.
If resource monitoring is enabled it will also install packages listed in
`requirements-optional.txt`. Otherwise it only installs the main
`requirements.txt` packages.

Usage (from project root):
    python tool/install_deps.py

This script calls pip via the current interpreter (sys.executable -m pip).
"""
import re
import sys
import subprocess
import os

# Get project root (parent directory of tool/)
TOOL_DIR = os.path.dirname(__file__)
ROOT = os.path.dirname(TOOL_DIR)
REQ_MAIN = os.path.join(TOOL_DIR, "requirements.txt")
REQ_OPT = os.path.join(TOOL_DIR, "requirements-optional.txt")
TARGET_FILE = os.path.join(ROOT, "yolo8_4cam_threadding.py")


def read_enable_flag(path):
    """Read ENABLE_RESOURCE_MONITOR flag from the given Python file without importing it.
    Returns True/False if found, otherwise None.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    m = re.search(r"^ENABLE_RESOURCE_MONITOR\s*=\s*(True|False)\b", content, re.M)
    if m:
        return m.group(1) == "True"
    return None


def run_pip_install(requirements_path):
    if not os.path.exists(requirements_path):
        print(f"Requirements file not found: {requirements_path}")
        return False
    cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_path]
    print("Running:", " ".join(cmd))
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print("pip install failed:", e)
        return False


def run_pip_uninstall(requirements_path):
    """Uninstall packages listed in a requirements file (ignores comments/blank lines)."""
    if not os.path.exists(requirements_path):
        print(f"Optional requirements file not found: {requirements_path}")
        return False

    pkgs = []
    with open(requirements_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # strip version specifiers for uninstall (keep name before [ or ==,>=,<)
            name = re.split(r"[>=<\[]", line)[0].strip()
            if name:
                pkgs.append(name)

    if not pkgs:
        print("No optional packages to uninstall.")
        return True

    cmd = [sys.executable, "-m", "pip", "uninstall", "-y"] + pkgs
    print("Running:", " ".join(cmd))
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print("pip uninstall failed:", e)
        return False


def main():
    print("Installing core requirements from requirements.txt")
    run_pip_install(REQ_MAIN)

    enabled = read_enable_flag(TARGET_FILE)
    if enabled is None:
        print("Could not detect ENABLE_RESOURCE_MONITOR flag in yolo8_4cam_threadding.py; skipping optional deps.")
        return

    if enabled:
        print("ENABLE_RESOURCE_MONITOR is True -> installing optional resource-monitoring packages")
        run_pip_install(REQ_OPT)
    else:
        print("ENABLE_RESOURCE_MONITOR is False -> uninstalling optional resource-monitoring packages (if present)")
        # attempt to uninstall optional packages listed in requirements-optional.txt
        run_pip_uninstall(REQ_OPT)


if __name__ == "__main__":
    main()
