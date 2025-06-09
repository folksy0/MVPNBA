#!/usr/bin/env python3
"""
Test script for CSV upload functionality
Tests various CSV formats and potential parsing issues
"""

import pandas as pd
import os
import sys
from app import validate_csv_format, process_csv_data
import sqlite3

def create_test_csv_files():
    """Create various test CSV files to test parsing robustness"""
    
    # Test 1: Standard format (similar to sample)
    test1_data = {
        'Player': ['LeBron James', 'Stephen Curry', 'Kevin Durant'],
        'Team': ['LAL', 'GSW', 'PHX'],
        'G': [56, 64, 47],
        'MP': [35.5, 34.7, 36.9],
        'FG%': [0.525, 0.427, 0.556],
        'PTS': [25.7, 26.4, 26.8],
        'TRB': [7.3, 4.5, 6.7],
        'AST': [7.3, 5.1, 5.0],
        'STL': [1.3, 0.9, 0.8],
        'BLK': [0.6, 0.4, 1.1],
        'TOV': [3.5, 3.1, 3.3],
        'PF': [1.8, 1.9, 2.0]
    }
    pd.DataFrame(test1_data).to_csv('test_standard.csv', index=False)
    
    # Test 2: Alternative column names
    test2_data = {
        'Player Name': ['Giannis Antetokounmpo', 'Luka Doncic'],
        'Team Name': ['MIL', 'DAL'],
        'Games': [63, 66],
        'Minutes': [32.1, 36.2],
        'Field Goal %': [0.553, 0.321],
        'Points': [31.1, 32.4],
        'Rebounds': [11.8, 8.2],
        'Assists': [5.7, 8.0],
        'Steals': [1.2, 1.4],
        'Blocks': [0.8, 0.5],
        'Turnovers': [3.4, 4.0],
        'Personal Fouls': [3.1, 2.8]
    }
    pd.DataFrame(test2_data).to_csv('test_alternative.csv', index=False)
    
    # Test 3: CSV with problematic characters and encoding
    test3_data = {
        'Player': ['Nikola Jokić', 'Dončić Test'],  # Unicode characters
        'Team': ['DEN', 'TEST'],
        'G': [69, 50],
        'MP': [33.7, 30.0],
        'FG%': [0.632, 0.500],
        'PTS': [24.5, 20.0],
        'TRB': [11.8, 8.0],
        'AST': [9.8, 6.0],
        'STL': [1.3, 1.0],
        'BLK': [0.7, 0.5],
        'TOV': [3.0, 2.5],
        'PF': [2.5, 2.0]
    }
    pd.DataFrame(test3_data).to_csv('test_unicode.csv', index=False, encoding='utf-8')
    
    print("✅ Created test CSV files")

def test_csv_validation():
    """Test CSV validation function"""
    print("\n🔍 Testing CSV Validation...")
    
    test_files = ['test_standard.csv', 'test_alternative.csv', 'test_unicode.csv']
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n📄 Testing {test_file}:")
            is_valid, message = validate_csv_format(test_file)
            print(f"   Valid: {is_valid}")
            print(f"   Message: {message}")
        else:
            print(f"❌ Test file {test_file} not found")

def test_csv_processing():
    """Test CSV processing function"""
    print("\n⚙️ Testing CSV Processing...")
    
    # Initialize database
    from app import init_database
    init_database()
    
    # Create a test session
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    session_id = 'test_session_001'
    cursor.execute('''
        INSERT INTO upload_sessions (id, filename, status, upload_time)
        VALUES (?, ?, ?, datetime('now'))
    ''', (session_id, 'test_standard.csv', 'uploading'))
    conn.commit()
    
    # Test processing
    try:
        process_csv_data('test_standard.csv', session_id)
        print("✅ CSV processing completed successfully")
        
        # Check results
        cursor.execute('SELECT COUNT(*) FROM players')
        player_count = cursor.fetchone()[0]
        print(f"   Players imported: {player_count}")
        
        cursor.execute('SELECT COUNT(*) FROM statistics')
        stats_count = cursor.fetchone()[0]
        print(f"   Statistics records: {stats_count}")
        
    except Exception as e:
        print(f"❌ CSV processing failed: {e}")
    
    conn.close()

def cleanup_test_files():
    """Clean up test files"""
    test_files = ['test_standard.csv', 'test_alternative.csv', 'test_unicode.csv']
    for test_file in test_files:
        if os.path.exists(test_file):
            os.remove(test_file)
    print("\n🧹 Cleaned up test files")

def main():
    """Run all tests"""
    print("🚀 NBA MVP CSV Upload Test Suite")
    print("=" * 50)
    
    try:
        create_test_csv_files()
        test_csv_validation()
        test_csv_processing()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
    
    finally:
        cleanup_test_files()

if __name__ == "__main__":
    main()
