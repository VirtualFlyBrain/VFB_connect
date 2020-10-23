'''
Created on Oct 24, 2016

@author: davidos
'''
import unittest
from ...cross_server_tools import VfbConnect

# TODO- pull over core nc tests from VFB_neo4j

class NewQueryWrapperTest(unittest.TestCase):

    def setUp(self):
        # Using this as a convenient way to wrap default neo server call
        self.vc = VfbConnect()


    def test_get_term_info(self):
        self.assertTrue(self.vc.neo_query_wrapper.get_type_TermInfo(['FBbt_00003686']))
        self.assertTrue(self.vc.neo_query_wrapper.get_type_TermInfo(short_forms=['FBbt_00003686']))
        self.assertTrue(
            self.vc.neo_query_wrapper.get_DataSet_TermInfo(['Ito2013']))
        self.assertTrue(
            self.vc.neo_query_wrapper.get_anatomical_individual_TermInfo(['VFB_00010001']))
        self.assertTrue(
            len(self.vc.neo_query_wrapper.get_TermInfo(['FBbt_00003686', 'VFB_00010001', 'Ito2013'])) == 3)

    def test_get_terms_by_xref(self):
        self.assertTrue(self.vc.neo_query_wrapper.get_terms_by_xref(['Trh-F-500041'], db='FlyCircuit'))

    def test_get_vfb_id_by_xref(self):
        self.assertTrue(self.vc.neo_query_wrapper.xref_2_vfb_id(['Trh-F-500041'], db='FlyCircuit'))
        self.assertTrue(self.vc.neo_query_wrapper.xref_2_vfb_id(db='FlyCircuit'))

    def test_get_xref_by_vfbid(self):
        self.assertTrue(self.vc.neo_query_wrapper.vfb_id_2_xrefs(['VFB_00014110'], db='FlyCircuit'))

    def test_get_image_by_filename(self):
        # super slow!
#        self.assertTrue(
#            self.vc.neo_query_wrapper.get_images_by_filename(
#                ['JFRC2_MBON-b1-a.nrrd']))
        self.assertTrue(
            self.vc.neo_query_wrapper.get_images_by_filename(
                ['JFRC2_MBON-b1-a.nrrd'], dataset='Aso2014'))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
