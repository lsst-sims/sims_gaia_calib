import matplotlib.pylab as plt
from lsst.sims.catalogs.db import CatalogDBObject
from lsst.sims.catUtils.baseCatalogModels import *
from lsst.sims.catUtils.exampleCatalogDefinitions import *
import numpy as np
from lsst.sims.utils import ObservationMetaData
import lsst.sims.photUtils.Sed as Sed
import lsst.sims.photUtils.Bandpass as Bandpass
from lsst.sims.photUtils import calcMagError_m5, PhotometricParameters
import lsst.sims.maf.db as db



from lsst.sims.photUtils import Sed, Bandpass
from lsst.utils import getPackageDir
from lsst.sims.utils import defaultSpecMap
import os
import subprocess
import glob
import copy

# ssh -L 51433:fatboy.phys.washington.edu:1433 gateway.astro.washington.edu

def call_ulysses(outdir='./output', wavefile='tempWave.dat',
                 specfile='temp_spectra.dat', noise=0):
    """
    wrapper to call ulysses .jar file
    """
    ulPath = '/Users/yoachim/ulysses/'
    call = 'java -Dlog4j.configuration=file:%sconf/logging.properties' % ulPath
    call += ' -Dulysses.configuration=file:%sconf/ulysses.properties' % ulPath
    call += ' -jar %sdist/ulysses.jar -f "%s"' % (ulPath, specfile)
    call += ' -w %s -conversion 1 -inputIndivFile -unnormalized -o %s' % (wavefile, outdir)
    if noise > 0:
        call += ' -n %i' % noise

    subprocess.call(call, shell=True)

# java -Dlog4j.configuration=file:/Users/yoachim/ulysses/conf/logging.properties -Dulysses.configuration=file:/Users/yoachim/ulysses/conf/ulysses.properties -jar ~/ulysses/dist/ulysses.jar --help


def readSpec(specfile):
    with open(specfile) as f:
        lines = f.readlines()
    keys = lines[-2][2:-1].replace(' ', '').split('|')

    values = lines[-1].split('|')
    types = [str, int, int]
    types.extend([float]*13)
    spec = {}
    for i, key in enumerate(keys):
        if i == 0:
            spec[key] = values[i]
        else:
            try:
                spec[key] = np.fromstring(values[i], sep=' ', dtype=types[i])
            except: 
                import pdb ; pdb.set_trace()
    return spec

def read_ulysses(dir='output', wavefile='Ulysses_GaiaBPRP_meanSpecWavelength.txt', 
                 specfile='Ulysses_GaiaBPRP_noiseFreeSpectra.txt', noiseRoot='Ulysses_GaiaBPRP_noisyPhotSpec'):
    """
    
    """
    with open(os.path.join(dir,wavefile)) as f:
        lines = f.readlines()
    BP, RP = lines[-1][:-1].split('|')
    BP = np.fromstring(BP, sep=' ')
    RP = np.fromstring(RP, sep=' ')
    
    spec = readSpec(os.path.join(dir, specfile))

    noiseSpecs = glob.glob(dir+'/'+noiseRoot+'*')
    noisySpec = []
    for filename in noiseSpecs:
        noisySpec.append(readSpec(filename))

    return {'BP_wave': BP, 'RP_wave': RP, 'noiseFreeSpec': spec, 'noisySpec': noisySpec}


def SED2GAIA(sed, noise=1):
    """
    Take an LSST Sed and observe it with Gaia
    """
    tempFile = open('temp_spectra.dat', 'w')
    tempWave = open('tempWave.dat', 'w')
    good = np.where((sed.flambda > 1e-40) & (sed.wavelen > 300) & (sed.wavelen < 1400))
    # XXX-might need to convert units to get flux right.
    for w, fl in zip(sed.wavelen[good], sed.flambda[good]):
        print >>tempFile, '%e' % (fl)
        print >> tempWave, '%f' % w
    tempFile.close()
    tempWave.close()
    call_ulysses(noise=noise)
    result = read_ulysses()
    return result


def make_response_func(magnorm=16., filename='starSED/wDs/bergeron_14000_85.dat_14200.gz'):
    """
    Declare some stars as "standards" and build a simple GAIA response function?

    Multiply GAIA observations by response function to get spectra in flambda units.
    """
    imsimBand = Bandpass()
    imsimBand.imsimBandpass()

    sed_dir = getPackageDir('sims_sed_library')
    filepath = os.path.join(sed_dir, filename)
    wd = Sed()
    wd.readSED_flambda(filepath)
    fNorm = wd.calcFluxNorm(magnorm, imsimBand)
    wd.multiplyFluxNorm(fNorm)
    red_wd = copy.copy(wd)
    blue_wd = copy.copy(wd)
    gaia_obs = SED2GAIA(wd)
    red_wd.resampleSED(wavelen_match = gaia_obs['RP_wave'])
    blue_wd.resampleSED(wavelen_match = gaia_obs['BP_wave'])
    red_response = red_wd.flambda / gaia_obs['noisySpec'][0]['RPNoisySpec']
    blue_response = blue_wd.flambda / gaia_obs['noisySpec'][0]['BPNoisySpec']

    # XXX check the mags of the original WD and the blue and red WD. 


    import pdb ; pdb.set_trace()

    # return {'RP_response': , 'BP_response': , 'RP_wave': , 'BP_wave': }



if __name__=="__main__":
    # ok, let's see if we can load up a spectrum, scale it properly, and then make some GAIA spectra

    make_response_func()

"""
    ra = 0.  # Degrees
    dec = 0.  # Degrees
    boundLength = 1.
    dbobj = CatalogDBObject.from_objid('allstars')
    obs_metadata = ObservationMetaData(boundType='circle', pointingRA=ra,
                                       pointingDec=dec, boundLength=boundLength, mjd=5700)
    t = dbobj.getCatalog('ref_catalog_star', obs_metadata=obs_metadata)

    constraint = 'rmag < 18 and rmag > 15'

    chunks = t.db_obj.query_columns(colnames=['magNorm', 'rmag', 'sedfilename', 'ebv'],
                                    obs_metadata=obs_metadata,constraint=constraint,
                                    chunk_size=1000000)

    for chunk in chunks:
        catalog = chunk

    sed_dir = getPackageDir('sims_sed_library')

    dex = 0 # index of the star whose spectrum we are generating
    imsimBand = Bandpass()
    imsimBand.imsimBandpass()
    ss = Sed()
    sed_name = os.path.join(sed_dir, defaultSpecMap[catalog['sedfilename'][dex]])
    ss.readSED_flambda(sed_name)
    fNorm = ss.calcFluxNorm(catalog['magNorm'][dex], imsimBand)
    ss.multiplyFluxNorm(fNorm)
    a_x, b_x = ss.setupCCMab()
    ss.addCCMDust(a_x, b_x, ebv=catalog['ebv'][dex])

    # now, output this to a text file, 
    tempFile = open('temp_spectra.dat', 'w')
    tempWave = open('tempWave.dat', 'w')
    good = np.where( (ss.flambda > 1e-40) & (ss.wavelen > 300) & (ss.wavelen < 1400))
    # XXX-might need to convert units to get flux right.
    for w, fl in zip(ss.wavelen[good], ss.flambda[good]):
        print >>tempFile, '%e' % (fl)
        print >> tempWave, '%f' % w
    tempFile.close()
    tempWave.close()

    call_ulysses(noise=3)

    result = read_ulysses()

"""

