import unittest
from vfb_connect.schema.vfb_term import create_vfbterm_from_json, VFBTerms, VFBTerm, Score, Relations, Xref

class VfbTermTest(unittest.TestCase):

    def setUp(self):
        from vfb_connect import vfb
        self.vfb = vfb

    def test_scRNAseq_cluster_to_genes(self):
        # Get all gene terms expressed in a given cluster
        cluster = self.vfb.term("FBlc0006144")
        print(cluster)
        genes = cluster.scRNAseq_genes
        self.assertIsNotNone(genes)
        self.assertTrue(isinstance(genes, VFBTerms))
        self.assertGreater(len(genes), 2000)

if __name__ == "__main__":
    unittest.main()