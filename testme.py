from os import path

from nipype.pipeline import Node, MapNode, Workflow, JoinNode
from nipype.interfaces.utility import Function, IdentityInterface

def dumpme(functionthing,functionouterthing):
    print(f'Function outerthing is {functionouterthing} and thing is {functionthing} j{functionouterthing}-{functionthing}')
    return (f'j{functionouterthing}-{functionthing}')

def postjoindump(joinedthing):
    print(f'Joined thing is {joinedthing}')

inputnode = Node(IdentityInterface(fields=['outerthing']), iterables=('outerthing', ('rc','ab')),  name='inputnode')

mapbold = Node(IdentityInterface(fields=['outerthing','innerthing']), iterables=[('innerthing',(1,2,3))], name='mapbold')

inputnode_inner = Node(IdentityInterface(fields=['innerthing','outerthing']), name='inputnode')

functionnode_inner = Node(Function(function=dumpme, input_names=['functionthing','functionouterthing'], output_names=['thing']), name='functionnode')

outputnode_inner = Node(IdentityInterface(fields=['thing']), name='outputnode')

joinnode_inner=JoinNode(IdentityInterface(fields=['innerthings']), joinsource='mapbold', joinfield='innerthings', name='joinnode')

postjoinfunctionode_inner = Node(Function(function=postjoindump, input_names=['joinedthing'], output_names=['thing']), name='postjoinfunctionnode')


wf_inner = Workflow(name='wf_inner')
wf_inner.connect(inputnode_inner, "innerthing", functionnode_inner, "functionthing")
wf_inner.connect(inputnode_inner, "outerthing", functionnode_inner, "functionouterthing")
wf_inner.connect(functionnode_inner, "thing", outputnode_inner, 'thing')

wf_base = Workflow(name="wf_base")
wf_base.connect(inputnode, "outerthing", mapbold, 'outerthing')
wf_base.connect(mapbold, 'outerthing', wf_inner, "inputnode.outerthing")
wf_base.connect(mapbold, 'innerthing', wf_inner, "inputnode.innerthing")
wf_base.connect(wf_inner, "outputnode.thing", joinnode_inner, "innerthings")
wf_base.connect(joinnode_inner, "innerthings", postjoinfunctionode_inner, "joinedthing")
wf_base.run()