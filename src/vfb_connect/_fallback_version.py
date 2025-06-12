"""
Fallback version module for when setuptools_scm fails to detect the version.
This is particularly useful for GitHub Actions where the checkout might not include
full Git history or tags.
"""

import os

__version__ = os.environ.get("VERSION", "0.0.0")
