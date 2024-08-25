#!/usr/bin/env python3
import pickle
import requests
import json
import re
import time
from datetime import timedelta
import math
import argparse
from ..default_servers import get_default_servers
import os


def cli_credentials():
    """Parses command line credentials for Neo4J rest connection;
    Optionally specify additional args as a list of dicts with
    args required by argparse.add_argument().  Order in list
    specified arg order"""
    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint",
                    help="Endpoint for connection to neo4J prod")
    parser.add_argument("usr",
                    help="username")
    parser.add_argument("pwd",
                    help="password")
#    if additional_args:
#        for a in additional_args:
#            parser.add_argument(**a)  # how to get this to work with non kewyord args
    return parser.parse_args()

def cli_neofj_connect():
    args = cli_credentials()
    return Neo4jConnect(endpoint=args.endpoint,
                        usr=args.usr,
                        pwd=args.pwd)


def chunks(l, n):
    """Yield successive n-sized chunks from l.

    :param l: a list
    :param: n, chunk size"""
    for i in range(0, len(l), n):
        yield l[i:i+n]


# @dataclass
# class Filter:
#     jpath: str
#     label: str
#     value_restriction: None
#
# @dataclass
# class CompoundFilter:
#     primary_filter: Filter
# #    secondary_filters: Array(Filter)
#
# #    image_folder_plus_meta = Filter(jpath="$.channel_image.[*].image.image_folder,template_anatomy")


# def batch_query_dict_opt(func):
#      # Assumes first arg is to be batched and that return value is dict
#      def wrapper_batch(*args, **kwargs):
#          if not (args[1] is None):
#              cs = chunks(args[1], 1000)
#          else:
#              return func(*args, **kwargs)
#          out = dict()
#          for c in cs:
#              arglist = list(args)
#              arglist[1] = c
#              subargs = tuple(arglist)
#              out.update(func(*subargs, **kwargs))
#      return wrapper_batch


