from .owl.owlery_query_tools import OWLeryConnect
from .neo.neo4j_tools import Neo4jConnect, QueryWrapper, get_lookup, gen_simple_report

class VfbConnect():
    def __init__(self, neo_connection=None,
                 owlery_connection=None):
        defaults = {
            'neo': {
                "endpoint": "http://pdb.virtualflybrain.org",
                "usr": "neo4j",
                "pwd": "neo4j"
            },
            "owlery": {
                "endpoint": "http://owl.virtualflybrain.org/kbs/vfb/",
                "lookup": get_lookup(limit_by_prefix=['FBbt', 'VFBexp'])
            }
        }
        if not neo_connection:
            self.nc = Neo4jConnect(**defaults['neo'])
            self.neo_query_wrapper = QueryWrapper(**defaults['neo'])
        else:
            self.neo_query_wrapper = QueryWrapper(**neo_connection)
        if not owlery_connection:
            self.oc = OWLeryConnect(**defaults['owlery'])
        else:
            self.oc = QueryWrapper(**owlery_connection)



    def get_terms_by_region(self, region, cells_only=False, verbose=False, query_by_label=True):
        """Generate JSON reports for all terms relevant to
         annotating some specific region,
        optionally limited by to cells"""
        preq = ''
        if cells_only:
            preq = "'cell' that "
        owl_query = preq + "'overlaps' some '%s'" % region
        if verbose:
            print("Running query: %s" % owl_query)

        terms = self.oc.get_subclasses(owl_query, query_by_label=query_by_label)
        if verbose:
            print("Found: %d terms" % len(terms))
        return gen_simple_report(terms)

    def get_subclasses(self, term, query_by_label=True, direct=False):
        """Generate JSON report of all subclasses of the submitted term."""
        terms = self.oc.get_subclasses("'%s'" % term, query_by_label=query_by_label)
        return gen_simple_report(terms)

    def get_superclasses(self, term, query_by_label=True, direct=False):
        """Generate JSON report of all subclasses of the submitted term."""
        terms = self.oc.get_subclasses("'%s'" % term, query_by_label=True)
        return gen_simple_report(terms)





