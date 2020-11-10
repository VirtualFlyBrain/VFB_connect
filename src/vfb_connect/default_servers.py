
# TODO refactor as dataclass for easier IDE support

def get_default_servers():
    return {
        'neo_endpoint':"http://pdb.p2.virtualflybrain.org",
        'neo_credentials': ('neo4j', 'neo4j'),
        'owlery_endpoint': "http://owl.p2.virtualflybrain.org/kbs/vfb/"
    }