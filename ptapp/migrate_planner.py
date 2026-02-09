"""
Migration script to add new columns to the planners table
Run this once to update your database schema
"""
import sqlite3
import os

# Path to your database
# Config says: f"sqlite:///{BASE_DIR / 'new_data.db'}"
# BASE_DIR is parent of app/config.py (so d:\PT\ptapp)
db_path = os.path.join(os.path.dirname(__file__), 'new_data.db')

print(f"Connecting to database: {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List of new columns to add
new_columns = [
    ("pair", "VARCHAR(20)"),
    ("direction", "VARCHAR(10)"),
    ("entry_price", "FLOAT"),
    ("stop_loss", "FLOAT"),
    ("take_profit", "FLOAT"),
    ("risk_amount", "FLOAT"),
    ("strategy", "VARCHAR(100)"),
    ("analysis", "TEXT"),
    ("executed_trade_id", "INTEGER"),
]

print("\nAdding new columns to planners table...")

for column_name, column_type in new_columns:
    try:
        # Check if column exists
        cursor.execute(f"PRAGMA table_info(planners)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if column_name not in columns:
            # Add the column
            cursor.execute(f"ALTER TABLE planners ADD COLUMN {column_name} {column_type}")
            print(f"✅ Added column: {column_name} ({column_type})")
        else:
            print(f"⏭️  Column already exists: {column_name}")
    except Exception as e:
        print(f"❌ Error adding column {column_name}: {e}")

# Commit changes
conn.commit()
print("\n✅ Migration completed successfully!")

# Show updated schema
print("\nUpdated planners table schema:")
cursor.execute("PRAGMA table_info(planners)")
for row in cursor.fetchall():
    print(f"  - {row[1]} ({row[2]})")

conn.close()
print("\n✅ Database connection closed.")
