# NBA MVP Decision Support System - Security Guide

## 🔒 Security Features Implemented

This guide outlines the comprehensive security measures implemented to protect your NBA MVP application against common web vulnerabilities.

## 🛡️ Protection Against XSS (Cross-Site Scripting)

### 1. HTML Sanitization
- **What it does**: Automatically sanitizes all user input to prevent malicious scripts
- **Implementation**: Using `bleach` library and HTML escaping
- **Files affected**: `security_utils.py`, all templates

### 2. Content Security Policy (CSP)
- **Header added**: `Content-Security-Policy` with restricted script sources
- **Effect**: Prevents execution of unauthorized scripts
- **Location**: `security_utils.py` - `security_headers` decorator

### 3. Template Protection
- **Jinja2 auto-escaping**: All variables automatically escaped with `| e` filter
- **Safe output**: Only trusted content marked as safe
- **Files**: All `.html` templates updated

## 🛡️ Protection Against SQL Injection

### 1. Parameterized Queries
- **What it does**: Uses placeholders instead of string concatenation
- **Implementation**: `DatabaseSecurity` class with safe query methods
- **Example**:
  ```python
  # SECURE
  DatabaseSecurity.execute_query("SELECT * FROM users WHERE id = ?", (user_id,))
  
  # INSECURE (AVOID)
  cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
  ```

### 2. Input Validation
- **Username**: Letters, numbers, underscore, hyphen only (3-50 chars)
- **Email**: Proper email format validation
- **Password**: Minimum 8 characters, letters + numbers required
- **File uploads**: Extension and size validation

## 🛡️ File Upload Security

### 1. File Validation
- **Extensions**: Only `.csv` files allowed
- **Size limits**: Maximum 16MB
- **Filename sanitization**: Removes dangerous characters
- **Content validation**: Checks CSV format before processing

### 2. Secure File Handling
```python
# Secure filename generation
safe_filename = SecurityValidator.validate_file_upload(file)

# Temporary storage with cleanup
file_path = os.path.join(SECURE_UPLOAD_FOLDER, safe_filename)
# ... process file ...
os.remove(file_path)  # Always cleanup
```

## 🛡️ Session Security

### 1. Session Management
- **Session timeout**: 24 hours with activity tracking
- **Secure session IDs**: UUID4 generation
- **Session validation**: Regular security checks
- **Activity logging**: All actions tracked with IP and user agent

### 2. Authentication Security
- **Rate limiting**: 5 login attempts per 15 minutes per IP
- **Password hashing**: Werkzeug's secure password hashing
- **Failed login logging**: Security events tracked

## 🛡️ Security Headers

All responses include these security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Browser XSS protection |
| `Content-Security-Policy` | Restricted sources | Controls resource loading |
| `Strict-Transport-Security` | `max-age=31536000` | Forces HTTPS |

## 🔧 Implementation Guide

### 1. Install Security Dependencies
```bash
pip install -r requirements.txt
# or run: install_security.bat
```

### 2. Key Security Classes

#### SecurityValidator
```python
from security_utils import SecurityValidator

# Sanitize user input
clean_input = SecurityValidator.sanitize_user_input(user_input)

# Validate forms
is_valid, message = SecurityValidator.validate_username(username)
```

#### DatabaseSecurity
```python
from security_utils import DatabaseSecurity

# Safe database queries
user = DatabaseSecurity.safe_user_lookup(username)
DatabaseSecurity.safe_log_activity(user_id, action, details)
```

### 3. Security Decorators

```python
from security_utils import security_headers, rate_limit_check, sanitize_form_input

@app.route('/login', methods=['POST'])
@security_headers
@rate_limit_check(max_attempts=5, window_minutes=15)
@sanitize_form_input(['username', 'password'])
def login():
    # Your secure login logic
    pass
```

## 🧪 Security Testing

### 1. Run Security Tests
```bash
python security_test.py
```

### 2. Manual Testing Checklist

- [ ] Try XSS payloads in forms: `<script>alert('XSS')</script>`
- [ ] Test SQL injection: `' OR '1'='1`
- [ ] Upload malicious files: `.php`, `.exe` files
- [ ] Check security headers in browser dev tools
- [ ] Test rate limiting by multiple failed logins
- [ ] Verify session timeout behavior

### 3. Vulnerability Checks

The security test script checks for:
- ✅ XSS protection in forms
- ✅ SQL injection prevention
- ✅ File upload restrictions
- ✅ Security headers presence
- ✅ Input validation
- ✅ Session security

## 🚨 Security Best Practices

### 1. Regular Updates
```bash
# Keep dependencies updated
pip install --upgrade -r requirements.txt

# Check for security vulnerabilities
pip-audit  # If installed
```

### 2. Environment Security
- Use strong secret keys in production
- Enable HTTPS in production
- Set up proper logging and monitoring
- Regular database backups
- Use environment variables for secrets

### 3. Monitoring and Logging

Security events are logged to:
- **Database**: `user_activity` table
- **Console**: Security logger
- **Categories**: login_failed, file_upload_rejected, etc.

### 4. Production Deployment

```python
# Use strong secret key
app.secret_key = os.environ.get('SECRET_KEY', 'your-strong-random-key')

# Enable HTTPS only
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

## 🔍 Common Attack Vectors Prevented

| Attack Type | Prevention Method | Status |
|-------------|-------------------|--------|
| XSS | HTML sanitization + CSP | ✅ Protected |
| SQL Injection | Parameterized queries | ✅ Protected |
| CSRF | SameSite cookies + validation | ✅ Protected |
| File Upload | Extension + size validation | ✅ Protected |
| Session Hijacking | Secure session management | ✅ Protected |
| Clickjacking | X-Frame-Options header | ✅ Protected |
| MIME Sniffing | X-Content-Type-Options | ✅ Protected |
| Brute Force | Rate limiting | ✅ Protected |

## 📞 Security Incident Response

If you discover a security issue:

1. **Immediate**: Change admin passwords
2. **Check logs**: Review `user_activity` table for suspicious activity
3. **Update**: Install latest security patches
4. **Monitor**: Watch for unusual activity patterns
5. **Report**: Document the incident for future prevention

## 🔧 Troubleshooting

### Common Issues

1. **"bleach module not found"**
   ```bash
   pip install bleach==6.1.0
   ```

2. **"Content Security Policy blocking scripts"**
   - Check CSP header in `security_utils.py`
   - Add trusted domains to CSP if needed

3. **"File upload rejected"**
   - Verify file is `.csv` format
   - Check file size (max 16MB)
   - Ensure filename has no special characters

### Debug Mode
```python
# Add to app.py for debugging (REMOVE in production)
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🎯 Summary

Your NBA MVP application now has enterprise-grade security featuring:

- ✅ **XSS Protection**: Input sanitization and CSP headers
- ✅ **SQL Injection Prevention**: Parameterized queries only
- ✅ **File Upload Security**: Validation and sanitization
- ✅ **Session Security**: Timeout and activity tracking
- ✅ **Rate Limiting**: Brute force protection
- ✅ **Security Headers**: Full OWASP recommendations
- ✅ **Input Validation**: Comprehensive form validation
- ✅ **Security Logging**: Activity monitoring and alerts

Run `python security_test.py` to verify all protections are working correctly!
