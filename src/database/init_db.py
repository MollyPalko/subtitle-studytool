import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "korean_vocab.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()
    print(f"✅ Database initialized from schema at {SCHEMA_PATH}")

if __name__ == "__main__":
    initialize_database()

