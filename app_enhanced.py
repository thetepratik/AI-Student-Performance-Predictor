"""
Flask API extensions for 10 new features:
1. SHAP explainability endpoint
2. Dropout prediction endpoint
3. Peer benchmarking endpoint
4. Goal-setting & streaks endpoints
5. AI chatbot tutor endpoint
6. Faculty intervention tracking
7. Behavioral engagement scoring
8. PDF report generation
9. Subject weakness heatmap
10. Cohort comparison

Add these to your existing app.py
"""

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
import sqlite3
from db_enhanced import get_connection as get_enhanced_connection
from ml_model_enhanced import (
    get_shap_explanation, 
    predict_dropout, 
    calculate_behavioral_engagement
)

# ─── 1. SHAP EXPLAINABILITY ENDPOINTS ────────────────────────────────────────

def shap_explainability_blueprint(app):
    """SHAP-based local feature attribution for students"""
    
    @app.route("/api/explainability/shap/<student_id>/<semester>", methods=["GET"])
    def get_shap_explanation_endpoint(student_id, semester):
        """
        Get SHAP waterfall explanation for a student's risk score.
        Shows how each feature (attendance, study hours, etc.) contributed
        to their specific prediction.
        """
        conn = get_enhanced_connection()
        record = conn.execute("""
            SELECT * FROM academic_records 
            WHERE student_id=? AND semester=?
        """, (student_id, int(semester))).fetchone()
        conn.close()
        
        if not record:
            return jsonify({"success": False, "message": "Record not found"}), 404
        
        student_data = {
            "Attendance": record["attendance"],
            "StudyHours": record["study_hours"],
            "ClassParticipation": record["class_participation"],
            "HomeworkCompletion": record["homework_completion"],
            "QuizScore": record["quiz_score"],
            "AssignmentScore": record["assignment_score"],
            "MidtermScore": record["midterm_score"],
            "InternalScore": record["internal_score"]
        }
        
        shap_exp = get_shap_explanation(student_data)
        
        if shap_exp is None:
            return jsonify({
                "success": False,
                "message": "SHAP not available. Install with: pip install shap"
            }), 400
        
        return jsonify({
            "success": True,
            "student_id": student_id,
            "semester": semester,
            "explanation": shap_exp
        })

    @app.route("/api/explainability/waterfall", methods=["POST"])
    def get_waterfall_chart_data():
        """Get data formatted for waterfall chart visualization"""
        body = request.json or {}
        student_data = body.get("student_data", {})
        
        shap_exp = get_shap_explanation(student_data)
        if shap_exp is None:
            return jsonify({"success": False, "message": "SHAP not available"}), 400
        
        # Format for waterfall chart (Plotly/Chart.js compatible)
        predicted_class = max(shap_exp.keys(), 
                             key=lambda k: shap_exp[k]["base_value"])
        
        explanation = shap_exp[predicted_class]
        waterfall_data = {
            "base_value": explanation["base_value"],
            "features": explanation["top_3_factors"],
            "predicted_class": predicted_class
        }
        
        return jsonify({"success": True, "waterfall": waterfall_data})

# ─── 2. DROPOUT PREDICTION ENDPOINTS ─────────────────────────────────────────

