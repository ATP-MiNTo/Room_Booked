import os
import psycopg2
import shutil
from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, date, time, timezone, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =================================================================
# การตั้งค่าที่เก็บรูปภาพ (บังคับให้ออกไปเซฟที่โฟลเดอร์ data ของโปรเจกต์หลัก)
# =================================================================
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
BASE_UPLOAD_DIR = os.path.join(ROOT_DIR, "data", "face_scanner")

if not os.path.exists(BASE_UPLOAD_DIR):
    os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)

# Mount path เพื่อให้หน้าเว็บเรียกดูรูปได้
app.mount("/data", StaticFiles(directory=os.path.join(ROOT_DIR, "data")), name="data")


def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=os.getenv("DB_PORT", 5432)
    )


class Reservation(BaseModel):
    seat_id: int 
    student_id: str
    user_name: str 
    reserve_date: date 
    start_time: time 
    end_time: time 


@app.get("/booked-seats")
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


@app.post("/reserve-with-image")
def reserve_with_image(
    seat_id: int = Form(...),
    student_id: str = Form(...),
    user_name: str = Form(...),
    reserve_date: date = Form(...),
    start_time: time = Form(...),
    end_time: time = Form(...),
    purpose: str = Form("ไม่ระบุ"),
    image: UploadFile = File(...)
):
    thai_tz = timezone(timedelta(hours=7))
    now = datetime.now(thai_tz)

    start_dt = datetime.combine(reserve_date, start_time).replace(tzinfo=thai_tz)
    end_dt = datetime.combine(reserve_date, end_time).replace(tzinfo=thai_tz)

    if start_dt <= now:
        raise HTTPException(status_code=400, detail="ไม่สามารถจองย้อนหลังได้")

    # =================================================================
    # การบันทึกรูปภาพ (สร้างโฟลเดอร์รายวัน)
    # =================================================================
    # 1. สร้างโฟลเดอร์ของวันนี้ (เช่น 2026-02-27)
    today_folder = now.strftime("%Y-%m-%d")
    daily_upload_dir = os.path.join(BASE_UPLOAD_DIR, today_folder)
    
    if not os.path.exists(daily_upload_dir):
        os.makedirs(daily_upload_dir, exist_ok=True)

    date_str = reserve_date.strftime("%Y%m%d")
    start_str = start_time.strftime("%H%M")
    end_str = end_time.strftime("%H%M")
    
    file_ext = image.filename.split(".")[-1] if "." in image.filename else "jpg"
    
    # 2. ชื่อไฟล์ (สิ่งที่จะถูกบันทึกลง Database เพียวๆ)
    filename = f"{date_str}_Seat{seat_id:02d}_{start_str}_{end_str}_{student_id}.{file_ext}"
    
    # 3. ที่อยู่จริงบนคอมพิวเตอร์ที่จะเอาไฟล์ไปวาง (เซฟลงในโฟลเดอร์รายวัน)
    file_path = os.path.join(daily_upload_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # =================================================================
    # การบันทึกข้อมูลลงฐานข้อมูล (Database)
    # =================================================================
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("BEGIN;")

        name_parts = user_name.strip().split(" ")
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        major = "ไม่ระบุ" 

        cur.execute("""
            INSERT INTO student_info (student_id, first_name, last_name, major)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (student_id) DO UPDATE 
            SET first_name = EXCLUDED.first_name, 
                last_name = EXCLUDED.last_name, 
                major = EXCLUDED.major;
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

        # บันทึกแค่ตัวแปร filename ลงไปในช่อง image_path
        cur.execute("""
            INSERT INTO reservations (student_id, seat_no, start_time, end_time, purpose, image_path)
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


@app.get("/reservations")
def get_all_reservations():
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT seat_no, start_time, end_time, image_path
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


@app.get("/")
def health():
    return {"status": "API running"}