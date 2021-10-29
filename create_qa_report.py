from enum import Enum
from  jinja2 import Template
from bids.layout import BIDSLayout
from os import path
import os
from shutil import copyfile
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from ptitprince import PtitPrince as pt

from jinja2 import Environment, FileSystemLoader, select_autoescape
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape()
)

# Absolute paths to foundcog data used for inputs
foundcog_dir = '/projects/pi-cusackrh/HPC_18_01039/foundcog'
experiment_dir = path.join(foundcog_dir,'bids')

# Relative paths used for outputs, for testing
relative_foundcog_dir = path.join('..','..','foundcog')
deriv_relative = path.join(relative_foundcog_dir,'bids','deriv')
reports_relative = path.join(relative_foundcog_dir,'reports')

if not os.path.isdir(reports_dir):
    os.mkdir(reports_dir)

# Get details from bids
layout = BIDSLayout(experiment_dir)
subject_list = layout.get_subjects()
task_list = layout.get_tasks()
session_list = layout.get_sessions()
run_list = layout.get_runs()

# Check for every possible movement parameter
individual_runs={}
fwd = pd.DataFrame()

for sub in subject_list:
    for task in task_list:
        for ses in session_list:
            for run in run_list:
                run_pth=f'_run_{run}_session_{ses}_subject_id_{sub}_task_name_{task}'
                comp_dir = path.join('motion_plots', run_pth)
                comp_fn = f'sub-{sub}_ses-{ses}_dir-AP_task-{task}_run-{run:03d}_bold_mcf.nii'
                
                src_path = path.join(deriv_relative, comp_dir, comp_fn + '_rot.png')
                if path.exists(src_path):
                    # add movement parameters to HTML report
                    dest_dir = path.join(reports_dir, comp_dir)
                    os.makedirs(dest_dir, exist_ok=True)
                    for partype in ['rot','trans']:
                        copyfile(path.join(deriv_relative, comp_dir, comp_fn + f'_{partype}.png'), path.join(dest_dir, comp_fn + f'_{partype}.png'))
                    if not sub in individual_runs:
                        individual_runs[sub] = {}
                    if not task in individual_runs[sub]:
                        individual_runs[sub][task]={}
                    if not ses in individual_runs[sub]:
                        individual_runs[sub][task][ses]={}
                    individual_runs[sub][task][ses][run]=path.join(comp_dir, comp_fn)

                    # gather framewise displacements for raincloud plots later
                    fwd_comp_dir = path.join('motion_fwd', run_pth)
                    fwd_comp_fn = f'sub-{sub}_ses-{ses}_dir-AP_task-{task}_run-{run:03d}_bold_mcf.nii'
                    fwd_pd = pd.read_csv(path.join(deriv_relative, fwd_comp_dir, 'fd_power_2012.txt'))
                    fwd_pd['id']=f'{sub}_{task}_ses-{ses}_run-{run:03d} [{len(fwd_pd.index)}]'
                    fwd = fwd.append(fwd_pd, ignore_index=True)

# Raincloud summary of FWD for each session of each subject
f, ax = plt.subplots(figsize=(12, 8))

dx="FramewiseDisplacement"; dy="id"; ort="h"

ax=pt.half_violinplot(data=fwd, palette="Set2", bw=.2,  linewidth=1,cut=0.,
                   scale="area", width=.8, inner=None,orient=ort,x=dx,y=dy)

ax=sns.stripplot(data=fwd, palette="Set2", edgecolor="white",size=2,orient=ort,
                 x=dx,y=dy,jitter=1,zorder=0)

ax=sns.boxplot(data=fwd, color="black",orient=ort,width=.15,x=dx,y=dy,zorder=10,
              showcaps=True,boxprops={'facecolor':'none', "zorder":10},
               showfliers=True,whiskerprops={'linewidth':2, "zorder":10},saturation=1)

# Finalize the figure
#ax.set(ylim=(3.5, -.7))
sns.despine(left=True)
plt.tight_layout()
plt.savefig(path.join(reports_dir,'fwd_raincloud.png'))

template = env.get_template("motion.html")
with open(path.join(reports_dir, 'motion.html'),'w') as f:
    f.write(template.render(individual_runs=individual_runs))


