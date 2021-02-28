#!/usr/bin/env python3
import requests
import json
import warnings
import re
import time
from datetime import timedelta
import math
import argparse
from ..default_servers import get_default_servers


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
    """Yield successive n-sized chunks from l."""
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
    handle multi-statement POST queries, return results and report errors."""
    # Return results might be better handled in the case of multiple statements - especially when chunked.
    # Not connection with original query is kept.

    def __init__(self, endpoint = get_default_servers()['neo_endpoint'],
                 usr=get_default_servers()['neo_credentials'][0],
                 pwd=get_default_servers()['neo_credentials'][1]):
        self.base_uri = endpoint
        self.usr = usr
        self.pwd = pwd
        self.test_connection()
       
    def commit_list(self, statements, return_graphs = False):
        """Commit a list of statements to neo4J DB via REST API.
        Prints requests status and warnings if any problems with commit.
            - statements = list of cypher statements as strings
            - return_graphs, optionally specify graphs to be returned in JSON results.
        Errors prompt warnings, not exceptions, and cause return  = FALSE.
        Returns results list of results or False if any errors are encountered."""
        cstatements = []
        if return_graphs:
            for s in statements:
                cstatements.append({'statement': s, "resultDataContents" : [ "row", "graph" ]})
        else:        
            for s in statements:
                cstatements.append({'statement': s}) # rows an columns are returned by default.
        payload = {'statements': cstatements}
        response = requests.post(url = "%s/db/data/transaction/commit" 
                                 % self.base_uri, auth = (self.usr, self.pwd) ,
                                  data = json.dumps(payload))
        if self.rest_return_check(response):
            return response.json()['results']
        else:
            return False
        
        
    def commit_list_in_chunks(self, statements, verbose=False, chunk_length=1000):
        """Commit a list of statements to neo4J DB via REST API, split into chunks.
        cypher_statments = list of cypher statements as strings
        base_uri = base URL for neo4J DB
        Default chunk size = 1000 statements. This can be overridden by KWARG chunk_length.
        Returns a list of results. Output is indistinguishable from output of commit_list (i.e. 
        chunking is not reflected in results list).
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
        """Checks status response to post. Prints warnings to STDERR if not OK.
        If OK, checks for errors in response. Prints any present as warnings to STDERR.
        Returns True STATUS OK and no errors, otherwise returns False.
        """
        if not (response.status_code == 200):
            warnings.warn("Connection error: %s (%s)" % (response.status_code, response.reason))
            return False
        else:
            j = response.json()
            if j['errors']:
                for e in j['errors']:
                    warnings.warn(str(e))
                return False
            else:
                return True
            
    def test_connection(self):
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

    def get_lookup(self, limit_by_prefix=None, include_individuals=False,
                   limit_properties_by_prefix=('RO', 'BFO', 'VFBext')):

        """Generate a name:ID lookup from a VFB neo4j DB, optionally restricted by a list of prefixes
        limit_by_prefix -  Optional list of id prefixes for limiting lookup.
        credentials - default = production DB
        include_individuals: If true, individuals included in lookup.
        """
        if limit_by_prefix:
            regex_string = '.+|'.join(limit_by_prefix) + '.+'
            where = " WHERE a.short_form =~ '%s' " % regex_string
        else:
            where = ''
        neo_labels = ['Class']
        if include_individuals:
            neo_labels.append('Individual')
        out = []
        for l in neo_labels:
            lookup_query = "MATCH (a:%s) %s RETURN a.short_form as id, a.label as name" % (l, where)
            q = self.commit_list([lookup_query])
            out.extend(dict_cursor(q))
            lookup_query = "MATCH (a:%s) %s AND exists(a.symbol) " \
                           "RETURN a.short_form as id, a.symbol[0] as name" % (l, where)
            q = self.commit_list([lookup_query])
            out.extend(dict_cursor(q))
        # All ObjectProperties wanted, irrespective of ID
        if limit_properties_by_prefix:
            regex_string = '.+|'.join(limit_properties_by_prefix) + '.+'
            where = " WHERE a.short_form =~ '%s' " % regex_string
        else:
            where = ''
        property_lookup_query = "MATCH (a:ObjectProperty) " \
                                " " + where + " " \
                                "RETURN a.short_form as id, a.label as name"
        q = self.commit_list([property_lookup_query])
        out.extend(dict_cursor(q))
        lookup = {x['name']: x['id'].replace('_', ':') for x in out}
        # print(lookup['neuron'])
        return lookup


def dict_cursor(results):
    """Takes JSON results from a neo4J query and turns them into a list of dicts.
    """
    dc = []
    for n in results:
        # Add conditional to skip any failures
        if n:
            for d in n['data']:
                dc.append(dict(zip(n['columns'], d['row'])))
    return dc


def escape_string(strng):
    # Simple escaping for strings used in neo queries.
    if type(strng) == str:
        strng = re.sub(r'\\', r'\\\\', strng)
        strng = re.sub("'", "\\'", strng)
        strng = re.sub('"', '\\"', strng)        
    return strng


