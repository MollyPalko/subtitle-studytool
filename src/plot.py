import pandas as pd
import matplotlib.pyplot as plt

# Load your data
df = pd.read_csv("benchmark_results.csv")

# Replace zeros with a small positive value for plotting clarity
# (or remove this if zeros are meaningful in your plots)
df['elapsed_seconds'] = df['elapsed_seconds'].replace(0, 0.1)

# Colors/markers for consistency
markers = ["o", "s", "D", "^", "v", "P", "X", "*"]
plt.rcParams.update({"figure.figsize": (8, 5), "font.size": 12})

# ------------------------------------------------------------
# 1. Serial vs Parallel vs Comm — elapsed time as limit grows
# ------------------------------------------------------------
plt.figure()
for version in df['version'].unique():
    subset = df[df['version'] == version]
    # Use only processes=1 for this comparison (otherwise lines mix)
    base = subset[subset['processes'] == 1]
    if len(base):
        plt.plot(base['limit'], base['elapsed_seconds'], marker='o', label=version)

plt.xlabel("Limit")
plt.ylabel("Elapsed Time (seconds)")
plt.title("Performance vs Limit (1 Process)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_version_vs_limit.png")
plt.close()

# ------------------------------------------------------------
# 2. Parallel scaling — elapsed time vs processes (grouped by limit)
# ------------------------------------------------------------
parallel = df[df['version'] == 'parallel']

plt.figure()
for i, limit in enumerate(sorted(parallel['limit'].unique())):
    sub = parallel[parallel['limit'] == limit]
    plt.plot(sub['processes'], sub['elapsed_seconds'],
             marker=markers[i % len(markers)],
             label=f"limit={limit}")

plt.xlabel("Processes")
plt.ylabel("Elapsed Time (seconds)")
plt.title("Parallel Scaling (Naive Parallel Version)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_parallel_scaling.png")
plt.close()

# ------------------------------------------------------------
# 3. Communication-optimized scaling — elapsed time vs processes
# ------------------------------------------------------------
comm = df[df['version'] == 'comm']

plt.figure()
for i, limit in enumerate(sorted(comm['limit'].unique())):
    sub = comm[comm['limit'] == limit]
    plt.plot(sub['processes'], sub['elapsed_seconds'],
             marker=markers[i % len(markers)],
             label=f"limit={limit}")

plt.xlabel("Processes")
plt.ylabel("Elapsed Time (seconds)")
plt.title("Communication Tree Version Scaling")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_comm_scaling.png")
plt.close()

print("Generated: plot_version_vs_limit.png, plot_parallel_scaling.png, plot_comm_scaling.png")

