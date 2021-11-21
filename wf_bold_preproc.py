
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


def get_wf_bold_preproc(experiment_dir, working_dir, output_dir):
    inputnode = Node(IdentityInterface(fields=['func']),
                  name="inputnode")

    outputnode = Node(IdentityInterface(fields=['func', 'smoothed_func']),
                  name="outputnode")
    

    preproc = Workflow(name='bold_preproc')
    preproc.base_dir = path.join(experiment_dir, working_dir, output_dir)

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
    motion_correct = Node(fsl.MCFLIRT(save_plots=True,output_type='NIFTI'), name="mcflirt")

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


    preproc.connect(inputnode, 'func', motion_correct,  'in_file')
    preproc.connect(inputnode, 'func', extract_ref, 'in_file')
    preproc.connect(inputnode, ('func', getmiddlevolume), extract_ref, 't_min')
    preproc.connect(extract_ref, 'roi_file', motion_correct, 'ref_file')
    preproc.connect(motion_correct, 'out_file', smooth, 'in_file')
    preproc.connect([(motion_correct, normalize_motion, [('par_file', 'in_file')])])
    preproc.connect(motion_correct, 'par_file', plot_motion, 'in_file')
    preproc.connect(normalize_motion, 'out_file', calc_fwd, 'in_file')
    preproc.connect([(plot_motion,  datasink, [('out_file', 'motion_plots')])])
    preproc.connect([(smooth,  datasink, [('smoothed_file', 'smoothed_files')])])
    preproc.connect([(motion_correct,  datasink, [('par_file', 'motion_parameters')])])
    preproc.connect([(calc_fwd, datasink, [('out_file', 'motion_fwd')] )])

    preproc.connect([(motion_correct, outputnode, [('out_file', 'func')] )])
    preproc.connect([(smooth, outputnode, [('smoothed_file', 'smoothed_func')] )])
    return preproc