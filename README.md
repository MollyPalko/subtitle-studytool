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
```
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
```


## database schema
    Words(
        word_id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        pos_tag TEXT NOT NULL,
        topik_level INTEGER NOT NULL,
        homonym BOOLEAN DEFAULT 0,
        guide TEXT,
        UNIQUE(word, pos, level, guide)
    )
    Videos( 
        video_id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_name TEXT NOT NULL,
        series_name TEXT,
        category TEXT,
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


### Note:
- user will simply be responsible for determining homonyms in context
- our analysis and database will track unique words in the sense of unique in terms of level, pos, and actual word.
- ex. 눈 and 눈 (both 1급, 명사) will not be differentiated in our database. it will enhance the learning experience of users to differentiate 'eye' and 'snow' in context
- we can consider fixing this or adding better homonym detection/differntiation in later versions
- words detected as homonyms in the words database will have the boolean homonym flag to aid users in detecting homonyms


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
```
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
```

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


## /aux_data/topik/
- total of 10635 words are labeled 1급-6급 across 6 files
- these files downloaded from [kleocean](https://kleocean.com/토픽-어휘-topik-vocab/)
- files from kleocean for topik I and II lists were passed up for containing only 1847 and 3873 words respectively and only labeling words as 초/중 not 1-6
- file from [국립국어원](https://www.korean.go.kr/front/etcData/etcDataView.do?mn_id=46&etc_seq=71&pageIndex=21) were passed up for scoring words by A/B/C only and for containing only 5966 words. (this resource does contain hanja in addition to pos tagging though)
- english pos column is added when inserted to database, new word_id is created to be key, and usage column is eliminated



## how to insert parsed words from json into the database:
first in the sqlite shell, add the video entry:
```
INSERT INTO Videos (video_name, category)
VALUES ('[BTS VLOG] RM | 미술관 VLOG', 'YouTube');
```

get the video id of newly added entry:
```
SELECT video_id, video_name 
FROM Videos WHERE video_name = '[BTS VLOG] RM | 미술관 VLOG';
```

then in the cmd line, run the script to add the words and get the summary:
```
~/subtitle-studytool/src/database$ python process_tokens.py ../../json/BTS_VLOG_RM_미술관.jsonl --db korean_vocab.db --video-id 1
=== SUMMARY ===
Processed file:         BTS_VLOG_RM_미술관.jsonl
Total tokens:           2462
Matched tokens:         1132
Ignored tokens:         706
Unmatched tokens:       624
Video ID:               1
WordFrequency updated:  447 words
Logs saved:             ignored_tokens_BTS_VLOG_RM_미술관.txt, unmatched_tokens_BTS_VLOG_RM_미술관.txt
```


