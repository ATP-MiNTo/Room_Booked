import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production-please")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def create_token(staff_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": staff_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ไม่ถูกต้อง")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token หมดอายุ")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token ไม่ถูกต้อง")