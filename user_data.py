# user_data.py (FINAL VERSION - SQLITE INTEGRATION)

import sqlite3

# --- Database Configuration ---
DB_NAME = 'nutrition_tracker.db'
# ------------------------------

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    # Allows accessing column data by name (dictionary-like access)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Creates the user table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create the 'users' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            name TEXT,
            age INTEGER,
            gender TEXT,
            activity_level TEXT
        );
    ''')
    conn.commit()
    conn.close()

# Initialize the database file and table on module startup
init_db()


def get_all_users():
    """
    Fetches all user data from the database into a dictionary. 
    This mimics the old USER_DATA structure for easy compatibility with app.py's login logic.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, password, name, age, gender, activity_level FROM users")
    users = cursor.fetchall()
    conn.close()
    
    # Convert list of SQLite Row objects to a nested dictionary
    user_dict = {}
    for user in users:
        user_dict[user['username']] = {
            'password': user['password'],
            'name': user['name'],
            'age': user['age'],
            'gender': user['gender'],
            'activity_level': user['activity_level']
        }
    return user_dict


def register_new_user(username, password, name, age, gender, activity_level='SEDENTARY'):
    """Adds a new user profile to the SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Check if user already exists
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return False, "Username already exists."
    
    # 2. Insert new user
    try:
        cursor.execute('''
            INSERT INTO users (username, password, name, age, gender, activity_level)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, password, name, age, gender, activity_level))
        conn.commit()
        conn.close()
        return True, "Registration successful."
    except sqlite3.Error as e:
        conn.close()
        return False, f"Database error during registration: {e}"


def fetch_rda(activity_level: str) -> dict:
    """Returns simplified RDA values based on activity level."""
    # Simplified RDA values (Calories, Protein, Iron, Vitamin C)
    if activity_level == 'SEDENTARY':
        return {'Calories': 2000, 'Protein': 50, 'Iron': 15, 'Vitamin C': 60}
    elif activity_level == 'MODERATE':
        return {'Calories': 2500, 'Protein': 65, 'Iron': 18, 'Vitamin C': 75}
    elif activity_level == 'ACTIVE':
        return {'Calories': 3000, 'Protein': 80, 'Iron': 20, 'Vitamin C': 90}
    
    # Default fallback
    return {'Calories': 2000, 'Protein': 50, 'Iron': 15, 'Vitamin C': 60}