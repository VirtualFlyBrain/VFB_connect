"""Minimal CIE Lab -> sRGB conversion.

Vendored replacement for the abandoned ``colormath`` dependency (see issue
#287).  Reproduces colormath's ``convert_color(LabColor(l, a, b), sRGBColor)``
pipeline exactly: Lab (D50, 2 degree observer) -> XYZ (D50) -> Bradford
chromatic adaptation to D65 -> linear sRGB -> gamma encoding, with the result
clamped to [0, 1].
"""

import numpy as np

_WHITE_D50 = np.array([0.96422, 1.00000, 0.82521])
_WHITE_D65 = np.array([0.95047, 1.00000, 1.08883])
_BRADFORD = np.array([[0.8951, 0.2664, -0.1614],
                      [-0.7502, 1.7135, 0.0367],
                      [0.0389, -0.0685, 1.0296]])
_XYZ_TO_SRGB = np.array([[3.24071, -1.53726, -0.498571],
                         [-0.969258, 1.87599, 0.0415557],
                         [0.0556352, -0.203996, 1.05707]])


def _adaptation_matrix():
    source = _BRADFORD @ _WHITE_D50
    destination = _BRADFORD @ _WHITE_D65
    scale = np.diag(destination / source)
    return np.linalg.inv(_BRADFORD) @ scale @ _BRADFORD


_ADAPT = _adaptation_matrix()

# CIE constants (actual values, as used by colormath).
_EPSILON = 216.0 / 24389.0
_KAPPA = 24389.0 / 27.0


def lab_to_srgb_clamped(l, a, b):
    """Convert a CIE Lab (D50) colour to clamped sRGB floats.

    :param l: Lightness, 0-100.
    :param a: Green-red axis.
    :param b: Blue-yellow axis.
    :return: ``numpy.ndarray`` of (r, g, b) floats clamped to [0, 1].
    """
    fy = (l + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0

    def _f_inv(t):
        t3 = t ** 3
        return t3 if t3 > _EPSILON else (116.0 * t - 16.0) / _KAPPA

    xyz = np.array([_f_inv(fx), _f_inv(fy), _f_inv(fz)]) * _WHITE_D50
    xyz = _ADAPT @ xyz
    rgb_linear = _XYZ_TO_SRGB @ xyz

    def _gamma(c):
        return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055

    rgb = np.array([_gamma(c) for c in rgb_linear])
    return np.clip(rgb, 0.0, 1.0)
