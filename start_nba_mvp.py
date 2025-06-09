#!/usr/bin/env python3
"""
NBA MVP Decision Support System Launcher
"""

import sys
import os

def main():
    print("🏀 NBA MVP Decision Support System")
    print("=" * 40)
    print("Initializing system...")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Import required modules
    try:
        print("Loading Flask...")
        from flask import Flask
        
        print("Loading data processing libraries...")
        import pandas as pd
        import numpy as np
        
        print("Loading visualization libraries...")
        import matplotlib.pyplot as plt
        
        print("Loading PDF generation...")
        from fpdf import FPDF
        
        print("✓ All modules loaded successfully!")
        
    except ImportError as e:
        print(f"✗ Error importing modules: {e}")
        return False
    
    # Import and start the main application
    try:
        print("\nStarting NBA MVP application...")
        import app
        
        print("Initializing database...")
        app.init_database()
        
        print("✓ Database initialized!")
        print("\n🌟 Starting Flask server...")
        print("📊 Access the application at: http://127.0.0.1:5000")
        print("📁 Sample data file available: sample_nba_data.csv")
        print("\nPress Ctrl+C to stop the server")
        print("-" * 40)
        
        # Start the Flask application
        app.app.run(debug=True, host='127.0.0.1', port=5000)
        
    except Exception as e:
        print(f"✗ Error starting application: {e}")
        return False
    
    return True

if __name__ == '__main__':
    main()
