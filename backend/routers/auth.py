from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db
from security import verify_password, create_token

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
        
        cur.execute("""
            SELECT staff_id, first_name, last_name, password_hash
            FROM admins
            WHERE username = %s
        """, (req.username,))
        
        admin = cur.fetchone()

        if not admin:
            raise HTTPException(status_code=401, detail="ชื่อผู้ใช้งาน หรือรหัสผ่านไม่ถูกต้อง")

        staff_id, first_name, last_name, db_password_hash = admin
        
        if not verify_password(req.password, db_password_hash):
            raise HTTPException(status_code=401, detail="ชื่อผู้ใช้งาน หรือรหัสผ่านไม่ถูกต้อง")

        token = create_token(staff_id)  # ✅ JWT จริง

        return {
            "message": "เข้าสู่ระบบสำเร็จ",
            "token": token,
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