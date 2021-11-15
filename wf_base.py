from os import path

from nipype.interfaces.io import BIDSDataGrabber
from nipype.pipeline import Node, MapNode, Workflow, JoinNode
from nipype.interfaces.utility import Function, IdentityInterface

from bids import BIDSLayout

from wf_bold_preproc import get_wf_bold_preproc

from nipype import config
config.enable_debug_mode()

experiment_dir = path.abspath(path.join('..','bids'))
layout = BIDSLayout(root= experiment_dir, database_path = path.abspath('../bidsdatabase'))

subjlist = layout.get_subjects()

def postjoindump(joinedthing):
    print(f'Joined thing is {joinedthing}')

# Each BOLD session defined by these
for subj in subjlist:
    # Get all the bolds for this subject, and extract their tags
    bolds=layout.get(subject = subj, suffix='bold', extension='nii.gz')
    bolds=tuple([path.abspath(x.path) for x in bolds])

    # Main loop across bold runs
    mapbold = Node(IdentityInterface(fields=['bold']), name='mapbold')
    mapbold.iterables = [('bold', bolds)]
    
    # Gather all of bolds at end
    joinbold=JoinNode(IdentityInterface(fields=['bold']), joinsource='mapbold', joinfield='bold', name='joinnode')
    
    # Check results
    postjoinfunctionode_inner = Node(Function(function=postjoindump, input_names=['joinedthing'], output_names=['thing']), name='postjoinfunctionnode')

    # BOLD preprocessing workflow
    wf_bold_preproc = get_wf_bold_preproc(experiment_dir)
    wf_bold_preproc.base_dir = path.join(experiment_dir, 'working_dir')

    wf_base = Workflow(name="wf_base")
    wf_base.base_dir = path.join(experiment_dir, 'working_dir')
    wf_base.connect(mapbold, 'bold', wf_bold_preproc, f"inputnode.bold")
    wf_base.connect(wf_bold_preproc, "outputnode.bold", joinbold, "bold")
    wf_base.connect(joinbold, "bold", postjoinfunctionode_inner, "joinedthing")

    wf_base.run()