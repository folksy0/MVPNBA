"""
NBA MVP Decision Support System
Flask Application with Mazar Template Integration
Enhanced with comprehensive security measures
Modified to use COPRAS method for MVP calculation with strict CSV column input
including the 'Team' column.
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

# Weight Criteria for MVP - ADAPTED TO COPRAS EXAMPLE SNIPPET
COPRA_MVP_WEIGHTS = {
    "C1": 0.08,  # Total Games
    "C2": 0.08,  # Minutes Played
    "C3": 0.09,  # FG% (Field Goal Percentage)
    "C4": 0.15,  # PTS (Points)
    "C5": 0.15,  # TRB (Total Rebounds)
    "C6": 0.15,  # AST (Assists)
    "C7": 0.15,  # STL (Steals)
    "C8": 0.15,  # BLK (Blocks)
    "C9": 0.50,  # TEAM (Team Performance Factor)
    "C10": 0.25, # TOV (Turnovers - cost criteria in COPRAS example)
    "C11": 0.25  # PF (Personal Fouls - cost criteria in COPRAS example)
}

# Benefit and Cost criteria - ADAPTED TO COPRAS EXAMPLE SNIPPET
COPRA_BENEFIT_CRITERIA = [f"C{i}" for i in range(1, 10)] # C1 to C9 are benefits
COPRA_COST_CRITERIA = ["C10", "C11"] # C10, C11 are costs

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
    # 'name' column will store the value from CSV 'A' column
    # 'team' will store the value from CSV 'Team' column
    # 'season' will be a default value or user input, not from CSV
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
    # Columns map directly to C1-C11 from CSV conceptually
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            games REAL,            -- Maps to C1
            minutes REAL,          -- Maps to C2
            fg_percent REAL,       -- Maps to C3
            points REAL,           -- Maps to C4
            rebounds REAL,         -- Maps to C5
            assists REAL,          -- Maps to C6
            steals REAL,           -- Maps to C7
            blocks REAL,           -- Maps to C8
            team_performance REAL, -- Maps to C9 (team ranking from preprocessing)
            turnovers REAL,        -- Maps to C10
            personal_fouls REAL,   -- Maps to C11
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
    ''')

    # MVP Scores table
    # 'final_score' will store the calculated Qi value
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mvp_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            season INTEGER,
            normalized_score REAL, -- Placeholder, Qi is in final_score
            final_score REAL,      -- Stores the COPRAS Qi value
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
    """MVP Decision Support System Calculator using COPRAS method"""

    def __init__(self, weights=COPRA_MVP_WEIGHTS, benefit_criteria=COPRA_BENEFIT_CRITERIA, cost_criteria=COPRA_COST_CRITERIA):
        self.weights = weights
        self.benefit_criteria = benefit_criteria
        self.cost_criteria = cost_criteria

    def calculate_mvp_scores(self, df):


        copras_df = df[['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11']].copy()
        for col in copras_df.columns:
            copras_df[col] = pd.to_numeric(copras_df[col], errors='coerce').fillna(0)

        all_criteria = self.benefit_criteria + self.cost_criteria

        normalized_df = copras_df.copy()
        for col_name_c in all_criteria:
            col_total = copras_df[col_name_c].sum()
            normalized_df[f"normalized_{col_name_c}"] = copras_df[col_name_c] / col_total if col_total != 0 else 0

        weighted_df = normalized_df.copy()
        for col_name_c in all_criteria:

            weighted_df[f"weighted_{col_name_c}"] = weighted_df[f"normalized_{col_name_c}"] * self.weights[col_name_c]


        weighted_cols_for_filter = [f"weighted_{c}" for c in all_criteria]

        # Apply the filter directly to the main DataFrame `df` to keep 'A' and 'Team' aligned
        # Also ensure to handle cases where weighted_cols_for_filter might be empty
        if weighted_cols_for_filter:
            # Check for columns that actually exist in weighted_df
            actual_weighted_cols_for_filter = [col for col in weighted_cols_for_filter if col in weighted_df.columns]

            # Create a boolean mask from weighted_df for filtering
            # Use .loc to ensure original index alignment for merging back
            mask = (weighted_df[actual_weighted_cols_for_filter] >= 0.000001).all(axis=1)

            # Apply the mask to the original df and the weighted_df to keep them synchronized
            df = df.loc[mask].copy() # Filter original df
            weighted_df = weighted_df.loc[mask].copy() # Filter weighted df

            # If after filtering, df becomes empty, return an empty DataFrame or handle appropriately
            if df.empty:
                return pd.DataFrame(columns=df.columns.tolist() + ['final_score', 'rank_position'])


        # --- COPRAS Step 3: Calculate Si+ and Si- ---
        # Sum of weighted benefit criteria
        weighted_benefit_cols = [f"weighted_{c}" for c in self.benefit_criteria]
        actual_weighted_benefit_cols = [col for col in weighted_benefit_cols if col in weighted_df.columns]
        weighted_df["Si+"] = weighted_df[actual_weighted_benefit_cols].sum(axis=1)

        # Sum of weighted cost criteria
        weighted_cost_cols = [f"weighted_{c}" for c in self.cost_criteria]
        actual_weighted_cost_cols = [col for col in weighted_cost_cols if col in weighted_df.columns]
        weighted_df["Si-"] = weighted_df[actual_weighted_cost_cols].sum(axis=1)

        # Rounding Si+ and Si- as in the example snippet
        weighted_df["Si+"] = weighted_df["Si+"].round(5)
        weighted_df["Si-"] = weighted_df["Si-"].round(5)

        # --- COPRAS Step 4: Calculate Qi ---
        s_min = weighted_df["Si-"].min() # Minimum Si- across all alternatives

        # Avoid division by zero by replacing 0 in Si- with a very small number (epsilon)
        weighted_df["Si-"] = weighted_df["Si-"].replace(0, np.finfo(float).eps)

        weighted_df["Qi"] = weighted_df["Si+"] + ((s_min * weighted_df["Si+"]) / weighted_df["Si-"])

        # --- COPRAS Step 5: Rank Players ---
        # Merge Qi back to the original DataFrame and rank
        # Use .set_index(df.index) to ensure proper alignment after filtering
        results_df = df.copy()
        results_df['final_score'] = weighted_df['Qi'].values # Assign Qi values directly by array to filtered df

        # Rank in descending order of Qi (higher Qi is better)
        results_df = results_df.sort_values('final_score', ascending=False)
        # 'method="min"' ensures tied ranks get the same minimum rank number
        results_df['rank_position'] = results_df['final_score'].rank(ascending=False, method="min").astype(int)

        # Reset index and drop the old index as in run_copras_model if that's desired for final output consistency
        results_df = results_df.reset_index(drop=True)

        return results_df


def validate_csv_format(file_path):
    """
    Validate CSV format to strictly require columns 'A', 'Team', 'C1' through 'C11'
    and nothing else.
    """
    try:
        df = None
        # Attempt to read CSV with various common encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-8-sig']

        for encoding in encodings:
            try:
                # Try comma separator
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=',',
                    quoting=1,  # Quote all fields
                    skipinitialspace=True,
                    skip_blank_lines=True,
                    on_bad_lines='skip',  # Skip lines that cause parsing errors
                    engine='python'  # Robust parsing engine
                )
                break # Break if successful
            except (UnicodeDecodeError, pd.errors.ParserError):
                try:
                    # Try semicolon separator if comma fails
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
                    break # Break if successful
                except:
                    continue # Continue to next encoding if both separators fail

        if df is None or df.empty:
            return False, "Unable to read CSV file with any supported encoding or format, or file is empty."

        # Clean column names (remove leading/trailing spaces)
        df.columns = df.columns.str.strip()

        # Define the strictly required columns in the exact order for validation
        required_columns = ['A', 'Team', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11']

        # Check if all required columns are present
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}. Your CSV must contain all of: {', '.join(required_columns)}."

        # Check for any extra columns not in the required list
        extra_columns = [col for col in df.columns if col not in required_columns]
        if extra_columns:
            return False, f"Extra unsupported columns found: {', '.join(extra_columns)}. Your CSV must contain *only* the columns: {', '.join(required_columns)}."

        # Validate numeric columns ('C1' through 'C11')
        numeric_cols_to_validate = [f'C{i}' for i in range(1, 12)]
        for col in numeric_cols_to_validate:
            # Convert to numeric, coercing any non-numeric values to NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')

            # Check if the column is entirely non-numeric after coercion (all NaNs)
            # and is not an empty series (which would also be all NaNs)
            if df[col].isnull().all() and not df[col].empty:
                return False, f"Column '{col}' contains no valid numeric data or is entirely empty after conversion. All values are NaN."

        # Check for minimum number of rows with valid data (excluding header)
        if len(df) < 1:
            return False, "CSV file is empty or contains no valid data rows after processing."

        return True, f"CSV format is valid. Found {len(df)} records with expected columns."

    except Exception as e:
        # Catch any unexpected errors during file reading or validation
        return False, f"An unexpected error occurred during CSV validation: {str(e)}"


def process_csv_data(file_path, session_id):
    """
    Process CSV data with strict column requirements ('A', 'Team', 'C1'-'C11')
    and store in the database.
    'A' column maps to player name, 'Team' to team name, 'C1' to 'C11' map to specific statistics.
    """
    try:
        df = None
        # Attempt to read CSV with various common encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-8-sig']

        for encoding in encodings:
            try:
                # Try comma separator
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
                    # Try semicolon separator
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
            raise Exception("Unable to read CSV file, or file is empty.")

        # Clean column names (remove leading/trailing spaces)
        df.columns = df.columns.str.strip()

        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()

        total_records = len(df)
        processed_records = 0

        # Update upload session status to 'processing' and set total records
        cursor.execute('''
            UPDATE upload_sessions
            SET total_records = ?, status = 'processing'
            WHERE id = ?
        ''', (total_records, session_id))

        # Define strict mapping from CSV 'C' columns to database column names
        csv_to_db_col_map = {
            'C1': 'games',
            'C2': 'minutes',
            'C3': 'fg_percent',
            'C4': 'points',
            'C5': 'rebounds',
            'C6': 'assists',
            'C7': 'steals',
            'C8': 'blocks',
            'C9': 'team_performance', # C9 is now the 'ranking' from your preprocessing
            'C10': 'turnovers',
            'C11': 'personal_fouls'
        }

        # Default values for attributes not present in the strict CSV format
        season = 2024 # Default season (can be user-defined in a form)

        for index, row in df.iterrows():
            try:
                player_name = str(row['A']).strip() # Get player name from 'A' column
                team_name = str(row['Team']).strip() # Get team name from 'Team' column

                if not player_name: # Basic check for empty player name
                    print(f"Skipping row {index+1}: Player name (column 'A') is empty.")
                    continue
                if not team_name: # Basic check for empty team name
                    print(f"Skipping row {index+1}: Team name (column 'Team') is empty for player {player_name}.")
                    team_name = "Unknown Team" # Fallback if team is empty

                # Insert player into 'players' table
                cursor.execute('''
                    INSERT INTO players (name, team, season)
                    VALUES (?, ?, ?)
                ''', (player_name, team_name, int(season)))

                player_id = cursor.lastrowid # Get the ID of the newly inserted player

                # Helper for safe numeric conversion: converts value from CSV to float,
                # returns default_val if it's NaN or conversion fails.
                def safe_numeric_from_csv(value, default_val=0.0):
                    try:
                        return float(value) if pd.notna(value) else default_val
                    except (ValueError, TypeError):
                        return default_val

                # Prepare statistics values from CSV 'C' columns for insertion
                stats_for_db = {
                    db_col: safe_numeric_from_csv(row[csv_col])
                    for csv_col, db_col in csv_to_db_col_map.items()
                }

                # Insert statistics into 'statistics' table
                cursor.execute('''
                    INSERT INTO statistics
                    (player_id, games, minutes, fg_percent, points, rebounds,
                     assists, steals, blocks, turnovers, personal_fouls, team_performance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    player_id,
                    stats_for_db['games'],
                    stats_for_db['minutes'],
                    stats_for_db['fg_percent'],
                    stats_for_db['points'],
                    stats_for_db['rebounds'],
                    stats_for_db['assists'],
                    stats_for_db['steals'],
                    stats_for_db['blocks'],
                    stats_for_db['turnovers'],
                    stats_for_db['personal_fouls'],
                    stats_for_db['team_performance'] # C9 from CSV
                ))

                processed_records += 1

                # Update progress in upload session (can be done less frequently for performance)
                cursor.execute('''
                    UPDATE upload_sessions
                    SET processed_records = ?
                    WHERE id = ?
                ''', (processed_records, session_id))

            except Exception as e:
                # Log specific row processing errors
                player_identifier = row['A'] if 'A' in row else f"row {index+1}"
                print(f"Error processing data for player/row {player_identifier}: {e}")
                # Consider adding more detailed error logging or storing problematic rows
                continue # Continue to the next row even if one fails

        # Mark upload session as 'completed'
        cursor.execute('''
            UPDATE upload_sessions
            SET status = 'completed'
            WHERE id = ?
        ''', (session_id,))

        conn.commit()
        conn.close()

        return True, f"Successfully processed {processed_records} records."

    except Exception as e:
        # Catch any high-level errors during data processing
        if 'conn' in locals() and conn: # Ensure connection exists before trying to rollback
            conn.rollback() # Rollback any partial changes
            conn.close()
        return False, f"An error occurred during data processing: {str(e)}"

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
    """
    Calculates MVP rankings for a specific season using the COPRAS method
    and stores the results in the database.
    """
    conn = sqlite3.connect('nba_mvp.db')

    # Fetch player data and map DB column names to 'C' criteria for MVPCalculator.
    # 'p.name AS A' maps player name to 'A' as expected by the calculator.
    # 's.games AS C1' etc., map statistics to C1-C11.
    query = f'''
        SELECT p.id, p.name AS A, p.team,
               s.games AS C1, s.minutes AS C2, s.fg_percent AS C3,
               s.points AS C4, s.rebounds AS C5, s.assists AS C6,
               s.steals AS C7, s.blocks AS C8, s.team_performance AS C9,
               s.turnovers AS C10, s.personal_fouls AS C11
        FROM players p
        JOIN statistics s ON p.id = s.player_id
        WHERE p.season = ?
    '''

    df = pd.read_sql_query(query, conn, params=(season,))

    if df.empty:
        flash(f'No data found for season {season} to calculate MVP rankings.', 'error')
        conn.close()
        return redirect(url_for('data_management'))

    # Instantiate MVPCalculator and perform the COPRAS calculation
    calculator = MVPCalculator()
    results_df = calculator.calculate_mvp_scores(df)

    # Save calculated results to the 'mvp_scores' table
    cursor = conn.cursor()

    try:
        # Clear any previous MVP calculations for this season to ensure fresh data
        cursor.execute('DELETE FROM mvp_scores WHERE season = ?', (season,))

        # Insert new calculations for each player
        for _, row in results_df.iterrows():
            cursor.execute('''
                INSERT INTO mvp_scores
                (player_id, season, normalized_score, final_score, rank_position)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                int(row['id']),        # Player ID from the original data
                season,                # Season being calculated
                0.0,                   # 'normalized_score' is a placeholder, as Qi is in final_score
                float(row['final_score']), # The COPRAS Qi value
                int(row['rank_position']) # The calculated rank
            ))

        conn.commit()
        flash(f'MVP rankings calculated successfully for season {season} using COPRAS method!', 'success')

    except sqlite3.Error as e:
        conn.rollback() # Rollback on error
        flash(f'Database error during MVP calculation: {e}', 'error')
    finally:
        conn.close() # Always close the connection

    return redirect(url_for('mvp_rankings', season=season))

@app.route('/mvp_rankings/<int:season>')
@login_required
@admin_restricted
def mvp_rankings(season):
    """Displays the top 10 MVP rankings for a given season."""
    conn = sqlite3.connect('nba_mvp.db')

    # Fetch player details along with their COPRAS final score (Qi) and rank position
    query = '''
        SELECT p.name, p.team, s.points, s.rebounds, s.assists,
               s.steals, s.blocks, mvp.final_score, mvp.rank_position
        FROM players p
        JOIN statistics s ON p.id = s.player_id
        JOIN mvp_scores mvp ON p.id = mvp.player_id
        WHERE p.season = ? AND mvp.season = ?
        ORDER BY mvp.rank_position ASC -- Order by rank, ascending
        LIMIT 10 -- Display top 10 players
    '''

    cursor = conn.cursor()
    cursor.execute(query, (season, season))
    top_players = cursor.fetchall() # Get all results

    conn.close()

    if not top_players:
        flash(f"No MVP rankings found for season {season}. Please ensure data is uploaded and calculations are run.", 'info')

    return render_template('mvp_rankings.html',
                         season=season,
                         top_players=top_players)

@app.route('/player_comparison')
@login_required
@admin_restricted
def player_comparison():
    """Renders the player comparison page."""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()

    # Fetch all players available for comparison
    cursor.execute('''
        SELECT p.id, p.name, p.team, p.season
        FROM players p
        ORDER BY p.season DESC, p.name ASC
    ''')

    players = cursor.fetchall()
    conn.close()

    return render_template('player_comparison.html', players=players)

@app.route('/api/compare_players', methods=['POST'])
@login_required
@admin_restricted
def compare_players():
    """API endpoint to fetch data for selected players for comparison chart/table."""
    player_ids = request.json.get('player_ids', [])

    if len(player_ids) < 2:
        return jsonify({'error': 'Please select at least 2 players for comparison.'}), 400

    conn = sqlite3.connect('nba_mvp.db')

    # Create placeholders for the IN clause in SQL query
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

    # Convert DataFrame to a list of dictionaries for JSON response
    comparison_data = df.to_dict('records')

    return jsonify({'players': comparison_data})

@app.route('/delete_season/<int:season>', methods=['POST'])
@login_required
@admin_restricted
def delete_season(season):
    """Deletes all player, statistics, and MVP score data for a specific season."""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()

    try:
        # Delete data in the correct order to respect foreign key constraints:
        # 1. Delete MVP scores
        # 2. Delete statistics
        # 3. Delete players
        cursor.execute('DELETE FROM mvp_scores WHERE season = ?', (season,))
        cursor.execute('''
            DELETE FROM statistics
            WHERE player_id IN (
                SELECT id FROM players WHERE season = ?
            )
        ''', (season,))
        cursor.execute('DELETE FROM players WHERE season = ?', (season,))

        conn.commit() # Commit the changes to the database
        flash(f'Successfully deleted all data for season {season}.', 'success')

    except sqlite3.Error as e:
        conn.rollback() # Rollback changes if any error occurs
        flash(f'Error deleting season data: {str(e)}', 'error')

    finally:
        conn.close() # Ensure connection is closed

    return redirect(url_for('data_management'))

@app.route('/export_rankings/<int:season>')
@login_required
@admin_restricted
def export_rankings(season):
    """Exports the MVP rankings for a specified season to a PDF file."""
    conn = sqlite3.connect('nba_mvp.db')

    # Fetch data required for the PDF report
    query = '''
        SELECT p.name, p.team, s.points, s.rebounds, s.assists,
               mvp.final_score, mvp.rank_position
        FROM players p
        JOIN statistics s ON p.id = s.player_id
        JOIN mvp_scores mvp ON p.id = mvp.player_id
        WHERE p.season = ? AND mvp.season = ?
        ORDER BY mvp.rank_position ASC
    '''

    df = pd.read_sql_query(query, conn, params=(season, season))
    conn.close()

    # Initialize FPDF object and add a page
    pdf = FPDF()
    pdf.add_page()

    # Set title and font for the PDF
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f'NBA MVP Rankings - Season {season} (COPRAS Method)', 0, 1, 'C')
    pdf.ln(10) # Add a line break

    # Set font for table headers and add headers
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(10, 10, 'Rank', 1)
    pdf.cell(40, 10, 'Player', 1)
    pdf.cell(30, 10, 'Team', 1)
    pdf.cell(20, 10, 'Points', 1)
    pdf.cell(20, 10, 'Rebounds', 1)
    pdf.cell(20, 10, 'Assists', 1)
    pdf.cell(30, 10, 'MVP Score (Qi)', 1) # Label for COPRAS Qi score
    pdf.ln() # Move to the next line after headers

    # Set font for table data and populate with player rankings
    pdf.set_font('Arial', '', 10)
    for _, row in df.iterrows():
        pdf.cell(10, 8, str(int(row['rank_position'])), 1)
        pdf.cell(40, 8, str(row['name'])[:15], 1) # Truncate player name if too long
        pdf.cell(30, 8, str(row['team']), 1)
        pdf.cell(20, 8, f"{row['points']:.1f}", 1) # Format points
        pdf.cell(20, 8, f"{row['rebounds']:.1f}", 1) # Format rebounds
        pdf.cell(20, 8, f"{row['assists']:.1f}", 1) # Format assists
        pdf.cell(30, 8, f"{row['final_score']:.4f}", 1) # Format Qi score
        pdf.ln() # Move to the next line for the next row

    # Save the PDF to an in-memory BytesIO object
    pdf_output = BytesIO()
    # Output PDF as a string and encode it to latin-1 (common for PDF)
    pdf_content = pdf.output(dest='S').encode('latin-1')
    pdf_output.write(pdf_content)
    pdf_output.seek(0) # Rewind to the beginning of the BytesIO object

    # Send the PDF file as an attachment
    return send_file(
        pdf_output,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'NBA_MVP_Rankings_{season}_COPRAS.pdf' # Suggested filename
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