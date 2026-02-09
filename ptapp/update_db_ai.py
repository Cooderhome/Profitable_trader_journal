import sqlite3
from pathlib import Path

BASE_DIR = Path('d:/PT/ptapp')
DB_PATH = BASE_DIR / 'new_data.db'

print(f"Connecting to {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE journal_entries ADD COLUMN ai_confidence FLOAT")
    print("Added ai_confidence")
except Exception as e:
    print(f"Could not add ai_confidence: {e}")

conn.commit()
conn.close()