def dropout_prediction_blueprint(app):
    """Separate dropout risk from grade performance"""
    
    @app.route("/api/dropout/predict/<student_id>/<semester>", methods=["GET"])
    def predict_dropout_endpoint(student_id, semester):
        """Predict course dropout probability"""
        conn = get_enhanced_connection()
        record = conn.execute("""
            SELECT * FROM academic_records 
            WHERE student_id=? AND semester=?
        """, (student_id, int(semester))).fetchone()
        conn.close()
        
        if not record:
            return jsonify({"success": False, "message": "Record not found"}), 404
        
        student_data = {
            "Attendance": record["attendance"],
            "StudyHours": record["study_hours"],
            "ClassParticipation": record["class_participation"],
            "HomeworkCompletion": record["homework_completion"],
            "QuizScore": record["quiz_score"],
            "AssignmentScore": record["assignment_score"],
            "MidtermScore": record["midterm_score"],
            "InternalScore": record["internal_score"]
        }
        
        dropout_pred = predict_dropout(student_data)
        
        # Store in database
        conn = get_enhanced_connection()
        conn.execute("""
            INSERT OR REPLACE INTO dropout_predictions 
            (student_id, semester, dropout_probability, dropout_risk_level, contributing_factors)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, int(semester), dropout_pred["dropout_probability"], 
              dropout_pred["dropout_risk_level"], 
              json.dumps(dropout_pred["contributing_factors"])))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "student_id": student_id,
            "dropout_prediction": dropout_pred
        })

    @app.route("/api/dropout/at-risk", methods=["GET"])
    def get_dropout_at_risk_students():
        """Get all students at high risk of dropout"""
        conn = get_enhanced_connection()
        rows = conn.execute("""
            SELECT dp.student_id, s.name, s.course, dp.dropout_probability, 
                   dp.dropout_risk_level, ar.gpa
            FROM dropout_predictions dp
            JOIN students s ON dp.student_id = s.student_id
            JOIN academic_records ar ON dp.student_id = ar.student_id
            WHERE dp.dropout_risk_level IN ('High', 'Medium')
            ORDER BY dp.dropout_probability DESC
        """).fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "at_risk_students": [dict(r) for r in rows]
        })

# ─── 3. PEER BENCHMARKING ENDPOINTS ──────────────────────────────────────────

def peer_benchmarking_blueprint(app):
    """Show students their metrics vs class average and top quartile"""
    
    @app.route("/api/benchmarking/student/<student_id>/<semester>", methods=["GET"])
    def get_peer_benchmark(student_id, semester):
        """
        Get radar chart data: student's 8 metrics vs class average vs top quartile
        """
        conn = get_enhanced_connection()
        
        # Get student record
        student_rec = conn.execute("""
            SELECT * FROM academic_records 
            WHERE student_id=? AND semester=?
        """, (student_id, int(semester))).fetchone()
        
        if not student_rec:
            conn.close()
            return jsonify({"success": False, "message": "Record not found"}), 404
        
        # Get class statistics
        class_stats = conn.execute("""
            SELECT 
                AVG(attendance) as avg_attendance,
                AVG(study_hours) as avg_study_hours,
                AVG(class_participation) as avg_participation,
                AVG(homework_completion) as avg_homework,
                AVG(quiz_score) as avg_quiz,
                AVG(assignment_score) as avg_assignment,
                AVG(midterm_score) as avg_midterm,
                AVG(internal_score) as avg_internal
            FROM academic_records WHERE semester=?
        """, (int(semester),)).fetchone()
        
        # Top quartile (75th percentile)
        top_quartile = conn.execute("""
            SELECT 
                PERCENTILE_CONT(0.75) WITHIN GROUP(ORDER BY attendance) as q75_attendance,
                PERCENTILE_CONT(0.75) WITHIN GROUP(ORDER BY study_hours) as q75_study_hours,
                PERCENTILE_CONT(0.75) WITHIN GROUP(ORDER BY class_participation) as q75_participation,
                PERCENTILE_CONT(0.75) WITHIN GROUP(ORDER BY homework_completion) as q75_homework,
                PERCENTILE_CONT(0.75) WITHIN GROUP(ORDER BY quiz_score) as q75_quiz,
                PERCENTILE_CONT(0.75) WITHIN GROUP(ORDER BY assignment_score) as q75_assignment,
                PERCENTILE_CONT(0.75) WITHIN GROUP(ORDER BY midterm_score) as q75_midterm,
                PERCENTILE_CONT(0.75) WITHIN GROUP(ORDER BY internal_score) as q75_internal
            FROM academic_records WHERE semester=?
        """, (int(semester),)).fetchone()
        conn.close()
        
        metrics = {
            "Attendance": {
                "student": student_rec["attendance"],
                "class_avg": class_stats["avg_attendance"] or 0,
                "top_quartile": top_quartile["q75_attendance"] or 0
            },
            "Study Hours": {
                "student": student_rec["study_hours"],
                "class_avg": class_stats["avg_study_hours"] or 0,
                "top_quartile": top_quartile["q75_study_hours"] or 0
            },
            "Participation": {
                "student": student_rec["class_participation"],
                "class_avg": class_stats["avg_participation"] or 0,
                "top_quartile": top_quartile["q75_participation"] or 0
            },
            "Homework": {
                "student": student_rec["homework_completion"],
                "class_avg": class_stats["avg_homework"] or 0,
                "top_quartile": top_quartile["q75_homework"] or 0
            },
            "Quiz Score": {
                "student": student_rec["quiz_score"],
                "class_avg": class_stats["avg_quiz"] or 0,
                "top_quartile": top_quartile["q75_quiz"] or 0
            },
            "Assignment": {
                "student": student_rec["assignment_score"],
                "class_avg": class_stats["avg_assignment"] or 0,
                "top_quartile": top_quartile["q75_assignment"] or 0
            },
            "Midterm": {
                "student": student_rec["midterm_score"],
                "class_avg": class_stats["avg_midterm"] or 0,
                "top_quartile": top_quartile["q75_midterm"] or 0
            },
            "Internal": {
                "student": student_rec["internal_score"],
                "class_avg": class_stats["avg_internal"] or 0,
                "top_quartile": top_quartile["q75_internal"] or 0
            }
        }
        
        return jsonify({
            "success": True,
            "student_id": student_id,
            "semester": semester,
            "benchmarks": metrics
        })

# ─── 4. GOAL-SETTING & STREAKS ENDPOINTS ────────────────────────────────────

def gamification_blueprint(app):
    """Gamified learning: goals, streaks, badges"""
    
    @app.route("/api/goals/<student_id>", methods=["GET"])
    def get_student_goals(student_id):
        """Get active goals for a student"""
        conn = get_enhanced_connection()
        goals = conn.execute("""
            SELECT * FROM student_goals 
            WHERE student_id=? AND status='active'
            ORDER BY target_date ASC
        """, (student_id,)).fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "goals": [dict(g) for g in goals]
        })

    @app.route("/api/goals", methods=["POST"])
    def create_goal():
        """Create a new learning goal"""
        body = request.json or {}
        student_id = body.get("student_id")
        goal_type = body.get("goal_type")  # "attendance", "study_hours", "assignment", etc.
        target_value = float(body.get("target_value", 0))
        target_date = body.get("target_date")
        
        conn = get_enhanced_connection()
        conn.execute("""
            INSERT INTO student_goals 
            (student_id, goal_type, target_value, target_date, status)
            VALUES (?, ?, ?, ?, 'active')
        """, (student_id, goal_type, target_value, target_date))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Goal created"})

    @app.route("/api/streaks/<student_id>", methods=["GET"])
    def get_student_streaks(student_id):
        """Get study streaks and badges"""
        conn = get_enhanced_connection()
        streaks = conn.execute("""
            SELECT * FROM study_streaks WHERE student_id=?
        """, (student_id,)).fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "streaks": [dict(s) for s in streaks]
        })

    @app.route("/api/streaks/update", methods=["POST"])
    def update_streak():
        """Update study streak (called after successful study session)"""
        body = request.json or {}
        student_id = body.get("student_id")
        streak_type = body.get("streak_type")  # "daily_login", "assignments", etc.
        
        conn = get_enhanced_connection()
        existing = conn.execute("""
            SELECT * FROM study_streaks 
            WHERE student_id=? AND streak_type=?
        """, (student_id, streak_type)).fetchone()
        
        today = datetime.now().date()
        
        if existing:
            last_activity = existing["last_activity_date"]
            if last_activity == str(today):
                # Same day, no update
                current_streak = existing["current_streak"]
            elif last_activity == str(today - timedelta(days=1)):
                # Consecutive day
                current_streak = existing["current_streak"] + 1
            else:
                # Streak broken
                current_streak = 1
            
            max_streak = max(existing["max_streak"], current_streak)
            
            # Award badges
            badge = None
            if current_streak == 7:
                badge = "Week Warrior"
            elif current_streak == 30:
                badge = "Monthly Master"
            elif current_streak == 100:
                badge = "Century Champion"
            
            conn.execute("""
                UPDATE study_streaks 
                SET current_streak=?, max_streak=?, last_activity_date=?, badge_earned=?
                WHERE student_id=? AND streak_type=?
            """, (current_streak, max_streak, today, badge, student_id, streak_type))
        else:
            conn.execute("""
                INSERT INTO study_streaks 
                (student_id, streak_type, current_streak, max_streak, last_activity_date)
                VALUES (?, ?, 1, 1, ?)
            """, (student_id, streak_type, today))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Streak updated"})

# ─── 5. AI CHATBOT TUTOR ENDPOINTS ──────────────────────────────────────────

def chatbot_tutor_blueprint(app):
    """In-app AI tutor using Anthropic API"""
    
    @app.route("/api/tutor/chat", methods=["POST"])
    def chat_with_tutor():
        """
        AI tutor endpoint - uses Anthropic API
        Inject student's weak subjects from their profile
        """
        try:
            import anthropic
        except ImportError:
            return jsonify({
                "success": False,
                "message": "Anthropic API not installed. Install with: pip install anthropic"
            }), 400
        
        body = request.json or {}
        student_id = body.get("student_id")
        user_message = body.get("message", "")
        
        # Get student's weak subjects
        conn = get_enhanced_connection()
        records = conn.execute("""
            SELECT ar.quiz_score, ar.assignment_score, ar.midterm_score, 
                   sp.subject, sp.overall_score
            FROM academic_records ar
            LEFT JOIN subject_performance sp ON ar.student_id = sp.student_id
            WHERE ar.student_id = ?
        """, (student_id,)).fetchall()
        conn.close()
        
        weak_subjects = []
        if records:
            weak_subjects = [r["subject"] for r in records if r["overall_score"] and r["overall_score"] < 60]
        
        # Create Anthropic client
        client = anthropic.Anthropic()
        
        system_prompt = f"""You are an AI tutor helping a student improve their academic performance.
Student weak areas: {', '.join(weak_subjects) if weak_subjects else 'General subjects'}

Provide clear, concise explanations and actionable advice. Be encouraging and supportive.
Keep responses under 200 words."""
        
        message = client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=300,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        tutor_response = message.content[0].text
        
        # Store interaction
        conn = get_enhanced_connection()
        conn.execute("""
            INSERT INTO chatbot_interactions 
            (student_id, message, response, weak_subject)
            VALUES (?, ?, ?, ?)
        """, (student_id, user_message, tutor_response, 
              weak_subjects[0] if weak_subjects else None))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "response": tutor_response,
            "weak_subjects": weak_subjects
        })

    @app.route("/api/tutor/history/<student_id>", methods=["GET"])
    def get_tutor_history(student_id):
        """Get conversation history with AI tutor"""
        conn = get_enhanced_connection()
        interactions = conn.execute("""
            SELECT message, response, weak_subject, timestamp
            FROM chatbot_interactions
            WHERE student_id=?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (student_id,)).fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "history": [dict(i) for i in interactions]
        })

