#!/usr/bin/env python3
"""
Standalone duration-based evaluation tool.
Recomputes eval metrics from existing eval_detail CSV files using occupancy duration logic.
No video processing or heavy dependencies required.
"""

import os
import sys
import argparse
import time
import pandas as pd
from collections import defaultdict


def pc_name_sort_key(pc_name):
    text = str(pc_name)
    if text == "ALL":
        return (10**9, "ALL")
    digits = "".join(ch for ch in text if ch.isdigit())
    number = int(digits) if digits else 10**8
    return (number, text)


def build_occupancy_intervals_from_detail(detail_rows, pc_name, debounce_sec=2.0):
    """
    Build continuous occupancy intervals from per-second detail samples.
    Filters for given pc_name and groups consecutive occupied_pred=1 samples.
    Debounce: ignore bursts shorter than debounce_sec.
    Returns list of (start_ts, end_ts) tuples in seconds.
    """
    pc_rows = [r for r in detail_rows if r.get("pc_name") == pc_name]
    if not pc_rows:
        return []
    
    # Sort by t_sec
    pc_rows_sorted = sorted(pc_rows, key=lambda r: float(r.get("t_sec", 0)))
    
    intervals = []
    in_interval = False
    interval_start = None
    last_occupied = None
    
    for row in pc_rows_sorted:
        occupied_pred = int(row.get("occupied_pred", 0))
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
                    intervals.append((interval_start, last_occupied + 1.0))  # +1 to include end second
                in_interval = False
                last_occupied = None
    
    # Close any open interval at end
    if in_interval and last_occupied is not None:
        duration = last_occupied - interval_start
        if duration >= debounce_sec:
            intervals.append((interval_start, last_occupied + 1.0))
    
    return sorted(intervals)


def parse_timestamp_seconds(time_text):
    """
    Parse timestamp string (e.g., "1970-01-01 00:00:00") to seconds since epoch.
    Handles dates before 1970 by using datetime.
    """
    try:
        from datetime import datetime as dt_obj
        dt = dt_obj.strptime(time_text, "%Y-%m-%d %H:%M:%S")
        epoch_date = dt_obj(1970, 1, 1, 0, 0, 0)
        delta = dt - epoch_date
        return delta.total_seconds()
    except Exception:
        return 0


def build_gt_occupancy_intervals(gt_lookup, pc_name, video_end_ts=None):
    """
    Build continuous occupancy intervals from sparse GT snapshots using forward-fill.
    Consecutive occupied samples are merged into one interval, matching see_roi_conf.py.
    Returns list of (start_ts, end_ts) tuples.
    """
    if not gt_lookup or not pc_name:
        return []
    
    # Get all GT rows for this PC, sorted by time
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
        if sec is not None:
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
        tail_end = video_end_ts if video_end_ts else (last_sec + 900)
        intervals.append((interval_start, tail_end))
    
    return sorted(intervals)


def compute_interval_overlap_sec(interval1, interval2):
    """Compute overlap in seconds between two (start, end) intervals."""
    start = max(interval1[0], interval2[0])
    end = min(interval1[1], interval2[1])
    return max(0, end - start)


