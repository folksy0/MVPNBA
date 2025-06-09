# NBA MVP Decision Support System

A comprehensive web application for analyzing NBA player performance and determining MVP candidates using a weighted scoring algorithm with the Mazar template integration.

## 🏀 Features

### Core Functionality
- **CSV Data Upload**: Drag-and-drop interface for uploading NBA player statistics
- **Weighted MVP Scoring**: Advanced algorithm using multiple criteria with configurable weights
- **Player Comparison**: Side-by-side analysis of player performance metrics
- **Data Management**: Season-based data organization and management
- **Rankings Visualization**: Top 10 MVP candidates with interactive charts
- **PDF Export**: Generate comprehensive MVP ranking reports

### Technical Features
- **Flask Backend**: Robust Python web framework
- **SQLite Database**: Efficient data storage and retrieval
- **Responsive UI**: Modern web interface using Mazar template
- **Data Validation**: CSV format validation and error handling
- **Chart Integration**: Interactive visualizations using Chart.js
- **Bootstrap Integration**: Responsive design components

## 📊 MVP Scoring Criteria

The system uses a weighted multi-criteria algorithm with the following weights:

| Criteria | Weight | Type | Description |
|----------|--------|------|-------------|
| Games Played (G) | 8% | Benefit | Total games in season |
| Minutes Played (MP) | 8% | Benefit | Average minutes per game |
| Field Goal % (FG%) | 9% | Benefit | Shooting efficiency |
| Points (PTS) | 15% | Benefit | Scoring average |
| Rebounds (TRB) | 15% | Benefit | Total rebounds average |
| Assists (AST) | 15% | Benefit | Assists average |
| Steals (STL) | 15% | Benefit | Steals average |
| Blocks (BLK) | 10% | Benefit | Blocks average |
| Team Performance | 50% | Benefit | Team success factor |
| Turnovers (TOV) | 25% | Cost | Turnovers (lower is better) |
| Personal Fouls (PF) | 10% | Cost | Fouls (lower is better) |

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation Steps

1. **Clone or Download the Project**
   ```bash
   # Navigate to the project directory
   cd nba-mvp-system
   ```

2. **Install Required Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Application**
   ```bash
   # Option 1: Use the launcher script (recommended)
   python start_nba_mvp.py

   # Option 2: Run directly
   python app.py
   ```

4. **Access the Application**
   - Open your web browser
   - Navigate to: `http://127.0.0.1:5000`

## 📁 Project Structure

```
nba-mvp-system/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── start_nba_mvp.py      # Application launcher
├── sample_nba_data.csv   # Sample data for testing
├── templates/            # HTML templates
│   ├── base.html         # Base template with Mazar styling
│   ├── index.html        # Dashboard
│   ├── upload.html       # CSV upload interface
│   ├── data_management.html # Data management
│   ├── mvp_rankings.html # Rankings display
│   └── player_comparison.html # Player comparison
├── static/              # Static assets
│   ├── assets/          # Mazar template assets
│   └── charts/          # Generated charts
└── uploads/             # Uploaded CSV files
```

## 📊 CSV Data Format

The system expects CSV files with the following columns:

```csv
Player,Team,G,MP,FG%,PTS,TRB,AST,STL,BLK,TOV,PF
Nikola Jokic,Denver Nuggets,69,33.7,63.2,24.5,11.8,9.8,1.3,0.7,3.8,2.9
```

### Required Columns:
- **Player**: Player name
- **Team**: Team name
- **G**: Games played
- **MP**: Minutes played (average)
- **FG%**: Field goal percentage
- **PTS**: Points per game
- **TRB**: Total rebounds per game
- **AST**: Assists per game
- **STL**: Steals per game
- **BLK**: Blocks per game
- **TOV**: Turnovers per game
- **PF**: Personal fouls per game

## 🎯 Usage Guide

### 1. Upload Data
1. Navigate to the "Upload Data" section
2. Drag and drop your CSV file or click to select
3. Validate the data format
4. Submit for processing

### 2. View Rankings
1. Go to "MVP Rankings"
2. Select the season
3. View top 10 MVP candidates
4. Export rankings as PDF

### 3. Compare Players
1. Access "Player Comparison"
2. Select two players to compare
3. View side-by-side statistics
4. Analyze performance differences

### 4. Manage Data
1. Use "Data Management" to organize seasons
2. Delete old data when needed
3. View upload history

## 🔧 Configuration

### MVP Weight Customization
Edit the `MVP_WEIGHTS` dictionary in `app.py`:

```python
MVP_WEIGHTS = {
    "C1": 0.08,  # Games
    "C2": 0.08,  # Minutes
    "C3": 0.09,  # FG%
    "C4": 0.15,  # Points
    # ... other weights
}
```

### Database Configuration
The system uses SQLite by default. The database file `nba_mvp.db` is created automatically.

## 🛠️ Technical Details

### Algorithm Implementation
- **Min-Max Normalization**: Scales all criteria to 0-1 range
- **Weighted Sum Model**: Combines normalized scores using criteria weights
- **Benefit/Cost Criteria**: Handles both positive and negative criteria appropriately

### Security Features
- File upload validation
- SQL injection prevention
- Secure filename handling
- Maximum file size limits

## 🧪 Testing

Use the included sample data file `sample_nba_data.csv` to test the system:

1. Start the application
2. Upload `sample_nba_data.csv`
3. View generated rankings
4. Test player comparisons

## 📝 Dependencies

- **Flask 2.3.3**: Web framework
- **Pandas 2.1.1**: Data manipulation
- **NumPy 1.24.3**: Numerical computing
- **Matplotlib 3.7.2**: Data visualization
- **Seaborn 0.12.2**: Statistical visualization
- **FPDF2 2.7.6**: PDF generation
- **Werkzeug 2.3.7**: WSGI utilities
- **Jinja2 3.1.2**: Template engine

## 🎨 Template Credits

This project uses the **Mazar** admin template for its user interface, providing a modern and responsive design.

## 📄 License

This project is created for educational and research purposes.

## 🤝 Contributing

Feel free to contribute to this project by:
1. Reporting bugs
2. Suggesting new features
3. Improving documentation
4. Submitting pull requests

## 📞 Support

For support or questions:
1. Check the documentation above
2. Review the sample data format
3. Ensure all dependencies are installed correctly

---

**Happy MVP Analysis! 🏀🏆**
