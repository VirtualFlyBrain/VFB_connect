import requests
import warnings
import re
import json
from ..default_servers import get_default_servers

## MVP: queries when passed a curie map
## desireable: obo curies automatically generated from query string.

def gen_short_form(iri):
    """Generate short_form (string) from an iri string
    iri: An iri string"""
    return re.split('/|#', iri)[-1]

class OWLeryConnect:

    def __init__(self,
                 endpoint=get_default_servers()['owlery_endpoint'],
                 lookup=None,
                 obo_curies=('FBbt', 'RO', 'BFO'),
                 curies=None):
        """Endpoint: owlery REST endpoint
           Lookup: Dict of name: ID;
           obo_curies: list of prefixes for generation of OBO curies.
                Default: ('FBbt', 'RO')
           curies: Dict of curie: base"""
        self.owlery_endpoint = endpoint
        if not (lookup):
            self.lookup = {}
        else:
            self.lookup = lookup
        if not curies:
            self.curies = {}
        else:
            self.curies = curies
        if obo_curies:
            self.add_obo_curies(obo_curies)

    def add_obo_curies(self, prefixes):
        obolib = "http://purl.obolibrary.org/obo/"
        c = {p : obolib + p + '_' for p in prefixes}
        self.curies.update(c)

    def query(self, query_type, return_type,
              query, query_by_label=False, direct=False, verbose=False):
        """
        A wrapper for querying Owlery Endpoints.  See
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
        """
        owl_endpoint = self.owlery_endpoint + query_type +"?"
        if query_by_label:
            query = self.labels_2_ids(query)
        print("Running query: " + query)
        payload = {'object': query, 'prefixes': json.dumps(self.curies),
                   'direct': direct}
        # print(payload)
        r = requests.get(url=owl_endpoint, params=payload)
        print("Query URL: " + r.url)
        if r.status_code == 200:
            print("Query results: " + str(len(r.json()[return_type])))
            return r.json()[return_type]
        else:
            warnings.warn(str(r.content))
            return False

    def get_subclasses(self, query, query_by_label=False, direct=False, return_short_forms=False):
        """Get subclasses satisfying  query, where query is an OWL DL is any OWL DL class expression
           """
        out = self.query(query_type='subclasses', return_type='superClassOf',
                          query=query, query_by_label=query_by_label,
                          direct=direct)
        if return_short_forms:
            return list(map(gen_short_form, out))
        else:
            return out

    def get_instances(self, query, query_by_label=False, direct=False, return_short_forms=False):
        """Get instances satisfying query, where query is an OWL DL is any OWL DL class expression
           """
        out = self.query(query_type='instances', return_type='hasInstance',
                          query=query, query_by_label=query_by_label,
                          direct=direct)
        if return_short_forms:
            return list(map(gen_short_form, out))
        else:
            return out

    def get_superclasses(self, query, query_by_label=False, direct=False, return_short_forms=False):
        """Get superclasses satisfying `query`, where `query` is any OWL DL class expression.
           """
        out = self.query(query_type='superclasses', return_type='subClassOf',
                          query=query, query_by_label=query_by_label,
                          direct=direct)
        if return_short_forms:
            return list(map(gen_short_form, out))
        else:
            return out


    def labels_2_ids(self, query_string):
        """Substitutes labels for IDs in a query string"""

        def subgp1_or_fail(m):
            out = self.lookup.get(m.group(1))
            if not out:
                raise ValueError("Query includes unknown term label: " + query_string)
            else:
                return out

        # This doesn't deal well with failure -> lambda too separate function
        return re.sub(r"'(.+?)'", lambda m: subgp1_or_fail(m), query_string)





