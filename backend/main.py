import os
import cloudinary
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers.booking import router as booking_router
from routers.system import router as system_router
from routers.auth import router as auth_router
from database import init_sequences

app = FastAPI(
    proxy_headers=True, 
    forwarded_allow_ips="*"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

@app.on_event("startup")
def startup():
    init_sequences()

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

app.include_router(booking_router)
app.include_router(system_router)
app.include_router(auth_router)

@app.get("/")
def health():
    return {"status": "API running with Cloudinary Support"}