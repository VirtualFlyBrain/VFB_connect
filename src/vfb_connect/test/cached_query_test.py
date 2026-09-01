"""Offline tests for the cached-query converters.

These pin the conversion from VFBquery's web-formatted rows to the plain
values, ID lists and records VFB_connect returns. They run against committed
fixtures of real cached rows plus the awkward cell shapes the website's own
processor documents, so a change in the converter fails here rather than in
somebody's notebook. No network.
"""

import json
import unittest
from importlib.resources import files

from vfb_connect.cached_query import (
    CONNECTED_NEURONS_BY_TYPE_COLUMNS,
    SIMILAR_NEURONS_COLUMNS,
    parse_images,
    parse_link,
    parse_links,
    parse_tags,
    rows_to_ids,
    rows_to_records,
)

FIXTURES = json.loads(
    (files('vfb_connect') / 'test' / 'fixtures' / 'cached_query_rows.json').read_text()
)


class ParseCellTest(unittest.TestCase):
    """The cell grammar, including the shapes that have broken parsers before."""

    def test_link(self):
        self.assertEqual(parse_link('[medulla](FBbt_00003748)'), ('medulla', 'FBbt_00003748'))

    def test_link_plain_text_passes_through(self):
        # Parentheses in a plain-text cell must not be read as a link target.
        self.assertEqual(parse_link('transmission electron microscopy (TEM)'),
                         ('transmission electron microscopy (TEM)', None))

    def test_link_empty(self):
        self.assertEqual(parse_link(''), ('', None))
        self.assertEqual(parse_link(None), ('', None))

    def test_link_percent_encoded_brackets(self):
        # VFBquery percent-encodes brackets inside a label so the frontend's
        # link parser is not confused by a name such as "Dm8 [FAFB]".
        self.assertEqual(parse_link('[Dm8 %5BFAFB%5D](FBbt_00110069)'),
                         ('Dm8 [FAFB]', 'FBbt_00110069'))

    def test_links_multi(self):
        cell = '[lobula plate columnar neuron LPC1](FBbt_00111767); [adult neuron](FBbt_00047095)'
        self.assertEqual(parse_links(cell),
                         [('lobula plate columnar neuron LPC1', 'FBbt_00111767'),
                          ('adult neuron', 'FBbt_00047095')])

    def test_links_empty(self):
        self.assertEqual(parse_links(''), [])

    def test_tags(self):
        self.assertEqual(parse_tags('Adult|Nervous_system|Neuron'),
                         ['Adult', 'Nervous_system', 'Neuron'])
        self.assertEqual(parse_tags(''), [])

    def test_image(self):
        cell = "[![Dm8b_L aligned to JRC2018U](https://x/thumbnail.png 'Dm8b_L aligned to JRC2018U')](VFB_00101567,VFB_001)"
        self.assertEqual(parse_images(cell), [{
            'alt': 'Dm8b_L aligned to JRC2018U',
            'url': 'https://x/thumbnail.png',
            'ref': 'VFB_00101567,VFB_001',
        }])

    def test_image_title_containing_apostrophe(self):
        # Kenyon-cell and PAM labels carry apostrophes. A naive `'[^']*'` title
        # body ends the title early and drops the row.
        cell = "[![KCa'b'-ap1_R aligned to JRC2018U](https://x/thumbnail.png 'KCa'b'-ap1_R aligned to JRC2018U')](VFB_1)"
        images = parse_images(cell)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['url'], 'https://x/thumbnail.png')
        self.assertEqual(images[0]['ref'], 'VFB_1')

    def test_image_without_url_is_skipped(self):
        # A term with no materialised image is emitted with an empty URL; it
        # must not become a blank entry.
        self.assertEqual(parse_images("[![alt]( 'alt')](VFB_1)"), [])

    def test_image_multi_and_http_upgraded(self):
        cell = ("[![a](http://x/1.png 'a')](VFB_1); "
                "[![b](https://x/2.png 'b')](VFB_2)")
        images = parse_images(cell)
        self.assertEqual([i['url'] for i in images],
                         ['https://x/1.png', 'https://x/2.png'])

    def test_image_on_a_non_image_cell(self):
        self.assertEqual(parse_images('[medulla](FBbt_00003748)'), [])


