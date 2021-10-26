
import os
import json
import nipype.interfaces.fsl as fsl 
from nipype.interfaces.spm import Smooth

from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.algorithms.rapidart import ArtifactDetect
import nipype.algorithms.confounds as confounds
from nipype import Workflow, Node, MapNode
from bids.layout import BIDSLayout
from niworkflows.interfaces.confounds import NormalizeMotionParams
#from fmriprep.workflows.bold.confounds import init_bold_confs_wf
#from fmriprep.workflows.bold import init_bold_hmc_wf
#from fmriprep import config
from os import path
from nipype.algorithms import confounds as ni_confounds

experiment_dir = '/projects/pi-cusackrh/HPC_18_01039/foundcog/bids'
output_dir = 'deriv'
working_dir = 'workingdir'

layout = BIDSLayout(experiment_dir)

# list of subject identifiers
subject_list = layout.get_subjects()
task_list = layout.get_tasks()
session_list = layout.get_sessions()
run_list = layout.get_runs()

# # TR of functional images
with open(path.join(experiment_dir,'task-pictures_bold.json'), 'rt') as fp:
    task_info = json.load(fp)
TR = task_info['RepetitionTime']

print(f'Subjects {subject_list}')
print(f'Sessions {session_list}')
print(f'Tasks {task_list}')
print(f'TR is {TR}')

# # Isometric resample of functional images to voxel size (in mm)
# iso_size = 4
# 

# Make a list of functional steps to do
iter_items= {'sub' : [], 'ses':[], 'task': [], 'run':[]}

# Template for func files
func_file = path.join('sub-{subject_id}', 'ses-{session}', 'func', 'sub-{subject_id}_ses-{session}_dir-AP_task-{task_name}_run-{run:03d}_bold.nii.gz')

for sub in subject_list:
    for ses in session_list:
        for task in task_list:
            for run in run_list:
                info = {'subject_id':sub, 'session':ses, 'task_name':task, 'run': run}
                target_file = func_file.format(**info)
                if path.isfile(path.join(experiment_dir, target_file)):
                    iter_items['sub'].append(sub)
                    iter_items['ses'].append(ses)
                    iter_items['task'].append(task)
                    iter_items['run'].append(run)


# Setup
omp_nthreads = 8
mem_gb = {"filesize": 1, "resampled": 1, "largemem": 1}

# MAIN WORKFLOW

# INPUT DATA
infosource = Node(IdentityInterface(fields=['subject_id', 'session', 'task_name', 'run']),
                  name="infosource")
infosource.iterables = [('subject_id', iter_items['sub']),
                        ('session', iter_items['ses']),
                        ('task_name', iter_items['task']),
                        ('run', iter_items['run']),
                        ]

infosource.synchronize = True # synchronised stepping through each of the iterable lists

# SelectFiles - to grab the data (alternativ to DataGrabber)

templates = {'func': func_file}
selectfiles = Node(SelectFiles(templates,
                               base_directory=experiment_dir),
                   name="selectfiles")

# Motion correction
#  extract reference for motion correction
#   TODO: extract robust reference in noisy infant data?
extract_ref = Node(interface=fsl.ExtractROI(t_size=1), name='extractref')

def getmiddlevolume(func):
    from nibabel import load
    funcfile = func
    if isinstance(func, list):
        funcfile = func[0]
    _, _, _, timepoints = load(funcfile).shape
    return int(timepoints / 2) - 1

#  MCFLIRT
motion_correct = Node(fsl.MCFLIRT(mean_vol=True, save_plots=True,output_type='NIFTI'), name="mcflirt")

#  Plot output
plot_motion = MapNode(
    interface=fsl.PlotMotionParams(in_source='fsl'),
    name='plot_motion',
    iterfield=['in_file'])
plot_motion.iterables = ('plot_type', ['rotations', 'translations'])

# # Summaries
calc_fwd = Node(
    interface=ni_confounds.FramewiseDisplacement(parameter_source='FSL'),
    name='calc_fwd'
)
calc_dvars = Node(
    interface=ni_confounds.ComputeDVARS(save_all=True, remove_zerovariance=True),
    name='calc_dvars'
)

# Normalize motion to SPM format
normalize_motion = Node(NormalizeMotionParams(format='FSL'),
                               name="normalize_motion")

# # 
# bold_confounds_wf = init_bold_confs_wf(mem_gb=mem_gb['largemem'],
#                                         metadata={},
#                                         regressors_all_comps=False,
#                                         regressors_dvars_th=1.5,
#                                         regressors_fd_th=0.5
#                                         )

# Datasink - creates output folder for important outputs
datasink = Node(DataSink(base_directory=experiment_dir,
                         container=output_dir),
                name="datasink")

# Create a preprocessing workflow
preproc = Workflow(name='preproc')
preproc.base_dir = path.join(experiment_dir, working_dir)

preproc.connect([(infosource, selectfiles, [('subject_id', 'subject_id'),
                                   ('session', 'session'),
                                   ('task_name', 'task_name'),
                                   ('run', 'run')])
                                   ])
preproc.connect(selectfiles, 'func', motion_correct,  'in_file')
preproc.connect(selectfiles, 'func', extract_ref, 'in_file')
preproc.connect(selectfiles, ('func', getmiddlevolume), extract_ref, 't_min')
preproc.connect(extract_ref, 'roi_file', motion_correct, 'ref_file')
preproc.connect([(motion_correct, normalize_motion, [('par_file', 'in_file')])])
preproc.connect(motion_correct, 'par_file', plot_motion, 'in_file')
preproc.connect(normalize_motion, 'out_file', calc_fwd, 'in_file')
preproc.connect([(plot_motion,  datasink, [('out_file', 'motion_plots')])])
preproc.connect([(motion_correct,  datasink, [('out_file', 'timeseries')])])
preproc.connect([(motion_correct,  datasink, [('par_file', 'motion_parameters')])])
preproc.connect([(calc_fwd, datasink, [('out_file', 'motion_fwd')] )])

# Create preproc output graph
preproc.write_graph(graph2use='colored', format='png', simple_form=True)

# Visualize the graph
from IPython.display import Image
Image(filename=path.join(preproc.base_dir, 'preproc', 'graph.png'))
# Visualize the detailed graph
preproc.write_graph(graph2use='flat', format='png', simple_form=True)
Image(filename=path.join(preproc.base_dir, 'preproc', 'graph_detailed.png'))

preproc.run()

# preproc.run(plugin='SLURMGraph', plugin_args = {'dont_resubmit_completed_jobs': True})
#'MultiProc', plugin_args={'n_procs': 8})