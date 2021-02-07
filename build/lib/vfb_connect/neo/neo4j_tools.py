#!/usr/bin/env python3

import requests
import json
import warnings
import re
import time
from datetime import timedelta
import math
import argparse
from string import Template
import pkg_resources
from ..default_servers import get_default_servers
from inspect import getfullargspec



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


def batch_query(func):
    # Assumes first arg is to be batches and that return value is list. Only works on class methods.
    # There has to be a better way to work with the values of args and kwargs than this!!!!
    def wrapper_batch(*args, **kwargs):
        arg_names = getfullargspec(func).args
        if len(args) > 1:
            arg1v = args[1]
            arg1typ = 'a'
        else:
            arg1v = kwargs[arg_names[1]]
            arg1typ = 'k'
        cs = chunks(arg1v, 2500)
        out = []
        for c in cs:
            if arg1typ == 'a':
                arglist = list(args)
                arglist[1] = c
                subargs = tuple(arglist)
                out.extend(func(*subargs, **kwargs))
            elif arg1typ == 'k':
                kwargdict = dict(kwargs)
                kwargdict[arg_names[1]] = c
                out.extend(func(*args, **kwargdict))
        return out
    return wrapper_batch

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


def gen_simple_report(terms):
    nc = Neo4jConnect("https://pdb.virtualflybrain.org", "neo4j", "neo4j")
    query = """MATCH (n:Class) WHERE n.iri in %s WITH n 
                OPTIONAL MATCH  (n)-[r]->(p:pub) WHERE r.typ = 'syn' 
                WITH n, 
                COLLECT({ synonym: r.synonym, PMID: 'PMID:' + p.PMID, 
                    miniref: p.label}) AS syns 
                OPTIONAL MATCH (n)-[r]-(p:pub) WHERE r.typ = 'def' 
                with n, syns, 
                collect({ PMID: 'PMID:' + p.PMID, miniref: p.label}) as pubs
                OPTIONAL MATCH (n)-[:SUBCLASSOF]->(super:Class)
                RETURN n.short_form as short_form, n.label as label, 
                n.description as description, syns, pubs,
                super.label, super.short_form
                 """ % str(terms)
    q = nc.commit_list([query])
    # add check
    return dict_cursor(q)


from xml.sax import saxutils

class QueryWrapper(Neo4jConnect):

    def __init__(self, *args, **kwargs):
        super(QueryWrapper, self).__init__(*args, **kwargs)
        query_json = pkg_resources.resource_filename(
                            "vfb_connect",
                            "resources/VFB_TermInfo_queries.json")
        with open(query_json, 'r') as f:
            self.queries = json.loads(saxutils.unescape(f.read()))

    def _query(self, q):
        qr = self.commit_list([q])
        if not qr:
            raise Exception('Query failed.')
        else:
            r = dict_cursor(qr)
            if not r:
                warnings.warn('No results returned')
                return []
            else:
                return r

    def get_dbs(self):
        query = "MATCH (i:Individual) " \
                "WHERE 'Site' in labels(i) OR 'API' in labels(i)" \
                "return i.short_form"
        return [d['i.short_form'] for d in self._query(query)]

    def vfb_id_2_xrefs(self, vfb_id, db='', id_type='', reverse_return=False):
        """Map a list of node short_form IDs in VFB to external DB IDs
        Args:
         vfb_id: list of short_form IDs of nodes in the VFB KB
         db: {optional} database identifier (short_form) in VFB
         id_type: {optional} name of external id type (e.g. bodyId)
        Return:
            dict { VFB_id : [{ db: <db> : acc : <acc> }
        """
        match = "MATCH (s:Individual)<-[r:database_cross_reference]-(i:Entity) " \
                "WHERE i.short_form in %s" % str(vfb_id)
        clause1 = ''
        if db:
            clause1 = "AND s.short_form = '%s'" % db
        clause2 = ''
        if id_type:
            clause2 = "AND r.id_type = '%s'" % id_type
        ret = "RETURN i.short_form as key, " \
              "collect({ db: s.short_form, acc: r.accession[0]}) as mapping"
        if reverse_return:
            ret = "RETURN r.accession[0] as key, " \
                  "collect({ db: s.short_form, vfb_id: i.short_form }) as mapping"
        q = ' '.join([match, clause1, clause2, ret])
        dc = self._query(q)
        return {d['key']: d['mapping'] for d in dc}

    def xref_2_vfb_id(self, acc=None, db='', id_type='', reverse_return=False):
        """Map an external ID (acc) to a VFB_id
        args:
            acc: list of external DB IDs (accessions)
            db: {optional} database identifier (short_form) in VFB
            id_type: {optional} name of external id type (e.g. bodyId)
        Return:
            dict { VFB_id : [{ db: <db> : acc : <acc> }]}"""
        match = "MATCH (s:Individual)<-[r:database_cross_reference]-(i:Entity) WHERE"
        conditions = []
        if not (acc is None):
            conditions.append("r.accession[0] in %s" % str(acc))
        if db:
            conditions.append("s.short_form = '%s'" % db)
        if id_type:
            conditions.append("r.id_type = '%s'" % id_type)
        condition_clauses = ' AND '.join(conditions)
        ret = "RETURN r.accession[0] as key, " \
              "collect({ db: s.short_form, vfb_id: i.short_form }) as mapping"
        if reverse_return:
            ret = "RETURN i.short_form as key, " \
                  "collect({ db: s.short_form, acc: r.accession[0]}) as mapping"
        q = ' '.join([match, condition_clauses, ret])
