import sqlite3

def init_db():
    """ 
    Initializes the SQLite database and creates the 'compliance' table if it does not exist.
    This function ensures that the database is set up correctly before storing compliance data.
    """
    try:
        # Establish a connection to the SQLite database (or create it if it doesn't exist)
        conn = sqlite3.connect('compliance.db')  # Ensure the filename is consistent with your app
        c = conn.cursor()
        # Create the 'compliance' table if it does not already exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS compliance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATETIME DEFAULT (datetime('now', 'localtime')),
                url TEXT NOT NULL,
                conformity TEXT NOT NULL,
                conformity_details BLOB NOT NULL
            )
        ''')
        # Commit the transaction to apply the changes
        conn.commit()
        print("Database initialized and table created.")
    except sqlite3.Error as e:
        # Handle any SQLite errors and print an error message
        print(f"An error occurred while initializing the database: {e}")
    finally:
        # Ensure the database connection is closed, even if an error occurs
        conn.close()  # Ensure the connection is closed even if an error occurs
# If the script is executed directly, initialize the database
if __name__ == '__main__':
    init_db()
