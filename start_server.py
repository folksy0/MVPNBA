#!/usr/bin/env python3
"""
NBA MVP Application Startup Script
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, init_database
    
    print("=" * 60)
    print("NBA MVP Decision Support System")
    print("=" * 60)
    
    print("Initializing database...")
    init_database()
    print("✓ Database initialized successfully")
    
    print("\nStarting Flask application...")
    print("✓ Server will be available at: http://localhost:5000")
    print("✓ Default admin credentials: admin / admin123")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 60)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
    
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all required dependencies are installed:")
    print("pip install flask werkzeug pandas numpy matplotlib seaborn fpdf2")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {e}")
    sys.exit(1)
