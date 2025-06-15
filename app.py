"""
NBA MVP Decision Support System
Flask Application with Mazar Template Integration
Enhanced with comprehensive security measures
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pandas as pd
import numpy as np
import os
import sqlite3
from datetime import datetime, timedelta
import json
import uuid
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import base64

# Import security utilities
from security_utils import (
    SecurityValidator, DatabaseSecurity, security_headers, 
    rate_limit_check, log_security_event, validate_session_security,
    sanitize_form_input
)

app = Flask(__name__)
app.secret_key = 'nba_mvp_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Session timeout

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/charts', exist_ok=True)

# Weight Criteria untuk MVP
MVP_WEIGHTS = {
    "C1": 0.08,  # Total Games
    "C2": 0.08,  # Minutes Played  
    "C3": 0.09,  # FG% (Field Goal Percentage)
    "C4": 0.15,  # PTS (Points)
    "C5": 0.15,  # TRB (Total Rebounds)
    "C6": 0.15,  # AST (Assists)
    "C7": 0.15,  # STL (Steals)
    "C8": 0.10,  # BLK (Blocks)
    "C9": 0.5,   # TEAM (Team Performance Factor)
    "C10": 0.25, # TOV (Turnovers - benefit criteria)
    "C11": 0.10  # PF (Personal Fouls - benefit criteria)
}

# Benefit and Cost criteria
BENEFIT_CRITERIA = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9']
COST_CRITERIA = ['C10', 'C11']

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
    
    # Players table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            team TEXT NOT NULL,
            season INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Statistics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            games INTEGER,
            minutes REAL,
            fg_percent REAL,
            points REAL,
            rebounds REAL,
            assists REAL,
            steals REAL,
            blocks REAL,
            turnovers REAL,
            personal_fouls REAL,
            team_performance REAL DEFAULT 50.0,
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
    ''')
    
    # MVP Scores table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mvp_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            season INTEGER,
            normalized_score REAL,
            final_score REAL,
            rank_position INTEGER,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
    ''')
      # Upload sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS upload_sessions (
            id TEXT PRIMARY KEY,
            filename TEXT,
            total_records INTEGER,
            processed_records INTEGER,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # File uploads table to track user-specific file storage
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id TEXT,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            upload_order INTEGER,
            file_type TEXT DEFAULT 'csv',
            status TEXT DEFAULT 'uploaded',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (session_id) REFERENCES upload_sessions (id)
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

# Authentication helper functions
def log_user_activity(user_id, action_type, action_details=None, ip_address=None, user_agent=None):
    """Log user activity to database"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_activity (user_id, action_type, action_details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action_type, action_details, ip_address, user_agent))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging user activity: {e}")

def create_user_session(user_id, ip_address=None, user_agent=None):
    """Create a new user session"""
    session_id = str(uuid.uuid4())
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_sessions (id, user_id, ip_address, user_agent)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_id, ip_address, user_agent))
        conn.commit()
        conn.close()
        return session_id
    except Exception as e:
        print(f"Error creating user session: {e}")
        return None

