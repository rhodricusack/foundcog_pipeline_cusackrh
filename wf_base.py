
import os
import json
from nipype.interfaces import ants, fsl
from nipype.interfaces.spm import Smooth

from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.io import SelectFiles, DataSink, BIDSDataGrabber
from nipype.algorithms.rapidart import ArtifactDetect
import nipype.algorithms.confounds as confounds
from nipype import Workflow, Node, MapNode, JoinNode, Function
from bids.layout import BIDSLayout
from niworkflows.interfaces.confounds import NormalizeMotionParams



from os import path
from nipype.algorithms import confounds as ni_confounds

from wf_bold_preproc import get_wf_bold_preproc

from nipype import config
config.enable_debug_mode()

# Switching to relative definition of path, for operation within forked repos
experiment_dir = path.abspath(path.join('..','..','foundcog','bids'))
output_dir = 'deriv'

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

    working_dir = f'workingdir/{sub}'
    output_dir = f'deriv'

    # INPUT DATA
    infosource_sub = Node(IdentityInterface(fields=['subject_id']), name="infosource_sub")
    infosource_sub.iterables = [('subject_id', [sub])]    

    infosource = Node(IdentityInterface(fields=['session', 'task_name', 'run']),
                    name="infosource")
    infosource.iterables = [('session', sub_items['ses']),('task_name', sub_items['task']),
                            ('run', sub_items['run']),
                            ]

    infosource.synchronize = True # synchronised stepping through each of the iterable lists

    # SelectFiles - to grab the data (alternativ to DataGrabber)
    templates = {'func': func_file}
    selectfiles = Node(SelectFiles(templates,
                                base_directory=experiment_dir),
                    name="selectfiles")

    # Datasink - creates output folder for important outputs
    datasink = Node(DataSink(base_directory=experiment_dir,
                            container=output_dir),
                    name="datasink")

    # Distortion correction using topup
    join_fmap = JoinNode(IdentityInterface(fields = ['subject']), name='join_fmap', joinsource='infosource', joinfield='subject')
    bg_fmap = Node(BIDSDataGrabber(fields=['subject', 'session'], base_dir=experiment_dir, database_path=path.abspath(path.join('..','bidsdatabase'))), iterables=('session',session_list), name='bg_fmap') 
    bg_fmap.inputs.output_query= {'fmap': {'datatype':'fmap', "extension": ["nii", ".nii.gz"]}}
    bg_fmap.raise_on_empty=False
    hmc_fmaps = MapNode(fsl.MCFLIRT(), iterfield='in_file', name='hmc_fmaps')
    mean_fmaps = MapNode(fsl.maths.MeanImage(), iterfield='in_file', name='mean_fmaps')
    merge_fmaps = Node(fsl.Merge(dimension='t'), name='merge_fmaps')

    templates = {'func': func_file}
    selectfiles = Node(SelectFiles(templates,
                                base_directory=experiment_dir),
                    name="selectfiles")

    # Pick the output from the topup run corresponding to the right session
    def select_by_session(session, applytopup_method, out_fieldcoef, out_movpar, out_enc_file):
        sessind = int(session)-1
        print("Session index %d"%sessind)
        return applytopup_method[sessind], out_fieldcoef[sessind], out_movpar[sessind],out_enc_file[sessind]

    def postjoindump(joinedthing):
        print(f'Joined thing is {joinedthing}')

    # Gather all of bolds at end
    joinbold=JoinNode(IdentityInterface(fields=['in_file']), joinsource='infosource', joinfield='in_file', name='joinnode')
    
    runmean = Node(fsl.maths.MeanImage(), name='runmean')
    
    
    def get_coreg_reference(in_files):
        print(f'get_coreg_reference received {in_files}')
        # Pick reference for coreg - order by pref rest10, rest5, videos, pictures
        for pref in ['rest10', 'rest5', 'videos', 'pictures']:
            res = [out_file for out_file in in_files if pref in out_file]
            if (res):
                return res[0]

        # If none of the above
        return in_files[0]

    def select_fmaps(in_files):
        import nibabel as nib
        import json
        import os
        import numpy as np

        remap={'i':'x', 'i-':'x-', 'j':'y', 'j-':'y-', 'k':'z', 'k-':'z-'}
        # Need affines
        ahs={}
        encoding_direction={}
        readout_times={}
        for fmap in in_files:
            affine = np.round(nib.load(fmap).affine,decimals=3)
            print(fmap)
            print(affine)
            affine.flags.writeable = False
            ah = hash(affine.data.tobytes()) # hash of affine matrix used as key
            if not ah in ahs:
                ahs[ah]=[]
                readout_times[ah]=[]
                encoding_direction[ah]=[]
            ahs[ah].append(fmap)


            fmap_s = os.path.splitext(fmap)
            if fmap_s[1]=='.gz':
                fmap_s = os.path.splitext(fmap_s[0])
            with open( fmap_s[0] + '.json', 'r') as f:
                fmap_json = affine = json.load(f)
                readout_times[ah].append(fmap_json['EffectiveEchoSpacing'])
                encoding_direction[ah].append(remap[fmap_json['PhaseEncodingDirection']])
        
        longest_key = max(ahs, key= lambda x: len(set(ahs[x])))

        print(ahs)
        # TODO: Need to adjust so that session-specific fieldmaps are used
        if len(ahs[longest_key])<2:
            ahs={'all': [x for k,v in ahs.items() for x in v ]} 
            encoding_direction={'all': [x for k,v in encoding_direction.items() for x in v ]} 
            readout_times={'all': [x for k,v in readout_times.items()  for x in v]} 
            longest_key='all'

        # if encoding_direction[longest_key][0][0]==encoding_direction[longest_key][1][0]:
        #     applytopup_method='lsr'
        # else:
        #     applytopup_method='jac'

        applytopup_method='jac'

        print(f'Affines {ahs} longest is {longest_key} encoding directions {encoding_direction[longest_key]} readout times {readout_times[longest_key]}')
        return ahs[longest_key], encoding_direction[longest_key], readout_times[longest_key], applytopup_method


    select_fmaps_node = Node(Function(function=select_fmaps, input_names=['in_files'], output_names=['out_files', 'encoding_direction', 'readout_times', 'applytopup_method']), name='select_fmaps')
    topup = Node(fsl.TOPUP(), name='topup')
    select_by_session_node = JoinNode(
                                Function(function=select_by_session, 
                                    input_names=["session", 'applytopup_method', "out_fieldcoef", "out_movpar", "out_enc_file"], 
                                    output_names=['applytopup_method', "out_fieldcoef", "out_movpar", "out_enc_file"]),
                                joinsource='bg_fmap', joinfield=['applytopup_method', "out_fieldcoef", "out_movpar", "out_enc_file"],
                                name='select_by_session_node')

    applytopup = Node(fsl.ApplyTOPUP(), name='applytopup')

    get_coreg_reference_node = Node(Function(function=get_coreg_reference, input_names=['in_files'], output_names=['reference']), name='get_coreg_reference')

    coreg_runs = Node(fsl.FLIRT(), name='coreg_runs')
    apply_xfm = Node(fsl.preprocess.ApplyXFM(), name='apply_coreg_runs')
    apply_xfm_to_mean= Node(fsl.preprocess.ApplyXFM(), name='apply_coreg_runs_to_mean')

    submean = JoinNode(ants.AverageImages(dimension=3, normalize=False),  joinsource = 'infosource', joinfield='images', name='submean')

    
    # Location of template file
    template = '/projects/pi-cusackrh/HPC_18_01039/cusackrh/foundcog/templates/nihpd_asym/nihpd_asym_02-05_t2w.nii'
    # or alternatively template = Info.standard_image('MNI152_T1_1mm.nii.gz')

    # AFFINE registration
    flirt_to_template = Node(fsl.FLIRT(bins=640, cost_func='mutualinfo', dof=12, reference=template), name='flirt')

    # BOLD preprocessing workflow

    bold_preproc = get_wf_bold_preproc(experiment_dir, working_dir, output_dir)

    # Base workflow
    preproc = Workflow(name='preproc')
    preproc.base_dir = path.join(experiment_dir, working_dir, output_dir)

    preproc.connect([(infosource_sub, infosource, [('subject_id', 'subject_id')]),
                                    ])

    preproc.connect([(infosource, selectfiles, [('subject_id', 'subject_id'),
                                    ('session', 'session'),
                                    ('task_name', 'task_name'),
                                    ('run', 'run')])
                                    ])
    preproc.connect([(infosource, join_fmap, [('subject_id', 'subject')])])

    # Calculate PE polar distortion correction field using topup
    # This will iterate for the two sessions
    preproc.connect([(join_fmap, bg_fmap, [('subject', 'subject')])])

    preproc.connect([(bg_fmap, select_fmaps_node, [('fmap', 'in_files')])])
    preproc.connect([(select_fmaps_node, hmc_fmaps, [('out_files', 'in_file')])])
    preproc.connect([(hmc_fmaps, mean_fmaps, [('out_file', 'in_file')])])
    preproc.connect([(mean_fmaps, merge_fmaps, [('out_file', 'in_files')])])
    preproc.connect([(select_fmaps_node, topup, [('readout_times', 'readout_times')])])
    preproc.connect([(select_fmaps_node, topup, [('encoding_direction', 'encoding_direction')])])
    preproc.connect([(merge_fmaps, topup, [('merged_file', 'in_file')])])
    
    preproc.connect([(selectfiles, bold_preproc, [('func','inputnode.func')])])
    
    # Apply topup
    preproc.connect(bold_preproc, "outputnode.func", applytopup, "in_files")
    
    # Join the fieldmaps processed for the each of the two sessions 
    #  and then pick the fieldmap from the session that matches the current file
    preproc.connect(infosource, "session", select_by_session_node, "session")
    preproc.connect(topup, "out_fieldcoef", select_by_session_node, "out_fieldcoef")
    preproc.connect(topup, "out_movpar", select_by_session_node, "out_movpar")
    preproc.connect(topup, "out_enc_file", select_by_session_node, "out_enc_file")
    preproc.connect(select_fmaps_node, "applytopup_method", select_by_session_node, "applytopup_method")
    
    # Pass this to applytopup
    preproc.connect(select_by_session_node, "out_fieldcoef", applytopup, "in_topup_fieldcoef")
    preproc.connect(select_by_session_node, "out_movpar", applytopup, "in_topup_movpar")
    preproc.connect(select_by_session_node, "out_enc_file", applytopup, "encoding_file")
    preproc.connect(select_by_session_node, "applytopup_method", applytopup, "method")


    # Find session means, pick best reference and coregister all means to this one    
    preproc.connect(applytopup, "out_corrected", runmean, "in_file")

    preproc.connect(runmean, "out_file", joinbold, "in_file")
    preproc.connect(joinbold, "in_file", get_coreg_reference_node, "in_files")
    
    preproc.connect(runmean, "out_file", coreg_runs, "in_file")
    preproc.connect(get_coreg_reference_node, "reference", coreg_runs, "reference")

    # Reorient runs to space of reference run
    preproc.connect(get_coreg_reference_node, "reference", apply_xfm, "reference")
    preproc.connect(applytopup, "out_corrected", apply_xfm, "in_file")
    preproc.connect(coreg_runs, "out_matrix_file",apply_xfm, "in_matrix_file")

    # Reorient means to space of reference run
    
    preproc.connect(get_coreg_reference_node, "reference", apply_xfm_to_mean, "reference")
    preproc.connect(runmean, "out_file", apply_xfm_to_mean, "in_file")
    preproc.connect(coreg_runs, "out_matrix_file",apply_xfm_to_mean, "in_matrix_file")

    # Mean across runs
    preproc.connect(apply_xfm_to_mean, "out_file", submean, "images")

    # preproc.connect(submean, "output_average_image", antsreg, "moving_image")
    preproc.connect(submean, "output_average_image", flirt_to_template, "in_file")
    preproc.connect(flirt_to_template, "out_file", datasink, "submean_affineflirt")
    preproc.connect(flirt_to_template, "out_matrix_file", datasink, "submean_affineflirt_matrix")



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
    
    # Single threaded?
    # preproc.run()
 
    # Or SLURM?
    preproc.run(plugin='SLURMGraph', plugin_args = {'dont_resubmit_completed_jobs': True})
    