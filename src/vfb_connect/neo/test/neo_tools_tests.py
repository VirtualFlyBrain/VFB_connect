'''
Created on Oct 24, 2016

@author: davidos
'''
import unittest
from ..neo4j_tools import Neo4jConnect, dict_cursor
import pandas as pd

class Test_commit(unittest.TestCase):
    
    def setUp(self):
        self.nc = Neo4jConnect('http://localhost:7474', 'neo4j', 'neo4j')

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
        qr = dict_cursor(q)
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










if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
