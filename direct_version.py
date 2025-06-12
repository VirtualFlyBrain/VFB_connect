#!/usr/bin/env python3
"""
This script provides a direct way to get the version from environment variable or Git.
It's designed to be used in CI/CD pipelines where setuptools_scm might not work correctly.
"""
import os
import subprocess
import sys
import re

def get_git_version():
    """Get version from git tags"""
    try:
        # First try to use git describe to get the version from the nearest tag
        cmd = ["git", "describe", "--tags", "--match", "v*.*.*"]
        print(f"Running: {' '.join(cmd)}", file=sys.stderr)
        
        try:
            version = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True).strip()
            print(f"Git describe output: {version}", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Git describe failed: {e.output}", file=sys.stderr)
            # Try fallback with --always to at least get the commit hash
            try:
                cmd = ["git", "describe", "--always"]
                commit_hash = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True).strip()
                print(f"Using commit hash: {commit_hash}", file=sys.stderr)
                return f"0.0.0.dev0+g{commit_hash}"
            except:
                return None
        
        # If it's an exact tag, just remove the v prefix
        if re.match(r"^v\d+\.\d+\.\d+$", version):
            print(f"Exact tag match: {version}", file=sys.stderr)
            return version[1:]
            
        # If it's a dev version (tag-N-hash), format it according to PEP 440
        match = re.match(r"^v(\d+\.\d+\.\d+)-(\d+)-g([0-9a-f]+)$", version)
        if match:
            base_version = match.group(1)
            distance = match.group(2)
            commit = match.group(3)
            result = f"{base_version}.dev{distance}+g{commit}"
            print(f"Dev version: {result}", file=sys.stderr)
            return result
            
        print(f"Using version with v stripped: {version.lstrip('v')}", file=sys.stderr)
        return version.lstrip("v")
    except Exception as e:
        print(f"Error getting git version: {e}", file=sys.stderr)
        return None

def get_version():
    """Get version from environment or Git"""
    print("Starting version detection", file=sys.stderr)
    
    # First check for explicit VERSION environment variable
    version_env = os.environ.get("VERSION")
    if version_env:
        print(f"Using VERSION from environment: {version_env}", file=sys.stderr)
        return version_env
        
    # Check for GITHUB_REF environment variable (used in GitHub Actions)
    github_ref = os.environ.get("GITHUB_REF")
    if github_ref and github_ref.startswith("refs/tags/v"):
        version = github_ref.replace("refs/tags/v", "")
        print(f"Using version from GITHUB_REF tag: {version}", file=sys.stderr)
        return version
        
    # Try to get version from Git
    print("Checking Git for version information...", file=sys.stderr)
    git_version = get_git_version()
    if git_version:
        print(f"Using Git-derived version: {git_version}", file=sys.stderr)
        return git_version
        
    # Fall back to reading version from _version.py if it exists
    print("Checking for _version.py...", file=sys.stderr)
    try:
        sys.path.insert(0, "src")
        from vfb_connect._version import __version__
        print(f"Using version from _version.py: {__version__}", file=sys.stderr)
        return __version__
    except ImportError as e:
        print(f"Could not import from _version.py: {e}", file=sys.stderr)
        pass
        
    # Last resort fallback
    print("Using fallback version 0.0.0", file=sys.stderr)
    return "0.0.0"

if __name__ == "__main__":
    print(get_version())
