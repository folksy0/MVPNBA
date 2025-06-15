"""
Security utilities for NBA MVP Decision Support System
Provides protection against XSS, SQL injection, and other security vulnerabilities
"""

import re
import html
import bleach
from urllib.parse import quote, unquote
import sqlite3
from functools import wraps
from flask import request, session, abort, flash, redirect, url_for
import logging
from datetime import datetime, timedelta

# Configure logging for security events
logging.basicConfig(level=logging.INFO)
security_logger = logging.getLogger('security')

# Allowed HTML tags for rich text content (very restrictive)
ALLOWED_HTML_TAGS = ['b', 'i', 'u', 'strong', 'em', 'br', 'p']
ALLOWED_HTML_ATTRIBUTES = {}

class SecurityValidator:
    """Comprehensive security validation class"""
    
    @staticmethod
    def sanitize_html(input_text):
        """Sanitize HTML content to prevent XSS attacks"""
        if not input_text:
            return ""
        
        # First escape all HTML entities
        escaped = html.escape(str(input_text))
        
        # Use bleach for additional cleaning (if allowing some HTML)
        cleaned = bleach.clean(
            escaped,
            tags=ALLOWED_HTML_TAGS,
            attributes=ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )
        
        return cleaned
    
    @staticmethod
    def sanitize_user_input(input_text, max_length=255, allow_special_chars=False):
        """Sanitize general user input"""
        if not input_text:
            return ""
        
        # Convert to string and strip whitespace
        sanitized = str(input_text).strip()
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Remove dangerous characters if not allowing special chars
        if not allow_special_chars:
            # Only allow alphanumeric, spaces, basic punctuation
            sanitized = re.sub(r'[^\w\s\-\.\,\'\"]', '', sanitized)
        
        # HTML escape for XSS prevention
        sanitized = html.escape(sanitized)
        
        return sanitized
    
    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not username:
            return False, "Username is required"
        
        username = username.strip()
        
        # Length check
        if len(username) < 3 or len(username) > 50:
            return False, "Username must be between 3 and 50 characters"
        
        # Character validation - only letters, numbers, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscore, and hyphen"
        
        return True, username
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email:
            return False, "Email is required"
        
        email = email.strip().lower()
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        if len(email) > 254:
            return False, "Email address too long"
        
        return True, email
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password too long (max 128 characters)"
        
        # Check for at least one letter and one number
        if not re.search(r'[a-zA-Z]', password):
            return False, "Password must contain at least one letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        return True, password
    
    @staticmethod
    def validate_file_upload(file, allowed_extensions=['csv'], max_size_mb=16):
        """Validate file upload security"""
        if not file or not file.filename:
            return False, "No file selected"
        
        # Check file extension
        if '.' not in file.filename:
            return False, "File must have an extension"
        
        extension = file.filename.rsplit('.', 1)[1].lower()
        if extension not in allowed_extensions:
            return False, f"Only {', '.join(allowed_extensions)} files are allowed"
        
        # Check file size (this is basic - Flask config handles the real limit)
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if size > max_size_mb * 1024 * 1024:
            return False, f"File too large (max {max_size_mb}MB)"
        
        if size == 0:
            return False, "File is empty"
        
        # Sanitize filename
        safe_filename = re.sub(r'[^\w\-_\.]', '', file.filename)
        if not safe_filename:
            safe_filename = "upload.csv"
        
        return True, safe_filename

class DatabaseSecurity:
    """Database security utilities with parameterized queries"""
    
    @staticmethod
    def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        """Execute parameterized query safely"""
        try:
            conn = sqlite3.connect('nba_mvp.db')
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            
            conn.commit()
            conn.close()
            
            return result
            
        except sqlite3.Error as e:
            security_logger.error(f"Database error: {e}")
            return None
    
    @staticmethod
    def safe_user_lookup(username_or_email):
        """Safely lookup user by username or email"""
        query = '''
            SELECT id, username, email, password_hash, role, is_active 
            FROM users WHERE username = ? OR email = ?
        '''
        return DatabaseSecurity.execute_query(query, (username_or_email, username_or_email), fetch_one=True)
    
    @staticmethod
    def safe_create_user(username, email, password_hash, role, created_by):
        """Safely create a new user"""
        query = '''
            INSERT INTO users (username, email, password_hash, role, created_by)
            VALUES (?, ?, ?, ?, ?)
        '''
        return DatabaseSecurity.execute_query(query, (username, email, password_hash, role, created_by))
    
    @staticmethod
    def safe_log_activity(user_id, action_type, action_details, ip_address, user_agent):
        """Safely log user activity"""
        query = '''
            INSERT INTO user_activity (user_id, action_type, action_details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        '''
        return DatabaseSecurity.execute_query(query, (user_id, action_type, action_details, ip_address, user_agent))

def security_headers(f):
    """Add security headers to responses"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        # Add security headers
        if hasattr(response, 'headers'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; img-src 'self' data:; font-src 'self' cdn.jsdelivr.net;"
        
        return response
    return decorated_function

def rate_limit_check(max_attempts=5, window_minutes=15):
    """Basic rate limiting for login attempts"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Simple in-memory rate limiting (in production, use Redis or database)
            if not hasattr(rate_limit_check, 'attempts'):
                rate_limit_check.attempts = {}
            
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            current_time = datetime.now()
            
            # Clean old attempts
            if client_ip in rate_limit_check.attempts:
                rate_limit_check.attempts[client_ip] = [
                    attempt_time for attempt_time in rate_limit_check.attempts[client_ip]
                    if (current_time - attempt_time).total_seconds() < window_minutes * 60
                ]
            
            # Check if rate limit exceeded
            if client_ip in rate_limit_check.attempts and len(rate_limit_check.attempts[client_ip]) >= max_attempts:
                security_logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                flash('Too many attempts. Please try again later.', 'error')
                return redirect(url_for('login'))
            
            # Record this attempt
            if client_ip not in rate_limit_check.attempts:
                rate_limit_check.attempts[client_ip] = []
            rate_limit_check.attempts[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_security_event(event_type, details, user_id=None):
    """Log security-related events"""
    ip_address = request.environ.get('REMOTE_ADDR', 'unknown')
    user_agent = request.headers.get('User-Agent', 'unknown')
    
    security_logger.warning(f"SECURITY EVENT - {event_type}: {details} | IP: {ip_address} | User: {user_id}")
    
    # Also log to database if user_id is available
    if user_id:
        DatabaseSecurity.safe_log_activity(user_id, f"security_{event_type}", details, ip_address, user_agent)

def validate_session_security():
    """Validate session security"""
    if 'user_id' not in session:
        return False
    
    # Check session timeout
    if 'last_activity' in session:
        from datetime import datetime, timedelta
        last_activity = datetime.fromisoformat(session['last_activity'])
        if datetime.now() - last_activity > timedelta(hours=24):
            session.clear()
            return False
    
    # Update last activity
    session['last_activity'] = datetime.now().isoformat()
    
    return True

# Input sanitization decorators
def sanitize_form_input(fields):
    """Decorator to automatically sanitize form input"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == 'POST':
                for field in fields:
                    if field in request.form:
                        # Store original for validation, sanitized for use
                        original_value = request.form.get(field, '')
                        sanitized_value = SecurityValidator.sanitize_user_input(original_value)
                        
                        # Add sanitized value to request context
                        if not hasattr(request, 'sanitized_form'):
                            request.sanitized_form = {}
                        request.sanitized_form[field] = sanitized_value
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
