import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers.booking import router as booking_router
from routers.system import router as system_router
from routers.auth import router as auth_router

app = FastAPI()

# 🟢 1. ตั้งค่า CORS (สำคัญมาก: ต้องอนุญาตให้ดึงข้อมูลข้ามพอร์ตได้)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # อนุญาตให้ทุกโดเมนเข้าถึงได้ (รวมถึง localhost:5173 ของ React)
    allow_credentials=True,
    allow_methods=["*"], # อนุญาตทุก Method (GET, POST, PUT, DELETE)
    allow_headers=["*"], # อนุญาตทุก Header
)

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

# 🟢 2. เช็คโฟลเดอร์ data ให้ชัวร์ว่าชี้ถูกที่
DATA_DIR = os.path.join(ROOT_DIR, "data")
print(f"Serving static files from: {DATA_DIR}") # ปริ้นท์บอกใน Terminal เพื่อให้เช็คได้ง่ายๆ

# 🟢 3. Mount โฟลเดอร์ data เพื่อให้เข้าถึงไฟล์ภาพได้ทาง URL /data/...
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

app.include_router(booking_router)
app.include_router(system_router)
app.include_router(auth_router)

@app.get("/")
def health():
    return {"status": "API running"}