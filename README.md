# 🖥️ ระบบจองห้องปฏิบัติการคอมพิวเตอร์ B4-302

ระบบจองที่นั่งแบบ Real-time พร้อมยืนยันตัวตนด้วยการสแกนใบหน้า และ Admin Dashboard สำหรับผู้ดูแลระบบ

🌐 **เว็บไซต์:** https://reserve-monitor-comlab.up.railway.app/

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React.js (Vite) → build เป็น static files เสิร์ฟผ่าน Nginx |
| Backend | Python FastAPI + WebSocket |
| Database | PostgreSQL 15 |
| Infrastructure | Docker, Docker Compose, Nginx (Reverse Proxy) |
| Hosting | Railway |
| Storage | Cloudinary (รูปภาพสแกนใบหน้า) |
| Camera tunnel | ngrok |

---

## 🌐 URLs

| หน้า | URL |
|---|---|
| จองที่นั่ง (นักศึกษา) | https://reserve-monitor-comlab.up.railway.app/ |
| Admin Dashboard | https://reserve-monitor-comlab.up.railway.app/admin |
| API Docs (Swagger) | https://reserve-monitor-comlab.up.railway.app/docs |

---

## ✅ Prerequisites (รันในเครื่อง)

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Git
3. ngrok (ถ้าต้องการเชื่อมกล้อง)

---

## 🚀 รันในเครื่อง (Local)

```bash
git clone <repository-url>
cd complab-reservation
```

สร้างไฟล์ `.env` (ดูหัวข้อถัดไป) แล้วรัน:

```bash
docker-compose up -d --build
```

> รอ 1–2 นาทีให้ทุก container พร้อม

**Import ฐานข้อมูล (ครั้งแรกเท่านั้น):**
```bash
docker exec -i complab_db psql -U admin -d complab_reservation_db < complab-reservation-db.session.sql
```

---

## ⚙️ ตั้งค่า .env

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_strong_password
POSTGRES_DB=complab_reservation_db
POSTGRES_PORT=5432
POSTGRES_HOST=db
JWT_SECRET_KEY=your_secret_key_here

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# กล้อง (ngrok) — ถ้ายังไม่มีให้เว้นว่างไว้ก่อน
VITE_CAMERA_WS_URL=https://xxxx.ngrok-free.app
```

> ⚠️ อย่า commit ไฟล์นี้ขึ้น Git เด็ดขาด

**สร้าง `JWT_SECRET_KEY`:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📷 เชื่อมกล้อง (ngrok)

หน้า Monitor จะรับข้อมูลจากเครื่องที่รันโค้ดกล้องผ่าน WebSocket ใช้ ngrok เป็น tunnel

**วิธีเชื่อม:**

1. รันโค้ดกล้องในเครื่องที่ต่อกล้องไว้
2. เปิด tunnel ด้วย ngrok:
   ```bash
   ./ngrok http <port-ของโค้ดกล้อง>
   ```
3. คัดลอก URL ที่ได้ เช่น `https://a1b2c3.ngrok-free.app`
4. ใส่ใน 2 ที่:
   - ไฟล์ `.env` ในเครื่อง: `VITE_CAMERA_WS_URL=https://a1b2c3.ngrok-free.app`
   - Railway → frontend service → **Variables**: `VITE_CAMERA_WS_URL=https://a1b2c3.ngrok-free.app`

> ⚠️ **ngrok free tier จะได้ URL ใหม่ทุกครั้งที่รีสตาร์ท** ต้องอัปเดต Railway Variables ทุกครั้ง  
> ⚠️ ngrok free tier มี connection limit — ถ้าใช้งานหนักให้พิจารณา plan แบบเสียเงิน

---

## ☁️ Cloudinary

ระบบเก็บรูปภาพสแกนใบหน้าไว้ที่ Cloudinary

- สมัครได้ที่: https://cloudinary.com (มี free tier)
- ดู credentials ได้ที่ Dashboard → **Cloud Name / API Key / API Secret**
- ใส่ค่าใน `.env` และ Railway → backend service → **Variables**

> ⚠️ Cloudinary free tier มี bandwidth และ storage จำกัด ควรตรวจสอบการใช้งานเป็นระยะ

---

## 🚂 Deploy บน Railway

### Environment Variables ที่ต้องตั้งใน Railway

**Backend service:**
```
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
POSTGRES_PORT
POSTGRES_HOST
JWT_SECRET_KEY
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
```

**Frontend service:**
```
VITE_CAMERA_WS_URL=https://xxxx.ngrok-free.app
```

> ⚠️ `VITE_CAMERA_WS_URL` ต้อง build ใหม่ทุกครั้งที่เปลี่ยนค่า เพราะ Vite อ่านค่าตอน build ไม่ใช่ runtime  
> กด **Redeploy** ใน Railway หลังอัปเดต Variables ทุกครั้ง

