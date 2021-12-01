#!/bin/bash
#SBATCH --time=4:0:0
/projects/pi-cusackrh/HPC_18_01039/foundcog/pyenv/bin/heudiconv -d /mnt/siemens-dicom/anon/{subject}_RC_FOUNDCOG/20211011T160055.492000/Series_*/*.dcm -c dcm2niix --overwrite -o ../bids -b -f heuristic.py -s IRC_9 -ss 2 --queue-args=--time=4:0:0
