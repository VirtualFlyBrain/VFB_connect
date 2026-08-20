# VFB_connect [![test_vfb-connect](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/test_vfb_connect.yml/badge.svg)](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/test_vfb-connect.yml) [![publish-to-pypi](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/publish-to-pypi.yml) [![PyPI version](https://badge.fury.io/py/vfb_connect.svg)](https://pypi.org/project/vfb_connect/) [![DOI](https://zenodo.org/badge/235797695.svg)](https://zenodo.org/badge/latestdoi/235797695)
[![test_notebooks](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/test_notebooks.yml/badge.svg)](https://github.com/VirtualFlyBrain/VFB_connect/actions/workflows/test_notebooks.yml) [![Documentation Status](https://readthedocs.org/projects/vfb_connect/badge/?version=stable)](https://vfb_connect.readthedocs.io/en/stable/?badge=latest)

VFB_connect is a Python lib that wraps data/knowledgeBase query endpoints and returns DataFrame tables.

Available on PyPi:

` pip install vfb_connect `
  
  
  ## Some examples:
  
 ```python

# VFB connect object wraps connections and queries to public VFB servers.

from vfb_connect import vfb

# Get TermInfo for Types/Classes, DataSets and anatomical individuals.

vfb.term('FBbt_00003686')

vfb.terms(['Ito02013'])

vfb.terms(['VFB_00010001'])

# Get all terms relevant to a brain region (all parts and all overlapping cells. You can query by label, symbol, synonym, id or xref.

vfb.get_terms_by_region('fan-shaped body')

```

TermInfo returns a pandas DataFrame by default but can also return a dict summary or full VFBTerms.

For more examples see our [Quick Guide Jupyter Notebook](https://github.com/VirtualFlyBrain/VFB_connect/blob/master/snippets/VFB_connect_Quick_Guide.ipynb)

## Cached query results

Several queries — similar morphology, the neurons and neuron types in a region, parts,
subtypes, lineage clones and innervating tracts — are answered from VFBquery's pre-computed
results at https://v3-cached.virtualflybrain.org, the same source the Virtual Fly Brain website
reads. Results and column names are unchanged; the query is simply not re-derived. If the service
is unavailable, slow or returns an incomplete result, the original Neo4j/Owlery query runs
instead, so nothing depends on it being up.

Results larger than one response (25,000 rows) are paged, with a progress bar — a whole
neuropil can be hundreds of thousands of rows. `vfb._load_limit` truncates them, and any
truncation is reported rather than silent.

`vfb.query_counts(id)` returns how many results *every* query on a term would give, in
one request and without running any of them:

```python
vfb.query_counts('FBbt_00003748')
# {'NeuronsSynaptic': 464, 'PartsOf': 28, 'ImagesNeurons': 226524, ...}
```

A count of `-1` there means VFBquery could not count that query — not that it is empty.

Environment variables:

* `VFB_USE_CACHED_QUERIES=false` — always run queries directly.
* `VFB_CACHED_QUERY_URL` — point at a different VFBquery deployment.
* `VFB_CACHED_QUERY_MAX_ROWS` — row ceiling before a result is truncated (default 250,000).

Methods that use it also take `use_cached=True|False` to override per call.
