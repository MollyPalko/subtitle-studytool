#!/usr/bin/env bash

# ================================
# Benchmark configuration
# ================================
PROGRAMS=(
    "serial:python build_database.py"
    "parallel:mpirun -n {P} python parallel_build.py"
    "comm:mpirun -n {P} python commtree_build.py"
)

LIMITS=(4 8 16 32)
PROCS=(1 4 8 16)
OUTPUT="benchmark_results.csv"

DB_PATH="database/korean_vocab.db"
JSON_DIR="../json"

# ================================
# Setup output CSV
# ================================
echo "version,processes,limit,elapsed_seconds" > "$OUTPUT"

# ================================
# Helper to clear database + JSON
# ================================
clear_state() {
    rm -f "$DB_PATH"
    rm -f ${JSON_DIR}/*.json
}

# ================================
# Run benchmarks
# ================================
for entry in "${PROGRAMS[@]}"; do

    # Split VERSION and COMMAND
    VERSION="${entry%%:*}"
    PROGRAM="${entry#*:}"

    for limit in "${LIMITS[@]}"; do

        # Determine process counts
        if [[ "$VERSION" == "serial" ]]; then
            PROC_LIST=(1)
        else
            PROC_LIST=("${PROCS[@]}")
        fi

        for P in "${PROC_LIST[@]}"; do
            clear_state

            # Inject process count
            cmd=$(echo "$PROGRAM" | sed "s/{P}/$P/g")
            cmd="$cmd --limit $limit --shuffle"

            echo ""
            echo "======================================"
            echo "Running: [$VERSION] P=$P limit=$limit"
            echo "CMD: $cmd"
            echo "======================================"

            start=$(date +%s)
            eval $cmd
            end=$(date +%s)

            elapsed=$((end - start))
            echo "  -> Time: ${elapsed}s"

            # Write CSV row in normalized format
            echo "$VERSION,$P,$limit,$elapsed" >> "$OUTPUT"

        done
    done
done

echo ""
echo "Benchmark complete. Results saved to $OUTPUT"


