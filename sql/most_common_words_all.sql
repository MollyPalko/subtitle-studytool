SELECT w.word, COUNT(DISTINCT wf.video_id) AS video_count
FROM WordFrequency wf
JOIN Words w ON wf.word_id = w.word_id
GROUP BY wf.word_id
ORDER BY video_count DESC
LIMIT 20;

