#!/bin/bash

#SBATCH --time=00:02:00 # walltime

#SBATCH --ntasks=1 # number of processor cores (i.e. tasks)

#SBATCH --nodes=1 # number of nodes

#SBATCH --gpus=a100:1

#SBATCH --export=NONE

#SBATCH --mem 5G

#SBATCH --qos=standby


# Set the max number of threads to use for programs using OpenMP. Should be <= ppn. Does nothing if the program doesn't use OpenMP.

export OMP_NUM_THREADS=$SLURM_CPUS_ON_NODE
export PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/bin:${PATH}
export LD_LIBRARY_PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/lib64:${LD_LIBRARY_PATH} 

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE 

module load spack
module load miniconda3
module load cuda

source activate pytom

pytom_create_template.py \
 -i /home/ejl62/template_matching_shared/masks/flagellum_AvgVol_4P120.mrc \
 -o /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/templates_masks/caulobacter_fm_template.mrc \
 --output-voxel 14.08 \
 --box-size 101 \
 --center \
 --low-pass 35

pytom_create_mask.py \
 -b 100 \
 -o /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/templates_masks/caulobacter_fm_mask.mrc \
 --voxel-size 14.08 \
 --radius 45 \
 --sigma 1
  
pytom_match_template.py \
 -t /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/templates_masks/caulobacter_fm_template.mrc \
 -m /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/templates_masks/caulobacter_fm_mask.mrc \
 -v /home/ejl62/fsl_groups/grp_tomo_db1_d1/nobackup/archive/TomoDB1_d1/FlagellarMotor_P1/Caulobacter\ crescentus/flag_3_full.rec \
 -d /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/results \
 --voxel-size-angstrom 14.08 \
 --particle-diameter 85 \
 --tilt-angles -60 60 \
 --random-phase \
 -g 0

pytom_estimate_roc.py \
 -j /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/results/flag_3_full_job.json \
 -n 5 \
 -r 60 \
 --crop-plot  > /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/results/flag_3_full_roc.log

pytom_extract_candidates.py \
 -j /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/results/flag_3_full_job.json \
 -n 5 \
 -r 60