'''
Created on Oct 24, 2016

@author: davidos
'''
import unittest
from uk.ac.ebi.vfb.neo4j.neo4j_tools import neo4j_connect, neo4jContentMover, results_2_dict_list
import pandas as pd

class Test_commit(unittest.TestCase):
    
    def setUp(self):
        self.nc = neo4j_connect('http://localhost:7474', 'neo4j', 'neo4j')

    def test_neo_create_node(self): 
        # Quite a minimal test...
        self.assertTrue(expr=self.nc.commit_list(["CREATE (t:Test { fu: 'bar' })"]),
                        msg="fu")

    def test_commit_from_remote_csv(self):
        # Quite a minimal test...
        self.nc.commit_csv(url='https://neo4j.com/docs/developer-manual/3.3/csv/artists-with-headers.csv',
                           statement="MERGE (:Artist { name: line.Name, year: toInteger(line.Year)})")

        q = self.nc.commit_list(["MATCH (a:Artist { name: 'ABBA'})"
                                 "RETURN a.year as y"])
        qr = results_2_dict_list(q)
        for r in qr:
            assert r['y'] == 1992  # Note - this required cast from string to int.

    def test_commit_from_local_csv(self):
        dl = [{'fu': 'A', 'bar': 'B'}, {'fu': 'D', 'bar': 'E'}]
        df = pd.DataFrame.from_records(dl)
        self.nc.commit_csv('file:///type_by_name_test.tsv',
                           statement='CREATE (n:fu { id : line.fu})')
        # Needs correct setup of neo filepaths




    def tearDown(self):
        self.nc.commit_list(["MATCH (t:Test { fu: 'bar' }) DELETE t"])




class TestContentMover(unittest.TestCase):

    def setUp(self):
        To = neo4j_connect('http://localhost:7474', 'neo4j', 'neo4j')
        From = neo4j_connect('http://kb.virtualflybrain.org', 'neo4j', 'neo4j')
        self.ncm = neo4jContentMover(From=From, To=To)

    def testMoveNode(self):
        match = "MATCH (n:Class { label : 'adult brain' }) "
        self.ncm.move_nodes(match,
                            key='iri')

    def testMoveEdges(self):
        self.ncm.move_nodes(match="MATCH (n:Individual { short_form : 'VFB_00000001' })",
                            key='iri')
        self.ncm.move_nodes(match="MATCH (n:Class { label : 'neuron' }) ",
                            key='iri')
        self.ncm.move_edges(match="MATCH (s:Individual { short_form : 'VFB_00000001'})"
                                  "-[r]-(o:Class { label : 'neuron' })",
                            node_key='iri')
        query = self.ncm.To.commit_list(["MATCH (s:Individual { short_form : 'VFB_00000001' })"
                                        "-[r]-(o:Class { label : 'neuron' }) "
                                        "RETURN type(r) as rtype"])
        query_results = results_2_dict_list(query)
        for q in query_results:
            assert q['rtype'] == 'INSTANCEOF'

    def testMoveNodeLabels(self):
        self.ncm.To.commit_list(["CREATE (n { short_form : 'VFB_00000002' })"])
        self.ncm.move_node_labels(match="MATCH (n { short_form : 'VFB_00000002' })",
                                  node_key='short_form')
        query = self.ncm.To.commit_list(["MATCH (n { short_form : 'VFB_00000002' })"
                                         "RETURN labels(n) as nlab"])
        query_results = results_2_dict_list(query)

        assert 'Individual' in query_results[0]['nlab']

    def tearDown(self):
        self.ncm.To.commit_list(["MATCH (x)-[r]-(y) DELETE r", "MATCH (n) delete (n)"])
        return





if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
