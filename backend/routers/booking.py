import os
import shutil
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, HTTPException, Query, File, UploadFile, Form 
from pydantic import BaseModel
from datetime import datetime, date, time, timezone, timedelta

from database import get_db

# ตั้งค่า Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dxnogh96j"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "367479691313863"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "TmEl9PP-xty69Y12jMKic6niE7g")
)

router = APIRouter()

ROUTERS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(ROUTERS_DIR)
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

# ==========================================
# 🟢 Helper Function: คำนวณปีการศึกษาปัจจุบัน และชั้นปี
# ==========================================
def get_current_academic_year_helper(cur):
    now = datetime.now()
    today_date = now.date()
    
    cur.execute("""
        SELECT academic_year 
        FROM academic_semesters 
        WHERE start_date <= %s AND end_date >= %s
        ORDER BY start_date DESC LIMIT 1
    """, (today_date, today_date))
    row = cur.fetchone()
    
    if row:
        return row[0] 
    
    thai_year = now.year + 543
    if now.month > 8 or (now.month == 8 and now.day > 10):
        return thai_year
    else:
        return thai_year - 1

# ฟังก์ชันคำนวณชั้นปีสำหรับตารางข้อมูลนักศึกษาและประวัติ
def get_year_level(student_id, current_year):
    student_id = str(student_id).strip()
    if len(student_id) != 10 or not student_id.startswith('1') or not student_id.isdigit():
        return "Error"
    try:
        entry_year = 2500 + int(student_id[1:3])
        yl = current_year - entry_year + 1
        if yl == 1: return "ปี 1"
        elif yl == 2: return "ปี 2"
        elif yl == 3: return "ปี 3"
        elif yl == 4: return "ปี 4"
        elif 5 <= yl <= 9: return "ปี 5++"
        elif yl >= 10: return "รีไทร์"
        else: return "Error"
    except:
        return "Error"

