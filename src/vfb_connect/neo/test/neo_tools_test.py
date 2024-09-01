import unittest
from ..neo4j_tools import Neo4jConnect
from vfb_connect.neo.query_wrapper import QueryWrapper

class NeoQueryWrapperTest(unittest.TestCase):

    def setUp(self):
        # Using this as a convenient way to wrap default neo server call
        self.qw = QueryWrapper()

    def test_get_term_info(self):
        fu = self.qw.get_TermInfo(['FBbt_00003686', 'VFB_00010001', 'Ito2013'], summary=False, return_dataframe=False)
        self.assertEqual(len(fu), 3)

    def test_get_type_term_info(self):
        result = self.qw.get_type_TermInfo(short_forms=['FBbt_00003686'], summary=False, return_dataframe=False)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

        df = self.qw.get_type_TermInfo(short_forms=['FBbt_00003686'])
        self.assertTrue(not df.empty)

    def test_get_DataSet_TermInfo(self):
        df = self.qw.get_DataSet_TermInfo(['Ito2013'])
        self.assertTrue(not df.empty)

    def test_get_anatomical_individual_TermInfo(self):
        result = self.qw.get_anatomical_individual_TermInfo(['VFB_00010001'], summary=False, return_dataframe=False)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

        df = self.qw.get_anatomical_individual_TermInfo(['VFB_00010001'])
        self.assertTrue(not df.empty)

    def test_get_terms_by_xref(self):
        df = self.qw.get_terms_by_xref(['Trh-F-500041'], db='FlyCircuit')
        self.assertTrue(not df.empty)

    def test_get_vfb_id_by_xref(self):
        result = self.qw.xref_2_vfb_id(['Trh-F-500041'], db='FlyCircuit')
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

        result_all = self.qw.xref_2_vfb_id(db='FlyCircuit')
        self.assertIsInstance(result_all, dict)

    def test_get_xref_by_vfbid(self):
        result = self.qw.vfb_id_2_xrefs(['VFB_00014110'], db='FlyCircuit')
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

    def test_get_image_by_filename(self):
        df = self.qw.get_images_by_filename(['JFRC2_MBON-b1-a.nrrd'])
        self.assertTrue(not df.empty)

        df_with_dataset = self.qw.get_images_by_filename(['JFRC2_MBON-b1-a.nrrd'], dataset='Aso2014')
        self.assertTrue(not df_with_dataset.empty)

    def test_get_datasets(self):
        result = self.qw.get_datasets(summary=False)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 10)

        df = self.qw.get_datasets()
        self.assertTrue(not df.empty)
        self.assertGreater(len(df), 10)

    def test_get_templates(self):
        result = self.qw.get_templates(summary=False)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 2)

        df = self.qw.get_templates()
        self.assertTrue(not df.empty)
        self.assertGreater(len(df), 2)


class Neo4jConnectTest(unittest.TestCase):

    def setUp(self):
        self.nc = Neo4jConnect()

    def test_lookup_gen(self):
        lookup = self.nc.get_lookup(limit_type_by_prefix=['FBbt'], include_individuals=False, include_synonyms=False)
        self.assertIsNotNone(lookup)  # Added an assertion to validate the lookup

if __name__ == "__main__":
    unittest.main()
