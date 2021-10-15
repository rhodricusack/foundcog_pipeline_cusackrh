# Processing pipeline for FOUNDCOG data
By the FOUNDCOG team, Cusack lab, Trinity College Dublin 
    
 www.foundcog.org  foundcog@tcd.ie  www.cusacklab.org 
 
## Main files
* run_heudiconv.py        converts all founcog data in /mnt/siemens-dicom/anon to BIDS format using heuristic.py 
* foundcog_preproc.py     runs nipype pipeline to do preprocessing
* create_qa_report.py     creates reports (e.g., motion HTML and figure)


## General 
### Useful resources
* fMRIprep code https://github.com/nipreps/fmriprep/tree/master/fmriprep/workflows/bold
* nipype legacy workflows https://github.com/niflows/nipype1-workflows

## Road map of things that should/could be implemented
### All fMRI 
* Distortion correction using phase encode polarity images
    - base on sdc flow from fmriprep?
* Motion
    - spikes (i.e., model out frames with big shift)
    - censoring (i.e., cut out chunks of data)
    - framewise displacement                      *<-- key QA metric*
    - summarise proportion of data used- i.e., for each desired session, was it acquired at all, and how much of the desired length of data was useable         *<-- key QA metric*
    - slice-wise motion correction with EDDY (like dHCP)
    - deep learning reco
* Normalisation from EPI
    - prerequisite for any group analysis steps
    - could be done on overall mean across all time series (procedure for using EPIs from adults), or on sub-runs after censoring (Turk-Browne/Saxe labs)
* Region of interest definition
   - presumably through back-normalisation. What ROIs should we use? Shen like normal?
    
### Videos fMRI
* Inter-(subject+session) correlation
* MVPA modelling (within subject)
    - RDM
    - MDS, clustering  
* Compare RDMS between infants and adults *<-- key QA metric AND key outcome*
* MVPA modelling (across subject)
    - RDM
    - Within vs. across video contrast          *<-- key QA metric AND key outcome* 
* regression model of perceptual and semantic factors
* model contextual order effects (need to sort out adult analysis first)

### Pictures fMRI
* Stimulus minus baseline                       *<-- key QA metric*
* MVPA modelling using within-subject repetitions of each picture class
    - RDM
    - contrast of within vs. across picture class           
    - MDS, clustering
* Compare RDMS between infants and adults *<-- key QA metric AND key outcome*
* MVPA modelling using within-subject repetitions of each associated context
    - RDM
    - contrast of within vs. across picture context
    - MDS, clustering
    - comparison with videos                    *<-- key outcome*

### Only resting state fMRI 
* Calculate intrinsic timescales 

### For all infants with both pictures and intrinsic timescales
* Compare semantic representation strength (e.g., within vs between; or comparison of picture and video RDMS) vs. intrinsic timescale

### Diffusion
* Pre-processing 
* Compare timescales with structural connectivity?
* Relate connectivity of voxels with their video selectivity (c.f., Laura)

### Structural, T2
* Normalise from these
* Quantify structures?

## Other Major Analysis Directions
### MVPA: Bayesian and Searchlight
* Bayesian MVPA may be more sensitive
* Searchlight MVPA to give us whole brain maps of semantic representation and so on

### Cerebellum
* Graham's interest. Maedbh King, Joern Dierdichsen etc
* Should do some QA on cerebellar data (e.g., check coverage)

### Surface analysis
* If we keep getting T2 structural, we could run surface-based analysis

## Log of development
### 2021-10-1 [RC]

### 2021-10-10 [RC]
* Set up initial pipeline, using MCFLIRT
* Need metrics for QA motion
    * Evaluated including confounds pipeline from fMRI prep
    * Not possible at present as acompcor and tcompcor need CSF/WM/GM masks, which we don't have as don't want to have to rely on having structural
    * Include CalculateFWD and CalculateDVARS directly in pipeline
* DVARS requires brain mask - usually calculated from structural but what should we do?



