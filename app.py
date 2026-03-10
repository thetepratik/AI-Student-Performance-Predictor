from flask import Flask, request, jsonify, send_from_directory, render_template 
from flask_cors import CORS
import hashlib
import sqlite3
import os
import sys
import json
import csv
import io
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db import get_connection, init_db
from ml_model import predict_performance, train_model, get_feature_importance, get_class_analytics

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="/")
CORS(app, origins="*")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def make_response_ok(data=None, message="Success"):
    return jsonify({"success": True, "message": message, "data": data})

def make_response_err(message="Error", code=400):
    return jsonify({"success": False, "message": message}), code

# ─── AUTH ───────────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    body = request.json or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or not password:
        return make_response_err("Username and password required")
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not user or user["password_hash"] != hash_password(password):
        return make_response_err("Invalid credentials", 401)
    return make_response_ok({
        "id": user["id"], "username": user["username"],
        "role": user["role"], "full_name": user["full_name"],
        "email": user["email"], "student_id": user["student_id"]
    })

@app.route("/api/auth/register", methods=["POST"])
def register():
    body = request.json or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")
    role = body.get("role", "student")
    full_name = body.get("full_name", "")
    email = body.get("email", "")
    student_id = body.get("student_id", "")

    if not username or not password:
        return make_response_err("Username and password required")
    if role not in ("student", "faculty"):
        return make_response_err("Invalid role")

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username,password_hash,role,full_name,email,student_id) VALUES (?,?,?,?,?,?)",
            (username, hash_password(password), role, full_name, email, student_id)
        )
        conn.commit()

        # If student, ensure student record exists
        if role == "student" and student_id:
            existing = conn.execute("SELECT id FROM students WHERE student_id=?", (student_id,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO students (student_id,name,email) VALUES (?,?,?)",
                    (student_id, full_name, email)
                )
                conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return make_response_err("Username already exists")
    conn.close()
    return make_response_ok(message="Registration successful")

# ─── STUDENTS ───────────────────────────────────────────────────────────────

@app.route("/api/students", methods=["GET"])
def get_students():
    conn = get_connection()
    students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    conn.close()
    return make_response_ok([dict(s) for s in students])

@app.route("/api/students/<student_id>", methods=["GET"])
def get_student(student_id):
    conn = get_connection()
    student = conn.execute("SELECT * FROM students WHERE student_id=?", (student_id,)).fetchone()
    if not student:
        conn.close()
        return make_response_err("Student not found", 404)
    records = conn.execute(
        "SELECT * FROM academic_records WHERE student_id=? ORDER BY semester",
        (student_id,)
    ).fetchall()
    conn.close()
    return make_response_ok({
        "student": dict(student),
        "records": [dict(r) for r in records]
    })

@app.route("/api/students", methods=["POST"])
def add_student():
    body = request.json or {}
    required = ["student_id", "name"]
    for f in required:
        if not body.get(f):
            return make_response_err(f"Missing required field: {f}")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO students (student_id,name,age,gender,course,semester,email,phone) VALUES (?,?,?,?,?,?,?,?)",
            (body["student_id"], body["name"], body.get("age"), body.get("gender"),
             body.get("course"), body.get("semester", 1), body.get("email"), body.get("phone"))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return make_response_err("Student ID already exists")
    conn.close()
    return make_response_ok(message="Student added successfully")

@app.route("/api/students/<student_id>", methods=["PUT"])
def update_student(student_id):
    body = request.json or {}
    conn = get_connection()
    conn.execute(
        "UPDATE students SET name=?,age=?,gender=?,course=?,semester=?,email=?,phone=?,updated_at=CURRENT_TIMESTAMP WHERE student_id=?",
        (body.get("name"), body.get("age"), body.get("gender"), body.get("course"),
         body.get("semester"), body.get("email"), body.get("phone"), student_id)
    )
    conn.commit()
    conn.close()
    return make_response_ok(message="Student updated")

@app.route("/api/students/<student_id>", methods=["DELETE"])
def delete_student(student_id):
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE student_id=?", (student_id,))
    conn.execute("DELETE FROM academic_records WHERE student_id=?", (student_id,))
    conn.commit()
    conn.close()
    return make_response_ok(message="Student deleted")

# ─── ACADEMIC RECORDS ───────────────────────────────────────────────────────

@app.route("/api/records/<student_id>", methods=["POST"])
def add_record(student_id):
    body = request.json or {}

    # Build prediction input
    pred_input = {
        "Attendance": float(body.get("attendance", 0)),
        "StudyHours": float(body.get("study_hours", 0)),
        "ClassParticipation": float(body.get("class_participation", 0)),
        "HomeworkCompletion": float(body.get("homework_completion", 0)),
        "QuizScore": float(body.get("quiz_score", 0)),
        "AssignmentScore": float(body.get("assignment_score", 0)),
        "MidtermScore": float(body.get("midterm_score", 0)),
        "InternalScore": float(body.get("internal_score", 0)),
    }
    prediction = predict_performance(pred_input)

    # Calculate GPA
    quiz = float(body.get("quiz_score", 0))
    assign = float(body.get("assignment_score", 0))
    mid = float(body.get("midterm_score", 0))
    final = float(body.get("final_score", 0))
    gpa = round(min(10, (quiz * 0.1 + assign * 0.2 + mid * 0.3 + final * 0.4) / 10), 2)

    # Performance from actual scores
    if gpa >= 8.0:
        actual_perf = "Excellent"
    elif gpa >= 6.0:
        actual_perf = "Good"
    elif gpa >= 4.0:
        actual_perf = "Average"
    else:
        actual_perf = "At Risk"

    conn = get_connection()
    semester = int(body.get("semester", 1))

    # Upsert
    existing = conn.execute(
        "SELECT id FROM academic_records WHERE student_id=? AND semester=?", (student_id, semester)
    ).fetchone()

    if existing:
        conn.execute("""UPDATE academic_records SET
            attendance=?,study_hours=?,class_participation=?,homework_completion=?,
            quiz_score=?,assignment_score=?,midterm_score=?,final_score=?,internal_score=?,
            gpa=?,performance=?,predicted_performance=?,prediction_probability=?,risk_level=?,academic_year=?
            WHERE student_id=? AND semester=?""",
            (pred_input["Attendance"], pred_input["StudyHours"], pred_input["ClassParticipation"],
             pred_input["HomeworkCompletion"], pred_input["QuizScore"], pred_input["AssignmentScore"],
             pred_input["MidtermScore"], float(body.get("final_score", 0)), pred_input["InternalScore"],
             gpa, actual_perf, prediction["predicted_performance"],
             prediction["confidence"], prediction["risk_level"],
             body.get("academic_year", "2024-25"), student_id, semester))
    else:
        conn.execute("""INSERT INTO academic_records
            (student_id,semester,academic_year,attendance,study_hours,class_participation,homework_completion,
            quiz_score,assignment_score,midterm_score,final_score,internal_score,gpa,performance,
            predicted_performance,prediction_probability,risk_level)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (student_id, semester, body.get("academic_year", "2024-25"),
             pred_input["Attendance"], pred_input["StudyHours"], pred_input["ClassParticipation"],
             pred_input["HomeworkCompletion"], pred_input["QuizScore"], pred_input["AssignmentScore"],
             pred_input["MidtermScore"], float(body.get("final_score", 0)), pred_input["InternalScore"],
             gpa, actual_perf, prediction["predicted_performance"],
             prediction["confidence"], prediction["risk_level"]))

    conn.commit()
    conn.close()

    return make_response_ok({**prediction, "gpa": gpa, "performance": actual_perf})

@app.route("/api/predict", methods=["POST"])
def predict():
    body = request.json or {}
    pred_input = {
        "Attendance": float(body.get("attendance", 75)),
        "StudyHours": float(body.get("study_hours", 3)),
        "ClassParticipation": float(body.get("class_participation", 5)),
        "HomeworkCompletion": float(body.get("homework_completion", 70)),
        "QuizScore": float(body.get("quiz_score", 60)),
        "AssignmentScore": float(body.get("assignment_score", 60)),
        "MidtermScore": float(body.get("midterm_score", 60)),
        "InternalScore": float(body.get("internal_score", 60)),
    }
    result = predict_performance(pred_input)
    return make_response_ok(result)

# ─── ANALYTICS ──────────────────────────────────────────────────────────────

@app.route("/api/analytics/class", methods=["GET"])
def class_analytics():
    conn = get_connection()
    records = conn.execute("SELECT * FROM academic_records").fetchall()
    conn.close()
    stats = get_class_analytics([dict(r) for r in records])
    return make_response_ok(stats)

@app.route("/api/analytics/feature-importance", methods=["GET"])
def feature_importance():
    importance = get_feature_importance()
    return make_response_ok(importance)

@app.route("/api/analytics/at-risk", methods=["GET"])
def at_risk_students():
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.student_id, s.name, s.course, s.semester,
               ar.attendance, ar.gpa, ar.risk_level, ar.predicted_performance,
               ar.study_hours, ar.assignment_score
        FROM students s
        JOIN academic_records ar ON s.student_id = ar.student_id
        WHERE ar.risk_level IN ('High','Medium')
        ORDER BY ar.risk_level DESC, ar.gpa ASC
    """).fetchall()
    conn.close()
    return make_response_ok([dict(r) for r in rows])

@app.route("/api/analytics/top-performers", methods=["GET"])
def top_performers():
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.student_id, s.name, s.course,
               ar.gpa, ar.performance, ar.attendance, ar.study_hours
        FROM students s
        JOIN academic_records ar ON s.student_id = ar.student_id
        WHERE ar.performance IN ('Excellent','Good')
        ORDER BY ar.gpa DESC LIMIT 10
    """).fetchall()
    conn.close()
    return make_response_ok([dict(r) for r in rows])

@app.route("/api/analytics/overview", methods=["GET"])
def overview():
    conn = get_connection()
    total_students = conn.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"]
    total_records = conn.execute("SELECT COUNT(*) as c FROM academic_records").fetchone()["c"]
    avg_gpa = conn.execute("SELECT AVG(gpa) as a FROM academic_records").fetchone()["a"] or 0
    at_risk = conn.execute("SELECT COUNT(*) as c FROM academic_records WHERE risk_level='High'").fetchone()["c"]
    perf_dist = conn.execute("SELECT performance, COUNT(*) as c FROM academic_records GROUP BY performance").fetchall()
    conn.close()
    return make_response_ok({
        "total_students": total_students,
        "total_records": total_records,
        "avg_gpa": round(avg_gpa, 2),
        "at_risk_count": at_risk,
        "performance_distribution": {row["performance"]: row["c"] for row in perf_dist}
    })

# ─── CSV IMPORT ─────────────────────────────────────────────────────────────

@app.route("/api/import/csv", methods=["POST"])
def import_csv():
    if "file" not in request.files:
        return make_response_err("No file uploaded")
    file = request.files["file"]
    content = file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    imported = 0
    errors = []

    conn = get_connection()
    for i, row in enumerate(reader):
        try:
            sid = row.get("StudentID", "").strip()
            if not sid:
                continue
            # Upsert student
            existing = conn.execute("SELECT id FROM students WHERE student_id=?", (sid,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO students (student_id,name,age,gender,course,semester) VALUES (?,?,?,?,?,?)",
                    (sid, row.get("Name","Unknown"), row.get("Age"), row.get("Gender"),
                     row.get("Course"), row.get("Semester",1))
                )
            # Build prediction input
            pred_input = {
                "Attendance": float(row.get("Attendance",0)),
                "StudyHours": float(row.get("StudyHours",0)),
                "ClassParticipation": float(row.get("ClassParticipation",5)),
                "HomeworkCompletion": float(row.get("HomeworkCompletion",70)),
                "QuizScore": float(row.get("QuizScore",0)),
                "AssignmentScore": float(row.get("AssignmentScore",0)),
                "MidtermScore": float(row.get("MidtermScore",0)),
                "InternalScore": float(row.get("InternalScore",0)),
            }
            prediction = predict_performance(pred_input)
            final_score = float(row.get("FinalScore", row.get("Final",0)))
            gpa = float(row.get("GPA",0)) or round(
                min(10, (pred_input["QuizScore"]*0.1 + pred_input["AssignmentScore"]*0.2 +
                         pred_input["MidtermScore"]*0.3 + final_score*0.4) / 10), 2)
            perf = row.get("Performance","") or prediction["predicted_performance"]

            semester = int(row.get("Semester",1))
            existing_rec = conn.execute("SELECT id FROM academic_records WHERE student_id=? AND semester=?", (sid, semester)).fetchone()
            if existing_rec:
                conn.execute("""UPDATE academic_records SET
                    attendance=?,study_hours=?,class_participation=?,homework_completion=?,
                    quiz_score=?,assignment_score=?,midterm_score=?,final_score=?,internal_score=?,
                    gpa=?,performance=?,predicted_performance=?,prediction_probability=?,risk_level=?
                    WHERE student_id=? AND semester=?""",
                    (pred_input["Attendance"], pred_input["StudyHours"], pred_input["ClassParticipation"],
                     pred_input["HomeworkCompletion"], pred_input["QuizScore"], pred_input["AssignmentScore"],
                     pred_input["MidtermScore"], final_score, pred_input["InternalScore"],
                     gpa, perf, prediction["predicted_performance"], prediction["confidence"],
                     prediction["risk_level"], sid, semester))
            else:
                conn.execute("""INSERT INTO academic_records
                    (student_id,semester,attendance,study_hours,class_participation,homework_completion,
                    quiz_score,assignment_score,midterm_score,final_score,internal_score,gpa,performance,
                    predicted_performance,prediction_probability,risk_level)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sid, semester, pred_input["Attendance"], pred_input["StudyHours"],
                     pred_input["ClassParticipation"], pred_input["HomeworkCompletion"],
                     pred_input["QuizScore"], pred_input["AssignmentScore"],
                     pred_input["MidtermScore"], final_score, pred_input["InternalScore"],
                     gpa, perf, prediction["predicted_performance"], prediction["confidence"],
                     prediction["risk_level"]))
            imported += 1
        except Exception as e:
            errors.append(f"Row {i+2}: {str(e)}")

    conn.commit()
    conn.close()
    return make_response_ok({"imported": imported, "errors": errors[:10]})

@app.route("/api/model/retrain", methods=["POST"])
def retrain():
    result = train_model()
    return make_response_ok(result)

# @app.route("/", defaults={"path": ""})
# @app.route("/<path:path>")
# def serve(path):
#     dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
#     if path and os.path.exists(os.path.join(dist, path)):
#         return send_from_directory(dist, path)
#     return send_from_directory(dist, "index.html")

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)

@app.route("/")
def home():
    return render_template("index.html")