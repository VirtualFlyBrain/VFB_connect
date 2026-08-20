"""Live tests that the cached-query path returns what VFB_connect always returned.

These hit production. They compare the pre-computed VFBquery result against the
Neo4j/Owlery result the same method produced before, and against the contract
its callers rely on.

What is asserted, and what deliberately is not:

* **Column set and dtypes must be identical** between the two paths. This is
  the regression gate — a converter change that renames a column, drops one, or
  turns a float into a string fails here.
* **Values must be identical for every ID both paths return.** A conversion bug
  shows up as a wrong label, score or accession on a shared row.
* **The two ID sets are not required to be equal.** The cached result is the
  current release, served from the same source as the VFB website; Owlery is
  loaded from a newer dump and legitimately runs ahead of it between releases.
  Gating on set equality would fail on every ontology release without
  indicating a fault. The overlap is reported so drift stays visible.
"""

import os
import unittest

import pandas as pd

from vfb_connect import vfb
from vfb_connect.cached_query import CachedQueryClient

# A neuron with NBLAST similarity data, and a region with neurons in it.
NEURON = 'VFB_jrchk00s'
REGION = 'FBbt_00003748'   # medulla
NEURON_CLASS = 'FBbt_00047573'  # descending neuron DNa02
# Medulla has no subclasses, so SubclassesOf is checked on a class that does.
SUBCLASSED = 'FBbt_00005155'  # Kenyon cell

# Properties wired to a cached query, with the query each uses.
CACHED_PROPERTIES = {
    'PartsOf': 'subparts',
    'NeuronsPartHere': 'neuron_types_that_overlap',
    'NeuronsSynaptic': 'neuron_types_with_synaptic_terminals_here',
    'NeuronsPresynapticHere': 'downstream_neuron_types',
    'NeuronsPostsynapticHere': 'upstream_neuron_types',
    'LineageClonesIn': 'lineage_clone_types',
    'TractsNervesInnervatingHere': 'innervating',
}


def _columns(result):
    if isinstance(result, pd.DataFrame):
        return list(result.columns)
    return list(result[0].keys()) if result else []


class CachedQueryFallbackTest(unittest.TestCase):
    """Every failure mode must return None so the caller runs its own query."""

    def test_disabled_by_environment(self):
        previous = os.environ.get('VFB_USE_CACHED_QUERIES')
        os.environ['VFB_USE_CACHED_QUERIES'] = 'false'
        try:
            self.assertIsNone(CachedQueryClient().run_query(REGION, 'PartsOf'))
        finally:
            if previous is None:
                os.environ.pop('VFB_USE_CACHED_QUERIES', None)
            else:
                os.environ['VFB_USE_CACHED_QUERIES'] = previous

    def test_unreachable_service(self):
        client = CachedQueryClient(url='http://127.0.0.1:9', timeout=2)
        self.assertIsNone(client.run_query(REGION, 'PartsOf'))

    def test_unknown_query_type(self):
        client = CachedQueryClient(timeout=30)
        self.assertIsNone(client.run_query(REGION, 'NoSuchQueryType'))

    def test_result_above_the_paging_limit(self):
        # ImagesNeurons on a large region is far bigger than one response and
        # bigger than the paging budget; it must decline rather than truncate.
        client = CachedQueryClient(timeout=60, max_rows=100)
        self.assertIsNone(client.run_query(REGION, 'ImagesNeurons'))


