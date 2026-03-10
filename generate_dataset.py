import pandas as pd
import numpy as np
import random

np.random.seed(42)
random.seed(42)

n = 500
names = [
    "Aarav Shah","Priya Patel","Rohan Mehta","Ananya Singh","Vikram Joshi",
    "Sneha Reddy","Arjun Kumar","Pooja Nair","Karan Sharma","Divya Iyer",
    "Amit Verma","Riya Gupta","Suresh Pillai","Kavya Rao","Nikhil Tiwari",
    "Aisha Khan","Rahul Dubey","Simran Kaur","Manish Yadav","Deepa Menon",
    "Siddharth Roy","Tanvi Desai","Abhishek Mishra","Shreya Jain","Vivek Nambiar",
    "Meera Krishnan","Rajesh Bose","Swati Agarwal","Harish Pandey","Nisha Malhotra",
    "Aryan Kapoor","Preethi Subramaniam","Gaurav Saxena","Latha Venkatesh","Sumit Chauhan",
    "Rekha Shetty","Mohit Bansal","Anjali Bhatt","Piyush Chopra","Sunita Tripathi",
    "John Smith","Emily Johnson","Michael Brown","Sarah Davis","James Wilson",
    "Emma Martinez","David Anderson","Olivia Taylor","Daniel Thomas","Sophia Jackson"
]

courses = ["Computer Science","Data Science","Electronics","Mathematics","Physics","Business Administration","Biotechnology","Civil Engineering"]
genders = ["Male","Female","Other"]

data = []
for i in range(n):
    student_id = f"STU{1000 + i}"
    name = random.choice(names)
    age = random.randint(17, 25)
    gender = random.choices(genders, weights=[48, 48, 4])[0]
    course = random.choice(courses)
    semester = random.randint(1, 8)

    # Correlated features
    base_ability = np.random.normal(65, 15)
    study_hours = max(0.5, min(10, np.random.normal(3, 1.5) + (base_ability - 65) * 0.05))
    attendance = max(30, min(100, np.random.normal(75, 15) + (base_ability - 65) * 0.2))
    participation = max(0, min(10, np.random.normal(5, 2) + (base_ability - 65) * 0.05))
    homework_completion = max(0, min(100, np.random.normal(70, 20) + (base_ability - 65) * 0.3))

    # Scores influenced by ability + study hours + attendance
    score_boost = (study_hours - 3) * 2 + (attendance - 75) * 0.2 + (participation - 5) * 1
    quiz_score = max(0, min(100, np.random.normal(base_ability + score_boost * 0.3, 10)))
    assignment_score = max(0, min(100, np.random.normal(base_ability + score_boost * 0.4, 8) + homework_completion * 0.1))
    midterm_score = max(0, min(100, np.random.normal(base_ability + score_boost * 0.5, 12)))
    final_score = max(0, min(100, np.random.normal(base_ability + score_boost * 0.6, 10)))
    internal_score = max(0, min(100, (quiz_score + assignment_score) / 2 + np.random.normal(0, 5)))

    # GPA calculation
    weighted = (quiz_score * 0.1 + assignment_score * 0.2 + midterm_score * 0.3 + final_score * 0.4)
    gpa = round(min(10, max(0, weighted / 10)), 2)

    # Performance category
    if gpa >= 8.0:
        performance = "Excellent"
    elif gpa >= 6.0:
        performance = "Good"
    elif gpa >= 4.0:
        performance = "Average"
    else:
        performance = "At Risk"

    data.append({
        "StudentID": student_id,
        "Name": name,
        "Age": int(age),
        "Gender": gender,
        "Course": course,
        "Semester": semester,
        "Attendance": round(attendance, 1),
        "StudyHours": round(study_hours, 1),
        "ClassParticipation": round(participation, 1),
        "HomeworkCompletion": round(homework_completion, 1),
        "QuizScore": round(quiz_score, 1),
        "AssignmentScore": round(assignment_score, 1),
        "MidtermScore": round(midterm_score, 1),
        "FinalScore": round(final_score, 1),
        "InternalScore": round(internal_score, 1),
        "GPA": gpa,
        "Performance": performance
    })

df = pd.DataFrame(data)
df.to_csv("/home/claude/student-predictor/data/student_dataset.csv", index=False)
print(f"Dataset created: {len(df)} records")
print(df["Performance"].value_counts())
print(df.head())
