import re
from pathlib import Path
import pandas as pd
import unicodedata

# Map Korean POS to OKT-style English POS
POS_TRANSLATIONS = {
    "명사": "Noun",
    "일반명사":"Noun",
    "고유명사":"Noun",
    "의존명사":"Noun",
    "대명사":"Noun",
    "수사":"Noun",
    "동사": "Verb",
    "형용사": "Adjective",
    "관형사": "Determiner",
    "부사": "Adverb",
    "접속사": "Conjunction",
    "감탄사": "Exclamation",
    "조사": "Josa",
    "선어말어미": "PreEomi",
    "어미": "Eomi",
    "접미사": "Suffix",
    "구두점": "Punctuation",
    "외국어": "Foreign",
    "알파벳": "Alpha",
    "숫자": "Number",
    "미등록어": "Unknown",
    "트위터 해쉬태그": "Hashtag",
    "트위터 아이디": "ScreenName",
    "이메일 주소": "Email",
    "웹주소": "URL",
    # options that are not included in OKT but still appear in the original topik lists:
    "접사":"OtherAffix",
    "줄어든꼴":"OtherReducedForm",
    "줄어든말":"OtherContracted",
    # Fallback mapping (if needed)
    "기타": "Unknown"
}

INPUT_DIR = Path("../../aux_data/topik/")  # adjust as needed
OUTPUT_FILE = Path("../../aux_data/topik/cleaned_topik.csv")



def normalize_word(word):
    return unicodedata.normalize("NFC", word)


def parse_multientry_rows(df):
    rows = []

    for _, row in df.iterrows():
        base_forms_raw = str(row["어휘 Vocabulary"]).split("/")
        pos_krs_raw = str(row["품사 Word class"]).split("/")
        level = row["등급 Level"]

        guide = row.get("길잡이말 Guide", "")
        guide = guide.strip() if isinstance(guide, str) else ""

        try:
            level_int = int(str(level).replace("급", "").strip())
        except Exception:
            continue

        # Expand base forms and pos tags to align by index, then further split pos on '∙'
        for base_raw, pos_kr_raw in zip(base_forms_raw, pos_krs_raw):
            clean_base = normalize_word("".join(filter(str.isalpha, base_raw)))
#            pos_parts = re.split(r"[\∙·]", pos_kr_raw.strip())
            pos_parts = re.split(r"[∙·・]", pos_kr_raw.strip())
            
            for pos_kr in pos_parts:
                pos_en = POS_TRANSLATIONS.get(pos_kr.strip(), "Unknown")
                rows.append({
                    "base_word": clean_base,
                    "pos_kr": pos_kr.strip(),
                    "pos_tag": pos_en,
                    "level": level_int,
                    "guide": guide
                })

    return pd.DataFrame(rows)



'''
def parse_multientry_rows(df):
    rows = []

    for _, row in df.iterrows():
        base_forms = row["어휘 Vocabulary"].split("/")
        pos_krs = row["품사 Word class"].split("/")
        level = row["등급 Level"]
#        guide = row.get("길잡이말 Guide", "").strip()
        guide = row.get("길잡이말 Guide", "")
        guide = guide.strip() if isinstance(guide, str) else ""


        # Align lengths if mismatch by repeating or trimming
        max_len = max(len(base_forms), len(pos_krs))
        base_forms = (base_forms * max_len)[:max_len]
        pos_krs = (pos_krs * max_len)[:max_len]

        for base, pos_kr in zip(base_forms, pos_krs):
            clean_base = normalize_word("".join(filter(str.isalpha, base)))
            pos_en = POS_TRANSLATIONS.get(pos_kr.strip(), "Unknown")
            try:
                level_int = int(level.replace("급", "").strip())
            except Exception:
                continue  # skip malformed rows
            rows.append({
                "base_word": clean_base,
                "pos_kr": pos_kr.strip(),
                "pos_tag": pos_en,
                "level": level_int,
                "guide": guide
            })

    return pd.DataFrame(rows)
'''

def clean_topik_data():
    all_dfs = []

    for file in sorted(INPUT_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(file, encoding="utf-8", delimiter=",")
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue

        df = df.dropna(subset=["어휘 Vocabulary", "품사 Word class", "등급 Level"])
        parsed_df = parse_multientry_rows(df)
        all_dfs.append(parsed_df)

    if not all_dfs:
        raise ValueError("No valid TOPIK data found.")

    final_df = pd.concat(all_dfs, ignore_index=True)

    # Mark homonyms: same base_word, pos_tag, level
    final_df["homonym"] = final_df.duplicated(subset=["base_word", "pos_tag", "level"], keep=False)

    # Drop unnecessary columns for v1
    final_df = final_df[["base_word", "pos_kr", "pos_tag", "level", "homonym"]]

    # Sort and export
    final_df = final_df.sort_values(by=["level", "base_word", "pos_tag"])
    final_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"Cleaned TOPIK data written to {OUTPUT_FILE}")

if __name__ == "__main__":
    clean_topik_data()


