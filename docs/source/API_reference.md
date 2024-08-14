# API Reference

It is sufficient to initialise a single `VfbConnect` object to get access to all
the functions in VFB_connect acting on our default API endpoints.

```Python
from vfb_connect import vfb
```
A range canned queries are available via methods directly accessible from this
object, or via vfb.

Core, cross server methods are directly accessible from this object

Direct queries of our `Neo4J` database are available via methods under `vfb.nc`
OWL queries are available under `vfb.oc`.

(Other direct query endpoint will be added in future)


### Queries cell and anatomical types

.. autosummary::
    :toctree: generated/

    ~VfbConnect.TreeNeuron.get_subclasses
    ~VfbConnect.get_superclasses
    ~VfbConnect.get_terms_by_region

### Connectivity queries

get_connected_neurons_by_type
get_neurons_downstream_of
get_neurons_upstream_of

### Queries for individual neurons

get_instances
get_instances_by_dataset
get_similar_neurons

### Queries for images

get_images_by_type()
get_images()

### VFB link generation methods

neo_query_wrapper.get_vfb_link

### ID conversion methods

vfb_id_2_xrefs
xref_2_vfb_id

### Methods for retrieving Term Information from arbitrary lists of IDs

get_TermInfo
get_terms_by_xref

neo_query_wrapper.get_template_TermInfo
neo_query_wrapper.get_type_TermInfo
neo_query_wrapper.get_anatomical_individual_TermInfo
neo_query_wrapper.get_DataSet_TermInfo

## Methods for retrieving lists of available get_connected_neurons_by_type

get_datasets
get_dbs
get_templates
