from .version import __version__
from .cross_server_tools import VfbConnect

# Create an instance of VfbConnect and make it available directly
vfb = VfbConnect(vfb_launch=True)

__all__ = ['vfb', 'VfbConnect', '__version__']
