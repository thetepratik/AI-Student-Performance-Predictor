#!/usr/bin/env python3
"""
Quick Setup Script for Enhanced Student Predictor Features
Initializes database, trains models, and registers endpoints
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def install_dependencies():
    """Install all required packages"""
    print_header("📦 Installing Dependencies")
    
    requirements_file = "requirements_enhanced.txt"
    if not Path(requirements_file).exists():
        print("⚠️  requirements_enhanced.txt not found!")
        return False
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print("✅ All dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def init_databases():
    """Initialize original and enhanced databases"""
    print_header("🗄️  Initializing Databases")
    
    try:
        from db import init_db
        init_db()
        print("✅ Original database initialized")
        
        from db_enhanced import init_enhanced_db
        init_enhanced_db()
        print("✅ Enhanced database initialized")
        
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def train_models():
    """Train ML models (performance + dropout)"""
    print_header("🤖 Training ML Models")
    
    try:
        from ml_model_enhanced import train_model_with_shap
        result = train_model_with_shap()
        print(f"✅ Models trained successfully!")
        print(f"   Model Accuracy: {result['accuracy']}%")
        print(f"   Feature Importance: {result['feature_importance']}")
        return True
    except Exception as e:
        print(f"❌ Model training failed: {e}")
        return False

def check_api_key():
    """Check for Anthropic API key"""
    print_header("🔑 Checking API Configuration")
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        masked = api_key[:7] + "..." + api_key[-4:]
        print(f"✅ ANTHROPIC_API_KEY found: {masked}")
        return True
    else:
        print("⚠️  ANTHROPIC_API_KEY not set")
        print("   For AI Chatbot Tutor and PDF reports, set:")
        print("   export ANTHROPIC_API_KEY='sk-...'")
        print("\n   You can still use other features without it.")
        return False

def verify_imports():
    """Verify all critical imports"""
    print_header("✔️  Verifying Imports")
    
    packages = [
        ("Flask", "flask"),
        ("Pandas", "pandas"),
        ("Scikit-learn", "sklearn"),
        ("SHAP", "shap"),
        ("Anthropic", "anthropic"),
        ("ReportLab", "reportlab"),
    ]
    
    failures = []
    for display_name, import_name in packages:
        try:
            __import__(import_name)
            print(f"✅ {display_name}")
        except ImportError:
            print(f"❌ {display_name} - Not installed")
            failures.append(display_name)
    
    if failures:
        print(f"\n⚠️  Missing packages: {', '.join(failures)}")
        print("   Run: pip install -r requirements_enhanced.txt")
        return False
    
    return True

def create_env_template():
    """Create .env template file"""
    print_header("📝 Creating Configuration Template")
    
    env_template = """
# Environment Configuration for Enhanced Student Predictor

# Anthropic API - Required for AI Tutor and PDF Reports
ANTHROPIC_API_KEY=sk-your-key-here

# Database
DATABASE_PATH=./student_predictor.db

# Flask
FLASK_ENV=development
FLASK_DEBUG=True

# API Configuration
API_PORT=5000
API_CORS_ORIGINS=*
"""
    
    try:
        with open(".env.example", "w") as f:
            f.write(env_template.strip())
        print("✅ Created .env.example template")
        print("   Copy to .env and add your API keys")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env.example: {e}")
        return False

def print_next_steps():
    """Print helpful next steps"""
    print_header("🚀 Next Steps")
    
    instructions = """
1. UPDATE YOUR app.py:
   
   Add these imports:
   ┌─────────────────────────────────────────────────────────┐
   │ from app_enhanced import register_all_enhanced_features │
   │ from db_enhanced import get_connection                  │
   └─────────────────────────────────────────────────────────┘
   
   Register features:
   ┌─────────────────────────────────────────────────────────┐
   │ app = Flask(__name__)                                   │
   │ register_all_enhanced_features(app)                     │
   └─────────────────────────────────────────────────────────┘

2. SET YOUR API KEY (for AI Tutor):
   
   ┌─────────────────────────────────────────────────────────┐
   │ export ANTHROPIC_API_KEY="sk-your-key-here"             │
   └─────────────────────────────────────────────────────────┘

3. TEST THE ENDPOINTS:
   
   Start your Flask server:
   ┌─────────────────────────────────────────────────────────┐
   │ python app.py                                           │
   └─────────────────────────────────────────────────────────┘
   
   Test SHAP explainability:
   ┌─────────────────────────────────────────────────────────┐
   │ curl http://localhost:5000/api/explainability/shap/S001/1
   └─────────────────────────────────────────────────────────┘

4. REVIEW DOCUMENTATION:
   
   Open IMPLEMENTATION_GUIDE.md for:
   - Detailed feature descriptions
   - API endpoint documentation
   - Frontend integration examples
   - Troubleshooting tips

5. RECOMMENDED IMPLEMENTATION ORDER:
   
   Phase 1 (This week):
   ✓ SHAP Explainability
   ✓ AI Chatbot Tutor
   ✓ Faculty Intervention Tracker
   
   Phase 2 (Next week):
   ✓ Dropout Prediction
   ✓ Peer Benchmarking
   ✓ Engagement Scoring

DOCUMENTATION FILES:
   - IMPLEMENTATION_GUIDE.md ......... Full feature documentation
   - db_enhanced.py ................. Database schema for new tables
   - ml_model_enhanced.py ........... Enhanced ML with SHAP & dropout
   - app_enhanced.py ................ All API endpoints

QUICK REFERENCE:

   SHAP Explanation:
   GET /api/explainability/shap/<student_id>/<semester>
   
   Dropout Prediction:
   GET /api/dropout/predict/<student_id>/<semester>
   
   Peer Benchmarking:
   GET /api/benchmarking/student/<student_id>/<semester>
   
   AI Tutor Chat:
   POST /api/tutor/chat
   
   Interventions:
   POST /api/interventions
   GET /api/interventions/<student_id>
   
   And 15+ more endpoints (see IMPLEMENTATION_GUIDE.md)
"""
    print(instructions)

def main():
    """Main setup flow"""
    print("\n" + "="*60)
    print("  🎓 Enhanced Student Predictor - Quick Setup")
    print("="*60)
    
    # Step 1: Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed at dependency installation")
        sys.exit(1)
    
    # Step 2: Verify imports
    if not verify_imports():
        print("\n⚠️  Warning: Some packages are missing")
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            sys.exit(1)
    
    # Step 3: Initialize databases
    if not init_databases():
        print("\n❌ Setup failed at database initialization")
        sys.exit(1)
    
    # Step 4: Train models
    if not train_models():
        print("\n⚠️  Warning: Model training failed")
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            sys.exit(1)
    
    # Step 5: Check API configuration
    check_api_key()
    
    # Step 6: Create config template
    create_env_template()
    
    # Step 7: Print next steps
    print_next_steps()
    
    print("\n" + "="*60)
    print("  ✅ Setup Complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
