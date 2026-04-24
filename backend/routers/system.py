import json
import zipfile
import io
import os
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Query, Depends, Header
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from datetime import date, time, datetime
from typing import Optional, List
from database import get_db
from security import get_password_hash, verify_token

router = APIRouter()

ROUTERS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(ROUTERS_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
BASE_UPLOAD_DIR = os.getenv("FACE_DIR", "data/face_scanner")

def ensure_gregorian(d_input):
    if isinstance(d_input, date):
        if d_input.year >= 2400:
            try:
                return date(d_input.year - 543, d_input.month, d_input.day)
            except ValueError:
                return date(d_input.year - 543, d_input.month, d_input.day - 1)
        return d_input
    if isinstance(d_input, str):
        try:
            y, m, d = map(int, d_input.split('-'))
            if y >= 2400:
                return f"{y-543:04d}-{m:02d}-{d:02d}"
            return d_input
        except:
            return d_input
    return d_input

# ==========================================
# จัดการปีการศึกษาและภาคเรียน
# ==========================================
class SemesterRequest(BaseModel):
    academic_year: int
    semester: str
    start_date: date
    end_date: date

@router.post("/api/system/semesters")
def add_semester(req: SemesterRequest, admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        g_start = ensure_gregorian(req.start_date)
        g_end = ensure_gregorian(req.end_date)
        
        cur.execute("""
            INSERT INTO academic_semesters (academic_year, semester, start_date, end_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (academic_year, semester) 
            DO UPDATE SET start_date = EXCLUDED.start_date, end_date = EXCLUDED.end_date
        """, (req.academic_year, req.semester, g_start, g_end))
        conn.commit()
        return {"message": "บันทึกข้อมูลปีการศึกษาเรียบร้อย"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/system/semesters")
def get_semesters(admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, academic_year, semester, start_date, end_date 
            FROM academic_semesters 
            ORDER BY academic_year DESC, semester ASC
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "academic_year": r[1],
                "semester": r[2],
                "start_date": str(r[3]),
                "end_date": str(r[4])
            } for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.delete("/api/system/semesters/{sem_id}")
def delete_semester(sem_id: int, admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM academic_semesters WHERE id = %s", (sem_id,))
        conn.commit()
        return {"message": "ลบปีการศึกษาสำเร็จ"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ==========================================
# ตารางเรียน
# ==========================================
class LockSeatRequest(BaseModel):
    academic_year: Optional[int] = None
    semester: Optional[str] = None
    start_date: date
    end_date: date
    day_of_week: str
    start_time: time
    end_time: time
    is_all_seats: bool
    seat_nos: List[int] = []
    purpose: str
    subject_name: Optional[str] = None
    section: Optional[str] = None
    teacher_name: Optional[str] = None
    note: str = ""
    admin_id: str

@router.post("/api/system/lock-seats")
def lock_seats(req: LockSeatRequest, admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        g_start = ensure_gregorian(req.start_date)
        g_end = ensure_gregorian(req.end_date)
        
        if req.is_all_seats or not req.seat_nos:
            cur.execute("""
                INSERT INTO lab_schedules 
                (academic_year, semester, start_date, end_date, day_of_week, start_time, end_time, seat_no, purpose, subject_name, section, teacher_name, note, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s)
            """, (req.academic_year, req.semester, g_start, g_end, req.day_of_week, req.start_time, req.end_time, req.purpose, req.subject_name, req.section, req.teacher_name, req.note, req.admin_id))
        else:
            for seat in req.seat_nos:
                cur.execute("""
                    INSERT INTO lab_schedules 
                    (academic_year, semester, start_date, end_date, day_of_week, start_time, end_time, seat_no, purpose, subject_name, section, teacher_name, note, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (req.academic_year, req.semester, g_start, g_end, req.day_of_week, req.start_time, req.end_time, seat, req.purpose, req.subject_name, req.section, req.teacher_name, req.note, req.admin_id))
        
        conn.commit()
        return {"message": "บันทึกข้อมูลตารางเรียบร้อย"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/system/schedules")
def get_schedules(admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, academic_year, semester, start_date, end_date, day_of_week, start_time, end_time, seat_no, purpose, subject_name, section, teacher_name, note, created_by 
            FROM lab_schedules 
            ORDER BY start_date DESC, start_time DESC
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "academic_year": r[1],
                "semester": r[2],
                "start_date": str(r[3]),
                "end_date": str(r[4]),
                "day_of_week": r[5],
                "start_time": str(r[6]),
                "end_time": str(r[7]),
                "seat_no": r[8],
                "purpose": r[9],
                "subject_name": r[10] or "-",
                "section": r[11] or "-",
                "teacher_name": r[12] or "-",
                "note": r[13],
                "created_by": r[14]
            } for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.delete("/api/system/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM lab_schedules WHERE id = %s", (schedule_id,))
        conn.commit()
        return {"message": "ลบตารางสำเร็จ"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ==========================================
# เครื่องเสีย
# ==========================================
class BrokenReportRequest(BaseModel):
    seat_no: int
    note: str
    admin_id: str

@router.post("/api/system/report-broken")
def report_broken(req: BrokenReportRequest, admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO broken_seats (seat_no, note, status, reported_by)
            VALUES (%s, %s, 'broken', %s)
        """, (req.seat_no, req.note, req.admin_id))
        conn.commit()
        return {"message": "บันทึกแจ้งเครื่องเสียสำเร็จ"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

class ResolveBrokenRequest(BaseModel):
    broken_id: int
    admin_id: str
    fixed_date: str 

@router.post("/api/system/resolve-broken")
def resolve_broken(req: ResolveBrokenRequest, admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        g_fixed = ensure_gregorian(req.fixed_date)
        cur.execute("""
            UPDATE broken_seats 
            SET status = 'fixed', fixed_date = %s
            WHERE id = %s
        """, (g_fixed, req.broken_id))
        conn.commit()
        return {"message": "อัปเดตสถานะสำเร็จ"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/system/broken-seats")
def get_broken_seats(admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, seat_no, note, status, broken_date, reported_by, fixed_date
            FROM broken_seats 
            ORDER BY broken_date DESC
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "seat_no": r[1],
                "note": r[2],
                "status": r[3],
                "broken_date": str(r[4].strftime("%Y-%m-%d %H:%M:%S")),
                "reported_by": r[5],
                "fixed_date": str(r[6]) if r[6] else None
            } for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ==========================================
# สำรองข้อมูล, นำเข้า (Migration) และ ประวัติ (Logs)
# ==========================================
@router.get("/api/system/backup")
def backup_database(start_date: str = Query(...), end_date: str = Query(...), admin_id: str = Query(None), admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        backup_data = {}
        is_all_time = (start_date == "all" or end_date == "all")

        def fetch_table_safe(query, params=None):
            try:
                cur.execute("SAVEPOINT sp1")
                cur.execute(query, params or ())
                cols = [desc[0] for desc in cur.description]
                data = [dict(zip(cols, row)) for row in cur.fetchall()]
                cur.execute("RELEASE SAVEPOINT sp1")
                return data
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp1")
                print(f"Skipping query due to error: {e}")
                return []

        backup_data['admins'] = fetch_table_safe("SELECT staff_id, first_name, last_name, department, position, username, priority, created_at FROM admins")
        backup_data['academic_semesters'] = fetch_table_safe("SELECT * FROM academic_semesters")

        if is_all_time:
            backup_data['reservations'] = fetch_table_safe("SELECT * FROM reservations")
            backup_data['student_info'] = fetch_table_safe("SELECT * FROM student_info")
            backup_data['lab_schedules'] = fetch_table_safe("SELECT * FROM lab_schedules")
            backup_data['broken_seats'] = fetch_table_safe("SELECT * FROM broken_seats")
        else:
            backup_data['reservations'] = fetch_table_safe(
                "SELECT * FROM reservations WHERE DATE(start_time) >= %s AND DATE(start_time) <= %s", (start_date, end_date))
            backup_data['student_info'] = fetch_table_safe("""
                SELECT * FROM student_info WHERE student_id IN (
                    SELECT student_id FROM reservations WHERE DATE(start_time) >= %s AND DATE(start_time) <= %s
                )""", (start_date, end_date))
            backup_data['lab_schedules'] = fetch_table_safe(
                "SELECT * FROM lab_schedules WHERE start_date >= %s AND start_date <= %s", (start_date, end_date))
            backup_data['broken_seats'] = fetch_table_safe(
                "SELECT * FROM broken_seats WHERE DATE(broken_date) >= %s AND DATE(broken_date) <= %s", (start_date, end_date))

        def json_serial(obj):
            if isinstance(obj, (datetime, date, time)):
                return obj.isoformat()
            return str(obj)

        json_str = json.dumps(backup_data, ensure_ascii=False, indent=2, default=json_serial)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name_suffix = "all_time" if is_all_time else f"{start_date}_to_{end_date}"
        final_filename = f"complab_backup_{file_name_suffix}_{timestamp}.zip"

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("backup_data.json", json_str.encode('utf-8'))
            
            if os.path.exists(BASE_UPLOAD_DIR):
                for folder_name in os.listdir(BASE_UPLOAD_DIR):
                    folder_path = os.path.join(BASE_UPLOAD_DIR, folder_name)
                    if os.path.isdir(folder_path):
                        if not is_all_time:
                            try:
                                folder_date = datetime.strptime(folder_name, "%Y-%m-%d").date()
                                start_d = datetime.strptime(start_date, "%Y-%m-%d").date()
                                end_d = datetime.strptime(end_date, "%Y-%m-%d").date()

                                if not (start_d <= folder_date <= end_d):
                                    continue
                            except ValueError:
                                continue
                        
                        for file_name in os.listdir(folder_path):
                            file_path = os.path.join(folder_path, file_name)
                            if os.path.isfile(file_path):
                                zip_file.write(file_path, arcname=f"images/{folder_name}/{file_name}")

        if admin_id:
            try:
                cur.execute("""
                    INSERT INTO system_logs (action_type, file_name, admin_id, details)
                    VALUES ('backup', %s, %s, %s)
                """, (final_filename, admin_id, "สำรองข้อมูลสำเร็จ"))
                conn.commit()
            except Exception as e:
                print("Failed to save backup log:", e)
                conn.rollback()

        zip_buffer.seek(0)
        return StreamingResponse(zip_buffer, media_type="application/zip", 
                                 headers={"Content-Disposition": f"attachment; filename={final_filename}"})
        
    except Exception as e:
        print(f"Backup Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.post("/api/system/migrate")
async def migrate_database(file: UploadFile = File(...), admin_id: Optional[str] = Form("unknown"), admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        content = await file.read()
        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
            json_data = zip_file.read("backup_data.json").decode('utf-8')
            backup_data = json.loads(json_data)
            os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)
            
            for file_info in zip_file.infolist():
                if file_info.filename.startswith("images/") and not file_info.is_dir():
                    rel_path = file_info.filename.replace("images/", "", 1)
                    extracted_path = os.path.join(BASE_UPLOAD_DIR, rel_path)
                    os.makedirs(os.path.dirname(extracted_path), exist_ok=True)
                    with open(extracted_path, "wb") as f_out: 
                        f_out.write(zip_file.read(file_info.filename))
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("BEGIN;")
        tables_order = ['admins', 'academic_semesters', 'student_info', 'lab_schedules', 'broken_seats', 'reservations']
        pk_map = {'admins': 'staff_id', 'academic_semesters': 'id', 'student_info': 'student_id', 'lab_schedules': 'id', 'broken_seats': 'id', 'reservations': 'id'}
        
        for table in tables_order:
            if table in backup_data and len(backup_data[table]) > 0:
                rows = backup_data[table]
                cols = list(rows[0].keys())
                col_names = ", ".join(cols)
                placeholders = ", ".join(["%s"] * len(cols))
                pk = pk_map.get(table, 'id')
                
                insert_query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT ({pk}) DO NOTHING"
                data_to_insert = [tuple(row[col] for col in cols) for row in rows]
                cur.executemany(insert_query, data_to_insert)
        
        try:
            admin_val = admin_id if admin_id != 'unknown' else None
            cur.execute("""
                INSERT INTO system_logs (action_type, file_name, admin_id, details)
                VALUES ('migration', %s, %s, %s)
            """, (file.filename, admin_val, "นำเข้าและรวมข้อมูลสำเร็จ"))
        except Exception as e:
            print("Failed to save migration log:", e)

        conn.commit()
        return {"message": "นำเข้าข้อมูลสำเร็จ"}
    except Exception as e:
        if conn: conn.rollback()
        print(f"Migration Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.get("/api/system/logs")
def get_system_logs(admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT l.created_at, l.action_type, a.first_name, a.last_name, l.file_name
            FROM system_logs l
            LEFT JOIN admins a ON l.admin_id = a.staff_id
            ORDER BY l.created_at DESC
            LIMIT 50
        """)
        rows = cur.fetchall()
        return [
            {
                "date": str(r[0].strftime("%d/%m/%Y %H:%M")),
                "type": r[1],
                "admin_name": f"{r[2]} {r[3]}" if r[2] else "แอดมิน (ไม่ระบุ)",
                "file_name": r[4]
            } for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ==========================================
# จัดการข้อมูลผู้ดูแลระบบ (Admin)
# ==========================================
class AdminCreate(BaseModel):
    staff_id: str
    first_name: str
    last_name: Optional[str] = None      # 🟢 ต้องมี = None
    department: Optional[str] = None     # 🟢 ต้องมี = None
    position: Optional[str] = None       # 🟢 ต้องมี = None
    username: str
    password: str
    priority: int = 3

class AdminUpdate(BaseModel):
    first_name: str
    last_name: Optional[str] = None      # 🟢 ต้องมี = None
    department: Optional[str] = None     # 🟢 ต้องมี = None
    position: Optional[str] = None       # 🟢 ต้องมี = None
    username: str
    password: Optional[str] = None       # 🟢 ต้องมี = None
    priority: int

@router.get("/api/admins")
def get_all_admins(admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
            
        cur.execute("""
            SELECT staff_id, first_name, last_name, department, position, username, priority, created_at 
            FROM admins
            ORDER BY priority ASC, created_at DESC
        """)
        rows = cur.fetchall()

        return [
            {
                "staff_id": r[0],
                "first_name": r[1],
                "last_name": r[2],
                "department": r[3] or "-",
                "position": r[4] or "-",
                "username": r[5],
                "priority": r[6] if r[6] else 3,
                "created_at": str(r[7]) if r[7] else None
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.post("/api/admins")
def create_admin(admin: AdminCreate, current_admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM admins WHERE staff_id = %s OR username = %s", (admin.staff_id, admin.username))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="รหัสพนักงาน หรือ Username นี้มีผู้ใช้งานแล้ว")

        # ✅ Hash รหัสผ่านก่อน INSERT เข้า Database
        hashed_pw = get_password_hash(admin.password)

        # 🟢 ดักค่า None ไว้ เผื่อตอน Insert ถ้าเป็น None ก็จะได้ค่า Null ใน DB หรือ '-' (ถ้าต้องการ)
        last_name_val = admin.last_name if admin.last_name else ""
        department_val = admin.department if admin.department else ""
        position_val = admin.position if admin.position else ""

        cur.execute("""
            INSERT INTO admins (staff_id, first_name, last_name, department, position, username, password_hash, priority)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (admin.staff_id, admin.first_name, last_name_val, department_val, position_val, admin.username, hashed_pw, admin.priority))
        
        conn.commit()
        return {"message": "เพิ่มผู้ดูแลระบบสำเร็จ"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.put("/api/admins/{staff_id}")
def update_admin(staff_id: str, admin: AdminUpdate, current_admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM admins WHERE staff_id = %s", (staff_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูลผู้ดูแลระบบรหัสนี้")

        cur.execute("SELECT 1 FROM admins WHERE username = %s AND staff_id != %s", (admin.username, staff_id))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username นี้มีผู้ใช้อื่นใช้งานแล้ว")

        # 🟢 จัดการค่า None ให้ปลอดภัย
        last_name_val = admin.last_name if admin.last_name else ""
        department_val = admin.department if admin.department else ""
        position_val = admin.position if admin.position else ""

        if admin.password and admin.password.strip() != "":
            # ✅ Hash รหัสผ่านใหม่ก่อน UPDATE
            hashed_pw = get_password_hash(admin.password)
            cur.execute("""
                UPDATE admins 
                SET first_name=%s, last_name=%s, department=%s, position=%s, username=%s, password_hash=%s, priority=%s
                WHERE staff_id=%s
            """, (admin.first_name, last_name_val, department_val, position_val, admin.username, hashed_pw, admin.priority, staff_id))
        else:
            cur.execute("""
                UPDATE admins 
                SET first_name=%s, last_name=%s, department=%s, position=%s, username=%s, priority=%s
                WHERE staff_id=%s
            """, (admin.first_name, last_name_val, department_val, position_val, admin.username, admin.priority, staff_id))
            
        conn.commit()
        return {"message": "อัปเดตข้อมูลสำเร็จ"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

@router.delete("/api/admins/{staff_id}")
def delete_admin(staff_id: str, current_admin=Depends(verify_token)):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM admins WHERE staff_id = %s", (staff_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูลผู้ดูแลระบบรหัสนี้")
            
        conn.commit()
        return {"message": "ลบผู้ดูแลระบบสำเร็จ"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()