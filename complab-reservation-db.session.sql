-- ============================================================
--  complab-reservation-db.session.sql
--  Schema เต็ม + Migration: เพิ่ม attended_status
--
--  วิธีรัน (เลือกวิธีใดวิธีหนึ่ง):
--
--  [A] ถ้าใช้ Docker (ใช้กับโปรเจกต์นี้)
--      1. เปิด terminal แล้วรัน:
--         docker exec -it complab_db psql -U admin -d complab_reservation_db
--      2. วาง SQL ด้านล่างทั้งหมด แล้วกด Enter
--      3. พิมพ์ \q แล้ว Enter เพื่อออก
--
--  [B] ถ้าใช้ psql โดยตรง (ไม่มี Docker)
--      psql -h localhost -p 5432 -U admin -d complab_reservation_db -f complab-reservation-db.session.sql
--
--  [C] ถ้าใช้ pgAdmin / DBeaver / TablePlus
--      เปิดไฟล์นี้ แล้วกด Run / Execute ได้เลย
--
--  *** ข้อมูลเดิมในตารางไม่หายครับ Migration ทำแค่ ADD COLUMN ***
-- ============================================================


-- ------------------------------------------------------------
--  1. สร้างตาราง (IF NOT EXISTS = ถ้ามีแล้วจะข้ามไป)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS student_info (
    student_id VARCHAR(15) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name  VARCHAR(100) NOT NULL,
    major      VARCHAR(150)
);

CREATE TABLE IF NOT EXISTS reservations (
    id               SERIAL PRIMARY KEY,
    student_id       VARCHAR(15) REFERENCES student_info(student_id) ON DELETE CASCADE,
    reservation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    seat_no          INTEGER   NOT NULL,
    start_time       TIMESTAMP NOT NULL,
    end_time         TIMESTAMP NOT NULL,
    purpose          VARCHAR(255) NOT NULL,
    image_name       VARCHAR(255),
    -- [Migration] สถานะการเข้านั่ง บันทึกโดยระบบกล้อง
    -- NULL     = ยังไม่ทราบ (ยังไม่ถึงเวลา หรือกล้องยังไม่ได้บันทึก)
    -- 'present' = จองและมานั่งจริง
    -- 'absent'  = จองแต่ไม่มานั่ง
    attended_status  VARCHAR(10) DEFAULT NULL
        CHECK (attended_status IN ('present', 'absent'))
);

CREATE TABLE IF NOT EXISTS admins (
    staff_id      VARCHAR(20) PRIMARY KEY,
    first_name    VARCHAR(100) NOT NULL,
    last_name     VARCHAR(100) NOT NULL,
    department    VARCHAR(150),
    position      VARCHAR(100),
    username      VARCHAR(50) UNIQUE,
    password_hash VARCHAR(255),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority      INT DEFAULT 3
);

CREATE TABLE IF NOT EXISTS academic_semesters (
    id            SERIAL PRIMARY KEY,
    academic_year INTEGER NOT NULL,
    semester      VARCHAR(10) NOT NULL,
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    UNIQUE(academic_year, semester)
);

CREATE TABLE IF NOT EXISTS lab_schedules (
    id            SERIAL PRIMARY KEY,
    academic_year INTEGER,
    semester      VARCHAR(10),
    section       VARCHAR(5),
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    day_of_week   VARCHAR(15) NOT NULL,
    start_time    TIME NOT NULL,
    end_time      TIME NOT NULL,
    seat_no       INTEGER,  -- NULL = จองทั้งห้อง
    purpose       VARCHAR(255) NOT NULL,
    subject_name  VARCHAR(255),
    teacher_name  VARCHAR(255),
    note          TEXT,
    created_by    VARCHAR(20),
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by    VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS broken_seats (
    id          SERIAL PRIMARY KEY,
    seat_no     INTEGER NOT NULL,
    note        TEXT NOT NULL,
    status      VARCHAR(20) DEFAULT 'broken',
    reported_by VARCHAR(20),
    broken_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fixed_date  DATE
);

CREATE TABLE IF NOT EXISTS system_logs (
    id          SERIAL PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    file_name   VARCHAR(255),
    admin_id    VARCHAR(20) REFERENCES admins(staff_id),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details     TEXT
);


-- ------------------------------------------------------------
--  2. Migration: เพิ่ม attended_status ถ้ายังไม่มี
--     (ถ้า DB สร้างใหม่จากบล็อก 1 จะมีอยู่แล้ว ส่วนนี้จะ skip อัตโนมัติ)
-- ------------------------------------------------------------

ALTER TABLE reservations
    ADD COLUMN IF NOT EXISTS attended_status VARCHAR(10) DEFAULT NULL
        CHECK (attended_status IN ('present', 'absent'));


-- ------------------------------------------------------------
--  3. Index เพื่อให้ Query KPI เร็วขึ้น
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_reservations_attended_status
    ON reservations (attended_status);

CREATE INDEX IF NOT EXISTS idx_reservations_start_time
    ON reservations (start_time);


-- ------------------------------------------------------------
--  4. ตรวจสอบผลลัพธ์ — ควรเห็น attended_status ในผลลัพธ์
-- ------------------------------------------------------------

SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'reservations'
ORDER BY ordinal_position;


-- ------------------------------------------------------------
--  ล้างข้อมูลทั้งหมด (ปิด comment ไว้ก่อน อย่ารันถ้าไม่ต้องการ reset)
-- ------------------------------------------------------------
-- TRUNCATE TABLE system_logs, broken_seats, lab_schedules,
--                academic_semesters, reservations, student_info
--     RESTART IDENTITY CASCADE;
