import os
import shutil
import json
import asyncio # 👉 เพิ่ม asyncio สำหรับทำงานเบื้องหลัง
from fastapi import APIRouter, HTTPException, Query, File, UploadFile, Form, WebSocket, WebSocketDisconnect 
from pydantic import BaseModel
from datetime import datetime, date, time, timezone, timedelta

from database import get_db

router = APIRouter()

# =================================================================
# การตั้งค่าที่เก็บรูปภาพ
# =================================================================
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
BASE_UPLOAD_DIR = os.path.join(ROOT_DIR, "data", "face_scanner")

if not os.path.exists(BASE_UPLOAD_DIR):
    os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)

class Reservation(BaseModel):
    seat_id: int 
    student_id: str
    user_name: str 
    reserve_date: date 
    start_time: time 
    end_time: time 

@router.get("/booked-seats")
def get_booked_seats(
    reserve_date: date = Query(...),
    start_time: time = Query(...),
    end_time: time = Query(...)
):
    conn = get_db()
    cur = conn.cursor()
    try:
        start_dt = datetime.combine(reserve_date, start_time)
        end_dt = datetime.combine(reserve_date, end_time)

        cur.execute("""
            SELECT DISTINCT seat_no
            FROM reservations
            WHERE start_time < %s AND end_time > %s
        """, (end_dt, start_dt))
        
        rows = cur.fetchall()
        return [str(row[0]) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.post("/reserve-with-image")
def reserve_with_image(
    seat_id: int = Form(...),
    student_id: str = Form(...),
    user_name: str = Form(...),
    reserve_date: date = Form(...),
    start_time: time = Form(...),
    end_time: time = Form(...),
    major: str = Form("ไม่ระบุ"),
    purpose: str = Form("ไม่ระบุ"),
    image: UploadFile = File(...)
):
    thai_tz = timezone(timedelta(hours=7))
    now = datetime.now(thai_tz)

    start_dt = datetime.combine(reserve_date, start_time).replace(tzinfo=thai_tz)
    end_dt = datetime.combine(reserve_date, end_time).replace(tzinfo=thai_tz)

    if start_dt <= now:
        raise HTTPException(status_code=400, detail="ไม่สามารถจองย้อนหลังได้")

    today_folder = now.strftime("%Y-%m-%d")
    daily_upload_dir = os.path.join(BASE_UPLOAD_DIR, today_folder)
    
    if not os.path.exists(daily_upload_dir):
        os.makedirs(daily_upload_dir, exist_ok=True)

    date_str = reserve_date.strftime("%Y%m%d")
    start_str = start_time.strftime("%H%M")
    end_str = end_time.strftime("%H%M")
    
    file_ext = image.filename.split(".")[-1] if "." in image.filename else "jpg"
    
    filename = f"{date_str}_Seat{seat_id:02d}_{start_str}_{end_str}_{student_id}.{file_ext}"
    file_path = os.path.join(daily_upload_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("BEGIN;")

        name_parts = user_name.strip().split(" ")
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        cur.execute("""
            INSERT INTO student_info (student_id, first_name, last_name, major)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (student_id) DO UPDATE 
            SET first_name = EXCLUDED.first_name, 
                last_name = EXCLUDED.last_name, 
                major = EXCLUDED.major
        """, (student_id, first_name, last_name, major))

        start_naive = start_dt.replace(tzinfo=None)
        end_naive = end_dt.replace(tzinfo=None)

        cur.execute("""
            SELECT 1 FROM reservations
            WHERE seat_no = %s AND start_time < %s AND end_time > %s
            FOR UPDATE
        """, (seat_id, end_naive, start_naive))

        if cur.fetchone():
            raise HTTPException(status_code=409, detail="ที่นั่งนี้ถูกจองแล้ว")
        
        cur.execute("""
            INSERT INTO reservations (student_id, seat_no, start_time, end_time, purpose, image_name)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (student_id, seat_id, start_naive, end_naive, purpose, filename))

        conn.commit()

        return {
            "message": "จองสำเร็จ",
            "image_filename": filename
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/reservations")
def get_all_reservations():
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT seat_no, start_time, end_time, image_name
            FROM reservations
            ORDER BY start_time
        """)
        rows = cur.fetchall()

        return [
            {
                "seat_id": r[0], 
                "reserve_date": r[1].date() if r[1] else None, 
                "start_time": str(r[1].time()) if r[1] else None, 
                "end_time": str(r[2].time()) if r[2] else None,
                "image_filename": r[3] 
            }
            for r in rows
        ]
    finally:
        cur.close()
        conn.close()


# =================================================================
# ระบบ WebSocket สำหรับล็อกที่นั่งชั่วคราว (สีเหลือง) พร้อมระบบตัดเวลา 4 นาที
# =================================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.locked_seats = {} 
        self.sweeper_task = None # 👉 ตัวแปรเก็บ รปภ. ดิจิทัล (Task)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_json({"type": "INIT", "data": list(self.locked_seats.keys())})

        # 👉 เริ่มเดินตรวจตราทันทีที่มีคนเปิดหน้าเว็บ (ถ้ายังไม่ได้เริ่ม)
        if self.sweeper_task is None:
            self.sweeper_task = asyncio.create_task(self.clear_expired_locks())

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

    # ✨ ฟังก์ชัน รปภ. ตรวจตราเวลาทุกๆ 10 วินาที ✨
    async def clear_expired_locks(self):
        while True:
            await asyncio.sleep(10) # รอ 10 วินาทีก่อนตรวจรอบถัดไป
            now = datetime.now()
            expired_keys = []
            
            # ตรวจสอบทุกโต๊ะที่ติดสีเหลืองอยู่
            for seat_key, lock_time in list(self.locked_seats.items()):
                # ถ้าเวลาผ่านไปเกิน 4 นาที (240 วินาที)
                if now - lock_time > timedelta(minutes=4):
                    expired_keys.append(seat_key)
                    
            # ทำการปลดล็อกโต๊ะที่หมดเวลา
            for key in expired_keys:
                if key in self.locked_seats:
                    del self.locked_seats[key]
                # ตะโกนบอกทุกคนในเว็บให้เอาสีเหลืองออก
                await self.broadcast({"type": "UNLOCK", "seat_key": key})


manager = ConnectionManager()

@router.websocket("/ws/seats")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")
            seat_key = payload.get("seat_key")

            if action == "lock":
                # 👉 บันทึกเวลาที่กดจองลงไปแทนค่า True แบบเก่า
                manager.locked_seats[seat_key] = datetime.now()
                await manager.broadcast({"type": "LOCK", "seat_key": seat_key})
            
            elif action == "unlock":
                if seat_key in manager.locked_seats:
                    del manager.locked_seats[seat_key]
                await manager.broadcast({"type": "UNLOCK", "seat_key": seat_key})

    except WebSocketDisconnect:
        manager.disconnect(websocket)