import json
import sys
from pathlib import Path

def report_stats(jsonl_path):
    path = Path(jsonl_path)
    if not path.exists():
        print(f"❌ File not found: {jsonl_path}")
        return

    # Derive the original file name
    original_path = path.parent / (path.stem.replace("_annotated", "") + ".jsonl")

    if not original_path.exists():
        print(f"❌ Original file not found: {original_path}")
        return

    # Count total lines in the original file
    with open(original_path, 'r', encoding='utf-8') as f:
        original_total = sum(1 for _ in f)

    total = 0
    correct = 0
    incorrect = 0
    skipped = 0

    # Read and count stats from the annotated file
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            total += 1
            try:
                data = json.loads(line)
                if 'correct' not in data:
                    skipped += 1
                elif data['correct']:
                    correct += 1
                else:
                    incorrect += 1
            except json.JSONDecodeError:
                skipped += 1  # Treat unreadable lines as skipped

    if original_total == 0:
        print("⚠️ Original file has no lines.")
        return

    # Output the stats
    annotated_percentage = (total / original_total) * 100
    print(f"📊 Annotation Report for {path.name}")
    print(f"Total lines annotated: {total}/{original_total} ({annotated_percentage:.1f}%)")
    print(f"Correct (✅):     {correct} ({correct / total:.1%})")
    print(f"Incorrect (❌):   {incorrect} ({incorrect / total:.1%})")
    print(f"Skipped (⏭):     {skipped} ({skipped / total:.1%})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python report_annotation_stats.py <path_to_jsonl>")
    else:
        report_stats(sys.argv[1])

