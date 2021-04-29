API Reference
=============

It is sufficient to initialise a single ``VfbConnect`` object to get
access to all the functions in VFB_connect acting on our default API
endpoints.

.. code:: Python

   from vfb_connect.cross_server_tools import VfbConnect
   vc = VfbConnect()

A range canned queries are available via methods directly accessible from this object, or via vc. Core, cross server methods are directly accessible from this object. Direct queries of our ``Neo4J`` database are available via methods under ``vc.nc`` OWL queries are available under ``vc.oc``.

(Other direct query endpoint will be added in future)

Queries for cell and anatomical types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. automodule:: vfb_connect.cross_server_tools.VfbConnect
   :members: get_subclasses, get_superclasses, get_terms_by_region
   
Queries for individual neurons
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vfb_connect.cross_server_tools.VfbConnect
   :members: get_instances, get_instances_by_dataset, get_similar_neurons
   
Queries for images
~~~~~~~~~~~~~~~~~~

.. automodule:: vfb_connect.cross_server_tools.VfbConnect
   :members: get_images_by_type
 
.. automodule:: vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper
   :members: get_images


Connectivity queries
~~~~~~~~~~~~~~~~~~~~

Methods for querying direct connectivity:

.. automodule:: vfb_connect.cross_server_tools.VfbConnect
   :members: get_connected_neurons_by_type, get_neurons_downstream_of,
get_neurons_upstream_of


VFB link generation methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vfb_connect.cross_server_tools.VfbConnect.neo_query_wrapper
   :members: get_vfb_link

ID conversion methods
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vfb_connect.cross_server_tools.VfbConnect.neo_query_wrapper
   :members: vfb_id_2_xrefs, neo_query_wrapper, xref_2_vfb_id

Methods for retrieving Term Information from arbitrary lists of IDs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vfb_connect.cross_server_tools.VfbConnect.neo_query_wrapper
   :members:  get_TermInfo, get_terms_by_xref, neo_query_wrapper.get_template_TermInfo, get_type_TermInfo, get_anatomical_individual_TermInfo, get_DataSet_TermInfo

Methods for retrieving lists of available get_connected_neurons_by_type
-----------------------------------------------------------------------

.. automodule:: vfb_connect.cross_server_tools.VfbConnect.neo_query_wrapper
   :members:  get_datasets, get_dbs, get_templates
