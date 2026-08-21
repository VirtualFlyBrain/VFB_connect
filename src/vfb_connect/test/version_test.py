"""The package must report one version, from one place.

These had drifted: `vfb_connect.__version__` read the generated `_version.py`
while `VfbConnect.__version__` read installed distribution metadata, so a source
checkout run alongside an installed copy reported two different versions, and
the property raised `PackageNotFoundError` when no copy was installed at all.
"""

import re
import unittest

import vfb_connect
from vfb_connect import vfb
from vfb_connect.version import UNKNOWN_VERSION, get_version

# PEP 440: a release, or a dev/pre/post build of one.
PEP440 = re.compile(r'^\d+\.\d+(\.\d+)?([._-]?(a|b|rc|dev|post)\.?\d*)*(\+[\w.]+)?$')


class VersionTest(unittest.TestCase):

    def test_the_package_and_the_session_agree(self):
        self.assertEqual(vfb_connect.__version__, vfb.__version__)

    def test_both_come_from_the_resolver(self):
        self.assertEqual(vfb_connect.__version__, get_version())

    def test_it_is_a_version_string(self):
        version = vfb_connect.__version__
        self.assertIsInstance(version, str)
        self.assertRegex(version, PEP440, f'{version!r} is not a PEP 440 version')

    def test_the_resolver_never_raises(self):
        # An unbuilt checkout with nothing installed must still import.
        self.assertTrue(get_version())

    def test_a_built_package_reports_a_real_version(self):
        # Guards the release: a wheel that reports 0.0.0 has lost its version.
        try:
            from vfb_connect import _version  # noqa: F401
        except ImportError:
            self.skipTest('unbuilt source checkout: 0.0.0 is the correct answer')
        self.assertNotEqual(vfb_connect.__version__, UNKNOWN_VERSION,
                            'built package reports no version')


if __name__ == '__main__':
    unittest.main()
