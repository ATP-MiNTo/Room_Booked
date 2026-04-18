CREATE TABLE IF NOT EXISTS student_info (
    student_id VARCHAR(15) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    major VARCHAR(150)
);

CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(15) REFERENCES student_info(student_id) ON DELETE CASCADE,
    reservation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    seat_no INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    image_name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS admins (
    staff_id VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    department VARCHAR(150),
    position VARCHAR(100),
    username VARCHAR(50) UNIQUE,
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority INT DEFAULT 3
);

CREATE TABLE IF NOT EXISTS academic_semesters (
    id SERIAL PRIMARY KEY,
    academic_year INTEGER NOT NULL,
    semester VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    UNIQUE(academic_year, semester)
);

CREATE TABLE IF NOT EXISTS lab_schedules (
    id SERIAL PRIMARY KEY,
    academic_year INTEGER,
    semester VARCHAR(10),
    section VARCHAR(5),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    day_of_week VARCHAR(15) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    seat_no INTEGER,  -- NULL = จองทั้งห้อง
    purpose VARCHAR(255) NOT NULL,
    subject_name VARCHAR(255),
    teacher_name VARCHAR(255),
    note TEXT,
    created_by VARCHAR(20),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS broken_seats (
    id SERIAL PRIMARY KEY,
    seat_no INTEGER NOT NULL,
    note TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'broken',
    reported_by VARCHAR(20),
    broken_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fixed_date DATE
);

CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    file_name VARCHAR(255),
    admin_id VARCHAR(20) REFERENCES admins(staff_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- ล้างข้อมูล (ยกเว้น admins)
-- TRUNCATE TABLE system_logs, broken_seats, lab_schedules, academic_semesters, reservations, student_info RESTART IDENTITY CASCADE;
