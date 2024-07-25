#!/bin/bash

#SBATCH --time=00:30:00 # walltime

#SBATCH --ntasks=2 # number of processor cores (i.e. tasks)

#SBATCH --nodes=1 # number of nodes

#SBATCH --gpus=a100:1

#SBATCH --qos=standby

#SBATCH --export=NONE

#SBATCH --mem 15G


# Set the max number of threads to use for programs using OpenMP. Should be <= ppn. Does nothing if the program doesn't use OpenMP.
export OMP_NUM_THREADS=$SLURM_CPUS_ON_NODE
export PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/bin:${PATH}
export LD_LIBRARY_PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/lib64:${LD_LIBRARY_PATH} 

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE

tomogram_path="/home/ejl62/fsl_groups/grp_tomo_db1_d1/nobackup/archive/TomoDB1_d1/FlagellarMotor_P1/Hylemonella gracilis/yc2013-01-03-1"
output_path="/home/ejl62/template_matching_shared/reconstruction_test"
root_name="Bdel_Hyle_0010002.mrc"
direct_file=/home/ejl62/template_matching/ribosomes_sc/test_batch.adoc 

batchruntomo -di "$direct_file" \
    -root "$root_name" \
    -current "$tomogram_path" \
    -deliever "$output_path" \
    -gpus 1 \
    -cpus 2 