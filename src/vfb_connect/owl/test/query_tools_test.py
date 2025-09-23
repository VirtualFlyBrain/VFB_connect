import unittest
from ..owlery_query_tools import OWLeryConnect


class OwleryConnectTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up the OWLery connection once for all tests"""
        cls.oc = OWLeryConnect(obo_curies=['FBbt', 'RO', 'BFO'])
        cls.test_query = "RO:0002131 some FBbt:00003679"
        cls.test_query_labels = "'overlaps' some 'fan-shaped body'"

    def setUp(self):
        self.oc = self.__class__.oc
        self.test_query = self.__class__.test_query
        self.test_query_labels = self.__class__.test_query_labels

    def test_labels_2_ids(self):
        self.oc.lookup = {'overlaps': 'RO:0002131',
                          'fan-shaped body': 'FBbt:00003679'}
        self.assertEqual(self.oc.labels_2_ids(self.test_query_labels),
                         self.test_query)

    def test_labels_2_ids_fail(self):
        self.oc.lookup = {'overlaps': 'RO:0002131',
                          'fan-shaped body': 'FBbt:00003679'}
        # This isn't a test so far! unittest support for exception tests seems to be poor.
        try:
            self.oc.labels_2_ids("'overlaps' some 'fan-shaped body'"),
        except:
            pass

    def test_get_subclasses(self):
        ofb = self.oc.get_subclasses(query=self.test_query)
        self.assertTrue(ofb, "Query failed.")
        self.assertGreater(len(ofb), 150,
                           "Unexpectedly small number structures overlap FB")
        self.oc.lookup = {'overlaps': 'RO:0002131',
                          'fan-shaped body': 'FBbt:00003679'}
        ofbl = self.oc.get_subclasses(query=self.test_query_labels, query_by_label=True)
        self.assertTrue(ofb, "Query failed.")
        self.assertTrue(set(ofb) == set(ofbl))


if __name__ == '__main__':
    unittest.main()
