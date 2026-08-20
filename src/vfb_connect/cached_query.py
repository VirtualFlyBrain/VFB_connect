"""Client and converters for VFBquery's cached query results.

VFBquery owns the specification of VFB's named queries — ``NeuronsSynaptic``,
``PartsOf``, ``SimilarMorphologyTo`` and the rest. Their results are
pre-computed and served from https://v3-cached.virtualflybrain.org, which is
the same source the VFB website reads, so a result fetched here is the current
release's answer. Fetching one is typically an order of magnitude cheaper than
re-deriving it from Neo4j or Owlery, and it removes a second round-trip: the
rows already carry the label, tags, template and thumbnail that VFB_connect
would otherwise fetch per ID.

The rows are formatted for the web frontend: cells are markdown links
(``[label](id)``), image carousels (``[![alt](url 'alt')](ref)``) and
pipe-joined tag strings, with square brackets inside labels percent-encoded.
This module does two things:

* :class:`CachedQueryClient` fetches a named query result and returns ``None``
  rather than raising whenever the answer cannot be trusted — service down,
  timeout, non-200, or a truncated payload. Every call site keeps its previous
  implementation as the fallback, so an outage degrades to the old behaviour
  instead of breaking.
* The ``parse_*`` and ``rows_to_*`` helpers turn those cells back into the
  plain values, ID lists and records the rest of VFB_connect works with.

Where a method's job is to return terms, use :func:`rows_to_ids` and let the
existing hydration build the objects: the cached query then supplies only the
ID set, and everything downstream is unchanged. Reach for
:func:`rows_to_records` only where a method's contract is a table of
query-specific columns.

The cell grammar mirrors ``VFBqueryJsonProcessor`` in ``uk.ac.vfb.geppetto``,
which performs the same conversion for the website — including its handling of
apostrophes inside image titles and of image items with no URL.
"""

import os
import re
from urllib.parse import unquote

import requests

__all__ = [
    'CachedQueryClient',
    'get_default_client',
    'cached_queries_enabled',
    'parse_link',
    'parse_links',
    'parse_tags',
    'parse_images',
    'rows_to_ids',
    'rows_to_records',
    'SIMILAR_NEURONS_COLUMNS',
    'CONNECTED_NEURONS_BY_TYPE_COLUMNS',
]


# ---------------------------------------------------------------------------
# Markdown cell parsing
# ---------------------------------------------------------------------------
#
# VFBquery builds these cells either in Cypher (``apoc.text.format``) or in
# Python, then runs them through its ``encode_markdown_links`` step, which
# percent-encodes ``[`` and ``]`` *inside the label* so the frontend's link
# parser is not confused by a bracketed name such as "Dm8 [FAFB]". Labels are
# therefore unquoted on the way back out.

# `[label](target)`. No VFB target contains whitespace or parentheses.
_LINK_RE = re.compile(r'\[(?P<label>[^\[\]]*)\]\((?P<target>[^()\s]*)\)')

# `[![alt](url 'title')](ref)`.
#
# The title delimiter is captured and back-referenced so an apostrophe *inside*
# the title does not end it early — neuron labels such as ``KCa'b'-ap1_R`` and
# ``PAM03(B2B'2a)_L`` are common, and a naive `'[^']*'` body drops every row
# that contains one. This is the same fix the website's Java processor carries.
_IMAGE_RE = re.compile(
    r"\[!\[(?P<alt>[^\]]*)\]\((?P<url>[^'\"]*?)(?:\s+(?P<q>['\"]).*?(?P=q)\s*)?\)\]\((?P<ref>[^)]+)\)"
)


def _clean(text):
    """Undo the percent-encoding VFBquery applies to bracketed labels."""
    return unquote(text) if text else ''


def parse_link(cell):
    """Split a single markdown-link cell into ``(label, target)``.

    Plain text comes back as ``(text, None)`` and an empty cell as
    ``('', None)``, so callers can treat every cell alike without first asking
    whether it happens to be a link.

    >>> parse_link('[medulla](FBbt_00003748)')
    ('medulla', 'FBbt_00003748')
    >>> parse_link('transmission electron microscopy (TEM)')
    ('transmission electron microscopy (TEM)', None)
    >>> parse_link('')
    ('', None)
    """
    if not cell:
        return '', None
    cell = str(cell)
    match = _LINK_RE.search(cell)
    if not match:
        return cell, None
    return _clean(match.group('label')), match.group('target')


