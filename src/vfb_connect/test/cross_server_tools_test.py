import unittest
from ..cross_server_tools import VfbConnect


class VfbConnectTest(unittest.TestCase):

    def setUp(self):
        self.vc = vc = VfbConnect()

    def test_get_term_info(self):
        self.assertTrue(self.vc.neo_query_wrapper.get_type_TermInfo('FBbt_00003686'))
        self.assertTrue(
            self.vc.neo_query_wrapper.get_DataSet_TermInfo('Ito2013'))
        self.assertTrue(
            self.vc.neo_query_wrapper.get_anatomical_individual_TermInfo('VFB_00010001'))

    def test_get_term_by_region(self):
        self.assertTrue(
            self.vc.get_terms_by_region('fan-shaped body'))

    def test_get_subclasses(self):
        self.assertTrue(
            self.vc.get_subclasses('fan-shaped body layer'))

