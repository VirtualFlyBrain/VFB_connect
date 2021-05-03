IDs on VFB
==========

All content on VFB is identified by a resolvable URL (IRI).  This provides a universal, resolvable way for external
databases and documents to refer to our content. The last part of this (following a ``/`` or
(more occasionally a ``#``) is referred to as a ``short form ID`` (see below for examples).
API methods requiring or returning IDs typically use and return short forms.


| label | symbol | iri | short_form | comment |
| -- | -- | -- | -- | -- | 
| 5-HTPLP01_R (FlyEM-HB:1324365879)| http://virtualflybrain.org/reports/VFB_jrchjrch | VFB_jrchjrch | Individual neuron |
| ellipsoid body | | http://purl.obolibrary.org/obo/FBbt_00003678  | FBbt_00003678 | Type of anatomical structure (AS) |
| EB on JRC2018Unisex adult brain | | http://virtualflybrain.org/reports/VFB_00102135 | VFB_00102135 | Individual AS |
| mushroom body output neuron | MBON | http://purl.obolibrary.org/obo/FBbt_00047953 | FBbt_00047953 | Type of neuron |


Links to external IDs:

Links to external identifiers consist of two parts: a database (source) ID indicating the source of the identifier
and an accession - the ID itself.

e.g. DB: catmaid_fafb; accession:6026853

.. code:: Python

    


