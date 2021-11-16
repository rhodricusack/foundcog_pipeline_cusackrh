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
allsubjdicom = glob.glob(path.join(dcmpth,'IRC_9_RC_FOUNDCOG'))

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
