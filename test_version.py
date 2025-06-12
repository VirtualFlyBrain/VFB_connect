#!/usr/bin/env python3
"""
Test script to check version detection in different environments.
This can be run locally or in CI to debug version issues.
"""
import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import the package
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Try different version detection methods
print("Environment:")
print(f"  GITHUB_REF: {os.environ.get('GITHUB_REF', 'Not set')}")
print(f"  VERSION: {os.environ.get('VERSION', 'Not set')}")

print("\nVersion detection:")
try:
    from setuptools_scm import get_version
    print(f"  setuptools_scm: {get_version()}")
except ImportError:
    print("  setuptools_scm: Not installed")
except Exception as e:
    print(f"  setuptools_scm error: {e}")

# Try to import the package
try:
    import vfb_connect
    print(f"  vfb_connect.__version__: {getattr(vfb_connect, '__version__', 'Not set')}")
except ImportError:
    print("  vfb_connect: Not installed or cannot be imported")
except Exception as e:
    print(f"  vfb_connect import error: {e}")

# Try to read _version.py directly
version_path = Path(__file__).parent / "src" / "vfb_connect" / "_version.py"
if version_path.exists():
    print(f"  _version.py exists: {version_path}")
    with open(version_path) as f:
        content = f.read()
        print(f"  _version.py content snippet:\n    {content.split('__version__ = ')[1].split('\n')[0]}")
else:
    print(f"  _version.py does not exist: {version_path}")

# Use get_version.py
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from get_version import get_version
    print(f"  get_version.py: {get_version('vfb_connect')}")
except Exception as e:
    print(f"  get_version.py error: {e}")