class RowsToIdsTest(unittest.TestCase):

    def test_ids_are_ordered_and_deduplicated(self):
        rows = [{'id': 'a'}, {'id': 'b'}, {'id': 'a'}, {'id': ''}, {}]
        self.assertEqual(rows_to_ids(rows), ['a', 'b'])

    def test_ids_unwrap_a_linked_id_column(self):
        self.assertEqual(rows_to_ids([{'id': '[medulla](FBbt_00003748)'}]), ['FBbt_00003748'])

    def test_ids_on_empty_input(self):
        self.assertEqual(rows_to_ids([]), [])
        self.assertEqual(rows_to_ids(None), [])

    def test_ids_from_every_fixture(self):
        for query_type, fixture in FIXTURES.items():
            if 'rows' not in fixture:
                continue
            ids = rows_to_ids(fixture['rows'])
            self.assertEqual(len(ids), len(fixture['rows']), query_type)
            for term_id in ids:
                self.assertNotIn('](', term_id, f'{query_type}: markdown leaked into an id')
                self.assertRegex(term_id, r'^[A-Za-z][A-Za-z0-9_]+$', query_type)


class SimilarNeuronsConversionTest(unittest.TestCase):
    """The one mapping where a column name means different things either side.

    VFB_connect's ``tags`` has always held the class labels the neuron
    instantiates. VFBquery calls that column ``type`` and uses ``tags`` for
    SuperTypes, so the converter reads ``type`` — mapping ``tags`` to ``tags``
    would silently change what the column means.
    """

    def setUp(self):
        self.rows = FIXTURES['SimilarMorphologyTo']['rows']
        self.records = rows_to_records(self.rows, SIMILAR_NEURONS_COLUMNS)

    def test_column_contract(self):
        self.assertEqual(set(self.records[0].keys()),
                         {'id', 'score', 'label', 'tags', 'source_id', 'accession_in_source'})

    def test_no_markdown_survives(self):
        for record in self.records:
            for column in ('id', 'label', 'source_id', 'accession_in_source'):
                self.assertNotIn('](', str(record[column]), column)
            for tag in record['tags']:
                self.assertNotIn('](', tag)

    def test_score_is_numeric(self):
        for record in self.records:
            self.assertIsInstance(record['score'], float)

    def test_tags_are_class_labels_not_supertypes(self):
        supertypes = set(parse_tags(self.rows[0]['tags']))
        tags = self.records[0]['tags']
        self.assertTrue(tags, 'expected at least one class label')
        self.assertFalse(supertypes & set(tags),
                         'tags came from the SuperTypes column, not the class labels')

    def test_label_matches_the_name_cell(self):
        for row, record in zip(self.rows, self.records):
            self.assertEqual(record['label'], parse_link(row['name'])[0])

    def test_source_columns_are_split_correctly(self):
        # `source` links the data source, `source_id` links the accession, and
        # VFB_connect names them the other way round: source_id is the site's
        # short_form and accession_in_source is the bare accession.
        for row, record in zip(self.rows, self.records):
            self.assertEqual(record['source_id'], parse_link(row['source'])[1])
            self.assertEqual(record['accession_in_source'], parse_link(row['source_id'])[0])


class ConnectivityConversionTest(unittest.TestCase):

    def test_column_contract_and_pass_through(self):
        fixture = FIXTURES.get('query_connectivity')
        if not fixture:
            self.skipTest('no connectivity fixture')
        records = rows_to_records(fixture['connections'], CONNECTED_NEURONS_BY_TYPE_COLUMNS)
        self.assertEqual(set(records[0].keys()), set(CONNECTED_NEURONS_BY_TYPE_COLUMNS))
        for record in records:
            self.assertIsInstance(record['pairwise_connections'], int)
            self.assertNotIn('](', str(record['upstream_class']))


class ConnectivityCachedMatchesLiveTest(unittest.TestCase):
    """After VFBquery adopted the subclass-closure rollup (#101), the cached
    endpoint must match the live query for group_by_class=True."""

    def test_cached_grouped_matches_live(self):
        from vfb_connect import vfb  # integration: hits production
        kw = dict(upstream_type="FBbt_00047030", downstream_type="FBbt_00003655",
                  weight=1, group_by_class=True, query_by_label=False,
                  exclude_dbs=[], return_dataframe=False)
        cached = vfb.get_connected_neurons_by_type(**kw, use_cached=True)
        live = vfb.get_connected_neurons_by_type(**kw, use_cached=False)
        key = lambda r: (r['upstream_class_id'], r['downstream_class_id'])
        self.assertEqual(
            {key(r): (r['total_weight'], r['pairwise_connections'],
                      r['percent_connected']) for r in cached},
            {key(r): (r['total_weight'], r['pairwise_connections'],
                      r['percent_connected']) for r in live},
        )


if __name__ == '__main__':
    unittest.main()
