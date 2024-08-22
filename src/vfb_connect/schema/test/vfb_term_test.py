import unittest
from vfb_connect.schema.vfb_term import create_vfbterm_from_json, VFBTerms, VFBTerm, Score, Relations, Xref

class VfbTermTest(unittest.TestCase):

    def setUp(self):
        from vfb_connect import vfb
        self.vfb = vfb

    def test_create_vfbterm_from_json(self):
        self.assertTrue(
            create_vfbterm_from_json(self.vfb.get_TermInfo("VFB_jrcv0jvf", summary=False)))

    def test_load_skeleton(self):
        json_data = self.vfb.get_TermInfo("VFB_jrcv0jvf", summary=False)
        print("got json_data ", json_data)
        term = create_vfbterm_from_json(json_data)
        print("got VFBTerm ", term)
        term.load_skeleton()
        print("got skeleton ", term.skeleton)
        self.assertTrue(term.skeleton and term.skeleton.id == "VFB_jrcv0jvf")

    def test_load_mesh(self):
        json_data = self.vfb.get_TermInfo("VFB_jrcv0jvf", summary=False)
        term = create_vfbterm_from_json(json_data)
        print("got VFBTerm ", term[0])
        term[0].load_mesh(verbose=True)
        print("got mesh ", term[0].mesh)
        self.assertTrue(term[0].mesh and term[0].mesh.id == "VFB_jrcv0jvf")

    def test_load_volume(self):
        json_data = self.vfb.get_TermInfo("VFB_jrcv0jvf", summary=False)
        term = create_vfbterm_from_json(json_data)
        print("got VFBTerm ", term[0])
        print("nrrd ", term[0].channel_images[0].image.image_nrrd)
        term[0].load_volume(verbose=True)
        print("got volume ", term[0].volume)
        self.assertTrue(term[0].volume and term[0].volume.id == "VFB_jrcv0jvf")

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
        terms = create_vfbterm_from_json(self.vfb.get_instances("'neuron' that 'has presynaptic terminals in' some 'nodulus'", summary=False)[0:100], verbose=True)
        terms = (terms[1:10:]+terms[0:10:])[0:2]
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) > 0)
        self.assertTrue(isinstance(terms, VFBTerms))
        try:
            terms.plot3d(template='JRC2018Unisex', verbose=True)
        except Exception as e:
            print("plot3d expectedly failed with ", e)
        self.assertTrue([True for term in terms if hasattr(term, 'skeleton') or hasattr(term, 'mesh') or hasattr(term, 'volume')])

    def test_VFBterms_addition(self):
        terms = create_vfbterm_from_json(self.vfb.get_instances("'neuron' that 'overlaps' some 'nodulus'", summary=False)[0:100], verbose=True)
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
        terms = create_vfbterm_from_json(self.vfb.get_instances("'neuron' that 'has presynaptic terminals in' some 'nodulus'", summary=False)[0:100], verbose=True)
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
        self.assertTrue(len(subparts)>20)

    def test_vfbterm_subtypes(self):
        term = self.vfb.term('FBt')
        print("got term ", term)
        subtypes = term.subtypes
        print("got subtypes ", subtypes)
        self.assertTrue(subtypes)
        self.assertTrue(isinstance(subtypes, VFBTerms))
        self.assertTrue(len(subtypes)>60)

    def test_vfbterm_children(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        children = term.children
        print("got children ", children)
        self.assertTrue(children)
        self.assertTrue(isinstance(children, VFBTerms))
        self.assertTrue(len(children)>20)

    def test_vfbterm_similarity_neuron_nblast(self):
        term = self.vfb.term('VGlut-F-000118')
        print("got term types", term.term.core.types)
        similar = term.similar_neurons_nblast
        print("got similar ", similar)
        self.assertTrue(similar)
        self.assertTrue(isinstance(similar[0], Score))
        self.assertTrue(len(similar)>10)

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
        self.assertTrue(len(downstream)>200)

    def test_vfbterm_upstream_types(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        upstream = term.upstream_neuron_types
        print("got upstream ", upstream)
        self.assertTrue(upstream)
        self.assertTrue(isinstance(upstream, VFBTerms))
        self.assertTrue(len(upstream)>200)

    def test_vfbterm_overlaps_types(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        overlaps = term.neuron_types_that_overlap
        print("got overlaps ", overlaps)
        self.assertTrue(overlaps)
        self.assertTrue(isinstance(overlaps, VFBTerms))
        self.assertTrue(len(overlaps)>300)

    def test_vfbterm_overlaps_instances(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        overlaps = term.neurons_that_overlap
        print("got overlaps ", overlaps)
        self.assertTrue(overlaps)
        self.assertTrue(isinstance(overlaps, VFBTerms))
        self.assertTrue(len(overlaps)>3000)

    def test_vfbterm_downstream_neurons(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        downstream = term.downstream_neurons
        print("got downstream ", downstream)
        self.assertTrue(downstream)
        self.assertTrue(isinstance(downstream, VFBTerms))
        self.assertTrue(len(downstream) > 100)

    def test_vfbterm_upstream_neurons(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        upstream = term.upstream_neurons
        print("got upstream ", upstream)
        self.assertTrue(upstream)
        self.assertTrue(isinstance(upstream, VFBTerms))
        self.assertTrue(len(upstream) > 700)

    def test_vfbterm_downstream_neuron_types(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        downstream_types = term.downstream_neuron_types
        print("got downstream types ", downstream_types)
        self.assertTrue(downstream_types)
        self.assertTrue(isinstance(downstream_types, VFBTerms))
        self.assertTrue(len(downstream_types) > 150)

    def test_vfbterm_neuron_types_with_synaptic_terminals_here(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        synaptic_terminals_types = term.neuron_types_with_synaptic_terminals_here
        print("got synaptic terminals types ", synaptic_terminals_types)
        self.assertTrue(synaptic_terminals_types)
        self.assertTrue(isinstance(synaptic_terminals_types, VFBTerms))
        self.assertTrue(len(synaptic_terminals_types) > 300)

    def test_vfbterm_neurons_with_synaptic_terminals_here(self):
        term = self.vfb.term('medulla')
        print("got term ", term)
        synaptic_terminals_neurons = term.neurons_with_synaptic_terminals_here
        print("got synaptic terminals neurons ", synaptic_terminals_neurons)
        self.assertTrue(synaptic_terminals_neurons)
        self.assertTrue(isinstance(synaptic_terminals_neurons, VFBTerms))
        self.assertTrue(len(synaptic_terminals_neurons) > 900)

    def test_vfbterm_downstream_neuron_types_from_ind(self):
        term = self.vfb.term('ME on JRC2018Unisex adult brain')
        print("got term ", term)
        downstream_types = term.downstream_neuron_types
        print("got downstream types ", downstream_types)
        self.assertTrue(downstream_types)
        self.assertTrue(isinstance(downstream_types, VFBTerms))
        self.assertTrue(len(downstream_types) > 150)

    def test_vfbterm_scRNAseq_Clusters(self):
        term = self.vfb.term('scRNAseq_2018_Davie_FULL_seq_clustering_dopaminergic_PAM_neurons')
        print("got term ", term)
        print(term.get_summary(return_dataframe=False))
        print(term.related_terms)
        self.assertTrue(term)

    def test_vfbterm_related_terms(self):
        term = self.vfb.term('scRNAseq_2018_Davie_FULL_seq_clustering_dopaminergic_PAM_neurons')
        print("got term ", term)
        print(term.related_terms)
        self.assertTrue(term)
        self.assertTrue(term.related_terms)
        self.assertTrue(isinstance(term.related_terms, Relations))
        print(term.related_terms.get_summary(return_dataframe=False))
        print(term.related_terms.get_terms())
        print(term.related_terms.get_relations())
        composed_of = term.related_terms.where(relation='composed primarily of')
        print(composed_of.get_summaries(return_dataframe=False))
        self.assertTrue(isinstance(composed_of, VFBTerms))

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
        neurons = med_neurons.AND(nod_neurons)
        print("got neurons ", neurons)
        print(f"got {len(neurons)} via logic and {len(terms2)} via OWL query")
        print(f"{neurons.get_names()} == {terms2.get_names()}")
        self.assertTrue(neurons == terms2)

    def test_vfbterms_xrefs(self):
        terms = self.vfb.terms(['catmaid_l1em:17545695', 'Neuprint web interface - hemibrain:v1.1:2039100722'])
        print("got terms ", terms)
        self.assertEqual(len(terms), 2)
        xref = terms[0].xrefs
        print("got xref ", xref)
        self.assertTrue(xref)
        self.assertTrue(isinstance(xref[0], Xref))
        self.assertEqual(len(xref), 1)


if __name__ == "__main__":
    unittest.main()