def parse_links(cell, sep='; '):
    """Split a multi-link cell into a list of ``(label, target)`` pairs.

    VFBquery joins repeated values with ``'; '`` — the ``type`` column of a
    similarity result carries every class the neuron instantiates that way.
    Empty cells give an empty list.
    """
    if not cell:
        return []
    return [parse_link(part) for part in str(cell).split(sep) if part.strip()]


def parse_tags(cell):
    """Split a pipe-joined tag cell into a list.

    These are VFB SuperTypes (``Nervous_system|Adult|Cholinergic``), not class
    labels. For the classes a term instantiates, parse the ``type`` column with
    :func:`parse_links`.
    """
    if not cell:
        return []
    return [tag for tag in str(cell).split('|') if tag]


def parse_images(cell, sep='; '):
    """Split an image-carousel cell into a list of ``{alt, url, ref}`` dicts.

    Items carrying no URL — VFBquery emits ``[![alt]( 'alt')](ref)`` for a term
    with no materialised image — are skipped rather than returned blank, and
    ``http://`` URLs are promoted to ``https://``, both matching what the
    website's processor does. Cells holding no image markdown give an empty
    list.
    """
    if not cell:
        return []
    images = []
    for match in _IMAGE_RE.finditer(str(cell)):
        url = (match.group('url') or '').strip()
        if not url:
            continue
        images.append({
            'alt': _clean(match.group('alt')),
            'url': url.replace('http://', 'https://'),
            'ref': match.group('ref'),
        })
    return images


# ---------------------------------------------------------------------------
# Row conversion
# ---------------------------------------------------------------------------

def rows_to_ids(rows, column='id'):
    """Return the ID column of a cached result, in order, without duplicates.

    This is the lossless conversion. For any method whose job is to return
    terms, the cached query supplies the ID set and the existing hydration path
    builds the objects exactly as before.
    """
    seen = set()
    ids = []
    for row in rows or []:
        value = row.get(column)
        if not value:
            continue
        # Some columns carry the id as a link even where a bare id is expected.
        if '](' in str(value):
            _, value = parse_link(value)
        if value and value not in seen:
            seen.add(value)
            ids.append(value)
    return ids


def rows_to_records(rows, colmap):
    """Convert cached rows into a method's own column contract.

    ``colmap`` maps each output column to either a source column name (copied
    verbatim) or a ``(source_column, extractor)`` pair, where ``extractor`` is
    called with the raw cell. Use this only where a method returns a table of
    query-specific columns; anything returning terms should go through
    :func:`rows_to_ids`.
    """
    records = []
    for row in rows or []:
        record = {}
        for out_column, spec in colmap.items():
            if isinstance(spec, tuple):
                source, extractor = spec
                record[out_column] = extractor(row.get(source))
            else:
                record[out_column] = row.get(spec)
        records.append(record)
    return records


def _to_float(cell):
    """Cached scores arrive as strings; VFB_connect's contract is a number."""
    try:
        return float(cell)
    except (TypeError, ValueError):
        return cell


#: ``get_similar_neurons`` / ``get_potential_drivers`` column contract.
#:
#: Note ``tags``: VFB_connect has always returned the *class labels* the
#: neuron instantiates, which VFBquery carries in its ``type`` column. The
#: cached ``tags`` column is something else — VFB SuperTypes — so mapping
#: ``tags`` to ``tags`` here would quietly change what the column means.
SIMILAR_NEURONS_COLUMNS = {
    'id': 'id',
    'score': ('score', _to_float),
    'label': ('name', lambda cell: parse_link(cell)[0]),
    'tags': ('type', lambda cell: [label for label, _ in parse_links(cell)]),
    'source_id': ('source', lambda cell: parse_link(cell)[1]),
    'accession_in_source': ('source_id', lambda cell: parse_link(cell)[0]),
}

#: ``get_connected_neurons_by_type(group_by_class=True)`` column contract.
#: ``/query_connectivity`` already returns these as plain values, so this is a
#: pass-through that exists to pin the column set.
CONNECTED_NEURONS_BY_TYPE_COLUMNS = {
    'upstream_class': 'upstream_class',
    'upstream_class_id': 'upstream_class_id',
    'downstream_class': 'downstream_class',
    'downstream_class_id': 'downstream_class_id',
    'total_upstream_count': 'total_upstream_count',
    'connected_upstream_count': 'connected_upstream_count',
    'percent_connected': 'percent_connected',
    'pairwise_connections': 'pairwise_connections',
    'total_weight': 'total_weight',
    'average_weight': 'average_weight',
}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

DEFAULT_CACHED_QUERY_URL = 'https://v3-cached.virtualflybrain.org'

