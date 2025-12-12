#!/bin/bash
#SBATCH --job-name=mpi_compare
#SBATCH --output=mpi_compare_%j.out
#SBATCH --error=mpi_compare_%j.err
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=20          # Max MPI processes we plan to test
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=mpalko26@unm.edu

# Load modules
module load miniconda3/latest
module load openmpi/4.1.7-e7k3

# Initialize conda
source /opt/local/miniconda3/etc/profile.d/conda.sh
conda activate myenv

# Output CSV file
RESULTS_FILE="mpi_build_results.csv"

# Create header if file does not exist
if [ ! -f "$RESULTS_FILE" ]; then
    echo "implementation,n,limit,runtime_seconds" > "$RESULTS_FILE"
fi

# Serial build limits
SERIAL_LIMITS=(1 8 16 32 64 128 )

for limit in "${SERIAL_LIMITS[@]}"; do
    echo "Running serial build with limit=$limit..."
    # Clean up before starting
    rm -f database/korean_vocab.db
    rm -f ../json/*

    start=$(date +%s)
    srun python build_database.py --limit "$limit" --shuffle
    end=$(date +%s)
    runtime=$((end - start))
    echo "serial,1,$limit,$runtime" >> "$RESULTS_FILE"
done

# Parallel build: vary MPI ranks and limit
PARALLEL_LIMITS=(2 8 16 ) #32 64 128 256)
PARALLEL_RANKS=(2 4 8 16 ) #32 64 128 256)

for n in "${PARALLEL_RANKS[@]}"; do
    for limit in "${PARALLEL_LIMITS[@]}"; do
        echo "Running parallel build with n=$n, limit=$limit..."
        # Clean up before starting
        rm -f database/korean_vocab.db
        rm -f ../json/*

        start=$(date +%s)
        srun -n "$n" python parallel_build.py --limit "$limit" --shuffle
        end=$(date +%s)
        runtime=$((end - start))
        echo "parallel,$n,$limit,$runtime" >> "$RESULTS_FILE"
    done
done

# Comm tree build: vary MPI ranks and limit
COMM_LIMITS=PARALLEL_LIMITS
COMM_RANKS=PARALLEL_RANKS

for n in "${COMM_RANKS[@]}"; do
    for limit in "${COMM_LIMITS[@]}"; do
        echo "Running commtree build with n=$n, limit=$limit..."
        # Clean up before starting
        rm -f database/korean_vocab.db
        rm -f ../json/*

        start=$(date +%s)
        srun -n "$n" python commtree_build.py --limit "$limit" --shuffle
        end=$(date +%s)
        runtime=$((end - start))
        echo "commtree,$n,$limit,$runtime" >> "$RESULTS_FILE"
    done
done

# Deactivate conda
conda deactivate

echo "All builds completed. Results written to $RESULTS_FILE."

