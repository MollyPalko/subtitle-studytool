#DB_PATH = "../database/all_korean.db"
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

# =========================
# CONFIG
# =========================
DB_PATH = "../../database/all_korean.db"
TEST_SIZE = 0.25
RANDOM_SEED = 0
LEARNING_RATE = 0.1
NUM_ITERATIONS = 300

LEVEL_MAP = {"A": 0, "B": 1, "C": 2, "D": 3}
INV_LEVEL_MAP = {v: k for k, v in LEVEL_MAP.items()}
K = 4  # number of classes

# =========================
# SOFTMAX MODEL FUNCTIONS
# =========================
def softmax(Z):
    Z = Z - np.max(Z, axis=1, keepdims=True)
    eZ = np.exp(Z)
    return eZ / np.sum(eZ, axis=1, keepdims=True)

def one_hot(y, K):
    Y = np.zeros((len(y), K), dtype=np.float32)
    Y[np.arange(len(y)), y] = 1.0
    return Y

def loss(P, Y):
    eps = 1e-12
    P = np.clip(P, eps, 1 - eps)
    return -np.mean(np.sum(Y * np.log(P), axis=1))

def accuracy(P, y):
    return np.mean(np.argmax(P, axis=1) == y)

def gradients(X, P, Y):
    m = X.shape[0]
    dW = (X.T @ (P - Y)) / m
    db = np.mean(P - Y, axis=0)
    return dW, db

# =========================
# LOAD DATA FROM SQLITE
# =========================
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

query = """
SELECT
    v.video_id,
    v.level,
    v.total_tokens,
    v.matched_tokens,
    v.duration_minutes,
    SUM(CASE WHEN w.topik_level = 1 THEN wf.frequency ELSE 0 END),
    SUM(CASE WHEN w.topik_level = 2 THEN wf.frequency ELSE 0 END),
    SUM(CASE WHEN w.topik_level = 3 THEN wf.frequency ELSE 0 END),
    SUM(CASE WHEN w.topik_level = 4 THEN wf.frequency ELSE 0 END),
    SUM(CASE WHEN w.topik_level = 5 THEN wf.frequency ELSE 0 END),
    SUM(CASE WHEN w.topik_level = 6 THEN wf.frequency ELSE 0 END)
FROM Videos v
LEFT JOIN WordFrequency wf ON v.video_id = wf.video_id
LEFT JOIN Words w ON wf.word_id = w.word_id
GROUP BY v.video_id, v.level;
"""

cursor.execute(query)
rows = cursor.fetchall()
conn.close()

# =========================
# BUILD FEATURE MATRICES
# =========================
X_known, y_known = [], []
X_unknown, unknown_ids = [], []

for row in rows:
    (
        vid, level, total_tokens, matched_tokens, duration,
        l1, l2, l3, l4, l5, l6
    ) = row

    matched_ratio = matched_tokens / total_tokens if total_tokens > 0 else 0.0
    tokens_per_min = total_tokens / duration if duration > 0 else 0.0

    features = np.array([
        total_tokens,
        matched_ratio,
        tokens_per_min,
        l1, l2, l3, l4, l5, l6
    ], dtype=np.float32)

    if level in LEVEL_MAP:
        X_known.append(features)
        y_known.append(LEVEL_MAP[level])
    elif level == "U":
        X_unknown.append(features)
        unknown_ids.append(vid)

X_known = np.array(X_known)
y_known = np.array(y_known)
X_unknown = np.array(X_unknown)

print("Known samples:", X_known.shape)
print("Unknown samples:", X_unknown.shape)

# =========================
# TRAIN / TEST SPLIT
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X_known, y_known, test_size=TEST_SIZE, random_state=RANDOM_SEED
)

# =========================
# FEATURE NORMALIZATION
# =========================
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)
X_unknown = scaler.transform(X_unknown)

Y_train = one_hot(y_train, K)
Y_test = one_hot(y_test, K)

# =========================
# INITIALIZE PARAMETERS
# =========================
d = X_train.shape[1]
rng = np.random.default_rng(RANDOM_SEED)
W = 0.01 * rng.standard_normal((d, K))
b = np.zeros(K)

# =========================
# GRADIENT DESCENT TRAINING
# =========================
train_losses, test_losses = [], []

for it in range(1, NUM_ITERATIONS + 1):
    P_train = softmax(X_train @ W + b)
    P_test = softmax(X_test @ W + b)

    dW, db = gradients(X_train, P_train, Y_train)
    W -= LEARNING_RATE * dW
    b -= LEARNING_RATE * db

    train_losses.append(loss(P_train, Y_train))
    test_losses.append(loss(P_test, Y_test))

    if it % 50 == 0:
        print(f"Iter {it}: train loss={train_losses[-1]:.4f}, "
              f"test loss={test_losses[-1]:.4f}")

# =========================
# TRAINING DIAGNOSTICS
# =========================
plt.figure(figsize=(8, 5))
plt.plot(train_losses, label="Train Loss")
plt.plot(test_losses, label="Test Loss")
plt.xlabel("Iteration")
plt.ylabel("Cross-Entropy Loss")
plt.title("Training and Test Loss Over Iterations")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("loss_curve.png")

# =========================
# EVALUATION
# =========================
P_train_final = softmax(X_train @ W + b)
P_test_final = softmax(X_test @ W + b)

print("\nTrain accuracy:", accuracy(P_train_final, y_train))
print("Test accuracy:", accuracy(P_test_final, y_test))

# Confusion matrix
cm = confusion_matrix(y_test, np.argmax(P_test_final, axis=1))
disp = ConfusionMatrixDisplay(cm, display_labels=["A", "B", "C", "D"])
disp.plot(cmap="Blues")
plt.title("Confusion Matrix (Test Set)")
plt.savefig("confusion_matrix.png")

# =========================
# PREDICT UNKNOWN VIDEOS
# =========================
if len(X_unknown) > 0:
    P_unknown = softmax(X_unknown @ W + b)
    preds = np.argmax(P_unknown, axis=1)

    print("\nPredictions for unknown videos:")
    for vid, p in zip(unknown_ids, preds):
        print(f"Video {vid}: predicted level {INV_LEVEL_MAP[p]}")

# ========================
# ANALYZE UNKNOWN VIDEO CONFIDENCE
# ========================
P_unknown = softmax(X_unknown @ W + b)
pred_classes = np.argmax(P_unknown, axis=1)
confidences = np.max(P_unknown, axis=1)
print("\nUnknown video prediction confidence:")
print("Mean confidence:", np.mean(confidences))
print("Min confidence:", np.min(confidences))
print("Max confidence:", np.max(confidences))
plt.figure()
plt.hist(confidences, bins=10)
plt.xlabel("Prediction confidence")
plt.ylabel("Number of videos")
plt.title("Confidence Distribution for Unknown Videos")
plt.savefig("confidence_dist_for_U.png")

threshold = 0.45
print("\nLow-confidence predictions:")
for vid, pred, conf in zip(unknown_ids, pred_classes, confidences):
    if conf < threshold:
        print(f"Video {vid}: predicted {INV_LEVEL_MAP[pred]} (confidence={conf:.2f})")

import pickle
MODEL_PATH = "./softmax_model.pkl"
with open(MODEL_PATH, "wb") as f:
    pickle.dump((W, b), f)
print(f"Model saved to {MODEL_PATH}")

