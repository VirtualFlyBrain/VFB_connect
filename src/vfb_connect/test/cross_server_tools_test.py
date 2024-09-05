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
        print()
        fu = self.vc.get_connected_neurons_by_type(upstream_type='Kenyon cell', downstream_type='mushroom body output neuron', weight=20)
        self.assertTrue(len(fu) > 0)
        fu = self.vc.get_connected_neurons_by_type(upstream_type='FBbt_00051488', weight=5)
        self.assertTrue(len(fu) > 0)
        fu = self.vc.get_connected_neurons_by_type(downstream_type='FBbt_00051488', weight=5)
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

    def test_lookup_id(self):
        from vfb_connect import vfb
        test_key = "LPC1 (FlyEM-HB:1808965929)"
        term = vfb.term(test_key, verbose=True)
        self.assertEqual(term.id, "VFB_jrchk00a")

    def test_get_owl_subclasses(self):
        ofb = self.vc.owl_subclasses(query="RO:0002131 some FBbt:00003679", return_id_only=True)
        self.assertTrue(ofb, "Query failed.")
        self.assertGreater(len(ofb), 150,
                           "Unexpectedly small number structures overlap FB")
        ofbl = self.vc.owl_subclasses(query="'overlaps' some 'fan-shaped body'", query_by_label=True, return_id_only=True)
        self.assertTrue(ofb, "Query failed.")
        self.assertTrue(set(ofb) == set(ofbl))

    def test_get_owl_instances(self):
        ofb = self.vc.owl_instances(query="RO:0002131 some FBbt:00003679", return_id_only=True)
        self.assertTrue(ofb, "Query failed.")
        self.assertGreater(len(ofb), 150,
                           "Unexpectedly small number structures overlap FB")
        ofbl = self.vc.owl_instances(query="'overlaps' some 'fan-shaped body'", query_by_label=True, return_id_only=True)
        self.assertTrue(ofb, "Query failed.")
        self.assertTrue(set(ofb) == set(ofbl))

    def test_cypher_query(self):
        fu = self.vc.cypher_query("MATCH (n:Class) WHERE n.label = 'fan-shaped body' RETURN n", return_dataframe=False)
        self.assertTrue(fu)
        self.assertTrue(len(fu) > 0)
        self.assertTrue(isinstance(fu[0], dict))
        self.assertEqual(fu[0]['n']['label'], 'fan-shaped body')

    def test_nt_receptors_in_downstream_neurons(self):
        fu = self.vc.get_nt_receptors_in_downstream_neurons(upstream_type='Dm8', downstream_type='Dm9', weight=10)
        print(fu)
        self.assertTrue(len(fu) > 9)
        bar = self.vc.get_nt_receptors_in_downstream_neurons(upstream_type='Dm8', downstream_type='Dm9', weight=10, return_dataframe=False)
        print(bar)
        self.assertTrue(len(bar) > 9)

    def test_xref_to_id(self):
        fu = self.vc.xref_2_vfb_id('FlyEM-HB:1353544607')
        self.assertTrue(fu)
        print(fu)
        self.assertTrue(fu == ['VFB_jrchk3bp'])

    def test_id_to_xref(self):
        fu = self.vc.vfb_id_2_xrefs('VFB_jrchk3bp', verbose=True)
        self.assertTrue(fu)
        print(fu)
        self.assertNotEqual(fu.keys(),['VFB_jrchk3bp'])
        
    def test_get_neuron_pubs(self):
        fu = self.vc.get_neuron_pubs('Kenyon cell')
        self.assertTrue(len(fu)> 9)

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

    def test_solr_search(self):
        fu = self.vc.search('fan-shaped body', return_dataframe=False)
        print(fu)
        self.assertTrue(len(fu) > 0)

if __name__ == "__main__":
    unittest.main()