# ─── 6. FACULTY INTERVENTION TRACKER ─────────────────────────────────────────

def intervention_tracker_blueprint(app):
    """Track faculty interventions and measure effectiveness"""
    
    @app.route("/api/interventions", methods=["POST"])
    def log_intervention():
        """Faculty logs an intervention"""
        body = request.json or {}
        
        conn = get_enhanced_connection()
        conn.execute("""
            INSERT INTO faculty_interventions 
            (faculty_id, student_id, semester, intervention_type, description, follow_up_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (body["faculty_id"], body["student_id"], body["semester"],
              body["intervention_type"], body.get("description"),
              body.get("follow_up_date")))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Intervention logged"})

    @app.route("/api/interventions/<student_id>", methods=["GET"])
    def get_student_interventions(student_id):
        """Get all interventions for a student"""
        conn = get_enhanced_connection()
        interventions = conn.execute("""
            SELECT * FROM faculty_interventions
            WHERE student_id=?
            ORDER BY intervention_date DESC
        """, (student_id,)).fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "interventions": [dict(i) for i in interventions]
        })

    @app.route("/api/interventions/<intervention_id>/outcome", methods=["PUT"])
    def update_intervention_outcome(intervention_id):
        """Faculty updates intervention outcome and effectiveness"""
        body = request.json or {}
        
        conn = get_enhanced_connection()
        conn.execute("""
            UPDATE faculty_interventions
            SET outcome_notes=?, effectiveness_score=?
            WHERE id=?
        """, (body.get("outcome_notes"), body.get("effectiveness_score"), 
              int(intervention_id)))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Outcome recorded"})

# ─── 7. BEHAVIORAL ENGAGEMENT SCORING ────────────────────────────────────────

def engagement_scoring_blueprint(app):
    """Track and score behavioral engagement"""
    
    @app.route("/api/engagement/log", methods=["POST"])
    def log_activity():
        """Log student activity (login, assignment, quiz, etc.)"""
        body = request.json or {}
        student_id = body.get("student_id")
        activity_type = body.get("activity_type")  # login, assignment_submit, quiz_attempt, message
        
        conn = get_enhanced_connection()
        conn.execute("""
            INSERT INTO activity_logs (student_id, activity_type, details, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (student_id, activity_type, body.get("details")))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Activity logged"})

    @app.route("/api/engagement/score/<student_id>", methods=["GET"])
    def get_engagement_score(student_id):
        """
        Calculate behavioral engagement score (0-100).
        Stanford research shows behavioral signals predict performance.
        """
        conn = get_enhanced_connection()
        activities = conn.execute("""
            SELECT activity_type, COUNT(*) as count
            FROM activity_logs
            WHERE student_id=? AND timestamp > datetime('now', '-7 days')
            GROUP BY activity_type
        """, (student_id,)).fetchall()
        conn.close()
        
        activity_log = [{"type": a["activity_type"], "count": a["count"]} for a in activities]
        engagement_score = calculate_behavioral_engagement(activity_log)
        
        return jsonify({
            "success": True,
            "engagement_score": engagement_score,
            "interpretation": "High engagement" if engagement_score > 70 else 
                            "Moderate engagement" if engagement_score > 40 else
                            "Low engagement"
        })

# ─── 8. PDF REPORT GENERATION ────────────────────────────────────────────────

def pdf_report_blueprint(app):
    """Generate PDF reports with LLM narrative"""
    
    @app.route("/api/reports/generate/<student_id>/<semester>", methods=["POST"])
    def generate_student_report(student_id, semester):
        """
        Generate comprehensive PDF report with:
        - LLM-written narrative (using Anthropic API)
        - Embedded charts
        - Recommendations
        """
        try:
            import anthropic
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError:
            return jsonify({
                "success": False,
                "message": "Required libraries not installed"
            }), 400
        
        conn = get_enhanced_connection()
        record = conn.execute("""
            SELECT ar.*, s.name, s.student_id, s.course
            FROM academic_records ar
            JOIN students s ON ar.student_id = s.student_id
            WHERE ar.student_id=? AND ar.semester=?
        """, (student_id, int(semester))).fetchone()
        conn.close()
        
        if not record:
            return jsonify({"success": False, "message": "Record not found"}), 404
        
        # Generate LLM narrative
        client = anthropic.Anthropic()
        prompt = f"""Write a brief (150-200 words), encouraging narrative assessment for a student report:
        Name: {record['name']}
        Course: {record['course']}
        Semester: {semester}
        GPA: {record['gpa']}/10
        Attendance: {record['attendance']}%
        Performance Level: {record['performance']}
        Risk Level: {record['risk_level']}
        
        Include: strengths, areas for improvement, and one specific actionable recommendation."""
        
        message = client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        narrative = message.content[0].text
        
        # Create PDF
        filename = f"/tmp/report_{student_id}_{semester}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        elements.append(Paragraph(f"Academic Performance Report - {record['name']}", styles['Heading1']))
        elements.append(Spacer(1, 0.3*254))
        
        # Key metrics table
        data = [
            ["Metric", "Value"],
            ["GPA", f"{record['gpa']}/10"],
            ["Attendance", f"{record['attendance']}%"],
            ["Performance", record['performance']],
            ["Risk Level", record['risk_level']]
        ]
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*254))
        
        # Narrative
        elements.append(Paragraph("Assessment", styles['Heading2']))
        elements.append(Paragraph(narrative, styles['BodyText']))
        
        # Build PDF
        doc.build(elements)
        
        # Store in database
        conn = get_enhanced_connection()
        conn.execute("""
            INSERT INTO generated_reports 
            (student_id, semester, file_path, gpa_snapshot, risk_level_snapshot, narrative)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (student_id, int(semester), filename, record['gpa'], 
              record['risk_level'], narrative))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Report generated",
            "file_path": filename,
            "narrative": narrative
        })

# ─── 9. COHORT COMPARISON ENDPOINTS ──────────────────────────────────────────

def cohort_comparison_blueprint(app):
    """Historical semester comparison"""
    
    @app.route("/api/cohort/snapshot", methods=["POST"])
    def create_cohort_snapshot():
        """Create historical snapshot of cohort metrics"""
        body = request.json or {}
        semester = body.get("semester")
        academic_year = body.get("academic_year")
        
        conn = get_enhanced_connection()
        stats = conn.execute("""
            SELECT 
                AVG(gpa) as avg_gpa,
                AVG(attendance) as avg_attendance,
                COUNT(CASE WHEN risk_level='High' THEN 1 END) as at_risk_count,
                COUNT(CASE WHEN performance='Excellent' THEN 1 END) as excellent_count,
                COUNT(CASE WHEN performance='Good' THEN 1 END) as good_count,
                COUNT(CASE WHEN performance='Average' THEN 1 END) as average_count
            FROM academic_records
            WHERE semester=?
        """, (semester,)).fetchone()
        
        conn.execute("""
            INSERT INTO cohort_snapshots 
            (semester, academic_year, avg_gpa, avg_attendance, at_risk_count, 
             excellent_count, good_count, average_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (semester, academic_year, stats['avg_gpa'], stats['avg_attendance'],
              stats['at_risk_count'], stats['excellent_count'], stats['good_count'],
              stats['average_count']))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Snapshot created"})

    @app.route("/api/cohort/compare/<int:semester>", methods=["GET"])
    def compare_cohorts(semester):
        """Compare current semester to last 3 semesters"""
        conn = get_enhanced_connection()
        snapshots = conn.execute("""
            SELECT * FROM cohort_snapshots
            WHERE semester BETWEEN ? AND ?
            ORDER BY semester DESC
            LIMIT 4
        """, (semester - 3, semester)).fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "comparison": [dict(s) for s in snapshots]
        })

