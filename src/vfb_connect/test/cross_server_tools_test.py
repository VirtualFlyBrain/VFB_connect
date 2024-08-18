import unittest
from ..cross_server_tools import VfbConnect
import os
import shutil
from ..schema.vfb_term import VFBTerm, VFBTerms

class VfbConnectTest(unittest.TestCase):

    def setUp(self):
        self.vc = VfbConnect()

    def test_get_term_by_region(self):
        terms = self.vc.get_terms_by_region("fan-shaped body")
        print(terms)
        self.assertTrue(
            len(terms) > 200)

    def test_get_subclasses(self):
        terms = self.vc.get_subclasses("fan-shaped body layer")
        print(terms)
        self.assertTrue(
            len(terms) > 7)

    def test_get_instances(self):
#        fbi = self.vc.get_instances("fan-shaped body")
#        self.assertTrue(fbi)
#        # test summary
#        fbis = self.vc.get_instances("fan-shaped body", summary=True)
#        self.assertEqual(len(fbi), len(fbis))
        # Test batched query
        alpn = self.vc.get_instances('antennal lobe projection neuron')
        self.assertTrue(
            len(alpn) > 1000)
        alpns = self.vc.get_instances('antennal lobe projection neuron', summary=True)
        self.assertEqual(len(alpn), len(alpns))

    def test_get_images(self):
        if os.path.exists('image_folder_tmp') and os.path.isdir('image_folder_tmp'):
            shutil.rmtree('image_folder_tmp')
        fu = self.vc.neo_query_wrapper.get_images(['VFB_00000100', 'VFB_0010129x'],
                                                                 image_folder='image_folder_tmp',
                                                                 template='JRC2018Unisex')
        print(len(fu))
        self.assertEqual(len(fu), 2)

    def test_get_images_by_type(self):
        if os.path.exists('image_folder_tmp') and os.path.isdir('image_folder_tmp'):
            shutil.rmtree('image_folder_tmp')
        fu = self.vc.get_images_by_type("'fan-shaped neuron F1'",
                                        image_folder='image_folder_tmp',
                                        template='JRC2018Unisex')
        self.assertTrue(len(fu) > 0)
        bar = self.vc.get_images_by_type('octopaminergic VPM3 neuron', stomp=True, template='JRC2018Unisex',
                                         image_folder='image_folder_tmp')
        self.assertTrue(len(bar) > 0)


    def test_get_downstream_neurons(self):
        fu = self.vc.get_neurons_downstream_of('D_adPN_R (FlyEM-HB:5813055184)', classification="'Kenyon cell'", weight=20, verbose=True)
        print(fu)
        self.assertTrue(len(fu) > 0)

    def test_get_upstream_neurons(self):
        fu = self.vc.get_neurons_upstream_of('D_adPN_R (FlyEM-HB:5813055184)', classification="'GABAergic neuron'", weight=20, verbose=True)
        print(fu)
        self.assertTrue(len(fu) > 0)

    def test_get_connected_neurons_by_type(self):
        fu = self.vc.get_connected_neurons_by_type('Kenyon cell', 'mushroom body output neuron', 20)
        self.assertTrue(len(fu) > 0)
        # Test quoting
        fu = self.vc.get_connected_neurons_by_type("'Kenyon cell'", 'mushroom body output neuron', 20)
        self.assertTrue(len(fu) > 0)

    def test_get_vfb_link(self):
        fu = self.vc.get_vfb_link(['VFB_jrchjz1e', 'VFB_jrchjtdn', 'VFB_jrchk8bo', 'VFB_jrchjz73',
                                   'VFB_jrchjvog',
                                   'VFB_jrchk8b0',
                                   'VFB_jrchjw9i',
                                   'VFB_jrchk8ao',
                                   'VFB_jrchjwae'], template='JRC2018Unisex')
        print(fu)
        self.assertTrue(fu)

    def test_get_instances_by_dataset(self):
        fu = self.vc.get_instances_by_dataset('Ito2013', summary=True)
        self.assertGreater(len(fu), 10)

    def tearDown(self):
        if os.path.exists('image_folder_tmp') and os.path.isdir('image_folder_tmp'):
            shutil.rmtree('image_folder_tmp')

class VfbTermTests(unittest.TestCase):

    def setUp(self):
        self.vc = VfbConnect()

    def test_term(self):
        fu = self.vc.term('VFB_00010001')
        self.assertTrue(fu)
        self.assertTrue(fu.id == 'VFB_00010001')
        self.assertTrue(fu.name == 'fru-F-500075')
        self.assertTrue(isinstance(fu, VFBTerm))

    def test_terms(self):
        fu = self.vc.terms(['VFB_00010001', 'VFB_00010002'])
        self.assertTrue(fu)
        self.assertTrue(len(fu) == 2)
        self.assertTrue(isinstance(fu, VFBTerms))

    def test_type_term_parents(self):
        fu = self.vc.term('Kenyon cell', verbose=False)
        self.assertTrue(fu)
        print(fu)
        print(fu.parents)
        self.assertTrue(fu.parents)
        self.assertTrue(isinstance(fu.parents, VFBTerms))
        self.assertTrue(len(fu.parents) > 0)
        self.assertTrue(isinstance(fu.parents[0], VFBTerm))
        self.assertTrue(len(fu) > 0)

if __name__ == "__main__":
    unittest.main()