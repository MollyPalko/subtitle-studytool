#!/bin/bash
#SBATCH --job-name=parallel_tests
#SBATCH --output=parallel_%j.out
#SBATCH --time=03:00:00
#SBATCH --ntasks=20

module load miniconda3/latest
module load openmpi/4.1.7-e7k3

source /opt/local/miniconda3/etc/profile.d/conda.sh
conda activate myenv

for n in ...; do
    srun -n $n python parallel_build.py ...
done

