'''
If running on TCHPC, need to add following to your .bashrc
# User specific aliases and functions
module load apps gcc/9.3.0
module load apps python/3.8.6
module load apps fsl
export PATH=/projects/pi-cusackrh/HPC_18_01039/software/mricron:$PATH
export PATH=/projects/pi-cusackrh/HPC_18_01039/software/dcm2niix-1.0.20211006/build/bin:$PATH
'''

from heudiconv import bids
from heudiconv.main import workflow
from os import path

import glob

# Path to scan
dcmpth='/mnt/siemens-dicom/anon'
bidsoutdir = path.abspath(path.join('..','bids'))
print(f'BIDS output dir {bidsoutdir}')

heuristic = path.abspath('heuristic.py')
print(f'Using heuristic {heuristic}')

# Each subject
allsubjdicom = glob.glob(path.join(dcmpth,'*_RC_FOUNDCOG'))

print(allsubjdicom)

for subjdicom in allsubjdicom:
    flds = path.basename(subjdicom).split('_') 
    # bids descriptor for this subject
    sub = '_'.join(flds[:2]) # removed _ (e.g., ICN_2 -> ICN2) as underscore typically splits fields in bids

    # Each session for this subject
    allsessdicom = glob.glob(path.join(subjdicom,'*'))
    allsessdicom.sort() # sessions in ascending order by time

    if not allsessdicom:
        print(f'No dicom session found for {sub}')

    for ses, sessdicom in enumerate(allsessdicom, start = 1):

        dcmtemplate = path.join(dcmpth,'{subject}_RC_FOUNDCOG',path.basename(sessdicom),'Series_*/*.dcm')
        print(f'Working on sub-{sub} ses-{ses} looking in {dcmtemplate}')

        workflow(dicom_dir_template=dcmtemplate,
            converter='dcm2niix',
            outdir=bidsoutdir,
            heuristic=heuristic,
            overwrite=True, 
            bids_options=[],
            subjs=[sub],
            session=ses, debug=True)
