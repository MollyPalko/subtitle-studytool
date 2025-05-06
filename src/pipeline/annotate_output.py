import json
from pathlib import Path

def annotate_jsonl(input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        print(f"Input file {input_path} not found.")
        return

    with input_path.open(encoding='utf-8') as infile, output_path.open('w', encoding='utf-8') as outfile:
        for line_num, line in enumerate(infile, 1):
            entry = json.loads(line.strip())
            print(f"\n=== Line {line_num} ===")
            print(f"Original: {entry.get('text', '(no text)')}")
            print(f"Filtered: {entry.get('filtered', '(no filtered output)')}")

            while True:
                response = input("Is this satisfactory? [y/n/s=skip/q=quit] ").strip().lower()
                if response in ['y', 'n', 's', 'q']:
                    break

            if response == 'q':
                print("Quitting.")
                break
            elif response == 's':
                continue

            annotation = {
                "index": entry.get("index", line_num),
                "text": entry.get("text"),
                "filtered": entry.get("filtered"),
                "satisfactory": response == 'y'
            }

            if response == 'n':
                note = input("Optional note: ").strip()
                if note:
                    annotation["note"] = note

            outfile.write(json.dumps(annotation, ensure_ascii=False) + "\n")

        print(f"\nAnnotations saved to: {output_path}")

if __name__ == "__main__":
    input_file = input("Path to input JSONL file: ").strip()
    output_file = input("Path to save annotations: ").strip()
    annotate_jsonl(input_file, output_file)

