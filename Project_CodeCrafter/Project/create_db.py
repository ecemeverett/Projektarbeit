import sqlite3

def init_db():
    """Initialize the SQLite database and create the compliance table."""
    try:
        conn = sqlite3.connect('compliance.db')  # Ensure the filename is consistent with your app
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS compliance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATETIME DEFAULT (datetime('now', 'localtime')),
                url TEXT NOT NULL,
                conformity TEXT NOT NULL,
                conformity_details BLOB NOT NULL
            )
        ''')
        conn.commit()
        print("Database initialized and table created.")
    except sqlite3.Error as e:
        print(f"An error occurred while initializing the database: {e}")
    finally:
        conn.close()  # Ensure the connection is closed even if an error occurs

if __name__ == '__main__':
    init_db()
