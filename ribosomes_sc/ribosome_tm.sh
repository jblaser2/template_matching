#!/bin/bash --login

  

#SBATCH --time=1:00:00 # walltime

#SBATCH --ntasks=1 # number of processor cores (i.e. tasks)

#SBATCH --nodes=1 # number of nodes

#SBATCH --gpus=4

#SBATCH --mail-user=ejl62@byu.edu # email address

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

source activate pytom

pytom_create_template.py \
 -i /home/ejl62/ImageAI/template-matching/PyTom/tm_tutorial/templates/6qzp_60S.mrc \
 -o /home/ejl62/ImageAI/template-matching/PyTom/tm_tutorial/templates/60S.mrc \
 --input-voxel 1.724 \
 --output-voxel 13.79 \
 --center \
 --invert \
 -b 60

pytom_create_mask.py \
 -b 60 \
 -o /home/ejl62/ImageAI/template-matching/PyTom/tm_tutorial/templates/mask_60S.mrc \
 --voxel-size 13.79 \
 --radius 10 \
 --sigma 1
  
pytom_match_template.py \
 -t /home/ejl62/ImageAI/template-matching/PyTom/tm_tutorial/templates/60S.mrc \
 -m /home/ejl62/ImageAI/template-matching/PyTom/tm_tutorial/templates/mask_60S.mrc \
 -v /home/ejl62/template_matching_shared/pytom_tutorial/dataset/tomo200528_100.mrc \
 -d /home/ejl62/template_matching_shared/pytom_tutorial/results_60S \
 --particle-diameter 300 \
 -a /home/ejl62/template_matching_shared/pytom_tutorial/dataset/tomo200528_100.rawtlt \
 --per-tilt-weighting \
 --low-pass 35 \
 --defocus /home/ejl62/template_matching_shared/pytom_tutorial/dataset/tomo200528_100.defocus \
 --amplitude 0.08 \
 --spherical 2.7 \
 --voltage 200 \
 --tomogram-ctf-model phase-flip \
 --dose-accumulation /home/ejl62/template_matching_shared/pytom_tutorial/dataset/tomo200528_100_dose.txt \
 --random-phase \
 -g 0

 pytom_estimate_roc.py \
 -j /home/ejl62/template_matching_shared/pytom_tutorial/results_60S/tomo200528_100_job.json \
 -n 800 \
 -r 8 \
 --bins 16 \
 --crop-plot  > /home/ejl62/template_matching_shared/pytom_tutorial/results_60S/tomo200528_100_roc.log

 pytom_extract_candidates.py -j /home/ejl62/template_matching_shared/pytom_tutorial/results_60S/tomo200528_100_job.json -n 300 -r 8