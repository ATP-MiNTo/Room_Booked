import asyncio
import glob
import os
import re
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# Hybrid API mode:
# - Realtime endpoints read from in-memory snapshot when available.
# - CSV is still used as persistent history and fallback source.

LOG_BASE_DIR = os.path.normpath(os.getenv("BOOKING_LOG_DIR", "logs"))
PC_STATE_CSV = os.path.join(LOG_BASE_DIR, "pc_state_all.csv")
PERF_SUMMARY_CSV = os.path.join(LOG_BASE_DIR, "performance_summary.csv")

PEOPLE_GLOB = os.path.join(LOG_BASE_DIR, "*", "people_with_conf_and_roi_*_*.csv")
PC_ACTIVITY_GLOB = os.path.join(LOG_BASE_DIR, "*", "pc_activity_events_*_*.csv")
UNATTENDED_GLOB = os.path.join(LOG_BASE_DIR, "pc_unattended_flags_*.csv")

DAY_TAG_PATTERN = re.compile(r"_(\d{8})\.csv$", re.IGNORECASE)

CSV_SYNC_INTERVAL_SEC = float(os.getenv("HYBRID_CSV_SYNC_INTERVAL_SEC", "0.5"))
MEMORY_STALE_SEC = float(os.getenv("HYBRID_MEMORY_STALE_SEC", "2.0"))
WS_PUSH_INTERVAL_SEC = float(os.getenv("HYBRID_WS_PUSH_INTERVAL_SEC", "1.0"))


app = FastAPI(
    title="Booking Log API (Hybrid)",
    description="Memory-first realtime API with CSV fallback and history endpoints.",
    version="1.0.0-hybrid",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PCStatusRowIn(BaseModel):
    pc_name: str
    pc_on: bool
    available: int = Field(default=0, ge=0, le=2)


class PCStatusPushPayload(BaseModel):
    rows: List[PCStatusRowIn]
    source: str = "external"


def normalize_label(value: Any) -> str:
    text = str(value or "").strip()
    cleaned = "".join((c if c.isalnum() or c in ("-", "_") else "_") for c in text)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_").lower()


def parse_date_to_day_tag(date_value: Optional[str]) -> Optional[str]:
    if date_value is None:
        return None

    text = str(date_value).strip()
    if not text:
        return None

    if re.fullmatch(r"\d{8}", text):
        return text

    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%Y%m%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD or YYYYMMDD.")


def day_tag_to_iso(day_tag: str) -> str:
    if not re.fullmatch(r"\d{8}", str(day_tag or "")):
        return str(day_tag or "")
    return f"{day_tag[0:4]}-{day_tag[4:6]}-{day_tag[6:8]}"


def extract_day_tag(file_path: str) -> Optional[str]:
    match = DAY_TAG_PATTERN.search(os.path.basename(file_path))
    return match.group(1) if match else None


def read_csv_safe(file_path: str) -> pd.DataFrame:
    if not os.path.exists(file_path):
        return pd.DataFrame()

    try:
        return pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read CSV: {file_path}. Error: {exc}")


def records_from_df(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    cleaned_df = df.where(pd.notnull(df), None)
    return cleaned_df.to_dict(orient="records")


def coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(int(value))
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "on"}


def pc_name_sort_key(pc_name: Any):
    text = str(pc_name or "")
    digits = "".join(ch for ch in text if ch.isdigit())
    number = int(digits) if digits else 10**9
    return number, text


def normalize_pc_status_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue

        pc_name = str(row.get("pc_name", "")).strip()
        if not pc_name:
            continue

        available_raw = row.get("available", row.get("availble", 0))
        available_num = pd.to_numeric(available_raw, errors="coerce")
        available_value = 0 if pd.isna(available_num) else int(available_num)
        if available_value < 0:
            available_value = 0
        elif available_value > 2:
            available_value = 2

        normalized.append(
            {
                "pc_name": pc_name,
                "pc_on": coerce_bool(row.get("pc_on")),
                "available": available_value,
            }
        )

    normalized.sort(key=lambda item: pc_name_sort_key(item.get("pc_name")))
    return normalized


def load_pc_status_rows_from_csv() -> List[Dict[str, Any]]:
    df = read_csv_safe(PC_STATE_CSV)
    if df.empty:
        return []

    if "availble" in df.columns and "available" not in df.columns:
        df = df.rename(columns={"availble": "available"})

    for col_name, default_value in (("pc_name", ""), ("pc_on", False), ("available", 0)):
        if col_name not in df.columns:
            df[col_name] = default_value

    return normalize_pc_status_rows(records_from_df(df))


def filter_files(glob_pattern: str, camera: Optional[str], day_tag: Optional[str]) -> List[str]:
    camera_filter = normalize_label(camera) if camera else None
    files = sorted(path for path in glob.glob(glob_pattern) if os.path.isfile(path))
    matched = []

    for file_path in files:
        if day_tag:
            file_day_tag = extract_day_tag(file_path)
            if file_day_tag != day_tag:
                continue

        if camera_filter:
            parent_label = normalize_label(os.path.basename(os.path.dirname(file_path)))
            if parent_label != camera_filter:
                continue

        matched.append(file_path)

    return matched


def apply_time_sort_and_limit(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    if "time" in df.columns:
        df = df.sort_values(by="time", ascending=False)
    if limit > 0:
        df = df.head(limit)
    return df


class HybridRealtimeStore:
    def __init__(self, sync_interval_sec: float, memory_stale_sec: float):
        self._sync_interval_sec = max(0.1, float(sync_interval_sec))
        self._memory_stale_sec = max(0.1, float(memory_stale_sec))

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker: Optional[threading.Thread] = None

        self._rows: List[Dict[str, Any]] = []
        self._last_update_epoch: Optional[float] = None
        self._last_source: str = "none"

    def start(self):
        self.refresh_from_csv(force=True)
        if self._worker and self._worker.is_alive():
            return

        self._stop_event.clear()
        self._worker = threading.Thread(target=self._run, name="hybrid-csv-sync", daemon=True)
        self._worker.start()

    def stop(self):
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=2.0)

    def _run(self):
        while not self._stop_event.is_set():
            self.refresh_from_csv(force=False)
            self._stop_event.wait(self._sync_interval_sec)

    def refresh_from_csv(self, force: bool = False):
        rows = load_pc_status_rows_from_csv()
        now_epoch = time.time()

        with self._lock:
            memory_is_fresh = (
                self._last_source.startswith("memory")
                and self._last_update_epoch is not None
                and (now_epoch - self._last_update_epoch) <= self._memory_stale_sec
            )
            if not force and memory_is_fresh:
                return

            self._rows = rows
            self._last_update_epoch = now_epoch
            self._last_source = "csv_sync"

    def set_memory_rows(self, rows: List[Dict[str, Any]], source: str = "memory"):
        normalized = normalize_pc_status_rows(rows)
        with self._lock:
            self._rows = normalized
            self._last_update_epoch = time.time()
            self._last_source = f"memory:{source}"

    def get_rows(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(row) for row in self._rows]

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            last_update_iso = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._last_update_epoch))
                if self._last_update_epoch
                else None
            )
            return {
                "rows": [dict(row) for row in self._rows],
                "source": self._last_source,
                "last_update_epoch": self._last_update_epoch,
                "last_update_iso": last_update_iso,
            }


