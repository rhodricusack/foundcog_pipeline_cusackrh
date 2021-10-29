# Setting up a forked repo on TCHPC with limited set of subjects as test data

* Create your own fork of https://github.com/rhodricusack/foundcog_pipeline 
* Create your personal foundcog directory (e.g., for me, /projects/pi-cusackrh/HPC_18_01039/cusackrh/foundcog)
* Clone this repo into your personal foundcog directory (e.g., /projects/pi-cusackrh/HPC_18_01039/cusackrh/foundcog/foundcog_pipeline)
* Create a bids directory in you personal foundcog directory
* Change into this directory 
    cd /projects/pi-cusackrh/HPC_18_01039/*username*/foundcog/bids
* Copy files but not directories here
    cp ../../../foundcog/bids .
* Choose subject(s) for test data and copy across
    cp -rf ../../../foundcog/bids/IRC13 .
* Edit your copy of participants.tsv so only this subject included
