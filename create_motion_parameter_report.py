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

from numpy import genfromtxt
import numpy as np

from nipype.utils.misc import normalize_mc_params

from jinja2 import Environment, FileSystemLoader, select_autoescape
from niworkflows.interfaces.confounds import NormalizeMotionParams

def raincloud(fwd, dx,dy,ort="h"):
    f, ax = plt.subplots(figsize=(12, 8))

    ax=pt.half_violinplot(data=fwd, palette="Set2", bw=.2,  linewidth=1,cut=0.,
                    scale="area", width=.8, inner=None,orient=ort,x=dx,y=dy)
    ax=sns.stripplot(data=fwd, palette="Set2", edgecolor="white",size=2,orient=ort,
                    x=dx,y=dy,jitter=1,zorder=0)
    ax=sns.boxplot(data=fwd, color="black",orient=ort,width=.15,x=dx,y=dy,zorder=10,
                showcaps=True,boxprops={'facecolor':'none', "zorder":10},
                showfliers=True,whiskerprops={'linewidth':2, "zorder":10},saturation=1)
    # Finalize the figure
    sns.despine(left=True)
    plt.tight_layout()


# Relative paths, for use in forked repos
foundcog_dir = path.abspath(path.join('..','..','foundcog'))
experiment_dir = path.join(foundcog_dir,'bids')
deriv_dir = path.join(foundcog_dir,'bids','deriv')
reports_dir = path.join(foundcog_dir,'reports')

percentile=95

if not os.path.isdir(reports_dir):
    os.mkdir(reports_dir)

# Get details from bids
#  should use bidsdatagrabber with deriv instead?
layout = BIDSLayout(experiment_dir)
subject_list = layout.get_subjects()
task_list = layout.get_tasks()
session_list = layout.get_sessions()
run_list = layout.get_runs()

# Check for every possible movement parameter
individual_runs={}
fwd = pd.DataFrame()

for sub in subject_list:
    nrun=0
    for task in task_list:
        for ses in session_list:
            for run in run_list:
                run_pth=f'_run_{run}_session_{ses}_subject_id_{sub}_task_name_{task}'
                comp_dir = path.join('motion_parameters', run_pth)
                comp_fn = f'sub-{sub}_ses-{ses}_task-{task}_dir-AP_run-{run:03d}_bold_mcf.nii'
                
                src_path = path.join(deriv_dir, comp_dir, comp_fn + '.par')
                if path.exists(src_path):
                    # Get movement parameters into numpy array 
                    movpar = genfromtxt(src_path)
                    nscans = np.shape(movpar)[0]
                    movpar = movpar[:, [3,4,5,0,1,2]]  # reorder like SPM so translations first
                    movpar = np.abs(np.diff(movpar, axis=0))  # absolute frame to frame difference                    
                    movpar = np.percentile(movpar, percentile, axis=0) # extreme values

                    # Store in pandas dataframe
                    fwd_pd = pd.DataFrame.from_dict(
                        {f'{sub}_{task}_ses-{ses}_run-{run:03d}': movpar},
                        orient='index',
                        columns=['x','y','z','pitch','roll', 'yaw'])

                    fwd_pd['nscans'] = nscans
                    fwd_pd['task']=task
                    fwd_pd['sub']=sub
                    fwd_pd['ses']=ses
                    fwd = fwd.append(fwd_pd)

                    nrun+=1
    print(f'Subject {sub} total runs {nrun}')


fwd_awake = fwd[(fwd['task']=='pictures') | (fwd['task']=='videos')]
fwd_asleep = fwd[(fwd['task']=='rest5') | (fwd['task']=='rest10')]
print('Awake')
awake_by_sub=fwd_awake.groupby(['sub']).mean()

print(awake_by_sub)
print('Asleep')
asleep_by_sub=fwd_asleep.groupby(['sub']).mean()
print(asleep_by_sub)

# Plot up
#  translations
fig, ax= plt.subplots(nrows=1, ncols=2, sharey=True)
awake_by_sub[['x','y','z']].plot.bar(ax=ax[0])
ax[0].title.set_text('awake')
ax[0].set_ylabel(f'Translations {percentile}th percentile')
asleep_by_sub[['x','y','z']].plot.bar(ax=ax[1])
ax[1].title.set_text('asleep')
plt.savefig(f'translations_perc{percentile}.png')

#  rotations
fig, ax= plt.subplots(nrows=1, ncols=2, sharey=True)
awake_by_sub[['pitch','roll','yaw']].plot.bar(ax=ax[0])
ax[0].title.set_text('awake')
ax[0].set_ylabel(f'Rotations {percentile}th percentile')
asleep_by_sub[['pitch','roll','yaw']].plot.bar(ax=ax[1])
ax[1].title.set_text('asleep')
plt.savefig(f'rotations_perc{percentile}.png')


# videos vs. pictures
fwd_pictures = fwd[(fwd['task']=='pictures')]
fwd_videos = fwd[(fwd['task']=='videos') ]
pictures_by_sub=fwd_pictures.groupby(['sub']).mean()
videos_by_sub=fwd_videos.groupby(['sub']).mean()

#  rotations
fig, ax= plt.subplots(nrows=1, ncols=2, sharey=True)
pictures_by_sub[['pitch','roll','yaw']].plot.bar(ax=ax[0])
ax[0].title.set_text('pictures')
ax[0].set_ylabel(f'Rotations {percentile}th percentile')
videos_by_sub[['pitch','roll','yaw']].plot.bar(ax=ax[1])
ax[1].title.set_text('videos')
plt.savefig(f'rotations_videosvspictures_perc{percentile}.png')



# nscans videos vs. pictures
fwd_pictures = fwd[(fwd['task']=='pictures')]
fwd_videos = fwd[(fwd['task']=='videos') ]
pictures_by_sub=fwd_pictures.groupby(['sub']).sum()
videos_by_sub=fwd_videos.groupby(['sub']).sum()

#  rotations
fig, ax= plt.subplots(nrows=1, ncols=2, sharey=True)
pictures_by_sub[['nscans']].plot.bar(ax=ax[0])
ax[0].title.set_text('pictures')
ax[0].set_ylabel(f'# scans')
videos_by_sub[['nscans']].plot.bar(ax=ax[1])
ax[1].title.set_text('videos')
plt.savefig(f'nscans_videosvspictures.png')
