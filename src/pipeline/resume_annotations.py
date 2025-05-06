import json
from pathlib import Path
import sys

def annotate_jsonl(input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Load previously annotated lines
    annotated = {}
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    annotated[data['index']] = data
                except json.JSONDecodeError:
                    continue  # skip malformed lines

    with open(input_path, 'r', encoding='utf-8') as fin, \
         open(output_path, 'a', encoding='utf-8') as fout:

        for line in fin:
            data = json.loads(line)
            idx = data['index']

            if idx in annotated:
                continue  # already annotated

            print(f"\n--- Segment {idx} ---")
            print("Original:", data['text'])
            print("Filtered Tokens:", data['filtered'])

            print("Is this annotation correct? (y/n): ", end='', flush=True)
            ans = sys.stdin.readline().strip().lower()
            correct = ans == 'y'

            print("Optional note: ", end='', flush=True)
            note = sys.stdin.readline().strip()

            data['correct'] = correct
            data['note'] = note

            fout.write(json.dumps(data, ensure_ascii=False) + '\n')

    print(f"\n✅ Annotation complete. Output saved to {output_path}")


if __name__ == "__main__":
    input_file = input("Path to input JSONL file: ").strip()
    output_file = input("Path to save annotations: ").strip()
    annotate_jsonl(input_file, output_file)

