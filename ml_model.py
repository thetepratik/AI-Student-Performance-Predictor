import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.pkl")
DATA_PATH = os.path.join(os.path.dirname(__file__), "student_dataset.csv")

FEATURES = ["Attendance","StudyHours","ClassParticipation","HomeworkCompletion",
            "QuizScore","AssignmentScore","MidtermScore","InternalScore"]

LABEL_MAP = {"At Risk": 0, "Average": 1, "Good": 2, "Excellent": 3}
LABEL_REVERSE = {v: k for k, v in LABEL_MAP.items()}

def train_model():
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

    # Feature importance
    importances = dict(zip(FEATURES, model.feature_importances_.tolist()))

    return {"accuracy": round(acc * 100, 2), "report": report, "feature_importance": importances}

def load_model():
    if not os.path.exists(MODEL_PATH):
        train_model()
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    return model, scaler

def predict_performance(student_data: dict):
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

    return {
        "predicted_performance": label,
        "probabilities": proba_dict,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "recommendations": recommendations,
        "confidence": round(float(max(pred_proba)) * 100, 1)
    }

def generate_recommendations(data: dict, predicted: str) -> list:
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
    model, _ = load_model()
    return dict(zip(FEATURES, [round(float(v)*100, 2) for v in model.feature_importances_]))

def get_class_analytics(records: list) -> dict:
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
    result = train_model()
    print(f"Model accuracy: {result['accuracy']}%")
    print(f"Feature importance: {result['feature_importance']}")
