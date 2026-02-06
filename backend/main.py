import os
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, date, time, timezone, timedelta

app = FastAPI()

# =============================
# CORS (สำหรับ Vite React)
# =============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# Database Connection
# =============================
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=os.getenv("DB_PORT", 5432)
    )

# =============================
# Schema ให้ตรงกับ App.jsx
# =============================
class Reservation(BaseModel):
    seat_id: int
    user_name: str
    user_email: str
    reserve_date: date
    start_time: time
    end_time: time


# =============================
# API Reserve
# =============================
@app.post("/reserve")
def reserve(req: Reservation):

    # ===== ใช้ timezone ไทย (+7) =====
    thai_tz = timezone(timedelta(hours=7))

    now = datetime.now(thai_tz)

    reserve_datetime = datetime.combine(
        req.reserve_date,
        req.start_time
    ).replace(tzinfo=thai_tz)

    # ===== ล็อคไม่ให้จองย้อนหลัง =====
    if reserve_datetime <= now:
        raise HTTPException(
            status_code=400,
            detail="ไม่สามารถจองเวลาย้อนหลังได้"
        )

    conn = get_db()
    cur = conn.cursor()

    try:
        # ===== เช็คเวลาชน =====
        cur.execute("""
            SELECT 1 FROM reservations
            WHERE seat_id = %s
              AND reserve_date = %s
              AND start_time < %s
              AND end_time > %s
        """, (
            req.seat_id,
            req.reserve_date,
            req.end_time,
            req.start_time
        ))

        if cur.fetchone():
            raise HTTPException(
                status_code=409,
                detail="ที่นั่งนี้ถูกจองแล้ว"
            )

        # ===== INSERT =====
        cur.execute("""
            INSERT INTO reservations
            (seat_id, user_name, user_email,
             reserve_date, start_time, end_time)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            req.seat_id,
            req.user_name,
            req.user_email,
            req.reserve_date,
            req.start_time,
            req.end_time
        ))

        conn.commit()

        return {"message": "จองสำเร็จ"}

    finally:
        cur.close()
        conn.close()
