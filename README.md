# VFB_connect [![Build Status](https://travis-ci.com/VirtualFlyBrain/VFB_connect.svg?branch=master)](https://travis-ci.com/VirtualFlyBrain/VFB_connect)

  * VFB connect wraps is a Python lib (to be published on PyPi) that wraps data/knowledgeBase query endpoints and returns VFB_json.
  * VFB connect will form the basis of a VFB REST API with a swagger interface.  This will re-use some of the architecture of the ingest API.
  
  
  ## Some examples:
  
 ```python

from vfb_connect.cross_server_tools import VfbConnect

# VFB connect object wraps connections and queries to public VFB servers.

vc=VfbConnect()

# Get TermInfo for Types/Classes, DataSets and anatomical individuals.

vc.neo_query_wrapper.get_type_TermInfo('FBbt_00003686')

vc.neo_query_wrapper.get_DataSet_TermInfo('Ito02013')

vc.neo_query_wrapper.get_anatomical_individual_TermInfo('VFB_00010001')

# Get all terms relevant to a brain region (all parts and all overlapping cells.  Query by label supported by default.

vc.get_terms_by_region('fan-shaped body')

```

TermInfo conforms to [VFB_json_schema](https://github.com/VirtualFlyBrain/VFB_json_schema/blob/master/src/json_schema/vfb_termInfo.json) - see also [mod.json](https://github.com/VirtualFlyBrain/VFB_json_schema/blob/master/src/json_schema/mod.json)
