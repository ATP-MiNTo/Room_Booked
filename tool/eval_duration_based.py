#!/usr/bin/env python3
"""
Standalone duration-based evaluation tool.
Recomputes eval metrics from existing eval detail CSV files using occupancy duration logic.
No video processing or heavy dependencies required.
"""

import os
import sys
import argparse
import pandas as pd
from collections import defaultdict


def pc_name_sort_key(pc_name):
    text = str(pc_name)
    if text == "ALL":
        return (10**9, "ALL")
    digits = "".join(ch for ch in text if ch.isdigit())
    number = int(digits) if digits else 10**8
    return (number, text)


def build_occupancy_intervals_from_detail(detail_rows, pc_name, debounce_sec=2.0, occupied_key="occupied_pred"):
    pc_rows = [r for r in detail_rows if r.get("pc_name") == pc_name]
    if not pc_rows:
        return []

    pc_rows_sorted = sorted(pc_rows, key=lambda r: float(r.get("t_sec", 0)))
    intervals = []
    in_interval = False
    interval_start = None
    last_occupied = None

    for row in pc_rows_sorted:
        occupied_pred = int(row.get(occupied_key, row.get("occupied_pred", 0)))
        t_sec = float(row.get("t_sec", 0))

        if occupied_pred == 1:
            if not in_interval:
                interval_start = t_sec
                in_interval = True
            last_occupied = t_sec
        else:
            if in_interval and last_occupied is not None:
                duration = last_occupied - interval_start
                if duration >= debounce_sec:
                    intervals.append((interval_start, last_occupied + 1.0))
                in_interval = False
                last_occupied = None

    if in_interval and last_occupied is not None:
        duration = last_occupied - interval_start
        if duration >= debounce_sec:
            intervals.append((interval_start, last_occupied + 1.0))

    return sorted(intervals)


def parse_timestamp_seconds(time_text):
    try:
        from datetime import datetime as dt_obj
        dt = dt_obj.strptime(time_text, "%Y-%m-%d %H:%M:%S")
        epoch_date = dt_obj(1970, 1, 1, 0, 0, 0)
        return (dt - epoch_date).total_seconds()
    except Exception:
        return 0.0


def build_gt_occupancy_intervals(gt_lookup, pc_name, video_end_ts=None):
    if not gt_lookup or not pc_name:
        return []

    gt_rows = [(time_text, gt_info) for (time_text, pc), gt_info in gt_lookup.items() if pc == pc_name]
    if not gt_rows:
        return []

    try:
        gt_rows_sorted = sorted(gt_rows, key=lambda x: parse_timestamp_seconds(x[0]))
    except Exception:
        return []

    timeline = {}
    for time_text, gt_info in gt_rows_sorted:
        sec = parse_timestamp_seconds(time_text)
        timeline[sec] = 1 if int(gt_info.get("occupied_gt", 0)) > 0 else 0

    points = sorted(timeline.items(), key=lambda item: item[0])
    if not points:
        return []

    intervals = []
    in_interval = False
    interval_start = None

    for i, (cur_sec, cur_occupied) in enumerate(points[:-1]):
        next_sec, next_occupied = points[i + 1]

        if cur_occupied == 1 and not in_interval:
            interval_start = cur_sec
            in_interval = True

        if in_interval and next_occupied == 0:
            intervals.append((interval_start, next_sec))
            in_interval = False
            interval_start = None

    last_sec, last_occupied = points[-1]
    if last_occupied == 1:
        if not in_interval:
            interval_start = last_sec
        tail_end = video_end_ts if video_end_ts is not None else (last_sec + 900)
        intervals.append((interval_start, tail_end))

    return sorted(intervals)


def compute_interval_overlap_sec(interval1, interval2):
    start = max(interval1[0], interval2[0])
    end = min(interval1[1], interval2[1])
    return max(0.0, end - start)


def compute_people_count_accuracy(detail_rows, gt_lookup, pc_name):
    total = 0
    correct = 0

    for row in detail_rows:
        if str(row.get("pc_name", "")) != str(pc_name):
            continue

        time_text = str(row.get("time", "")).strip()
        if not time_text:
            continue

        gt = gt_lookup.get((time_text, str(pc_name)))
        if not gt:
            continue

        try:
            pred_count = int(row.get("people_count_pred", 0))
            gt_count = int(gt.get("people_count_gt", 0))
        except Exception:
            continue

        total += 1
        if pred_count == gt_count:
            correct += 1

    accuracy_percent = (100.0 * correct / total) if total > 0 else 0.0
    return {
        "count_correct_samples": int(correct),
        "count_total_samples": int(total),
        "count_accuracy_percent": round(accuracy_percent, 2),
    }


