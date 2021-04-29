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
   
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_subclasses
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_superclasses
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_terms_by_region

   
Queries for individual neurons
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_instances, 
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_instances_by_dataset
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_similar_neurons
   
Queries for images
~~~~~~~~~~~~~~~~~~

.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_images_by_type

(Note, this method can be accessed from VfbConnect.neo_query_wrapper)

.. autofunction:: vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.get_images

Connectivity queries
~~~~~~~~~~~~~~~~~~~~

Methods for querying direct connectivity:
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_connected_neurons_by_type
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_neurons_downstream_of
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_neurons_upstream_of


VFB link generation methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.get_vfb_link

ID conversion methods
~~~~~~~~~~~~~~~~~~~~~

Methods for converting between VFB_ids and external IDs, and vice versa

(Note these methods can be accessed from VfbConnect.neo_query_wrapper)

.. autofunction::  vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.vfb_id_2_xrefs
.. autofunction::  vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.xref_2_vfb_id

Methods for retrieving Term Information from arbitrary lists of IDs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(Note these methods can be accessed from VfbConnect.neo_query_wrapper)

Function for any type of VFB entity (slow for long lists)
.. autofunction:: vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.get_TermInfo

Function for any type of VFB entity using an external ID
.. autofunction:: vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.get_terms_by_xref

Functions by type (these are faster then the generic queries)

.. autofunction:: vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.get_template_TermInfo
.. autofunction:: vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.get_type_TermInfo
.. autofunction:: vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.get_anatomical_individual_TermInfo
.. autofunction:: vfb_connect.neo.neo4j_tools.query_wrapper.QueryWrapper.get_DataSet_TermInfo

Methods for retrieving lists of available 
-----------------------------------------------------------------------

.. automodule:: vfb_connect.cross_server_tools.VfbConnect.neo_query_wrapper
   :members:  get_datasets, get_dbs, get_templates
