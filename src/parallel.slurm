#!/bin/bash
#SBATCH --job-name=parallel_build
#SBATCH --output=parallel_%j.out
#SBATCH --error=parallel_%j.err
#SBATCH --time=06:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=260
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --mail-user=mpalko26@unm.edu
#SBATCH --mail-type=END,FAIL,BEGIN

module load miniconda3/latest
module load openmpi/4.1.7-e7k3

source /opt/local/miniconda3/etc/profile.d/conda.sh
conda activate myenv

RESULTS_FILE="parallel_results.csv"

if [ ! -f "$RESULTS_FILE" ]; then
    echo "implementation,n,limit,runtime_seconds" > "$RESULTS_FILE"
fi

# Strong- and weak-scaling limits
PARALLEL_RANKS=(1 4 8 16 32 64 128 256)
PARALLEL_LIMITS=(1 8 16 32 64 128 256)

echo "[$(date)] Starting parallel tests."

for n in "${PARALLEL_RANKS[@]}"; do
    for limit in "${PARALLEL_LIMITS[@]}"; do

        echo "[$(date)] Running parallel build: n=$n limit=$limit"

        rm -f database/korean_vocab.db
        rm -f ../json/*

        start=$(date +%s)
        srun -n "$n" python parallel_build.py --limit "$limit" --shuffle
        end=$(date +%s)

        runtime=$((end - start))
        echo "parallel,$n,$limit,$runtime" >> "$RESULTS_FILE"
    done
done

echo "[$(date)] Parallel testing completed."
conda deactivate

