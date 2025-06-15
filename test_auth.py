#!/usr/bin/env python3
"""
Simplified NBA MVP Application Test
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import uuid
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'nba_mvp_secret_key_2024'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    # Users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # User activity tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            action_details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # User sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            logout_time TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    
    # Create default admin user if it doesn't exist
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    admin_count = cursor.fetchone()[0]
    
    if admin_count == 0:
        admin_password_hash = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@nbamvp.com', admin_password_hash, 'admin'))
        conn.commit()
        print("Default admin user created: admin/admin123")
    
    conn.close()

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        if session.get('user_role') != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Main route - redirect to login or dashboard based on auth status"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # User is authenticated, redirect based on role
    if session.get('user_role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with database authentication"""
    if 'user_id' in session:
        # User already logged in, redirect based on role
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('auth/login.html')
        
        try:
            conn = sqlite3.connect('nba_mvp.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, password_hash, role, is_active 
                FROM users WHERE username = ? OR email = ?
            ''', (username, username))
            user = cursor.fetchone()
            conn.close()
            
            if user and user[5] and check_password_hash(user[3], password):
                # Set session variables
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['user_email'] = user[2]
                session['user_role'] = user[4]
                session.permanent = True
                
                flash(f'Welcome back, {user[1]}!', 'success')
                
                # Redirect based on role
                if user[4] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
                
        except Exception as e:
            flash('An error occurred during login. Please try again.', 'error')
            print(f"Login error: {e}")
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    return f"<h1>Welcome {session.get('username')}!</h1><p>Role: {session.get('user_role')}</p><a href='/logout'>Logout</a>"

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        # Get user statistics
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin" AND is_active = 1')
        total_admins = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "user" AND is_active = 1')
        total_regular_users = cursor.fetchone()[0]
        
        # Get all users for management
        cursor.execute('''
            SELECT u.id, u.username, u.email, u.role, u.is_active, u.created_at
            FROM users u
            ORDER BY u.created_at DESC
        ''')
        all_users = cursor.fetchall()
        
        conn.close()
        
        dashboard_stats = {
            'total_users': total_users,
            'total_admins': total_admins, 
            'total_regular_users': total_regular_users
        }
        
        return render_template('admin/dashboard.html',
                             dashboard_stats=dashboard_stats,
                             recent_activity=[],
                             active_sessions=[],
                             all_users=all_users)
        
    except Exception as e:
        flash('Error loading admin dashboard', 'error')
        print(f"Admin dashboard error: {e}")
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    print("=" * 60)
    print("NBA MVP Decision Support System - Authentication Test")
    print("=" * 60)
    
    print("Initializing database...")
    init_database()
    print("✓ Database initialized successfully")
    
    print("\nStarting Flask application...")
    print("✓ Server will be available at: http://localhost:5000")
    print("✓ Default admin credentials: admin / admin123")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
