import matplotlib.pylab as plt
# from lsst.sims.catalogs.db import CatalogDBObject
# from lsst.sims.catUtils.baseCatalogModels import *
# from lsst.sims.catUtils.exampleCatalogDefinitions import *
import numpy as np
from lsst.sims.utils import ObservationMetaData
from lsst.sims.photUtils import calcMagError_m5, PhotometricParameters
import lsst.sims.maf.db as db

from lsst.sims.photUtils import Sed, Bandpass, cache_LSST_seds
from lsst.utils import getPackageDir
from lsst.sims.utils import defaultSpecMap, angularSeparation, equatorialFromGalactic
import os
import subprocess
import glob
import copy
import sys

# ssh -L 51433:fatboy.phys.washington.edu:1433 gateway.astro.washington.edu


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


def stubb_fitlers(wave_min=375., wave_max=1050):
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



def call_ulysses(workdir='./output', wavefile='tempWave.dat',
                 specfile='temp_spectra.dat', noise=0):
    """
    wrapper to call ulysses .jar file
    """
    ulPath = '/Users/yoachim/ulysses/'
    call = 'java -Dlog4j.configuration=file:%sconf/logging.properties' % ulPath
    call += ' -Dulysses.configuration=file:%sconf/ulysses.properties' % ulPath
    call += ' -jar %sdist/ulysses.jar -f "%s"' % (ulPath, specfile)
    call += ' -w %s -conversion 1 -inputIndivFile -unnormalized -o %s > gaia.log' % (wavefile, workdir)
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
            spec[key] = np.fromstring(values[i], sep=' ', dtype=types[i])

    return spec


def read_ulysses(workdir='output', wavefile='Ulysses_GaiaBPRP_meanSpecWavelength.txt',
                 specfile='Ulysses_GaiaBPRP_noiseFreeSpectra.txt',
                 noiseRoot='Ulysses_GaiaBPRP_noisyPhotSpec'):
    """
    Read in the spectrum generated by ULYSSES.
    """

    with open(os.path.join(workdir, wavefile)) as f:
        lines = f.readlines()
    BP, RP = lines[-1][:-1].split('|')
    BP = np.fromstring(BP, sep=' ')
    RP = np.fromstring(RP, sep=' ')

    spec = readSpec(os.path.join(workdir, specfile))

    noiseSpecs = glob.glob(workdir+'/'+noiseRoot+'*')
    noisySpec = []
    for filename in noiseSpecs:
        noisySpec.append(readSpec(filename))

    return {'BP_wave': BP, 'RP_wave': RP, 'noiseFreeSpec': spec, 'noisySpec': noisySpec}


def ulysses2SED(data=None, workdir='output', wavefile='Ulysses_GaiaBPRP_meanSpecWavelength.txt',
                specfile='Ulysses_GaiaBPRP_noiseFreeSpectra.txt',
                noiseRoot='Ulysses_GaiaBPRP_noisyPhotSpec', noisy=True,
                response=None, wavelen_step=1.0, switch=675.):
    """
    Read in some ulysses output and return a single SED object.
    """
    if data is None:
        data = read_ulysses(workdir=workdir, wavefile=wavefile, specfile=specfile,
                            noiseRoot=noiseRoot)
    if response is None:
        response = gaia_response()

    if noisy:
        datakey = 'noisySpec'
        key2 = 'NoisySpec'
        red_spec = response.apply(data[datakey][0]['RP'+key2], blue=False)
        blue_spec = response.apply(data[datakey][0]['BP'+key2], blue=True)
    else:
        datakey = 'noiseFreeSpec'
        key2 = 'NoiseFreeSpec'
        red_spec = response.apply(data[datakey]['RP'+key2], blue=False)
        blue_spec = response.apply(data[datakey]['BP'+key2], blue=True)

    red_sed = Sed(wavelen=data['RP_wave'], flambda=red_spec)  # * 1e3)
    blue_sed = Sed(wavelen=data['BP_wave'], flambda=blue_spec)  # * 1e3)

    wavelen_min = data['BP_wave'].min()
    wavelen_max = data['RP_wave'].max()

    # Rebin the red and blue to a common wavelength array
    red_sed.resampleSED(wavelen_min=wavelen_min, wavelen_max=wavelen_max, wavelen_step=wavelen_step)
    blue_sed.resampleSED(wavelen_min=wavelen_min, wavelen_max=wavelen_max, wavelen_step=wavelen_step)

    # Clean up nan's from resampling
    red_sed.flambda[np.isnan(red_sed.flambda)] = 0.
    blue_sed.flambda[np.isnan(blue_sed.flambda)] = 0.

    # Assume Poisson stats for the noise.
    red_weight = np.ones(red_sed.flambda.size, dtype=float)  # 1./red_sed.flambda
    blue_weight = np.ones(red_sed.flambda.size, dtype=float)  # 1./blue_sed.flambda

    red_weight[np.where(red_sed.flambda == 0)] = 0.
    blue_weight[np.where(blue_sed.flambda == 0)] = 0.

    # red_cutoff = np.min(response.red_wavelen[np.where(response.red_response == 0.)])
    # blue_cutoff = np.max(response.blue_wavelen[np.where(response.blue_response == 0.)])

    #red_weight[np.where(red_sed.wavelen < red_cutoff+cutoff_pad)] = 0.
    #blue_weight[np.where(blue_sed.wavelen > blue_cutoff-cutoff_pad)] = 0.
    # Just make a simple switchover wavelength
    red_weight[np.where(red_sed.wavelen <= switch)] = 0.
    blue_weight[np.where(blue_sed.wavelen > switch)] = 0.

    # weight = np.zeros(red_sed.wavelen.size, dtype=float)
    # weight[np.where(red_sed.flambda > 0)] += 1
    # weight[np.where(blue_sed.flambda > 0)] += 1

    flambda = (red_sed.flambda*red_weight + blue_sed.flambda*blue_weight) / (red_weight + blue_weight)
    # flambda[np.where(weight == 0.)] = 0.

    finalSED = Sed(flambda=flambda, wavelen=red_sed.wavelen)
    return finalSED