---

## 👤 เพิ่ม Admin เริ่มต้น

```bash
# 1. สร้าง password hash
python -c "import bcrypt; print(bcrypt.hashpw('admin1234'.encode(), bcrypt.gensalt()).decode())"

# 2. INSERT เข้า DB
docker exec -it complab_db psql -U admin -d complab_reservation_db -c "
INSERT INTO admins (staff_id, first_name, last_name, department, position, username, password_hash, priority)
VALUES ('ADM001', 'ชื่อ', 'นามสกุล', 'IT Center', 'Administrator', 'admin', '\$2b\$12\$xxx...', 1);
"
```

หรือใช้ข้อมูลจำลอง (ดูหัวข้อถัดไป)

---

## 🧪 ข้อมูลจำลองสำหรับทดสอบ

```bash
# Import SQL
docker exec -i complab_db psql -U admin -d complab_reservation_db < simu_data/simu_data.txt

# คัดลอกรูปภาพจำลอง
docker cp simu_data/face_scanner/. complab_backend:/app/../data/face_scanner/
```

**บัญชี Admin จากข้อมูลจำลอง:**

| Field | ค่า |
|---|---|
| Username | `admin` |
| Password | `Admin@12345` |

---

## 📁 โครงสร้างโปรเจกต์

```
complab-reservation/
├── README.md
├── docker-compose.yml
├── .env                                    # ⚠️ ต้องสร้างเอง
├── ngrok.exe
├── complab-reservation-db.session.sql      # SQL schema สำหรับสร้างตาราง
├── data/                                   # รูปภาพสแกนใบหน้า (สร้างอัตโนมัติ)
├── backend/                                # FastAPI
│   ├── Dockerfile
│   ├── main.py                             # Entry point, register routers
│   ├── database.py                         # เชื่อมต่อ PostgreSQL
│   ├── security.py                         # bcrypt + JWT
│   ├── requirements.txt
│   └── routers/
│       ├── auth.py                         # Login / logout / session admin
│       ├── booking.py                      # จองที่นั่ง, WebSocket real-time
│       └── system.py                       # Backup, Logs, ตั้งค่าระบบ
├── frontend/                               # React + Vite
│   ├── Dockerfile
│   ├── nginx-frontend.conf
│   ├── vite.config.js
│   ├── index.html
│   ├── package.json
│   ├── dist/                               # Static files หลัง build
│   └── src/
│       ├── App.jsx                         # Router หลัก
│       ├── main.jsx
│       ├── assets/
│       ├── styles/
│       │   ├── App.css
│       │   ├── FaceScanner.css
│       │   └── index.css
│       ├── utils/
│       │   ├── authFetch.js
│       │   ├── dateUtils.js                # ฟังก์ชันวันที่ภาษาไทย, export CSV
│       │   └── uiConstants.js
│       ├── components/
│       │   ├── FaceScanner.jsx             # สแกนใบหน้า (face-api.js)
│       │   ├── ProtectedRoute.jsx
│       │   ├── ReservationForm.jsx
│       │   ├── SeatMap.jsx                 # แผนผังที่นั่ง 30 ที่
│       │   ├── TimeSelector.jsx
│       │   └── admin/
│       │       ├── Accordion.jsx
│       │       ├── AdminLayout.jsx         # Layout + Sidebar admin
│       │       ├── SeatGrid.jsx
│       │       └── ThaiDatePicker.jsx
│       └── pages/
│           ├── Booking.jsx                 # หน้าจองที่นั่ง (นักศึกษา)
│           └── admin/
│               ├── Login.jsx
│               ├── Monitor.jsx             # Live monitor (รับข้อมูลกล้องผ่าน WebSocket)
│               ├── MonitorMock.jsx         # Mock monitor (ไม่ต้องการกล้อง)
│               ├── BookingHistory.jsx
│               ├── StudentInfo.jsx
│               ├── Analytics.jsx
│               ├── BackupRestore.jsx
│               ├── AdminManage.jsx
│               └── SystemManage.jsx
├── nginx/
│   └── nginx.conf                          # Reverse proxy frontend/backend
└── simu_data/                              # ข้อมูลจำลองสำหรับทดสอบ
```

---

## 📋 คำสั่งที่ใช้บ่อย

```bash
# รัน
docker-compose up -d --build

# หยุด
docker-compose down

# ดู logs
docker-compose logs -f backend

# Backup DB
docker exec complab_db pg_dump -U admin complab_reservation_db > backup.sql

# Reset sequence (กรณี duplicate key error)
docker exec -it complab_db psql -U admin -d complab_reservation_db -c \
  "SELECT setval('reservations_id_seq', (SELECT MAX(id) FROM reservations));"
```