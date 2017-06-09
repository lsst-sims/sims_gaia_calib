import numpy as np


class sdss_metal(object):
    def __init__(self, feh, g_r):
        # From Bind et al 2010
        self.coeff = np.array([-13.13, 14.09, 28.04, -5.51, -5.90, -58.68, 9.14, -20.61, 0.0, 58.20])
        self.terms = np.zeros(self.coeff.size, dtype=float)
        self.feh = feh
        self.g_r = g_r

    def __call__(self, u_g):
        x = u_g
        y = self.g_r

        self.terms[0] = 1.
        self.terms[1] = x
        self.terms[2] = y
        self.terms[3] = x*y
        self.terms[4] = x**2
        self.terms[5] = y**2
        self.terms[6] = x**2*y
        self.terms[7] = x*y**2
        self.terms[8] = x**3
        self.terms[9] = y**3

        result = np.sum(self.coef*self.terms) - self.feh
        return result




