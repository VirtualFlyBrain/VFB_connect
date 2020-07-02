import unittest
from ..cross_server_tools import VfbConnect


class VfbConnectTest(unittest.TestCase):

    def setUp(self):
        self.vc = vc = VfbConnect()

    def test_get_term_info(self):
        self.assertTrue(self.vc.neo_query_wrapper.get_type_TermInfo(['FBbt_00003686']))
        self.assertTrue(
            self.vc.neo_query_wrapper.get_DataSet_TermInfo(['Ito2013']))
        self.assertTrue(
            self.vc.neo_query_wrapper.get_anatomical_individual_TermInfo(['VFB_00010001']))
        self.assertTrue(
            len(self.vc.neo_query_wrapper.get_TermInfo(['FBbt_00003686', 'VFB_00010001', 'Ito2013'])) == 3)
    
    def test_get_by_xref(self):
        self.assertTrue(self.vc.neo_query_wrapper.get_terms_by_xref(['Trh-F-500041'], db='FlyCircuit'))

    def test_get_vfb_id_by_xref(self):
        self.assertTrue(self.vc.neo_query_wrapper.xref_2_vfb_id(['Trh-F-500041'], db='FlyCircuit'))

    def test_get_xref_by_vfbid(self):
        self.assertTrue(self.vc.neo_query_wrapper.vfb_id_2_xrefs(['VFB_00014110'], db='FlyCircuit'))

    def test_get_term_by_region(self):
        self.assertTrue(
            self.vc.get_terms_by_region("fan-shaped body"))

    def test_get_subclasses(self):
        self.assertTrue(
            self.vc.get_subclasses("fan-shaped body layer"))

