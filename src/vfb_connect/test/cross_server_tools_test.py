import unittest
from ..cross_server_tools import VfbConnect


class VfbConnectTest(unittest.TestCase):

    def setUp(self):
        self.vc = VfbConnect()

    def test_get_term_by_region(self):
        self.assertTrue(
            self.vc.get_terms_by_region("fan-shaped body"))

    def test_get_subclasses(self):
        self.assertTrue(
            self.vc.get_subclasses("fan-shaped body layer"))

    def test_get_images(self):
        self.assertTrue(
            self.vc.get_subclasses("fan-shaped body"))

