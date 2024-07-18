#!/bin/bash --login

  

#SBATCH --time=8:00:00 # walltime

#SBATCH --ntasks=1 # number of processor cores (i.e. tasks)

#SBATCH --nodes=1 # number of nodes

#SBATCH --gpus=4

#SBATCH -C 'pascal' # features syntax (use quotes): -C 'a&b&c&d'

#SBATCH --mail-user=ejl62@byu.edu # email address

#SBATCH --mail-type=BEGIN

#SBATCH --mail-type=END

#SBATCH --export=NONE

#SBATCH --mem 60G

  

# Set the max number of threads to use for programs using OpenMP. Should be <= ppn. Does nothing if the program doesn't use OpenMP.

export OMP_NUM_THREADS=$SLURM_CPUS_ON_NODE

export PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/bin:${PATH}
export LD_LIBRARY_PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/lib64:${LD_LIBRARY_PATH}
  

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE

  

module load miniconda3/24.3.0-poykqmt
module load cuda/12.4.1-pw6cogp

source activate pytme

  

python /home/ejl62/pyTME/scripts/match_template.py \
--target /home/ejl62/fsl_groups/grp_tomo_db1_d1/nobackup/archive/TomoDB1_d1/FlagellarMotor_P1/Caulobacter\ crescentus/flag_3_full.rec \
--template /home/ejl62/Documents/template_matching/fm_caulo_tm/flagellum_AvgVol_4P120.mrc \
--invert_target_contrast \
--use_gpu \
-n 4 \
-a 5 \
--memory_scaling 0.96 \
--no_fourier_padding \
-o /home/ejl62/ImageAI/template-matching/PyTME/tm_run_outputs/caulobacter_fm_1.pickle