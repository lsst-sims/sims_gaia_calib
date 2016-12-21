import numpy as numpy
from gaia_spec import *

# make_response_func(magnorm=16., filename='starSED/wDs/bergeron_14000_85.dat_14200.gz',
                      # savefile='gaia_response.npz', noise=1, count_min=8.,
                      # bluecut=700., redcut=650):


filenames = ['km40_4000.fits_g15_4000.gz',
             'km05_5000.fits_g00_5000.gz',
             'km10_6000.fits_g20_6000.gz',
             'km25_7000.fits_g25_7000.gz',
             'kp01_8000.fits_g40_8000.gz',
             'kp05_9000.fits_g40_9000.gz',
             'kp01_10000.fits_g45_10000.gz']
teffs = [4000,5000,6000,7000,8000,9000,10000]


for fn, teff in zip(filenames, teffs):
    make_response_func(magnorm=10, filename='starSED/kurucz/'+fn, savefile='gaia_response_%i.npz' %teff, noise=0)

