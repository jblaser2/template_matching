#!/bin/bash

#SBATCH --time=00:30:00 # walltime

#SBATCH --ntasks=1 # number of processor cores (i.e. tasks)

#SBATCH --nodes=1 # number of nodes

#SBATCH --gpus=a100:1

#SBATCH --export=NONE

#SBATCH --mem 5G

#SBATCH --qos=standby


# Set the max number of threads to use for programs using OpenMP. Should be <= ppn. Does nothing if the program doesn't use OpenMP.

export OMP_NUM_THREADS=$SLURM_CPUS_ON_NODE

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
module load cuda

tomogram_path="~/fsl_groups/grp_tomo_db1_d1/nobackup/archive/TomoDB1_d1/FlagellarMotor_P1/Hylemonella\ gracilis/yc2012-09-23-13/20120923_Hylemonella_10003.mrc"

