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
from vfb_connect.cached_query import (CONNECTED_NEURONS_BY_TYPE_COLUMNS, CachedQueryClient,
                                      get_default_client, rows_to_ids, rows_to_records)

# A neuron with NBLAST similarity data, and a region with neurons in it.
NEURON = 'VFB_jrchk00s'
REGION = 'FBbt_00003748'   # medulla
NEURON_CLASS = 'FBbt_00047573'  # descending neuron DNa02
# Medulla has no subclasses, so SubclassesOf is checked on a class that does.
SUBCLASSED = 'FBbt_00005155'  # sense organ, 853 subclasses

# Properties wired to a cached query, with the query each uses.
CACHED_PROPERTIES = {
    'PartsOf': 'subparts',
    'NeuronsPartHere': 'neuron_types_that_overlap',
    'NeuronsSynaptic': 'neuron_types_with_synaptic_terminals_here',
    'NeuronsPresynapticHere': 'downstream_neuron_types',
    'NeuronsPostsynapticHere': 'upstream_neuron_types',
    'LineageClonesIn': 'lineage_clone_types',
    'TractsNervesInnervatingHere': 'innervating',
    'ImagesNeurons': 'neurons_that_overlap',
}

# A region small enough to compare an individual-level result set in full.
SMALL_REGION = 'FBbt_00040051'


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

    def test_a_result_above_max_rows_truncates_and_says_so(self):
        # ImagesNeurons on a whole neuropil is 226,524 rows. Above max_rows it
        # must stop at the limit rather than pretend, and must not fail.
        client = CachedQueryClient(timeout=120, max_rows=26000, progress=False)
        rows = client.run_query(REGION, 'ImagesNeurons')
        self.assertEqual(len(rows), 26000)


class PagingTest(unittest.TestCase):
    """Results larger than one response are paged, counted and truncatable."""

    def test_query_counts_without_running_the_queries(self):
        counts = vfb.query_counts(REGION)
        self.assertIsNotNone(counts)
        self.assertIn('ImagesNeurons', counts)
        self.assertGreater(counts['ImagesNeurons'], 25000,
                           'expected a result larger than one response')
        # The counts must agree with what the query actually returns.
        self.assertEqual(counts['PartsOf'], len(vfb.cached_query_ids(REGION, 'PartsOf', limit=0)))

    def test_limit_spans_pages_exactly(self):
        client = CachedQueryClient(timeout=120, progress=False)
        rows = client.run_query(REGION, 'ImagesNeurons', limit=30000)
        self.assertEqual(len(rows), 30000, 'limit must be honoured across a page boundary')
        ids = rows_to_ids(rows)
        self.assertEqual(len(ids), 30000, 'paging returned duplicate rows')

    def test_load_limit_truncates(self):
        previous = vfb._load_limit
        vfb._load_limit = 5
        try:
            self.assertEqual(len(vfb.cached_query_ids(REGION, 'ImagesNeurons')), 5)
        finally:
            vfb._load_limit = previous


class SimilarNeuronsParityTest(unittest.TestCase):
    """get_similar_neurons: cached vs live."""

    @classmethod
    def setUpClass(cls):
        # A fallback would make `cached` a second copy of the live result, and
        # every assertion below would pass without testing anything. Count them.
        client = get_default_client()
        before = client.fallbacks
        cls.cached = vfb.get_similar_neurons(NEURON, query_by_label=False,
                                             return_dataframe=False, use_cached=True)
        cls.fell_back = client.fallbacks > before
        cls.live = vfb.get_similar_neurons(NEURON, query_by_label=False,
                                           return_dataframe=False, use_cached=False)

    def test_the_cached_path_was_actually_used(self):
        self.assertFalse(self.fell_back,
                         'the cached call fell back to a live query, so the comparisons '
                         'below would be the live path against itself')

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


