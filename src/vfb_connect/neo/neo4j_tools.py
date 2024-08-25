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

        :param use_cache: If `True`, uses a cached lookup. If `False`, generates a new lookup.
        :param limit_by_prefix:  Optional list of id prefixes for limiting lookup of classes & individuals
        :param include_individuals: If `True`, individuals included in lookup.
        :param limit_properties_by_prefix:  Optional list of id prefixes for limiting lookup of properties.
        :param curies: If `True`, returns CURIEs instead of IDs.
        :param include_synonyms: If `True`, includes synonyms in the lookup.
        :return: A dictionary with names (or synonyms) as keys and their corresponding IDs as values.
        """
        try:
            three_months_in_seconds = 3 * 30 * 24 * 60 * 60
            if cache and os.path.exists(cache) and os.path.getctime(cache) > time.time() - three_months_in_seconds:
                print("Loading cache lookup from disk...") if verbose else None
                with open(cache, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            print(f"Failed to load cache lookup from disk: {e}")

        # Print the loading message
        print("Caching all terms for faster lookup...")

        where = ''
        if limit_type_by_prefix:
            regex_string = '.+|'.join(limit_type_by_prefix) + '.+'
            where += "AND a.short_form =~ '%s' " % regex_string
        where += "AND NOT a:Deprecated "

        out = []
        # All Classes wanted, where id starts with prefix in limit_type_by_prefix
        l = 'Class'
        print(f"Caching {l} names...")
        lookup_query = "MATCH (a:%s) WHERE EXISTS(a.short_form) AND EXISTS(a.label) %s RETURN a.short_form as id, a.label as name" % (l, where)
        q = self.commit_list([lookup_query])
        out.extend(dict_cursor(q))
        print(f"Caching {l} symbols...")
        lookup_query = "MATCH (a:%s) WHERE EXISTS(a.short_form) %s AND exists(a.symbol) " \
                    "RETURN a.short_form as id, a.symbol[0] as name" % (l, where)
        q = self.commit_list([lookup_query])
        out.extend(dict_cursor(q))

        if include_synonyms:
            print(f"Caching {l} synonyms...")
            lookup_query = "MATCH (a:%s) WHERE EXISTS(a.short_form) %s AND EXISTS(a.synonyms) OR (a)-[:has_reference {typ:'syn'}]->(:pub:Individual) " \
                        "UNWIND a.synonyms AS synonym2 " \
                        "RETURN DISTINCT a.short_form AS id, synonym2 AS name " \
                        "UNION ALL MATCH (a)-[r:has_reference {typ:'syn'}]->(:pub:Individual) " \
                        "UNWIND r.value AS synonym1 " \
                        "WITH a.short_form AS id, synonym1 AS synonym " \
                        "RETURN DISTINCT id, synonym AS name" % (l, where)
            q = self.commit_list([lookup_query])
            # Iterate through the results and add only if the label doesn't already exist to avoid duplicate synonyms e.g. cell
            name_to_id = {item['name']: item['id'] for item in out}
            print(f"Initial lookup contains {len(name_to_id)} entries") if verbose else None
            print(f"Result for cell: {name_to_id['cell']}") if verbose else None
            existing_names = set(name_to_id.keys())
            for result in dict_cursor(q):
                if not result['name'] in existing_names:
                    out.append(result)
                    existing_names.add(result['name'])
                    name_to_id[result['name']] = result['id']
                else:
                    print(f"Skipping duplicate synonym: {result['name']} - {result['id']} in favour or existing {name_to_id[result['name']]}") if verbose and result['id'] != name_to_id[result['name']] else None


        if include_individuals:
            where = "AND NOT a:Deprecated AND NOT a.short_form STARTS WITH 'VFBc_' AND NOT a:Person "
            # If individuals are wanted, get them
            l = 'Individual'
            print(f"Caching {l} names...")
            lookup_query = "MATCH (a:%s) WHERE EXISTS(a.short_form) AND EXISTS(a.label) %s RETURN a.short_form as id, a.label as name" % (l, where)
            q = self.commit_list([lookup_query])
            out.extend(dict_cursor(q))
            print(f"Caching {l} symbols...")
            lookup_query = "MATCH (a:%s) WHERE EXISTS(a.short_form) %s AND exists(a.symbol) " \
                        "RETURN a.short_form as id, a.symbol[0] as name" % (l, where)
            q = self.commit_list([lookup_query])
            out.extend(dict_cursor(q))

            if include_synonyms:
                print(f"Caching {l} synonyms...")
                lookup_query = "MATCH (a:%s) WHERE EXISTS(a.short_form) %s AND EXISTS(a.synonyms) OR (a)-[:has_reference {typ:'syn'}]->(:pub:Individual) " \
                            "UNWIND a.synonyms AS synonym2 " \
                            "RETURN DISTINCT a.short_form AS id, synonym2 AS name " \
                            "UNION ALL MATCH (a)-[r:has_reference {typ:'syn'}]->(:pub:Individual) " \
                            "UNWIND r.value AS synonym1 " \
                            "WITH a.short_form AS id, synonym1 AS synonym " \
                            "RETURN DISTINCT id, synonym AS name" % (l, where)
                q = self.commit_list([lookup_query])
                # Iterate through the results and add only if the label doesn't already exist to avoid duplicate synonyms e.g. cell
                name_to_id = {item['name']: item['id'] for item in out}
                print(f"Initial lookup contains {len(name_to_id)} entries") if verbose else None
                print(f"Result for cell: {name_to_id['cell']}") if verbose else None
                existing_names = set(name_to_id.keys())
                for result in dict_cursor(q):
                    if not result['name'] in existing_names:
                        out.append(result)
                        existing_names.add(result['name'])
                        name_to_id[result['name']] = result['id']
                    else:
                        print(f"Skipping duplicate synonym: {result['name']} - {result['id']} in favour or existing {name_to_id[result['name']]}") if verbose and result['id'] != name_to_id[result['name']] else None

        # All ObjectProperties wanted, irrespective of ID
        if limit_properties_by_prefix:
            match_string = "' OR a.short_form STARTS WITH '".join(limit_properties_by_prefix)
            where = " WHERE a.short_form STARTS WITH '%s' " % match_string
        else:
            where = ''
        print(f"Caching ObjectProperties...")
        property_lookup_query = "MATCH (a:ObjectProperty) " \
                                + where + \
                                "RETURN a.short_form as id, a.label as name"
        q = self.commit_list([property_lookup_query])
        out.extend(dict_cursor(q))

        # All alternative terms for ObjectProperties
        if limit_properties_by_prefix:
            match_string = "' OR a.short_form STARTS WITH '".join(limit_properties_by_prefix)
            where = " WHERE exists(a.alternative_term) and size(a.alternative_term) > 0 and a.short_form STARTS WITH '%s' " % match_string
        else:
            where = ''
        print(f"Caching ObjectProperties alternative labels...")
        property_lookup_query = "MATCH (a:ObjectProperty) " \
                                + where + \
                                "UNWIND a.alternative_term as label " + \
                                "RETURN a.short_form as id, label as name"
        q = self.commit_list([property_lookup_query])

        # Iterate through the results and add only if the label doesn't already exist to avoid duplicate object properties e.g. overlaps
        name_to_id = {item['name']: item['id'] for item in out}
        print(f"Initial lookup contains {len(name_to_id)} entries") if verbose else None
        print(f"Result for overlaps: {name_to_id['overlaps']}") if verbose else None
        existing_names = set(name_to_id.keys())
        for result in dict_cursor(q):
            if not result['name'] in existing_names:
                out.append(result)
                existing_names.add(result['name'])
                name_to_id[result['name']] = result['id']
            else:
                print(f"Skipping duplicate object property: {result['name']} - {result['id']} in favour or existing {name_to_id[result['name']]}") if verbose and result['id'] != name_to_id[result['name']] else None

        # Removing duplicates while maintaining order
        seen = set()
        unique_out = []

        for item in out:
            pair = (item['name'], item['id'])
            if pair not in seen:
                seen.add(pair)
                unique_out.append(item)

        # Construct the final lookup dictionary
        if curies:
            lookup = {x['name']: x['id'].replace('_', ':') for x in unique_out}
            lookup.update({x['id'].replace(':', '_'): x['id'] for x in set(lookup.values())})
        else:
            lookup = {x['name']: x['id'] for x in unique_out}

        # Save the lookup to a cache file
        try:
            if cache:
                with open(cache, 'wb') as f:
                    pickle.dump(lookup, f)
        except Exception as e:
            print(f"Failed to save cache lookup on disk: {e}")
        return lookup



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


