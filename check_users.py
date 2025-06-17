import sqlite3
import hashlib

def check_database():
    try:
        # Connect to database
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        # Check all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables in database:")
        for table in tables:
            print(f"- {table[0]}")
        
        print("\n" + "="*50)
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        users_table = cursor.fetchone()
        
        if users_table:
            print("Users table found!")
            
            # Get table structure
            cursor.execute("PRAGMA table_info(users);")
            columns = cursor.fetchall()
            print("\nUsers table structure:")
            for col in columns:
                print(f"- {col[1]} ({col[2]})")
            
            # Get all users
            cursor.execute("SELECT * FROM users;")
            users = cursor.fetchall()
            print(f"\nTotal users: {len(users)}")
            
            if users:
                print("\nUser data:")
                for user in users:
                    print(f"ID: {user[0]}")
                    if len(user) > 1:
                        print(f"Username: {user[1]}")
                    if len(user) > 2:
                        print(f"Password (hashed): {user[2][:20]}...")
                    if len(user) > 3:
                        print(f"Role: {user[3]}")
                    print("-" * 30)
        else:
            print("Users table not found!")
            
        # Check for other authentication-related tables
        auth_tables = ['user', 'login', 'account', 'auth']
        for table_name in auth_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            if cursor.fetchone():
                print(f"\nFound {table_name} table:")
                cursor.execute(f"SELECT * FROM {table_name};")
                data = cursor.fetchall()
                for row in data:
                    print(row)
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

def verify_password(username, password):
    """Function to verify login credentials"""
    try:
        conn = sqlite3.connect('nba_mvp.db')
        cursor = conn.cursor()
        
        # Hash the password (assuming it's stored as SHA-256)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
        user = cursor.fetchone()
        
        if user:
            print(f"✅ Login successful for user: {username}")
            print(f"User role: {user[3] if len(user) > 3 else 'N/A'}")
            return True
        else:
            print(f"❌ Login failed for user: {username}")
            return False
            
        conn.close()
        
    except Exception as e:
        print(f"Error during verification: {e}")
        return False

if __name__ == "__main__":
    print("NBA MVP Database User Checker")
    print("="*50)
    check_database()
    
    print("\n" + "="*50)
    print("Test login functionality:")
    
    # Test with common default users
    test_users = [
        ("admin", "admin"),
        ("admin", "password"),
        ("user", "user"),
        ("test", "test")
    ]
    
    for username, password in test_users:
        print(f"\nTesting: {username}/{password}")
        verify_password(username, password)
