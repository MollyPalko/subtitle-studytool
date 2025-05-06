import pysrt
import json
from konlpy.tag import Okt

def process_line(text, okt):
    lemmas = okt.pos(text, stem=True)
#    filtered = [word for word, pos in lemmas if pos not in ['Punctuation']]
#    filtered = [word for word, pos in lemmas if pos in ['Noun', 'Verb', 'Adjective', 'Adverb']]
#    return lemmas, filtered
    return lemmas, lemmas

def srt_to_jsonl(srt_path, jsonl_path):
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

