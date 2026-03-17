import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from reservation import router as reservation_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

# Mount path สำหรับให้หน้าเว็บดึงรูปไปโชว์
app.mount("/data", StaticFiles(directory=os.path.join(ROOT_DIR, "data")), name="data")


app.include_router(reservation_router)

@app.get("/")
def health():
    return {"status": "API running"}