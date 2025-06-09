#!/usr/bin/env python3
"""
Simple CSV parsing test
"""

import pandas as pd
import sys
import os

def test_robust_csv_parsing():
    print("Testing robust CSV parsing...")
    
    # Create a test CSV with potential issues
    test_data = """Player,Team,G,MP,FG%,PTS,TRB,AST,STL,BLK,TOV,PF
LeBron James,LAL,56,35.5,0.525,25.7,7.3,7.3,1.3,0.6,3.5,1.8
Stephen Curry,GSW,64,34.7,0.427,26.4,4.5,5.1,0.9,0.4,3.1,1.9
"Kevin Durant",PHX,47,36.9,0.556,26.8,6.7,5.0,0.8,1.1,3.3,2.0"""
    
    with open('test_simple.csv', 'w', encoding='utf-8') as f:
        f.write(test_data)
    
    # Test different parsing methods
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-8-sig']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(
                'test_simple.csv', 
                encoding=encoding,
                sep=',',
                quoting=1,
                skipinitialspace=True,
                skip_blank_lines=True,
                on_bad_lines='skip',
                engine='python'
            )
            print(f"✅ Successfully parsed with {encoding}")
            print(f"   Shape: {df.shape}")
            print(f"   Columns: {list(df.columns)}")
            break
        except Exception as e:
            print(f"❌ Failed with {encoding}: {e}")
    
    # Clean up
    if os.path.exists('test_simple.csv'):
        os.remove('test_simple.csv')

if __name__ == "__main__":
    test_robust_csv_parsing()
