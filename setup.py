from setuptools import setup, find_packages
from os import path
import glob

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='vfb_connect',  # Required
      version='v1.2.5',  # Required
      packages=find_packages(where='src'),
      package_dir={'': 'src'},
      py_modules=[path.splitext(path.basename(path))[0] for path in glob.glob('src/*.py')],
      include_package_data=True,
      description='Wrapper for querying VirtualFlyBrain servers.',  # Optional)
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='David Osumi-Sutherland',  # Optional
      url='https://github.com/VirtualFlyBrain/VFB_connect',
      # This should be a valid email address corresponding to the author listed
      # above.
      author_email='dosumis@gmail.com',  # Optional
      install_requires=['requests', 'pandas', 'jsonpath_rw'],
      data_files=[('json_schema', ['src/vfb_connect/resources/VFB_TermInfo_queries.json'])],
      classifiers=[  # Optional
          # How mature is this project? Common values are
          #   3 - Alpha
          #   4 - Beta
          #   5 - Production/Stable
          'Development Status :: 4 - Beta',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Programming Language :: Python :: 3',
       ],
      project_urls={  # Optional
          'Bug Reports': 'https://github.com/VirtualFlyBrain/VFB_connect/issues',
          'Source': 'https://github.com/VirtualFlyBrain/VFB_connect',
       },
)