def SED2GAIA(sed, noise=1, workdir='output'):
    """
    Take an LSST Sed and observe it with Gaia
    """
    tempFile = open('temp_spectra.dat', 'w')
    tempWave = open('tempWave.dat', 'w')
    good = np.where((sed.flambda > 1e-40) & (sed.wavelen > 300) & (sed.wavelen < 1400))
    # XXX-might need to convert units to get flux right. ??????
    # From ULYSSES README:
    # The original input spectra fluxes are assumed to be in W~m$^{-2}$~s$^{-1}$~nm$^{-1}$
    # for Sed, flambda (ergs/cm^s/s/nm)
    # using -conversion 1, input should be ergs cm^{-2} s^{-1} \AA^{-1}
    # flambda = sed.flambda[good] / 1e3  # Convert to W/m^2
    flambda = sed.flambda[good] / 10.  # convert nm^-1 to AA^-1
    for w, fl in zip(sed.wavelen[good], flambda):
        print >>tempFile, '%e' % (fl)
        print >> tempWave, '%f' % w
    tempFile.close()
    tempWave.close()
    call_ulysses(noise=noise, workdir=workdir)
    result = read_ulysses(workdir=workdir)
    return result


def make_response_func(magnorm=16., filename='starSED/wDs/bergeron_14000_85.dat_14200.gz',
                       savefile='gaia_response.npz', noise=1, count_min=8.,
                       bluecut=700., redcut=650):
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
    # Let's just use a flat spectrum
    wd.setFlatSED()
    fNorm = wd.calcFluxNorm(magnorm, imsimBand)
    wd.multiplyFluxNorm(fNorm)
    red_wd = copy.copy(wd)
    blue_wd = copy.copy(wd)
    gaia_obs = SED2GAIA(wd, noise=noise)
    red_wd.resampleSED(wavelen_match = gaia_obs['RP_wave'])
    blue_wd.resampleSED(wavelen_match = gaia_obs['BP_wave'])
    if noise == 1:
        red_response = red_wd.flambda / gaia_obs['noisySpec'][0]['RPNoisySpec']
        blue_response = blue_wd.flambda / gaia_obs['noisySpec'][0]['BPNoisySpec']
        too_low = np.where(gaia_obs['noisySpec'][0]['RPNoisySpec'] < count_min)
        red_response[too_low] = 0
        too_low = np.where(gaia_obs['noisySpec'][0]['BPNoisySpec'] < count_min)
        blue_response[too_low] = 0
    elif noise == 0:
        red_response = red_wd.flambda / gaia_obs['noiseFreeSpec']['RPNoiseFreeSpec']
        blue_response = blue_wd.flambda / gaia_obs['noiseFreeSpec']['BPNoiseFreeSpec']
        too_low = np.where(gaia_obs['noiseFreeSpec']['RPNoiseFreeSpec'] < count_min)
        red_response[too_low] = 0
        too_low = np.where(gaia_obs['noiseFreeSpec']['BPNoiseFreeSpec'] < count_min)
        blue_response[too_low] = 0

    blue_response[np.where(gaia_obs['BP_wave'] > bluecut)] = 0.
    red_response[np.where(gaia_obs['RP_wave'] < redcut)] = 0.

    # XXX check the mags of the original WD and the blue and red WD.

    np.savez(savefile, red_response=red_response, blue_response=blue_response,
             red_wavelen=gaia_obs['RP_wave'], blue_wavelen=gaia_obs['BP_wave'])