#        print(q)
        dc = self._query(q)
        return {d['key']: d['mapping'] for d in dc}

    @batch_query
    def get_terms_by_xref(self, acc, db='', id_type=''):
        """Get terms in VFB corresponding to a
            acc: list of external DB IDs (accession)
            db: {optional} database identifier (short_form) in VFB
            id_type: {optional} name of external id type (e.g. bodyId)"""
        return self.get_TermInfo(list(self.xref_2_vfb_id(acc,
                                                         db=db,
                                                         id_type=id_type,
                                                         reverse_return=True).keys()))

    def get_images_by_filename(self, filenames, dataset=None):
        """Takes a list of filenames as input and returns a list of image terminfo.
        Optionally restrict by dataset (improves speed)"""
        m = "MATCH (ds:DataSet)<-[has_source]-(ai:Individual)<-[:depicts]" \
            "-(channel:Individual)-[irw:in_register_with]-(tc:Template)"
        w = "WHERE irw.filename[0]in %s" % str([escape_string(f) for f in filenames])
        if dataset:
            w += "AND ds.short_form = '%s'" % dataset
        r = "RETURN ai.short_form"
        dc = self._query(' '.join([m, w, r]))
        return self.get_anatomical_individual_TermInfo([d['ai.short_form']
                                                        for d in dc])

    @batch_query
    def get_TermInfo(self, short_forms):
        pre_query = "MATCH (e:Entity) " \
                    "WHERE e.short_form in %s " \
                    "RETURN e.short_form as short_form, labels(e) as labs " % str(short_forms)
        r = self._query(pre_query)
        out = []
        for e in r:
            if 'Class' in e['labs']:
               out.extend(self.get_type_TermInfo([e['short_form']]))
            elif 'Individual' in e['labs'] and 'Anatomy' in e['labs']:
                out.extend(self.get_anatomical_individual_TermInfo([e['short_form']]))
            elif 'DataSet' in e['labs']:
                out.extend(self.get_DataSet_TermInfo([e['short_form']]))
        return out

    def _get_TermInfo(self, short_forms: list, typ, show_query=True):
        sfl = "', '".join(short_forms)
        qs = Template(self.queries[typ]).substitute(ID=sfl)
        if show_query:
            print(qs)
        return self._query(qs)



    @batch_query
    def get_anatomical_individual_TermInfo(self, short_forms):
        return self._get_TermInfo(short_forms, typ='Get JSON for Individual:Anatomy')

    @batch_query
    def get_type_TermInfo(self, short_forms):
        return self._get_TermInfo(short_forms, typ='Get JSON for Class')

    @batch_query
    def get_DataSet_TermInfo(self, short_forms):
        return self._get_TermInfo(short_forms, typ='Get JSON for DataSet')

    @batch_query
    def get_template_TermInfo(self, short_forms):
        return self._get_TermInfo(short_forms, typ='Get JSON for Template')


