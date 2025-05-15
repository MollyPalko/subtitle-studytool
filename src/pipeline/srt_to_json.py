import pysrt
import json
from konlpy.tag import Okt
import sys
import argparse
from pathlib import Path

def process_line(text, okt):
    lemmas = okt.pos(text, stem=True)
#    filtered = [word for word, pos in lemmas if pos not in ['Punctuation']]
#    filtered = [word for word, pos in lemmas if pos in ['Noun', 'Verb', 'Adjective', 'Adverb']]
#    return lemmas, filtered
    return lemmas, lemmas

def srt_to_jsonl(srt_path, jsonl_path):
    srt_path = Path(srt_path)
    jsonl_path = Path(jsonl_path)
    subs = pysrt.open(str(srt_path))  # pysrt needs str

    subs = pysrt.open(srt_path)
    okt = Okt()

    with open(jsonl_path, 'w', encoding='utf-8') as fout:
        for sub in subs:
            index = sub.index
            start = str(sub.start.to_time())
            end = str(sub.end.to_time())
            text = sub.text.strip().replace('\n', ' ')

            lemmas, filtered = process_line(text, okt)

            json_obj = {
                "index": index,
                "start": start,
                "end": end,
                "text": text,
                "lemmas": lemmas,
                "filtered": filtered
            }

            fout.write(json.dumps(json_obj, ensure_ascii=False) + '\n')

    print(f"✅ Processed and saved to {jsonl_path}")

def run_ex():
  # Example usage
  yt_srt = "../../raw/youtube/BTS_VLOG_RM_미술관.srt"
  yt_json = "../../json/BTS_VLOG_RM_미술관.jsonl"
  cp_srt = "../../raw/drama/Coffee_Prince/ep1.srt"
  cp_json = "../../json/Coffee_Prince_ep1.jsonl"
  tb_srt = "../../raw/drama/True_Beuty/ep1.srt"
  tb_json = "../../json/True_Beuty_ep1.jsonl"
  srt_to_jsonl(yt_srt, yt_json)
  srt_to_jsonl(cp_srt, cp_json)
  srt_to_jsonl(tb_srt, tb_json)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--build-script", action="store_true", help="Run from build script")
  parser.add_argument("--srt", type=str, help="Path to .srt file")
  parser.add_argument("--json", type=str, help="Output path for .jsonl file")
  args = parser.parse_args()

  if args.build_script:
# Resolve only if relative
    srt_path = Path(args.srt)
    json_path = Path(args.json)
    if not srt_path.is_absolute():
      srt_path = (Path(__file__).resolve().parent.parent / srt_path).resolve()

    if not json_path.is_absolute():
      json_path = (Path(__file__).resolve().parent.parent / json_path).resolve()

    print(f"🔧 [BUILD MODE] Converting {srt_path} -> {json_path}")
    srt_to_jsonl(srt_path, json_path)

  else:
    run_ex()


if __name__ == "__main__":
    main()


