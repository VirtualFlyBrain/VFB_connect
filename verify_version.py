#!/usr/bin/env python3
"""
Script to verify that the installed package has the expected version.
This is particularly useful for CI/CD to ensure the built package
has the correct version number before publishing.
"""
import os
import sys
import importlib

# Try to import the package
try:
    import vfb_connect
    actual_version = getattr(vfb_connect, "__version__", "unknown")
except ImportError:
    print("ERROR: Could not import vfb_connect")
    sys.exit(1)

# Get expected version from environment
expected_version = os.environ.get("VERSION", "")

# Print versions for debugging
print(f"Expected version: {expected_version}")
print(f"Actual version: {actual_version}")

# Compare versions
if expected_version and expected_version != actual_version:
    print("ERROR: Version mismatch!")
    sys.exit(1)
else:
    print("Version verification successful")
    sys.exit(0)
