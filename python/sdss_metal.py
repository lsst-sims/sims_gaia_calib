import numpy as np
from scipy.optimize import ridder


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

        result = np.sum(self.coeff*self.terms) - self.feh
        return result


def calc_u_g(feh, g_r, u_g_range = [0.7, 1.7]):
    """
    Use relation from Bond et al 2010 to compute the expected u-g color given
    stellar metalicity and g-r color.
    # g-r in range 0.25 to 0.58
    """

    if np.size(feh) > 1:
        result = []
        for metal, color in zip(feh, g_r):
            func = sdss_metal(metal, color)
            u_g = ridder(func, u_g_range[0], u_g_range[1])
            result.append(u_g)
        result = np.array(result)
    else:
        func = sdss_metal(feh, g_r)
        result = ridder(func, u_g_range[0], u_g_range[1])
    return result