# Warm responses are 200-400ms, but a revalidation against a cold upstream has
# been seen to take upwards of 40s. A caller that waits that long is worse off
# than one that ran the query itself, so the budget is deliberately short and
# overrunning it falls through to the live path.
DEFAULT_TIMEOUT = 30

# The service caps a single response; anything longer has to be paged.
_PAGE_SIZE = 25000

# Above this, paging costs more than the query it replaces. Falls through.
DEFAULT_MAX_ROWS = 100000


def cached_queries_enabled():
    """Whether cached results may be used. Set ``VFB_USE_CACHED_QUERIES=false`` to disable."""
    return os.getenv('VFB_USE_CACHED_QUERIES', 'true').lower() not in ('false', '0', 'no', 'off')


class CachedQueryClient:
    """Fetch pre-computed VFBquery results, or ``None`` if they cannot be trusted.

    Nothing here raises on a service problem. Every method returns ``None``
    when the answer is missing, incomplete or slow, which is the caller's
    signal to run its own query instead.
    """

    def __init__(self, url=None, timeout=DEFAULT_TIMEOUT, max_rows=DEFAULT_MAX_ROWS, verbose=False):
        self.url = (url or os.getenv('VFB_CACHED_QUERY_URL', DEFAULT_CACHED_QUERY_URL)).rstrip('/')
        self.timeout = timeout
        self.max_rows = max_rows
        self.verbose = verbose
        self._session = requests.Session()

    def _warn(self, message):
        if self.verbose:
            print(f'\033[33mWarning:\033[0m {message}')

    def _get(self, path, params):
        if not cached_queries_enabled():
            return None
        try:
            response = self._session.get(f'{self.url}{path}', params=params, timeout=self.timeout)
        except requests.RequestException as error:
            self._warn(f'cached query unavailable ({error}); using a live query.')
            return None
        if response.status_code != 200:
            self._warn(f'cached query returned HTTP {response.status_code}; using a live query.')
            return None
        try:
            return response.json()
        except ValueError:
            self._warn('cached query returned a non-JSON body; using a live query.')
            return None

    @staticmethod
    def _rows_of(payload):
        if not isinstance(payload, dict):
            return None, None
        rows = payload.get('rows')
        if rows is None:
            rows = payload.get('data')
        return rows, payload.get('count')

    def run_query(self, short_form, query_type):
        """Return every row of a named VFBquery query, or ``None``.

        Results longer than one response are paged until the reported ``count``
        is reached. A payload that neither completes nor pages cleanly is
        rejected: a caller cannot tell a truncated preview from a genuinely
        short answer, and guessing wrong loses rows silently.
        """
        payload = self._get('/run_query', {
            'id': short_form, 'query_type': query_type, 'limit': 0, 'offset': 0,
        })
        rows, count = self._rows_of(payload)
        if rows is None:
            return None

        # count == -1 means "uncounted", not "empty" — the rows are still whole.
        if not isinstance(count, int) or count < 0 or count == len(rows):
            return rows

        if count > self.max_rows:
            self._warn(f'cached {query_type}({short_form}) has {count} rows, above the '
                       f'{self.max_rows} paging limit; using a live query.')
            return None

        while len(rows) < count:
            page_payload = self._get('/run_query', {
                'id': short_form, 'query_type': query_type,
                'limit': _PAGE_SIZE, 'offset': len(rows),
            })
            page, _ = self._rows_of(page_payload)
            if not page:
                self._warn(f'cached {query_type}({short_form}) stopped paging at '
                           f'{len(rows)} of {count} rows; using a live query.')
                return None
            rows.extend(page)

        return rows

    def query_connectivity(self, upstream_type=None, downstream_type=None, weight=5,
                           group_by_class=False, exclude_dbs=('hb', 'fafb')):
        """Return the connection list for a type-to-type connectivity query, or ``None``."""
        params = {
            'weight': weight,
            'group_by_class': 'true' if group_by_class else 'false',
        }
        if upstream_type:
            params['upstream_type'] = upstream_type
        if downstream_type:
            params['downstream_type'] = downstream_type
        if exclude_dbs is not None:
            params['exclude_dbs'] = ','.join(exclude_dbs)
        payload = self._get('/query_connectivity', params)
        if not isinstance(payload, dict):
            return None
        for warning in payload.get('warnings') or []:
            self._warn(f'cached connectivity query: {warning}')
        return payload.get('connections')


_default_client = None


def get_default_client(verbose=False):
    """Return the process-wide client, creating it on first use."""
    global _default_client
    if _default_client is None:
        _default_client = CachedQueryClient(verbose=verbose)
    return _default_client
