import requests
import warnings
import re
import json

## MVP: queries when passed a curie map
## desireable: obo curies automatically generated from query string.





class OWLeryConnect:

    def __init__(self,
                 endpoint="http://owl.virtualflybrain.org/kbs/vfb/",
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
              query, query_by_label=False, direct=False):
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
            return r.json()[return_type]
        else:
            warnings.warn(str(r.content))
            return False

    def get_subclasses(self, query, query_by_label=False, direct=False):
        """Get subclasses of
           """
        return self.query(query_type='subclasses', return_type='superClassOf',
                          query=query, query_by_label=query_by_label,
                          direct=direct)

    def get_superclasses(self, query, query_by_label=False, direct=False):
        """Get subclasses of
           """
        return self.query(query_type='superclasses', return_type='subClassOf',
                          query=query, query_by_label=query_by_label,
                          direct=direct)


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





