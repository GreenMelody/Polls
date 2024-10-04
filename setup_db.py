import os
import sqlite3
from dotenv import load_dotenv

def setup_database():
    # Set up the database
    print(f"setup_db.py execution")
    dotenv_path = os.path.abspath(os.path.join('sharedworkspace/','.env'))
    load_dotenv(dotenv_path)
    app_db_path = os.getenv('DB_PATH')
    app_db_file = os.getenv('DB_FILE')
    app_db_file_path = os.path.join(app_db_path, app_db_file)

    conn = sqlite3.connect(app_db_file_path)
    cursor = conn.cursor()

    # Polls table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            id TEXT PRIMARY KEY,
            title TEXT,
            options TEXT, -- JSON format
            password TEXT, -- hashed password
            end_date DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            visit_count INTEGER DEFAULT 0 -- 투표 페이지 방문자 수
        )
    ''')

    # Votes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            user_id TEXT,
            poll_id TEXT,
            option_index INTEGER,
            vote_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, poll_id)
        )
    ''')

    # Visitors table for tracking daily and total visits
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            date DATE PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS total_visits (
            total_count INTEGER DEFAULT 0
        )
    ''')

    # Initialize total visits if not present
    cursor.execute('INSERT INTO total_visits (total_count) SELECT 0 WHERE NOT EXISTS (SELECT 1 FROM total_visits)')

    # Polls count table for tracking total number of polls created
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls_count (
            total_polls INTEGER DEFAULT 0
        )
    ''')

    # Initialize polls count if not present
    cursor.execute('INSERT INTO polls_count (total_polls) SELECT 0 WHERE NOT EXISTS (SELECT 1 FROM polls_count)')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    setup_database()
