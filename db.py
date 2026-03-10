import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "student_predictor.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','faculty')),
        student_id TEXT,
        full_name TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        course TEXT,
        semester INTEGER,
        email TEXT,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS academic_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        semester INTEGER NOT NULL,
        academic_year TEXT,
        attendance REAL DEFAULT 0,
        study_hours REAL DEFAULT 0,
        class_participation REAL DEFAULT 0,
        homework_completion REAL DEFAULT 0,
        quiz_score REAL DEFAULT 0,
        assignment_score REAL DEFAULT 0,
        midterm_score REAL DEFAULT 0,
        final_score REAL DEFAULT 0,
        internal_score REAL DEFAULT 0,
        gpa REAL DEFAULT 0,
        performance TEXT,
        predicted_performance TEXT,
        prediction_probability REAL,
        risk_level TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        semester INTEGER,
        recommendation_text TEXT,
        category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed default faculty user
    faculty_pass = hashlib.sha256("faculty123".encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, password_hash, role, full_name, email) VALUES (?,?,?,?,?)",
                  ("faculty", faculty_pass, "faculty", "Dr. Admin Faculty", "faculty@university.edu"))
    except:
        pass

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()
