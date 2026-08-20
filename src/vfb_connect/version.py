"""Where the package version comes from.

One resolver, so that ``vfb_connect.__version__`` and
``VfbConnect.__version__`` can never disagree — they had drifted apart, one
reading the generated file and the other the installed distribution metadata,
which give different answers whenever a source checkout is run alongside an
installed copy.

Resolution order, most to least specific:

1. ``_version.py``, written by setuptools_scm when this tree was built, and by
   the release workflow from the release tag. This comes first deliberately: it
   describes the code actually being imported, which is what a caller means by
   "what version is this".
2. Installed distribution metadata, for an install whose generated file is
   missing.
3. ``$VERSION``, which the release workflow sets during a build.
4. ``0.0.0`` — an unbuilt source checkout. Honest, rather than a stale number.

``_version.py`` is generated, not tracked. A checkout that has never been built
reports ``0.0.0``; building or installing gives the real version.
"""

import os

__all__ = ['__version__', 'get_version']

UNKNOWN_VERSION = '0.0.0'

DISTRIBUTION_NAME = 'vfb_connect'


def get_version():
    """Return the version of the vfb_connect being imported.

    :return: A PEP 440 version string, or `'0.0.0'` if it cannot be determined.
    :rtype: str
    """
    try:
        from ._version import version
        if version:
            return str(version)
    except Exception:
        # Generated file absent (unbuilt checkout) or malformed. Keep looking.
        pass

    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as distribution_version
        try:
            return distribution_version(DISTRIBUTION_NAME)
        except PackageNotFoundError:
            pass
    except ImportError:  # pragma: no cover - Python < 3.8
        pass

    return os.environ.get('VERSION', UNKNOWN_VERSION)


__version__ = get_version()