class gaia_response(object):

    def __init__(self, restore_file='gaia_response.npz'):

        temp = np.load(restore_file)

        self.red_response = temp['red_response'].copy()
        self.blue_response = temp['blue_response'].copy()
        self.red_wavelen = temp['red_wavelen'].copy()
        self.blue_wavelen = temp['blue_wavelen'].copy()
        temp.close()

    def mean_response(self, filenames):
        """
        Load up several response functions and average them together
        """
        pass

    def apply(self, in_spec, in_wave=None, blue=True):
        if blue:
            response = self.blue_response
            wavelen = self.blue_wavelen
        else:
            response = self.red_response
            wavelen = self.red_wavelen

        if in_wave is not None:
            if not np.array_equal(in_wave, wavelen):
                raise ValueError('Wavelength does not match response wavlenth.')

        result = in_spec * response
        return result

class gums_catalog(object):
    def __init__(self, gums_dir='/Users/yoachim/ulysses/gums'):
        # read in all the gums data
        filenames = glob.glob(gums_dir+'/*.csv')
        names = ['sourceExtendedId', 'raj2000', 'dej2000', 'meanAbsoluteV',
        'magG', 'magGBp', 'magGRp', 'magGRvs', 'alpha', 'delta', 'distance', 'muAlpha', 'muDelta',
        'radialVelocity', 'colorVminusI', 'Av', 'age', 'alphaFe', 'bondAlbedo', 'eccentricity',
        'feH', 'flagInteracting', 'geomAlbedo', 'hasPhotocenterMotion', 'host', 'inclination',
        'logg', 'longitudeAscendingNode', 'mass', 'mbol', 'nc', 'nt', 'orbitPeriod', 'periastronArgument',
        'periastronDate', 'phase', 'population', 'rEnvRStar', 'radius', 'semimajorAxis', 'teff',
        'variabilityAmplitude', 'variabilityPeriod', 'variabilityPhase', 'variabilityType', 'vsini']

        types = ['|S30']
        types.extend([float]*(len(names)-1))
        self.catalog = np.genfromtxt(filenames[0], skip_header=1, dtype=zip(names, types), delimiter=',')

        for filename in filenames[1:]:
            temp = np.genfromtxt(filename, skip_header=1, dtype=zip(names, types), delimiter=',')
            self.catalog = np.append(self.catalog, temp)


    def prune(self, verbose=True, magG_max=19.5, magG_min=15., poleClip=True):
        """
        Remove the variable and multiple systems from the catalog
        """
        start_size = np.size(self.catalog)
        singles = []
        for i, starID in enumerate(self.catalog['sourceExtendedId']):
            if (starID[-1] == 'A') | (starID[-1] == 'B') | (starID[-1] == '+'):
                singles.append(False)
            else:
                singles.append(True)

        singles = np.array(singles)
        self.catalog = self.catalog[np.where(singles == True)]
        nonvariables = np.where(self.catalog['variabilityAmplitude'] == 0)[0]
        self.catalog = self.catalog[nonvariables]

        self.catalog = self.catalog[np.where((self.catalog['magG'] < magG_max) &
                                             (self.catalog['magG'] > magG_min))]

        if poleClip:
            ra_pole = np.median(self.catalog['raj2000'])
            dec_pole = np.median(self.catalog['dej2000'])
            dist_to_center = angularSeparation(ra_pole, dec_pole, self.catalog['raj2000'], self.catalog['dej2000'])
            clip_dist=3.6/2.  # Degrees
            good = np.where(dist_to_center < clip_dist)
            self.catalog = self.catalog[good]

        if verbose:
            end_size = np.size(self.catalog)
            print 'clipped %i entries. %i remain.' % (start_size - end_size, end_size)