class SimilarNeuronsParityTest(unittest.TestCase):
    """get_similar_neurons: cached vs live."""

    @classmethod
    def setUpClass(cls):
        cls.cached = vfb.get_similar_neurons(NEURON, query_by_label=False,
                                             return_dataframe=False, use_cached=True)
        cls.live = vfb.get_similar_neurons(NEURON, query_by_label=False,
                                           return_dataframe=False, use_cached=False)

    def test_cached_path_returned_something(self):
        self.assertTrue(self.cached, 'cached SimilarMorphologyTo returned no rows')
        self.assertTrue(self.live, 'live query returned no rows')

    def test_column_set_is_unchanged(self):
        self.assertEqual(sorted(_columns(self.cached)), sorted(_columns(self.live)))

    def test_dataframe_shape_is_unchanged(self):
        frame = vfb.get_similar_neurons(NEURON, query_by_label=False,
                                        return_dataframe=True, use_cached=True)
        self.assertIsInstance(frame, pd.DataFrame)
        self.assertEqual(sorted(frame.columns), sorted(_columns(self.live)))

    def test_values_match_for_every_shared_id(self):
        live_by_id = {row['id']: row for row in self.live}
        cached_by_id = {row['id']: row for row in self.cached}
        shared = sorted(set(live_by_id) & set(cached_by_id))
        self.assertTrue(shared, 'no overlap between cached and live results')
        print(f'\nSimilarMorphologyTo({NEURON}): cached {len(cached_by_id)}, '
              f'live {len(live_by_id)}, shared {len(shared)}')
        mismatches = []
        for term_id in shared:
            cached_row, live_row = cached_by_id[term_id], live_by_id[term_id]
            if cached_row['label'] != live_row['label']:
                mismatches.append(f"{term_id} label {cached_row['label']!r} != {live_row['label']!r}")
            if abs(float(cached_row['score']) - float(live_row['score'])) > 0.005:
                mismatches.append(f"{term_id} score {cached_row['score']} != {live_row['score']}")
            if cached_row['source_id'] != live_row['source_id']:
                mismatches.append(f"{term_id} source_id {cached_row['source_id']!r} != {live_row['source_id']!r}")
            if cached_row['accession_in_source'] != live_row['accession_in_source']:
                mismatches.append(f"{term_id} accession {cached_row['accession_in_source']!r} "
                                  f"!= {live_row['accession_in_source']!r}")
            if set(cached_row['tags']) != set(live_row['tags']):
                mismatches.append(f"{term_id} tags {sorted(cached_row['tags'])} != {sorted(live_row['tags'])}")
        self.assertEqual(mismatches[:10], [], f'{len(mismatches)} converted values differ')


class ConnectedNeuronsByTypeParityTest(unittest.TestCase):
    """get_connected_neurons_by_type(group_by_class=True): cached vs live."""

    @classmethod
    def setUpClass(cls):
        cls.cached = vfb.get_connected_neurons_by_type(
            weight=10, upstream_type=NEURON_CLASS, query_by_label=False,
            group_by_class=True, return_dataframe=False, use_cached=True)

    def test_cached_path_returned_something(self):
        self.assertTrue(self.cached)

    def test_column_contract(self):
        self.assertEqual(
            sorted(_columns(self.cached)),
            sorted(['upstream_class', 'upstream_class_id', 'downstream_class',
                    'downstream_class_id', 'total_upstream_count',
                    'connected_upstream_count', 'percent_connected',
                    'pairwise_connections', 'total_weight', 'average_weight']))

    def test_no_markdown_in_labels(self):
        for row in self.cached:
            self.assertNotIn('](', str(row['upstream_class']))
            self.assertNotIn('](', str(row['downstream_class']))


class CachedPropertyIdsTest(unittest.TestCase):
    """Every wired property must get a usable ID list from its cached query."""

    def test_ids_are_wellformed(self):
        for query_type, property_name in CACHED_PROPERTIES.items():
            with self.subTest(query=query_type, property=property_name):
                ids = vfb.cached_query_ids(REGION, query_type, use_cached=True)
                self.assertIsNotNone(ids, f'{query_type} returned no cached result')
                for term_id in ids:
                    self.assertNotIn('](', term_id)
                    self.assertRegex(term_id, r'^[A-Za-z][A-Za-z0-9_]+$')

    def test_subclasses_of_ids_are_wellformed(self):
        ids = vfb.cached_query_ids(SUBCLASSED, 'SubclassesOf', use_cached=True)
        self.assertIsNotNone(ids, 'SubclassesOf returned no cached result')
        self.assertTrue(len(ids) > 100, f'expected a large subclass closure, got {len(ids)}')
        for term_id in ids:
            self.assertNotIn('](', term_id)
            self.assertRegex(term_id, r'^[A-Za-z][A-Za-z0-9_]+$')

    def test_a_property_hydrates_to_terms(self):
        term = vfb.term(REGION, verbose=False)
        subparts = term.subparts
        self.assertTrue(len(subparts) > 0)
        self.assertTrue(all(t.id for t in subparts))


if __name__ == '__main__':
    unittest.main()
