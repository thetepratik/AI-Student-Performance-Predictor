# 🎓 EduPredict AI — Student Performance Predictor

A complete AI-powered system to predict and analyze student academic performance using machine learning.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python run.py
```

### 3. Open in Browser
```
http://localhost:5000
```

---

## 👤 Default Login

| Role    | Username | Password     |
|---------|----------|-------------|
| Faculty | faculty  | faculty123  |
| Student | Register via the app |

> Faculty can see all students, analytics, at-risk alerts, and import data.
> Students can only see their own performance dashboard and AI recommendations.

---

##  Project Structure

```
student-predictor/
├── run.py                    # Startup script
├── app.py                    # Flask backend API
├── requirements.txt
│
├── 
│   └── ml_model.py           # ML training + prediction
│
├──
│   ├── db.py                 # SQLite schema + init
│   └── student_predictor.db  # Auto-created
│
├── 
│   ├── generate_dataset.py   # Synthetic data generator
│   └── student_dataset.csv   # 500-record training dataset
│
└── templates
    └── index.html            # Full single-page app
```

---

##  ML Model

- **Algorithm**: Gradient Boosting Classifier (sklearn)
- **Features**: Attendance, Study Hours, Class Participation, Homework Completion, Quiz Score, Assignment Score, Midterm Score, Internal Score
- **Target**: Performance category (Excellent / Good / Average / At Risk)
- **Accuracy**: ~81% on test set
- **Training Data**: 500 synthetic student records

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/register` | Register |
| GET | `/api/students` | List all students (faculty) |
| POST | `/api/students` | Add student |
| PUT | `/api/students/:id` | Update student |
| DELETE | `/api/students/:id` | Delete student |
| POST | `/api/records/:id` | Add/update academic record + auto-predict |
| POST | `/api/predict` | Run prediction without saving |
| GET | `/api/analytics/overview` | Dashboard stats |
| GET | `/api/analytics/class` | Class analytics |
| GET | `/api/analytics/feature-importance` | ML feature weights |
| GET | `/api/analytics/at-risk` | At-risk student list |
| POST | `/api/import/csv` | Bulk CSV import |
| POST | `/api/model/retrain` | Retrain ML model |

---

##  Features

### Faculty
-  Student CRUD (Add/Edit/Delete)
-  Academic records per semester
-  AI performance prediction
-  At-risk early warning system
-  Feature importance analysis
-  Class analytics dashboard
-  CSV bulk import
-  Model retraining

### Students
-  Personal performance dashboard
-  AI-predicted grade + confidence
-  Risk level assessment
-  Personalized recommendations
-  Score trend charts
-  GPA tracker

---

## 📦 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python + Flask |
| ML Model | scikit-learn (Gradient Boosting) |
| Database | SQLite |
| Frontend | Vanilla JS + Chart.js |
| Data | Pandas + NumPy |

---

## 📥 CSV Import Format

```csv
StudentID,Name,Age,Gender,Course,Semester,Attendance,StudyHours,
ClassParticipation,HomeworkCompletion,QuizScore,AssignmentScore,
MidtermScore,FinalScore,InternalScore
```

Download the template from the Import page in the app.