from os import path

from nipype.pipeline import Node, MapNode, Workflow, JoinNode
from nipype.interfaces.utility import Function, IdentityInterface

def dumpme(functionthing,functionouterthing):
    print(f'Function outerthing is {functionouterthing} and thing is {functionthing} j{functionouterthing}-{functionthing}')
    return (f'j{functionouterthing}-{functionthing}')

def postjoindump(joinedthing):
    print(f'Joined thing is {joinedthing}')

inputnode = Node(IdentityInterface(fields=['outerthing']), iterables=('outerthing', ('rc','ab')),  name='inputnode')

inputnode_inner = Node(IdentityInterface(fields=['innerthing','outerthing']), iterables=[('innerthing',(1,2,3))], name='inputnode_inner')

functionnode_inner = Node(Function(function=dumpme, input_names=['functionthing','functionouterthing'], output_names=['thing']), name='functionnode')

joinnode_inner=JoinNode(IdentityInterface(fields=['innerthings']), joinsource='inputnode_inner', joinfield='innerthings', name='joinnode')

postjoinfunctionode_inner = Node(Function(function=postjoindump, input_names=['joinedthing'], output_names=['thing']), name='postjoinfunctionnode')


wf_base = Workflow(name="wf_base")
wf_base.connect(inputnode, "outerthing", inputnode_inner, "outerthing")
wf_base.connect(inputnode_inner, "innerthing", functionnode_inner, "functionthing")
wf_base.connect(inputnode_inner, "outerthing", functionnode_inner, "functionouterthing")
wf_base.connect(functionnode_inner, "thing", joinnode_inner, "innerthings")
wf_base.connect(joinnode_inner, "innerthings", postjoinfunctionode_inner, "joinedthing")
wf_base.run()