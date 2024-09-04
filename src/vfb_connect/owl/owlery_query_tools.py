import requests
import re
import json
from ..default_servers import get_default_servers


def gen_short_form(iri):
    """Generate short_form (string) from an iri string,
    assuming short_form delimiters, in order of precedence:
    '#' '/'.
    :param iri: An iri string
    :return: short_form
    """
    return re.split('/|#', iri)[-1]

class OWLeryConnect:

    """Wrapper class for querying the VFB OWLery endpoint.
    Unless you have specialist configuration needs, it is
    better to access this object with full default configurations
    from VfbConnect.oc.

        :param endpoint: owlery REST endpoint
        :param lookup: Dict of name: ID;
        :param: obo_curies: list of prefixes for generation of OBO curies.
            Default: ('FBbt', 'RO')
        :param: curies: Dict of curies"""

    def __init__(self,
                 endpoint=get_default_servers()['owlery_endpoint'],
                 lookup=None,
                 obo_curies=('FBbt', 'RO', 'BFO'),
                 curies=None,
                 obo_format=True):
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
            self._add_obo_curies(obo_curies)

    def _add_obo_curies(self, prefixes):

        obolib = "http://purl.obolibrary.org/obo/"
        c = {p : obolib + p + '_' for p in prefixes}
        self.curies.update(c)

    def query(self, query_type, return_type,
              query, query_by_label=True, direct=False, verbose=False):
        """
        A wrapper for querying Owlery Endpoints.  See
        https://owlery.phenoscape.org/api/ for doc

        :param query_type: Options: subclasses, superclasses,
        equivalent, instances, types
        :param query: 'Manchester syntax query with owl entities as <iri>,
         curie (supporting curies declared on object)
         or single quoted label (if query_by_label isTrue)
        :param query_by_label: Boolean. Default False.
        :param direct: Boolean. Default False. Determines T/F
        :param verbose - print verbose output to stdout for debugging purposes.
        :return: list of IRIs.
        """
        owl_endpoint = self.owlery_endpoint + query_type +"?"
        if query_by_label:
            query = self.labels_2_ids(query)
        if verbose:
            print("Running query: " + query) 
        payload = {'object': query, 'prefixes': json.dumps(self.curies),
                   'direct': direct}
        # print(payload)
        r = requests.get(url=owl_endpoint, params=payload)
        if verbose:
            print("Query URL: " + r.url)
        if r.status_code == 200:
            if verbose:
                print("\033[32mQuery results:\033[0m " + str(len(r.json()[return_type])))
            return r.json()[return_type]
        else:
            print("\033[31mConnection Error:\033[0m " + str(r.content))
            return False

    def get_subclasses(self, query, query_by_label=True, direct=False, return_short_forms=True, verbose=False):
        """Generate list of IDs of all subclasses of class_expression.

                :param class_expression: A valid OWL class expression, e.g. the name of a class.
                :param query_by_label: Optional.  If `False``, class_expression takes CURIEs instead of labels.  Default `False`
                :param direct: Return direct subclasses only.  Default `False`
                :param return_short_forms: Optional.  If `True`, returns short_forms instead of IRIs. Default `True`
                :return: Returns a list of terms as nested python data structures following VFB_json or a summary_report_json
                :rtype: list of IRIs or short_forms (depending on return_short_form option)
                """
        out = self.query(query_type='subclasses', return_type='superClassOf',
                          query=query, query_by_label=query_by_label,
                          direct=direct, verbose=verbose)
        if not isinstance(out,list):
            print("\033[33mWarning:\033[0m No results! This is likely due to a query error")
            print("Query: " + query)
            print("Results: " + str(self.query(query_type='subclasses', return_type='superClassOf',
                          query=query, query_by_label=query_by_label,
                          direct=direct, verbose=True)))
            return []
        if return_short_forms:
            return list(map(gen_short_form, out))
        else:
            return out

    def get_instances(self, query, query_by_label=True, direct=False, return_short_forms=True, verbose=False):
        """Generate list of IDs of all instances of class_expression.

                :param class_expression: A valid OWL class expression, e.g. the name of a class.
                :param query_by_label: Optional.  If `False``, class_expression takes CURIEs instead of labels.  Default `False`
                :param direct: Return direct instances only.  Default `False`
                :param return_short_forms: Optional.  If `True`, returns short_forms instead of IRIs. Default `True`
                :return: Returns a list of terms as nested python data structures following VFB_json or a summary_report_json
                :rtype: list of IRIs or short_forms (depending on return_short_form option)
                """
        out = self.query(query_type='instances', return_type='hasInstance',
                          query=query, query_by_label=query_by_label,
                          direct=direct, verbose=verbose)
        if not isinstance(out,list):
            print("\033[33mWarning:\033[0m No results! This is likely due to a query error")
            print("Query: " + query)
            print("Results: " + str(self.query(query_type='subclasses', return_type='superClassOf',
                          query=query, query_by_label=query_by_label,
                          direct=direct, verbose=True)))
            return []
        if return_short_forms:
            return list(map(gen_short_form, out))
        else:
            return out

    def get_superclasses(self, query, query_by_label=True, direct=False, return_short_forms=True, verbose=False):
        """Generate list of IDs of all superclasses of class_expression.

        :param class_expression: A valid OWL class expression, e.g. the name (or CURIE) of a class.
        :param query_by_label: Optional.  If `False``, class_expression takes CURIEs instead of labels.  Default `False`
        :param direct: Return direct instances only.  Default `False`
        :param return_short_forms: Optional.  If `True`, returns short_forms instead of IRIs. Default `True`
        :return: Returns a list of terms as nested python data structures following VFB_json or a summary_report_json
        :rtype: list of IRIs or short_forms (depending on return_short_form option)
        """
        out = self.query(query_type='superclasses', return_type='subClassOf',
                          query=query, query_by_label=query_by_label,
                          direct=direct, verbose=verbose)
        if not isinstance(out,list):
            print("\033[33mWarning:\033[0m No results! This is likely due to a query error")
            print("Query: " + query)
            print("Results: " + str(self.query(query_type='subclasses', return_type='superClassOf',
                          query=query, query_by_label=query_by_label,
                          direct=direct, verbose=True)))
            return []
        if return_short_forms:
            return list(map(gen_short_form, out))
        else:
            return out


    def labels_2_ids(self, query_string):
        """Substitutes labels for CURIEs in a query string

        :param query_string: A OWL class expression in which all labels of OWL entities are single-quoted.  Internal
        single quotes should be escaped with a backslash.
        :return: query string in which labels have been converted to unquoted CURIEs.
        """
        from vfb_connect import vfb
        def subgp1_or_fail(m):
            out = vfb.lookup_id(m.group(1), return_curie=True)
            if not out:
                raise ValueError("Query includes unknown term label: " + query_string)
            else:
                return out

        # This doesn't deal well with failure -> lambda too separate function
        return re.sub(r"'(.+?)'", lambda m: subgp1_or_fail(m), query_string)





