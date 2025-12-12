#!/bin/bash
#SBATCH --job-name=test
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
echo "trying to run serial build..."
srun python build_database.py --limit 2 --shuffle
#srun -n $N python test_env.py
echo "-------------------------------"

echo "trying to run parallel build..."
srun -n 2 python parallel_build.py --limit 2 --shuffle
#srun -n $N python test_env.py
echo "-------------------------------"

echo "trying to run comm tree build..."
srun -n 2 python commtree_build.py --limit 2 --shuffle
#srun -n $N python test_env.py
echo "-------------------------------"


conda deactivate
