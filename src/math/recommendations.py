import sqlite3
import numpy as np
import matplotlib.pyplot as plt
import pickle
from sklearn.preprocessing import StandardScaler
import csv
import os

MODEL_VER = "noFrequencyFeaturesInModel" # doesn't work with this version
MODEL_VER = "frequencyFeaturesInModel"
os.chdir(MODEL_VER)

# =========================
# CONFIG
# =========================
DB_PATH = "../../database/all_korean.db"
MODEL_PATH = "./softmax_model.pkl"
LEVEL_MAP = {"A": 0, "B": 1, "C": 2, "D": 3}
INV_LEVEL_MAP = {v: k for k, v in LEVEL_MAP.items()}
K = 4

# =========================
# LOAD MODEL
# =========================
with open(MODEL_PATH, "rb") as f:
    W, b = pickle.load(f)

# =========================
# SOFTMAX FUNCTION
# =========================
def softmax(Z):
    Z = Z - np.max(Z, axis=1, keepdims=True)
    eZ = np.exp(Z)
    return eZ / np.sum(eZ, axis=1, keepdims=True)

# =========================
# QUERY UNKNOWN DRAMA VIDEOS
# =========================
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

query = """
SELECT
    v.video_id,
    v.video,
    v.series,
    v.total_tokens,
    v.matched_tokens,
    v.duration_minutes,
    GROUP_CONCAT(w.topik_level || ':' || wf.frequency)
FROM Videos v
LEFT JOIN WordFrequency wf ON v.video_id = wf.video_id
LEFT JOIN Words w ON wf.word_id = w.word_id
WHERE v.level = 'U' AND v.source = 'drama'
GROUP BY v.video_id;
"""

cursor.execute(query)
rows = cursor.fetchall()
conn.close()

# =========================
# BUILD FEATURE MATRIX
# =========================
X_unknown = []
unknown_info = []

for row in rows:
    vid, video_field, series_field, total_tokens, matched_tokens, duration, freq_str = row
    matched_ratio = matched_tokens / total_tokens if total_tokens > 0 else 0.0
    tokens_per_min = total_tokens / duration if duration > 0 else 0.0

    # Parse frequencies
    topik_freqs = {i: [] for i in range(1, 7)}
    all_freqs = []
    if freq_str:
        for item in freq_str.split(','):
            topik, freq = item.split(':')
            topik = int(topik)
            freq = int(freq)
            topik_freqs[topik].append(freq)
            all_freqs.append(freq)

    # Aggregate level-specific sums
    level_sums = [sum(topik_freqs[i]) for i in range(1, 7)]

    # Frequency stats
    avg_word_freq = np.mean(all_freqs) if all_freqs else 0.0
    max_word_freq = np.max(all_freqs) if all_freqs else 0.0
    var_word_freq = np.var(all_freqs) if all_freqs else 0.0

    # Level-specific frequency ratios
    level_ratios = [s / total_tokens if total_tokens > 0 else 0.0 for s in level_sums]

    features = np.array([
        total_tokens,
        matched_ratio,
        tokens_per_min,
        avg_word_freq,
        max_word_freq,
        var_word_freq,
        *level_ratios
    ], dtype=np.float32)

    X_unknown.append(features)
    unknown_info.append({
        "video_id": vid,
        "video": video_field,
        "series": series_field
    })

X_unknown = np.array(X_unknown)

# =========================
# FEATURE SCALING
# =========================
scaler = StandardScaler()
X_unknown_scaled = scaler.fit_transform(X_unknown)

# =========================
# PREDICT UNKNOWN VIDEOS
# =========================
P_unknown = softmax(X_unknown_scaled @ W + b)
pred_classes = np.argmax(P_unknown, axis=1)
confidences = np.max(P_unknown, axis=1)

# Attach predictions to video info
for info, pred, conf in zip(unknown_info, pred_classes, confidences):
    info["pred_level"] = INV_LEVEL_MAP[pred]
    info["confidence"] = conf

# =========================
# PLOT RECOMMENDATIONS
# =========================
plt.figure(figsize=(14, 7))

# Map series names to colors
series_names = list({info["series"] for info in unknown_info})
colors = plt.cm.tab10.colors  # plt.cm.Pastel1.colors  
series_color_map = {name: colors[i % len(colors)] for i, name in enumerate(series_names)}

# Horizontal jitter
jitter_width = 0.25
for info in unknown_info:
    x = LEVEL_MAP[info["pred_level"]] + np.random.uniform(-jitter_width, jitter_width)
    y = info["confidence"]
    c = series_color_map.get(info["series"], "gray")
    plt.scatter(x, y, color=c, alpha=0.7)
    # (this was actually too much) Label each dot with video field, slightly above the point
#   plt.text(x, y + 0.01, info["video"], fontsize=7, rotation=45, ha='center', va='bottom')

# Legend
handles = [plt.Line2D([0], [0], marker='o', color='w',
                      markerfacecolor=series_color_map[name], markersize=8)
           for name in series_names]
plt.legend(handles, series_names, title="Series", bbox_to_anchor=(1.05, 1), loc='upper left')

plt.xticks(list(LEVEL_MAP.values()), list(LEVEL_MAP.keys()))
plt.xlabel("Predicted Level")
plt.ylabel("Prediction Confidence")
plt.title("Unknown Drama Video Recommendations")
plt.grid(True)
plt.tight_layout()
plt.savefig("unknown_drama_recommendations.png")

# =========================
# EXPORT DATA TO CSV
# =========================
with open("unknown_drama_predictions.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["video_id","video","series","pred_level","confidence"])
    writer.writeheader()
    writer.writerows(unknown_info)

print("Exported unknown drama video predictions to unknown_drama_predictions.csv")