def compute_people_count_accuracy(detail_rows, gt_lookup, pc_name):
    """Compute exact-match accuracy for people_count_pred against GT for one seat."""
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
    """
    Compute seat-time efficiency metrics: coverage, duration error, etc.
    """
    pred_intervals = build_occupancy_intervals_from_detail(detail_rows, pc_name, debounce_sec=2.0)
    gt_intervals = build_gt_occupancy_intervals(gt_lookup, pc_name, video_end_ts)
    
    if not gt_intervals:
        return None
    
    # Compute GT total occupied time
    gt_total_sec = sum(end - start for start, end in gt_intervals)
    
    # Compute predicted total occupied time
    pred_total_sec = sum(end - start for start, end in pred_intervals)
    
    # Compute coverage: overlap / gt_total
    total_overlap_sec = 0
    for pred_interval in pred_intervals:
        for gt_interval in gt_intervals:
            total_overlap_sec += compute_interval_overlap_sec(pred_interval, gt_interval)
    
    coverage = total_overlap_sec / gt_total_sec if gt_total_sec > 0 else 0.0
    
    # Duration error
    duration_error_sec = abs(pred_total_sec - gt_total_sec)
    duration_error_ratio = duration_error_sec / gt_total_sec if gt_total_sec > 0 else 0.0
    occupied_accuracy_percent = coverage * 100.0
    count_metrics = compute_people_count_accuracy(detail_rows, gt_lookup, pc_name)
    
    # Over-occupancy: predicted but not in GT
    over_occupancy_sec = pred_total_sec - total_overlap_sec
    
    # Missed occupancy: GT but not predicted
    missed_occupancy_sec = gt_total_sec - total_overlap_sec
    
    return {
        "gt_occupied_sec": round(gt_total_sec, 2),
        "pred_occupied_sec": round(pred_total_sec, 2),
        "overlap_sec": round(total_overlap_sec, 2),
        "coverage": round(coverage, 4),
        "occupied_accuracy_percent": round(occupied_accuracy_percent, 2),
        "duration_error_sec": round(duration_error_sec, 2),
        "duration_error_ratio": round(duration_error_ratio, 4),
        "over_occupancy_sec": round(over_occupancy_sec, 2),
        "missed_occupancy_sec": round(missed_occupancy_sec, 2),
        "gt_intervals": len(gt_intervals),
        "pred_intervals": len(pred_intervals),
        "count_accuracy_percent": count_metrics["count_accuracy_percent"],
        "count_correct_samples": count_metrics["count_correct_samples"],
        "count_total_samples": count_metrics["count_total_samples"],
    }


