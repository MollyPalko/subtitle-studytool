# subtitle-studytool

## requirements
```
pip install konlpy pysrt
```

## pipeline stages/passes
1. pass 1:
- transform srt files to json files
- do line by line processing
- do tokenization, lemmatization, pos tagging using konlpy
2. pass 2:
- insert json files to database entries
- insert TOPIK levels, frequency counts, etc

## directory structure (to have by the end of the project)
korean-subtitle-nlp/
├── README.md
├── requirements.txt
├── .gitignore
│
├── raw/                         # ✅ Manually & automatically collected SRTs
│   ├── youtube/
│   ├── dramas/
│   ├── varietyShows/
│   └── idolLives/
│
├── data_aux/                    # ✅ Auxiliary data like word lists, dictionaries, etc.
│   ├── topik_vocab.csv
│   ├── korean_dict.csv
│   └── ...
│
├── data_intermediate/          # ✅ JSONL or CSV outputs from Pass 1
│   ├── youtube/
│   └── ...
│
├── data_db/                     # ✅ Optional: database file(s), e.g. SQLite
│   └── corpus.sqlite
│
├── src/
│   ├── pipeline/                # ✅ Core NLP pipeline logic
│   │   ├── pass1_tokenize.py
│   │   ├── pass2_index.py
│   │   └── utils/
│   │       ├── nlp_helpers.py
│   │       ├── file_utils.py
│   │       └── ...
│   │
│   └── downloaders/            # ✅ Subtitle download scripts
│       ├── download_viki.py
│       ├── download_yt.py
│       └── ...
│
├── notebooks/                  # 📓 Optional: Jupyter notebooks for testing/analyzing
│   └── explore_word_freq.ipynb
│
└── scripts/                    # 🔁 CLI tools, DB setup, batch runners
    ├── run_pipeline.py
    └── build_database.py


## database schema
    Words(
        word_id INTEGER PRIMARY KEY,
        word TEXT NOT NULL,
        pos_tag TEXT,             -- e.g., Noun, Verb, Adjective
        topik_level INTEGER       -- 1–6 or NULL if unknown
    )
    Videos( 
        video_id INTEGER PRIMARY KEY,
        video_name TEXT NOT NULL,
        series_name TEXT,         -- NULL if not 
        category TEXT,            -- 'drama', 'variety', 'idol_live', 'youtube'
        source_id TEXT            
        source TEXT
    )
    WordFrequency(
        word_id INTEGER,
        video_id INTEGER,
        frequency INTEGER DEFAULT 1,
        PRIMARY KEY (word_id, video_id),
        FOREIGN KEY (word_id) REFERENCES Words(word_id),
        FOREIGN KEY (video_id) REFERENCES Videos(video_id)
    )

## possibly helpful aux data
- TOPIK guide's 6000-word list
- GitHub versions in csv format
- Korean WordNet (KorLex) - great for root/semantic mappings, synonyms, etc
- NIADic (Korean Morpheme Dictionary from NIA)
- OpenKorDict

## future steps:
- create srt sub downloader for yt, viki, (and maybe weverse)
- create scripts to to use srt sub downloader to automatically populate raw directory
- improve pipeline in future iterations (confidence metrics, homonym differentiation, semantic analysis, automatic translation, etc)
- create GUI/CLI tools for on demand searching of YT and interacting with database
- integrate with Anki or other user data metrics


## current accuracy (manually graded by me)
📊 Annotation Report for True_Beuty_ep1_annotated.jsonl
Total lines annotated: 140/953 (14.7%)
Correct (✅):     105 (75.0%)
Incorrect (❌):   35 (25.0%)
Skipped (⏭):     0 (0.0%)

📊 Annotation Report for BTS_VLOG_RM_미술관_annotated.jsonl
Total lines annotated: 169/410 (41.2%)
Correct (✅):     128 (75.7%)
Incorrect (❌):   38 (22.5%)
Skipped (⏭):     3 (1.8%)


## current files and directory structure and purpose
/src/pipeline/
- annotate_output.py (original file to go through original output json and create another annotated json of correct/incorrect and notes)
- report_annotations.py (summarizes metrics like above from annotated json files)
- resume_annotations.py (better script to annotate output jsons for correctness - picks up where you left off last time)
- srt_to_json.py (contains function that takes in paths to input srt and output json and does the pass 1)

/json/
- BTS_VLOG_RM_미술관_annotated.jsonl
- BTS_VLOG_RM_미술관.jsonl
- Coffee_Prince_ep1.jsonl
- True_Beuty_ep1_annotated.jsonl
- True_Beuty_ep1.jsonl

the scheme here is that the original output data from pass 1 is the *.jsonl file and my manually annotated files are the *_annotated.jsonl files




