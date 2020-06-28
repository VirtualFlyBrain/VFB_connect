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

    def tearDown(self):
        self.nc.commit_list(["MATCH (t:Test { fu: 'bar' }) DELETE t"])


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
