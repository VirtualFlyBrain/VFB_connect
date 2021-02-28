'''
Created on Oct 24, 2016

@author: davidos
'''
import unittest
from ..neo4j_tools import Neo4jConnect
from vfb_connect.neo.query_wrapper import QueryWrapper


# TODO- pull over core nc tests from VFB_neo4j


class NeoQueryWrapperTest(unittest.TestCase):

    def setUp(self):
        # Using this as a convenient way to wrap default neo server call
        self.qw = QueryWrapper()

    def test_get_term_info(self):
        fu = self.qw.get_TermInfo(['FBbt_00003686', 'VFB_00010001', 'Ito2013'])
        self.assertTrue(
            len(fu) == 3)

    def test_get_type_term_info(self):
        self.assertTrue(self.qw.get_type_TermInfo(short_forms=['FBbt_00003686']))
        self.assertTrue(self.qw.get_type_TermInfo(short_forms=['FBbt_00003686'], summary=True))

    def test_get_DataSet_TermInfo(self):
        self.assertTrue(
            self.qw.get_DataSet_TermInfo(['Ito2013']))

    def test_get_anatomical_individual_TermInfo(self):
        self.assertTrue(
            self.qw.get_anatomical_individual_TermInfo(['VFB_00010001']))
        self.assertTrue(
            self.qw.get_anatomical_individual_TermInfo(['VFB_00010001'], summary=True))

    def test_get_terms_by_xref(self):
        self.assertTrue(self.qw.get_terms_by_xref(['Trh-F-500041'], db='FlyCircuit'))

    def test_get_vfb_id_by_xref(self):
        self.assertTrue(self.qw.xref_2_vfb_id(['Trh-F-500041'], db='FlyCircuit'))
        self.assertTrue(self.qw.xref_2_vfb_id(db='FlyCircuit'))

    def test_get_xref_by_vfbid(self):
        self.assertTrue(self.qw.vfb_id_2_xrefs(['VFB_00014110'], db='FlyCircuit'))

    def test_get_image_by_filename(self):
        # super slow!
#        self.assertTrue(
#            self.vc.neo_query_wrapper.get_images_by_filename(
#                ['JFRC2_MBON-b1-a.nrrd']))
        self.assertTrue(
            self.qw.get_images_by_filename(
                ['JFRC2_MBON-b1-a.nrrd']))
        self.assertTrue(
            self.qw.get_images_by_filename(
                ['JFRC2_MBON-b1-a.nrrd'], dataset='Aso2014'))

    def test_get_datasets(self):
        self.assertGreater(len(self.qw.get_datasets()), 10)
        self.assertGreater(len(self.qw.get_datasets(summary=True)), 10)

    def test_get_templates(self):
        self.assertGreater(len(self.qw.get_templates()), 2)
        self.assertGreater(len(self.qw.get_templates(summary=True)), 2)


class Neo4jConnectTest(unittest.TestCase):

    def setUp(self):
        self.nc = Neo4jConnect()

    def test_lookup_gen(self):
        lookup = self.nc.get_lookup(limit_by_prefix=['FBbt'])
        print()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
