#!/bin/bash
#SBATCH --time=4:0:0
/projects/pi-cusackrh/HPC_18_01039/foundcog/pyenv/bin/heudiconv -d /mnt/siemens-dicom/anon/{subject}_RC_FOUNDCOG/20210928T141058.642000/Series_*/*.dcm -c dcm2niix -o ../bids -b -f heuristic.py -s IRN_1 -ss 1 --queue-args=--time=4:0:0
