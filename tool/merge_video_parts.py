import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2


def merge_with_ffmpeg(input_a: Path, input_b: Path, output_path: Path) -> bool:
    """Try lossless concat first when ffmpeg is available."""
    if shutil.which("ffmpeg") is None:
        return False

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        list_file = Path(f.name)
        f.write(f"file '{input_a.as_posix()}'\n")
        f.write(f"file '{input_b.as_posix()}'\n")

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    finally:
        try:
            os.remove(list_file)
        except OSError:
            pass


def _open_video(path: Path) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {path}")
    return cap


def merge_with_opencv(input_a: Path, input_b: Path, output_path: Path) -> None:
    """Re-encode two videos into one output using OpenCV."""
    cap1 = _open_video(input_a)
    cap2 = _open_video(input_b)

    fps1 = cap1.get(cv2.CAP_PROP_FPS)
    fps2 = cap2.get(cv2.CAP_PROP_FPS)
    fps = fps1 if fps1 and fps1 > 0 else (fps2 if fps2 and fps2 > 0 else 25.0)

    width = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        cap1.release()
        cap2.release()
        raise RuntimeError("Cannot read output frame size from first input video.")

    # mp4v is broadly available with OpenCV on Windows.
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    if not out.isOpened():
        cap1.release()
        cap2.release()
        raise RuntimeError(f"Cannot create output video: {output_path}")

    try:
        for cap in (cap1, cap2):
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame.shape[1] != width or frame.shape[0] != height:
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)
                out.write(frame)
    finally:
        cap1.release()
        cap2.release()
        out.release()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge two split video files into one output video."
    )
    parser.add_argument("input_a", help="First video part (plays first)")
    parser.add_argument("input_b", help="Second video part (plays second)")
    parser.add_argument("output", help="Output merged video path, e.g. merged.mp4")
    parser.add_argument(
        "--opencv-only",
        action="store_true",
        help="Skip ffmpeg and force OpenCV re-encode path.",
    )
    args = parser.parse_args()

    input_a = Path(args.input_a)
    input_b = Path(args.input_b)
    output_path = Path(args.output)

    if not input_a.exists():
        raise FileNotFoundError(f"Input file not found: {input_a}")
    if not input_b.exists():
        raise FileNotFoundError(f"Input file not found: {input_b}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.opencv_only and merge_with_ffmpeg(input_a, input_b, output_path):
        print(f"Merged successfully with ffmpeg: {output_path}")
        return

    merge_with_opencv(input_a, input_b, output_path)
    print(f"Merged successfully with OpenCV: {output_path}")


if __name__ == "__main__":
    main()
