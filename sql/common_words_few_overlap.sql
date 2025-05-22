SELECT w.word, SUM(wf.frequency) AS total_freq, COUNT(DISTINCT wf.video_id) AS video_count
FROM WordFrequency wf
JOIN Words w ON wf.word_id = w.word_id
GROUP BY wf.word_id
HAVING video_count <= 2 AND total_freq > 10
ORDER BY total_freq DESC;