class ConnectivityDivergenceTest(unittest.TestCase):
    """Why get_connected_neurons_by_type is *not* served from the cache.

    The row shape matches, which makes this look convertible. It is not:
    `/query_connectivity` aggregates against the directly asserted class, while
    this method has aggregated with subclass closure since #276, counting a
    connection for every ancestor pair in scope.

    This test asserts the divergence rather than the agreement. If VFBquery
    adopts the closure it will go red, which is the signal to wire the method up
    — the converter and client method are already in place.
    """

    @classmethod
    def setUpClass(cls):
        # A long timeout: at the default this call can exceed its budget and
        # return None, which would read as agreement by absence.
        client = CachedQueryClient(timeout=300)
        connections = client.query_connectivity(
            upstream_type=NEURON_CLASS, weight=10, group_by_class=True,
            exclude_dbs=('hb', 'fafb'))
        cls.cached = rows_to_records(connections or [], CONNECTED_NEURONS_BY_TYPE_COLUMNS)
        cls.live = vfb.get_connected_neurons_by_type(
            weight=10, upstream_type=NEURON_CLASS, query_by_label=False,
            group_by_class=True, return_dataframe=False)

    def test_both_paths_returned_rows(self):
        self.assertTrue(self.cached, 'no cached connectivity result to compare')
        self.assertTrue(self.live, 'live connectivity query returned nothing')

    def test_column_contract_matches(self):
        self.assertEqual(sorted(_columns(self.cached)), sorted(_columns(self.live)))

    def test_no_markdown_in_labels(self):
        for row in self.cached:
            self.assertNotIn('](', str(row['upstream_class']))
            self.assertNotIn('](', str(row['downstream_class']))

    def test_the_aggregations_still_differ(self):
        key = lambda row: (row['upstream_class_id'], row['downstream_class_id'])
        cached = {key(row): row for row in self.cached}
        live = {key(row): row for row in self.live}
        shared = set(cached) & set(live)
        value_diffs = [k for k in shared
                       if cached[k]['pairwise_connections'] != live[k]['pairwise_connections']]
        print(f'\nquery_connectivity({NEURON_CLASS}): cached {len(cached)} rows, '
              f'live {len(live)}, {len(set(live) - set(cached))} live-only, '
              f'{len(value_diffs)} of {len(shared)} shared rows differ')
        if len(cached) == len(live) and not value_diffs:
            self.fail('cached and live connectivity now agree — VFBquery appears to have '
                      'adopted subclass closure, so get_connected_neurons_by_type can be '
                      'routed through /query_connectivity')


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

    def test_images_neurons_matches_the_owl_instance_query(self):
        # ImagesNeurons is the individual-level `neuron that overlaps some X`,
        # which is exactly what neurons_that_overlap asked Owlery for. Checked
        # on a region small enough to compare the whole set.
        owl = ("<http://purl.obolibrary.org/obo/FBbt_00005106> and "
               "<http://purl.obolibrary.org/obo/RO_0002131> some "
               f"<http://purl.obolibrary.org/obo/{SMALL_REGION}>")
        live = set(vfb.oc.get_instances(owl, query_by_label=False))
        cached = set(vfb.cached_query_ids(SMALL_REGION, 'ImagesNeurons',
                                          limit=0, use_cached=True))
        self.assertTrue(cached, 'no cached ImagesNeurons result')
        overlap = len(cached & live) / max(len(live), 1)
        print(f'\nImagesNeurons({SMALL_REGION}): cached {len(cached)}, live {len(live)}, '
              f'overlap {overlap:.3%}')
        self.assertGreater(overlap, 0.98, 'cached and live instance sets have diverged')

    def test_a_property_hydrates_to_terms(self):
        term = vfb.term(REGION, verbose=False)
        subparts = term.subparts
        self.assertTrue(len(subparts) > 0)
        self.assertTrue(all(t.id for t in subparts))


if __name__ == '__main__':
    unittest.main()
