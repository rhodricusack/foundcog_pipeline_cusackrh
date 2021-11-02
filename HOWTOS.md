# Setting up a forked repo on TCHPC with limited set of subjects as test data

* Create your own fork of https://github.com/rhodricusack/foundcog_pipeline 
* Create your personal foundcog directory (e.g., for me, /projects/pi-cusackrh/HPC_18_01039/cusackrh/foundcog)
* Clone this repo into your personal foundcog directory (e.g., /projects/pi-cusackrh/HPC_18_01039/cusackrh/foundcog/foundcog_pipeline)
* Add the main repo as an upstream branch 
    git remote add upstream https://github.com/rhodricusack/foundcog_pipeline.git
    *to pull from this main repo*
    git fetch upstream
    git merge upstream/master master
* Create a bids directory in you personal foundcog directory
* Change into this directory 
    cd /projects/pi-cusackrh/HPC_18_01039/*username*/foundcog/bids
* Copy files but not directories here
    cp ../../../foundcog/bids .
* Choose subject(s) for test data and copy across
    cp -rf ../../../foundcog/bids/IRC13 .
* Edit your copy of participants.tsv so only this subject included


# Prior to running a script: Load fsl
* After you ssh kelvin, before running a script, you will need to load fsl as follows:

    `module load apps`

    `module load fsl`
    
* Note: if you ever wish to use fsl as a stand alone app, type `fsl`. This is not required for the foundcog analysis.


# Using Python on TCHPC

* To enable installation of packages on TCHPC, a virtual environment may be set up in your user account, containing your own copy of python and the packages that you require.

* For the foundcog analysis we will use the following shared environment:
  `/projects/pi-cusackrh/HPC_18_01039/foundcog/pyenv`
  
  To activate this environment type:
    `source /projects/pi-cusackrh/HPC_18_01039/foundcog/pyenv/bin/activate`
    
  Test that this is working with:
    `which python`
    
  Which should return:
    `/projects/pi-cusackrh/HPC_18_01039/foundcog/pyenv/bin/python`
