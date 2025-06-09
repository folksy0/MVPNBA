#!/usr/bin/env python3
"""
Direct test of the enhanced CSV validation function
"""

import sys
import os
sys.path.append('.')

from app import validate_csv_format
import pandas as pd

def create_problematic_csv():
    """Create a CSV that might cause tokenizing errors"""
    
    # This simulates the kind of CSV that might cause "Expected 1 fields in line 13, saw 3"
    problematic_content = '''Player,Team,G,MP,FG%,PTS,TRB,AST,STL,BLK,TOV,PF
LeBron James,LAL,56,35.5,0.525,25.7,7.3,7.3,1.3,0.6,3.5,1.8
Stephen Curry,GSW,64,34.7,0.427,26.4,4.5,5.1,0.9,0.4,3.1,1.9

Kevin Durant,PHX,47,36.9,0.556,26.8,6.7,5.0,0.8,1.1,3.3,2.0
Giannis Antetokounmpo,MIL,63,32.1,0.553,31.1,11.8,5.7,1.2,0.8,3.4,3.1
Nikola Jokić,DEN,69,33.7,0.632,24.5,11.8,9.8,1.3,0.7,3.0,2.5

"Luka, Doncic",DAL,66,36.2,0.321,32.4,8.2,8.0,1.4,0.5,4.0,2.8
'''
    
    with open('test_problematic.csv', 'w', encoding='utf-8') as f:
        f.write(problematic_content)
    
    print("Created test CSV with potential parsing issues")

def test_validation():
    """Test the validation function"""
    
    print("\n" + "="*50)
    print("Testing Enhanced CSV Validation")
    print("="*50)
    
    create_problematic_csv()
    
    # Test with our enhanced validation
    print("\n📋 Testing with enhanced validation function...")
    is_valid, message = validate_csv_format('test_problematic.csv')
    
    print(f"✅ Validation Result: {'PASSED' if is_valid else 'FAILED'}")
    print(f"📝 Message: {message}")
    
    # Also test direct pandas reading to compare
    print("\n📋 Testing direct pandas reading (old method)...")
    try:
        df = pd.read_csv('test_problematic.csv')
        print(f"✅ Direct pandas: SUCCESS - Shape: {df.shape}")
        print(f"📝 Columns: {list(df.columns)}")
    except Exception as e:
        print(f"❌ Direct pandas: FAILED - {e}")
    
    # Clean up
    if os.path.exists('test_problematic.csv'):
        os.remove('test_problematic.csv')
    
    print("\n" + "="*50)

if __name__ == "__main__":
    test_validation()