class Neo4jConnect:
    """Thin layer over REST API to hold connection details,
    handle multi-statement POST queries, return results and report errors.

    :param endpoint: a neo4j REST endpoint
    :param usr: username (content ignored if credentials not rqd)
    :param pwd: password (content ignored if credentials not rqd)"""
    # Return results might be better handled in the case of multiple statements - especially when chunked.
    # Not connection with original query is kept.

    def __init__(self, endpoint = get_default_servers()['neo_endpoint'],
                 usr=get_default_servers()['neo_credentials'][0],
                 pwd=get_default_servers()['neo_credentials'][1]):
        self.base_uri = endpoint
        self.usr = usr
        self.pwd = pwd
        self.commit = "/db/neo4j/tx/commit"
        self.headers = {'Content-type': 'application/json'}
        if not self.test_connection():
            print("Falling back to Neo4j v3 connection")
            self.commit = "/db/data/transaction/commit"
            self.headers = {}
            if not self.test_connection():
                raise Exception("Failed to connect to Neo4j.")

    def commit_list(self, statements, return_graphs=False):
        """Commit a list of statements to neo4J DB via REST API.
        Errors prompt warnings (STDERR), not exceptions, and cause return = FALSE.

        :param: statements: A list of cypher statements.
        :param: return_graphs: Optional. Boolean. Returns graphs under 'graph' key if True. Default: False
        :Return: List of results or False if any errors are encountered.
        """

        cstatements = []
        if return_graphs:
            for s in statements:
                cstatements.append({'statement': s, "resultDataContents" : [ "row", "graph" ]})
        else:
            for s in statements:
                cstatements.append({'statement': s}) # rows an columns are returned by default.
        payload = {'statements': cstatements}
        response = requests.post(url = "%s%s"
                                 % (self.base_uri, self.commit), auth = (self.usr, self.pwd) ,
                                  data = json.dumps(payload), headers = self.headers)
        if self.rest_return_check(response):
            return response.json()['results']
        else:
            return False

    def commit_list_in_chunks(self, statements, verbose=False, chunk_length=1000):

        """Commit multiple (chunked) commit of statements to neo4J DB via REST API.
         Errors prompt warnings (STDOUT), not exceptions, and cause return = FALSE.

         :param: statements: A list of cypher statements.
         :param: verbose: Boolean. Optionally print periodic reports of progress to STDOUT
         :param: chunk_length. Int. Optional. Set chunk size.  Default = 1000.
         :Return: List of results or False if any errors are encountered. Chunking is not reflected in results.
         """

        chunked_statements = chunks(l = statements, n=chunk_length)
        chunk_results = []
        i = 1
        c_no = math.ceil(len(statements)/chunk_length)
        for c in chunked_statements:
            if verbose:
                start_time = time.time()
                print("Processing chunk of %d of %d starting with: %s" % (i,
                                                                          c_no,
                                                                          c[0].encode('utf8')))
            r = self.commit_list(c)
            if verbose:
                t = time.time() - start_time
                print("Processing took %d seconds for %s statements" % (t, len(c)))
                print("Estimated time to completion: %s." % str(timedelta(seconds=(t*(c_no - i)))))
            if type(r) == list:
                chunk_results.extend(r)
            else:
                chunk_results.append(r)
            i += 1
        return chunk_results

    def commit_csv(self, url, statement, chunk_size=1000, sep=","):
        # May need some configuration to work with file://...
        cypher = "USING PERIODIC COMMIT %d " \
                 "LOAD CSV WITH HEADERS FROM '%s' AS line FIELDTERMINATOR '%s' " \
                 "%s" % (chunk_size, url, sep, statement)
        self.commit_list([cypher])

    def rest_return_check(self, response):
        """Checks status response to post. Prints warnings if not OK.
        If OK, checks for errors in response. Prints any present as warnings.
        Returns True STATUS OK and no errors, otherwise returns False.
        """
        if not (response.status_code == 200):
            print("\033[31mConnection Error:\033[0m %s (%s)" % (response.status_code, response.reason))
            return False
        else:
            j = response.json()
            if j['errors']:
                for e in j['errors']:
                    print("\033[31mQuery Error:\033[0m " + str(e))
                return False
            else:
                return True

    def test_connection(self):
        """Test neo4j endpoint connection"""
        statements = ["MATCH (n) RETURN n LIMIT 1"]
        if self.commit_list(statements):
            return True
        else:
            return False

    def list_all_node_props(self):
        r = self.commit_list(['MATCH (n) with keys(n) AS kl UNWIND kl as k RETURN DISTINCT k'])
        d = dict_cursor(r)
        return [x['k'] for x in d]

    def list_all_edge_props(self):
        r = self.commit_list(['MATCH ()-[r]-() with keys(r) AS kl UNWIND kl as k RETURN DISTINCT k'])
        d = dict_cursor(r)
        return [x['k'] for x in d]

    def get_lookup(self, cache=None, limit_type_by_prefix=('FBbt', 'VFBexp', 'VFBext'), include_individuals=True,
                   limit_properties_by_prefix=('RO', 'BFO', 'VFBext'), curies=False, include_synonyms=True, verbose=False):
        """Generate a name:ID lookup from a VFB neo4j DB, optionally restricted by a list of prefixes.

        :param cache: If a valid cache path is provided, uses a cached lookup. Otherwise, generates a new lookup.
        :param limit_type_by_prefix: Optional list of id prefixes for limiting lookup of classes & individuals.
        :param include_individuals: If `True`, individuals are included in the lookup.
        :param limit_properties_by_prefix: Optional list of id prefixes for limiting lookup of properties.
        :param curies: If `True`, returns CURIEs instead of IDs.
        :param include_synonyms: If `True`, includes synonyms in the lookup.
        :param verbose: If `True`, provides verbose output.
        :return: A dictionary with names (or synonyms) as keys and their corresponding IDs as values.
        """
        try:
            three_months_in_seconds = 3 * 30 * 24 * 60 * 60
            if cache and os.path.exists(cache) and os.path.getctime(cache) > time.time() - three_months_in_seconds:
                if verbose:
                    print("Loading cache lookup from disk...")
                with open(cache, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            print(f"Failed to load cache lookup from disk: {e}")

        print("Caching all terms for faster lookup...")

        out = []
        existing_names = set()

        # Step 1: Load FBbt terms first
        self.load_fb_bt_terms(out, existing_names, include_synonyms, verbose)

        # Step 2: Load individuals next
        if include_individuals:
            self.load_individual_terms(out, existing_names, include_synonyms, verbose)

        # Step 3: Load the rest of the classes (excluding FBbt)
        self.load_other_classes(out, existing_names, limit_type_by_prefix, include_synonyms, verbose)

        return {item['name']: item['id'] for item in out}

    def load_fb_bt_terms(self, out, existing_names, include_synonyms, verbose):
        """Load FBbt terms specifically before other classes.

        :param out: The list to store fetched terms.
        :param existing_names: The set of existing names to avoid duplicates.
        :param include_synonyms: If `True`, includes synonyms in the lookup.
        :param verbose: If `True`, provides verbose output.
        """
        where_clause = "AND a.short_form STARTS WITH 'FBbt' "
        self.execute_and_process_query('Class', where_clause, 'label', out, existing_names, verbose)
        self.execute_and_process_query('Class', where_clause, 'symbol[0]', out, existing_names, verbose)

        if include_synonyms:
            self.execute_and_process_query('Class', where_clause, 'synonyms', out, existing_names, verbose)

    def load_individual_terms(self, out, existing_names, include_synonyms, verbose):
        """Load individual terms.

        :param out: The list to store fetched terms.
        :param existing_names: The set of existing names to avoid duplicates.
        :param include_synonyms: If `True`, includes synonyms in the lookup.
        :param verbose: If `True`, provides verbose output.
        """
        where_clause = "AND NOT a:Deprecated AND NOT a.short_form STARTS WITH 'VFBc_' AND NOT a:Person "
        self.execute_and_process_query('Individual', where_clause, 'label', out, existing_names, verbose)
        self.execute_and_process_query('Individual', where_clause, 'symbol[0]', out, existing_names, verbose)

        if include_synonyms:
            self.execute_and_process_query('Individual', where_clause, 'synonyms', out, existing_names, verbose)

    def load_other_classes(self, out, existing_names, limit_type_by_prefix, include_synonyms, verbose):
        """Load other class terms excluding FBbt.

        :param out: The list to store fetched terms.
        :param existing_names: The set of existing names to avoid duplicates.
        :param limit_type_by_prefix: Optional list of id prefixes for limiting lookup of classes.
        :param include_synonyms: If `True`, includes synonyms in the lookup.
        :param verbose: If `True`, provides verbose output.
        """
        # Exclude 'FBbt' since it's already processed
        other_prefixes = [prefix for prefix in limit_type_by_prefix if prefix != 'FBbt']
        if other_prefixes:
            where_clause = self.construct_where_clause('Class', other_prefixes)
            self.execute_and_process_query('Class', where_clause, 'label', out, existing_names, verbose)
            self.execute_and_process_query('Class', where_clause, 'symbol[0]', out, existing_names, verbose)

            if include_synonyms:
                self.execute_and_process_query('Class', where_clause, 'synonyms', out, existing_names, verbose)

    def construct_where_clause(self, term_type, prefixes):
        """Construct the WHERE clause for the query based on term type and prefix limitations.

        :param term_type: The type of terms to fetch (e.g., 'Class', 'Individual').
        :param prefixes: List of id prefixes for limiting lookup.
        :return: A string representing the WHERE clause for the query.
        """
        where = "AND NOT a:Deprecated "
        if prefixes:
            prefix_conditions = " OR ".join([f"a.short_form STARTS WITH '{prefix}'" for prefix in prefixes])
            where += f"AND ({prefix_conditions}) "
        return where

    def execute_and_process_query(self, term_type, where, property_name, out, existing_names, verbose):
        """Execute a Cypher query and process the results, adding to the output list if not duplicate.

        :param term_type: The type of terms to fetch (e.g., 'Class', 'Individual').
        :param where: The WHERE clause of the query.
        :param property_name: The property to fetch (e.g., 'label', 'symbol[0]', 'synonyms').
        :param out: The list to store fetched terms.
        :param existing_names: The set of existing names to avoid duplicates.
        :param verbose: If `True`, provides verbose output.
        """
        if property_name == 'synonyms':
            query = f"""
                MATCH (a:{term_type}) 
                WHERE EXISTS(a.short_form) {where} AND EXISTS(a.synonyms)
                UNWIND a.synonyms AS synonym
                RETURN DISTINCT a.short_form as id, synonym as name
                UNION ALL
                MATCH (a:{term_type})-[r:has_reference {{typ:'syn'}}]->(:pub:Individual)
                UNWIND r.value AS synonym
                RETURN DISTINCT a.short_form as id, synonym as name
            """
        else:
            query = f"MATCH (a:{term_type}) WHERE EXISTS(a.short_form) {where} AND EXISTS(a.{property_name.split('[')[0]}) " \
                    f"RETURN a.short_form as id, a.{property_name} as name"

        results = self.commit_list([query])

        name_to_id = {item['name']: item['id'] for item in out}
        dc = dict_cursor(results)
        if not dc:
            raise ValueError(f"Lookup failure for: {query}")
        for result in dc:
            if result['name'] not in existing_names:
                out.append(result)
                existing_names.add(result['name'])
                name_to_id[result['name']] = result['id']
            elif verbose and result['id'] != name_to_id[result['name']]:
                print(f"Skipping duplicate: {result['name']} - {result['id']} in favour of existing {name_to_id[result['name']]}")


def dict_cursor(results):
    """Takes JSON results from a neo4J query and turns them into a list of dicts.

    :param results: neo4j query results
    :return: list of dicts
    """
    dc = []
    for n in results:
        # Add conditional to skip any failures
        if n:
            for d in n['data']:
                dc.append(dict(zip(n['columns'], d['row'])))
    return dc


def escape_string(strng):
    """Simple escaping for strings used in neo queries."""
    if type(strng) == str:
        strng = re.sub(r'\\', r'\\\\', strng)
        strng = re.sub("'", "\\'", strng)
        strng = re.sub('"', '\\"', strng)
    return strng


