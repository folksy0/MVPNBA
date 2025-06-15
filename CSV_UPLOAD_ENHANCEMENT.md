# NBA MVP System - CSV Upload Enhancement

## Recent Improvements

### Enhanced CSV Parsing (December 2024)

The CSV upload functionality has been significantly improved to handle various file formats and potential parsing issues:

#### 1. Robust Encoding Support
- **Multiple Encodings**: Now supports utf-8, latin-1, cp1252, iso-8859-1, utf-8-sig
- **Automatic Detection**: System tries different encodings automatically
- **Unicode Support**: Handles special characters in player names (e.g., Nikola Jokić)

#### 2. Flexible Column Mapping
The system now accepts various column naming conventions:

| Data Field | Accepted Column Names |
|------------|----------------------|
| Player Name | Player, Player Name, Name |
| Team | Team, Team Name |
| Games | G, Games, GP, Games Played |
| Minutes | MP, Minutes, MIN, Minutes Played |
| Field Goal % | FG%, FG Percent, Field Goal %, Field Goal Percentage |
| Points | PTS, Points, PPG, Points Per Game |
| Rebounds | TRB, Rebounds, REB, RPG, Rebounds Per Game |
| Assists | AST, Assists, APG, Assists Per Game |
| Steals | STL, Steals, SPG, Steals Per Game |
| Blocks | BLK, Blocks, BPG, Blocks Per Game |
| Turnovers | TOV, Turnovers, TO, Turnovers Per Game |
| Personal Fouls | PF, Personal Fouls, Fouls, PF Per Game |

#### 3. Enhanced Error Handling
- **Malformed Lines**: Automatically skips problematic lines instead of failing
- **Multiple Separators**: Supports both comma (,) and semicolon (;) separators
- **Safe Data Conversion**: Graceful handling of missing or invalid numeric data
- **Better Error Messages**: More informative error messages for troubleshooting

#### 4. Improved File Processing
- **Robust Parser**: Uses Python's more flexible CSV parser engine
- **Quote Handling**: Better handling of quoted fields and special characters
- **Whitespace Cleanup**: Automatically trims whitespace from column names and data
- **Empty Line Handling**: Skips blank lines automatically

### How to Use

1. **Prepare Your CSV File**:
   - Ensure first row contains column headers
   - Use any of the supported column naming conventions
   - Save in UTF-8 encoding when possible
   - Include at least player names and basic statistics

2. **Upload Process**:
   - Navigate to the Upload page
   - Drag and drop your CSV file or click to browse
   - System will validate format automatically
   - If validation passes, data will be processed and stored

3. **Troubleshooting**:
   - If upload fails, check the error message for specific issues
   - Ensure your CSV has the required data columns
   - Try saving your file in different encoding (UTF-8 recommended)
   - Remove any completely empty rows or columns

### Technical Implementation

The enhanced CSV parsing uses a multi-step approach:

```python
# 1. Try multiple encodings
encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-8-sig']

# 2. Use robust parsing parameters
df = pd.read_csv(
    file_path, 
    encoding=encoding,
    sep=',',
    quoting=1,                # Handle quoted fields
    skipinitialspace=True,    # Remove leading whitespace
    skip_blank_lines=True,    # Skip empty lines
    on_bad_lines='skip',      # Skip malformed lines
    engine='python'           # Use flexible parser
)

# 3. Flexible column mapping
column_mappings = {
    'player': ['Player', 'Player Name', 'Name'],
    'team': ['Team', 'Team Name'],
    # ... etc
}
```

### Benefits

- ✅ **Higher Success Rate**: More CSV files will upload successfully
- ✅ **Better User Experience**: Clear error messages and validation feedback
- ✅ **Flexible Format Support**: Works with various NBA data export formats
- ✅ **Robust Error Recovery**: Continues processing even with some data issues
- ✅ **Unicode Support**: Handles international player names correctly

This enhancement resolves the "Error tokenizing data" issues that can occur with various CSV file formats and encoding problems.