# ─── 10. SUBJECT WEAKNESS HEATMAP ────────────────────────────────────────────

def subject_heatmap_blueprint(app):
    """Subject performance matrix"""
    
    @app.route("/api/heatmap/subject-performance/<int:semester>", methods=["GET"])
    def get_subject_heatmap(semester):
        """Get heatmap data: students vs subjects, color by performance"""
        conn = get_enhanced_connection()
        data = conn.execute("""
            SELECT sp.student_id, s.name, sp.subject, sp.overall_score, 
                   CASE 
                       WHEN sp.overall_score >= 80 THEN 'excellent'
                       WHEN sp.overall_score >= 60 THEN 'good'
                       WHEN sp.overall_score >= 40 THEN 'average'
                       ELSE 'poor'
                   END as performance_level
            FROM subject_performance sp
            JOIN students s ON sp.student_id = s.student_id
            WHERE sp.semester=?
            ORDER BY s.name, sp.subject
        """, (semester,)).fetchall()
        conn.close()
        
        # Format for heatmap visualization
        students = {}
        subjects = set()
        
        for row in data:
            student_id = row['student_id']
            subject = row['subject']
            score = row['overall_score']
            subjects.add(subject)
            
            if student_id not in students:
                students[student_id] = {'name': row['name'], 'scores': {}}
            students[student_id]['scores'][subject] = score
        
        return jsonify({
            "success": True,
            "heatmap": {
                "students": students,
                "subjects": list(subjects),
                "semester": semester
            }
        })