def update_session_activity(session_id):
    """Update last activity time for a session"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_sessions 
            SET last_activity = CURRENT_TIMESTAMP 
            WHERE id = ? AND is_active = 1
        ''', (session_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating session activity: {e}")

def end_user_session(session_id):
    """End a user session"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_sessions 
            SET logout_time = CURRENT_TIMESTAMP, is_active = 0 
            WHERE id = ?
        ''', (session_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error ending user session: {e}")

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Update session activity
        if 'session_id' in session:
            update_session_activity(session['session_id'])
        
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
        
        # Update session activity
        if 'session_id' in session:
            update_session_activity(session['session_id'])
        
        return f(*args, **kwargs)
    return decorated_function

def admin_restricted(f):
    """Decorator to restrict admin access to certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        if session.get('user_role') == 'admin':
            flash('Admins can only access the Admin Panel and Upload Data functions.', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Update session activity
        if 'session_id' in session:
            update_session_activity(session['session_id'])
        
        return f(*args, **kwargs)
    return decorated_function

class MVPCalculator:
    """MVP Decision Support System Calculator"""
    
    def __init__(self, weights=MVP_WEIGHTS):
        self.weights = weights
        self.benefit_criteria = BENEFIT_CRITERIA
        self.cost_criteria = COST_CRITERIA
    
    def normalize_data(self, df):
        """Normalize data using min-max normalization"""
        normalized_df = df.copy()
        criteria_columns = ['games', 'minutes', 'fg_percent', 'points', 'rebounds', 
                          'assists', 'steals', 'blocks', 'team_performance', 
                          'turnovers', 'personal_fouls']
        
        for i, col in enumerate(criteria_columns, 1):
            criterion = f'C{i}'
            if col in df.columns:
                min_val = df[col].min()
                max_val = df[col].max()
                
                if max_val != min_val:
                    if criterion in self.benefit_criteria:
                        # For benefit criteria: higher is better
                        normalized_df[f'{col}_norm'] = (df[col] - min_val) / (max_val - min_val)
                    else:
                        # For cost criteria: lower is better
                        normalized_df[f'{col}_norm'] = (max_val - df[col]) / (max_val - min_val)
                else:
                    normalized_df[f'{col}_norm'] = 0.5
        
        return normalized_df
    
    def calculate_mvp_scores(self, df):
        """Calculate final MVP scores using weighted criteria"""
        normalized_df = self.normalize_data(df)
        
        # Calculate weighted scores
        normalized_df['final_score'] = 0
        criteria_mapping = {
            'C1': 'games_norm',
            'C2': 'minutes_norm', 
            'C3': 'fg_percent_norm',
            'C4': 'points_norm',
            'C5': 'rebounds_norm',
            'C6': 'assists_norm',
            'C7': 'steals_norm',
            'C8': 'blocks_norm',
            'C9': 'team_performance_norm',
            'C10': 'turnovers_norm',
            'C11': 'personal_fouls_norm'
        }
        
        for criterion, weight in self.weights.items():
            if criterion in criteria_mapping:
                col_name = criteria_mapping[criterion]
                if col_name in normalized_df.columns:
                    normalized_df['final_score'] += normalized_df[col_name] * weight
        
        # Rank players
        normalized_df = normalized_df.sort_values('final_score', ascending=False)
        normalized_df['rank_position'] = range(1, len(normalized_df) + 1)
        
        return normalized_df

def validate_csv_format(file_path):
    """Validate CSV format and required columns with flexible column mapping"""
    try:
        # Try reading with different encoding options and parameters
        df = None
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-8-sig']
        
        for encoding in encodings:
            try:
                # Try different CSV parsing parameters to handle malformed files
                df = pd.read_csv(
                    file_path, 
                    encoding=encoding,
                    sep=',',
                    quoting=1,  # QUOTE_ALL
                    skipinitialspace=True,
                    skip_blank_lines=True,
                    on_bad_lines='skip',  # Skip problematic lines
                    engine='python'  # More robust parser
                )
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                try:
                    # Try with different separator
                    df = pd.read_csv(
                        file_path, 
                        encoding=encoding,
                        sep=';',  # Try semicolon separator
                        quoting=1,
                        skipinitialspace=True,
                        skip_blank_lines=True,
                        on_bad_lines='skip',
                        engine='python'
                    )
                    break
                except:
                    continue
        
        if df is None or df.empty:
            return False, "Unable to read CSV file with any supported encoding or format"
        
        # Clean column names (remove extra spaces, etc.)
        df.columns = df.columns.str.strip()
        
        # Define flexible column mapping - support multiple formats
        column_mappings = {
            # Standard format (from sample)
            'player': ['Player', 'Player Name', 'Name'],
            'team': ['Team', 'Team Name'],
            'games': ['G', 'Games', 'GP', 'Games Played'],
            'minutes': ['MP', 'Minutes', 'MIN', 'Minutes Played'],
            'fg_percent': ['FG%', 'FG Percent', 'Field Goal %', 'Field Goal Percentage'],
            'points': ['PTS', 'Points', 'PPG', 'Points Per Game'],
            'rebounds': ['TRB', 'Rebounds', 'REB', 'RPG', 'Rebounds Per Game'],
            'assists': ['AST', 'Assists', 'APG', 'Assists Per Game'],
            'steals': ['STL', 'Steals', 'SPG', 'Steals Per Game'],
            'blocks': ['BLK', 'Blocks', 'BPG', 'Blocks Per Game'],
            'turnovers': ['TOV', 'Turnovers', 'TO', 'Turnovers Per Game'],
            'personal_fouls': ['PF', 'Personal Fouls', 'Fouls', 'PF Per Game']
        }
        
        # Find actual column names in the CSV
        actual_columns = {}
        missing_fields = []
        
        for field, possible_names in column_mappings.items():
            found = False
            for name in possible_names:
                if name in df.columns:
                    actual_columns[field] = name
                    found = True
                    break
            if not found:
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}. Available columns: {', '.join(df.columns)}"
        
        # Validate numeric columns
        numeric_fields = ['games', 'minutes', 'fg_percent', 'points', 'rebounds', 
                         'assists', 'steals', 'blocks', 'turnovers', 'personal_fouls']
        
        for field in numeric_fields:
            col_name = actual_columns[field]
            # Convert to numeric, replacing any non-numeric values with NaN
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
            
            # Check if we have any valid numeric data
            if df[col_name].isna().all():
                return False, f"Column '{col_name}' contains no valid numeric data"
        
        # Check for minimum number of rows
        if len(df) < 1:
            return False, "CSV file is empty or contains no valid data rows"
        
        return True, f"CSV format is valid. Found {len(df)} player records with columns: {', '.join(df.columns)}"
    
    except Exception as e:
        return False, f"Error reading CSV: {str(e)}"

def process_csv_data(file_path, session_id):
    """Process CSV data and store in database"""
    try:
        # Use same robust CSV reading as validation
        df = None
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-8-sig']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path, 
                    encoding=encoding,
                    sep=',',
                    quoting=1,
                    skipinitialspace=True,
                    skip_blank_lines=True,
                    on_bad_lines='skip',
                    engine='python'
                )
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                try:
                    df = pd.read_csv(
                        file_path, 
                        encoding=encoding,
                        sep=';',
                        quoting=1,
                        skipinitialspace=True,
                        skip_blank_lines=True,
                        on_bad_lines='skip',
                        engine='python'
                    )
                    break
                except:
                    continue
        
        if df is None or df.empty:
            raise Exception("Unable to read CSV file")
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        total_records = len(df)
        processed_records = 0
        
        # Update session
        cursor.execute('''
            UPDATE upload_sessions 
            SET total_records = ?, status = 'processing' 
            WHERE id = ?
        ''', (total_records, session_id))        
        # Define flexible column mapping - same as validation
        column_mappings = {
            'player': ['Player', 'Player Name', 'Name'],
            'team': ['Team', 'Team Name'],
            'games': ['G', 'Games', 'GP', 'Games Played'],
            'minutes': ['MP', 'Minutes', 'MIN', 'Minutes Played'],
            'fg_percent': ['FG%', 'FG Percent', 'Field Goal %', 'Field Goal Percentage'],
            'points': ['PTS', 'Points', 'PPG', 'Points Per Game'],
            'rebounds': ['TRB', 'Rebounds', 'REB', 'RPG', 'Rebounds Per Game'],
            'assists': ['AST', 'Assists', 'APG', 'Assists Per Game'],
            'steals': ['STL', 'Steals', 'SPG', 'Steals Per Game'],
            'blocks': ['BLK', 'Blocks', 'BPG', 'Blocks Per Game'],
            'turnovers': ['TOV', 'Turnovers', 'TO', 'Turnovers Per Game'],
            'personal_fouls': ['PF', 'Personal Fouls', 'Fouls', 'PF Per Game']
        }
        
        # Find actual column names in the CSV
        actual_columns = {}
        for field, possible_names in column_mappings.items():
            for name in possible_names:
                if name in df.columns:
                    actual_columns[field] = name
                    break
        
        # Default season if not provided
        season = 2024
        if 'Season' in df.columns:
            season = df['Season'].iloc[0] if not df['Season'].isna().all() else 2024
        elif 'Season Year' in df.columns:
            season = df['Season Year'].iloc[0] if not df['Season Year'].isna().all() else 2024
        
        for _, row in df.iterrows():
            try:
                # Get values using flexible column mapping
                player_name = row[actual_columns.get('player', df.columns[0])]  # Use first column if no match
                team_name = row[actual_columns.get('team', 'Unknown')] if 'team' in actual_columns else 'Unknown'
                
                # Insert player
                cursor.execute('''
                    INSERT INTO players (name, team, season) 
                    VALUES (?, ?, ?)
                ''', (str(player_name), str(team_name), int(season)))
                
                player_id = cursor.lastrowid
                
                # Get numeric values with safe conversion
                def safe_float(value, default=0.0):
                    try:
                        return float(value) if pd.notna(value) else default
                    except:
                        return default
                
                def safe_int(value, default=0):
                    try:
                        return int(value) if pd.notna(value) else default
                    except:
                        return default
                
                # Insert statistics with safe conversion
                cursor.execute('''
                    INSERT INTO statistics 
                    (player_id, games, minutes, fg_percent, points, rebounds, 
                     assists, steals, blocks, turnovers, personal_fouls, team_performance) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    player_id,
                    safe_int(row[actual_columns.get('games', df.columns[1])] if 'games' in actual_columns else 0),
                    safe_float(row[actual_columns.get('minutes', df.columns[2])] if 'minutes' in actual_columns else 0),
                    safe_float(row[actual_columns.get('fg_percent', df.columns[3])] if 'fg_percent' in actual_columns else 0),
                    safe_float(row[actual_columns.get('points', df.columns[4])] if 'points' in actual_columns else 0),
                    safe_float(row[actual_columns.get('rebounds', df.columns[5])] if 'rebounds' in actual_columns else 0),
                    safe_float(row[actual_columns.get('assists', df.columns[6])] if 'assists' in actual_columns else 0),
                    safe_float(row[actual_columns.get('steals', df.columns[7])] if 'steals' in actual_columns else 0),
                    safe_float(row[actual_columns.get('blocks', df.columns[8])] if 'blocks' in actual_columns else 0),
                    safe_float(row[actual_columns.get('turnovers', df.columns[9])] if 'turnovers' in actual_columns else 0),
                    safe_float(row[actual_columns.get('personal_fouls', df.columns[10])] if 'personal_fouls' in actual_columns else 0),
                    50.0  # Default team performance
                ))
                
                processed_records += 1
                
                # Update progress
                cursor.execute('''
                    UPDATE upload_sessions 
                    SET processed_records = ? 
                    WHERE id = ?
                ''', (processed_records, session_id))
                
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        # Mark as completed
        cursor.execute('''
            UPDATE upload_sessions 
            SET status = 'completed' 
            WHERE id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()        
        return True, f"Successfully processed {processed_records} records"
    
    except Exception as e:
        return False, f"Error processing data: {str(e)}"

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

def dashboard_data():
    """Get dashboard data for authenticated users with file upload info"""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    user_id = session.get('user_id')
    
    # Get general statistics
    cursor.execute('''
        SELECT COUNT(DISTINCT season) as total_seasons,
               COUNT(*) as total_players,
               MAX(season) as latest_season
        FROM players
    ''')
    
    stats = cursor.fetchone()
    dashboard_stats = {
        'total_seasons': stats[0] if stats[0] else 0,
        'total_players': stats[1] if stats[1] else 0,
        'latest_season': stats[2] if stats[2] else 'No data'
    }
    
    # Get user-specific upload statistics
    if user_id:
        cursor.execute('''
            SELECT COUNT(*) as user_uploads,
                   COALESCE(SUM(file_size), 0) as total_storage,
                   MAX(upload_order) as latest_upload_order
            FROM file_uploads
            WHERE user_id = ?
        ''', (user_id,))
        
        user_stats = cursor.fetchone()
        dashboard_stats.update({
            'user_uploads': user_stats[0] if user_stats[0] else 0,
            'user_storage_mb': round((user_stats[1] / (1024 * 1024)) if user_stats[1] else 0, 2),
            'latest_upload_order': user_stats[2] if user_stats[2] else 0
        })
        
        # Get user's recent uploads
        cursor.execute('''
            SELECT original_filename, file_size, status, created_at, upload_order
            FROM file_uploads
            WHERE user_id = ?
            ORDER BY upload_order DESC
            LIMIT 5
        ''', (user_id,))
        
        recent_uploads = []
        for row in cursor.fetchall():
            file_size_mb = (row[1] / (1024 * 1024)) if row[1] else 0
            recent_uploads.append({
                'filename': row[0],
                'file_size_mb': round(file_size_mb, 2),
                'status': row[2],
                'created_at': row[3],
                'upload_order': row[4]
            })
    else:
        # Get general recent uploads for non-authenticated view
        cursor.execute('''
            SELECT filename, total_records, status, created_at
            FROM upload_sessions
            ORDER BY created_at DESC
            LIMIT 5
        ''')
        
        recent_uploads = cursor.fetchall()
        dashboard_stats.update({
            'user_uploads': 0,
            'user_storage_mb': 0,
            'latest_upload_order': 0
        })
    
    # Get available seasons for the template
    cursor.execute('SELECT DISTINCT season FROM players ORDER BY season DESC')
    seasons = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return dashboard_stats, recent_uploads, seasons

@app.route('/login', methods=['GET', 'POST'])
@security_headers
@rate_limit_check(max_attempts=5, window_minutes=15)
def login():
    """Login page with database authentication and security measures"""
    if 'user_id' in session:
        # User already logged in, redirect based on role
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Get and validate input
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Basic validation
        if not username or not password:
            log_security_event('login_attempt', 'Missing credentials')
            flash('Please enter both username and password', 'error')
            return render_template('auth/login.html')
        
        # Validate username format
        is_valid_username, validated_username = SecurityValidator.validate_username(username)
        if not is_valid_username:
            log_security_event('login_attempt', f'Invalid username format: {username}')
            flash('Invalid username format', 'error')
            return render_template('auth/login.html')
        
        # Validate email if username looks like email
        if '@' in username:
            is_valid_email, validated_email = SecurityValidator.validate_email(username)
            if not is_valid_email:
                log_security_event('login_attempt', f'Invalid email format: {username}')
                flash('Invalid email format', 'error')
                return render_template('auth/login.html')
            username = validated_email
        else:
            username = validated_username
        
        try:
            # Use secure database lookup
            user = DatabaseSecurity.safe_user_lookup(username)
            
            if user and user[5] and check_password_hash(user[3], password):  # is_active and password check
                # Create session
                session_id = create_user_session(
                    user[0], 
                    request.environ.get('REMOTE_ADDR'),
                    request.headers.get('User-Agent')
                )
                
                # Set session variables
                session['user_id'] = user[0]
                session['username'] = SecurityValidator.sanitize_user_input(user[1])
                session['user_email'] = SecurityValidator.sanitize_user_input(user[2])
                session['user_role'] = user[4]
                session['session_id'] = session_id
                session['last_activity'] = datetime.now().isoformat()
                session.permanent = True
                
                # Log successful login
                DatabaseSecurity.safe_log_activity(
                    user[0], 
                    'login', 
                    f'Successful login from {request.environ.get("REMOTE_ADDR")}',
                    request.environ.get('REMOTE_ADDR'),
                    request.headers.get('User-Agent')
                )
                
                flash(f'Welcome back, {SecurityValidator.sanitize_user_input(user[1])}!', 'success')
                
                # Redirect based on role
                if user[4] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                # Log failed login attempt
                log_security_event('login_failed', f'Failed login attempt for: {username}')
                flash('Invalid username/email or password', 'error')
                
        except Exception as e:
            log_security_event('login_error', f'Login system error: {str(e)}')
            flash('Login system temporarily unavailable', 'error')
            print(f"Login error: {e}")
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    try:
        # Log activity
        if 'user_id' in session:
            log_user_activity(
                session['user_id'], 
                'logout', 
                f'User logged out from {request.environ.get("REMOTE_ADDR")}',
                request.environ.get('REMOTE_ADDR'),
                request.headers.get('User-Agent')
            )
        
        # End session in database
        if 'session_id' in session:
            end_user_session(session['session_id'])
        
        # Clear session
        session.clear()
        flash('You have been logged out successfully', 'success')
    except Exception as e:
        print(f"Logout error: {e}")
        session.clear()
    
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard - redirects admins to admin panel"""
    # If user is admin, redirect to admin dashboard
    if session.get('user_role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    try:
        dashboard_stats, recent_uploads, seasons = dashboard_data()
        return render_template('index.html', 
                             dashboard_stats=dashboard_stats,
                             recent_uploads=recent_uploads,
                             seasons=seasons)
    except Exception as e:
        flash('Error loading dashboard', 'error')
        print(f"Dashboard error: {e}")
        return render_template('index.html', 
                             dashboard_stats={'total_seasons': 0, 'total_players': 0, 'latest_season': 'No data'},
                             recent_uploads=[],
                             seasons=[])

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with user management and analytics"""
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
        
        # Get recent activity
        cursor.execute('''
            SELECT ua.timestamp, u.username, ua.action_type, ua.action_details, ua.ip_address
            FROM user_activity ua
            JOIN users u ON ua.user_id = u.id
            ORDER BY ua.timestamp DESC
            LIMIT 10
        ''')
        recent_activity = cursor.fetchall()
        
        # Get active sessions
        cursor.execute('''
            SELECT us.login_time, us.last_activity, u.username, us.ip_address
            FROM user_sessions us
            JOIN users u ON us.user_id = u.id
            WHERE us.is_active = 1
            ORDER BY us.last_activity DESC
            LIMIT 10
        ''')
        active_sessions = cursor.fetchall()
        
        # Get all users for management
        cursor.execute('''
            SELECT u.id, u.username, u.email, u.role, u.is_active, u.created_at,
                   creator.username as created_by_name,
                   us.login_time as last_login,
                   us.logout_time as last_logout
            FROM users u
            LEFT JOIN users creator ON u.created_by = creator.id
            LEFT JOIN (
                SELECT user_id, MAX(login_time) as login_time, logout_time
                FROM user_sessions 
                GROUP BY user_id
            ) us ON u.id = us.user_id
            ORDER BY u.created_at DESC
        ''')
        all_users = cursor.fetchall()
        
        conn.close()
        
        # Get NBA data statistics (existing functionality)
        try:
            conn = sqlite3.connect('nba_mvp.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(DISTINCT season) FROM players')
            total_seasons = cursor.fetchone()[0] if cursor.fetchone() else 0
            
            cursor.execute('SELECT COUNT(*) FROM players')
            total_players = cursor.fetchone()[0] if cursor.fetchone() else 0
            
            conn.close()
        except:
            total_seasons = 0
            total_players = 0
        
        dashboard_stats = {
            'total_users': total_users,
            'total_admins': total_admins, 
            'total_regular_users': total_regular_users,
            'total_seasons': total_seasons,
            'total_players': total_players
        }
        
        return render_template('admin/dashboard.html',
                             dashboard_stats=dashboard_stats,
                             recent_activity=recent_activity,
                             active_sessions=active_sessions,
                             all_users=all_users)
        
    except Exception as e:
        flash('Error loading admin dashboard', 'error')
        print(f"Admin dashboard error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/admin/create_user', methods=['POST'])
@admin_required
@security_headers
@sanitize_form_input(['username', 'email', 'password', 'role'])
def create_user():
    """Create a new user (admin only) with security validation"""
    try:
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')
        
        # Validate all required fields
        if not all([username, email, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Validate username
        is_valid_username, validated_username = SecurityValidator.validate_username(username)
        if not is_valid_username:
            flash(validated_username, 'error')  # Error message
            return redirect(url_for('admin_dashboard'))
        
        # Validate email
        is_valid_email, validated_email = SecurityValidator.validate_email(email)
        if not is_valid_email:
            flash(validated_email, 'error')  # Error message
            return redirect(url_for('admin_dashboard'))
        
        # Validate password
        is_valid_password, password_message = SecurityValidator.validate_password(password)
        if not is_valid_password:
            flash(password_message, 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Validate role
        if role not in ['user', 'admin']:
            log_security_event('invalid_role', f'Invalid role attempted: {role}', session['user_id'])
            flash('Invalid role specified', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Check if username or email already exists using secure method
        existing_user_check = DatabaseSecurity.execute_query(
            'SELECT COUNT(*) FROM users WHERE username = ? OR email = ?', 
            (validated_username, validated_email), 
            fetch_one=True
        )
        
        if existing_user_check and existing_user_check[0] > 0:
            flash('Username or email already exists', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Create user with secure method
        password_hash = generate_password_hash(password)
        
        result = DatabaseSecurity.safe_create_user(
            validated_username, 
            validated_email, 
            password_hash, 
            role, 
            session['user_id']
        )
        
        if result is not None:
            # Log activity
            DatabaseSecurity.safe_log_activity(
                session['user_id'],
                'user_created',
                f'Created {role} account for {validated_username} ({validated_email})',
                request.environ.get('REMOTE_ADDR'),
                request.headers.get('User-Agent')
            )
            
            flash(f'{role.title()} account created successfully for {SecurityValidator.sanitize_user_input(validated_username)}', 'success')
        else:
            flash('Error creating user account', 'error')
        
    except Exception as e:
        log_security_event('user_creation_error', f'Error creating user: {str(e)}', session.get('user_id'))
        flash('Error creating user account', 'error')
        print(f"Create user error: {e}")
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_user/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        # Get current user info
        cursor.execute('SELECT username, is_active FROM users WHERE id = ?', (user_id,))
        user_info = cursor.fetchone()
        
        if not user_info:
            flash('User not found', 'error')
            conn.close()
            return redirect(url_for('admin_dashboard'))
        
        # Don't allow deactivating yourself
        if user_id == session['user_id']:
            flash('You cannot deactivate your own account', 'error')
            conn.close()
            return redirect(url_for('admin_dashboard'))
        
        # Toggle status
        new_status = not user_info[1]
        cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
        conn.close()
        
        # Log activity
        action = 'activated' if new_status else 'deactivated'
        log_user_activity(
            session['user_id'],
            f'user_{action}',
            f'{action.title()} user account: {user_info[0]}',
            request.environ.get('REMOTE_ADDR'),
            request.headers.get('User-Agent')
        )
        
        flash(f'User {user_info[0]} has been {action}', 'success')
        
    except Exception as e:
        flash('Error updating user status', 'error')
        print(f"Toggle user status error: {e}")
    
    return redirect(url_for('admin_dashboard'))

@app.route('/upload')
@login_required
def upload_page():
    """Upload CSV page"""
    return render_template('upload.html')

@app.route('/upload_csv', methods=['POST'])
@login_required
@security_headers
def upload_csv():
    """Handle CSV file upload with user-specific file storage"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    # Validate file upload security
    is_valid_file, file_message = SecurityValidator.validate_file_upload(
        file, 
        allowed_extensions=['csv'], 
        max_size_mb=16
    )
    
    if not is_valid_file:
        log_security_event('file_upload_rejected', file_message, session.get('user_id'))
        flash(f'File upload rejected: {file_message}', 'error')
        return redirect(url_for('upload_page'))
    
    # Use the safe filename from validation
    safe_filename = file_message
    original_filename = secure_filename(file.filename)
    user_id = session['user_id']
    upload_id = None
    
    try:
        # Get user-specific directory and upload order
        user_dir = get_user_upload_directory(user_id)
        upload_order = get_next_upload_order(user_id)
        
        # Create standardized stored filename
        stored_filename = create_stored_filename(user_id, upload_order, original_filename)
        file_path = os.path.join(user_dir, stored_filename)
        
        # Save file to user directory
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Validate CSV format
        is_valid, message = validate_csv_format(file_path)
        if not is_valid:
            os.remove(file_path)
            log_security_event('csv_validation_failed', message, user_id)
            flash(f'Invalid CSV format: {message}', 'error')
            return redirect(url_for('upload_page'))
        
        # Create upload session
        session_id = str(uuid.uuid4())
        DatabaseSecurity.execute_query(
            '''INSERT INTO upload_sessions (id, filename, status) VALUES (?, ?, 'pending')''',
            (session_id, stored_filename)
        )
        
        # Save file upload record
        upload_id = save_file_upload_record(
            user_id, session_id, original_filename, stored_filename, 
            file_path, file_size, upload_order
        )
        
        if not upload_id:
            raise Exception("Failed to save file upload record")
        
        # Process data
        success, result_message = process_csv_data(file_path, session_id)
        
        if success:
            # Update file status to processed
            update_file_processing_status(upload_id, 'processed')
            
            # Log successful upload
            DatabaseSecurity.safe_log_activity(
                user_id,
                'csv_upload_success',
                f'Successfully uploaded and processed: {original_filename} (Order: {upload_order})',
                request.environ.get('REMOTE_ADDR'),
                request.headers.get('User-Agent')
            )
            
            # Clean up old uploads (keep latest 10)
            cleanup_old_uploads(user_id, keep_latest=10)
            
            flash(f'Successfully uploaded and processed: {SecurityValidator.sanitize_user_input(original_filename)} (Upload #{upload_order})', 'success')
        else:
            # Update file status to failed
            update_file_processing_status(upload_id, 'failed')
            log_security_event('csv_processing_error', result_message, user_id)
            flash(f'Error processing file: {SecurityValidator.sanitize_user_input(result_message)}', 'error')
        
        return redirect(url_for('data_management'))
    
    except Exception as e:
        # Clean up file if exists
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        # Update upload status if record was created
        if upload_id:
            update_file_processing_status(upload_id, 'error')
        
        log_security_event('upload_system_error', str(e), session.get('user_id'))
        flash('Upload system error. Please try again.', 'error')
        print(f"Upload error: {e}")
        return redirect(url_for('upload_page'))

@app.route('/data_management')
@login_required
@admin_restricted
def data_management():
    """Data management page with file upload tracking"""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    # Get available seasons
    cursor.execute('SELECT DISTINCT season FROM players ORDER BY season DESC')
    seasons = [row[0] for row in cursor.fetchall()]
    
    # Get data summary by season
    cursor.execute('''
        SELECT season, COUNT(*) as player_count, 
               GROUP_CONCAT(DISTINCT team) as teams
        FROM players 
        GROUP BY season 
        ORDER BY season DESC
    ''')
    
    season_data = []
    for row in cursor.fetchall():
        season_data.append({
            'season': row[0],
            'player_count': row[1],
            'teams': row[2].split(',') if row[2] else []
        })
    
    # Get recent file uploads (admin can see all users' uploads)
    cursor.execute('''
        SELECT fu.id, fu.original_filename, fu.upload_order, fu.status, 
               fu.created_at, fu.file_size, u.username
        FROM file_uploads fu
        JOIN users u ON fu.user_id = u.id
        ORDER BY fu.created_at DESC
        LIMIT 20
    ''')
    
    recent_uploads = []
    for row in cursor.fetchall():
        file_size_mb = (row[5] / (1024 * 1024)) if row[5] else 0
        recent_uploads.append({
            'id': row[0],
            'filename': row[1],
            'upload_order': row[2],
            'status': row[3],
            'created_at': row[4],
            'file_size_mb': round(file_size_mb, 2),
            'username': row[6]
        })
    
    # Get upload statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total_uploads,
            COUNT(DISTINCT user_id) as active_users,
            SUM(file_size) as total_storage,
            AVG(file_size) as avg_file_size
        FROM file_uploads
    ''')
    
    stats = cursor.fetchone()
    upload_stats = {
        'total_uploads': stats[0] if stats[0] else 0,
        'active_users': stats[1] if stats[1] else 0,
        'total_storage_mb': round((stats[2] / (1024 * 1024)) if stats[2] else 0, 2),
        'avg_file_size_mb': round((stats[3] / (1024 * 1024)) if stats[3] else 0, 2)
    }
    
    conn.close()
    
    return render_template('data_management.html', 
                         seasons=seasons, 
                         season_data=season_data,
                         recent_uploads=recent_uploads,
                         upload_stats=upload_stats)

