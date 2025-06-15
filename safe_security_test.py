#!/usr/bin/env python3
"""
Safe Security Validation Tool for NBA MVP Application
Tests XSS and SQL injection protections without triggering antivirus
"""

import requests
import json
import time
from urllib.parse import urljoin

class SafeSecurityValidator:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def log_test(self, test_name, passed, details=""):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({
            'test': test_name,
            'status': status,
            'passed': passed,
            'details': details
        })
        print(f"{status} - {test_name}")
        if details:
            print(f"    Details: {details}")
    
    def test_xss_protection(self):
        """Test XSS protection in login form"""
        print("\n🛡️ Testing XSS Protection...")
        
        # Test cases for XSS
        xss_tests = [
            {
                'name': 'Basic Script Tag',
                'payload': '<script>alert("xss")</script>',
                'description': 'Tests if script tags are sanitized'
            },
            {
                'name': 'Image Tag XSS',
                'payload': '<img src=x onerror=alert("xss")>',
                'description': 'Tests if malicious image tags are blocked'
            },
            {
                'name': 'JavaScript URL',
                'payload': 'javascript:alert("xss")',
                'description': 'Tests if javascript: URLs are sanitized'
            },
            {
                'name': 'HTML Entities',
                'payload': '&lt;script&gt;alert("xss")&lt;/script&gt;',
                'description': 'Tests if HTML entities are properly handled'
            }
        ]
        
        for test in xss_tests:
            try:
                # Send XSS payload in login form
                response = self.session.post(
                    urljoin(self.base_url, '/login'),
                    data={
                        'username': test['payload'],
                        'password': 'test123'
                    },
                    allow_redirects=False
                )
                
                # Check if payload is reflected back unescaped
                response_text = response.text.lower()
                
                # Look for signs that XSS was NOT prevented
                dangerous_patterns = [
                    '<script>',
                    'onerror=',
                    'javascript:',
                    'alert(',
                    'eval(',
                    'document.cookie'
                ]
                
                xss_found = any(pattern in response_text for pattern in dangerous_patterns)
                
                if xss_found:
                    self.log_test(f"XSS Test: {test['name']}", False, 
                                "XSS payload not properly sanitized!")
                else:
                    self.log_test(f"XSS Test: {test['name']}", True, 
                                "XSS payload properly sanitized")
                    
            except Exception as e:
                self.log_test(f"XSS Test: {test['name']}", False, f"Error: {str(e)}")
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection"""
        print("\n🛡️ Testing SQL Injection Protection...")
        
        # Test cases for SQL injection
        sql_tests = [
            {
                'name': 'Basic OR Bypass',
                'payload': "admin' OR '1'='1",
                'description': 'Tests basic SQL injection bypass attempt'
            },
            {
                'name': 'Comment Bypass',
                'payload': "admin'--",
                'description': 'Tests SQL comment bypass attempt'
            },
            {
                'name': 'Union Select',
                'payload': "admin' UNION SELECT * FROM users--",
                'description': 'Tests UNION SELECT injection'
            },
            {
                'name': 'Blind SQL Injection',
                'payload': "admin' AND (SELECT COUNT(*) FROM users) > 0--",
                'description': 'Tests blind SQL injection attempt'
            }
        ]
        
        for test in sql_tests:
            try:
                # Send SQL injection payload in login form
                response = self.session.post(
                    urljoin(self.base_url, '/login'),
                    data={
                        'username': test['payload'],
                        'password': 'test123'
                    },
                    allow_redirects=False
                )
                
                # Check for signs of SQL injection success
                response_text = response.text.lower()
                
                # Signs that SQL injection might have worked
                sql_success_indicators = [
                    'welcome back',  # Successful login
                    '/dashboard',    # Redirect to dashboard
                    'admin panel',   # Access to admin area
                ]
                
                # Signs of SQL errors (also bad - should be handled gracefully)
                sql_error_indicators = [
                    'sqlite',
                    'syntax error',
                    'database',
                    'sql',
                    'table',
                    'column'
                ]
                
                # Check if we got redirected (potential successful bypass)
                if response.status_code in [301, 302]:
                    location = response.headers.get('Location', '')
                    if 'dashboard' in location or 'admin' in location:
                        self.log_test(f"SQL Test: {test['name']}", False,
                                    "Possible SQL injection bypass - redirected to protected area")
                        continue
                
                # Check for SQL success indicators
                sql_success = any(indicator in response_text for indicator in sql_success_indicators)
                sql_errors = any(error in response_text for error in sql_error_indicators)
                
                if sql_success:
                    self.log_test(f"SQL Test: {test['name']}", False,
                                "SQL injection may have succeeded")
                elif sql_errors:
                    self.log_test(f"SQL Test: {test['name']}", False,
                                "SQL errors exposed to user")
                else:
                    self.log_test(f"SQL Test: {test['name']}", True,
                                "SQL injection properly prevented")
                    
            except Exception as e:
                self.log_test(f"SQL Test: {test['name']}", False, f"Error: {str(e)}")
    
    def test_input_validation(self):
        """Test input validation"""
        print("\n🛡️ Testing Input Validation...")
        
        validation_tests = [
            {
                'name': 'Empty Username',
                'username': '',
                'password': 'test123',
                'should_fail': True
            },
            {
                'name': 'Empty Password', 
                'username': 'testuser',
                'password': '',
                'should_fail': True
            },
            {
                'name': 'Very Long Username',
                'username': 'a' * 500,
                'password': 'test123',
                'should_fail': True
            },
            {
                'name': 'Invalid Email Format',
                'username': 'invalid-email-format',
                'password': 'test123',
                'should_fail': True
            }
        ]
        
        for test in validation_tests:
            try:
                response = self.session.post(
                    urljoin(self.base_url, '/login'),
                    data={
                        'username': test['username'],
                        'password': test['password']
                    },
                    allow_redirects=False
                )
                
                # Check if validation worked as expected
                response_text = response.text.lower()
                
                # Look for validation error messages
                validation_errors = [
                    'required',
                    'invalid',
                    'error',
                    'please enter',
                    'format',
                    'too long',
                    'too short'
                ]
                
                has_validation_error = any(error in response_text for error in validation_errors)
                
                if test['should_fail']:
                    if has_validation_error or response.status_code == 400:
                        self.log_test(f"Validation Test: {test['name']}", True,
                                    "Input properly validated")
                    else:
                        self.log_test(f"Validation Test: {test['name']}", False,
                                    "Input validation may be missing")
                else:
                    if not has_validation_error:
                        self.log_test(f"Validation Test: {test['name']}", True,
                                    "Valid input accepted")
                    else:
                        self.log_test(f"Validation Test: {test['name']}", False,
                                    "Valid input rejected")
                        
            except Exception as e:
                self.log_test(f"Validation Test: {test['name']}", False, f"Error: {str(e)}")
    
    def test_rate_limiting(self):
        """Test rate limiting protection"""
        print("\n🛡️ Testing Rate Limiting...")
        
        try:
            # Attempt multiple rapid login attempts
            responses = []
            for i in range(6):  # Try 6 attempts (should be limited after 5)
                response = self.session.post(
                    urljoin(self.base_url, '/login'),
                    data={
                        'username': 'testuser',
                        'password': 'wrongpassword'
                    },
                    allow_redirects=False
                )
                responses.append(response.status_code)
                time.sleep(0.1)  # Small delay between requests
            
            # Check if rate limiting kicked in
            if 429 in responses:  # HTTP 429 Too Many Requests
                self.log_test("Rate Limiting Test", True, "Rate limiting active (HTTP 429)")
            elif len(set(responses)) > 1:  # Different response codes indicate some form of limiting
                self.log_test("Rate Limiting Test", True, "Rate limiting appears active")
            else:
                # Check response content for rate limiting messages
                last_response = self.session.post(
                    urljoin(self.base_url, '/login'),
                    data={'username': 'testuser', 'password': 'wrongpassword'},
                    allow_redirects=False
                )
                
                rate_limit_indicators = [
                    'too many',
                    'rate limit',
                    'try again later',
                    'attempts exceeded'
                ]
                
                if any(indicator in last_response.text.lower() for indicator in rate_limit_indicators):
                    self.log_test("Rate Limiting Test", True, "Rate limiting message detected")
                else:
                    self.log_test("Rate Limiting Test", False, "No rate limiting detected")
                    
        except Exception as e:
            self.log_test("Rate Limiting Test", False, f"Error: {str(e)}")
    
    def test_security_headers(self):
        """Test security headers"""
        print("\n🛡️ Testing Security Headers...")
        
        try:
            response = self.session.get(urljoin(self.base_url, '/login'))
            headers = response.headers
            
            security_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
                'X-XSS-Protection': '1; mode=block',
                'Content-Security-Policy': None  # Just check if present
            }
            
            for header, expected in security_headers.items():
                if header in headers:
                    if expected is None:  # Just check presence
                        self.log_test(f"Security Header: {header}", True, f"Present: {headers[header]}")
                    elif isinstance(expected, list):  # Multiple valid values
                        if headers[header] in expected:
                            self.log_test(f"Security Header: {header}", True, f"Value: {headers[header]}")
                        else:
                            self.log_test(f"Security Header: {header}", False, f"Unexpected value: {headers[header]}")
                    else:  # Exact match
                        if headers[header] == expected:
                            self.log_test(f"Security Header: {header}", True, f"Correct value")
                        else:
                            self.log_test(f"Security Header: {header}", False, f"Wrong value: {headers[header]}")
                else:
                    self.log_test(f"Security Header: {header}", False, "Header missing")
                    
        except Exception as e:
            self.log_test("Security Headers Test", False, f"Error: {str(e)}")
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🚀 NBA MVP Security Validation Suite")
        print("=" * 50)
        print("Testing your application's security defenses...")
        print("=" * 50)
        
        # Run all tests
        self.test_security_headers()
        self.test_xss_protection()
        self.test_sql_injection_protection()
        self.test_input_validation()
        self.test_rate_limiting()
        
        # Generate report
        print("\n" + "=" * 50)
        print("🔒 SECURITY TEST RESULTS")
        print("=" * 50)
        
        passed_tests = sum(1 for result in self.results if result['passed'])
        total_tests = len(self.results)
        
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n📊 Detailed Results:")
        for result in self.results:
            print(f"{result['status']} {result['test']}")
            if result['details']:
                print(f"    → {result['details']}")
        
        if passed_tests == total_tests:
            print("\n🎉 EXCELLENT! All security tests passed!")
            print("Your application is well protected against common attacks.")
        elif passed_tests >= total_tests * 0.8:
            print("\n✅ GOOD! Most security tests passed.")
            print("Review the failed tests for potential improvements.")
        else:
            print("\n⚠️ NEEDS ATTENTION! Several security tests failed.")
            print("Please review and fix the security issues found.")
        
        print("=" * 50)
        return passed_tests == total_tests

def main():
    """Main function"""
    print("NBA MVP Security Validation Tool")
    print("This tool safely tests your application's security defenses")
    print("Make sure your NBA MVP app is running on http://127.0.0.1:5000")
    
    # Check if application is running
    try:
        response = requests.get("http://127.0.0.1:5000", timeout=5)
        print("✅ Application is running and accessible")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to http://127.0.0.1:5000")
        print("Please start your NBA MVP application first")
        return 1
    except Exception as e:
        print(f"❌ Error connecting to application: {e}")
        return 1
    
    input("\nPress Enter to start security testing...")
    
    validator = SafeSecurityValidator()
    is_secure = validator.run_all_tests()
    
    return 0 if is_secure else 1

if __name__ == "__main__":
    exit(main())
