import numpy as np
from lsst.sims.photUtils import Sed, Bandpass, cache_LSST_seds, read_close_Kurucz
import os
from lsst.utils import getPackageDir


def lsst_filters():
    throughPath = os.path.join(getPackageDir('throughputs'), 'baseline')
    lsstKeys = ['u', 'g', 'r', 'i', 'z', 'y']
    bps = {}
    for key in lsstKeys:
        bp = np.loadtxt(os.path.join(throughPath, 'total_'+key+'.dat'),
                        dtype=zip(['wave', 'trans'], [float]*2))
        bpTemp = Bandpass()
        good = np.where(bp['trans'] > 0.)
        bpTemp.setBandpass(bp['wave'], bp['trans'], wavelen_min=bp['wave'][good].min(),
                           wavelen_max=bp['wave'][good].max())
        bps[key] = bpTemp
    return bps


def stubb_fitlers(wave_min=350., wave_max=1050):
    """
    Define some narrow filters that overlap LSST u and y, and are in GAIA overlap.
    """
    throughPath = os.path.join(getPackageDir('throughputs'), 'baseline')
    bps = {}
    lsstKeys = ['u', 'y']
    bps = {}
    for key in lsstKeys:
        bp = np.loadtxt(os.path.join(throughPath, 'total_'+key+'.dat'),
                        dtype=zip(['wave', 'trans'], [float]*2))
        bpTemp = Bandpass()
        good = np.where((bp['trans'] > 0.) & (bp['wave'] > wave_min) & (bp['wave'] < wave_max))
        bpTemp.setBandpass(bp['wave'], bp['trans'], wavelen_min=bp['wave'][good].min(),
                           wavelen_max=bp['wave'][good].max())
        bps[key+'_truncated'] = bpTemp
    return bps


# Load up the cached spectra
sed, pd = read_close_Kurucz(6000, 0., 4.4)
a_x, b_x = sed.setupCCMab()


# What extinctions do we want to use
Avs = np.linspace(0., 0.8, 9)

# bandpasses
bps = lsst_filters()
bps.update(stubb_fitlers())


result = []
for i, filename in enumerate(sed.param_combos['filename'][0:100]):
    for Av in Avs:
        sed.readSED_flambda(filename)
        sed.addCCMDust(a_x, b_x, A_v=Av)
        mags = {}
        for filtername in bps:
            mags[filtername] = sed.calcMag(bps[filtername])
        result.append([mags['u_truncated']-mags['g'], mags['u']-mags['g'], mags['g']-mags['r'],
                      mags['r']-mags['i'], mags['i']-mags['z'], mags['z']-mags['y'],
                      mags['z']-mags['y_truncated']])

# OK, then I can use scipy.interpolate.LinearNDInterpolator to make my interpolation engine. 

# XXX--next step, make sure my stubb filters actually work. Then I think I can start running and generate my catalog.


