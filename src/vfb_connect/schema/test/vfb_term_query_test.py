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

    def test_get_scRNAseq_expression(self):
        # Get clusters showing expressin in given anatomy term
        term = self.vfb.term("FBbt_00100214")
        print(term)
        summary = self.vfb.get_scRNAseq_expression(id=term, return_dataframe=True)
        print(summary)
        self.assertIsNotNone(summary)
        self.assertTrue(isinstance(summary, pd.DataFrame))
        self.assertGreater(len(summary), 5)
        expression = term.scRNAseq_expression
        print(expression)
        print(expression[0].summary)
        self.assertIsNotNone(expression)
        self.assertTrue(isinstance(expression, ExpressionList))
        self.assertGreater(len(expression), 5)
        print(expression[0].summary)

    def test_scRNAseq_datasets(self):
        cluster = self.vfb.term("FBlc0006144")
        datasets = cluster.datasets
        self.vfb._load_limit = 10
        datasets[0].debug = True
        print(datasets)
        self.assertIsNotNone(datasets)
        self.assertTrue(isinstance(datasets, VFBTerms))
        self.assertGreater(len(datasets), 0)
        ds_instances = datasets[0].instances
        print(ds_instances.get_summaries())
        self.assertIsNotNone(ds_instances)
        self.assertTrue(isinstance(ds_instances, VFBTerms))
        self.assertGreater(len(ds_instances), 8)
        print(ds_instances[0].has_tag('Cluster'))

if __name__ == "__main__":
    unittest.main()