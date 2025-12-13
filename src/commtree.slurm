#!/bin/bash
#SBATCH --job-name=commtree_build
#SBATCH --output=commtree_%j.out
#SBATCH --error=commtree_%j.err
#SBATCH --time=06:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=20
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --mail-user=mpalko26@unm.edu
#SBATCH --mail-type=END,FAIL,BEGIN

module load miniconda3/latest
module load openmpi/4.1.7-e7k3

source /opt/local/miniconda3/etc/profile.d/conda.sh
conda activate myenv

RESULTS_FILE="commtree_results.csv"

if [ ! -f "$RESULTS_FILE" ]; then
    echo "implementation,n,limit,runtime_seconds" > "$RESULTS_FILE"
fi

COMM_RANKS=(1 8 16 32 64 128 256)
COMM_LIMITS=(1 8 16 32 64 128 256)

echo "[$(date)] Starting comm-tree tests."

for n in "${COMM_RANKS[@]}"; do
    for limit in "${COMM_LIMITS[@]}"; do

        echo "[$(date)] Running comm-tree build: n=$n limit=$limit"

        rm -f database/korean_vocab.db
        rm -f ../json/*

        start=$(date +%s)
        mpirun -np "$n" python commtree_build.py --limit "$limit" --shuffle
        end=$(date +%s)

        runtime=$((end - start))
        echo "commtree,$n,$limit,$runtime" >> "$RESULTS_FILE"
    done
done

echo "[$(date)] Comm-tree testing completed."
conda deactivate

