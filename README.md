# 🎓 ระบบจองห้องปฏิบัติการคอมพิวเตอร์ B4-302 (Computer Lab Reservation System)

โปรเจกต์ระบบจองที่นั่งห้องแล็บคอมพิวเตอร์แบบ Real-time พร้อมระบบยืนยันตัวตนด้วยการสแกนใบหน้า (Face Recognition) และระบบจัดการหลังบ้านสำหรับผู้ดูแล (Admin Dashboard)

## 🛠️ Tech Stack
- **Frontend:** React.js (Vite), React Router DOM
- **Backend:** Python FastAPI, WebSockets (สำหรับสถานะที่นั่ง Real-time)
- **Database:** PostgreSQL
- **Infrastructure:** Docker & Docker Compose, Nginx (Reverse Proxy)

---

## ⚙️ สิ่งที่ต้องมีในเครื่องก่อนเริ่มงาน (Prerequisites)
กรุณาตรวจสอบให้แน่ใจว่าเครื่องของคุณติดตั้งโปรแกรมเหล่านี้แล้ว:
1. **Docker Desktop** (เปิดโปรแกรมรันไว้เบื้องหลังด้วย)
2. **Git**
3. โปรแกรมจัดการฐานข้อมูล เช่น **DBeaver** หรือ **pgAdmin**

---

## 🚀 วิธีการรันโปรเจกต์ (How to Run)

ไม่ต้องลง Node.js หรือ Python ในเครื่อง แค่ใช้ Docker คำสั่งเดียวจบ!

1. เปิด Terminal แล้วเข้าไปที่โฟลเดอร์โปรเจกต์
2. รันคำสั่งนี้เพื่อสร้างและเปิดการทำงานของ Container ทั้งหมด:
   ```bash
   docker-compose up -d --build
   ```
3. รอจนกว่าระบบจะขึ้นคำว่า `Started` ครบทุก Container

---

## 🗄️ การตั้งค่าฐานข้อมูล (Database Setup - ทำแค่ครั้งแรก)

เมื่อรัน Docker เสร็จแล้ว ฐานข้อมูลจะว่างเปล่าอยู่ ให้ทำตามขั้นตอนนี้:
1. เปิด DBeaver หรือโปรแกรมจัดการ DB
2. เชื่อมต่อฐานข้อมูลด้วยค่าคอนฟิกดังนี้:
   - **Host:** `localhost`
   - **Port:** `5432`
   - **Database:** `complab_reservation_db`
   - **User:** `admin`
   - **Password:** `password123`
3. เปิดไฟล์ `complab-reservation-db.session.sql` ที่อยู่ในโฟลเดอร์หลัก
4. กดรันคำสั่ง SQL ทั้งหมดในไฟล์นั้น เพื่อสร้างตาราง `student_info` และ `reservations` ให้พร้อมใช้งาน

---

## 🌐 ช่องทางการเข้าใช้งาน (URLs)

เมื่อระบบรันสมบูรณ์ สามารถเข้าใช้งานผ่านเบราว์เซอร์ได้ตามลิงก์นี้:
- **หน้าจองที่นั่ง (สำหรับนักศึกษา):** [http://localhost](http://localhost)
- **หน้าจัดการระบบ (Admin Dashboard):** [http://localhost/admin](http://localhost/admin)
- **API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)

*(หมายเหตุ: หากต้องการนำลิงก์ไปเปิดในมือถือเพื่อทดสอบการสแกนหน้า ให้รัน Ngrok ที่พอร์ต 80)*

---

## 📂 โครงสร้างโฟลเดอร์ที่สำคัญ (Folder Structure)

ระบบถูกแบ่งแยกส่วนหน้าบ้านและหลังบ้านออกจากกันอย่างชัดเจน เพื่อความง่ายในการพัฒนาต่อ

```text
complab-reservation/
│
├── frontend/                 # ⚛️ ฝั่งหน้าบ้าน (React + Vite)
│   ├── src/
│   │   ├── components/       # Component ย่อย (เช่น SeatMap, FaceScanner)
│   │   ├── pages/            # หน้าจอหลัก
│   │   │   ├── Booking.jsx         # 📍 หน้าจองที่นั่งของนักศึกษา
│   │   │   └── admin/
│   │   │       ├── AdminLayout.jsx # โครงร่างเมนู Sidebar สีเข้ม
│   │   │       └── BookingLogs.jsx # 📍 หน้าตารางประวัติการจองของ Admin
│   │   ├── styles/           # ไฟล์ CSS ทั้งหมด
│   │   └── App.jsx           # ตัวจัดการ Router สลับหน้าเว็บ
│   └── vite.config.js
│
├── backend/                  # 🐍 ฝั่งหลังบ้าน (FastAPI)
│   ├── main.py               # จุดเริ่มต้นของ API
│   ├── reservation.py        # 📍 จัดการ API จองที่นั่ง และระบบ WebSockets (ที่นั่งสีเหลือง)
│   └── database.py           # ตั้งค่าการเชื่อมต่อ PostgreSQL
│
├── nginx/                    # 🚦 ตั้งค่า Nginx Reverse Proxy (เชื่อมพอร์ต 80 และ WebSockets)
├── data/                     # 📸 พื้นที่เก็บรูปภาพสแกนใบหน้า (แยกตามโฟลเดอร์วันที่)
└── docker-compose.yml        # ตัวคุมการสร้าง Server ทั้งหมด
```

## 💬 Note ถึงทีมพัฒนา (Briefing)
- **ระบบ Real-time:** ตอนนี้เราต่อท่อ WebSocket ไว้เรียบร้อยแล้ว เวลามีคนกดเลือกที่นั่ง จอของคนอื่นจะขึ้น **"สีเหลือง"** ทันที (โค้ดอยู่ที่ `backend/reservation.py`)
- **หน้า Admin:** หน้าตารางประวัติการจองถูกย้ายไปครอบด้วยเลย์เอาต์เมนูด้านข้างแล้ว ให้ไปเขียนโค้ดต่อได้เลยที่ `frontend/src/pages/admin/BookingLogs.jsx`
- **รูปภาพ:** รูปที่สแกนหน้าจะถูกบันทึกลงโฟลเดอร์ `data/face_scanner/` อัตโนมัติ (ตั้งค่า `.gitignore` ไว้แล้วเพื่อไม่ให้ไฟล์รูปจริงถูก Push ขึ้น Git)