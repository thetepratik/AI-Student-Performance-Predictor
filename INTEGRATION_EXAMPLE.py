"""
INTEGRATION EXAMPLE: How to add enhanced features to your existing app.py

This shows the minimal changes needed to integrate all 10 features.
"""

# ============================================================================
# STEP 1: Add these imports at the top of your existing app.py
# ============================================================================

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

# ✨ NEW: Import enhanced features
from db import get_connection, init_db
from db_enhanced import get_connection as get_enhanced_connection, init_enhanced_db
from ml_model import predict_performance, train_model, get_feature_importance, get_class_analytics
from app_enhanced import register_all_enhanced_features  # ← NEW

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="/")
CORS(app, origins="*")

# ============================================================================
# STEP 2: Initialize both databases in your main block
# ============================================================================

if __name__ == "__main__":
    # Initialize original database
    init_db()
    
    # ✨ NEW: Initialize enhanced database
    init_enhanced_db()
    
    # ✨ NEW: Register all 10 enhanced features as API endpoints
    register_all_enhanced_features(app)
    
    # Start server
    app.run(debug=True, port=5000)

# ============================================================================
# That's it! You don't need to modify any existing code.
# All 10 features are now available as new API endpoints.
# ============================================================================

# ============================================================================
# OPTIONAL: Add these endpoints to your existing app.py for better 
# integration with your current student/academic records flow
# ============================================================================

@app.route("/api/records/<student_id>", methods=["POST"])
def add_record(student_id):
    """
    Your existing endpoint (already in app.py)
    We just enhance it to also store SHAP explanation and dropout prediction
    """
    body = request.json or {}

    # Your existing code...
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
    
    # ... your existing GPA calculation and database insert ...
    
    # ✨ NEW: Store SHAP explanation for this student
    from ml_model_enhanced import get_shap_explanation
    shap_exp = get_shap_explanation(pred_input)
    
    if shap_exp:
        conn = get_enhanced_connection()
        predicted_class = max(shap_exp.keys(), 
                             key=lambda k: shap_exp[k]["base_value"])
        explanation = shap_exp[predicted_class]
        
        for feature_contrib in explanation["feature_contributions"]:
            conn.execute("""
                INSERT INTO shap_explanations 
                (student_id, semester, feature_name, shap_value, feature_value)
                VALUES (?, ?, ?, ?, ?)
            """, (student_id, body.get("semester", 1), 
                  feature_contrib["feature"], 
                  feature_contrib["shap_value"],
                  feature_contrib["value"]))
        conn.commit()
        conn.close()
    
    # ✨ NEW: Store dropout prediction
    from ml_model_enhanced import predict_dropout
    dropout_pred = predict_dropout(pred_input)
    
    conn = get_enhanced_connection()
    conn.execute("""
        INSERT OR REPLACE INTO dropout_predictions 
        (student_id, semester, dropout_probability, dropout_risk_level)
        VALUES (?, ?, ?, ?)
    """, (student_id, body.get("semester", 1), 
          dropout_pred["dropout_probability"],
          dropout_pred["dropout_risk_level"]))
    conn.commit()
    conn.close()
    
    # Return enhanced prediction with all new data
    return make_response_ok({
        **prediction,
        "shap_explanation": shap_exp,
        "dropout_prediction": dropout_pred,
        "gpa": gpa,
        "performance": actual_perf
    })

# ============================================================================
# OPTIONAL: Create a combined dashboard endpoint
# ============================================================================