@app.route('/calculate_mvp/<int:season>')
@login_required
@admin_restricted
def calculate_mvp(season):
    """Calculate MVP rankings for a specific season"""
    conn = sqlite3.connect('nba_mvp.db')
    
    # Get player data for the season
    query = '''
        SELECT p.id, p.name, p.team, s.games, s.minutes, s.fg_percent,
               s.points, s.rebounds, s.assists, s.steals, s.blocks,
               s.turnovers, s.personal_fouls, s.team_performance
        FROM players p
        JOIN statistics s ON p.id = s.player_id
        WHERE p.season = ?
    '''
    
    df = pd.read_sql_query(query, conn, params=(season,))
    
    if df.empty:
        flash(f'No data found for season {season}', 'error')
        return redirect(url_for('data_management'))
    
    # Calculate MVP scores
    calculator = MVPCalculator()
    results_df = calculator.calculate_mvp_scores(df)
    
    # Save results to database
    cursor = conn.cursor()
    
    # Clear previous calculations for this season
    cursor.execute('DELETE FROM mvp_scores WHERE season = ?', (season,))
    
    # Insert new calculations
    for _, row in results_df.iterrows():
        cursor.execute('''
            INSERT INTO mvp_scores 
            (player_id, season, normalized_score, final_score, rank_position)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            int(row['id']),
            season,
            0.0,  # normalized_score placeholder
            float(row['final_score']),
            int(row['rank_position'])
        ))
    
    conn.commit()
    conn.close()
    
    flash(f'MVP rankings calculated successfully for season {season}', 'success')
    return redirect(url_for('mvp_rankings', season=season))

@app.route('/mvp_rankings/<int:season>')
@login_required
@admin_restricted
def mvp_rankings(season):
    """Display MVP rankings for a season"""
    conn = sqlite3.connect('nba_mvp.db')
    
    query = '''
        SELECT p.name, p.team, s.points, s.rebounds, s.assists,
               s.steals, s.blocks, mvp.final_score, mvp.rank_position
        FROM players p
        JOIN statistics s ON p.id = s.player_id
        JOIN mvp_scores mvp ON p.id = mvp.player_id
        WHERE p.season = ? AND mvp.season = ?
        ORDER BY mvp.rank_position
        LIMIT 10
    '''
    
    cursor = conn.cursor()
    cursor.execute(query, (season, season))
    top_players = cursor.fetchall()
    
    conn.close()
    
    return render_template('mvp_rankings.html', 
                         season=season, 
                         top_players=top_players)

@app.route('/player_comparison')
@login_required
@admin_restricted
def player_comparison():
    """Player comparison page"""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    # Get all players for comparison
    cursor.execute('''
        SELECT p.id, p.name, p.team, p.season
        FROM players p
        ORDER BY p.season DESC, p.name
    ''')
    
    players = cursor.fetchall()
    conn.close()
    
    return render_template('player_comparison.html', players=players)

@app.route('/api/compare_players', methods=['POST'])
@login_required
@admin_restricted
def compare_players():
    """API endpoint to compare selected players"""
    player_ids = request.json.get('player_ids', [])
    
    if len(player_ids) < 2:
        return jsonify({'error': 'Please select at least 2 players'}), 400
    
    conn = sqlite3.connect('nba_mvp.db')
    
    placeholders = ','.join(['?' for _ in player_ids])
    query = f'''
        SELECT p.name, p.team, p.season, s.points, s.rebounds, s.assists,
               s.steals, s.blocks, s.fg_percent, s.games, s.minutes
        FROM players p
        JOIN statistics s ON p.id = s.player_id
        WHERE p.id IN ({placeholders})
    '''
    
    df = pd.read_sql_query(query, conn, params=player_ids)
    conn.close()
    
    # Convert to JSON for frontend
    comparison_data = df.to_dict('records')
    
    return jsonify({'players': comparison_data})

@app.route('/delete_season/<int:season>', methods=['POST'])
@login_required
@admin_restricted
def delete_season(season):
    """Delete all data for a specific season"""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    try:
        # Delete in correct order due to foreign keys
        cursor.execute('DELETE FROM mvp_scores WHERE season = ?', (season,))
        cursor.execute('''
            DELETE FROM statistics 
            WHERE player_id IN (
                SELECT id FROM players WHERE season = ?
            )
        ''', (season,))
        cursor.execute('DELETE FROM players WHERE season = ?', (season,))
        
        conn.commit()
        flash(f'Successfully deleted all data for season {season}', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting season data: {str(e)}', 'error')
    
    finally:
        conn.close()
    
    return redirect(url_for('data_management'))

@app.route('/export_rankings/<int:season>')
@login_required
@admin_restricted
def export_rankings(season):
    """Export MVP rankings to PDF"""
    conn = sqlite3.connect('nba_mvp.db')
    
    query = '''
        SELECT p.name, p.team, s.points, s.rebounds, s.assists,
               mvp.final_score, mvp.rank_position
        FROM players p
        JOIN statistics s ON p.id = s.player_id
        JOIN mvp_scores mvp ON p.id = mvp.player_id
        WHERE p.season = ? AND mvp.season = ?
        ORDER BY mvp.rank_position
    '''
    
    df = pd.read_sql_query(query, conn, params=(season, season))
    conn.close()
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f'NBA MVP Rankings - Season {season}', 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(10, 10, 'Rank', 1)
    pdf.cell(40, 10, 'Player', 1)
    pdf.cell(30, 10, 'Team', 1)
    pdf.cell(20, 10, 'Points', 1)
    pdf.cell(20, 10, 'Rebounds', 1)
    pdf.cell(20, 10, 'Assists', 1)
    pdf.cell(30, 10, 'MVP Score', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 10)
    for _, row in df.iterrows():
        pdf.cell(10, 8, str(int(row['rank_position'])), 1)
        pdf.cell(40, 8, str(row['name'])[:15], 1)
        pdf.cell(30, 8, str(row['team']), 1)
        pdf.cell(20, 8, str(row['points']), 1)
        pdf.cell(20, 8, str(row['rebounds']), 1)
        pdf.cell(20, 8, str(row['assists']), 1)
        pdf.cell(30, 8, f"{row['final_score']:.4f}", 1)
        pdf.ln()
    
    # Save to BytesIO
    pdf_output = BytesIO()
    pdf_content = pdf.output(dest='S').encode('latin-1')
    pdf_output.write(pdf_content)
    pdf_output.seek(0)
    
    return send_file(
        pdf_output,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'NBA_MVP_Rankings_{season}.pdf'
    )

# File management helper functions
def get_user_upload_directory(user_id):
    """Get or create user-specific upload directory"""
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}')
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_next_upload_order(user_id):
    """Get the next upload order number for a user"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COALESCE(MAX(upload_order), 0) + 1 
            FROM file_uploads 
            WHERE user_id = ?
        ''', (user_id,))
        next_order = cursor.fetchone()[0]
        conn.close()
        return next_order
    except Exception as e:
        print(f"Error getting next upload order: {e}")
        return 1

