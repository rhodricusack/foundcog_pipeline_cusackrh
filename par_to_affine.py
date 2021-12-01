import numpy as np
import sys

args=sys.argv[1:]
if len(args)<7:
    print('Requires at least 6 arguments')
    exit()

p=[np.double(x) for x in args]

t=[ [1,0,0,p[0]], [0,1,0,p[1]], [0,0,1,p[2]], [0,0,0,1]]
r1=np.array([[1,0,0,0], [0,np.cos(p[3]), np.sin(p[3]),0], [0,-np.sin(p[3]), np.cos(p[3]),0], [0,0,0,1]])
r2=[[np.cos(p[4]),0,np.sin(p[4]),0], [0,1,0,0], [-np.sin(p[4]),0,np.cos(p[4]),0], [0,0,0,1]]
r3=[[np.cos(p[5]), np.sin(p[5]), 0,0], [-np.sin(p[5]), np.cos(p[5]),0,0], [0,0,1,0], [0,0,0,1]]

mat=t@r1@r2@r3
for row in mat:
    print(' '.join([str(val) for val in row]))