hybrid_store = HybridRealtimeStore(
    sync_interval_sec=CSV_SYNC_INTERVAL_SEC,
    memory_stale_sec=MEMORY_STALE_SEC,
)


@app.on_event("startup")
def _on_startup():
    hybrid_store.start()


@app.on_event("shutdown")
def _on_shutdown():
    hybrid_store.stop()


@app.get("/")
def root() -> Dict[str, Any]:
    snapshot = hybrid_store.get_snapshot()
    return {
        "service": "booking-log-api-hybrid",
        "mode": "memory-first-with-csv-fallback",
        "log_base_dir": LOG_BASE_DIR,
        "realtime_source": snapshot.get("source"),
        "realtime_last_update": snapshot.get("last_update_iso"),
        "endpoints": [
            "/api/pc-status",
            "/api/hybrid/status",
            "/api/hybrid/push-pc-status",
            "/ws/pc-updates",
        ],
    }


@app.get("/api/hybrid/status")
def get_hybrid_status() -> Dict[str, Any]:
    snapshot = hybrid_store.get_snapshot()
    return {
        "mode": "hybrid",
        "source": snapshot.get("source"),
        "row_count": len(snapshot.get("rows", [])),
        "last_update": snapshot.get("last_update_iso"),
        "csv_sync_interval_sec": CSV_SYNC_INTERVAL_SEC,
        "memory_stale_sec": MEMORY_STALE_SEC,
    }


@app.post("/api/hybrid/push-pc-status")
def push_pc_status(payload: PCStatusPushPayload) -> Dict[str, Any]:
    rows = [
        {
            "pc_name": row.pc_name,
            "pc_on": row.pc_on,
            "available": row.available,
        }
        for row in payload.rows
    ]
    hybrid_store.set_memory_rows(rows, source=payload.source or "external")
    snapshot = hybrid_store.get_snapshot()
    return {
        "updated": len(rows),
        "source": snapshot.get("source"),
        "last_update": snapshot.get("last_update_iso"),
    }


@app.get("/api/pc-status")
def get_pc_status() -> List[Dict[str, Any]]:
    rows = hybrid_store.get_rows()
    if rows:
        return rows

    fallback_rows = load_pc_status_rows_from_csv()
    if fallback_rows:
        hybrid_store.set_memory_rows(fallback_rows, source="fallback_csv")
    return fallback_rows


@app.websocket("/ws/pc-updates")
async def websocket_pc_updates(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            snapshot = hybrid_store.get_snapshot()
            payload = {
                "type": "pc_status",
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "source": snapshot.get("source"),
                "data": snapshot.get("rows", []),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(max(0.1, WS_PUSH_INTERVAL_SEC))
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_hybrid:app", host="0.0.0.0", port=8000, reload=False)