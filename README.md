# 🖥️ ระบบจองห้องปฏิบัติการคอมพิวเตอร์ B4-302

ระบบจองที่นั่งแบบ Real-time พร้อมยืนยันตัวตนด้วยการสแกนใบหน้า และ Admin Dashboard สำหรับผู้ดูแลระบบ

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React.js (Vite) → build เป็น static files เสิร์ฟผ่าน Nginx |
| Backend | Python FastAPI + WebSocket |
| Database | PostgreSQL 15 |
| Infrastructure | Docker, Docker Compose, Nginx (Reverse Proxy) |

---

## ✅ Prerequisites

ติดตั้งก่อนเริ่มใช้งาน:
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) (เปิดรันไว้เบื้องหลัง)
2. Git

---

## 🚀 วิธีรันโปรเจกต์

1. Clone โปรเจกต์
```bash
git clone <repository-url>
cd complab-reservation-monitoring
```

2. สร้างไฟล์ .env (ดูตัวอย่างด้านล่าง)


3. รัน Docker
```bash
docker-compose up -d --build
```

> รอประมาณ 1–2 นาทีให้ทุก container พร้อม

---

## ⚙️ ตั้งค่า .env

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

## 🗄️ ตั้งค่าฐานข้อมูล (ครั้งแรก)

หลัง Docker รันแล้ว import schema:

```bash
docker exec -i complab_db psql -U admin -d complab_reservation_db < complab-reservation-db.session.sql
```

หรือเปิดด้วย SQLTools / DBeaver แล้วรันไฟล์ `complab-reservation-db.session.sql`

**ค่าเชื่อมต่อ DB (จากเครื่อง host):**

| Field | ค่า |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `complab_reservation_db` |
| Username | `admin` |
| Password | ตามที่ตั้งใน `.env` |

---

## 🌐 URLs

| หน้า | URL |
|---|---|
| จองที่นั่ง (นักศึกษา) | http://localhost |
| Admin Dashboard | http://localhost/admin |
| API Docs (Swagger) | http://localhost:8000/docs |

### 📱 เปิดผ่าน HTTPS / มือถือ (ngrok)

ระบบสแกนใบหน้าต้องการ HTTPS:

```bash
./ngrok http 80
```

คัดลอก URL ที่ได้ (`https://xxxx.ngrok-free.dev`) ไปเปิดในมือถือ

---

## 📁 โครงสร้างโปรเจกต์

```
complab-reservation/
├── README.md
├── docker-compose.yml
├── .env                                
├── ngrok.exe                           
├── complab-reservation-db.session.sql  # SQL schema สำหรับสร้างตาราง
│
├── backend/                        # FastAPI
│   ├── Dockerfile
│   ├── main.py                     # Entry point, mount /data static files, register routers
│   ├── database.py                 # เชื่อมต่อ PostgreSQL ด้วย psycopg2
│   ├── security.py                 # hash และ verify password ด้วย bcrypt
│   ├── requirements.txt
│   └── routers/
│       ├── auth.py                 # Login / logout / session ของ admin
│       ├── booking.py              # จองที่นั่ง, ดูที่นั่งว่าง, WebSocket real-time
│       └── system.py               # Backup, Migration, ประวัติการใช้งาน (Logs)
│
├── frontend/                       # React + Vite (build → static)
│   ├── Dockerfile
│   ├── nginx-frontend.conf         # Nginx เสิร์ฟ static files พร้อม fallback index.html
│   ├── vite.config.js
│   ├── index.html
│   ├── package.json
│   └── src/
│       ├── App.jsx                 # Router หลัก กำหนด path ทุกหน้า
│       ├── main.jsx                # Entry point ของ React
│       ├── assets/
│       ├── styles/
│       │   ├── App.css             # สไตล์หลักของแอป
│       │   ├── FaceScanner.css     # สไตล์หน้าสแกนใบหน้า
│       │   └── index.css           # global styles
│       ├── utils/
│       │   ├── dateUtils.js        # ฟังก์ชันจัดการวันที่ภาษาไทย, export CSV
│       │   └── uiConstants.js      # shared styles, ตัวเลือก major/ชั้นปี
│       ├── components/
│       │   ├── FaceScanner.jsx     # สแกนใบหน้าด้วย face-api.js ถ่ายรูปยืนยันตัวตน
│       │   ├── ProtectedRoute.jsx  # ป้องกัน route admin ให้ login ก่อนเข้าได้
│       │   ├── ReservationForm.jsx # ฟอร์มกรอกข้อมูลจองที่นั่ง
│       │   ├── SeatMap.jsx         # แผนผังที่นั่ง 30 ที่นั่ง แสดงสถานะว่าง/ไม่ว่าง
│       │   ├── TimeSelector.jsx    # dropdown เลือกช่วงเวลาจอง
│       │   └── admin/
│       │       ├── AdminLayout.jsx     # Layout หลัก admin มี sidebar และ header
│       │       ├── AdminManage.jsx     # จัดการบัญชี admin (เพิ่ม/แก้ไข/ลบ)
│       │       ├── Accordion.jsx       # component accordion ใช้ใน SystemManage
│       │       ├── SeatGrid.jsx        # grid เลือกที่นั่ง 30 ที่ ใช้ตั้งค่าที่นั่งเสีย
│       │       └── ThaiDatePicker.jsx  # date picker แสดงเดือน/ปีภาษาไทย
│       └── pages/
│           ├── Booking.jsx             # หน้าจองที่นั่ง (นักศึกษา) เลือกเวลา/ที่นั่ง/สแกนหน้า
│           └── admin/
│               ├── Login.jsx           # หน้า login admin
│               ├── Monitor.jsx         # Live monitor ที่นั่ง real-time ผ่าน WebSocket
│               ├── MonitorMock.jsx     # Monitor จำลอง สำหรับทดสอบโดยไม่ต้องมีกล้อง
│               ├── BookingHistory.jsx  # ประวัติการจองทั้งหมด ค้นหา/กรอง/export CSV
│               ├── StudentInfo.jsx     # ข้อมูลนักศึกษาที่เคยใช้ระบบ
│               ├── Analytics.jsx       # สถิติและกราฟการใช้ห้อง
│               ├── BackupRestore.jsx   # สำรองข้อมูล (.zip) และนำเข้าข้อมูล (Migration)
│               └── SystemManage.jsx    # ตั้งค่าระบบ เช่น ตารางเรียน, ที่นั่งเสีย, จัดการ admin
│
├── nginx/
│   └── nginx.conf                  # Reverse proxy: routing ระหว่าง frontend/backend/static
└── data/
    └── face_scanner/               # รูปภาพสแกนใบหน้า จัดเก็บแยกตามวันที่
```

---

## 📋 คำสั่งที่ใช้บ่อย

# รันระบบ
```bash
docker-compose up -d --build
```
```bash
# หยุดระบบ
docker-compose down
```
# ดู logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```
# Backup ฐานข้อมูล
```bash
docker exec complab_db pg_dump -U admin complab_reservation_db > backup.sql
```
# Reset sequence (กรณี duplicate key error)
```bash
docker exec -it complab_db psql -U admin -d complab_reservation_db -c \
  "SELECT setval('reservations_id_seq', (SELECT MAX(id) FROM reservations));"
```