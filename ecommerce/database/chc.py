import sqlite3

# Path to your database
db_path = 'ecommerce/database/ecommerce.db'

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Update statement
cursor.execute("""
    UPDATE users
    SET email = 'dhaanishahamed5@gmail.com',
        name = 'Dhaanish Ahamed'
    WHERE email = 'bob.wilson@email.com';
""")

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Record updated successfully.")
