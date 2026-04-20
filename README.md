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

**1. Clone โปรเจกต์**
```bash
git clone <repository-url>
cd complab-reservation-monitoring
```

**2. สร้างไฟล์ `.env`** ที่ root ของโปรเจกต์ (ดูตัวอย่างในหัวข้อถัดไป)

**3. รัน Docker**
```bash
docker-compose up -d --build
```

> รอประมาณ 1–2 นาทีให้ทุก container พร้อม

**4. Import ฐานข้อมูล (ครั้งแรกเท่านั้น)**
```bash
docker exec -i complab_db psql -U admin -d complab_reservation_db < complab-reservation-db.session.sql
```

---

## ⚙️ ตั้งค่า .env

สร้างไฟล์ `.env` ที่ root ของโปรเจกต์ โดยมีเนื้อหาดังนี้:

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_strong_password
POSTGRES_DB=complab_reservation_db
POSTGRES_PORT=5432
POSTGRES_HOST=db
JWT_SECRET_KEY=your_secret_key_here
```

> ⚠️ ไฟล์นี้เก็บ credential สำคัญ อย่า commit ขึ้น Git

**สร้าง `JWT_SECRET_KEY` ด้วยคำสั่ง:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
คัดลอกค่าที่ได้ไปใส่ใน `.env`

---

## 🗄️ ตั้งค่าฐานข้อมูล

หลัง Docker รันแล้ว import schema ด้วยคำสั่งด้านบน หรือเปิดด้วย SQLTools / DBeaver แล้วรันไฟล์ `complab-reservation-db.session.sql`

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

ระบบสแกนใบหน้าต้องการ HTTPS จึงต้องใช้ ngrok เมื่อทดสอบจากมือถือ:

```bash
./ngrok http 80
```

คัดลอก URL ที่ได้ (`https://xxxx.ngrok-free.dev`) ไปเปิดในมือถือ

---

## 👤 เพิ่มบัญชี Admin เริ่มต้น

หลัง import schema แล้ว ต้องสร้าง admin อย่างน้อย 1 บัญชีก่อนจึงจะ login ได้

**วิธีที่ 1: สร้าง password hash ก่อน แล้ว INSERT เข้า DB**

```bash
# 1. สร้าง hash ของรหัสผ่านที่ต้องการ (เช่น "admin1234")
python -c "import bcrypt; print(bcrypt.hashpw('admin1234'.encode(), bcrypt.gensalt()).decode())"
```

ได้ค่า hash ประมาณนี้:
```
$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

```bash
# 2. INSERT บัญชี admin เข้า DB
docker exec -it complab_db psql -U admin -d complab_reservation_db -c "
INSERT INTO admins (staff_id, first_name, last_name, department, position, username, password_hash, priority)
VALUES ('ADM001', 'ชื่อ', 'นามสกุล', 'IT Center', 'Administrator', 'admin', '\$2b\$12\$xxx...', 1);
"
```

**วิธีที่ 2: ใช้ข้อมูลตัวอย่างจากโฟลเดอร์ `simu_data` (แนะนำสำหรับทดสอบ)**

ดูหัวข้อถัดไป

---

## 🧪 ข้อมูลจำลองสำหรับทดสอบ (simu_data)

โฟลเดอร์ `simu_data/` มีข้อมูลตัวอย่างพร้อมใช้ ประกอบด้วย:

- `simu_data.txt` — SQL สำหรับ insert ข้อมูลจำลองทั้งหมด (admin, นักศึกษา, การจอง, ตารางเรียน, แจ้งซ่อม)
- `face_scanner/` — รูปภาพสแกนใบหน้าจำลอง จัดเก็บแยกตามวันที่ (56 ไฟล์)

**วิธี import ข้อมูลจำลอง:**

```bash
# 1. Import SQL (admin + นักศึกษา + การจอง + ตารางเรียน + แจ้งซ่อม)
docker exec -i complab_db psql -U admin -d complab_reservation_db < simu_data/simu_data.txt

# 2. คัดลอกรูปภาพจำลองเข้า container
docker cp simu_data/face_scanner/. complab_backend:/app/../data/face_scanner/
```

**บัญชี Admin ที่ได้จากข้อมูลจำลอง:**

| Field | ค่า |
|---|---|
| Username | `admin` |
| Password | `Admin@12345` |

> หากต้องการเปลี่ยน password ให้เข้าไปแก้ในหน้า Admin → จัดการผู้ดูแลระบบ

---

## 📁 โครงสร้างโปรเจกต์

```
complab-reservation/
├── README.md
├── docker-compose.yml
├── .env                                # ⚠️ ต้องสร้างเอง (ดูหัวข้อ ตั้งค่า .env)
├── ngrok.exe
├── complab-reservation-db.session.sql  # SQL schema สำหรับสร้างตาราง
│
├── backend/                        # FastAPI
│   ├── Dockerfile
│   ├── main.py                     # Entry point, mount /data static files, register routers
│   ├── database.py                 # เชื่อมต่อ PostgreSQL ด้วย psycopg2
│   ├── security.py                 # hash และ verify password ด้วย bcrypt, JWT
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
├── data/
│   └── face_scanner/               # รูปภาพสแกนใบหน้า จัดเก็บแยกตามวันที่ (สร้างอัตโนมัติ)
└── simu_data/                      # ข้อมูลจำลองสำหรับทดสอบ
    ├── simu_data.txt               # SQL insert ข้อมูลตัวอย่างทั้งหมด
    └── face_scanner/               # รูปภาพจำลอง 56 ไฟล์ จัดเก็บแยกตามวันที่
```

---

## 📋 คำสั่งที่ใช้บ่อย

**รันระบบ**
```bash
docker-compose up -d --build
```

**หยุดระบบ**
```bash
docker-compose down
```

**ดู logs**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Backup ฐานข้อมูล**
```bash
docker exec complab_db pg_dump -U admin complab_reservation_db > backup.sql
```

**Reset sequence (กรณี duplicate key error)**
```bash
docker exec -it complab_db psql -U admin -d complab_reservation_db -c \
  "SELECT setval('reservations_id_seq', (SELECT MAX(id) FROM reservations));"
```