def create_stored_filename(user_id, upload_order, original_filename):
    """Create a standardized filename for storage"""
    file_ext = os.path.splitext(original_filename)[1].lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"upload_{upload_order:04d}_{timestamp}{file_ext}"

def save_file_upload_record(user_id, session_id, original_filename, stored_filename, 
                          file_path, file_size, upload_order):
    """Save file upload record to database"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO file_uploads 
            (user_id, session_id, original_filename, stored_filename, 
             file_path, file_size, upload_order, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'uploaded')
        ''', (user_id, session_id, original_filename, stored_filename, 
              file_path, file_size, upload_order))
        conn.commit()
        upload_id = cursor.lastrowid
        conn.close()
        return upload_id
    except Exception as e:
        print(f"Error saving file upload record: {e}")
        return None

def get_user_uploads(user_id, limit=None):
    """Get user's upload history ordered by upload order"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        query = '''
            SELECT id, original_filename, stored_filename, file_path, 
                   file_size, upload_order, status, created_at, processed_at
            FROM file_uploads 
            WHERE user_id = ? 
            ORDER BY upload_order DESC
        '''
        
        params = [user_id]
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        cursor.execute(query, params)
        uploads = []
        for row in cursor.fetchall():
            uploads.append({
                'id': row[0],
                'original_filename': row[1],
                'stored_filename': row[2],
                'file_path': row[3],
                'file_size': row[4],
                'upload_order': row[5],
                'status': row[6],
                'created_at': row[7],
                'processed_at': row[8]
            })
        
        conn.close()
        return uploads
    except Exception as e:
        print(f"Error getting user uploads: {e}")
        return []

def update_file_processing_status(upload_id, status, processed_at=None):
    """Update file processing status"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        if processed_at is None:
            processed_at = datetime.now()
        
        cursor.execute('''
            UPDATE file_uploads 
            SET status = ?, processed_at = ?
            WHERE id = ?
        ''', (status, processed_at, upload_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating file processing status: {e}")
        return False

def cleanup_old_uploads(user_id, keep_latest=10):
    """Clean up old upload files for a user, keeping only the latest N files"""
    try:
        uploads = get_user_uploads(user_id)
        if len(uploads) <= keep_latest:
            return True
        
        # Get files to delete (oldest ones)
        files_to_delete = uploads[keep_latest:]
        
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        for file_record in files_to_delete:
            # Delete physical file
            if os.path.exists(file_record['file_path']):
                try:
                    os.remove(file_record['file_path'])
                except OSError as e:
                    print(f"Error deleting file {file_record['file_path']}: {e}")
            
            # Delete database record
            cursor.execute('DELETE FROM file_uploads WHERE id = ?', (file_record['id'],))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error cleaning up old uploads: {e}")
        return False

@app.route('/upload_history')
@login_required
def upload_history():
    """View user's upload history"""
    user_id = session['user_id']
    uploads = get_user_uploads(user_id, limit=50)
    
    # Calculate total storage used
    total_size = sum(upload['file_size'] for upload in uploads if upload['file_size'])
    total_size_mb = total_size / (1024 * 1024) if total_size else 0
    
    return render_template('upload_history.html', 
                         uploads=uploads, 
                         total_size_mb=round(total_size_mb, 2))

@app.route('/download_upload/<int:upload_id>')
@login_required
def download_upload(upload_id):
    """Download a user's uploaded file"""
    user_id = session['user_id']
    
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        # Verify file belongs to user
        cursor.execute('''
            SELECT original_filename, file_path, stored_filename
            FROM file_uploads 
            WHERE id = ? AND user_id = ?
        ''', (upload_id, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            flash('File not found or access denied', 'error')
            return redirect(url_for('upload_history'))
        
        original_filename, file_path, stored_filename = result
        
        if not os.path.exists(file_path):
            flash('File no longer exists on server', 'error')
            return redirect(url_for('upload_history'))
        
        # Log download activity
        DatabaseSecurity.safe_log_activity(
            user_id,
            'file_download',
            f'Downloaded file: {original_filename}',
            request.environ.get('REMOTE_ADDR'),
            request.headers.get('User-Agent')
        )
        
        return send_file(file_path, 
                        as_attachment=True, 
                        download_name=original_filename,
                        mimetype='text/csv')
    
    except Exception as e:
        log_security_event('download_error', str(e), user_id)
        flash('Error downloading file', 'error')
        print(f"Download error: {e}")
        return redirect(url_for('upload_history'))

@app.route('/delete_upload/<int:upload_id>', methods=['POST'])
@login_required
def delete_upload(upload_id):
    """Delete a user's uploaded file"""
    user_id = session['user_id']
    
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        # Verify file belongs to user
        cursor.execute('''
            SELECT original_filename, file_path
            FROM file_uploads 
            WHERE id = ? AND user_id = ?
        ''', (upload_id, user_id))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            flash('File not found or access denied', 'error')
            return redirect(url_for('upload_history'))
        
        original_filename, file_path = result
        
        # Delete file record
        cursor.execute('DELETE FROM file_uploads WHERE id = ?', (upload_id,))
        conn.commit()
        conn.close()
        
        # Delete physical file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Error deleting physical file: {e}")
        
        # Log deletion activity
        DatabaseSecurity.safe_log_activity(
            user_id,
            'file_deletion',
            f'Deleted file: {original_filename}',
            request.environ.get('REMOTE_ADDR'),
            request.headers.get('User-Agent')
        )
        
        flash(f'File "{original_filename}" deleted successfully', 'success')
        return redirect(url_for('upload_history'))
    
    except Exception as e:
        log_security_event('deletion_error', str(e), user_id)
        flash('Error deleting file', 'error')
        print(f"Deletion error: {e}")
        return redirect(url_for('upload_history'))

if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)
