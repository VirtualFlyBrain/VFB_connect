Module vfb_connect.cross_server_tools
=====================================

Functions
---------

    
`gen_short_form(iri)`
:   Generate short_form (string) from an iri string
    iri: An iri string

Classes
-------

`VfbConnect(neo_endpoint='http://pdb.virtualflybrain.org', neo_credentials=('neo4j', 'vfb'), owlery_endpoint='http://owl.virtualflybrain.org/kbs/vfb/', lookup_prefixes=('FBbt', 'VFBexp', 'VFBext'))`
:   API wrapper class.  By default this wraps connections to the more basal API endpoints (OWL, Neo4j).
    
    Top level methods combined semantic queries that range across VFB content with neo4j queries, returning detailed
    metadata about anatomical classes and individuals that fulfill these queries.
    
    Methods allowing direct queries cypher queries of the production Neo4j are available under `nc`
    
    Methods for querying Neo4j with arbitrary lists of identifiers to return rich metadata or mappings to external IDs
    are available under `neo_query_wrapper`.
    
    Direct access OWL queries, returning identifiers only, are available via methods under `oc`
    
    Example semantic queries (OWL class expressions).  Note quoting scheme (outer `"` + single quotes for entities).
    
    "'GABAergic neuron'"
    "'GABAeric neuron' that 'overlaps' some 'antennal lobe'"

    ### Methods

    `get_connected_neurons_by_type(self, upstream_type, downstream_type, weight, query_by_label=True, return_dataframe=True)`
    :   Get all synaptic connections between individual neurons of `upstream_type` and `dowstream_type` where
        each of these types is the name of a neuron class/type in VFB.

    `get_images_by_type(self, class_expression, template, image_folder, image_type='swc', query_by_label=True, direct=False)`
    :   Retrieve images of instances of `class_expression` registered to `template` and save to disk,
        along with manifest and references, to `image_folder`. Default image type = swc. Also supported: obj, nrrd, rds, wlz.
        Returns manifest

    `get_instances(self, class_expression, query_by_label=True, direct=False, summary=False)`
    :   Generate JSON report of all instances of class_expression. Instances are specific examples
        of a type/class of structure, e.g. a specific instance of the neuron DA1 adPN from the FAFB_catmaid
         database.  Instances are typically associated with registered 3D image data and may include
         connectomics data.

    `get_neurons_downstream_of(self, neuron, weight, classification=None, query_by_label=True, return_dataframe=True)`
    :   Get all neurons downstream of individual `neuron` (short_form if query_by_label=False, otherwise label)
        with connection strength > threshold.  Optionally restrict target neurons to those specified by
        `classification = 'class expression' e.g. "'Kenyon cell'" or "'neuron' that overlaps 'lateral horn'".

    `get_neurons_upstream_of(self, neuron, weight, classification=None, query_by_label=True, return_dataframe=True)`
    :   Get all neurons upstream of individual `neuron` (short_form if query_by_label=False, otherwise label)
        with connection strength > threshold.  Optionally restrict target neurons to those specified by
        `classification = 'class expression' e.g. "'Kenyon cell'" or "'neuron' that overlaps 'lateral horn'".

    `get_similar_neurons(self, neuron, similarity_score='NBLAST_score', cutoff=None, source=None, return_dataframe=True)`
    :   Get all neurons

    `get_subclasses(self, class_expression, query_by_label=True, direct=False, summary=False)`
    :   Generate JSON report of all subclasses of class_expression.

    `get_superclasses(self, class_expression, query_by_label=True, direct=False, summary=False)`
    :   Generate JSON report of all superclasses of class_expression.

    `get_terms_by_region(self, region, cells_only=False, verbose=False, query_by_label=True, summary=True)`
    :   Generate JSON reports for all terms relevant to
         annotating some specific region,
        optionally limited by to cells

    `get_vfb_link(self, short_forms: <built-in function iter>, template)`
    :   Takes a list of VFB IDs (short_forms) and the name (label) of a template.
        Returns a link to VFB loading all available images
        of neurons on that template.

    `get_gene_function_filters(self)`
    :   Returns a list of all unique gene function labels in the database in alphabetical order.

    `get_transcriptomic_profile(self, cell_type, gene_type=False, return_dataframe=True)`
    :   Takes a cell_type (name, ID or symbol) from the Drosophila anatomy ontology as a String.
        Returns transcriptomics data for clusters annotated as the given cell_type (and subtypes).
        Can optionally be restricted to genes of a particular function by specifying gene_type as a String.
        Available gene functions can be retrieved by running get_gene_function_filters().