# ─── 11. ADDITIONAL ENHANCED APIS ──────────────────────────────────────────

def additional_analytics_blueprint(app):
    """Add extra endpoints for alerts, forecasting, study plan and what-if."""

    @app.route("/api/alerts/student/<student_id>", methods=["GET"])
    def get_student_alerts(student_id):
        from ml_model_enhanced import generate_early_warning_alerts
        from db_enhanced import get_connection

        # Trigger generation based on latest semester
        conn = get_connection()
        row = conn.execute("SELECT MAX(semester) as sem FROM academic_records WHERE student_id=?", (student_id,)).fetchone()
        conn.close()
        if not row or row['sem'] is None:
            return jsonify({"success": True, "alerts": [], "message": "No academic records yet"}), 200

        alerts = generate_early_warning_alerts(student_id, row['sem'])
        return jsonify({"success": True, "alerts": alerts})

    @app.route("/api/predict/future/<student_id>", methods=["GET"])
    def get_future_gpa(student_id):
        from ml_model_enhanced import predict_future_gpa
        out = predict_future_gpa(student_id)
        return jsonify({"success": True, "future_prediction": out})

    @app.route("/api/study-plan/<student_id>", methods=["GET"])
    def get_study_plan(student_id):
        from ml_model_enhanced import generate_study_plan
        out = generate_study_plan(student_id)
        return jsonify({"success": True, "study_plan": out})

    @app.route("/api/peer/match/<student_id>", methods=["GET"])
    def get_peer_match(student_id):
        from ml_model_enhanced import match_peer
        out = match_peer(student_id)
        if out is None:
            return jsonify({"success": False, "message": "No mentor found"}), 404
        return jsonify({"success": True, "peer_match": out})

    @app.route("/api/attendance/predict/<student_id>", methods=["GET"])
    def get_attendance_predict(student_id):
        from ml_model_enhanced import predict_attendance
        out = predict_attendance(student_id)
        return jsonify({"success": True, "attendance_forecast": out})

    @app.route("/api/simulate", methods=["POST"])
    def simulate_input():
        from ml_model_enhanced import simulate_parameters
        data = request.json or {}
        if not data:
            return jsonify({"success": False, "message": "No input data"}), 400
        out = simulate_parameters(data)
        return jsonify({"success": True, "simulation": out})

    @app.route("/api/alerts/resume/<student_id>", methods=["GET"])
    def get_resume_summary(student_id):
        from ml_model_enhanced import build_resume_summary
        out = build_resume_summary(student_id)
        if not out:
            return jsonify({"success": False, "message": "Student not found"}), 404
        return jsonify({"success": True, "resume_summary": out})

    @app.route("/api/subject-weakness/<student_id>", methods=["GET"])
    def get_subject_weakness(student_id):
        from ml_model_enhanced import detect_subject_weaknesses
        out = detect_subject_weaknesses(student_id)
        return jsonify({"success": True, "subject_weaknesses": out})

# ─── REGISTER ALL BLUEPRINTS IN YOUR APP ────────────────────────────────────

def register_all_enhanced_features(app):
    """Call this function in your app.py to register all enhanced features"""
    shap_explainability_blueprint(app)
    dropout_prediction_blueprint(app)
    peer_benchmarking_blueprint(app)
    gamification_blueprint(app)
    chatbot_tutor_blueprint(app)
    intervention_tracker_blueprint(app)
    engagement_scoring_blueprint(app)
    pdf_report_blueprint(app)
    cohort_comparison_blueprint(app)
    subject_heatmap_blueprint(app)
    additional_analytics_blueprint(app)
    
    print("✓ All 10+ enhanced features registered!")

if __name__ == "__main__":
    print("""
    Usage: Import and call in your app.py:
    
    from app_enhanced import register_all_enhanced_features
    
    app = Flask(__name__)
    register_all_enhanced_features(app)
    """)
