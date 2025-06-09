"""
NBA MVP Decision Support System
Flask Application with Mazar Template Integration
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import os
import sqlite3
from datetime import datetime
import json
import uuid
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import base64

app = Flask(__name__)
app.secret_key = 'nba_mvp_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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
    
    conn.commit()
    conn.close()

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
    """Dashboard page"""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    # Get statistics
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
    
    # Get recent uploads
    cursor.execute('''
        SELECT filename, total_records, status, created_at
        FROM upload_sessions
        ORDER BY created_at DESC
        LIMIT 5
    ''')
    
    recent_uploads = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', 
                         dashboard_stats=dashboard_stats,
                         recent_uploads=recent_uploads)

@app.route('/upload')
def upload_page():
    """Upload CSV page"""
    return render_template('upload.html')

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    """Handle CSV file upload"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Validate CSV format
        is_valid, message = validate_csv_format(file_path)
        if not is_valid:
            os.remove(file_path)
            flash(f'Invalid CSV format: {message}', 'error')
            return redirect(url_for('upload_page'))
        
        # Create upload session
        session_id = str(uuid.uuid4())
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO upload_sessions (id, filename, status) 
            VALUES (?, ?, 'pending')
        ''', (session_id, filename))
        conn.commit()
        conn.close()
        
        # Process data
        success, result_message = process_csv_data(file_path, session_id)
        
        if success:
            flash(f'Successfully uploaded and processed: {result_message}', 'success')
        else:
            flash(f'Error processing file: {result_message}', 'error')
        
        os.remove(file_path)  # Clean up uploaded file
        return redirect(url_for('data_management'))
    
    flash('Please upload a valid CSV file', 'error')
    return redirect(url_for('upload_page'))

@app.route('/data_management')
def data_management():
    """Data management page"""
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
    
    conn.close()
    
    return render_template('data_management.html', 
                         seasons=seasons, 
                         season_data=season_data)

@app.route('/calculate_mvp/<int:season>')
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

if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)
