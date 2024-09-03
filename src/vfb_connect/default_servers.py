
# TODO refactor as dataclass for easier IDE support

def get_default_servers():
    return {
        'neo_endpoint':"http://pdb.v4.virtualflybrain.org",
        'neo_credentials': ('neo4j', 'vfb'),
        'owlery_endpoint': "http://owl.virtualflybrain.org/kbs/vfb/",
        'solr_endpoint': 'http://solr.virtualflybrain.org/solr/ontology/'
    }
