import unittest
from ..cross_server_tools import VfbConnect
import os
import shutil


class VfbConnectTest(unittest.TestCase):

    def setUp(self):
        self.vc = VfbConnect()

    def test_get_term_by_region(self):
        self.assertTrue(
            self.vc.get_terms_by_region("fan-shaped body"))

    def test_get_subclasses(self):
        self.assertTrue(
            self.vc.get_subclasses("fan-shaped body layer"))

    def test_get_instances(self):
        self.assertTrue(
            self.vc.get_instances("fan-shaped body"))
        # Tests batched query
        self.assertTrue(
            len(self.vc.get_instances('antennal lobe projection neuron')) > 1000)
        self.assertTrue(self.vc.get_instances('antennal lobe projection neuron', summary=True))

    def test_get_images(self):
        if os.path.exists('image_folder_tmp') and os.path.isdir('image_folder_tmp'):
            shutil.rmtree('image_folder_tmp')
        self.assertTrue(len(self.vc.neo_query_wrapper.get_images(['VFB_00000100', 'VFB_0010129x'],
                                               image_folder='image_folder_tmp',
                                               template='JRC2018Unisex')))

    def test_get_images_by_type(self):
        if os.path.exists('image_folder_tmp') and os.path.isdir('image_folder_tmp'):
            shutil.rmtree('image_folder_tmp')
        fu = self.vc.get_images_by_type("'fan-shaped neuron F1'",
                                        image_folder='image_folder_tmp',
                                        template='JRC2018Unisex')
        self.assertTrue(len(fu) > 0)

    def test_get_downstream_neurons(self):
        fu = self.vc.get_neurons_downstream_of('D_adPN_R - 5813055184', classification="'Kenyon cell'", weight=20)
        self.assertTrue(len(fu) > 0)

    def test_get_upstream_neurons(self):
        fu = self.vc.get_neurons_upstream_of('D_adPN_R - 5813055184', classification="'GABAergic neuron'", weight=20)
        self.assertTrue(len(fu) > 0)

    def test_get_connected_neurons_by_type(self):
        fu = self.vc.get_connected_neurons_by_type('Kenyon cell', 'mushroom body output neuron', 20)
        self.assertTrue(len(fu) > 0)

    def tearDown(self):
        if os.path.exists('image_folder_tmp') and os.path.isdir('image_folder_tmp'):
            shutil.rmtree('image_folder_tmp')
