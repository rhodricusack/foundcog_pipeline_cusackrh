#!/bin/bash
cd /projects/pi-cusackrh/HPC_18_01039/foundcog
source pyenv/bin/activate
cd foundcog_pipeline
source run_heudiconv.sh
export PYTHONPATH=/projects/pi-cusackrh/HPC_18_01039/repos/fmriprep:/projects/pi-cusackrh/HPC_18_01039/repos/niworkflows
export NIPYPE_NO_ET=1
python foundcog_preproc.py
python create_qa_report.py