import numpy as np
import glob 
import os

# Let's see if we can package up all the kuruz models

# Pulled all the models from
# http://www.stsci.edu/science/starburst/Kurucz.html

def name_parse(filename):
    """
    Return the teff, logg, feH for the filename
    """

    fn = filename.replace('.dat', '')
    fn = fn.replace('t', '')
    fn = fn.replace('g', ' ')
    fn = fn.replace('p', ' ')
    fn = fn.replace('m', ' -')
    teff, logg, feH = fn.split(' ')
    teff = float(teff)
    logg = float(logg)/10.
    feH = float(feH)/10.
    return teff, logg, feH




files = glob.glob('/Users/yoachim/Scratch/Kurucz/*.dat')

names = ['wave', 'flux']
types = [float, float]
temp = np.loadtxt(files[0], dtype=zip(names, types))
wave = temp['wave']

stellar_fluxes = np.zeros((len(files), temp.size), dtype=float)
properties = np.zeros(len(files), dtype=zip(['teff', 'logg', 'feH'], [float]*3))
teffs = []
loggs = []
feHs = []


for i, filename in enumerate(files):
    temp = np.loadtxt(filename, dtype=zip(names, types))
    stellar_fluxes[i,:] = temp['flux']
    if not np.array_equal(temp['wave'], wave):
        import pdb ; pdb.set_trace()
    n1,n2,n3 = name_parse(os.path.split(filename)[1])
    properties['teff'][i] = n1
    properties['logg'][i] = n2
    properties['feH'][i] = n3


# Units are Angstroms for wavelengths and erg/s/cm/cm/A for fluxes

# Let's convert to nm 
wave = wave/10.
stellar_fluxes = stellar_fluxes*10.


np.savez('Kurucz_models.npz', stellar_fluxes=stellar_fluxes, wave=wave, properties=properties)




