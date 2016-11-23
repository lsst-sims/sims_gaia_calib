import numpy as np

import lsst.sims.photUtils.Sed as Sed
import lsst.sims.photUtils.Bandpass as Bandpass
from gaia_spec import *
import copy

# let's look at the magnitude of things



response = gaia_response(restore_file='gaia_response.npz')
# response = gaia_response(restore_file='gaia_response_nonoise.npz')


filename = 'starSED/wDs/bergeron_14000_85.dat_14200.gz'
imsimBand = Bandpass()
imsimBand.imsimBandpass()

sed_dir = getPackageDir('sims_sed_library')
filepath = os.path.join(sed_dir, filename)
wd = Sed()
wd.readSED_flambda(filepath)
magnorm = 16
fNorm = wd.calcFluxNorm(magnorm, imsimBand)
wd.multiplyFluxNorm(fNorm)

throughPath = os.path.join(getPackageDir('throughputs'), 'baseline')
lsstKeys = ['u', 'g', 'r', 'i', 'z', 'y']
# lsstKeys = ['r']
bps = {}
for key in lsstKeys:
    bp = np.loadtxt(os.path.join(throughPath, 'total_'+key+'.dat'),
                    dtype=zip(['wave', 'trans'], [float]*2))
    bpTemp = Bandpass()
    good = np.where(bp['trans'] > 0.)
    bpTemp.setBandpass(bp['wave'], bp['trans'], wavelen_min=bp['wave'][good].min(),
                       wavelen_max=bp['wave'][good].max())
    bps[key] = bpTemp

# Generate a GAIA observation
gaia_obs = SED2GAIA(wd)

# Read it in as an SED object
final_sed = ulysses2SED(data=gaia_obs, noisy=False, response=response)
print 're-binned mag, orignal mag, diff'
for key in lsstKeys:
    print key, final_sed.calcMag(bps[key]), wd.calcMag(bps[key]), \
        final_sed.calcMag(bps[key])-wd.calcMag(bps[key])


