# Preprocessing workflow for a single BOLD session
# The FOUNDCOG team, www.foundcog.org
# v0.0, 2021-11-08: Rhodri Cusack cusackrh@tcd.ie

import os
import json
import nipype.interfaces.fsl as fsl 
from nipype.interfaces.spm import Smooth

from nipype.interfaces.utility import IdentityInterface, Select
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.algorithms.rapidart import ArtifactDetect
import nipype.algorithms.confounds as confounds

from nipype import Workflow, Node, MapNode, Function
from bids.layout import BIDSLayout
from niworkflows.interfaces.confounds import NormalizeMotionParams
from os import path
from nipype.algorithms import confounds as ni_confounds
from nipype.interfaces.io import BIDSDataGrabber



def get_wf_bold_preproc(bids_dir):
    # Inputs, outputs, datasink
    inputnode = Node(interface=IdentityInterface(fields=['bold']), name='inputnode')

    outputnode = Node(interface=IdentityInterface(
        fields=['bold','session_mean','motion_parameters','motion_fwd']), 
        name='outputnode')
    datasink = Node(interface=DataSink(), name='datasink')

    
    # Motion correction
    #  extract reference for motion correction
    #   TODO: extract robust reference in noisy infant data?
    extract_ref = Node(interface=fsl.ExtractROI(t_size=1), iterfield='in_file', name='extractref')

    def dumpme(bold):
        print(f'***Dumping type: {type(bold)} value: {bold}')

        return bold

    def getmiddlevolume(func):
        from nibabel import load
        print(f'getmiddlevolume received {func}')
        funcfile = func
        if isinstance(func, list):
            funcfile = func[0]
        _, _, _, timepoints = load(funcfile).shape
        return int(timepoints / 2) - 1

    dumpmenode = Node(Function(function=dumpme, input_names=['bold'], output_names=['bold']), name='dumpme')

    #  MCFLIRT
    motion_correct = Node(fsl.MCFLIRT(mean_vol=True, save_plots=True,output_type='NIFTI'), name="mcflirt", iterfield=['in_file'])

    # Mean
    mean = Node(fsl.maths.MeanImage(), name='session_mean', iterfield=['in_file'])

    # Smoothing
    smooth = Node(fsl.Smooth(fwhm=8.0), name="smoothing", iterfield=['in_file'])

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


    # Create a preprocessing workflow
    preproc = Workflow(name='bold_preproc')
    # for tag in tags:
    #     preproc.connect(inputnode, tag, bdg, tag)
    preproc.connect(inputnode, 'bold', dumpmenode,  'bold')
    preproc.connect(inputnode, 'bold', mean, 'in_file')
    preproc.connect(dumpmenode, 'bold', motion_correct,  'in_file')
    preproc.connect(dumpmenode, ('bold', getmiddlevolume), extract_ref, 't_min')
    preproc.connect(dumpmenode, 'bold', extract_ref, 'in_file')
    preproc.connect(extract_ref, 'roi_file', motion_correct, 'ref_file')
    preproc.connect(motion_correct, 'out_file', smooth, 'in_file')
    #preproc.connect(motion_correct, 'out_file', mean, 'in_file')
    preproc.connect([(motion_correct, normalize_motion, [('par_file', 'in_file')])])
    preproc.connect(motion_correct, 'par_file', plot_motion, 'in_file')
    preproc.connect(normalize_motion, 'out_file', calc_fwd, 'in_file')

    preproc.connect([(plot_motion,  datasink, [('out_file', 'motion_plots')])])
    preproc.connect([(mean,  datasink, [('out_file', 'session_mean')])])
    preproc.connect([(smooth,  datasink, [('smoothed_file', 'smoothed_files')])])
    preproc.connect([(motion_correct, datasink, [('par_file', 'motion_parameters')])])
    preproc.connect([(calc_fwd, datasink, [('out_file', 'motion_fwd')] )])
    
    preproc.connect([(mean,  outputnode, [('out_file', 'session_mean')])])
    preproc.connect([(smooth,  outputnode, [('smoothed_file', 'bold')])])
    preproc.connect([(motion_correct, outputnode, [('par_file', 'motion_parameters')])])
    preproc.connect([(calc_fwd, outputnode, [('out_file', 'motion_fwd')] )])

    return preproc