import os
import pandas as pd
import matplotlib.pyplot as plt

# ============================
# Configuration
# ============================

SERIAL_PATH = "../src/serial_results.csv"
PARALLEL_PATH = "../parallel_results.csv"
COMMTREE_PATH = "../src/commtree_results.csv"

OUTPUT_DIR = "figures"
SCALING_LIMIT = 128          # limit used for scaling + speedup plots
REPRESENTATIVE_NS = [8, 16]  # worker counts to visualize

# ============================
# Setup
# ============================

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================
# Load data
# ============================

serial = pd.read_csv(SERIAL_PATH)
parallel = pd.read_csv(PARALLEL_PATH)
commtree = pd.read_csv(COMMTREE_PATH)

# Normalize schema
serial["n"] = 1

# ============================
# Helper functions
# ============================

def save(fig_name):
    path = os.path.join(OUTPUT_DIR, fig_name)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    print(f"Saved {path}")

def get_serial_time(limit):
    return serial[serial["limit"] == limit]["runtime_seconds"].iloc[0]

def best_parallel_for_limit(limit):
    subset = parallel[parallel["limit"] == limit]
    return subset.loc[subset["runtime_seconds"].idxmin()]

# ============================
# Figure 1: Runtime vs Input Size
# ============================

plt.figure()

plt.plot(
    serial["limit"],
    serial["runtime_seconds"],
    marker="o",
    label="Serial"
)

for n in REPRESENTATIVE_NS:
    subset = parallel[parallel["n"] == n]
    plt.plot(
        subset["limit"],
        subset["runtime_seconds"],
        marker="o",
        label=f"Parallel (n={n})"
    )

for n in REPRESENTATIVE_NS:
    subset = commtree[commtree["n"] == n]
    plt.plot(
        subset["limit"],
        subset["runtime_seconds"],
        marker="o",
        label=f"CommTree (n={n})"
    )

plt.xscale("log")
plt.yscale("log")
plt.xlabel("Input Size (limit)")
plt.ylabel("Runtime (seconds)")
plt.title("Runtime vs Input Size")
plt.legend()
plt.grid(True)

save("runtime_vs_input_size.png")

# ============================
# Figure 2: Scaling with Workers
# ============================

plt.figure()

parallel_subset = parallel[parallel["limit"] == SCALING_LIMIT]
commtree_subset = commtree[commtree["limit"] == SCALING_LIMIT]

plt.plot(
    parallel_subset["n"],
    parallel_subset["runtime_seconds"],
    marker="o",
    label="Parallel"
)

plt.plot(
    commtree_subset["n"],
    commtree_subset["runtime_seconds"],
    marker="o",
    label="CommTree"
)

plt.xlabel("Number of Workers (n)")
plt.ylabel("Runtime (seconds)")
plt.title(f"Scaling with Workers (limit={SCALING_LIMIT})")
plt.legend()
plt.grid(True)

save("scaling_with_workers.png")

# ============================
# Figure 3: Speedup vs Workers
# ============================

serial_time = get_serial_time(SCALING_LIMIT)

speedup_parallel = serial_time / parallel_subset["runtime_seconds"]
speedup_commtree = serial_time / commtree_subset["runtime_seconds"]

plt.figure()

plt.plot(
    parallel_subset["n"],
    speedup_parallel,
    marker="o",
    label="Parallel"
)

plt.plot(
    commtree_subset["n"],
    speedup_commtree,
    marker="o",
    label="CommTree"
)

plt.xlabel("Number of Workers (n)")
plt.ylabel("Speedup (T_serial / T_parallel)")
plt.title(f"Speedup vs Workers (limit={SCALING_LIMIT})")
plt.legend()
plt.grid(True)

save("speedup_vs_workers.png")

# ============================
# Figure 4: Parallel Efficiency
# ============================

eff_parallel = speedup_parallel / parallel_subset["n"]
eff_commtree = speedup_commtree / commtree_subset["n"]

plt.figure()

plt.plot(
    parallel_subset["n"],
    eff_parallel,
    marker="o",
    label="Parallel"
)

plt.plot(
    commtree_subset["n"],
    eff_commtree,
    marker="o",
    label="CommTree"
)

plt.xlabel("Number of Workers (n)")
plt.ylabel("Parallel Efficiency")
plt.title(f"Efficiency vs Workers (limit={SCALING_LIMIT})")
plt.legend()
plt.grid(True)

save("efficiency_vs_workers.png")

# ============================
# Figure 5: Serial vs Best Parallel
# ============================

best_rows = []
for limit in serial["limit"]:
    best_rows.append(best_parallel_for_limit(limit))

best_parallel_df = pd.DataFrame(best_rows)

plt.figure()

plt.plot(
    serial["limit"],
    serial["runtime_seconds"],
    marker="o",
    label="Serial"
)

plt.plot(
    best_parallel_df["limit"],
    best_parallel_df["runtime_seconds"],
    marker="o",
    label="Best Parallel Configuration"
)

plt.xscale("log")
plt.yscale("log")
plt.xlabel("Input Size (limit)")
plt.ylabel("Runtime (seconds)")
plt.title("Serial vs Best Parallel Runtime")
plt.legend()
plt.grid(True)

save("serial_vs_best_parallel.png")

