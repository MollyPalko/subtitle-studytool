import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("benchmark_results.csv")

# SERIAL
plt.figure()
sub = df[df["version"] == "serial"]
for p in sorted(sub["processes"].unique()):
    sub2 = sub[sub["processes"] == p]
    plt.plot(sub2["limit"], sub2["elapsed_seconds"], marker="o", label=f"proc={p}")

plt.xlabel("limit")
plt.ylabel("elapsed (s)")
plt.title("Serial workflow")
plt.legend()
plt.tight_layout()
plt.savefig("serial.png")

# PARALLEL
plt.figure()
sub = df[df["version"] == "parallel"]
for p in sorted(sub["processes"].unique()):
    sub2 = sub[sub["processes"] == p]
    plt.plot(sub2["limit"], sub2["elapsed_seconds"], marker="o", label=f"proc={p}")

plt.xlabel("limit")
plt.ylabel("elapsed (s)")
plt.title("Parallel workflow")
plt.legend()
plt.tight_layout()
plt.savefig("parallel.png")

# COMM
plt.figure()
sub = df[df["version"] == "comm"]
for p in sorted(sub["processes"].unique()):
    sub2 = sub[sub["processes"] == p]
    plt.plot(sub2["limit"], sub2["elapsed_seconds"], marker="o", label=f"proc={p}")

plt.xlabel("limit")
plt.ylabel("elapsed (s)")
plt.title("Comm workflow")
plt.legend()
plt.tight_layout()
plt.savefig("comm.png")

