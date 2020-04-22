from .owl.owlery_query_tools import OWLeryConnect
from .neo.neo4j_tools import Neo4jConnect, get_lookup, gen_simple_report

class VfbConnect():
    def __init__(self, neo_connection = None,
                 owlery_connection=None):
        defaults = {
            'neo': {
                "endpoint": "http://pdb.virtualflybrain.org",
                "usr": "neo4j",
                "pwd": "neo4j"
            },
            "owlery": {
                "endpoint": "http://owl.virtualflybrain.org/kbs/vfb/"
            }
        }
        if not neo_connection:
            self.nc = Neo4jConnect(**defaults['neo'])
        else:
            self.nc = Neo4jConnect(**neo_connection)
        if not owlery_connection:
            self.nc = Neo4jConnect(**defaults['endpoint'])



def get_terms_by_region(region, cells_only=False, verbose=True):
    """Generate JSON reports for all terms relevant to
     annotating some specific region,
    optionally limited by to cells"""
    oc = OWLeryConnect(lookup=get_lookup(limit_by_prefix=['FBbt']))
    preq = ''
    if cells_only:
        preq = "'cell' that "
    owl_query = preq + "'overlaps' some '%s'" % region
    if verbose:
        print("Running query: %s" % owl_query)

    terms = oc.get_subclasses(owl_query, query_by_label=True)
    if verbose:
        print("Found: %d terms" % len(terms))
    return gen_simple_report(terms)

def get_subclasses(term,  direct = False):
    """Generate JSON report of all subclasses of the submitted term."""
    oc = OWLeryConnect(lookup=get_lookup(limit_by_prefix=['FBbt']))
    terms = oc.get_subclasses("'%s'" % term, query_by_label=True)
    return gen_simple_report(terms)

def get_superclasses(term,  direct = False):
    """Generate JSON report of all subclasses of the submitted term."""
    oc = OWLeryConnect(lookup=get_lookup(limit_by_prefix=['FBbt']))
    terms = oc.get_subclasses("'%s'" % term, query_by_label=True)
    return gen_simple_report(terms)