def gen_gums_mag_cat(istart=0, nstars=100, workdir='', noisyResponse=False, verbose=False, save=True):
    """
    generate a catalog of true and observed magnitudes for stars from the gums catalog
    """
    # Load response function
    if noisyResponse:
        response = gaia_response()
    else:
        response = gaia_response(restore_file='gaia_response_nonoise.npz')

    # Load gums catalog
    gum_cat = gums_catalog()
    gum_cat.prune()
    gum_cat = gum_cat.catalog

    print 'using %i stars from GAIA' % gum_cat.size

    sed = Sed()

    # Load up bandpass
    imsimBand = Bandpass()
    imsimBand.imsimBandpass()

    bps = lsst_filters()

    bps.update(stubb_fitlers())

    names = ['id', 'sourceExtendedId', 'raj2000', 'dej2000', 'u_truncated', 'u', 'g', 'r',
             'i', 'z', 'y', 'y_truncated',
             'u_truncated_true', 'u_true', 'g_true', 'r_true', 'i_true', 'z_true',
             'y_true', 'y_truncated_true']
    types = [int, '|S30']
    types.extend([float]*(len(names)-1))
    result_cat = np.zeros(nstars, dtype=zip(names, types))
    copy_keys = ['sourceExtendedId', 'raj2000', 'dej2000']
    a_x = None
    b_x = None
    maxI = float(nstars)
    for i, gems_index in enumerate(np.arange(istart, istart+nstars)):
        result_cat['id'][i] = gems_index
        for key in copy_keys:
            result_cat[key][i] = gum_cat[key][gems_index]
        # Lookup the file with the closest teff, feH, and logg to gum_cat[i]
        sed.read_close_SED(gum_cat['teff'][gems_index], gum_cat['feH'][gems_index],
                           gum_cat['logg'][gems_index])
        # Let's figure out the GAIA-G to SDSS g conversion. Assume SDSS_g ~ LSST_g
        # poly fit from https://arxiv.org/pdf/1008.0815.pdf
        g_mag = sed.calcMag(bps['g'])
        i_mag = sed.calcMag(bps['i'])
        g_i = g_mag - i_mag
        gnorm = gum_cat['magG'][gems_index] + 0.0094 + 0.531*(g_i) + 0.0974*(g_i)**2 - 0.0052*(g_i)**3
        if a_x is None:
            a_x, b_x = sed.setupCCMab()
        sed.addCCMDust(a_x, b_x, A_v=gum_cat['Av'][gems_index])
        # do the magnorm here
        fNorm = sed.calcFluxNorm(gnorm, bps['g'])
        sed.multiplyFluxNorm(fNorm)
        # Observe sed with GAIA, both with and without noise
        # Wrap in a try block so if ULYSSES fails for some reason the star just gets skipped
        try:
            gaia_observed = SED2GAIA(sed, workdir=workdir)
            observed_sed = ulysses2SED(data=gaia_observed, response=response)
            not_nan = ~np.isnan(observed_sed.flambda)
            # Let's interpolate out any nans
            observed_sed.flambda = np.interp(observed_sed.wavelen, observed_sed.wavelen[not_nan],
                                             observed_sed.flambda[not_nan])

            for filtername in bps:
                try:
                    result_cat[filtername][i] = observed_sed.calcMag(bps[filtername])
                except:
                    pass
                result_cat[filtername+'_true'][i] = sed.calcMag(bps[filtername])

            if verbose:
                progress = i/maxI*100
                text = "\rprogress = %.1f%%"%progress
                sys.stdout.write(text)
                sys.stdout.flush()
        except:
            import pdb ; pdb.set_trace()
        # Try to catch a failure example:
        #if (result_cat['g'][i] < 18.) & (result_cat['g'][i] > 0.):
        #    if (np.abs(result_cat['g'][i]-result_cat['g_true'][i]) > 0.75) | (np.abs(result_cat['r'][i]-result_cat['r_true'][i]) > 0.75):
        #        import matplotlib.pylab as plt
        #        import pdb ; pdb.set_trace()
    print ''

    if save:
        np.savez('%i_%i_gum_mag_cat.npz' % (istart, nstars+istart), result_cat=result_cat)
    else:
        return result_cat, sed, observed_sed



if __name__ == "__main__":
    # ok, let's see if we can load up a spectrum, scale it properly, and then make some GAIA spectra

    #make_response_func()

    # response = gaia_response()

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

