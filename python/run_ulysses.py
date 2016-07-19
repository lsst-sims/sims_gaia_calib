import matplotlib.pylab as plt
from lsst.sims.catalogs.generation.db import CatalogDBObject
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


# ssh -L 51433:fatboy.phys.washington.edu:1433 gateway.astro.washington.edu


# ok, let's see if we can load up a spectrum, scale it properly, and then make some GAIA spectra

ra = 0.  # Degrees
dec = 0.  # Degrees
boundLength = 1. 
dbobj = CatalogDBObject.from_objid('allstars')
obs_metadata = ObservationMetaData(boundType='circle',pointingRA=ra,
                                   pointingDec=dec,boundLength=boundLength, mjd=5700)
t = dbobj.getCatalog('ref_catalog_star', obs_metadata=obs_metadata)

constraint = 'rmag < 18 and rmag > 15'
chunks = t.db_obj.query_columns(colnames=['magNorm', 'rmag', 'sedfilename', 'ebv', 'especid'], 
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
good = np.where( ss.flambda > 1e-40)
for w, fl in zip(ss.wavelen[good], ss.flambda[good]):
    print >>tempFile, '%f, %e' % (w, fl)
tempFile.close()




