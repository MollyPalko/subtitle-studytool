"""
Processes tokens from a JSONL subtitle transcript and updates:
- WordFrequency table
- Video metadata (total tokens, matched tokens, duration)

Run:
python process_tokens.py episode1.jsonl --db korean_vocab.db --video-id 3
"""

import sqlite3
import json
import argparse
from collections import Counter, defaultdict
from pathlib import Path


IGNORED_POS = {
    "Punctuation", "Josa", "Foreign", "Suffix", "Determiner",
    "Conjunction", "Exclamation"
}


# === Helpers ===
def parse_timestamp(ts: str) -> float:
    """Convert HH:MM:SS.micro to seconds (float)."""
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


# === Argument Parsing ===
parser = argparse.ArgumentParser(description="Add word frequencies and metadata from JSON to database.")
parser.add_argument("json_file", help="Path to the JSON subtitle file")
parser.add_argument("--db", default="your_database.db", help="Path to SQLite database")
parser.add_argument("--video-id", type=int, required=True, help="Video ID (must already exist in Videos table)")
parser.add_argument(
    '--enable-logging',
    action='store_true',
    help='Enable logging (default: False)'
)
args = parser.parse_args()

json_path = Path(args.json_file)
basename = json_path.stem
video_id = args.video_id


# === Logging Paths ===
ignored_log_path = f"ignored_tokens_{basename}.txt"
unmatched_log_path = f"unmatched_tokens_{basename}.txt"


# === Connect to DB ===
conn = sqlite3.connect(args.db)
cursor = conn.cursor()


# === Counters ===
total_tokens = 0
matched_tokens = 0
unmatched_tokens = 0
ignored_tokens = 0

word_freq_counter = Counter()
ignored_words_log = defaultdict(set)
unmatched_tokens_log = set()

video_duration_seconds = 0.0


# === Load JSONL ===
with open(json_path, encoding="utf-8") as f:
    data = [json.loads(line) for line in f if line.strip()]


# === Process Entries ===
for entry in data:
    # Update maximum end time
    end_ts = entry.get("end")
    if end_ts:
        end_sec = parse_timestamp(end_ts)
        if end_sec > video_duration_seconds:
            video_duration_seconds = end_sec

    # Tokens
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
            word_id = result[0]
            matched_tokens += 1
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


# === Update Video Metadata ===
duration_minutes = video_duration_seconds / 60.0

cursor.execute("""
    UPDATE Videos
    SET total_tokens = ?,
        matched_tokens = ?,
        duration_minutes = ?
    WHERE video_id = ?
""", (total_tokens, matched_tokens, duration_minutes, video_id))

conn.commit()


# === Write Logs ===
if args.enable_logging:
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

# maybe add an optional arg to turn these back on
# === Summary ===
"""
print("=== SUMMARY ===")
print(f"Processed file:         {json_path.name}")
print(f"  Total tokens:           {total_tokens}")
print(f"  Matched tokens:         {matched_tokens}")
print(f"  Duration (minutes):     {duration_minutes:.3f}")
print(f"Ignored tokens:         {ignored_tokens}")
print(f"Unmatched tokens:       {unmatched_tokens}")
print(f"Video ID:               {video_id}")
print(f"WordFrequency updated:  {len(word_freq_counter)} entries")
"""
if args.enable_logging:
    print(f"Logs saved:             {ignored_log_path}, {unmatched_log_path}")

conn.close()

