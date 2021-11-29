#!/bin/bash
# Run heudiconv for all subjects
#  Rhodri Cusack and the FOUNDCOG team, TCIN Dublin 2021-11-26, cusackrh@tcd.ie
for subpath in  /mnt/siemens-dicom/anon/*FOUNDCOG; do
    sub="$(basename -- $subpath | sed 's/_RC_FOUNDCOG//g')"
    echo "Working on $sub"

    ses=1    
    for sespath in $subpath/*; do
        echo "Session $ses in $sespath"
        sesbasename="$(basename -- $sespath)"
        heudiconv -d "/mnt/siemens-dicom/anon/{subject}_RC_FOUNDCOG/${sesbasename}/Series_*/*.dcm" -c dcm2niix -o ../bids -b -f heuristic.py -s $sub -ss $ses -q SLURM  --queue-args="--time=4:0:0"
        ses=$(($ses + 1))
    done
done