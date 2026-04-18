import bcrypt

def get_password_hash(password: str) -> str:
    """ฟังก์ชันสำหรับแปลงรหัสผ่านธรรมดาให้เป็น Hash"""
    # สุ่มเกลือ (salt) และเข้ารหัส
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ฟังก์ชันสำหรับตรวจสอบรหัสผ่านตอน Login"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        # ดักจับ Error กรณี Hash ใน Database ไม่ถูกต้องตามฟอร์แมต
        return False