"""
Enhanced ML module with:
1. SHAP explainability for per-student feature attribution
2. Dropout probability prediction (separate model)
3. Behavioral engagement scoring
4. Feature importance tracking
"""

import pandas as pd
import numpy as np
import pickle
import os
import json
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# Try to import SHAP; if not available, it will be installed
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.pkl")
DROPOUT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "dropout_model.pkl")
DROPOUT_SCALER_PATH = os.path.join(os.path.dirname(__file__), "dropout_scaler.pkl")
EXPLAINER_PATH = os.path.join(os.path.dirname(__file__), "shap_explainer.pkl")
DATA_PATH = os.path.join(os.path.dirname(__file__), "student_dataset.csv")

FEATURES = ["Attendance","StudyHours","ClassParticipation","HomeworkCompletion",
            "QuizScore","AssignmentScore","MidtermScore","InternalScore"]

LABEL_MAP = {"At Risk": 0, "Average": 1, "Good": 2, "Excellent": 3}
LABEL_REVERSE = {v: k for k, v in LABEL_MAP.items()}

def train_dropout_model(df):
    """Train separate dropout probability model"""
    # Create binary dropout labels (simulate with low GPA students)
    df['dropout'] = (df['GPA'] < 2.0).astype(int) if 'GPA' in df.columns else 0
    
    X = df[FEATURES].fillna(df[FEATURES].mean())
    y = df['dropout']
    
    if y.sum() == 0:
        print("No dropout samples in data, skipping dropout model training")
        return None, None
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
    
    with open(DROPOUT_MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(DROPOUT_SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
    
    print(f"Dropout model trained. Accuracy: {accuracy:.2%}")
    return model, scaler

def train_model_with_shap():
    """Train performance model and create SHAP explainer"""
    df = pd.read_csv(DATA_PATH)
    X = df[FEATURES].fillna(df[FEATURES].mean())
    y = df["Performance"].map(LABEL_MAP)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = GradientBoostingClassifier(n_estimators=200, learning_rate=0.1, max_depth=4, random_state=42)
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=list(LABEL_MAP.keys()))

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    # Train dropout model
    train_dropout_model(df)

    # Create SHAP explainer if available
    if SHAP_AVAILABLE:
        try:
            explainer = shap.TreeExplainer(model)
            with open(EXPLAINER_PATH, "wb") as f:
                pickle.dump(explainer, f)
            print("SHAP explainer created and saved")
        except Exception as e:
            print(f"Warning: Could not create SHAP explainer: {e}")

    importances = dict(zip(FEATURES, model.feature_importances_.tolist()))

    return {"accuracy": round(acc * 100, 2), "report": report, "feature_importance": importances}

def load_model():
    """Load main model and scaler"""
    if not os.path.exists(MODEL_PATH):
        train_model_with_shap()
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    return model, scaler

def load_dropout_model():
    """Load dropout model if available"""
    try:
        with open(DROPOUT_MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(DROPOUT_SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)
        return model, scaler
    except FileNotFoundError:
        return None, None

def load_shap_explainer():
    """Load SHAP explainer if available"""
    try:
        with open(EXPLAINER_PATH, "rb") as f:
            explainer = pickle.load(f)
        return explainer
    except FileNotFoundError:
        return None

def get_shap_explanation(student_data: dict):
    """
    Get SHAP-based explanation for a student's prediction.
    Returns attribution of each feature to the final prediction.
    """
    if not SHAP_AVAILABLE:
        return None
    
    model, scaler = load_model()
    explainer = load_shap_explainer()
    
    if explainer is None:
        return None
    
    features = np.array([student_data.get(f, 0) for f in FEATURES]).reshape(1, -1)
    X_scaled = scaler.transform(features)
    
    # Get SHAP values for this prediction
    shap_values = explainer.shap_values(X_scaled)
    base_value = explainer.expected_value
    
    # Create explanation for each class
    explanations = {}
    for class_idx, class_label in LABEL_REVERSE.items():
        class_shap = shap_values[class_idx][0] if isinstance(shap_values, list) else shap_values[0]
        
        feature_contributions = []
        for i, feature_name in enumerate(FEATURES):
            feature_contributions.append({
                "feature": feature_name,
                "value": float(student_data.get(feature_name, 0)),
                "shap_value": float(class_shap[i]),
                "contribution": "positive" if class_shap[i] > 0 else "negative"
            })
        
        # Sort by absolute SHAP value
        feature_contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        
        explanations[class_label] = {
            "base_value": float(base_value[class_idx] if isinstance(base_value, np.ndarray) else base_value),
            "feature_contributions": feature_contributions,
            "top_3_factors": feature_contributions[:3]
        }
    
    return explanations

def predict_dropout(student_data: dict):
    """
    Predict probability of student dropping the course.
    Returns dropout risk assessment separate from performance.
    """
    model, scaler = load_dropout_model()
    
    if model is None:
        return {
            "dropout_probability": 0.0,
            "dropout_risk": "Unknown",
            "confidence": 0.0
        }
    
    features = np.array([student_data.get(f, 0) for f in FEATURES]).reshape(1, -1)
    X_scaled = scaler.transform(features)
    
    dropout_prob = float(model.predict_proba(X_scaled)[0][1])
    
    # Risk level based on probability
    if dropout_prob > 0.7:
        risk_level = "High"
    elif dropout_prob > 0.4:
        risk_level = "Medium"
    else:
        risk_level = "Low"
    
    # Contributing factors (simplified)
    contributing_factors = []
    if student_data.get("Attendance", 75) < 60:
        contributing_factors.append("Very low attendance")
    if student_data.get("StudyHours", 3) < 1:
        contributing_factors.append("Minimal study effort")
    if student_data.get("MidtermScore", 50) < 40:
        contributing_factors.append("Midterm exam failure")
    
    return {
        "dropout_probability": round(dropout_prob, 3),
        "dropout_risk_level": risk_level,
        "contributing_factors": contributing_factors,
        "confidence": round(max(dropout_prob, 1 - dropout_prob) * 100, 1)
    }

# --- New features for enhanced analytics ---

def generate_early_warning_alerts(student_id: str, semester: int):
    """Generate simple alert rules based on attendance and GPA drop."""
    from db_enhanced import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT semester, attendance, gpa
        FROM academic_records
        WHERE student_id = ?
        ORDER BY semester ASC
    """, (student_id,)).fetchall()
    conn.close()

    if not rows:
        return []

    alerts = []
    prev_attendance = None
    prev_gpa = None
    for row in rows:
        sem = row['semester']
        att = row['attendance'] or 0
        gpa = row['gpa'] or 0

        if prev_attendance is not None and prev_attendance > 0:
            down = prev_attendance - att
            if down >= 10:
                alerts.append({
                    'student_id': student_id,
                    'semester': sem,
                    'alert': f'Attendance dropped by {down:.1f}% compared to previous semester',
                    'severity': 'High' if down >= 20 else 'Medium',
                    'source': 'attendance-drop'
                })
        if prev_gpa is not None:
            decline = prev_gpa - gpa
            if decline >= 0.5:
                alerts.append({
                    'student_id': student_id,
                    'semester': sem,
                    'alert': f'GPA declined by {decline:.2f}',
                    'severity': 'High' if decline >= 1.0 else 'Medium',
                    'source': 'gpa-decline'
                })

        prev_attendance = att
        prev_gpa = gpa

    # Save to alerts table
    if alerts:
        conn = get_connection()
        for obj in alerts:
            conn.execute("""
                INSERT INTO alerts (student_id, semester, alert, severity, source)
                VALUES (?, ?, ?, ?, ?)
            """, (obj['student_id'], obj['semester'], obj['alert'], obj['severity'], obj['source']))
        conn.commit()
        conn.close()

    return alerts


def predict_future_gpa(student_id: str):
    """Simple linear regression trend forecast for next semester GPA."""
    from db_enhanced import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT semester, gpa
        FROM academic_records
        WHERE student_id=? AND gpa IS NOT NULL
        ORDER BY semester ASC
    """, (student_id,)).fetchall()
    conn.close()

    if len(rows) < 2:
        return {'next_semester_gpa': rows[-1]['gpa'] if rows else None, 'trend': 'stable'}

    x = np.array([r['semester'] for r in rows]).reshape(-1, 1)
    y = np.array([r['gpa'] for r in rows])

    from sklearn.linear_model import LinearRegression
    model = LinearRegression()
    model.fit(x, y)
    next_sem = np.array([[rows[-1]['semester'] + 1]])
    predicted = float(model.predict(next_sem)[0])
    if predicted > 10: predicted = 10.0
    if predicted < 0: predicted = 0.0

    trend = 'stable'
    if predicted > y[-1] + 0.2: trend = 'improving'
    elif predicted < y[-1] - 0.2: trend = 'declining'

    return {'next_semester_gpa': round(predicted, 2), 'trend': trend}


def generate_study_plan(student_id: str):
    """Generate simple plan from latest scores and weaknesses."""
    from db_enhanced import get_connection
    conn = get_connection()
    latest = conn.execute("""
        SELECT * FROM academic_records WHERE student_id=? ORDER BY semester DESC LIMIT 1
    """, (student_id,)).fetchone()
    weak_subs = conn.execute("""
        SELECT subject, overall_score FROM subject_performance
        WHERE student_id=? AND overall_score IS NOT NULL
        ORDER BY overall_score ASC LIMIT 3
    """, (student_id,)).fetchall()
    conn.close()

    recommendations = []
    if latest:
        if latest['attendance'] < 85:
            recommendations.append('Increase attendance to at least 85% to stay engaged.')
        if latest['study_hours'] < 4:
            recommendations.append('Study at least 4 hours daily with focused breaks.')
        if latest['homework_completion'] < 80:
            recommendations.append('Complete 90% of assignments on time for consolidation.')
    if weak_subs:
        for sub in weak_subs:
            recommendations.append(f'Focus 2 hrs/day on {sub["subject"]} observed weak score ({sub["overall_score"]}%).')

    if not recommendations:
        recommendations.append('Maintain discipline and keep current strong practice.')

    return {
        'student_id': student_id,
        'recommendations': recommendations,
        'weak_subjects': [r['subject'] for r in weak_subs]
    }


def match_peer(student_id: str):
    """Simple mentorship pairing by same course highest GPA."""
    from db_enhanced import get_connection
    conn = get_connection()
    target = conn.execute("""
        SELECT course FROM students WHERE student_id=?
    """, (student_id,)).fetchone()
    if not target:
        conn.close()
        return None
    course = target['course']
    mentor = conn.execute("""
        SELECT s.student_id, s.name, ar.gpa FROM students s
        JOIN academic_records ar ON s.student_id=ar.student_id
        WHERE s.course=? AND s.student_id != ?
        ORDER BY ar.gpa DESC LIMIT 1
    """, (course, student_id)).fetchone()
    conn.close()
    if not mentor:
        return None
    return {'mentor': mentor['student_id'], 'name': mentor['name'], 'gpa': mentor['gpa'], 'reason': 'High GPA + same course'}


def predict_attendance(student_id: str):
    """Predict attendance trend from recent semesters."""
    from db_enhanced import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT semester, attendance FROM academic_records
        WHERE student_id=? ORDER BY semester ASC
    """, (student_id,)).fetchall()
    conn.close()

    if not rows:
        return {'predicted_attendance': None, 'risk': 'Unknown', 'trend': 'stable'}

    arr = np.array([r['attendance'] for r in rows])
    if len(arr) < 2:
        pred = float(arr[-1])
        risk = 'High' if pred < 70 else 'Medium' if pred < 85 else 'Low'
        return {'predicted_attendance': pred, 'risk': risk, 'trend': 'stable'}

    x = np.arange(len(arr)).reshape(-1, 1)
    y = np.array(arr)
    from sklearn.linear_model import LinearRegression
    model = LinearRegression().fit(x, y)
    next_val = float(model.predict([[len(arr)]])[0])
    next_val = max(0.0, min(100.0, next_val))
    risk = 'High' if next_val < 70 else 'Medium' if next_val < 85 else 'Low'
    trend = 'declining' if next_val < y[-1] else 'improving' if next_val > y[-1] else 'stable'
    return {'predicted_attendance': round(next_val, 1), 'risk': risk, 'trend': trend}


def simulate_parameters(changes: dict):
    """Simulate new prediction with changed parameters."""
    base = {f: float(changes.get(f, 0)) for f in FEATURES}
    result = predict_performance(base)
    return {'simulation_input': base, 'simulation_output': result}


def build_resume_summary(student_id: str):
    """Generate quick performance summary for shareable export."""
    from db_enhanced import get_connection
    conn = get_connection()
    student = conn.execute("SELECT * FROM students WHERE student_id=?", (student_id,)).fetchone()
    record = conn.execute("SELECT * FROM academic_records WHERE student_id=? ORDER BY semester DESC LIMIT 1", (student_id,)).fetchone()
    conn.close()
    if not student or not record:
        return None
    return {
        'student_id': student_id,
        'name': student['name'],
        'course': student['course'],
        'semester': record['semester'],
        'gpa': record['gpa'],
        'performance': record['performance'],
        'recommendations': generate_study_plan(student_id)['recommendations']
    }


def detect_subject_weaknesses(student_id: str):
    from db_enhanced import get_connection
    conn = get_connection()
    rows = conn.execute("SELECT subject, overall_score FROM subject_performance WHERE student_id=? ORDER BY overall_score ASC", (student_id,)).fetchall()
    conn.close()
    return [{'subject': r['subject'], 'score': r['overall_score'], 'weak': r['overall_score'] < 60} for r in rows]


def calculate_behavioral_engagement(activity_log: list) -> float:
    """
    Calculate engagement score from behavioral signals.
    Based on Stanford research: login frequency, assignment timing, message activity.
    
    Score: 0-100
    """
    if not activity_log:
        return 0.0
    
    score = 0.0
    max_score = 100.0
    
    # Login frequency (max 30 points)
    login_count = len([a for a in activity_log if a['type'] == 'login'])
    score += min(30, login_count * 3)
    
    # Assignment submission timing (max 30 points)
    early_submissions = len([a for a in activity_log if a['type'] == 'assignment_submit' and a.get('hours_early', 0) > 0])
    score += min(30, early_submissions * 5)
    
    # Message/discussion activity (max 25 points)
    messages = len([a for a in activity_log if a['type'] == 'message'])
    score += min(25, messages * 2)
    
    # Quiz attempts (max 15 points)
    quizzes = len([a for a in activity_log if a['type'] == 'quiz_attempt'])
    score += min(15, quizzes * 3)
    
    return round(min(score, max_score), 1)

def predict_performance(student_data: dict):
    """Main prediction with SHAP explanation and dropout risk"""
    model, scaler = load_model()
    features = [student_data.get(f, 0) for f in FEATURES]
    X = np.array(features).reshape(1, -1)
    X_scaled = scaler.transform(X)
    pred_class = model.predict(X_scaled)[0]
    pred_proba = model.predict_proba(X_scaled)[0]
    label = LABEL_REVERSE[pred_class]
    proba_dict = {LABEL_REVERSE[i]: round(float(p) * 100, 1) for i, p in enumerate(pred_proba)}

    # Risk assessment
    risk_level = "Low"
    risk_reasons = []
    if student_data.get("Attendance", 100) < 60:
        risk_level = "High"
        risk_reasons.append("Very low attendance")
    elif student_data.get("Attendance", 100) < 75:
        risk_level = "Medium"
        risk_reasons.append("Below required attendance")
    if student_data.get("StudyHours", 5) < 1.5:
        risk_level = "High" if risk_level == "Medium" else risk_level
        risk_reasons.append("Insufficient study hours")
    if student_data.get("AssignmentScore", 100) < 50:
        risk_reasons.append("Poor assignment performance")
    if student_data.get("MidtermScore", 100) < 40:
        risk_level = "High"
        risk_reasons.append("Failed midterm exam")
    if label == "At Risk":
        risk_level = "High"

    # Recommendations
    recommendations = generate_recommendations(student_data, label)
    
    # SHAP explanation
    shap_explanation = get_shap_explanation(student_data)
    
    # Dropout prediction
    dropout_pred = predict_dropout(student_data)

    return {
        "predicted_performance": label,
        "probabilities": proba_dict,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "recommendations": recommendations,
        "confidence": round(float(max(pred_proba)) * 100, 1),
        "shap_explanation": shap_explanation,
        "dropout_prediction": dropout_pred
    }

def generate_recommendations(data: dict, predicted: str) -> list:
    """Generate actionable recommendations"""
    recs = []
    attendance = data.get("Attendance", 75)
    study_hours = data.get("StudyHours", 3)
    hw = data.get("HomeworkCompletion", 70)
    participation = data.get("ClassParticipation", 5)
    assignment = data.get("AssignmentScore", 60)
    midterm = data.get("MidtermScore", 60)

    if attendance < 75:
        recs.append({"category": "Attendance", "text": f"Increase attendance to at least 75%. Current: {attendance}%. Missing classes directly impacts exam performance.", "priority": "High"})
    if study_hours < 3:
        recs.append({"category": "Study Habits", "text": f"Increase daily study hours to 3–4 hours. Currently studying {study_hours} hrs/day.", "priority": "High" if study_hours < 1.5 else "Medium"})
    if hw < 70:
        recs.append({"category": "Assignments", "text": f"Improve homework completion rate to above 80%. Current completion: {hw}%.", "priority": "Medium"})
    if participation < 5:
        recs.append({"category": "Participation", "text": "Actively participate in class discussions. Ask questions and engage with the material.", "priority": "Low"})
    if midterm < 50:
        recs.append({"category": "Exam Prep", "text": "Seek extra tutoring for exam preparation. Consider forming study groups with peers.", "priority": "High"})
    if assignment < 60:
        recs.append({"category": "Assignment Quality", "text": "Focus on assignment quality. Visit office hours for guidance on weak subjects.", "priority": "Medium"})
    if not recs:
        recs.append({"category": "Keep It Up", "text": "Excellent progress! Maintain current habits and continue challenging yourself.", "priority": "Low"})
    return recs

def get_feature_importance():
    """Get global feature importance"""
    model, _ = load_model()
    return dict(zip(FEATURES, [round(float(v)*100, 2) for v in model.feature_importances_]))

def get_class_analytics(records: list) -> dict:
    """Get class-level analytics"""
    if not records:
        return {}
    df = pd.DataFrame(records)
    numeric_cols = ["attendance","study_hours","quiz_score","assignment_score","midterm_score","final_score","gpa"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    stats = {}
    for col in numeric_cols:
        if col in df.columns:
            stats[col] = {
                "mean": round(df[col].mean(), 2),
                "min": round(df[col].min(), 2),
                "max": round(df[col].max(), 2),
                "std": round(df[col].std(), 2)
            }
    if "performance" in df.columns:
        stats["performance_dist"] = df["performance"].value_counts().to_dict()
    if "risk_level" in df.columns:
        stats["risk_dist"] = df["risk_level"].value_counts().to_dict()
    return stats

if __name__ == "__main__":
    result = train_model_with_shap()
    print(f"Model accuracy: {result['accuracy']}%")
    print(f"Feature importance: {result['feature_importance']}")
