
import os
import json
from nipype.interfaces import ants, fsl
from nipype.interfaces.spm import Smooth

from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.algorithms.rapidart import ArtifactDetect
import nipype.algorithms.confounds as confounds
from nipype import Workflow, Node, MapNode, JoinNode, Function
from bids.layout import BIDSLayout
from niworkflows.interfaces.confounds import NormalizeMotionParams
#from fmriprep.workflows.bold.confounds import init_bold_confs_wf
#from fmriprep.workflows.bold import init_bold_hmc_wf
#from fmriprep import config
from os import path
from nipype.algorithms import confounds as ni_confounds

from wf_bold_preproc import get_wf_bold_preproc


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
iter_items= {}

# Template for func files
func_file = path.join('sub-{subject_id}', 'ses-{session}', 'func', 'sub-{subject_id}_ses-{session}_task-{task_name}_dir-AP_run-{run:03d}_bold.nii.gz')

for sub in subject_list:
    iter_items[sub]= {'ses':[], 'task': [], 'run':[]}
    for ses in session_list:
        for task in task_list:
            for run in run_list:
                info = {'subject_id':sub, 'session':ses, 'task_name':task, 'run': run}
                target_file = func_file.format(**info)
                if path.isfile(path.join(experiment_dir, target_file)):
                    iter_items[sub]['ses'].append(ses)
                    iter_items[sub]['task'].append(task)
                    iter_items[sub]['run'].append(run)


# Setup
omp_nthreads = 8
mem_gb = {"filesize": 1, "resampled": 1, "largemem": 1}

