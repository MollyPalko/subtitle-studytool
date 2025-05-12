CREATE TABLE IF NOT EXISTS Words (
    word_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    pos_tag TEXT NOT NULL,
    topik_level INTEGER NOT NULL,
    homonym BOOLEAN DEFAULT 0,
    UNIQUE(word, pos_tag, topik_level)
);

CREATE TABLE IF NOT EXISTS Videos (
    video_id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_name TEXT NOT NULL,
    series_name TEXT,
    category TEXT,
    source_id TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS WordFrequency (
    word_id INTEGER,
    video_id INTEGER,
    frequency INTEGER DEFAULT 1,
    PRIMARY KEY (word_id, video_id),
    FOREIGN KEY (word_id) REFERENCES Words(word_id),
    FOREIGN KEY (video_id) REFERENCES Videos(video_id)
);

