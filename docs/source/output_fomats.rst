VFB_connect output formats
==========================

VFB_JSON
--------

A JSON representation of the information displayed in VFB term
information reports.

The confirms to a standard JSON schema: `raw schema
docs <https://github.com/VirtualFlyBrain/VFB_json_schema/blob/master/src/json_schema/vfb_termInfo.json>`__;
[schema in browsable form](https://virtualflybrain.github.io/VFB_json_schema/doc/schema_doc.html).

Summary reports
---------------

Summary reports provide a high-level, tabular summary of VFB term
information, provided as a list of dictionaries in JSON, which can be
easily loaded into Python Pandas:

.. code:: Python

   import pandas
   df = pd.DataFrame.from_records(vc.<some method call>)  # Add example

Applies to \| Column name \| content -- \| -- all \| label \| name of
entity all \| symbol \| short symbol for entity (if any) all \| id \|
VFB ID of entity all \| tags \| tags associated with entity (gross
class; data flags) anatomical types & individuals \| parents_label \|
parent class labels (``|`` delim) anatomical types & individuals \|
parents_id \| parent classes IDs (``|`` delim) anatomical individuals \|
data_source \| ID of data_source anatomical individuals \| accession \|
ID of individual in data_source anatomical individuals \| dataset \|
dataset(s) individual belongs to (``|`` delim) anatomical individuals \|
templates \| template(s) registered to (``|`` delim) anatomical
individuals \| license \| license data is available under dataset \|
description \| DataSet description, if present dataset \| miniref \|
minimal informtion for DataSet referece dataset \| FlyBase \| FlyBase ID
for DataSet reference dataset \| PMID \| PMID for DataSet reference
dataset \| DOI \| DOI for DataSet reference

ID Mappings
-----------

Mappings between VFB IDs and external IDs are provided as dictionaries
with the form:

.. code:: Python

   { VFB_id : [{ db: <db> : acc : <acc> }]
   # Return if `reverse_return` is True:
   { acc : [{ db: <db> : vfb_id : <VFB_id> }]