@app.route("/api/student/comprehensive/<student_id>/<semester>", methods=["GET"])
def get_comprehensive_student_view(student_id, semester):
    """
    Get all student data in one request:
    - Academic records
    - SHAP explanation
    - Dropout risk
    - Peer benchmarks
    - Study streaks
    - Intervention history
    - Engagement score
    """
    
    conn = get_enhanced_connection()
    
    # 1. Academic record
    record = conn.execute("""
        SELECT * FROM academic_records 
        WHERE student_id=? AND semester=?
    """, (student_id, int(semester))).fetchone()
    
    if not record:
        conn.close()
        return make_response_err("Student record not found", 404)
    
    # 2. SHAP explanation (latest)
    shap_data = conn.execute("""
        SELECT feature_name, shap_value FROM shap_explanations
        WHERE student_id=? AND semester=?
        ORDER BY ABS(shap_value) DESC LIMIT 5
    """, (student_id, int(semester))).fetchall()
    
    # 3. Dropout prediction (latest)
    dropout = conn.execute("""
        SELECT * FROM dropout_predictions 
        WHERE student_id=? AND semester=?
    """, (student_id, int(semester))).fetchone()
    
    # 4. Study streaks
    streaks = conn.execute("""
        SELECT * FROM study_streaks WHERE student_id=?
    """, (student_id,)).fetchall()
    
    # 5. Recent interventions
    interventions = conn.execute("""
        SELECT * FROM faculty_interventions
        WHERE student_id=? AND semester=?
        ORDER BY intervention_date DESC LIMIT 5
    """, (student_id, int(semester))).fetchall()
    
    # 6. Active goals
    goals = conn.execute("""
        SELECT * FROM student_goals 
        WHERE student_id=? AND status='active'
    """, (student_id,)).fetchall()
    
    conn.close()
    
    # Calculate engagement score
    from ml_model_enhanced import calculate_behavioral_engagement
    activities = conn.execute("""
        SELECT activity_type FROM activity_logs
        WHERE student_id=? AND timestamp > datetime('now', '-7 days')
    """, (student_id,)).fetchall()
    engagement_score = calculate_behavioral_engagement([{"type": a[0]} for a in activities])
    
    return make_response_ok({
        "student_id": student_id,
        "semester": semester,
        "academic_record": dict(record),
        "shap_explanation": [dict(s) for s in shap_data],
        "dropout_risk": dict(dropout) if dropout else None,
        "study_streaks": [dict(s) for s in streaks],
        "recent_interventions": [dict(i) for i in interventions],
        "active_goals": [dict(g) for g in goals],
        "engagement_score": engagement_score
    })

# ============================================================================
# HELPER: Make sure your existing helper functions are defined
# ============================================================================

def make_response_ok(data=None, message="Success"):
    return jsonify({"success": True, "message": message, "data": data})

def make_response_err(message="Error", code=400):
    return jsonify({"success": False, "message": message}), code

# ============================================================================
# THAT'S ALL YOU NEED!
#
# All 10 features are now integrated into your system:
#
# 1. ✅ SHAP Explainability
# 2. ✅ Dropout Prediction
# 3. ✅ Peer Benchmarking
# 4. ✅ Goal-Setting & Streaks
# 5. ✅ AI Chatbot Tutor
# 6. ✅ Faculty Intervention Tracker
# 7. ✅ Behavioral Engagement Scoring
# 8. ✅ PDF Report Generation
# 9. ✅ Cohort Comparison
# 10. ✅ Subject Weakness Heatmap
#
# Available endpoints (26 new API routes):
# ============================================================================

"""
SHAP & Explainability:
  GET  /api/explainability/shap/<student_id>/<semester>
  POST /api/explainability/waterfall

Dropout Prediction:
  GET  /api/dropout/predict/<student_id>/<semester>
  GET  /api/dropout/at-risk

Peer Benchmarking:
  GET  /api/benchmarking/student/<student_id>/<semester>

Goals & Streaks:
  GET  /api/goals/<student_id>
  POST /api/goals
  GET  /api/streaks/<student_id>
  POST /api/streaks/update

AI Tutor:
  POST /api/tutor/chat
  GET  /api/tutor/history/<student_id>

Interventions:
  POST /api/interventions
  GET  /api/interventions/<student_id>
  PUT  /api/interventions/<intervention_id>/outcome

Engagement:
  POST /api/engagement/log
  GET  /api/engagement/score/<student_id>

Reports:
  POST /api/reports/generate/<student_id>/<semester>

Cohorts:
  POST /api/cohort/snapshot
  GET  /api/cohort/compare/<semester>

Heatmap:
  GET  /api/heatmap/subject-performance/<semester>

Comprehensive View:
  GET  /api/student/comprehensive/<student_id>/<semester>

See IMPLEMENTATION_GUIDE.md for detailed documentation of each endpoint.
"""
