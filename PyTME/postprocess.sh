#!/bin/bash --login

  

#SBATCH --time=1:00:00 # walltime

#SBATCH --ntasks=1 # number of processor cores (i.e. tasks)

#SBATCH --nodes=1 # number of nodes

#SBATCH --gpus=1 # number of GPUs

#SBATCH --mail-user=ejl62@byu.edu # email address

#SBATCH --mail-type=END

#SBATCH --export=NONE

#SBATCH --mem 20G

  

# Set the max number of threads to use for programs using OpenMP. Should be <= ppn. Does nothing if the program doesn't use OpenMP.

export OMP_NUM_THREADS=$SLURM_CPUS_ON_NODE

export PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/bin:${PATH}
export LD_LIBRARY_PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/lib64:${LD_LIBRARY_PATH}
  

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE

module load miniconda3/24.3.0-poykqmt
module load cuda/12.4.1-pw6cogp

source activate pytme

postprocess.py \
--input_file ~/fsl_groups/fslg_imagseg/nobackup/archive/template_matching/pytme_output/caulobacter_fm_1.pickle \
--output_prefix caulobacter_pp_list \
--output_format relion