from .owl.owlery_query_tools import OWLeryConnect
from .neo.neo4j_tools import Neo4jConnect, QueryWrapper, re
from .default_servers import get_default_servers

def gen_short_form(iri):
    """Generate short_form (string) from an iri string
    iri: An iri string"""
    return re.split('/|#', iri)[-1]


class VfbConnect:
    def __init__(self, neo_endpoint=get_default_servers()['neo_endpoint'],
                 neo_credentials=get_default_servers()['neo_credentials'],
                 owlery_endpoint=get_default_servers()['owlery_endpoint'],
                 lookup_prefixes=('FBbt', 'VFBexp', 'VFBext')):
        connections = {
            'neo': {
                "endpoint": neo_endpoint,
                "usr": neo_credentials[0],
                "pwd": neo_credentials[1]
            }
        }
        self.nc = Neo4jConnect(**connections['neo'])
        self.neo_query_wrapper = QueryWrapper(**connections['neo'])

        self.oc = OWLeryConnect(endpoint=owlery_endpoint,
                                lookup=self.nc.get_lookup(limit_by_prefix=lookup_prefixes))

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
        return self.neo_query_wrapper.get_type_TermInfo(list(map(gen_short_form, terms)))

    def get_subclasses(self, class_expression, query_by_label=True, direct=False):
        """Generate JSON report of all subclasses of the submitted term."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_subclasses("%s" % class_expression, query_by_label=query_by_label)
        return self.neo_query_wrapper.get_type_TermInfo(list(map(gen_short_form, terms)))

    def get_superclasses(self, class_expression, query_by_label=True, direct=False):
        """Generate JSON report of all subclasses of the submitted term."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_subclasses("%s" % class_expression, query_by_label=query_by_label)
        return self.neo_query_wrapper.get_type_TermInfo(list(map(gen_short_form, terms)))

    def get_images(self, class_expression, query_by_label = True, direct = False):
        """Generate JSON report of all images of the submitted type."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_instances("%s" % class_expression, query_by_label=query_by_label)
        return self.neo_query_wrapper.get_anatomical_individual_TermInfo(list(map(gen_short_form, terms)))