def compute_duration_metrics(detail_rows, gt_lookup, pc_name, video_end_ts=None):
    pred_intervals = build_occupancy_intervals_from_detail(
        detail_rows,
        pc_name,
        debounce_sec=2.0,
        occupied_key="occupied_pred",
    )
    pred_model_only_intervals = build_occupancy_intervals_from_detail(
        detail_rows,
        pc_name,
        debounce_sec=2.0,
        occupied_key="occupied_pred_model_only",
    )
    gt_intervals = build_gt_occupancy_intervals(gt_lookup, pc_name, video_end_ts)
    if not gt_intervals:
        return None

    gt_total_sec = sum(end - start for start, end in gt_intervals)
    pred_total_sec = sum(end - start for start, end in pred_intervals)
    pred_total_sec_model_only = sum(end - start for start, end in pred_model_only_intervals)

    total_overlap_sec = 0.0
    for pred_interval in pred_intervals:
        for gt_interval in gt_intervals:
            total_overlap_sec += compute_interval_overlap_sec(pred_interval, gt_interval)

    coverage = total_overlap_sec / gt_total_sec if gt_total_sec > 0 else 0.0
    occupied_accuracy_percent = coverage * 100.0
    over_occupancy_sec = pred_total_sec - total_overlap_sec
    count_metrics = compute_people_count_accuracy(detail_rows, gt_lookup, pc_name)

    return {
        "gt_occupied_sec": round(gt_total_sec, 2),
        "pred_occupied_sec": round(pred_total_sec, 2),
        "pred_occupied_sec_model_only": round(pred_total_sec_model_only, 2),
        "occupied_accuracy_percent": round(occupied_accuracy_percent, 2),
        "count_accuracy_percent": count_metrics["count_accuracy_percent"],
        "count_correct_samples": count_metrics["count_correct_samples"],
        "count_total_samples": count_metrics["count_total_samples"],
        "_overlap_sec_internal": float(total_overlap_sec),
        "_over_occupancy_sec_internal": float(over_occupancy_sec),
    }


def discover_detail_csv(cam_eval_dir):
    eval_detail_csvs = [
        f for f in os.listdir(cam_eval_dir)
        if f.startswith("eval_detail_") and f.endswith(".csv")
    ]
    if eval_detail_csvs:
        return os.path.join(cam_eval_dir, sorted(eval_detail_csvs)[-1]), "eval_detail"

    detection_detail_csvs = [
        f for f in os.listdir(cam_eval_dir)
        if f.startswith("detection_detail_") and f.endswith(".csv")
    ]
    if detection_detail_csvs:
        return os.path.join(cam_eval_dir, sorted(detection_detail_csvs)[-1]), "detection_detail"

    return None, None


