# VFB_connect output formats

## VFB_JSON

A JSON representation of the information displayed in VFB term information
reports.

The confirms to a standard JSON schema: [raw schema docs](https://github.com/VirtualFlyBrain/VFB_json_schema/blob/master/src/json_schema/vfb_termInfo.json);
[schema in browsable form]().

## Summary reports

Summary reports provide a high-level, tabular summary of VFB term information,
provided as a list of dictionaries in JSON, which can be easily loaded into
Python Pandas:

```Python
import pandas
df = pd.DataFrame.from_records(vc.<some method call>)  # Add example
```


...


| Applies to | Column name | content |
| -- | -- | -- |
| all | label |  name of entity |
| all | symbol | short symbol for entity (if any) |
| all | id | VFB ID of entity |
| all | tags | tags associated with entity (gross class; data flags) |
| anatomical types & individuals | parents_label | parent class labels (`|` delim)" |
| anatomical types & individuals | parents_id | parent classes IDs (`|` delim) |
| anatomical individuals | data_source | ID of data_source |
| anatomical individuals | accession | ID of individual in data_source |
| anatomical individuals | dataset | dataset(s) individual belongs to (`|` delim) |
| anatomical individuals | templates | template(s) registered to (`|` delim) |
| anatomical individuals | license | license data is available under |
| dataset | description | DataSet description, if present |
| dataset | miniref | minimal information for DataSet reference |
| dataset | FlyBase | FlyBase ID for DataSet reference |
| dataset | PMID | PMID for DataSet reference |
| dataset | DOI | DOI for DataSet reference |

### Image manifest

Image download methods save an image manifest to disk, consisting of a tsv with summary info for
anatomical individuals depicted in the the downloaded images, with an addition column containing filenames.


## ID Mappings

Mappings between VFB IDs and external IDs are provided as dictionaries with
the form:

```Python
{ VFB_id : [{ db: <db> : acc : <acc> }]}
# OR
{ acc : [{ db: <db> : vfb_id : <VFB_id> }]}
```

This structure is necessary because the relationship of VFB_id and external identifier my not always be 1:1. 
ID mapping methods come with an option to switch between the two representations.

## Connectomics & neuron similarity reports

type: type

| column | content |
| -- | -- |
| upstream_neuron_id | VFB id (short_form) of upstream neuron |
| upstream_neuron_name | name of upstream neuron in VFB |
| weight | weight |
| downstream_neuron_id | VFB id (short_form) of downstream neuron |
| downstream_neuron_name |  name of downstream neuron in VFB |
| upstream_class | upstream neuron type(s) (name; `|` delim if multiple typing) |
| downstream_class | downstream neuron type(s) (name; `|` delim if multiple typing) |


| up_data_source |  |
| up_accession | |
| down_source | |
| down_accession | |

Individual: type

| column | content |
| -- | -- |
| query_neuron_id | VFB id (short_form) of query neuron |
| query_neuron_name | name of query neuron in VFB |
| weight | weight |
| target_neuron_id | VFB id (short_form) of target neuron | 
| target_neuron_name | name of target neuron in VFB |

Similarity

| column | content |
| id |  VFB id (short_form) of target neuron |
| NBLAST_score | |
| label | |
| types | |
| source_id | | 
| accession_in_source | |