"""
Migration script to add trading_goal_id to journal_entries
"""
import sqlite3
import os

# Create path to the database
# Based on app/config.py: BASE_DIR / 'new_data.db'
db_path = os.path.join(os.path.dirname(__file__), 'new_data.db')

print(f"Connecting to database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Adding trading_goal_id column to journal_entries table...")
    cursor.execute("ALTER TABLE journal_entries ADD COLUMN trading_goal_id INTEGER REFERENCES trading_goals(id)")
    print("✅ Successfully added column.")
except Exception as e:
    print(f"⚠️ Error (column might already exist): {e}")

conn.commit()
conn.close()
print("Done.")
