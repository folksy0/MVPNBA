#!/usr/bin/env python3
"""
Quick Security Test for NBA MVP Application
Simple command-line tool to test XSS and SQL injection protection
"""

def test_xss_manually():
    """Instructions for manual XSS testing"""
    print("🛡️ XSS Protection Testing")
    print("=" * 40)
    print("Go to your login page: http://127.0.0.1:5000/login")
    print("\nTry these payloads in the username field:")
    
    xss_payloads = [
        '<script>alert("XSS")</script>',
        '<img src=x onerror=alert("XSS")>',
        'javascript:alert("XSS")',
        '"><script>alert("XSS")</script>',
    ]
    
    for i, payload in enumerate(xss_payloads, 1):
        print(f"\n{i}. {payload}")
    
    print("\n✅ GOOD (Secure): No popups appear, input is escaped/sanitized")
    print("❌ BAD (Vulnerable): JavaScript alert popups appear")

def test_sql_manually():
    """Instructions for manual SQL injection testing"""
    print("\n🛡️ SQL Injection Protection Testing")
    print("=" * 40)
    print("Go to your login page: http://127.0.0.1:5000/login")
    print("\nTry these payloads in the username field:")
    
    sql_payloads = [
        "admin' OR '1'='1",
        "admin'--",
        "admin' UNION SELECT * FROM users--",
        "' OR 1=1 --",
    ]
    
    for i, payload in enumerate(sql_payloads, 1):
        print(f"\n{i}. {payload}")
    
    print("\n✅ GOOD (Secure): Login fails with normal error message")
    print("❌ BAD (Vulnerable): Successful login or database errors shown")

def automated_test():
    """Run automated security test"""
    print("\n🤖 Running Automated Security Test...")
    print("=" * 40)
    
    try:
        import requests
        
        # Test if app is running
        try:
            response = requests.get("http://127.0.0.1:5000/login", timeout=5)
            print("✅ Application is running")
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to http://127.0.0.1:5000")
            print("Please start your NBA MVP application first")
            return
        
        # Test XSS protection
        print("\nTesting XSS protection...")
        xss_payload = '<script>alert("xss")</script>'
        response = requests.post(
            "http://127.0.0.1:5000/login",
            data={'username': xss_payload, 'password': 'test'}
        )
        
        if '<script>' in response.text:
            print("❌ XSS vulnerability detected!")
        else:
            print("✅ XSS protection working")
        
        # Test SQL injection protection
        print("Testing SQL injection protection...")
        sql_payload = "admin' OR '1'='1"
        response = requests.post(
            "http://127.0.0.1:5000/login",
            data={'username': sql_payload, 'password': 'test'},
            allow_redirects=False
        )
        
        if response.status_code in [301, 302] and 'dashboard' in response.headers.get('Location', ''):
            print("❌ SQL injection vulnerability detected!")
        elif 'welcome' in response.text.lower():
            print("❌ Possible SQL injection vulnerability!")
        else:
            print("✅ SQL injection protection working")
        
        # Test security headers
        print("Checking security headers...")
        headers_to_check = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Content-Security-Policy'
        ]
        
        for header in headers_to_check:
            if header in response.headers:
                print(f"✅ {header}: {response.headers[header]}")
            else:
                print(f"❌ Missing: {header}")
        
    except ImportError:
        print("❌ 'requests' module not found. Please install it:")
        print("pip install requests")
    except Exception as e:
        print(f"❌ Error during automated testing: {e}")

def main():
    """Main menu"""
    while True:
        print("\n" + "="*50)
        print("🔒 NBA MVP Security Testing Tool")
        print("="*50)
        print("1. Manual XSS Testing Instructions")
        print("2. Manual SQL Injection Testing Instructions")
        print("3. Run Automated Security Test")
        print("4. Open HTML Testing Tool")
        print("5. Exit")
        
        choice = input("\nSelect an option (1-5): ").strip()
        
        if choice == '1':
            test_xss_manually()
        elif choice == '2':
            test_sql_manually()
        elif choice == '3':
            automated_test()
        elif choice == '4':
            import webbrowser
            import os
            html_file = os.path.join(os.path.dirname(__file__), 'security_testing_tool.html')
            if os.path.exists(html_file):
                webbrowser.open(f'file://{html_file}')
                print("✅ Opening HTML testing tool in your browser...")
            else:
                print("❌ HTML testing tool not found")
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    main()
