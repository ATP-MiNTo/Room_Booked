# ระบบจองห้องปฏิบัติการคอมพิวเตอร์ B4-302

ระบบจองที่นั่งแบบ Real-time พร้อมยืนยันตัวตนด้วยการสแกนใบหน้า และ Admin Dashboard สำหรับผู้ดูแลระบบ

## Tech Stack

- **Frontend:** React.js (Vite) — build เป็น static files เสิร์ฟผ่าน Nginx
- **Backend:** Python FastAPI + WebSocket
- **Database:** PostgreSQL 15
- **Infrastructure:** Docker, Docker Compose, Nginx (Reverse Proxy)

---

## Prerequisites

ติดตั้งก่อนเริ่มใช้งาน:
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) (เปิดรันไว้เบื้องหลัง)
2. Git

---

## วิธีรันโปรเจกต์

```bash
# 1. Clone โปรเจกต์
git clone <repository-url>
cd comlab-reservation-monitoring

# 2. สร้างไฟล์ .env (ดูตัวอย่างด้านล่าง)

# 3. รัน Docker
docker compose up -d --build
```

รอประมาณ 1-2 นาทีให้ทุก container พร้อม

---

## ตั้งค่า .env

สร้างไฟล์ `.env` ที่ root ของโปรเจกต์:

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_strong_password
POSTGRES_DB=complab_reservation_db
POSTGRES_PORT=5432
POSTGRES_HOST=db
```

> ⚠️ อย่า commit ไฟล์ `.env` ขึ้น Git

---

## ตั้งค่าฐานข้อมูล (ครั้งแรก)

หลัง docker รันแล้ว import schema:

```bash
docker exec -i complab_db psql -U admin -d complab_reservation_db < complab-reservation-db.session.sql
```

หรือเปิดด้วย SQLTools / DBeaver แล้วรันไฟล์ `complab-reservation-db.session.sql`

**ค่าเชื่อมต่อ DB (จากเครื่อง host):**
| Field | ค่า |
|---|---|
| Host | localhost |
| Port | 5432 |
| Database | complab_reservation_db |
| Username | admin |
| Password | (ตามที่ตั้งใน .env) |

---

## URLs

| หน้า | URL |
|---|---|
| จองที่นั่ง (นักศึกษา) | http://localhost |
| Admin Dashboard | http://localhost/admin |
| API Docs (Swagger) | http://localhost:8000/docs |

### เปิดผ่าน HTTPS / มือถือ (ngrok)

ระบบสแกนใบหน้าต้องการ HTTPS:

```bash
./ngrok http 80
```

คัดลอก URL ที่ได้ (`https://xxxx.ngrok-free.dev`) ไปเปิดในมือถือ

---

## โครงสร้างโปรเจกต์

```
complab-reservation/
├── README.md
├── docker-compose.yml
├── .env                            # ไม่ commit ขึ้น Git
├── ngrok.exe                       # สำหรับเปิด HTTPS ทดสอบผ่านมือถือ
├── simu_data.txt
├── complab-reservation-db.session.sql  # SQL schema สำหรับสร้างตาราง
│
├── backend/                        # FastAPI
│   ├── Dockerfile
│   ├── main.py                     # Entry point, mount static files
│   ├── database.py                 # เชื่อมต่อ PostgreSQL
│   ├── security.py                 # JWT / password hashing
│   ├── requirements.txt
│   └── routers/
│       ├── auth.py                 # Login / session
│       ├── booking.py              # จอง, WebSocket, ที่นั่ง
│       └── system.py               # Backup, Migrate, Logs
│
├── frontend/                       # React + Vite (build → static)
│   ├── Dockerfile
│   ├── nginx-frontend.conf         # Nginx เสิร์ฟ static files
│   ├── vite.config.js
│   ├── index.html
│   ├── package.json
│   └── src/
│       ├── App.jsx                 # Router หลัก
│       ├── main.jsx
│       ├── assets/
│       ├── styles/
│       │   ├── App.css
│       │   ├── FaceScanner.css
│       │   └── index.css
│       ├── utils/
│       │   ├── dateUtils.js
│       │   └── uiConstants.js
│       ├── components/
│       │   ├── FaceScanner.jsx     # สแกนใบหน้า (face-api.js)
│       │   ├── ProtectedRoute.jsx
│       │   ├── ReservationForm.jsx
│       │   ├── SeatMap.jsx         # แผนผังที่นั่ง
│       │   ├── TimeSelector.jsx
│       │   └── admin/
│       │       ├── AdminLayout.jsx     # Sidebar layout
│       │       ├── AdminManage.jsx
│       │       ├── Accordion.jsx
│       │       ├── SeatGrid.jsx
│       │       └── ThaiDatePicker.jsx
│       └── pages/
│           ├── Booking.jsx         # หน้าจองที่นั่ง (นักศึกษา)
│           └── admin/
│               ├── Login.jsx
│               ├── Monitor.jsx         # Live monitor ที่นั่ง
│               ├── MonitorMock.jsx
│               ├── BookingHistory.jsx  # ประวัติการจอง
│               ├── StudentInfo.jsx
│               ├── Analytics.jsx
│               ├── BackupRestore.jsx   # Backup & Migration
│               └── SystemManage.jsx
│
├── nginx/
│   └── nginx.conf                  # Reverse proxy config
└── data/
    └── face_scanner/               # รูปภาพสแกนใบหน้า (แยกตามวันที่)
```

---

## คำสั่งที่ใช้บ่อย

```bash
# รันระบบ
docker compose up -d --build

# หยุดระบบ
docker compose down

# ดู logs
docker compose logs -f backend
docker compose logs -f frontend

# Backup ฐานข้อมูล
docker exec complab_db pg_dump -U admin complab_reservation_db > backup.sql

# Reset sequence (กรณี duplicate key error)
docker exec -it complab_db psql -U admin -d complab_reservation_db -c "SELECT setval('reservations_id_seq', (SELECT MAX(id) FROM reservations));"
```