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


'''
Created on 4 Feb 2016

Tools for connecting to the neo4j REST API

@author: davidos
'''



def cli_credentials():
    """Parses command line credentials for Neo4J rest connection;
    Optionally specifcy additional args as a list of dicts with
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
    return Neo4jConnect(base_uri=args.endpoint,
                        usr=args.usr,
                        pwd=args.pwd)


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i+n]
 

        
class Neo4jConnect():
    """Thin layer over REST API to hold connection details, 
    handle multi-statement POST queries, return results and report errors."""
    # Return results might be better handled in the case of multiple statements - especially when chunked.
    # Not connection with original query is kept.
    
    
    def __init__(self, endpoint, usr, pwd):
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


def get_lookup(limit_by_prefix=None,
               credentials=("https://pdb.virtualflybrain.org", "neo4j", "neo4j"),
               include_individuals=False):

    """Generate a name:ID lookup from a VFB neo4j DB, optionally restricted by a lost of prefixes
    limit_by_prefix -  Optional list of id prefixes for limiting lookup.
    credentials - default = production DB
    include_individuals: If true, individuals included in lookup.
    """
    if limit_by_prefix:
        regex_string = ':.+|'.join(limit_by_prefix) + ':.+'
        where = " AND a.obo_id =~ '%s' " % regex_string
    else:
        where = ''
    nc = Neo4jConnect(*credentials)
    neo_labels = ['Class', 'Property']
    if include_individuals:
        neo_labels.append('Individual')
    lookup_query = "MATCH (a:Class) WHERE exists (a.obo_id)" + where + " RETURN a.obo_id as id, a.label as name"
    q = nc.commit_list([lookup_query])
    r = dict_cursor(q)
    lookup = {x['name']: x['id'] for x in r}
    #print(lookup['neuron'])
    property_query = "MATCH (p:Property) WHERE exists(p.obo_id) RETURN p.obo_id as id, p.label as name"
    q = nc.commit_list([property_query])
    r = dict_cursor(q)
    lookup.update({x['name']: x['id'] for x in r})
    #print(lookup['neuron'])
    return lookup

class QueryWrapper(Neo4jConnect):

    def __init__(self, *args, **kwargs):
        super(QueryWrapper, self).__init__(*args, **kwargs)
        query_json = pkg_resources.resource_filename(
                            "vfb_connect",
                            "resources/VFB_TermInfo_queries.json")
        with open(query_json, 'r') as f:
            self.queries = json.loads(f.read())

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
        match = "MATCH (s:Individual)<-[r:hasDbXref]-(i:Entity) " \
                "WHERE i.short_form in %s" % str(vfb_id)
        clause1 = ''
        if db:
            clause1 = "AND s.short_form = '%s'" % db
        clause2 = ''
        if id_type:
            clause2 = "AND r.id_type = '%s'" % id_type
        ret = "RETURN i.short_form as key, " \
              "collect({ db: s.short_form, acc: r.accession}) as mapping"
        if reverse_return:
            ret = "RETURN r.accession as key, " \
                  "collect({ db: s.short_form, vfb_id: i.short_form }) as mapping"
        q = ' '.join([match, clause1, clause2, ret])
        dc = self._query(q)

        return {d['key']: d['mapping'] for d in dc}

    def xref_2_vfb_id(self, acc, db='', id_type='', reverse_return=False):
        """Map an external ID (acc) to a VFB_id
        args:
            acc: list of external DB IDs (accessions)
            db: {optional} database identifier (short_form) in VFB
            id_type: {optional} name of external id type (e.g. bodyId)
        Return:
            dict { VFB_id : [{ db: <db> : acc : <acc> }]}"""
        match = "MATCH (s:Individual)<-[r:hasDbXref]-(i:Entity) " \
                "WHERE r.accession in %s" % str(acc)
        clause1 = ''
        if db:
            clause1 = "AND s.short_form = '%s'" % db
        clause2 = ''
        if id_type:
            clause2 = "AND r.id_type = '%s'" % id_type
        ret = "RETURN r.accession as key, " \
              "collect({ db: s.short_form, vfb_id: i.short_form }) as mapping"
        if reverse_return:
            ret = "RETURN i.short_form as key, " \
                  "collect({ db: s.short_form, acc: r.accession}) as mapping"
        q = ' '.join([match, clause1, clause2, ret])
        print(q)
        dc = self._query(q)
        return {d['key']: d['mapping'] for d in dc}

    def get_terms_by_xref(self, acc, db='', id_type=''):
        """Get terms in VFB corresponding to a
            acc: list of external DB IDs (accession)
            db: {optional} database identifier (short_form) in VFB
            id_type: {optional} name of external id type (e.g. bodyId)"""
        return self.get_TermInfo(list(self.xref_2_vfb_id(acc, db=db, id_type=id_type, reverse_return=True).keys()))

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


    def _get_TermInfo(self, short_forms: list, typ, show_query=False):
        sfl = "', '".join(short_forms)
        qs = Template(self.queries[typ]).substitute(ID=sfl)
        if show_query:
            print(qs)
        return self._query(qs)

    def get_anatomical_individual_TermInfo(self, short_forms):
        return self._get_TermInfo(short_forms, typ='Get JSON for Individual:Anatomy')
    
    def get_type_TermInfo(self, short_forms):
        return self._get_TermInfo(short_forms, typ='Get JSON for Class')

    def get_DataSet_TermInfo(self, short_forms):
        return self._get_TermInfo(short_forms, typ='Get JSON for DataSet')

    def get_template_TermInfo(self, short_forms):
        return self._get_TermInfo(short_forms, typ='Get JSON for Template')


