from .cross_server_tools import VfbConnect

# Try to get version from setuptools_scm generated file
try:
    from ._version import __version__
except ImportError:
    try:
        # Fall back to environment variable based version
        from ._fallback_version import __version__
    except ImportError:
        import os
        # Last resort fallback
        __version__ = os.environ.get("VERSION", "0.0.0")

# Create an instance of VfbConnect and make it available directly
vfb = VfbConnect(vfb_launch=True)

__all__ = ['vfb', 'VfbConnect', '__version__']