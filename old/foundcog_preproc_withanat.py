
import os
import json
import nipype.interfaces.fsl as fsl 
from nipype.interfaces.spm import Smooth

from nipype.interfaces.utility import IdentityInterface, Select
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


iso_size = 3

# Switching to relative definition of path, for operation within forked repos
experiment_dir = path.abspath(path.join('..','..','foundcog','bids'))
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

templates_anat = {'anat': path.join('sub-{subject_id}', '*', 'anat', 'sub-{subject_id}_*_T2w.nii.gz')}
selectfiles_anat = Node(SelectFiles(templates_anat,
                               base_directory=experiment_dir, force_list=True),
                   name="selectfiles_anat")

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

# Select just last anatomical
select_last_anat = Node(Select(index=[-1]), name='select_last_anat')

# Skull strip anatomy
bet_anat = Node(fsl.BET(frac=0.5,
                    robust=True,
                    output_type='NIFTI_GZ'),
                name="bet_anat")

# FAST - Image Segmentation
segmentation = Node(fsl.FAST(output_type='NIFTI_GZ'),
                number_classes=4,
                name="segmentation")

# Select WM segmentation file from segmentation output
def get_wm(files):
    return files[-1]

# Threshold - Threshold WM probability image
threshold = Node(fsl.Threshold(thresh=0.5,
                           args='-bin',
                           output_type='NIFTI_GZ'),
                name="threshold")

# FLIRT - pre-alignment of functional images to anatomical images
coreg_pre = Node(fsl.FLIRT(dof=6, output_type='NIFTI_GZ'),
                 name="coreg_pre")

# FLIRT - coregistration of functional images to anatomical images with BBR
coreg_bbr = Node(fsl.FLIRT(dof=6,
                       cost='bbr',
                       schedule=path.join(os.getenv('FSLDIR'),
                                    'etc/flirtsch/bbr.sch'),
                       output_type='NIFTI_GZ'),
                 name="coreg_bbr")

# Apply coregistration warp to functional images
applywarp = Node(fsl.FLIRT(interp='spline',
                       apply_isoxfm=iso_size,
                       output_type='NIFTI'),
                 name="applywarp")

# Apply coregistration warp to mean file
applywarp_mean = Node(fsl.FLIRT(interp='spline',
                            apply_isoxfm=iso_size,
                            output_type='NIFTI_GZ'),
                 name="applywarp_mean")

# Artifact Detection - determines outliers in functional images
art = Node(ArtifactDetect(norm_threshold=2,
                          zintensity_threshold=3,
                          mask_type='spm_global',
                          parameter_source='FSL',
                          use_differences=[True, False],
                          plot_type='svg'),
           name="art")

# Mean
mean = Node(fsl.maths.MeanImage(), name='session_mean')

# Smoothing
smooth = Node(fsl.Smooth(fwhm=8.0), name="smoothing")

#  Plot output
plot_motion = MapNode(
    interface=fsl.PlotMotionParams(in_source='fsl'),
    name='plot_motion',
    iterfield=['in_file'])
plot_motion.iterables = ('plot_type', ['rotations', 'translations'])

# # Summaries
# Normalize motion to SPM format
normalize_motion = Node(NormalizeMotionParams(format='FSL'),
                               name="normalize_motion")

calc_fwd = Node(
    interface=ni_confounds.FramewiseDisplacement(parameter_source='SPM'),   # use parameter source as SPM because these have been processed with NormalizeMotionParams, for compatability with fmriprep
    name='calc_fwd'
)
calc_dvars = Node(
    interface=ni_confounds.ComputeDVARS(save_all=True, remove_zerovariance=True),
    name='calc_dvars'
)


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
preproc.connect([(infosource, selectfiles_anat, [('subject_id', 'subject_id')])])
preproc.connect([(selectfiles_anat, select_last_anat, [('anat', 'inlist')])])
preproc.connect(selectfiles, 'func', motion_correct,  'in_file')
preproc.connect(selectfiles, 'func', extract_ref, 'in_file')
preproc.connect(selectfiles, ('func', getmiddlevolume), extract_ref, 't_min')
preproc.connect(extract_ref, 'roi_file', motion_correct, 'ref_file')
preproc.connect(motion_correct, 'out_file', smooth, 'in_file')
preproc.connect(motion_correct, 'out_file', mean, 'in_file')
preproc.connect([(motion_correct, normalize_motion, [('par_file', 'in_file')])])
preproc.connect(motion_correct, 'par_file', plot_motion, 'in_file')
preproc.connect(normalize_motion, 'out_file', calc_fwd, 'in_file')

# coreg
preproc.connect([(bet_anat, segmentation, [('out_file', 'in_files')]),
                 (segmentation, threshold, [(('partial_volume_files', get_wm),
                                             'in_file')]),
                 (bet_anat, coreg_pre, [('out_file', 'reference')]),
                 (threshold, coreg_bbr, [('out_file', 'wm_seg')]),
                 (coreg_pre, coreg_bbr, [('out_matrix_file', 'in_matrix_file')]),
                 (coreg_bbr, applywarp, [('out_matrix_file', 'in_matrix_file')]),
                 (coreg_bbr, applywarp_mean, [('out_matrix_file', 'in_matrix_file')]),
                 (bet_anat, applywarp_mean, [('out_file', 'in_file')]),
                 ])
preproc.connect(select_last_anat, 'out', bet_anat,  'in_file')
preproc.connect(bet_anat, 'out_file', coreg_bbr,  'reference')
preproc.connect(mean, 'out_file', coreg_pre,  'in_file')
preproc.connect(mean, 'out_file', coreg_bbr,  'in_file')

preproc.connect(motion_correct, 'out_file', applywarp,  'in_file')



preproc.connect([(plot_motion,  datasink, [('out_file', 'motion_plots')])])
preproc.connect([(mean,  datasink, [('out_file', 'session_mean')])])
preproc.connect([(smooth,  datasink, [('smoothed_file', 'smoothed_files')])])
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