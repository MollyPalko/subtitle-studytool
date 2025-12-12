#!/bin/bash
#SBATCH --job-name=mpi_test
#SBATCH --output=mpi_test_%j.out
#SBATCH --error=mpi_test_%j.err
#SBATCH --time=00:30:00
#SBATCH --nodes=1
#SBATCH --ntasks=8          # Max MPI processes we plan to test
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G

# Load modules
module load miniconda3/latest
module load openmpi/4.1.7-e7k3

# Initialize conda
source /opt/local/miniconda3/etc/profile.d/conda.sh
conda activate myenv

# Loop over MPI ranks
for N in 1 2 4 8
do
    echo "Running with $N MPI processes..."
    srun -n $N python test_env.py
    echo "-------------------------------"
done

conda deactivate
