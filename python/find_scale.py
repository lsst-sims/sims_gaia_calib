import numpy as np
import matplotlib.pylab as plt
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LinearRegression, BayesianRidge
from lsst.sims.utils import raDec2Hpid
from lsst.utils import getPackageDir
import os
import healpy as hp
from astropy.coordinates import SkyCoord
from astropy import units as u

# Find the spatial scale that GAIA stars can be used to calibrate on

def gnomonic_project_toxy(RA1, Dec1, RAcen, Deccen):
    """
    Calculate the x/y values of RA1/Dec1 in a gnomonic projection with center at RAcen/Deccen.

    Parameters
    ----------
    RA1 : numpy.ndarray
        RA values of the data to be projected, in radians.
    Dec1 : numpy.ndarray
        Dec values of the data to be projected, in radians.
    RAcen: float
        RA value of the center of the projection, in radians.
    Deccen : float
        Dec value of the center of the projection, in radians.

    Returns
    -------
    numpy.ndarray, numpy.ndarray
        The x/y values of the projected RA1/Dec1 positions.
    """
    cosc = np.sin(Deccen) * np.sin(Dec1) + np.cos(Deccen) * np.cos(Dec1) * np.cos(RA1-RAcen)
    x = np.cos(Dec1) * np.sin(RA1-RAcen) / cosc
    y = (np.cos(Deccen)*np.sin(Dec1) - np.sin(Deccen)*np.cos(Dec1)*np.cos(RA1-RAcen)) / cosc
    return x, y

# Load up the data
ack = np.load('0_33578_gum_mag_cat.npz')
stars = ack['result_cat'].copy()
ack.close()
fn = 'g'
good = np.where(stars[fn] != 0)[0]

# Make a correction so now only the random noise is left.
filters = ['u', 'u_truncated', 'g', 'r', 'i', 'z', 'y', 'y_truncated']
for fn in filters:
    diff = stars[fn+'_noiseless'][good]-stars[fn+'_true'][good]
    stars[fn][good] -= diff

# Compute the uncertainty for each star to use as a weight.
someFilters = ['g', 'r', 'i', 'z', 'y']


bins = np.linspace(15,21, 100)

star_errs = np.zeros(bins.size-1, dtype=zip(someFilters, [float]*len(someFilters)))

for filtername in someFilters:
    i=0
    resids = stars[filtername] - stars[filtername+'_true']
    for b1, b2 in zip(bins[:-1], bins[1:]):
        good = np.where((stars[filtername+'_true'] >= b1) & (stars[filtername+'_true'] < b2))
        star_errs[filtername][i] = np.std(resids[good])
        i+=1

x,y = gnomonic_project_toxy(np.radians(stars['raj2000']), np.radians(stars['dej2000']), 
                      np.radians(340.), np.radians(27.5))
x = np.degrees(x)
y = np.degrees(y)
filtername = 'r'
good =np.where((stars[filtername] > 17) & (stars[filtername] < 20))
# OK, LSST has 15 CCDs that go over 3.5 degrees. So I want 1 bin per 0.233 deg. So ~13 bins on a 3 degree FoV
hb = plt.hexbin(x[good], y[good], gridsize=13)


