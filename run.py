#!/usr/bin/env python3
"""
EduPredict AI - Student Performance Predictor
Quick startup script
"""
import os
import sys

# Add project root to path
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from db import init_db
from ml_model import train_model

if __name__ == "__main__":
    print("=" * 50)
    print("🎓 EduPredict AI - Startup")
    print("=" * 50)

    print("\n[1/3] Initializing database...")
    init_db()

    model_path = os.path.join(BASE, "backend", "model.pkl")
    if not os.path.exists(model_path):
        print("\n[2/3] Training ML model (first time)...")
        result = train_model()
        print(f"  ✅ Model trained! Accuracy: {result['accuracy']}%")
    else:
        print("\n[2/3] ML model already trained ✅")

    print("\n[3/3] Starting Flask server...")
    print("\n  🌐 Open browser: http://localhost:5000")
    print("  👤 Faculty login: faculty / faculty123")
    print("  📝 Or register a new student/faculty account")
    print("\n  Press CTRL+C to stop\n")

    from app import app
    app.run(debug=False, port=5000, host="0.0.0.0")
