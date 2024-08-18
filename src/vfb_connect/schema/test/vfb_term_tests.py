import unittest

from vfb_connect import vfb
from vfb_connect.schema.vfb_term import create_vfbterm_from_json, VFBTerms

class VfbConnectTest(unittest.TestCase):

    def setUp(self):
        self.vfb = vfb

    def test_create_vfbterm_from_json(self):
        self.assertTrue(
            create_vfbterm_from_json(self.vfb.get_TermInfo("VFB_jrcv0jvf", summary=False)))

    def test_load_skeleton(self):
        json_data = self.vfb.get_TermInfo("VFB_jrcv0jvf", summary=False)
        term = create_vfbterm_from_json(json_data)
        print("got VFBTerm ", term[0])
        term[0].load_skeleton()
        print("got skeleton ", term[0].skeleton)
        self.assertTrue(term[0].skeleton and term[0].skeleton.id == "VFB_jrcv0jvf")

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
        terms = create_vfbterm_from_json(self.vfb.get_terms_by_region("nodulus", summary=False))
        print(f"got {len(terms)} VFBTerms: {terms}")
        self.assertTrue(terms)
        ids = terms.get_ids()
        print(f"got {len(ids)} ids: {ids}")
        self.assertTrue(len(ids) == len(terms))
        names = terms.get_names()
        print(f"got {len(names)} names: {names}")
        self.assertTrue(len(names) == len(terms))

    def test_VFBterms_plot3d(self):
        terms = create_vfbterm_from_json(self.vfb.get_instances("'neuron' that 'overlaps' some 'nodulus'", summary=False)[0:100], verbose=True)
        terms = terms[1:10:]+terms[0:10:]
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) > 0)
        self.assertTrue(isinstance(terms[0:10], VFBTerms))
        terms.plot3d(template='JRC2018Unisex', verbose=True)
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
        terms = create_vfbterm_from_json(self.vfb.get_instances("'neuron' that 'overlaps' some 'nodulus'", summary=False)[0:100], verbose=True)
        self.assertTrue(isinstance(terms, VFBTerms))
        self.assertTrue(len(terms) > 0)
        # test subtraction
        terms=terms[0:2]-terms[0:1]
        self.assertTrue(len(terms)==(len(terms[0:2])-len(terms[0:1])))
