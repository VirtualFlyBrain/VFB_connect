"""Offline tests for the vendored Lab -> sRGB conversion (issue #287).

Reference values were generated with colormath 3.0.0's
``convert_color(LabColor(l, a, b), sRGBColor)`` (clamped channels), which this
module replaces.
"""

import unittest

import numpy as np

from vfb_connect.color_conversion import lab_to_srgb_clamped


class LabToSrgbTest(unittest.TestCase):

    # ((L, a, b), (r, g, b)) pairs from colormath 3.0.0
    REFERENCE = [
        ((0, 0, 0), (0.000000, 0.000000, 0.000000)),
        ((100, 0, 0), (1.000000, 0.999994, 0.999935)),
        ((50, 0, 0), (0.466344, 0.466324, 0.466295)),
        ((53.24, 80.09, 67.2), (0.982320, 0.000000, 0.025792)),
        ((87.74, -86.18, 83.18), (0.000000, 1.000000, 0.000000)),
        ((32.3, 79.19, -107.86), (0.355268, 0.000000, 1.000000)),
        ((50, -30, 40), (0.313814, 0.516759, 0.172645)),
        ((75, 20, -50), (0.711677, 0.684838, 1.000000)),
        ((20, 60, 10), (0.467718, 0.000000, 0.147970)),
    ]

    def test_matches_colormath_reference(self):
        for lab, expected in self.REFERENCE:
            got = lab_to_srgb_clamped(*lab)
            np.testing.assert_allclose(got, expected, atol=5e-6,
                                       err_msg=f"Lab {lab}")

    def test_output_clamped(self):
        for l in np.linspace(0, 100, 5):
            for a in np.linspace(-110, 110, 5):
                for b in np.linspace(-110, 110, 5):
                    rgb = lab_to_srgb_clamped(l, a, b)
                    self.assertTrue(np.all(rgb >= 0.0) and np.all(rgb <= 1.0))


if __name__ == "__main__":
    unittest.main()
