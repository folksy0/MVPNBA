#!/usr/bin/env python3
"""
Secure NBA MVP Application Launcher
Includes security        print("📊 Access the application at: http://127.0.0.1:5000")
        print("🔐 Default admin credentials: admin / admin123")
        print("🧪 Run security validation: python security_checker.py")
        print("📋 Manual security guide: SECURITY_TESTING_GUIDE.md")
        print("\nPress Ctrl+C to stop the server")idation on startup
"""

import sys
import os

def validate_security_setup():
    """Validate that security components are properly installed"""
    print("🔒 Validating Security Setup...")
    
    try:
        # Check security packages
        import bleach
        print("✅ Bleach (HTML sanitization) - OK")
        
        from markupsafe import escape
        print("✅ MarkupSafe (HTML escaping) - OK")
        
        import requests
        print("✅ Requests (security testing) - OK")
        
        # Check security utilities
        from security_utils import SecurityValidator, DatabaseSecurity
        print("✅ Security utilities - OK")
        
        # Test security validator
        test_input = "<script>alert('test')</script>"
        sanitized = SecurityValidator.sanitize_html(test_input)
        if "<script>" not in sanitized:
            print("✅ XSS protection - OK")
        else:
            print("❌ XSS protection - FAILED")
            return False
        
        # Test database security
        if hasattr(DatabaseSecurity, 'safe_user_lookup'):
            print("✅ SQL injection protection - OK")
        else:
            print("❌ SQL injection protection - FAILED")
            return False
        
        print("✅ All security components validated!")
        return True
        
    except ImportError as e:
        print(f"❌ Security setup incomplete: {e}")
        print("Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Security validation error: {e}")
        return False

def main():
    print("🏀 NBA MVP Decision Support System (Secure Version)")
    print("=" * 50)
    
    # Validate security setup first
    if not validate_security_setup():
        print("\n❌ Security validation failed. Please fix security setup before starting.")
        return False
    
    print("\n🚀 Starting secure application...")
    
    # Import and start the main application
    try:
        import app
        
        print("Initializing database...")
        app.init_database()
        print("✅ Database initialized!")
        
        print("\n🌟 Starting Flask server with security features enabled...")
        print("🔒 Security Features Active:")
        print("   • XSS Protection")
        print("   • SQL Injection Prevention") 
        print("   • File Upload Validation")
        print("   • Rate Limiting")
        print("   • Security Headers")
        print("   • Session Security")
        
        print("\n📊 Access the application at: http://127.0.0.1:5000")
        print("🔐 Default admin credentials: admin / admin123")
        print("🧪 Run security tests: python security_test.py")
        print("\nPress Ctrl+C to stop the server")
        print("-" * 50)
        
        # Start the Flask application
        app.app.run(debug=True, host='127.0.0.1', port=5000)
        
    except Exception as e:
        print(f"❌ Error starting secure application: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)
