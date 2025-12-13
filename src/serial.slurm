#!/bin/bash
#SBATCH --job-name=serial_build
#SBATCH --output=serial_%j.out
#SBATCH --error=serial_%j.err
#SBATCH --time=05:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --mail-user=mpalko26@unm.edu
#SBATCH --mail-type=END,FAIL,BEGIN

module load miniconda3/latest
source /opt/local/miniconda3/etc/profile.d/conda.sh
conda activate myenv

RESULTS_FILE="serial_results.csv"

# Create output CSV if not present
if [ ! -f "$RESULTS_FILE" ]; then
    echo "implementation,n,limit,runtime_seconds" > "$RESULTS_FILE"
fi

# Serial build limits
SERIAL_LIMITS=(1 4 8 16 32 64 128 256)

echo "[$(date)] Starting serial tests."

for limit in "${SERIAL_LIMITS[@]}"; do
    echo "[$(date)] Running serial build: limit=$limit"

    rm -f database/korean_vocab.db
    rm -f ../json/*

    start=$(date +%s)
    python build_database.py --limit "$limit" --shuffle
    end=$(date +%s)

    runtime=$((end - start))
    echo "serial,1,$limit,$runtime" >> "$RESULTS_FILE"
done

echo "[$(date)] Serial testing completed."
conda deactivate

