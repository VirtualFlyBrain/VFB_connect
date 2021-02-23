import warnings

from .owl.owlery_query_tools import OWLeryConnect
from .neo.neo4j_tools import Neo4jConnect, re, dict_cursor
from .neo.query_wrapper import QueryWrapper
from .default_servers import get_default_servers
import pandas as pd


def gen_short_form(iri):
    """Generate short_form (string) from an iri string
    iri: An iri string"""
    return re.split('/|#', iri)[-1]


class VfbConnect:
    """API wrapper class.  By default this wraps connections to the more basal API endpoints (OWL, Neo4j).

    Top level methods combined semantic queries that range across VFB content with neo4j queries, returning detailed
    metadata about anatomical classes and individuals that fulfill these queries.

    Methods allowing direct queries cypher queries of the production Neo4j are available under `nc`

    Methods for querying Neo4j with arbitrary lists of identifiers to return rich metadata or mappings to external IDs
    are available under `neo_query_wrapper`.

    Direct access OWL queries, returning identifiers only, are available via methods under `oc`

    Example semantic queries (OWL class expressions).  Note quoting scheme (outer `"` + single quotes for entities).

    "'GABAergic neuron'"
    "'GABAeric neuron' that 'overlaps' some 'antennal lobe'"

    """
    def __init__(self, neo_endpoint=get_default_servers()['neo_endpoint'],
                 neo_credentials=get_default_servers()['neo_credentials'],
                 owlery_endpoint=get_default_servers()['owlery_endpoint'],
                 lookup_prefixes=('FBbt', 'VFBexp', 'VFBext')):
        connections = {
            'neo': {
                "endpoint": neo_endpoint,
                "usr": neo_credentials[0],
                "pwd": neo_credentials[1]
            }
        }
        self.nc = Neo4jConnect(**connections['neo'])
        self.neo_query_wrapper = QueryWrapper(**connections['neo'])

        self.oc = OWLeryConnect(endpoint=owlery_endpoint,
                                lookup=self.nc.get_lookup(limit_by_prefix=lookup_prefixes))
        self.vfb_base = "https://v2.virtualflybrain.org/org.geppetto.frontend/geppetto?id="

    def get_terms_by_region(self, region, cells_only=False, verbose=False, query_by_label=True, summary=True):
        """Generate JSON reports for all terms relevant to
         annotating some specific region,
        optionally limited by to cells"""
        preq = ''
        if cells_only:
            preq = "'cell' that "
        owl_query = preq + "'overlaps' some '%s'" % region
        if verbose:
            print("Running query: %s" % owl_query)

        terms = self.oc.get_subclasses(owl_query, query_by_label=query_by_label)
        if verbose:
            print("Found: %d terms" % len(terms))
        return self.neo_query_wrapper.get_type_TermInfo(list(map(gen_short_form, terms)),
                                                        summary=summary)

    def get_subclasses(self, class_expression, query_by_label=True, direct=False, summary=False):
        """Generate JSON report of all subclasses of class_expression."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_subclasses("%s" % class_expression, query_by_label=query_by_label)
        return self.neo_query_wrapper.get_type_TermInfo(list(map(gen_short_form, terms)),
                                                        summary=summary)
    def get_superclasses(self, class_expression, query_by_label=True, direct=False, summary=False):
        """Generate JSON report of all superclasses of class_expression."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_superclasses("%s" % class_expression, query_by_label=query_by_label)
        return self.neo_query_wrapper.get_type_TermInfo(list(map(gen_short_form, terms)),
                                                        summary=summary)

    def get_instances(self, class_expression, query_by_label=True, direct=False, summary=False):
        """Generate JSON report of all instances of class_expression. Instances are specific examples
        of a type/class of structure, e.g. a specific instance of the neuron DA1 adPN from the FAFB_catmaid
         database.  Instances are typically associated with registered 3D image data and may include
         connectomics data."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_instances("%s" % class_expression, query_by_label=query_by_label)
        return self.neo_query_wrapper.get_anatomical_individual_TermInfo(list(map(gen_short_form, terms)),
                                                                         summary=summary)

    def _get_neurons_connected_to(self, neuron, weight, direction, classification=None, query_by_label=True):
        instances = []
        directions = ['upstream', 'downstream']
        if not (direction in directions):
            raise Exception(ValueError)  # Needs improving
        if classification:
            instances = self.oc.get_instances(classification, query_by_label=query_by_label)
        cypher_query = 'MATCH (upstream:Neuron)-[r:synapsed_to]->(downstream:Neuron) ' \
                       'WHERE r.weight[0] >= %d ' % weight
        if query_by_label:
            cypher_query += 'AND %s.label = "%s" ' % (direction, neuron)
        else:
            cypher_query += 'AND %s.short_form = "%s" ' % (direction, neuron)
        if classification and instances:
            directions.remove(direction)
            cypher_query += "AND %s.iri IN %s " % (directions[0], str(instances))
        cypher_query += "RETURN upstream.short_form as query_neuron_id, upstream.label as query_neuron_name, " \
                        "r.weight[0] as weight, " \
                        "downstream.short_form as target_neuron_id, downstream.label as target_neuron_name"
        r = self.nc.commit_list([cypher_query])
        dc = dict_cursor(r)
        return pd.DataFrame.from_records(dc)

    def get_neurons_downstream_of(self, neuron, weight, classification=None, query_by_label=True):
        """Get all neurons downstream of individual `neuron` (short_form if query_by_label=False, otherwise label)
        with connection strength > threshold.  Optionally restrict target neurons to those specified by
        `classification = 'class expression' e.g. "'Kenyon cell'" or "'neuron' that overlaps 'lateral horn'"."""
        return self._get_neurons_connected_to(neuron=neuron, weight=weight, direction='upstream',
                                              classification=classification, query_by_label=query_by_label)

    def get_neurons_upstream_of(self, neuron, weight, classification=None, query_by_label=True):
        """Get all neurons downstream of individual `neuron` (short_form if query_by_label=False, otherwise label)
         with connection strength > threshold.  Optionally restrict target neurons to those specified by
         `classification = 'class expression' e.g. "'Kenyon cell'" or "'neuron' that overlaps 'lateral horn'"."""
        return self._get_neurons_connected_to(neuron=neuron, weight=weight, direction='downstream',
                                              classification=classification, query_by_label=query_by_label)

    def get_connected_neurons_by_type(self, upstream_type, downstream_type, weight, query_by_label=True):
        """Get all synaptic connections between individual neurons of `upstream_type` and `dowstream_type` where
         each of these types is the name of a neuron class/type in VFB."""

        # Note - chose not to do this with class expressions to avoid poor performance and blowing up results.
        # This might be confusing tough, given behavior of other, similar methods.
        # Might be better to refactor to work out if query is class expression or class & funnel query method
        # accordingly.

        qprop = 'short_form'
        if query_by_label:
            qprop = 'label'
#        upstream_instances = self.oc.get_instances(upstream_type, query_by_label=query_by_label)
        cypher_query = "MATCH (up:Class:Neuron)<-[:SUBCLASSOF|INSTANCEOF*..]-(n1:Neuron:Individual)" \
                       "-[r:synapsed_to]->(n2:Neuron:Individual)-[:SUBCLASSOF|INSTANCEOF*..]->(down:Class:Neuron) " \
                       "WHERE r.weight[0] > %d " % weight
        cypher_query += 'AND up.%s = "%s" and down.%s = "%s" ' % (qprop, upstream_type, qprop, downstream_type)
        cypher_query += "RETURN n1.short_form as upstream_neuron_id, n1.label as upstream_neuron_name, " \
                        "r.weight[0] as weight, " \
                        "n2.short_form as downstream_neuron_id, n2.label as downstream_neuron_name"
        r = self.nc.commit_list([cypher_query])
        dc = dict_cursor(r)
        return pd.DataFrame.from_records(dc)

    def get_vfb_link(self, short_forms: iter, template):
        """Takes a list of VFB IDs (short_forms) for individuals and returns a link to VFB loading all available images
         of neurons on that template."""
        return self.vfb_base + short_forms.pop() + "&i=" + template + ',' + ','.join(short_forms)

    def get_images_by_type(self, class_expression, template, image_folder,
                           image_type='swc', query_by_label=True, direct=False):
        """Retrieve images of instances of `class_expression` registered to `template` and save to disk,
        along with manifest and references, to `image_folder`. Default image type = swc. Also supported: obj, nrrd, rds, wlz.
        Returns manifest"""
        instances = self.oc.get_instances(class_expression,
                                          query_by_label=query_by_label,
                                          direct=direct)
        return self.neo_query_wrapper.get_images([gen_short_form(i) for i in instances],
                                                 template=template,
                                                 image_folder=image_folder,
                                                 image_type=image_type)








