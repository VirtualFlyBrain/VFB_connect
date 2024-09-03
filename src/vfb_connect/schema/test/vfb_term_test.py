import unittest
import time
from vfb_connect.schema.vfb_term import create_vfbterm_from_json, VFBTerms, VFBTerm, Score, Relations, Xref, ExpressionList, Expression

class VfbTermTest(unittest.TestCase):

    def setUp(self):
        from vfb_connect import vfb
        self.vfb = vfb
        self.vfb._load_limit = 10

    def test_create_vfbterm_from_json(self):
        self.assertTrue(
            create_vfbterm_from_json(self.vfb.get_TermInfo("VFB_jrcv0jvf", summary=False)))

    def test_load_skeleton(self):
        term = self.vfb.term("VFB_jrcv0jvf")
        print("got VFBTerm ", term)
        term.load_skeleton()
        print("got skeleton ", term._skeleton)
        self.assertTrue(term._skeleton and term._skeleton.id == "VFB_jrcv0jvf")

    def test_load_mesh(self):
        term = self.vfb.term("VFB_jrcv0jvf")
        print("got VFBTerm ", term[0])
        term[0].load_mesh(verbose=True)
        print("got mesh ", term[0]._mesh)
        self.assertTrue(term[0]._mesh and term[0]._mesh.id == "VFB_jrcv0jvf")

    def test_load_volume(self):
        term = self.vfb.term("VFB_jrcv0jvf")
        print("got VFBTerm ", term[0])
        print("nrrd ", term[0].channel_images[0].image.image_nrrd)
        term[0].load_volume(verbose=True)
        print("got volume ", term[0]._volume)
        self.assertTrue(term[0]._volume and term[0]._volume.id == "VFB_jrcv0jvf")

    def test_VFBterms_by_region(self):
        oid = self.vfb.lookup_id('overlaps', return_curie=True)
        print(f"got overlaps: {oid}")
        self.assertEqual(oid, 'RO:0002131')
        terms = create_vfbterm_from_json(self.vfb.get_terms_by_region("nodulus", summary=False, verbose=True), verbose=True)
        print(f"got {len(terms)} VFBTerms: {terms}")
        self.assertTrue(terms)
        ids = terms.get_ids()
        print(f"got {len(ids)} ids: {ids}")
        self.assertTrue(len(ids) == len(terms))
        names = terms.get_names()
        print(f"got {len(names)} names: {names}")
        self.assertTrue(len(names) == len(terms))

    def test_VFBterms_plot3d(self):
        terms = self.vfb.terms(['VFB_jrchjwj7', 'VFB_jrchjwim', 'VFB_00004023', 'VFB_jrchk3b0', 'VFB_jrchk3b1', 'VFB_jrchk3b2', 'VFB_jrchk3b3', 'VFB_jrchk3b4', 'VFB_jrchk3b5', 'VFB_jrchk3b6', 'VFB_jrchk3b7', 'VFB_jrchk3b8', 'VFB_jrchk3b9', 'VFB_00007403', 'VFB_jrchk3ao', 'VFB_jrchk3ap', 'VFB_jrchk3aq', 'VFB_jrchk3ar', 'VFB_jrchk3as', 'VFB_jrchk3at', 'VFB_jrchk3au', 'VFB_jrchk3av', 'VFB_jrchk3aw', 'VFB_jrchk3ax', 'VFB_jrchk3ay', 'VFB_jrchk3az', 'VFB_jrchk3ba', 'VFB_jrchk3bb', 'VFB_jrchk3bc', 'VFB_jrchk3bd', 'VFB_jrchk3be', 'VFB_jrchk3bf', 'VFB_jrchk3bg', 'VFB_jrchk3bh', 'VFB_jrchk3bi', 'VFB_jrchk3bj', 'VFB_jrchk3bk', 'VFB_jrchk3bl', 'VFB_jrchk3bm', 'VFB_jrchk3bn', 'VFB_jrchk3bo', 'VFB_jrchk3bp', 'VFB_jrchk3bq', 'VFB_jrchk3br', 'VFB_jrchk3bs', 'VFB_jrchk3bt', 'VFB_jrchk3e0', 'VFB_jrchk3e1', 'VFB_jrchk3e2', 'VFB_jrchk3e3', 'VFB_jrchk3e4', 'VFB_jrchk3e5', 'VFB_001012bm', 'VFB_001012bk', 'VFB_001012bj', 'VFB_001012bi', 'VFB_001012bh', 'VFB_00013165', 'VFB_001001dr', 'VFB_00005531', 'VFB_00007701', 'VFB_jrchk8iq', 'VFB_jrchk3gx', 'VFB_jrchk3gy', 'VFB_jrchk3gz', 'VFB_jrchk3ha', 'VFB_jrchk3hb', 'VFB_jrchk3hc', 'VFB_jrchk3hd', 'VFB_jrchk3he', 'VFB_jrchk3hf', 'VFB_jrchk3hg', 'VFB_jrchk3hh', 'VFB_jrchk3hi', 'VFB_jrchk3hj', 'VFB_jrchk3hk', 'VFB_jrchk3hl', 'VFB_jrchk3hm', 'VFB_jrchk3hn', 'VFB_jrchk3j0', 'VFB_jrchk3ho', 'VFB_jrchk3j1', 'VFB_00005875', 'VFB_jrchk3j2', 'VFB_jrchk3hp', 'VFB_jrchk3hq', 'VFB_jrchk3j3', 'VFB_jrchk3hr', 'VFB_jrchk3j4', 'VFB_jrchk3j5', 'VFB_jrchk3hs', 'VFB_jrchk3ht', 'VFB_jrchk3j6', 'VFB_jrchk3j7', 'VFB_jrchk3hu', 'VFB_jrchk3j8', 'VFB_jrchk3hv', 'VFB_jrchk3j9', 'VFB_jrchk3hw', 'VFB_jrchk3hx'])
        terms = (terms[1:10:]+terms[0:10:])[0:2]
        terms = (terms[1:10:]+terms[0:10:])[0:2]
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) > 0)
        self.assertTrue(isinstance(terms, VFBTerms))
        try:
            terms.plot3d(template='JRC2018Unisex', verbose=True, limit = 2)
        except Exception as e:
            print("plot3d expectedly failed with ", e)
        self.assertTrue([True for term in terms if hasattr(term, 'skeleton') or hasattr(term, 'mesh') or hasattr(term, 'volume')])

    def test_VFBterms_plot2d(self):
        terms = self.vfb.terms(['VFB_00000001','VFB_00010001'])
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) > 0)
        self.assertTrue(isinstance(terms, VFBTerms))
        try:
            terms.plot2d(template='JRC2018Unisex', verbose=True)
        except Exception as e:
            print("plot2d expectedly failed with ", e)
        self.assertTrue([True for term in terms if hasattr(term, 'skeleton') or hasattr(term, 'mesh') or hasattr(term, 'volume')])

    def test_VFBterms_addition(self):
        terms = self.vfb.terms(['VFB_jrchjwj7', 'VFB_jrchjwim', 'VFB_00004023', 'VFB_jrchk3b0', 'VFB_jrchk3b1', 'VFB_jrchk3b2', 'VFB_jrchk3b3', 'VFB_jrchk3b4', 'VFB_jrchk3b5', 'VFB_jrchk3b6', 'VFB_jrchk3b7', 'VFB_jrchk3b8', 'VFB_jrchk3b9', 'VFB_00007403', 'VFB_jrchk3ao', 'VFB_jrchk3ap', 'VFB_jrchk3aq', 'VFB_jrchk3ar', 'VFB_jrchk3as', 'VFB_jrchk3at', 'VFB_jrchk3au', 'VFB_jrchk3av', 'VFB_jrchk3aw', 'VFB_jrchk3ax', 'VFB_jrchk3ay', 'VFB_jrchk3az', 'VFB_jrchk3ba', 'VFB_jrchk3bb', 'VFB_jrchk3bc', 'VFB_jrchk3bd', 'VFB_jrchk3be', 'VFB_jrchk3bf', 'VFB_jrchk3bg', 'VFB_jrchk3bh', 'VFB_jrchk3bi', 'VFB_jrchk3bj', 'VFB_jrchk3bk', 'VFB_jrchk3bl', 'VFB_jrchk3bm', 'VFB_jrchk3bn', 'VFB_jrchk3bo', 'VFB_jrchk3bp', 'VFB_jrchk3bq', 'VFB_jrchk3br', 'VFB_jrchk3bs', 'VFB_jrchk3bt', 'VFB_jrchk3e0', 'VFB_jrchk3e1', 'VFB_jrchk3e2', 'VFB_jrchk3e3', 'VFB_jrchk3e4', 'VFB_jrchk3e5', 'VFB_001012bm', 'VFB_001012bk', 'VFB_001012bj', 'VFB_001012bi', 'VFB_001012bh', 'VFB_00013165', 'VFB_001001dr', 'VFB_00005531', 'VFB_00007701', 'VFB_jrchk8iq', 'VFB_jrchk3gx', 'VFB_jrchk3gy', 'VFB_jrchk3gz', 'VFB_jrchk3ha', 'VFB_jrchk3hb', 'VFB_jrchk3hc', 'VFB_jrchk3hd', 'VFB_jrchk3he', 'VFB_jrchk3hf', 'VFB_jrchk3hg', 'VFB_jrchk3hh', 'VFB_jrchk3hi', 'VFB_jrchk3hj', 'VFB_jrchk3hk', 'VFB_jrchk3hl', 'VFB_jrchk3hm', 'VFB_jrchk3hn', 'VFB_jrchk3j0', 'VFB_jrchk3ho', 'VFB_jrchk3j1', 'VFB_00005875', 'VFB_jrchk3j2', 'VFB_jrchk3hp', 'VFB_jrchk3hq', 'VFB_jrchk3j3', 'VFB_jrchk3hr', 'VFB_jrchk3j4', 'VFB_jrchk3j5', 'VFB_jrchk3hs', 'VFB_jrchk3ht', 'VFB_jrchk3j6', 'VFB_jrchk3j7', 'VFB_jrchk3hu', 'VFB_jrchk3j8', 'VFB_jrchk3hv', 'VFB_jrchk3j9', 'VFB_jrchk3hw', 'VFB_jrchk3hx'], verbose=True)
        # test addition of slices
        terms = terms[1:10:]+terms[0:10:]
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) > 0)
        # check simple slicing
        self.assertTrue(isinstance(terms[0:2], VFBTerms))
        # test addition uniqueness contraint
        terms=terms[0:2]+terms[0:2]
        self.assertTrue(len(terms)==len(terms[0:2]))

    def test_VFBterms_subtraction(self):
        terms = self.vfb.terms(['VFB_jrchjwj7', 'VFB_jrchjwim', 'VFB_00004023', 'VFB_jrchk3b0', 'VFB_jrchk3b1', 'VFB_jrchk3b2', 'VFB_jrchk3b3', 'VFB_jrchk3b4', 'VFB_jrchk3b5', 'VFB_jrchk3b6', 'VFB_jrchk3b7', 'VFB_jrchk3b8', 'VFB_jrchk3b9', 'VFB_00007403', 'VFB_jrchk3ao', 'VFB_jrchk3ap', 'VFB_jrchk3aq', 'VFB_jrchk3ar', 'VFB_jrchk3as', 'VFB_jrchk3at', 'VFB_jrchk3au', 'VFB_jrchk3av', 'VFB_jrchk3aw', 'VFB_jrchk3ax', 'VFB_jrchk3ay', 'VFB_jrchk3az', 'VFB_jrchk3ba', 'VFB_jrchk3bb', 'VFB_jrchk3bc', 'VFB_jrchk3bd', 'VFB_jrchk3be', 'VFB_jrchk3bf', 'VFB_jrchk3bg', 'VFB_jrchk3bh', 'VFB_jrchk3bi', 'VFB_jrchk3bj', 'VFB_jrchk3bk', 'VFB_jrchk3bl', 'VFB_jrchk3bm', 'VFB_jrchk3bn', 'VFB_jrchk3bo', 'VFB_jrchk3bp', 'VFB_jrchk3bq', 'VFB_jrchk3br', 'VFB_jrchk3bs', 'VFB_jrchk3bt', 'VFB_jrchk3e0', 'VFB_jrchk3e1', 'VFB_jrchk3e2', 'VFB_jrchk3e3', 'VFB_jrchk3e4', 'VFB_jrchk3e5', 'VFB_001012bm', 'VFB_001012bk', 'VFB_001012bj', 'VFB_001012bi', 'VFB_001012bh', 'VFB_00013165', 'VFB_001001dr', 'VFB_00005531', 'VFB_00007701', 'VFB_jrchk8iq', 'VFB_jrchk3gx', 'VFB_jrchk3gy', 'VFB_jrchk3gz', 'VFB_jrchk3ha', 'VFB_jrchk3hb', 'VFB_jrchk3hc', 'VFB_jrchk3hd', 'VFB_jrchk3he', 'VFB_jrchk3hf', 'VFB_jrchk3hg', 'VFB_jrchk3hh', 'VFB_jrchk3hi', 'VFB_jrchk3hj', 'VFB_jrchk3hk', 'VFB_jrchk3hl', 'VFB_jrchk3hm', 'VFB_jrchk3hn', 'VFB_jrchk3j0', 'VFB_jrchk3ho', 'VFB_jrchk3j1', 'VFB_00005875', 'VFB_jrchk3j2', 'VFB_jrchk3hp', 'VFB_jrchk3hq', 'VFB_jrchk3j3', 'VFB_jrchk3hr', 'VFB_jrchk3j4', 'VFB_jrchk3j5', 'VFB_jrchk3hs', 'VFB_jrchk3ht', 'VFB_jrchk3j6', 'VFB_jrchk3j7', 'VFB_jrchk3hu', 'VFB_jrchk3j8', 'VFB_jrchk3hv', 'VFB_jrchk3j9', 'VFB_jrchk3hw', 'VFB_jrchk3hx'])
        print('starting subtraction test with ', len(terms), ' terms')
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) > 0)
        # test subtraction
        minus_terms=terms[0:5]-terms[0:2]
        print(f"looking for {terms[0:5]}")
        print(f"minus {terms[0:2]}")
        print(f"equals {terms[2:5]}")
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) > 0)
        print(f"looking for {len(terms[0:5])} - {len(terms[0:2])} = {len(terms[2:5])} terms")
        print(f"got {len(minus_terms)} terms: {minus_terms}")
        self.assertTrue(len(minus_terms)==len(terms[2:5]))

    def test_create_vfbterm_from_id(self):
        term=VFBTerm("VFB_jrcv0jvf")
        print("got term ", term)
        self.assertTrue(term)
        self.assertTrue(isinstance(term, VFBTerm))

    def test_create_vfbterm_from_name(self):
        term=VFBTerm("nodulus")
        print("got term ", term)
        self.assertTrue(term)
        self.assertTrue(isinstance(term, VFBTerm))

    def test_create_vfbterms_from_list(self):
        terms=VFBTerms(["nodulus", "VFB_jrcv0jvf"])
        print("got terms ", terms)
        self.assertTrue(terms)
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms)==2)

    def test_vfbterm_subparts(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        subparts = term.subparts
        print("got subparts ", subparts)
        self.assertTrue(subparts)
        self.assertTrue(isinstance(subparts, VFBTerms))
        self.assertEqual(len(subparts), self.vfb._load_limit)

    def test_vfbterm_subtypes(self):
        term = self.vfb.term('FBt')
        print("got term ", term)
        subtypes = term.subtypes
        print("got subtypes ", subtypes)
        self.assertTrue(subtypes)
        self.assertTrue(isinstance(subtypes, VFBTerms))
        self.assertEqual(len(subtypes), self.vfb._load_limit)

    def test_vfbterm_children(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        children = term.children
        print("got children ", children)
        self.assertTrue(children)
        self.assertTrue(isinstance(children, VFBTerms))
        self.assertEqual(len(children), self.vfb._load_limit)

    def test_vfbterm_similarity_neuron_nblast(self):
        term = self.vfb.term('VGlut-F-000118')
        print("got term types", term.term.core.types)
        similar = term.similar_neurons_nblast
        print("got similar ", similar)
        self.assertTrue(similar)
        self.assertTrue(isinstance(similar[0], Score))
        self.assertGreater(len(similar), 50)

    # def test_vfbterm_similarity_neuron_neuronbridge(self):
    #     # TODO No neuronbridge neuron - neuron score exist at the monent
    #     term = self.vfb.term('LPC1 (FlyEM-HB:1838269993)')
    #     print("got term ", term)
    #     similar = term.similar_neurons_neuronbridge
    #     print("got similar ", similar)
    #     self.assertFalse(similar)
    #     # self.assertFalse(isinstance(similar[0], Score))
    #     self.assertFalse(len(similar)>2)

    def test_vfbterm_potental_drivers_nblast(self):
        term = self.vfb.term('VGlut-F-000118')
        print("got term ", term)
        drivers = term.potential_drivers_nblast
        print("got drivers ", drivers)
        print(f"got {len(drivers)} drivers")
        self.assertTrue(drivers)
        self.assertTrue(isinstance(drivers, list))
        self.assertTrue(isinstance(drivers[0], Score))
        self.assertTrue(len(drivers)>2)

    def test_vfbterm_potential_drivers_neuronbridge(self):
        term = self.vfb.term('LPC1 (FlyEM-HB:1838269993)')
        print("got term ", term)
        drivers = term.potential_drivers_neuronbridge
        print("got drivers ", drivers)
        print(f"got {len(drivers)} drivers")
        self.assertTrue(drivers)
        self.assertTrue(isinstance(drivers, list))
        self.assertTrue(isinstance(drivers[0], Score))
        self.assertTrue(len(drivers)>2)

    def test_vfbterm_downstream_types(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        downstream = term.downstream_neuron_types
        print("got downstream ", downstream)
        self.assertTrue(downstream)
        self.assertTrue(isinstance(downstream, VFBTerms))
        self.assertEqual(len(downstream), self.vfb._load_limit)

    def test_vfbterm_upstream_types(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        upstream = term.upstream_neuron_types
        print("got upstream ", upstream)
        self.assertTrue(upstream)
        self.assertTrue(isinstance(upstream, VFBTerms))
        self.assertEqual(len(upstream), self.vfb._load_limit)

    def test_vfbterm_overlaps_types(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        overlaps = term.neuron_types_that_overlap
        print("got overlaps ", overlaps)
        self.assertTrue(overlaps)
        self.assertTrue(isinstance(overlaps, VFBTerms))
        self.assertEqual(len(overlaps), self.vfb._load_limit)

    def test_vfbterm_overlaps_instances(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        overlaps = term.neurons_that_overlap
        print("got overlaps ", overlaps)
        self.assertTrue(overlaps)
        self.assertTrue(isinstance(overlaps, VFBTerms))
        self.assertEqual(len(overlaps), self.vfb._load_limit)

    def test_vfbterm_downstream_neurons(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        downstream = term.downstream_neurons
        print("got downstream ", downstream)
        self.assertTrue(downstream)
        self.assertTrue(isinstance(downstream, VFBTerms))
        self.assertEqual(len(downstream), self.vfb._load_limit)

    def test_vfbterm_upstream_neurons(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        upstream = term.upstream_neurons
        print("got upstream ", upstream)
        self.assertTrue(upstream)
        self.assertTrue(isinstance(upstream, VFBTerms))
        self.assertEqual(len(upstream), self.vfb._load_limit)

    def test_vfbterm_downstream_neuron_types(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        downstream_types = term.downstream_neuron_types
        print("got downstream types ", downstream_types)
        self.assertTrue(downstream_types)
        self.assertTrue(isinstance(downstream_types, VFBTerms))
        self.assertEqual(len(downstream_types), self.vfb._load_limit)

    def test_vfbterm_neuron_types_with_synaptic_terminals_here(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        synaptic_terminals_types = term.neuron_types_with_synaptic_terminals_here
        print("got synaptic terminals types ", synaptic_terminals_types)
        self.assertTrue(synaptic_terminals_types)
        self.assertTrue(isinstance(synaptic_terminals_types, VFBTerms))
        self.assertEqual(len(synaptic_terminals_types), self.vfb._load_limit)

    def test_vfbterm_neurons_with_synaptic_terminals_here(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        synaptic_terminals_neurons = term.neurons_with_synaptic_terminals_here
        print("got synaptic terminals neurons ", synaptic_terminals_neurons)
        self.assertTrue(synaptic_terminals_neurons)
        self.assertTrue(isinstance(synaptic_terminals_neurons, VFBTerms))
        self.assertEqual(len(synaptic_terminals_neurons), self.vfb._load_limit)

    def test_vfbterm_downstream_neuron_types_from_ind(self):
        term = self.vfb.term('ME on JRC2018Unisex adult brain')
        print("got term ", term)
        downstream_types = term.downstream_neuron_types
        print("got downstream types ", downstream_types)
        self.assertTrue(downstream_types)
        self.assertTrue(isinstance(downstream_types, VFBTerms))
        self.assertEqual(len(downstream_types), self.vfb._load_limit)

    def test_vfbterm_scRNAseq_Clusters(self):
        term = self.vfb.term('scRNAseq_2018_Davie_FULL_seq_clustering_dopaminergic_PAM_neurons')
        print("got term ", term)
        print(term.get_summary(return_dataframe=False))
        print(term.related_terms)
        self.assertTrue(term)

    def test_vfbterm_related_terms(self):
        term = self.vfb.term('scRNAseq_2018_Davie_FULL_seq_clustering_dopaminergic_PAM_neurons')
        print("got term ", term)
        self.assertTrue(term)
        rel = term.related_terms
        print(rel.summary)
        self.assertTrue(rel)
        self.assertTrue(isinstance(rel, Relations))
        print(term.related_terms.get_summary(return_dataframe=False))
        print(term.related_terms.get_terms())
        print(term.related_terms.get_relations())
        composed_of = term.related_terms.where(relation='composed primarily of')
        print(composed_of.get_summaries(return_dataframe=False))
        self.assertTrue(isinstance(composed_of, VFBTerms))
        term2 = self.vfb.term('VFB_jrcv0jj4', verbose=True)
        rel = term2.related_terms
        print(rel.summary)
        print(rel.where(relation='capable of').get_summaries(return_dataframe=False))
        print(dir(term2))
        print(term2.part_of)
        self.assertGreater(len(term2.part_of), 1)

    def test_vfbterm_addition(self):
        terms1 = self.vfb.terms(['medulla on JRC2018Unisex adult brain', 'nodulus on JRC2018Unisex adult brain'])
        ids = self.vfb.get_instances("'neuron' that 'has synaptic terminal in' some 'nodulus' and 'has synaptic terminal in' some 'medulla'")
        terms2 = self.vfb.terms(ids)
        print("got terms1 ", terms1)
        print("got terms2 ", terms2)
        terms = terms1+terms2
        print("got terms ", terms)
        self.assertTrue(terms)
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) == len(terms1)+len(terms2))
        terms = terms1+terms1
        print("got terms ", terms)
        self.assertTrue(terms)
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) == len(terms1))

        med_neurons = terms1[0].neurons_with_synaptic_terminals_here
        nod_neurons = terms1[1].neurons_with_synaptic_terminals_here
        print("got med_neurons ", med_neurons)
        print("got nod_neurons ", nod_neurons)
        # neurons = med_neurons.AND(nod_neurons)
        # print("got neurons ", neurons)
        # print(f"got {len(neurons)} via logic and {len(terms2)} via OWL query")
        # print(f"{neurons.get_names()} == {terms2.get_names()}")
        # self.assertTrue(neurons == terms2)

    def test_vfbterms_xrefs(self):
        self.vfb._dbs = None
        terms = self.vfb.terms(['catmaid_l1em:17545695', 'neuprint_JRC_Hemibrain_1point1:2039100722'])
        print("got terms ", terms)
        print(self.vfb._dbs)
        self.assertEqual(len(terms), 2)
        xref = terms[0].xrefs
        print("got xref ", xref)
        self.assertTrue(xref)
        self.assertTrue(isinstance(xref[0], Xref))
        self.assertGreaterEqual(len(xref), 1)

    def test_vfbterms_transgene_expression(self):
        term = self.vfb.term('medulla')
        print("got terms ", term)
        lct = term.lineage_clone_types
        print(lct.summary)
        self.assertTrue(lct)
        self.assertGreater(len(lct), 4)
        lc = term.lineage_clones
        print(lc.summary)
        self.assertGreater(len(lc), 9)

    def test_vfbterms_innervating(self):
        term = self.vfb.term('medulla')
        print("got terms ", term)
        lct = term.innervating
        print(lct.summary)
        self.assertTrue(lct)
        self.assertGreater(len(lct), 2)

    def test_vfbterms_transcriptomic_profile(self):
        print(self.vfb.lookup_id('LC12'))
        term = self.vfb.term('LC12')
        print("got terms ", term)
        lct = term.get_transcriptomic_profile()
        print(type(lct))
        self.assertTrue(isinstance(lct, ExpressionList))
        print(lct.summary)
        print(len(lct[0]))
        self.assertGreater(len(lct), 2)

    def test_lookups(self):
        id = self.vfb.lookup_id('LC12')
        print("got id ", id)
        self.assertEqual(id, 'FBbt_00100484')
        id = self.vfb.lookup_id('overlaps', return_curie=True)
        print("got id ", id)
        self.assertEqual(id, 'RO:0002131')
        id = self.vfb.lookup_id('cell')
        print("got id ", id)
        self.assertEqual(id, 'FBbt_00007002')
        id = self.vfb.lookup_id('part_of')
        print("got id ", id)
        self.assertEqual(id, 'BFO_0000050')

    def test_lookup_names(self):
        name = self.vfb.lookup_name('FBbt_00100484')
        print("got name ", name)
        self.assertEqual(name, 'Lcn12')
        name = self.vfb.lookup_name(["RO_0002292", "RO_0002120"])
        print("got name ", name)
        self.assertEqual(name, ['expresses', 'synapsed to'])

    def test_lookups_matching(self):
        id = self.vfb.lookup_id(' LC12' ,verbose=True)
        print("got id ", id)
        self.assertEqual(id, 'FBbt_00100484')
        id = self.vfb.lookup_id('LC_12')
        print("got id ", id)
        self.assertEqual(id, 'FBbt_00100484')
        id = self.vfb.lookup_id('LC_12 ')
        print("got id ", id)
        self.assertEqual(id, 'FBbt_00100484')
        id = self.vfb.lookup_id('LC 12 ')
        print("got id ", id)
        self.assertEqual(id, 'FBbt_00100484')

    def test_vfbterm_cache(self):
        base = len(self.vfb._term_cache)
        print(self.vfb._term_cache)

        self.vfb._use_cache=True

        # Timing the first call to 'medulla'
        start_time = time.time()
        self.vfb.term('medulla')
        end_time = time.time()
        print(f"Time taken for vfb.term('medulla'): {end_time - start_time:.4f} seconds")
        base = len(self.vfb._term_cache)
        print(base)

        # Timing the second call to 'medulla'
        start_time = time.time()
        self.vfb.term('medulla')
        end_time = time.time()
        print(f"Time taken for vfb.term('medulla') again: {end_time - start_time:.4f} seconds")

        print(base)
        self.assertEqual(len(self.vfb._term_cache), base)

        # Timing the call to 'LC12'
        start_time = time.time()
        self.vfb.term('LC12')
        end_time = time.time()
        print(f"Time taken for vfb.term('LC12'): {end_time - start_time:.4f} seconds")
        print(self.vfb._term_cache)
        self.assertGreater(len(self.vfb._term_cache), base)
        base = len(self.vfb._term_cache)
        print(base)

        self.vfb._use_cache=False

    def test_vfbterms_get_all(self):
        terms = self.vfb.terms(['IN13A015_T1_R (MANC:81202)','SNta24_MesoLN_R (MANC:45077)'])
        print("got terms ", terms)
        self.assertTrue(terms)
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertEqual(len(terms), 2)
        NT = terms.get_all('capable_of')
        print(NT)
        self.assertEqual(len(NT), 2)
        fail = terms.get_all('magic_term')
        print(fail)
        self.assertFalse(fail)
        self.assertEqual(len(fail), 0)
        NT = terms.get_all('capable_of', return_dict=True)
        print(NT)
        self.assertEqual(NT['glutamate secretion, neurotransmission'], ['VFB_jrcv1qnm'])

    def test_vfbterms_get_colours_for_terms(self):
        terms = self.vfb.terms(['IN13A015_T1_R (MANC:81202)','SNta24_MesoLN_R (MANC:45077)','SNta24_MesoLN_L (MANC:157685)','SNta24_MesoLN_L (MANC:22390588623)'])
        print("got terms ", terms)
        cp = terms.get_colours_for('capable_of')
        print(cp)
        self.assertTrue(cp)
        self.assertEqual(len(cp), 4)
        tp = terms.get_colours_for('types')
        print(tp)
        self.assertEqual(len(tp), 4)
        tp = terms.get_colours_for('types', take_first=True)
        print(tp)
        self.assertEqual(len(tp), 4)
        tp = terms.get_colours_for('parents', take_first=False, verbose=True)
        print(tp)
        self.assertEqual(len(tp), 4)

    def test_vfbterm_site(self):
        term = self.vfb.term('fafb_catmaid_api')
        print("got term ", term)
        term.debug = True
        term._return_type='id'
        print(term.instances)
        self.assertGreater(len(term._instances_ids), 9)
        print(dir(term))
        print(term.get_summary(return_dataframe=False))
        self.assertTrue(term.has_image)

    def test_vfbterm_xref(self):
        term = self.vfb.term('VFB_jrcv1ngs')
        print("got term ", term)
        print(term.xrefs)
        self.assertTrue(term.xref_id)
        print(dir(term))
        print(term.xref_id)
        self.assertEqual(self.vfb.xref_2_vfb_id(term.xref_id, return_just_ids=True)[0], term.id)

if __name__ == "__main__":
    unittest.main()