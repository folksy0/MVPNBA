"""
NBA MVP System Database Initialization Script
Creates tables for user-specific file storage and upload ordering
"""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

def init_database_with_file_storage():
    """Initialize database with enhanced file storage capabilities"""
    
    # Create database connection
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    print("Initializing NBA MVP Database with File Storage...")
    
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            FOREIGN KEY (uploaded_by) REFERENCES users (id)
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
            uploaded_by INTEGER,
            FOREIGN KEY (player_id) REFERENCES players (id),
            FOREIGN KEY (uploaded_by) REFERENCES users (id)
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
            calculated_by INTEGER,
            FOREIGN KEY (player_id) REFERENCES players (id),
            FOREIGN KEY (calculated_by) REFERENCES users (id)
        )
    ''')
    
    # Upload sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS upload_sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            filename TEXT,
            total_records INTEGER,
            processed_records INTEGER,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # File uploads table - NEW for user-specific file storage
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
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_uploads_user_id ON file_uploads(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_uploads_upload_order ON file_uploads(user_id, upload_order)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_season ON players(season)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id)')
    
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
        print("✓ Default admin user created: admin/admin123")
    else:
        print("✓ Admin user already exists")
    
    # Create demo user if it doesn't exist
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = "demo"')
    demo_count = cursor.fetchone()[0]
    
    if demo_count == 0:
        demo_password_hash = generate_password_hash('demo123')
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', ('demo', 'demo@nbamvp.com', demo_password_hash, 'user'))
        conn.commit()
        print("✓ Demo user created: demo/demo123")
    else:
        print("✓ Demo user already exists")
    
    conn.close()
    
    # Create upload directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('static/charts', exist_ok=True)
    print("✓ Upload directories created")
    
    print("\n✅ Database initialization completed successfully!")
    print("\nAvailable user accounts:")
    print("  Admin: admin / admin123")
    print("  Demo:  demo / demo123")
    print("\nFile Storage Structure:")
    print("  - Each user gets a separate directory: uploads/user_{user_id}/")
    print("  - Files are numbered by upload order: upload_0001_timestamp.csv")
    print("  - Database stores only file paths and metadata, not file content")
    print("  - Automatic cleanup keeps only the latest 10 files per user")

def show_database_info():
    """Show current database information"""
    
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        print("\n📊 Database Information:")
        print("=" * 50)
        
        # Users count
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        print(f"Users: {user_count}")
        
        # File uploads count
        cursor.execute('SELECT COUNT(*) FROM file_uploads')
        file_count = cursor.fetchone()[0]
        print(f"File uploads: {file_count}")
        
        # Total storage used
        cursor.execute('SELECT SUM(file_size) FROM file_uploads')
        total_size = cursor.fetchone()[0] or 0
        total_size_mb = total_size / (1024 * 1024)
        print(f"Total storage: {total_size_mb:.2f} MB")
        
        # Players count
        cursor.execute('SELECT COUNT(*) FROM players')
        player_count = cursor.fetchone()[0]
        print(f"Players in database: {player_count}")
        
        # Available seasons
        cursor.execute('SELECT DISTINCT season FROM players ORDER BY season')
        seasons = [str(row[0]) for row in cursor.fetchall()]
        if seasons:
            print(f"Available seasons: {', '.join(seasons)}")
        else:
            print("Available seasons: None")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Error accessing database: {e}")

if __name__ == "__main__":
    init_database_with_file_storage()
    show_database_info()
