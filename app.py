"""
NBA MVP Decision Support System
Flask Application with Mazar Template Integration
Modified to use COPRAS method for MVP calculation with strict CSV column input
including the 'Team' column.
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
    
    conn.commit()
    conn.close()

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
    """Dashboard page: Displays overall statistics and recent uploads."""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    # Get overall statistics about the stored data
    cursor.execute('''
        SELECT COUNT(DISTINCT season) as total_seasons,
               COUNT(DISTINCT p.id) as total_players, -- Count distinct player IDs
               MAX(season) as latest_season
        FROM players p
    ''')
    
    stats = cursor.fetchone()
    dashboard_stats = {
        'total_seasons': stats[0] if stats[0] else 0,
        'total_players': stats[1] if stats[1] else 0,
        'latest_season': stats[2] if stats[2] else 'No data'
    }
    
    # Get recent upload session details
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
    """Renders the CSV file upload page."""
    return render_template('upload.html')

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    """Handles the POST request for CSV file upload."""
    if 'file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('upload_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected for upload.', 'error')
        return redirect(url_for('upload_page'))
    
    # Check if the file has a .csv extension
    if file and file.filename.lower().endswith('.csv'):
        filename = secure_filename(file.filename) # Sanitize filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path) # Save the uploaded file temporarily
        
        # Validate the format of the uploaded CSV file
        is_valid, message = validate_csv_format(file_path)
        if not is_valid:
            os.remove(file_path) # Remove invalid file
            flash(f'Invalid CSV format: {message}', 'error')
            return redirect(url_for('upload_page'))
        
        # Create a unique session ID for tracking the upload process
        session_id = str(uuid.uuid4())
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        try:
            # Record the new upload session as 'pending'
            cursor.execute('''
                INSERT INTO upload_sessions (id, filename, status) 
                VALUES (?, ?, 'pending')
            ''', (session_id, filename))
            conn.commit()
        except sqlite3.Error as e:
            flash(f"Database error creating upload session: {e}", 'error')
            conn.rollback()
            os.remove(file_path)
            return redirect(url_for('upload_page'))
        finally:
            conn.close()
        
        # Process the data in the uploaded CSV file
        success, result_message = process_csv_data(file_path, session_id)
        
        if success:
            flash(f'Successfully uploaded and processed: {result_message}', 'success')
        else:
            flash(f'Error processing file: {result_message}', 'error')
        
        os.remove(file_path)  # Clean up the temporary uploaded file
        return redirect(url_for('data_management'))
    
    flash('Please upload a valid CSV file (.csv extension required).', 'error')
    return redirect(url_for('upload_page'))

@app.route('/data_management')
def data_management():
    """Data management page: Displays available seasons and player counts."""
    conn = sqlite3.connect('nba_mvp.db')
    cursor = conn.cursor()
    
    # Get distinct seasons from players table
    cursor.execute('SELECT DISTINCT season FROM players ORDER BY season DESC')
    seasons = [row[0] for row in cursor.fetchall()]
    
    # Get data summary grouped by season (player count and teams)
    cursor.execute('''
        SELECT season, COUNT(DISTINCT p.id) as player_count, 
               GROUP_CONCAT(DISTINCT team) as teams -- Concatenate unique team names
        FROM players p
        GROUP BY season 
        ORDER BY season DESC
    ''')
    
    season_data = []
    for row in cursor.fetchall():
        season_data.append({
            'season': row[0],
            'player_count': row[1],
            'teams': row[2].split(',') if row[2] else [] # Split concatenated teams into a list
        })
    
    conn.close()
    
    return render_template('data_management.html', 
                         seasons=seasons, 
                         season_data=season_data)

@app.route('/calculate_mvp/<int:season>')
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

if __name__ == '__main__':
    init_database() # Initialize database tables on app start
    app.run(debug=True, host='0.0.0.0', port=5000) # Run Flask application in debug mode