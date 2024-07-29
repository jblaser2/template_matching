#!/bin/bash --login

  

#SBATCH --time=0:20:00 # walltime

#SBATCH --ntasks=2 # number of processor cores (i.e. tasks)

#SBATCH --nodes=1 # number of nodes

#SBATCH --gpus=v100:1

#SBATCH --qos=msg

#SBATCH --export=NONE

#SBATCH --mem 10G

#SBATCH --job-name=qdtm_45

  

# Set the max number of threads to use for programs using OpenMP. Should be <= ppn. Does nothing if the program doesn't use OpenMP.
export OMP_NUM_THREADS=$SLURM_CPUS_ON_NODE
export PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/bin:${PATH}
export LD_LIBRARY_PATH=/apps/spack/root/opt/spack/linux-rhel9-haswell/gcc-13.2.0/cuda-12.4.1-pw6cogp5nuczn2qcgqnw6lvqdznny2ef/lib64:${LD_LIBRARY_PATH}

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE 
module load spack/release
module load miniconda3
module load cuda

source activate pytom

pytom_match_template.py \
 -t /home/ejl62/eben_s/template_matching/pytom/pytom_tutorial/templates/60S.mrc \
 -m /home/ejl62/eben_s/template_matching/pytom/pytom_tutorial/templates/mask_60S.mrc \
 -v /home/ejl62/eben_s/template_matching/pytom/pytom_tutorial/dataset/tomo200528_100.mrc \
 -d /home/ejl62/eben_s/template_matching/qd_tm_test_results/45 \
 --particle-diameter 300 \
 -a -45 45 \
 --low-pass 35 \
 --amplitude 0.08 \
 --spherical 2.7 \
 --voltage 200 \
 --tomogram-ctf-model phase-flip \
 --random-phase \
 -g 0

if [ $? -eq 0 ]; then
    pytom_estimate_roc.py \
    -j /home/ejl62/eben_s/template_matching/qd_tm_test_results/45/tomo200528_100_job.json \
    -n 800 \
    -r 8 \
    --bins 16 \
    --crop-plot  > //home/ejl62/eben_s/template_matching/qd_tm_test_results/45/tomo200528_100_roc.log

    pytom_extract_candidates.py -j /home/ejl62/eben_s/template_matching/qd_tm_test_results/45/tomo200528_100_job.json \
    -n 300 \
    -r 8 \
    -c 0.4
 else 
    echo "Shot through the heart, and you're to blame. Template matching failed again."
 fi