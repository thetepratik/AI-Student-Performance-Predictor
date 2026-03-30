"""
Enhanced database schema for 10 new features:
1. SHAP explainability data
2. Dropout predictions
3. Behavioral engagement metrics
4. Goal-setting & streaks
5. Faculty interventions
6. Cohort snapshots (historical)
7. Student engagement logs
8. Chatbot interactions
9. PDF reports
10. Subject weakness records
"""

import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "student_predictor.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_enhanced_db():
    """Extend existing database with new tables for 10 features"""
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
    -- 1. SHAP explainability: Store SHAP values per student prediction
    CREATE TABLE IF NOT EXISTS shap_explanations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        semester INTEGER NOT NULL,
        feature_name TEXT NOT NULL,
        shap_value REAL NOT NULL,
        feature_value REAL,
        base_value REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    -- 2. Dropout prediction: Separate model predictions for course dropout
    CREATE TABLE IF NOT EXISTS dropout_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        semester INTEGER NOT NULL,
        dropout_probability REAL NOT NULL,
        dropout_risk_level TEXT CHECK(dropout_risk_level IN ('Low','Medium','High')),
        contributing_factors TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    -- 3. Behavioral engagement: Derived from login/activity logs
    CREATE TABLE IF NOT EXISTS behavioral_engagement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        date DATE NOT NULL,
        login_count INTEGER DEFAULT 0,
        platform_minutes INTEGER DEFAULT 0,
        assignment_submit_hours_early INTEGER DEFAULT 0,
        message_activity_count INTEGER DEFAULT 0,
        quiz_attempt_count INTEGER DEFAULT 0,
        engagement_score REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    -- 4. Goal-setting & streaks: Gamification features
    CREATE TABLE IF NOT EXISTS student_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        goal_type TEXT NOT NULL,
        goal_description TEXT,
        target_value REAL NOT NULL,
        current_value REAL DEFAULT 0.0,
        status TEXT DEFAULT 'active' CHECK(status IN ('active','completed','abandoned')),
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        target_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    CREATE TABLE IF NOT EXISTS study_streaks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        streak_type TEXT NOT NULL,
        current_streak INTEGER DEFAULT 0,
        max_streak INTEGER DEFAULT 0,
        last_activity_date DATE,
        badge_earned TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    -- 5. Faculty intervention tracker: Link interventions to outcomes
    CREATE TABLE IF NOT EXISTS faculty_interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_id INTEGER NOT NULL,
        student_id TEXT NOT NULL,
        semester INTEGER NOT NULL,
        intervention_type TEXT NOT NULL CHECK(intervention_type IN 
            ('counseling','tutoring','parental_contact','extra_tutoring','course_change','other')),
        description TEXT,
        intervention_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        follow_up_date TIMESTAMP,
        outcome_notes TEXT,
        effectiveness_score INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (faculty_id) REFERENCES users(id),
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    -- 6. Cohort snapshots: Historical comparison
    CREATE TABLE IF NOT EXISTS cohort_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester INTEGER NOT NULL,
        academic_year TEXT NOT NULL,
        snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        avg_gpa REAL,
        avg_attendance REAL,
        dropout_count INTEGER DEFAULT 0,
        at_risk_count INTEGER DEFAULT 0,
        excellent_count INTEGER DEFAULT 0,
        good_count INTEGER DEFAULT 0,
        average_count INTEGER DEFAULT 0,
        performance_distribution TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 7. Engagement activity log: Raw login/activity tracking
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        activity_type TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    -- 8. Chatbot interactions: Store AI tutor conversations
    CREATE TABLE IF NOT EXISTS chatbot_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        message TEXT NOT NULL,
        response TEXT NOT NULL,
        weak_subject TEXT,
        helpful_rating INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    -- 9. Generated reports: Track PDF reports sent
    CREATE TABLE IF NOT EXISTS generated_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        semester INTEGER NOT NULL,
        report_type TEXT DEFAULT 'comprehensive',
        file_path TEXT,
        gpa_snapshot REAL,
        risk_level_snapshot TEXT,
        narrative TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sent_to_parent INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    -- 10. Subject weakness heatmap: Per-subject performance tracking
    CREATE TABLE IF NOT EXISTS subject_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        semester INTEGER NOT NULL,
        subject TEXT NOT NULL,
        assignment_avg REAL DEFAULT 0.0,
        quiz_avg REAL DEFAULT 0.0,
        exam_score REAL DEFAULT 0.0,
        participation_level REAL DEFAULT 0.0,
        overall_score REAL DEFAULT 0.0,
        weakness_flag INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    -- Peer benchmarking data
    CREATE TABLE IF NOT EXISTS peer_benchmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester INTEGER NOT NULL,
        metric TEXT NOT NULL,
        class_avg REAL NOT NULL,
        top_quartile REAL NOT NULL,
        bottom_quartile REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Early warning alerts for risk patterns
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        semester INTEGER NOT NULL,
        alert TEXT NOT NULL,
        severity TEXT CHECK(severity IN ('Low','Medium','High')) NOT NULL,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );
    """)

    conn.commit()
    conn.close()
    print("Enhanced database initialized successfully!")

if __name__ == "__main__":
    init_enhanced_db()
