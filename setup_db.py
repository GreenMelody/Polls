import sqlite3

def setup_databases():
    # Set up polls database
    conn = sqlite3.connect('polls.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            id TEXT PRIMARY KEY,
            title TEXT,
            options TEXT, -- JSON format
            password TEXT, -- hashed password
            end_date DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

    # Set up poll results database
    conn = sqlite3.connect('poll-result.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            user_id TEXT,
            poll_id TEXT,
            option_index INTEGER,
            vote_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, poll_id)
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    setup_databases()
