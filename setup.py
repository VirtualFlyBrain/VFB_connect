from setuptools import setup, find_packages
from os import path
import glob

here = path.abspath(path.dirname(__file__))

from get_version import get_version
__version__ = get_version(__file__)
del get_version

# Get the long description from the README file
with open(path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(name='vfb_connect',  
      version=__version__, 
      packages=find_packages(where='src'),
      package_dir={'': 'src'},
      py_modules=[path.splitext(path.basename(path))[0] for path in glob.glob('src/*.py')],
      include_package_data=True,
      description='Wrapper for querying VirtualFlyBrain servers.',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Robert Court', 
      url='https://github.com/VirtualFlyBrain/VFB_connect',
      author_email='rcourt@ed.ac.uk',  
      install_requires=['requests', 'pandas', 'jsonpath_rw', 'pysolr', 'navis', 'numpy>=1.26.4, <2.0.0', 'seaborn>0.13', 'colormath', 'tqdm',],
      data_files=[('json_schema', ['src/vfb_connect/resources/VFB_TermInfo_queries.json','src/vfb_connect/resources/VFB_results_single_input.json','src/vfb_connect/resources/VFB_results_multi_input.json'])],
      classifiers=[  
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Programming Language :: Python :: 3',
       ],
      project_urls={
          'Bug Reports': 'https://github.com/VirtualFlyBrain/VFB_connect/issues',
          'Source': 'https://github.com/VirtualFlyBrain/VFB_connect',
          'Documentation': 'https://vfb-connect.readthedocs.io/en/stable/'
       },
)
