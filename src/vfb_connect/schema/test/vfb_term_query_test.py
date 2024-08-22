import unittest

import pandas as pd
from vfb_connect.schema.vfb_term import create_vfbterm_from_json, VFBTerms, VFBTerm, Score, Relations, Xref, ExpressionList, Expression


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
        self.assertTrue(isinstance(genes, ExpressionList))
        self.assertGreater(len(genes), 2000)
        print(genes[0].summary)
        summary = self.vfb.get_scRNAseq_gene_expression(cluster=cluster, return_dataframe=True)
        print(summary)
        self.assertIsNotNone(summary)
        self.assertTrue(isinstance(summary, pd.DataFrame))
        self.assertGreater(len(summary), 2000)

    def test_get_gene_expression(self):
        # Get gene expression for a given gene
        gene = self.vfb.term("FBgn0000014")
        print(gene)
        expression = gene.scRNAseq_expression
        self.assertIsNotNone(expression)
        self.assertTrue(isinstance(expression, VFBTerms))
        self.assertGreater(len(expression), 2000)
        print(expression[0].summary)
        summary = self.vfb.get_scRNAseq_gene_expression(gene=gene, return_dataframe=True)
        print(summary)
        self.assertIsNotNone(summary)
        self.assertTrue(isinstance(summary, pd.DataFrame))
        self.assertGreater(len(summary), 2000)

    def test_random_gene(self):
        summary = self.vfb.get_scRNAseq_gene_expression(cluster="FBlc0006144", return_dataframe=False)
        print(summary[0])
    

if __name__ == "__main__":
    unittest.main()