@router.get("/api/current-academic-year")
def api_get_current_academic_year():
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        year = get_current_academic_year_helper(cur)
        return {"current_academic_year": year}
    except Exception as e:
        now = datetime.now()
        thai_year = now.year + 543
        fallback_year = thai_year if now.month > 8 or (now.month == 8 and now.day > 10) else thai_year - 1
        return {"current_academic_year": fallback_year}
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/booked-seats")
def get_booked_seats(
    reserve_date: date = Query(...),
    start_time: time = Query(...),
    end_time: time = Query(...)
):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        start_dt = datetime.combine(reserve_date, start_time)
        end_dt = datetime.combine(reserve_date, end_time)
        
        seat_statuses = {}

        cur.execute("""
            SELECT DISTINCT seat_no
            FROM reservations
            WHERE start_time < %s AND end_time > %s
        """, (end_dt, start_dt))
        for row in cur.fetchall():
            seat_statuses[str(row[0])] = {"status": "booked", "reason": "มีผู้จองแล้ว"}

        days_map = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        target_day = days_map[reserve_date.weekday()] 

        cur.execute("""
            SELECT seat_no, purpose, subject_name, section, teacher_name
            FROM lab_schedules
            WHERE 
              (
                (start_date <= %s AND end_date >= %s AND day_of_week = %s)
                OR 
                (start_date = %s AND end_date = %s)
              )
              AND start_time < %s AND end_time > %s
        """, (reserve_date, reserve_date, target_day, reserve_date, reserve_date, end_time, start_time))
        
        for row in cur.fetchall():
            seat_no = row[0]
            purpose = row[1]
            subject = row[2]
            section = row[3]
            teacher = row[4]
            
            reason_text = purpose
            if subject and subject != "-":
                reason_text = f"วิชา {subject}"
                if section and section != "-":
                    reason_text += f" Sec.{section}"
                if teacher and teacher != "-":
                    reason_text += f" ({teacher})"

            if seat_no is None: 
                for i in range(1, 31):
                    seat_statuses[str(i)] = {"status": "locked", "reason": reason_text}
            else:
                seat_statuses[str(seat_no)] = {"status": "locked", "reason": reason_text}

        cur.execute("SELECT seat_no, note FROM broken_seats WHERE status = 'broken'")
        for row in cur.fetchall():
            seat_statuses[str(row[0])] = {"status": "broken", "reason": row[1]}

        return seat_statuses

    except Exception as e:
        print(f"DATABASE ERROR (GET /booked-seats): {e}")
        raise HTTPException(status_code=500, detail="ไม่สามารถตรวจสอบสถานะที่นั่งได้")
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ==========================================
# 🟢 API: จองที่นั่งพร้อมแนบรูปภาพใบหน้า (เพิ่ม Validation อย่างละเอียด)
# ==========================================
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
    student_id = student_id.strip()
    
    # 1. เช็ครูปแบบรหัสนักศึกษา (10 หลัก เริ่มด้วย 1)
    if len(student_id) != 10 or not student_id.startswith('1') or not student_id.isdigit():
        raise HTTPException(status_code=400, detail="รหัสนักศึกษาไม่ถูกต้อง (ต้องเป็นตัวเลข 10 หลัก และขึ้นต้นด้วย 1)")

    thai_tz = timezone(timedelta(hours=7))
    now = datetime.now(thai_tz)
    start_dt = datetime.combine(reserve_date, start_time).replace(tzinfo=thai_tz)
    end_dt = datetime.combine(reserve_date, end_time).replace(tzinfo=thai_tz)

    if end_dt <= now:
        raise HTTPException(status_code=400, detail="ไม่สามารถจองรอบที่เวลาสิ้นสุดไปแล้วได้")
    if start_dt < now and (now - start_dt).total_seconds() > 1800:
        raise HTTPException(status_code=400, detail="ไม่สามารถจองย้อนหลังเกิน 30 นาทีได้")

    name_parts = user_name.strip().split(" ")
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("BEGIN;")

        # 2. ตรวจสอบความถูกต้องของข้อมูลในระบบ (Cross-check)
        cur.execute("SELECT first_name, last_name, major FROM student_info WHERE student_id = %s", (student_id,))
        existing_student = cur.fetchone()
        
        if existing_student:
            db_fname, db_lname, db_major = existing_student
            if db_fname != first_name or db_lname != last_name or db_major != major:
                raise HTTPException(status_code=400, detail="ข้อมูล ชื่อ, นามสกุล หรือ สาขา ไม่ตรงกับรหัสนักศึกษานี้ในระบบ (หากมีการเปลี่ยนแปลง โปรดติดต่อผู้ดูแลระบบ)")
        else:
            # ถ้ารหัสนี้ยังไม่มีในระบบ เช็คต่อว่าชื่อ/สาขานี้ ไปซ้ำกับรหัสอื่นที่มีอยู่แล้วหรือไม่
            cur.execute("SELECT student_id FROM student_info WHERE first_name = %s AND last_name = %s AND major = %s", (first_name, last_name, major))
            existing_name = cur.fetchone()
            if existing_name:
                raise HTTPException(status_code=400, detail=f"พบข้อมูลชื่อ-นามสกุลนี้ ผูกกับรหัสนักศึกษาอื่นในระบบแล้ว ({existing_name[0]})")

        # บันทึก / อัปเดตข้อมูลนักศึกษา
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

        # เช็คการจองซ้ำ
        cur.execute("""
            SELECT 1 FROM reservations
            WHERE seat_no = %s AND start_time < %s AND end_time > %s
            FOR UPDATE
        """, (seat_id, end_naive, start_naive))

        if cur.fetchone():
            raise HTTPException(status_code=409, detail="ที่นั่งนี้ถูกจองไปแล้ว กรุณาเลือกรอบเวลาอื่น")
        
        # จัดการไฟล์รูปภาพ
        date_str = reserve_date.strftime("%Y%m%d")
        start_str = start_time.strftime("%H%M")
        end_str = end_time.strftime("%H%M")
        public_id = f"face_scanner/{reserve_date.strftime('%Y-%m-%d')}/{date_str}_Seat{seat_id:02d}_{start_str}_{end_str}_{student_id}"
        image_data = image.file.read()

        # Upload ไป Cloudinary
        upload_result = cloudinary.uploader.upload(
            image_data,
            public_id=public_id,
            overwrite=True,
            resource_type="image"
        )
        image_url = upload_result["secure_url"]

        cur.execute("""
            INSERT INTO reservations (student_id, seat_no, start_time, end_time, purpose, image_name)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (student_id, seat_id, start_naive, end_naive, purpose, image_url))

        conn.commit()

        return {"message": "จองสำเร็จ", "image_filename": image_url}

    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        print(f"DATABASE ERROR (POST /reserve-with-image): {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ─────────────────────────────────────────────────────────────────
# Admin: บังคับยกเลิกการจอง (Force End)
# DELETE /api/reservations/{id}
# ─────────────────────────────────────────────────────────────────
@router.delete("/api/reservations/{reservation_id}")
def delete_reservation(reservation_id: int):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM reservations WHERE id = %s RETURNING id",
            (reservation_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"ไม่พบการจอง id={reservation_id}")
        conn.commit()
        return {"message": "ยกเลิกการจองเรียบร้อยแล้ว", "id": reservation_id}
    except HTTPException:
        raise
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ─────────────────────────────────────────────────────────────────
# Endpoint สำหรับระบบกล้อง: อัปเดตสถานะการเข้านั่งของการจอง
# PATCH /api/reservations/{reservation_id}/attendance
# Body: { "status": "present" | "absent" }
# ─────────────────────────────────────────────────────────────────
from pydantic import BaseModel as _BaseModel

class AttendanceUpdate(_BaseModel):
    status: str  # "present" | "absent"

@router.patch("/api/reservations/{reservation_id}/attendance")
def update_attendance(reservation_id: int, body: AttendanceUpdate):
    if body.status not in ("present", "absent"):
        raise HTTPException(status_code=400, detail="status ต้องเป็น 'present' หรือ 'absent' เท่านั้น")
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE reservations SET attended_status = %s WHERE id = %s RETURNING id",
            (body.status, reservation_id)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"ไม่พบการจอง id={reservation_id}")
        conn.commit()
        return {"id": reservation_id, "attended_status": body.status, "message": "อัปเดตสำเร็จ"}
    except HTTPException:
        raise
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()


@router.get("/reservations")
def get_all_reservations():
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        current_year = get_current_academic_year_helper(cur)

        cur.execute("""
            SELECT r.id, r.seat_no, r.start_time, r.end_time, r.student_id, r.image_name,
                   s.first_name, s.last_name, s.major, r.purpose, r.attended_status
            FROM reservations r
            LEFT JOIN student_info s ON r.student_id = s.student_id
            ORDER BY r.start_time DESC
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "seat_id": r[1], "reserve_date": str(r[2].date()) if r[2] else None,
                "start_time": str(r[2].time()) if r[2] else None, "end_time": str(r[3].time()) if r[3] else None,
                "student_id": r[4], "image_filename": r[5], "first_name": r[6] or "ไม่ระบุ",
                "last_name": r[7] or "", "major": r[8] or "ไม่ระบุ", "purpose": r[9] or "ไม่ระบุ",
                "year_level": get_year_level(r[4], current_year), "attended_status": r[10]
            } for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/students")
