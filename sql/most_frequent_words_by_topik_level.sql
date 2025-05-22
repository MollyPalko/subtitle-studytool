SELECT w.topik_level, w.word, SUM(wf.frequency) as total_freq
FROM WordFrequency wf
JOIN Words w ON wf.word_id = w.word_id
GROUP BY w.topik_level, w.word
ORDER BY w.topik_level ASC, total_freq DESC;

