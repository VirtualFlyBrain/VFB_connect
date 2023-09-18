API Reference
=============

This document organises methods by their function.  For a general introduction, please see
our QuickStart documentation :doc:`tutorials/overview`.

Introduction
~~~~~~~~~~~~

It is sufficient to initialise a single ``VfbConnect`` object to get
access to all the functions in VFB_connect acting on our default API
endpoints (see code snippet below).  :doc:`Semantic_queries` returning rich metadata
on entities found (see :doc:`output formats`) are available via direct methods on ``VfbConnect``.  Semantic queries
returning IDs only are available via methods on ``VfbConnect.oc`` (a shortcut to
``vfb_connect.owl.owlery_query_tools.OWLeryConnect.``). Queries taking ID lists as input (see :doc:`IDs_on_VFB`)
and returning rich metadata or mappings to/from external IDs are available via methods on
``VFBConnect.neo_query_wrapper`` (a shortcut to ``vfb_connect.neo.query_wrapper.QueryWrapper``)

Direct queries of our neo4j endpoint are available via methods on ``vc.nc`` (a shortcut to
``vfb_connect.neo.neo4j_tools.Neo4jConnect``).  A guide to the VFB Neo4J schema and how to
query it is in preparation.

.. code:: Python

   from vfb_connect.cross_server_tools import VfbConnect
   vc = VfbConnect()

   # Semantic queries returning rich metadata on entities found
   # methods directly on VfbConnect object.
   # e.g.
   vc.get_subclasses('DL1_adPN', summary=True)

   # Semantic queries returning IDs only
   # shortcut to vfb_connect.owl.owlery_query_tools.OWLeryConnect.get_subclasses
   # e.g.
   vc.oc.get_subclasses('DL1_adPN', summary=True)

   # Queries taking ID lists as input and returning rich metadata or mappings
   # shortcut to vfb_connect.neo.query_wrapper.QueryWrapper.get_TermInfo
   # e.g.
   vc.neo_query_wrapper.get_TermInfo(['FBbt_00003680'])

   # Direct cypher query of the VFB neo4j database
   # shortcut to vfb_connect.neo.neo4j_tools.Neo4jConnect.commit_list
   # e.g.
   vc.nc.commit_list(['MATCH (n:neuron:Class { symbol: 'DL1_adPN'}) RETURN n'])



Semantic queries for cell and anatomical types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Methods returning extended information about types

.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_subclasses
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_superclasses
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_terms_by_region


Methods returning IDs only.  These methods are all accessible via ``VfbConnect.oc``

.. autofunction:: vfb_connect.owl.owlery_query_tools.OWLeryConnect.get_subclasses
.. autofunction:: vfb_connect.owl.owlery_query_tools.OWLeryConnect.get_superclasses

Semantic queries for individual neurons
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Methods returning extended information about types

.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_instances
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_instances_by_dataset
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_similar_neurons


Methods returning IDs only.  These methods are accessible via ``VfbConnect.oc``

.. autofunction:: vfb_connect.owl.owlery_query_tools.OWLeryConnect.get_instances

Queries for images
~~~~~~~~~~~~~~~~~~

Semantic queries for images

.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_images_by_type

(Note, this method can be accessed from VfbConnect.neo_query_wrapper)

.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_images

Connectivity queries
~~~~~~~~~~~~~~~~~~~~

**Methods for finding synaptic connections**

.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_connected_neurons_by_type
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_neurons_downstream_of
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_neurons_upstream_of

Transcriptomics Queries
~~~~~~~~~~~~~~~~~~~~~~~

**Methods for retrieving transcriptomics data**

.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_transcriptomic_profile
.. autofunction:: vfb_connect.cross_server_tools.VfbConnect.get_gene_function_filters

VFB link generation
~~~~~~~~~~~~~~~~~~~~

.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_vfb_link

ID conversion
~~~~~~~~~~~~~~

**Methods for converting between VFB_ids and external IDs, and vice versa**
(Note these methods can be accessed from ``VfbConnect.neo_query_wrapper``
For more information on IDs on VFB see :doc:`IDs_on_VFB`.

.. autofunction::  vfb_connect.neo.query_wrapper.QueryWrapper.vfb_id_2_xrefs
.. autofunction::  vfb_connect.neo.query_wrapper.QueryWrapper.xref_2_vfb_id

Retrieving Term Information by ID
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The methods can all be accessed from ```VfbConnect.neo_query_wrapper```

**Function for any type of VFB entity (slow for long lists)**

.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_TermInfo

**Function for any type of VFB entity using an external ID**

.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_terms_by_xref

**Functions by type (these are faster then the generic queries)**

.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_template_TermInfo
.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_type_TermInfo
.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_anatomical_individual_TermInfo
.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_DataSet_TermInfo

Retrieving all IDs for some specific type
-----------------------------------------------------------------------

.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_datasets
.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_dbs
.. autofunction:: vfb_connect.neo.query_wrapper.QueryWrapper.get_templates

Directly querying the VFB neo4j database
----------------------------------------------------

These functions are accessible under VFBConnect.nc

.. autofunction:: vfb_connect.neo.neo4j_tools.Neo4jConnect.commit_list
.. autofunction:: vfb_connect.neo.neo4j_tools.Neo4jConnect.commit_list_in_chunks


