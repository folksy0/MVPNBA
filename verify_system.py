"""
Quick System Verification for NBA MVP Decision Support System
"""

def verify_installation():
    print("🏀 NBA MVP System Verification")
    print("=" * 35)
    
    # Check file structure
    import os
    required_files = [
        'app.py',
        'requirements.txt', 
        'sample_nba_data.csv',
        'templates/base.html',
        'templates/index.html',
        'static/assets'
    ]
    
    print("📁 Checking file structure...")
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file}")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {missing_files}")
        return False
    
    # Check Python modules
    print("\n📦 Checking Python modules...")
    modules = ['flask', 'pandas', 'numpy', 'matplotlib', 'fpdf']
    missing_modules = []
    
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"✗ {module}")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n⚠️  Missing modules: {missing_modules}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("\n✅ System verification complete!")
    print("🚀 Ready to launch NBA MVP system")
    return True

if __name__ == '__main__':
    verify_installation()
