#!/bin/bash

#SBATCH --time=00:30:00 # walltime

#SBATCH --ntasks=4 # number of processor cores (i.e. tasks)

#SBATCH --nodes=1 # number of nodes

#SBATCH --gpus=v100:1

#SBATCH --qos=msg

#SBATCH --export=NONE

#SBATCH --mem 15G

#SBATCH --job-name="reconstruct_tomo"


# Set the max number of threads to use for programs using OpenMP. Should be <= ppn. Does nothing if the program doesn't use OpenMP.
export OMP_NUM_THREADS=$SLURM_CPUS_ON_NODE
export PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/bin:${PATH}
export LD_LIBRARY_PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/lib64:${LD_LIBRARY_PATH} 

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
module load spack
module load cuda

tomogram_path="/home/ejl62/eben_s/reconstruct_tomo/test_tomos/"
output_path="/home/ejl62/eben_s/reconstruct_tomo/test1_out/"
root_name="09sep10b_090409MP22_016"
direct_file=/home/ejl62/template_matching/ribosomes_sc/test_batch.adoc 

batchruntomo -di "$direct_file" \
    -root "$root_name" \
    -current "$tomogram_path" \
    -deliver "$output_path" \
    -gpus 1 \
    -cpus 4