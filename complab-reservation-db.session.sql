
CREATE TABLE student_info (
    student_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    major TEXT,
    total_usage_minutes INTEGER DEFAULT 0
);

CREATE TABLE reservations (
    id SERIAL PRIMARY KEY,
    student_id TEXT REFERENCES student_info(student_id),
    reservation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    seat_no INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    purpose TEXT NOT NULL
);