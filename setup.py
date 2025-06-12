from setuptools import setup, find_packages
from os import path
import glob

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(name='vfb-connect',  
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
      data_files=[('json_schema', ['src/vfb_connect/resources/VFB_TermInfo_queries.json','src/vfb_connect/resources/VFB_results_single_input.json','src/vfb_connect/resources/VFB_results_multi_input.json'])],
      project_urls={
          'Bug Reports': 'https://github.com/VirtualFlyBrain/VFB_connect/issues',
          'Source': 'https://github.com/VirtualFlyBrain/VFB_connect',
          'Documentation': 'https://vfb-connect.readthedocs.io/en/stable/'
       },
)