def get_all_students():
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        current_year = get_current_academic_year_helper(cur)

        cur.execute("SELECT student_id, first_name, last_name, major FROM student_info ORDER BY student_id ASC")
        rows = cur.fetchall()
        return [
            {
                "student_id": r[0], "first_name": r[1], "last_name": r[2], "major": r[3],
                "year_level": get_year_level(r[0], current_year)
            } for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/students/{student_id}/reservations")
def get_student_reservations(student_id: str):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, seat_no, start_time, end_time, purpose, image_name, attended_status
            FROM reservations WHERE student_id = %s ORDER BY start_time DESC
        """, (student_id,))
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "seat_id": r[1], "reserve_date": str(r[2].date()) if r[2] else None,
                "start_time": str(r[2].time()) if r[2] else None, "end_time": str(r[3].time()) if r[3] else None,
                "purpose": r[4] or "ไม่ระบุ", "image_filename": r[5], "attended_status": r[6]
            } for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/active-bookings")
def get_active_bookings():
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        thai_tz = timezone(timedelta(hours=7))
        now = datetime.now(thai_tz).replace(tzinfo=None)
        
        cur.execute("SELECT DISTINCT seat_no FROM reservations WHERE start_time <= %s AND end_time > %s", (now, now))
        rows = cur.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="ไม่สามารถดึงข้อมูลการใช้งานปัจจุบันได้")
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/bookings/range")
def get_bookings_range(
    start: str = Query(None), end: str = Query(None),
    month: str = Query(None), year: str = Query(None),
    major: str = Query(None)
):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        base_query = """
            SELECT DATE(r.start_time) as reserve_date, COUNT(*) as total
            FROM reservations r LEFT JOIN student_info s ON r.student_id = s.student_id WHERE 1=1
        """
        params = []
        if major:
            base_query += " AND s.major = %s"
            params.append(major)
        if year:
            base_query += " AND TO_CHAR(r.start_time, 'YYYY') = %s"
            params.append(year)
        elif month:
            base_query += " AND TO_CHAR(r.start_time, 'YYYY-MM') = %s"
            params.append(month)
        elif start and end:
            base_query += " AND DATE(r.start_time) >= %s AND DATE(r.start_time) <= %s"
            params.append(start)
            params.append(end)

        base_query += " GROUP BY DATE(r.start_time) ORDER BY DATE(r.start_time)"
        cur.execute(base_query, params)
        rows = cur.fetchall()

        results = []
        for row in rows:
            date_val = str(row[0])
            total = row[1]
            if year:
                # group by month for yearly view
                results.append({"date": date_val, "total": total})
            elif month:
                day_val = date_val.split('-')[2]
                results.append({"day": day_val, "total": total, "date": date_val})
            else:
                results.append({"date": date_val, "total": total})
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail="ไม่สามารถดึงข้อมูลสถิติได้")
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/analytics/kpi")
def get_analytics_kpi(period: str = Query("week"), ref_date: str = Query(None), ref_week: str = Query(None), ref_month: str = Query(None), ref_year: str = Query(None)):
    """
    period: today | week | month | year
    ref_date:  YYYY-MM-DD  (today mode)
    ref_week:  YYYY-Www    (week mode, e.g. 2026-W15)
    ref_month: YYYY-MM     (month mode)
    ref_year:  YYYY        (year mode)
    """
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        thai_tz = timezone(timedelta(hours=7))
        now = datetime.now(thai_tz).replace(tzinfo=None)

        if period == "today":
            if ref_date:
                d = datetime.strptime(ref_date, "%Y-%m-%d")
            else:
                d = now
            start_cur = d.replace(hour=0, minute=0, second=0, microsecond=0)
            end_cur   = start_cur + timedelta(days=1)
            start_prev = start_cur - timedelta(days=1)
            end_prev   = start_cur

        elif period == "week":
            if ref_week:
                # parse ISO week e.g. "2026-W15"
                parts = ref_week.split("-W")
                yr, wk = int(parts[0]), int(parts[1])
                start_cur = datetime.strptime(f"{yr}-W{wk:02d}-1", "%Y-W%W-%w")
            else:
                start_cur = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end_cur   = start_cur + timedelta(weeks=1)
            start_prev = start_cur - timedelta(weeks=1)
            end_prev   = start_cur

        elif period == "month":
            if ref_month:
                parts = ref_month.split("-")
                yr, mo = int(parts[0]), int(parts[1])
                start_cur = datetime(yr, mo, 1)
            else:
                start_cur = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start_cur.month == 12:
                end_cur = datetime(start_cur.year + 1, 1, 1)
            else:
                end_cur = datetime(start_cur.year, start_cur.month + 1, 1)
            # prev month
            if start_cur.month == 1:
                start_prev = datetime(start_cur.year - 1, 12, 1)
            else:
                start_prev = datetime(start_cur.year, start_cur.month - 1, 1)
            end_prev = start_cur

        else:  # year
            yr = int(ref_year) if ref_year else now.year
            start_cur  = datetime(yr, 1, 1)
            end_cur    = datetime(yr + 1, 1, 1)
            start_prev = datetime(yr - 1, 1, 1)
            end_prev   = start_cur

        # cap end_cur ที่ now → ไม่นับการจองในอนาคต
        end_cur_capped = min(end_cur, now) if start_cur <= now else start_cur

        def count_by_status(s, e, status=None):
            if status:
                cur.execute(
                    "SELECT COUNT(*) FROM reservations WHERE start_time >= %s AND start_time < %s AND attended_status = %s",
                    (s, e, status)
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM reservations WHERE start_time >= %s AND start_time < %s",
                    (s, e)
                )
            return cur.fetchone()[0]

        # นับเฉพาะการจองที่ผ่านมาแล้ว (ตัด future bookings ออก)
        total_cur      = count_by_status(start_cur, end_cur_capped)
        total_prev     = count_by_status(start_prev, end_prev)
        present_cur    = count_by_status(start_cur, end_cur_capped, "present")
        present_prev   = count_by_status(start_prev, end_prev, "present")
        absent_cur     = count_by_status(start_cur, end_cur_capped, "absent")
        absent_prev    = count_by_status(start_prev, end_prev, "absent")

        cur.execute("SELECT COUNT(*) FROM broken_seats WHERE status = 'broken'")
        broken = cur.fetchone()[0]

        cur.execute("SELECT seat_no, note, broken_date FROM broken_seats WHERE status = 'broken' ORDER BY broken_date DESC LIMIT 10")
        broken_list = [{"seat_no": f"PC{str(r[0]).zfill(2)}", "note": r[1], "date": str(r[2].date()) if r[2] else ""} for r in cur.fetchall()]

        def trend(cur_val, prev_val):
            diff = cur_val - prev_val
            pct  = round((diff / prev_val * 100), 1) if prev_val > 0 else 0.0
            return diff, pct

        diff_total,   pct_total   = trend(total_cur,   total_prev)
        diff_present, pct_present = trend(present_cur, present_prev)
        diff_absent,  pct_absent  = trend(absent_cur,  absent_prev)

        return {
            "totalReservations":  total_cur,   "trendCount":        diff_total,   "trendPct":     pct_total,
            "broken": broken, "brokenList": broken_list,
            "totalNormal":        present_cur,  "trendNormalCount":  diff_present, "trendNormal":  pct_present,
            "totalNoShow":        absent_cur,   "trendNoShowCount":  diff_absent,  "trendNoShow":  pct_absent,
            "totalWalkin": 0, "trendWalkinCount": 0, "trendWalkin": 0.0
        }
    except Exception as e:
        print(f"KPI ERROR: {e}")
        raise HTTPException(status_code=500, detail="ไม่สามารถดึง KPI ได้")
    finally:
        if cur: cur.close()
        if conn: conn.close()

def _build_date_filter(params, month=None, year=None, start=None, end=None, table_prefix=""):
    """Helper: returns WHERE clause snippet and appends to params list"""
    col = f"{table_prefix}start_time" if table_prefix else "start_time"
    if year:
        clause = f" AND TO_CHAR({col}, 'YYYY') = %s"
        params.append(year)
    elif month:
        clause = f" AND TO_CHAR({col}, 'YYYY-MM') = %s"
        params.append(month)
    elif start and end:
        clause = f" AND DATE({col}) >= %s AND DATE({col}) <= %s"
        params += [start, end]
    else:
        clause = ""
    return clause

@router.get("/api/analytics/seat-usage")
def get_seat_usage(start: str = Query(None), end: str = Query(None), month: str = Query(None), year: str = Query(None)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        params = []
        clause = _build_date_filter(params, month=month, year=year, start=start, end=end)
        query = f"SELECT seat_no, COUNT(*) as usage FROM reservations WHERE 1=1{clause} GROUP BY seat_no ORDER BY usage DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        return [{"name": f"PC{str(r[0]).zfill(2)}", "usage": r[1]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="ไม่สามารถดึงสถิติที่นั่งได้")
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/analytics/peak-hours")
def get_peak_hours(start: str = Query(None), end: str = Query(None), month: str = Query(None), year: str = Query(None)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        params = []
        clause = _build_date_filter(params, month=month, year=year, start=start, end=end)
        query = f"SELECT EXTRACT(HOUR FROM start_time) as hour, COUNT(*) as users FROM reservations WHERE 1=1{clause} GROUP BY hour ORDER BY hour"
        cur.execute(query, params)
        rows = cur.fetchall()
        return [{"time": f"{int(r[0]):02d}:00", "users": r[1]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="ไม่สามารถดึง peak hours ได้")
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/analytics/by-major")
def get_by_major(start: str = Query(None), end: str = Query(None), month: str = Query(None), year: str = Query(None)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        params = []
        clause = _build_date_filter(params, month=month, year=year, start=start, end=end, table_prefix="r.")
        query = f"SELECT COALESCE(s.major, 'ไม่ระบุ') as major, COUNT(*) as total FROM reservations r LEFT JOIN student_info s ON r.student_id = s.student_id WHERE 1=1{clause} GROUP BY major ORDER BY total DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        return [{"major": r[0], "total": r[1]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="ไม่สามารถดึงข้อมูลสาขาได้")
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/analytics/by-year")
def get_by_year(start: str = Query(None), end: str = Query(None), month: str = Query(None), year: str = Query(None)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        params = []
        clause = _build_date_filter(params, month=month, year=year, start=start, end=end, table_prefix="r.")
        query = f"SELECT s.student_id, COUNT(*) as total FROM reservations r JOIN student_info s ON r.student_id = s.student_id WHERE s.student_id IS NOT NULL{clause} GROUP BY s.student_id"
        cur.execute(query, params)
        rows = cur.fetchall()

        current_academic_year = get_current_academic_year_helper(cur)
        year_counts = {"ปี 1": 0, "ปี 2": 0, "ปี 3": 0, "ปี 4": 0, "ปี 5++": 0, "รีไทร์": 0, "Error": 0}

        for row in rows:
            student_id = str(row[0]).strip()
            count = row[1]
            yl_text = get_year_level(student_id, current_academic_year)
            if yl_text in year_counts:
                year_counts[yl_text] += count
            else:
                year_counts["Error"] += count

        result = [{"year": k, "total": v} for k, v in year_counts.items() if v > 0]
        order = {"ปี 1":1, "ปี 2":2, "ปี 3":3, "ปี 4":4, "ปี 5++":5, "รีไทร์":6, "Error":7}
        result.sort(key=lambda x: order.get(x["year"], 99))
        return result
    except Exception as e:
        print(f"DATABASE ERROR (GET /api/analytics/by-year): {e}")
        raise HTTPException(status_code=500, detail="ไม่สามารถดึงข้อมูลชั้นปีได้")
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ==========================================
# API: จัดการข้อมูลนักศึกษา (Edit & Delete)
# ==========================================
class EditStudentRequest(BaseModel):
    first_name: str
    last_name: str
    major: str

@router.put("/api/students/{student_id}")
def update_student(student_id: str, req: EditStudentRequest):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE student_info 
            SET first_name = %s, last_name = %s, major = %s
            WHERE student_id = %s
        """, (req.first_name, req.last_name, req.major, student_id))
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูลนักศึกษารหัสนี้")
            
        conn.commit()
        return {"message": "อัปเดตข้อมูลสำเร็จ"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.delete("/api/students/{student_id}")
def delete_student(student_id: str):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM student_info WHERE student_id = %s", (student_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูลนักศึกษารหัสนี้")

        cur.execute("DELETE FROM reservations WHERE student_id = %s", (student_id,))
        cur.execute("DELETE FROM student_info WHERE student_id = %s", (student_id,))
            
        conn.commit()
        return {"message": "ลบข้อมูลสำเร็จ"}
    except HTTPException:
        raise
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()
