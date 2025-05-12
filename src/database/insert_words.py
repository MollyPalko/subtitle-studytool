import sqlite3
import csv

CLEANED_CSV_PATH = '../../aux_data/topik/cleaned_topik.csv'

# Connect to the SQLite database
conn = sqlite3.connect('./korean_vocab.db')
# Change this to your actual .db file
cursor = conn.cursor()

# Open the CSV file
with open(CLEANED_CSV_PATH, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)  # Use DictReader to map column headers

    for row in reader:
        # Extract and rename fields from CSV to match the DB schema
        word = row['base_word']
        pos_tag = row['pos_tag']
        level = int(row['level'])  # topik_level in DB
        hstr = row['homonym'].strip().lower()
        homonym = 1 if hstr in ['1', 'true', 'yes'] else 0

        try:
            cursor.execute('''
                INSERT OR IGNORE INTO Words (word, pos_tag, topik_level, homonym)
                VALUES (?, ?, ?, ?)
            ''', (word, pos_tag, level, homonym))
        except Exception as e:
            print(f"Failed to insert row {row}: {e}")

# Commit and close
conn.commit()
conn.close()