def run_eval_only_duration(eval_log_root, groundtruth_dir):
    print("\n=== Duration-Based Evaluation (Seat-Time Efficiency) ===")
    print(f"Eval log root: {eval_log_root}")
    print(f"Groundtruth dir: {groundtruth_dir}")

    if not os.path.exists(eval_log_root):
        print(f"Error: eval log root does not exist: {eval_log_root}")
        return False

    cam_folders = [d for d in os.listdir(eval_log_root) if os.path.isdir(os.path.join(eval_log_root, d))]
    if not cam_folders:
        print("No camera eval folders found.")
        return False

    all_summary_rows = []

    for cam_label in sorted(cam_folders):
        cam_eval_dir = os.path.join(eval_log_root, cam_label)

        detail_csv, detail_kind = discover_detail_csv(cam_eval_dir)
        if not detail_csv:
            print(f"No eval_detail or detection_detail CSV found for {cam_label}, skipping.")
            continue

        print(f"\nProcessing {detail_csv} ({detail_kind})...")

        try:
            detail_df = pd.read_csv(detail_csv)
        except Exception as e:
            print(f"Failed to read {detail_csv}: {e}")
            continue

        if detail_df.empty:
            print(f"Warning: {detail_csv} is empty, skipping.")
            continue

        cam_name = detail_df["cam_name"].iloc[0] if len(detail_df) > 0 else cam_label
        gt_path = os.path.join(groundtruth_dir, f"{cam_label}_gt.csv")

        if not os.path.exists(gt_path):
            print(f"Groundtruth not found for {cam_label}: {gt_path}, skipping.")
            continue

        try:
            gt_df = pd.read_csv(gt_path)
            gt_lookup = {}
            for _, row in gt_df.iterrows():
                time_text = str(row.get("time", "")).strip()
                pc_name = str(row.get("pc_name", "")).strip()
                if time_text and pc_name:
                    gt_lookup[(time_text, pc_name)] = {
                        "occupied_gt": int(row.get("occupied_gt", 0)),
                        "people_count_gt": int(row.get("people_count_gt", 0)),
                    }
            print(f"Loaded {len(gt_lookup)} GT entries for {cam_label}")
        except Exception as e:
            print(f"Failed to load groundtruth {gt_path}: {e}")
            continue

        video_end_ts = None
        if len(detail_df) > 0:
            video_end_ts = float(detail_df["t_sec"].iloc[-1])

        detail_records = detail_df.to_dict("records")
        pc_names = sorted(detail_df["pc_name"].unique())

        print(f"  {len(pc_names)} seats found, computing metrics...")

        pc_count = 0
        cam_gt_total = 0.0
        cam_overlap_total = 0.0
        cam_over_occupancy_total = 0.0
        cam_pred_model_only_total = 0.0
        cam_count_correct_samples = 0
        cam_count_total_samples = 0

        for pc_name in pc_names:
            metrics = compute_duration_metrics(detail_records, gt_lookup, pc_name, video_end_ts)
            if metrics is None:
                continue

            pc_count += 1
            all_summary_rows.append({
                "cam_name": cam_name,
                "pc_name": pc_name,
                "model_name": detail_df["model_name"].iloc[0] if len(detail_df) > 0 else "unknown",
                "gt_occupied_sec": metrics["gt_occupied_sec"],
                "pred_occupied_sec": metrics["pred_occupied_sec"],
                "pred_occupied_sec_model_only": metrics["pred_occupied_sec_model_only"],
                "occupied_accuracy_percent": metrics["occupied_accuracy_percent"],
                "count_accuracy_percent": metrics["count_accuracy_percent"],
            })

            cam_gt_total += float(metrics["gt_occupied_sec"])
            cam_overlap_total += float(metrics.get("_overlap_sec_internal", 0.0))
            cam_over_occupancy_total += float(metrics.get("_over_occupancy_sec_internal", 0.0))
            cam_pred_model_only_total += float(metrics.get("pred_occupied_sec_model_only", 0.0))
            cam_count_correct_samples += int(metrics.get("count_correct_samples", 0))
            cam_count_total_samples += int(metrics.get("count_total_samples", 0))

        if pc_count > 0:
            pred_total = cam_overlap_total + cam_over_occupancy_total
            coverage = cam_overlap_total / cam_gt_total if cam_gt_total > 0 else 0.0

            all_summary_rows.append({
                "cam_name": cam_name,
                "pc_name": "ALL",
                "model_name": detail_df["model_name"].iloc[0] if len(detail_df) > 0 else "unknown",
                "gt_occupied_sec": round(cam_gt_total, 2),
                "pred_occupied_sec": round(pred_total, 2),
                "pred_occupied_sec_model_only": round(cam_pred_model_only_total, 2),
                "occupied_accuracy_percent": round(coverage * 100.0, 2),
                "count_accuracy_percent": round((100.0 * cam_count_correct_samples / cam_count_total_samples) if cam_count_total_samples > 0 else 0.0, 2),
            })
            print(f"  {pc_count} seats evaluated, camera {cam_name} occupied_accuracy={coverage * 100.0:.1f}%")

    if all_summary_rows:
        summary_path = os.path.join(eval_log_root, "eval_summary_duration_based.csv")
        summary_columns = [
            "pc_name", "cam_name", "model_name", "gt_occupied_sec", "pred_occupied_sec", "pred_occupied_sec_model_only",
            "occupied_accuracy_percent", "count_accuracy_percent",
        ]
        all_summary_rows = sorted(
            all_summary_rows,
            key=lambda row: (
                pc_name_sort_key(row.get("pc_name", "")),
                str(row.get("pc_name", "")) == "ALL",
                str(row.get("cam_name", "")),
            ),
        )
        summary_df = pd.DataFrame(all_summary_rows)
        summary_df = summary_df[summary_columns]
        summary_df.to_csv(summary_path, index=False)

        print("\n=== Summary Saved ===")
        print(f"File: {summary_path}")
        return True

    print("No metrics computed.")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Duration-based evaluation tool (reprocess existing eval outputs)")
    parser.add_argument(
        "--eval-log-dir",
        default="",
        help="Eval output root directory (default: logs_video_mode/eval)",
    )
    parser.add_argument(
        "--groundtruth-dir",
        default=os.path.join("tool", "groundtruth"),
        help="Groundtruth CSV directory",
    )
    args = parser.parse_args()

    eval_log_root = args.eval_log_dir.strip() if args.eval_log_dir else "logs_video_mode/eval"
    eval_log_root = os.path.normpath(eval_log_root)
    groundtruth_dir = os.path.normpath(args.groundtruth_dir)

    success = run_eval_only_duration(eval_log_root, groundtruth_dir)
    sys.exit(0 if success else 1)