def discover_detail_csv(cam_eval_dir):
    """Prefer eval detail CSVs, but fall back to reusable detection snapshots."""
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
    """
    Re-evaluate existing eval outputs using duration-based metrics.
    """
    print("\n=== Duration-Based Evaluation (Seat-Time Efficiency) ===")
    print(f"Eval log root: {eval_log_root}")
    print(f"Groundtruth dir: {groundtruth_dir}")
    
    if not os.path.exists(eval_log_root):
        print(f"Error: eval log root does not exist: {eval_log_root}")
        return False
    
    # Discover all camera eval folders
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
        
        # Get camera name and load groundtruth
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
                    occupied_gt = int(row.get("occupied_gt", 0))
                    people_count_gt = int(row.get("people_count_gt", 0))
                    gt_lookup[(time_text, pc_name)] = {
                        "occupied_gt": occupied_gt,
                        "people_count_gt": people_count_gt,
                    }
            print(f"Loaded {len(gt_lookup)} GT entries for {cam_label}")
        except Exception as e:
            print(f"Failed to load groundtruth {gt_path}: {e}")
            continue
        
        # Get video end time from detail CSV (last t_sec)
        video_end_ts = None
        if len(detail_df) > 0:
            last_t_sec = float(detail_df["t_sec"].iloc[-1])
            video_end_ts = last_t_sec
        
        # Compute duration metrics per PC
        detail_records = detail_df.to_dict("records")
        pc_names = sorted(detail_df["pc_name"].unique())
        
        print(f"  {len(pc_names)} seats found, computing metrics...")
        
        cam_level_metrics = defaultdict(float)
        pc_count = 0
        cam_count_correct_samples = 0
        cam_count_total_samples = 0
        
        for pc_name in pc_names:
            pred_intervals = build_occupancy_intervals_from_detail(detail_records, pc_name, debounce_sec=2.0)
            gt_intervals = build_gt_occupancy_intervals(gt_lookup, pc_name, video_end_ts)
            
            if not gt_intervals:
                continue
            
            metrics = compute_duration_metrics(detail_records, gt_lookup, pc_name, video_end_ts)
            if metrics is None:
                continue
            
            pc_count += 1
            all_summary_rows.append({
                "cam_name": cam_name,
                "pc_name": pc_name,
                "model_name": detail_df["model_name"].iloc[0] if len(detail_df) > 0 else "unknown",
                **metrics,
            })
            
            # Accumulate for camera-level
            cam_level_metrics["gt_occupied_sec"] += metrics["gt_occupied_sec"]
            cam_level_metrics["overlap_sec"] += metrics["overlap_sec"]
            cam_level_metrics["over_occupancy_sec"] += metrics["over_occupancy_sec"]
            cam_level_metrics["missed_occupancy_sec"] += metrics["missed_occupancy_sec"]
            cam_count_correct_samples += int(metrics.get("count_correct_samples", 0))
            cam_count_total_samples += int(metrics.get("count_total_samples", 0))
        
        # Camera-level aggregation
        if pc_count > 0:
            gt_total = cam_level_metrics["gt_occupied_sec"]
            pred_total = cam_level_metrics["overlap_sec"] + cam_level_metrics["over_occupancy_sec"]
            coverage = cam_level_metrics["overlap_sec"] / gt_total if gt_total > 0 else 0.0
            
            all_summary_rows.append({
                "cam_name": cam_name,
                "pc_name": "ALL",
                "model_name": detail_df["model_name"].iloc[0] if len(detail_df) > 0 else "unknown",
                "gt_occupied_sec": round(gt_total, 2),
                "pred_occupied_sec": round(pred_total, 2),
                "overlap_sec": round(cam_level_metrics["overlap_sec"], 2),
                "coverage": round(coverage, 4),
                "occupied_accuracy_percent": round(coverage * 100.0, 2),
                "duration_error_sec": round(abs(pred_total - gt_total), 2),
                "duration_error_ratio": round(abs(pred_total - gt_total) / gt_total if gt_total > 0 else 0, 4),
                "over_occupancy_sec": round(cam_level_metrics["over_occupancy_sec"], 2),
                "missed_occupancy_sec": round(cam_level_metrics["missed_occupancy_sec"], 2),
                "gt_intervals": 0,
                "pred_intervals": 0,
                "count_accuracy_percent": round((100.0 * cam_count_correct_samples / cam_count_total_samples) if cam_count_total_samples > 0 else 0.0, 2),
                "count_correct_samples": int(cam_count_correct_samples),
                "count_total_samples": int(cam_count_total_samples),
            })
            
            print(f"  {pc_count} seats evaluated, camera {cam_name} coverage={coverage*100:.1f}%")
    
    # Write summary
    if all_summary_rows:
        summary_path = os.path.join(eval_log_root, "eval_summary_duration_based.csv")
        summary_columns = [
            "pc_name", "cam_name", "model_name", "gt_occupied_sec", "pred_occupied_sec", "overlap_sec",
            "coverage", "duration_error_sec", "duration_error_ratio", "over_occupancy_sec",
            "missed_occupancy_sec", "gt_intervals", "pred_intervals", "occupied_accuracy_percent", "count_accuracy_percent",
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
        
        print(f"\n=== Summary Saved ===")
        print(f"File: {summary_path}")
        print("\nTop 15 results (by coverage):")
        print("-" * 100)
        
        for row in sorted(all_summary_rows, key=lambda r: r.get("coverage", 0), reverse=True)[:15]:
            if row.get("pc_name") != "ALL":
                print(
                    f"{row['cam_name']:12} {row['pc_name']:6} | "
                    f"Coverage: {row['coverage']*100:6.1f}% | "
                    f"GT: {row['gt_occupied_sec']:8.0f}s | "
                    f"Pred: {row['pred_occupied_sec']:8.0f}s | "
                    f"Error: {row['duration_error_sec']:7.0f}s ({row['duration_error_ratio']*100:5.1f}%)"
                )
        
        print("\nCamera-level summaries:")
        print("-" * 100)
        for row in sorted(all_summary_rows, key=lambda r: r.get("cam_name", "")):
            if row.get("pc_name") == "ALL":
                print(
                    f"{row['cam_name']:12} ALL      | "
                    f"Coverage: {row['coverage']*100:6.1f}% | "
                    f"GT: {row['gt_occupied_sec']:8.0f}s | "
                    f"Pred: {row['pred_occupied_sec']:8.0f}s | "
                    f"Error: {row['duration_error_sec']:7.0f}s"
                )
        
        return True
    else:
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
