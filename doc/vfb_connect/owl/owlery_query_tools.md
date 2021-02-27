Module vfb_connect.owl.owlery_query_tools
=========================================

Classes
-------

`OWLeryConnect(endpoint='http://owl.virtualflybrain.org/kbs/vfb/', lookup=None, obo_curies=('FBbt', 'RO', 'BFO'), curies=None)`
:   Endpoint: owlery REST endpoint
    Lookup: Dict of name: ID;
    obo_curies: list of prefixes for generation of OBO curies.
         Default: ('FBbt', 'RO')
    curies: Dict of curie: base

    ### Methods

    `add_obo_curies(self, prefixes)`
    :

    `get_instances(self, query, query_by_label=False, direct=False)`
    :   Get instances satisfying query, where query is an OWL DL query

    `get_subclasses(self, query, query_by_label=False, direct=False)`
    :   Get subclasses satisfying  query, where query is an OWL DL query

    `get_superclasses(self, query, query_by_label=False, direct=False)`
    :   Get subclasses of

    `labels_2_ids(self, query_string)`
    :   Substitutes labels for IDs in a query string

    `query(self, query_type, return_type, query, query_by_label=False, direct=False, verbose=False)`
    :   A wrapper for querying Owlery Endpoints.  See
        https://owlery.phenoscape.org/api/ for doc
        :param query_type: Options: subclasses, superclasses,
        equivalent, instances, types
        :param return_type:
        :param query: 'Manchester syntax query with owl entities as <iri>,
         curie (supporting curies declared on object)
         or single quoted label (if query_by_label isTrue)
        :param query_by_label: Boolean. Default False.
        :param direct: Boolean. Default False. Determines T/F
        :param verbose - print verbose output to stdout for debugging purposes.
        :return: