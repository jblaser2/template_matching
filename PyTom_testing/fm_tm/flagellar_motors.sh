#!/bin/bash

#SBATCH --time=00:30:00 # walltime

#SBATCH --ntasks=1 # number of processor cores (i.e. tasks)

#SBATCH --nodes=1 # number of nodes

#SBATCH --gpus=a100:1

#SBATCH --export=NONE

#SBATCH --mem 10G

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
 -i /home/ejl62/template_matching_shared/maps/flagellum_AvgVol_4P120.mrc \
 -o /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/templates_masks/vibrio_fm_template.mrc \
 --output-voxel 13.33 \
 --box-size 101 \
 --center \
 --low-pass 35

pytom_create_mask.py \
 -b 100 \
 -o /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/templates_masks/vibrio_fm_mask.mrc \
 --voxel-size 13.33 \
 --radius 45 \
 --sigma 1
  
pytom_match_template.py \
 -t /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/templates_masks/vibrio_fm_template.mrc \
 -m /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/templates_masks/vibrio_fm_mask.mrc \
 -v /home/ejl62/template_matching_shared/dataset_vibrio/Vibrio_pilTpilU_85_rec.mrc \
 -d /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/vibrio_results \
 --particle-diameter 1068.04 \
 -a /home/ejl62/template_matching_shared/dataset_vibrio/Vibrio_pilTpilU_85.rawtlt \
 --per-tilt-weighting \
 --low-pass 35 \
 --defocus /home/ejl62/template_matching_shared/dataset_vibrio/Vibrio_pilTpilU_85.defocus \
 --amplitude 0.07 \
 --spherical 2.7 \
 --voltage 300 \
 --random-phase \
 --rng-seed 7591214 \
 -g 0

pytom_estimate_roc.py \
 -j /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/vibrio_results/Vibrio_pilTpilU_85_rec_job.json \
 -n 3 \
 --radius-px 40.07 \
 --crop-plot  > /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/vibrio_results/Vibrio_pilTpilU_85_rec_roc.log \
 --log info

pytom_extract_candidates.py \
 -j /home/ejl62/template_matching_shared/pytom/flagellar_motor_tm/vibrio_results/Vibrio_pilTpilU_85_rec_job.json \
 -n 3 \
 --radius-px 40.07 \
 --log info