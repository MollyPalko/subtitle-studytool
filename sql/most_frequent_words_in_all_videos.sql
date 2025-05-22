SELECT w.word, w.pos_tag, w.topik_level, SUM(wf.frequency) as total_freq
FROM WordFrequency wf
JOIN Words w ON wf.word_id = w.word_id
GROUP BY wf.word_id
ORDER BY total_freq DESC
LIMIT 20;

