Module vfb_connect.neo.query_wrapper
====================================

Functions
---------

    
`batch_query(func)`
:   

    
`gen_simple_report(terms)`
:   

    
`pop_from_jpath(jpath, json)`
:   

Classes
-------

`QueryWrapper(*args, **kwargs)`
:   Thin layer over REST API to hold connection details, 
    handle multi-statement POST queries, return results and report errors.

    ### Ancestors (in MRO)

    * vfb_connect.neo.neo4j_tools.Neo4jConnect

    ### Methods

    `get_DataSet_TermInfo(self, short_forms, summary=False)`
    :

    `get_TermInfo(*args, **kwargs)`
    :

    `get_anatomical_individual_TermInfo(self, short_forms, summary=False)`
    :

    `get_dbs(self)`
    :

    `get_images(self, short_forms: <built-in function iter>, template, image_folder, image_type='swc', stomp=False)`
    :   Given an array of `short_forms` for instances, find all images of specified `image_type`
        registered to `template`. Save these to `image_folder` along with a manifest.tsv.  Return manifest as
        pandas DataFrame.

    `get_images_by_filename(self, filenames, dataset=None)`
    :   Takes a list of filenames as input and returns a list of image terminfo.
        Optionally restrict by dataset (improves speed)

    `get_sites(self)`
    :

    `get_template_TermInfo(self, short_forms, summary=False)`
    :

    `get_templates(self)`
    :

    `get_terms_by_xref(*args, **kwargs)`
    :

    `get_type_TermInfo(self, short_forms, summary=False)`
    :

    `vfb_id_2_neuprint_bodyID(self, vfb_id, db='')`
    :

    `vfb_id_2_xrefs(self, vfb_id: <built-in function iter>, db='', id_type='', reverse_return=False)`
    :   Map a list of node short_form IDs in VFB to external DB IDs
        Args:
         vfb_id: list of short_form IDs of nodes in the VFB KB
         db: {optional} database identifier (short_form) in VFB
         id_type: {optional} name of external id type (e.g. bodyId)
        Return if `reverse_return` is False:
            dict { VFB_id : [{ db: <db> : acc : <acc> }
        Return if `reverse_return` is True:
             dict { acc : [{ db: <db> : vfb_id : <VFB_id> }

    `xref_2_vfb_id(self, acc=None, db='', id_type='', reverse_return=False)`
    :   Map an external ID (acc) to a VFB_id
        args:
            acc: list of external DB IDs (accessions)
            db: {optional} database identifier (short_form) in VFB
            id_type: {optional} name of external id type (e.g. bodyId)
        Return:
            dict { VFB_id : [{ db: <db> : acc : <acc> }]}