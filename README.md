# VFB_connect [![test_vfb-connect](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/test_vfb-connect.yml/badge.svg)](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/test_vfb-connect.yml) [![publish-to-pypi](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/publish-to-pypi.yml) [![PyPI version](https://badge.fury.io/py/vfb-connect.svg)](https://pypi.org/project/vfb-connect/)
[![test_notebooks](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/test_notebooks.yml/badge.svg)](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/test_notebooks.yml) [![Documentation Status](https://readthedocs.org/projects/vfb-connect/badge/?version=stable)](https://vfb-connect.readthedocs.io/en/stable/?badge=latest)

VFB_connect is a Python lib that wraps data/knowledgeBase query endpoints and returns DataFrame tables.

Available on PyPi:

` pip install vfb_connect `
  
  
  ## Some examples:
  
 ```python

# VFB connect object wraps connections and queries to public VFB servers.

from vfb_connect import vfb

# Get TermInfo for Types/Classes, DataSets and anatomical individuals.

vfb.get_TermInfo(['FBbt_00003686'])

vfb.get_TermInfo(['Ito02013'])

vfb.get_TermInfo(['VFB_00010001'])

# Get all terms relevant to a brain region (all parts and all overlapping cells.  Query by label supported by default.

vfb.get_terms_by_region('fan-shaped body')

```

TermInfo return a pandas DataFrame by default but can also return a dict summary or full VFB_json values that conform to [VFB_json_schema](https://virtualflybrain.github.io/schema_doc.html)

For more examples see our [Quick Guide Jupyter Notebook](https://github.com/VirtualFlyBrain/VFB_connect/blob/master/snippets/VFB_connect_Quick_Guide.ipynb)
