'''
this file takes in a json of the tokens from a video and adds
words that match an entry from the topik/Words table to the database
while counting the frequency, ignores and logs words with an ignorable
pos, and logs and ignores words that do not match an entry from the 
topik/Words table. 

This is to ignore words that are potentially incorrectly parsed/tagged
and still be able to inspect the parsed scripts for valid words not
in the official topik lists. maybe in future we can add a new
functionality where users can manually add their own entries to the
Words table.

run this file with: 
python process_tokens.py episode1.json --db my.db --video-id 3
(after you have already added the entry to the videos table)

this file can then be connected to another script to automatically add
words from many json files
'''

import sqlite3
import json
import argparse
from collections import Counter, defaultdict
from pathlib import Path

IGNORED_POS = {
    "Punctuation", "Josa", "Foreign", "Suffix", "Determiner",
    "Conjunction", "Exclamation"
}


# === Argument Parsing ===
parser = argparse.ArgumentParser(description="Add word frequencies from JSON to WordFrequency table.")
parser.add_argument("json_file", help="Path to the JSON subtitle file")
parser.add_argument("--db", default="your_database.db", help="Path to SQLite database")
parser.add_argument("--video-id", type=int, required=True, help="Video ID (must already exist in Videos table)")
args = parser.parse_args()

json_path = Path(args.json_file)
basename = json_path.stem
video_id = args.video_id


# === Setup Logging Paths ===
ignored_log_path = f"ignored_tokens_{basename}.txt"
unmatched_log_path = f"unmatched_tokens_{basename}.txt"

# === Connect to Database ===
conn = sqlite3.connect(args.db)
cursor = conn.cursor()

# === Token Counters & Logs ===
total_tokens = 0
matched_tokens = 0
unmatched_tokens = 0
ignored_tokens = 0

word_freq_counter = Counter()
ignored_words_log = defaultdict(set)
unmatched_tokens_log = set()

# === Load JSON ===
with open(json_path, encoding="utf-8") as f:
    data = [json.loads(line) for line in f if line.strip()]
    #data = json.load(f)

# === Process Tokens ===
for entry in data:
    for word, pos_tag in entry.get("filtered", []):
        total_tokens += 1

        if pos_tag in IGNORED_POS:
            ignored_tokens += 1
            ignored_words_log[pos_tag].add(word)
            continue

        cursor.execute("""
            SELECT word_id FROM Words
            WHERE word = ? AND pos_tag = ?
        """, (word, pos_tag))
        result = cursor.fetchone()

        if result:
            matched_tokens += 1
            word_id = result[0]
            word_freq_counter[word_id] += 1
        else:
            unmatched_tokens += 1
            unmatched_tokens_log.add((word, pos_tag))

# === Insert Word Frequencies ===
for word_id, count in word_freq_counter.items():
    cursor.execute("""
        INSERT INTO WordFrequency (video_id, word_id, frequency)
        VALUES (?, ?, ?)
        ON CONFLICT(video_id, word_id)
        DO UPDATE SET frequency = frequency + excluded.frequency
    """, (video_id, word_id, count))

conn.commit()

# === Write Logs ===
with open(ignored_log_path, "w", encoding="utf-8") as f:
    f.write("=== IGNORED TOKENS BY POS TAG ===\n")
    for pos_tag, words in sorted(ignored_words_log.items()):
        f.write(f"\n[{pos_tag}] ({len(words)} words)\n")
        for word in sorted(words):
            f.write(f"  {word}\n")

with open(unmatched_log_path, "w", encoding="utf-8") as f:
    f.write("=== UNMATCHED TOKENS (not in Words table) ===\n")
    for word, pos_tag in sorted(unmatched_tokens_log):
        f.write(f"{word} ({pos_tag})\n")

# === Summary ===
print("=== SUMMARY ===")
print(f"Processed file:         {json_path.name}")
print(f"Total tokens:           {total_tokens}")
print(f"Matched tokens:         {matched_tokens}")
print(f"Ignored tokens:         {ignored_tokens}")
print(f"Unmatched tokens:       {unmatched_tokens}")
print(f"Video ID:               {video_id}")
print(f"WordFrequency updated:  {len(word_freq_counter)} words")
print(f"Logs saved:             {ignored_log_path}, {unmatched_log_path}")

conn.close()



