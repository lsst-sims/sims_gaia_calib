import numpy as np

# Let's generate the calls to make all the catalogs

nstars = 532321

points = np.linspace(0,nstars, 500)

outfile = open('calls.sh', 'w')

pream = 'export LSST_HOME=~/lsst; source $LSST_HOME/loadLSST.bash ; setup sims_gaia_calib -t yoachim -t sims ; '

for i in range(points.size-1):
    print >>outfile, "%s ./make_catalog.py --start_star %i --nstars %i --workdir %s " % (pream, points[i], points[i+1]-points[i], 'cat_'+str(i))
