import unittest

from vfb_connect import vfb
from vfb_connect.schema.vfb_term import create_vfbterm_from_json

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
        term[0].load_mesh()
        print("got mesh ", term[0].mesh)
        self.assertTrue(term[0].mesh and term[0].mesh.id == "VFB_jrcv0jvf")

    def test_load_volume(self):
        json_data = self.vfb.get_TermInfo("VFB_jrcv0jvf", summary=False)
        term = create_vfbterm_from_json(json_data)
        print("got VFBTerm ", term[0])
        print("nrrd ", term[0].channel_images[0].image.image_nrrd)
        term[0].load_volume()
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
        terms = create_vfbterm_from_json(self.vfb.get_terms_by_region("nodulus", summary=False))
        terms.plot3d()
        print("Images with skeletons: ", [term.name for term in terms if hasattr(term, 'skeleton')])
        self.assertTrue([True for term in terms if hasattr(term, 'skeleton')])