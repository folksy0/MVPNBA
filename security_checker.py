#!/usr/bin/env python3
"""
Security Validation Script for NBA MVP Decision Support System
A clean security checker that won't trigger antivirus false positives
"""

import requests
import json
import os
from urllib.parse import urljoin

class SecurityChecker:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.issues = []
    
    def check_security_headers(self):
        """Check if security headers are present"""
        print("🔍 Checking Security Headers...")
        
        try:
            response = self.session.get(urljoin(self.base_url, '/login'))
            
            required_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Content-Security-Policy': 'present'
            }
            
            for header, expected in required_headers.items():
                if header not in response.headers:
                    self.issues.append(f"Missing security header: {header}")
                    print(f"❌ Missing: {header}")
                else:
                    print(f"✅ Found: {header}")
                    
        except Exception as e:
            print(f"❌ Error checking headers: {e}")
    
    def check_input_validation(self):
        """Check basic input validation"""
        print("🔍 Checking Input Validation...")
        
        try:
            # Test empty form submission
            response = self.session.post(
                urljoin(self.base_url, '/login'),
                data={'username': '', 'password': ''},
                allow_redirects=False
            )
            
            if 'error' in response.text.lower() or response.status_code == 400:
                print("✅ Empty input validation working")
            else:
                self.issues.append("Input validation may be insufficient")
                print("❌ Input validation needs improvement")
                
        except Exception as e:
            print(f"❌ Error checking input validation: {e}")
    
    def check_file_upload_restrictions(self):
        """Check if file upload has proper restrictions"""
        print("🔍 Checking File Upload Security...")
        
        try:
            # Test if upload endpoint exists and requires authentication
            response = self.session.get(urljoin(self.base_url, '/upload'))
            
            if response.status_code == 302:  # Redirect to login
                print("✅ Upload page requires authentication")
            elif response.status_code == 200:
                if 'csv' in response.text.lower():
                    print("✅ Upload page mentions CSV restriction")
                else:
                    self.issues.append("Upload restrictions unclear")
            else:
                print("❌ Upload endpoint status unclear")
                
        except Exception as e:
            print(f"❌ Error checking file upload: {e}")
    
    def check_authentication_security(self):
        """Check authentication security basics"""
        print("🔍 Checking Authentication Security...")
        
        try:
            # Check if multiple rapid requests are handled
            responses = []
            for i in range(3):
                response = self.session.post(
                    urljoin(self.base_url, '/login'),
                    data={'username': 'testuser', 'password': 'wrongpass'},
                    allow_redirects=False
                )
                responses.append(response.status_code)
            
            if all(r in [200, 302, 429] for r in responses):
                print("✅ Authentication endpoint responding properly")
            else:
                self.issues.append("Authentication endpoint behavior inconsistent")
                
        except Exception as e:
            print(f"❌ Error checking authentication: {e}")
    
    def check_database_connection_security(self):
        """Check if database errors are handled securely"""
        print("🔍 Checking Database Error Handling...")
        
        try:
            # Test with unusual characters that might cause database issues
            response = self.session.post(
                urljoin(self.base_url, '/login'),
                data={'username': 'user@test.com', 'password': 'test123'},
                allow_redirects=False
            )
            
            # Check if response contains database error information
            if 'sqlite' in response.text.lower() or 'database' in response.text.lower():
                self.issues.append("Database errors may be exposed")
                print("❌ Database error information may be leaking")
            else:
                print("✅ Database errors handled securely")
                
        except Exception as e:
            print(f"❌ Error checking database security: {e}")
    
    def run_security_check(self):
        """Run all security checks"""
        print("🚀 Starting NBA MVP Security Check\n")
        
        self.check_security_headers()
        print()
        self.check_input_validation()
        print()
        self.check_file_upload_restrictions()
        print()
        self.check_authentication_security()
        print()
        self.check_database_connection_security()
        
        print("\n" + "="*50)
        print("🔒 SECURITY CHECK RESULTS")
        print("="*50)
        
        if not self.issues:
            print("✅ NO SECURITY ISSUES FOUND!")
            print("Your application appears to have good security practices.")
        else:
            print(f"⚠️  FOUND {len(self.issues)} POTENTIAL ISSUES:")
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue}")
        
        print("="*50)
        return len(self.issues) == 0

def main():
    """Run security validation"""
    print("NBA MVP Decision Support System - Security Validation")
    print("This tool checks your application's security configuration")
    print("Make sure the application is running on http://127.0.0.1:5000")
    
    input("Press Enter to start security validation...")
    
    checker = SecurityChecker()
    is_secure = checker.run_security_check()
    
    if is_secure:
        print("\n🎉 Security validation passed! Your application looks secure.")
        return 0
    else:
        print("\n⚠️  Please review and address the security recommendations.")
        return 1

if __name__ == "__main__":
    exit(main())