# MAIN WORKFLOW
#  different sessions/runs/tasks per subject so some work needed here
for sub, sub_items in iter_items.items():
    # INPUT DATA
    infosource = Node(IdentityInterface(fields=['subject_id', 'session', 'task_name', 'run']),
                    name="infosource")
    infosource.iterables = [('subject_id', [sub] * len(sub_items['ses']) ),    # keep subject as an iterable so cached values will not clash
                            ('session', sub_items['ses']),
                            ('task_name', sub_items['task']),
                            ('run', sub_items['run']),
                            ]

    infosource.synchronize = True # synchronised stepping through each of the iterable lists

    # SelectFiles - to grab the data (alternativ to DataGrabber)

    templates = {'func': func_file}
    selectfiles = Node(SelectFiles(templates,
                                base_directory=experiment_dir),
                    name="selectfiles")

    def postjoindump(joinedthing):
        print(f'Joined thing is {joinedthing}')

    # Gather all of bolds at end
    joinbold=JoinNode(IdentityInterface(fields=['in_file']), joinsource='infosource', joinfield='in_file', name='joinnode')
    
    # Check results
    postjoinfunctionode_inner = Node(Function(function=postjoindump, input_names=['joinedthing'], output_names=['thing']), name='postjoinfunctionnode')

    runmean = Node(fsl.maths.MeanImage(), name='runmean')
    
    
    def get_coreg_reference(in_files):
        # Pick reference for coreg - order by pref rest10, rest5, videos, pictures
        for pref in ['rest10', 'rest5', 'videos', 'pictures']:
            res = [out_file for out_file in in_files if pref in out_file]
            if (res):
                return res[0]

        # If none of the above
        return in_files[0]

    get_coreg_reference_node = Node(Function(function=get_coreg_reference, input_names=['in_files'], output_names=['reference']), name='get_coreg_reference')

    coreg_runs = Node(fsl.FLIRT(), name='coreg_runs')
    apply_xfm = Node(fsl.preprocess.ApplyXFM(), name='apply_coreg_runs')
    apply_xfm_to_mean= Node(fsl.preprocess.ApplyXFM(), name='apply_coreg_runs_to_mean')

    submean = JoinNode(ants.AverageImages(dimension=3, normalize=False),  joinsource = 'infosource', joinfield='images', name='submean')

    # Location of template file
    template = '/data/ds000114/derivatives/fmriprep/mni_icbm152_nlin_asym_09c/1mm_T1.nii.gz'
    # or alternatively template = Info.standard_image('MNI152_T1_1mm.nii.gz')

    # Registration - computes registration between subject's anatomy & the MNI template
    # antsreg = Node(ants.Registration(args='--float',
    #                             collapse_output_transforms=True,
    #                             fixed_image=template,
    #                             initial_moving_transform_com=True,
    #                             num_threads=4,
    #                             output_inverse_warped_image=True,
    #                             output_warped_image=True,
    #                             sigma_units=['vox'] * 3,
    #                             transforms=['Rigid', 'Affine', 'SyN'],
    #                             terminal_output='file',
    #                             winsorize_lower_quantile=0.005,
    #                             winsorize_upper_quantile=0.995,
    #                             convergence_threshold=[1e-06],
    #                             convergence_window_size=[10],
    #                             metric=['MI', 'MI', 'CC'],
    #                             metric_weight=[1.0] * 3,
    #                             number_of_iterations=[[1000, 500, 250, 100],
    #                                                 [1000, 500, 250, 100],
    #                                                 [100, 70, 50, 20]],
    #                             radius_or_number_of_bins=[32, 32, 4],
    #                             sampling_percentage=[0.25, 0.25, 1],
    #                             sampling_strategy=['Regular', 'Regular', 'None'],
    #                             shrink_factors=[[8, 4, 2, 1]] * 3,
    #                             smoothing_sigmas=[[3, 2, 1, 0]] * 3,
    #                             transform_parameters=[(0.1,), (0.1,),
    #                                                 (0.1, 3.0, 0.0)],
    #                             use_histogram_matching=True,
    #                             write_composite_transform=True),
    #                 name='antsreg')



    # BOLD preprocessing workflow
    bold_preproc = get_wf_bold_preproc(experiment_dir, working_dir, output_dir)

    # Base workflow
    preproc = Workflow(name='preproc')
    preproc.base_dir = path.join(experiment_dir, working_dir, output_dir)

    preproc.connect([(infosource, selectfiles, [('subject_id', 'subject_id'),
                                    ('session', 'session'),
                                    ('task_name', 'task_name'),
                                    ('run', 'run')])
                                    ])
    preproc.connect([(selectfiles, bold_preproc, [('func','inputnode.func')])])
    
    # Find session means, pick best reference and coregister all means to this one    
    preproc.connect(bold_preproc, "outputnode.func", runmean, "in_file")

    preproc.connect(runmean, "out_file", joinbold, "in_file")
    preproc.connect(joinbold, "in_file", get_coreg_reference_node, "in_files")
    
    preproc.connect(runmean, "out_file", coreg_runs, "in_file")
    preproc.connect(get_coreg_reference_node, "reference", coreg_runs, "reference")

    # Reorient runs to space of reference run
    preproc.connect(get_coreg_reference_node, "reference", apply_xfm, "reference")
    preproc.connect(bold_preproc, "outputnode.smoothed_func", apply_xfm, "in_file")
    preproc.connect(coreg_runs, "out_matrix_file",apply_xfm, "in_matrix_file")

    # Reorient means to space of reference run
    preproc.connect(get_coreg_reference_node, "reference", apply_xfm_to_mean, "reference")
    preproc.connect(runmean, "out_file", apply_xfm_to_mean, "in_file")
    preproc.connect(coreg_runs, "out_matrix_file",apply_xfm_to_mean, "in_matrix_file")

    # Mean across runs
    preproc.connect(apply_xfm_to_mean, "out_file", submean, "images")

    # GRAPHS
    # Create preproc output graph
    preproc.write_graph(graph2use='colored', format='png', simple_form=True)

    # Visualize the graph
    from IPython.display import Image
    Image(filename=path.join(preproc.base_dir, 'preproc', 'graph.png'))
    # Visualize the detailed graph
    preproc.write_graph(graph2use='flat', format='png', simple_form=True)
    Image(filename=path.join(preproc.base_dir, 'preproc', 'graph_detailed.png'))

    # RUN
    preproc.run()

    # preproc.run(plugin='SLURMGraph', plugin_args = {'dont_resubmit_completed_jobs': True})
    #'MultiProc', plugin_args={'n_procs': 8})