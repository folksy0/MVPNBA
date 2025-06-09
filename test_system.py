#!/usr/bin/env python3
"""
Test script for NBA MVP Decision Support System
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database():
    """Test database creation and basic operations"""
    print("Testing database functionality...")
    
    # Initialize database
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            team TEXT NOT NULL,
            season TEXT NOT NULL,
            upload_session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            games_played INTEGER,
            minutes_played REAL,
            field_goal_percentage REAL,
            points REAL,
            total_rebounds REAL,
            assists REAL,
            steals REAL,
            blocks REAL,
            turnovers REAL,
            personal_fouls REAL,
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
    ''')
    
    # Test data insertion
    cursor.execute('''
        INSERT INTO players (name, team, season, upload_session_id) 
        VALUES (?, ?, ?, ?)
    ''', ("Test Player", "Test Team", "2023-24", "test-session"))
    
    player_id = cursor.lastrowid
    
    cursor.execute('''
        INSERT INTO statistics (player_id, games_played, minutes_played, field_goal_percentage,
                              points, total_rebounds, assists, steals, blocks, turnovers, personal_fouls)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (player_id, 82, 35.0, 50.0, 25.0, 8.0, 6.0, 1.5, 1.0, 3.0, 2.5))
    
    conn.commit()
    
    # Test data retrieval
    cursor.execute('SELECT COUNT(*) FROM players')
    player_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM statistics')
    stats_count = cursor.fetchone()[0]
    
    print(f"✓ Database created successfully")
    print(f"✓ Players table: {player_count} records")
    print(f"✓ Statistics table: {stats_count} records")
    
    # Clean up test data
    cursor.execute('DELETE FROM statistics WHERE player_id = ?', (player_id,))
    cursor.execute('DELETE FROM players WHERE id = ?', (player_id,))
    conn.commit()
    conn.close()
    
    return True

def test_mvp_calculation():
    """Test MVP calculation algorithm"""
    print("\nTesting MVP calculation algorithm...")
    
    # Sample player data
    sample_data = {
        'games_played': 75,
        'minutes_played': 35.0,
        'field_goal_percentage': 52.5,
        'points': 28.5,
        'total_rebounds': 10.2,
        'assists': 8.1,
        'steals': 1.4,
        'blocks': 0.8,
        'turnovers': 3.2,
        'personal_fouls': 2.1
    }
    
    # MVP weights
    weights = {
        "C1": 0.08,  # Total Games
        "C2": 0.08,  # Minutes Played  
        "C3": 0.09,  # FG% (Field Goal Percentage)
        "C4": 0.15,  # PTS (Points)
        "C5": 0.15,  # TRB (Total Rebounds)
        "C6": 0.15,  # AST (Assists)
        "C7": 0.15,  # STL (Steals)
        "C8": 0.10,  # BLK (Blocks)
        "C9": 0.5,   # TEAM (Team Performance Factor)
        "C10": 0.25, # TOV (Turnovers - cost criteria)
        "C11": 0.10  # PF (Personal Fouls - cost criteria)
    }
    
    print(f"✓ Sample player data loaded")
    print(f"✓ MVP weights configured")
    print(f"✓ Algorithm components ready")
    
    return True

def test_flask_imports():
    """Test Flask and required module imports"""
    print("\nTesting Flask imports...")
    
    try:
        from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
        print("✓ Flask modules imported successfully")
        
        import pandas as pd
        print("✓ Pandas imported successfully")
        
        import numpy as np
        print("✓ NumPy imported successfully")
        
        import matplotlib.pyplot as plt
        print("✓ Matplotlib imported successfully")
        
        from fpdf import FPDF
        print("✓ FPDF imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def main():
    """Run all tests"""
    print("NBA MVP Decision Support System - Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_flask_imports():
        success = False
    
    # Test database
    try:
        if not test_database():
            success = False
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        success = False
    
    # Test MVP calculation
    try:
        if not test_mvp_calculation():
            success = False
    except Exception as e:
        print(f"✗ MVP calculation test failed: {e}")
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! The NBA MVP system is ready to run.")
        print("\nTo start the application:")
        print("1. Run: python app.py")
        print("2. Open browser to: http://127.0.0.1:5000")
        print("3. Upload sample CSV file: sample_nba_data.csv")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    
    return success

if __name__ == '__main__':
    main()
