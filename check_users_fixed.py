import sqlite3
import hashlib

def check_database():
    try:
        # Connect to database
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        print("NBA MVP Database User Checker")
        print("="*50)
        
        # Check users table structure
        cursor.execute("PRAGMA table_info(users);")
        columns = cursor.fetchall()
        print("Users table structure:")
        for col in columns:
            print(f"- Column: {col[1]} | Type: {col[2]} | Not Null: {col[3]} | Default: {col[4]} | Primary Key: {col[5]}")
        
        print("\n" + "="*50)
        
        # Get all users with proper column names
        cursor.execute("SELECT * FROM users;")
        users = cursor.fetchall()
        print(f"Total users: {len(users)}")
        
        if users:
            print("\nUser data:")
            # Get column names
            column_names = [description[0] for description in cursor.description]
            print(f"Columns: {column_names}")
            
            for i, user in enumerate(users, 1):
                print(f"\nUser {i}:")
                for j, value in enumerate(user):
                    if j < len(column_names):
                        col_name = column_names[j]
                        if 'password' in col_name.lower() or 'hash' in col_name.lower():
                            # Show only first 30 characters of password hash
                            display_value = str(value)[:30] + "..." if len(str(value)) > 30 else str(value)
                            print(f"  {col_name}: {display_value}")
                        else:
                            print(f"  {col_name}: {value}")
        
        # Check what authentication method might be used
        print("\n" + "="*50)
        print("Authentication Analysis:")
        
        # Look for common password-related columns
        password_columns = []
        for col in columns:
            col_name = col[1].lower()
            if any(keyword in col_name for keyword in ['password', 'hash', 'pwd', 'pass']):
                password_columns.append(col[1])
        
        if password_columns:
            print(f"Found password-related columns: {password_columns}")
        else:
            print("No obvious password columns found")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

def show_login_methods():
    """Show possible ways to login based on the app.py file"""
    print("\n" + "="*50)
    print("How to find login credentials:")
    print("1. Check app.py file for hardcoded credentials")
    print("2. Look for default admin user creation")
    print("3. Check if there's a registration endpoint")
    print("4. Look for environment variables")
    print("5. Check documentation files")

if __name__ == "__main__":
    check_database()
    show_login_methods()
