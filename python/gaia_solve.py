import numpy as np
from lsst.sims.selfcal.utils import fastRead
from lsst.sims.selfcal.solver import lsqrSolver


# Read in some observation file, load up the GAIA truth, solve for each zeropoint.

# for the gaia stars, need to put their true LSST mags in the general db
# then generate a realization of expected LSST mags to calibrate against.


class gaiaSolver(lsqrSolver):

    def readGaia(self, gaiaFile='gaia_mags.dat'):
        """
        read in the mags for the gaia stars.  
        """
        names = ['starID', 'mag', 'magErr', 'radius', 'hpID']
        types = [int,int,float,float,float,int]

        self.gaiaMags = fastRead(gaiaFile, dtype=zip(names, types), delimiter=',')

    def run(self):
        self.readData()
        self.readGaia()
        self.solveGaia()

    def solveGaia(self):
        self.observations.sort(order='patchID')

        patchResult = np.empty(self.observations.size, dtype=float )
        starResult = np.empty(self.Stars.size, dtype=zip(['starID','fitMag'],[int,float]) )
        starResult.fill(-666)

        upid = np.unique(self.observations['patchID'])
        left = np.searchsorted(self.observations['patchID'], upid)
        right = np.searchsorted(self.observations['patchID'], upid, side='right')

        zps = np.zeros(upid.size, dtype=float)

        for le, ri, i in enumerate(zip(left,right)):
            
            # find the gaia stars in the patch

            # Fit the patch zeropoint using the GAIA stars

            patchResult[le:ri] = patchZP

        # Apply the fitted patch zeropoints and find the best mag for each star
        


