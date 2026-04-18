from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db
from security import verify_password  # นำเข้าฟังก์ชันตรวจสอบ Hash ที่เราเพิ่งสร้าง

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/api/admin/login")
def admin_login(req: LoginRequest):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # 1. ดึงข้อมูลแอดมินจาก Database ด้วย Username
        cur.execute("""
            SELECT staff_id, first_name, last_name, password_hash
            FROM admins
            WHERE username = %s
        """, (req.username,))
        
        admin = cur.fetchone()

        # 2. เช็คว่าเจอ Username นี้ในระบบไหม
        if not admin:
            raise HTTPException(status_code=401, detail="ชื่อผู้ใช้งาน หรือรหัสผ่านไม่ถูกต้อง")

        staff_id, first_name, last_name, db_password_hash = admin
        
        # 3. เช็ครหัสผ่าน โดยเทียบ "รหัสที่ผู้ใช้กรอกมา (req.password)" กับ "Hash ใน Database (db_password_hash)"
        # ถ้าเช็คแล้วได้ค่า False แสดงว่ารหัสผิด
        if not verify_password(req.password, db_password_hash):
            raise HTTPException(status_code=401, detail="ชื่อผู้ใช้งาน หรือรหัสผ่านไม่ถูกต้อง")

        # 4. ถ้ารหัสถูก ให้สร้าง Token (จำลอง) และเข้าสู่ระบบ
        return {
            "message": "เข้าสู่ระบบสำเร็จ",
            "token": f"admin_token_{staff_id}", 
            "admin_id": staff_id,
            "admin_name": f"{first_name} {last_name}"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"DATABASE ERROR (POST /api/admin/login): {e}")
        raise HTTPException(status_code=500, detail="ระบบฐานข้อมูลขัดข้อง")
    finally:
        if cur: cur.close()
        if conn: conn.close()