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
        self.lookup = self.nc.get_lookup(limit_by_prefix=lookup_prefixes)
        self.oc = OWLeryConnect(endpoint=owlery_endpoint,
                                lookup=self.lookup)
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
            if query_by_label:
                class_expression = self.lookup[class_expression].replace(':', '_')
            out = self.neo_query_wrapper._get_anatomical_individual_TermInfo_by_type(class_expression,
                                                                                     summary=True)
        else:
            terms = self.oc.get_instances("%s" % class_expression, query_by_label=query_by_label)
            out = self.neo_query_wrapper.get_anatomical_individual_TermInfo(list(map(gen_short_form, terms)),
                                                                            summary=summary)
        return out

    def _get_neurons_connected_to(self, neuron, weight, direction, classification=None, query_by_label=True,
                                  return_dataframe=True):
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
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        else:
            return dc

    def get_similar_neurons(self, neuron, similarity_score='NBLAST_score', cutoff=None, source=None, return_dataframe=True):
        """Get all neurons """
        query = "MATCH (c1:Class)<-[:INSTANCEOF]-(n1)-[r:has_similar_morphology_to]-(n2)-[:INSTANCEOF]->(c2:Class) " \
                "WHERE n1.short_form = '%s' " \
                "WITH c1, n1, r, n2, c2 " \
                "OPTIONAL MATCH (n1)-[dbx1:database_cross_reference]->(s1:Site), " \
                "(n2)-[dbx2:database_cross_reference]->(s2:Site) " \
                "WHERE s1.is_data_source and s2.is_data_source " \
                "RETURN DISTINCT n2.short_form AS id, r.NBLAST_score[0] AS NBLAST_score, n2.label AS label, " \
                "COLLECT(c2.label) AS types, s2.short_form AS source_id, dbx2.accession[0] AS accession_in_source " \
                "ORDER BY %s DESC""" % (neuron, similarity_score)
        dc = self.neo_query_wrapper._query(query)
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        else:
            return dc

    def get_neurons_downstream_of(self, neuron, weight, classification=None, query_by_label=True,
                                  return_dataframe = True):
        """Get all neurons downstream of individual `neuron` (short_form if query_by_label=False, otherwise label)
        with connection strength > threshold.  Optionally restrict target neurons to those specified by
        `classification = 'class expression' e.g. "'Kenyon cell'" or "'neuron' that overlaps 'lateral horn'"."""
        return self._get_neurons_connected_to(neuron=neuron, weight=weight, direction='upstream',
                                              classification=classification, query_by_label=query_by_label,
                                              return_dataframe=return_dataframe)

    def get_neurons_upstream_of(self, neuron, weight, classification=None, query_by_label=True, return_dataframe=True):
        """Get all neurons downstream of individual `neuron` (short_form if query_by_label=False, otherwise label)
         with connection strength > threshold.  Optionally restrict target neurons to those specified by
         `classification = 'class expression' e.g. "'Kenyon cell'" or "'neuron' that overlaps 'lateral horn'"."""
        return self._get_neurons_connected_to(neuron=neuron, weight=weight, direction='downstream',
                                              classification=classification, query_by_label=query_by_label,
                                              return_dataframe=return_dataframe)

    def get_connected_neurons_by_type(self, upstream_type, downstream_type, weight, query_by_label=True,
                                      return_dataframe=True):
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
        cypher_query = "MATCH (up:Class:Neuron)<-[:SUBCLASSOF|INSTANCEOF*..]-(n1:Neuron:Individual)-[r:synapsed_to]->" \
                       "(n2:Neuron:Individual)-[:SUBCLASSOF|INSTANCEOF*..]->(down:Class:Neuron)"
        cypher_query += "WHERE r.weight[0] > %d " % weight
        cypher_query += 'AND up.%s = "%s" and down.%s = "%s" ' % (qprop, upstream_type, qprop, downstream_type)
        cypher_query += "MATCH (c1)<-[:INSTANCEOF]-(n1),  (c2)<-[:INSTANCEOF]-(n2)" \
                        "OPTIONAL MATCH (n1)-[r1:database_cross_reference]->(s1:Site) " \
                        "WHERE exists(s1.is_data_source) AND s1.is_data_source = True " \
                        "OPTIONAL MATCH (n2)-[r2:database_cross_reference]->(s2:Site) " \
                        "WHERE exists(s1.is_data_source) AND s2.is_data_source = True " \
                        "RETURN n1.short_form as upstream_neuron_id, n1.label as upstream_neuron_name, " \
                        "r.weight[0] as weight, " \
                        "n2.short_form as downstream_neuron_id, n2.label as downstream_neuron_name, " \
                        "apoc.text.join(collect(c1.label),'|') AS upstream_class, " \
                        "apoc.text.join(collect(c2.label),'|') as downstream_class, " \
                        "s1.short_form AS up_data_source, r1.accession[0] as up_accession," \
                        "s2.short_form AS down_source, r2.accession[0] AS down_accession"

        r = self.nc.commit_list([cypher_query])
        dc = dict_cursor(r)
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        else:
            return dc

    def get_instances_by_dataset(self, dataset, summary=False):
        """Returns metadata for a dataset"""
        if dataset:
            query = "MATCH (ds:DataSet)<-[:has_source]-(i:Individual) " \
                    "WHERE ds.short_form = '%s' " \
                    "RETURN collect(i.short_form) as inds" % dataset
            dc = self.neo_query_wrapper._query(query)  # Would better to use the original column oriented return!
            return self.neo_query_wrapper.get_anatomical_individual_TermInfo(dc[0]['inds'], summary=summary)
    

    def get_vfb_link(self, short_forms: iter, template):
        """Takes a list of VFB IDs (short_forms) and the name (label) of a template.
         Returns a link to VFB loading all available images
         of neurons on that template."""
        short_forms = list(short_forms)
        query = "MATCH (t:Template { label: '%s'}) return t.short_form" % template
        dc = self.neo_query_wrapper._query(query)
        if not dc:
            raise ValueError("Unrecognised template name %s" % template)
        else:
            return self.vfb_base + short_forms.pop() + "&i=" + dc[0]['t.short_form'] + ',' + ','.join(short_forms)

    def get_images_by_type(self, class_expression, template, image_folder,
                           image_type='swc', query_by_label=True, direct=False, stomp=False):
        """Retrieve images of instances of `class_expression` registered to `template` and save to disk,
        along with manifest and references, to `image_folder`. Default image type = swc. Also supported: obj, nrrd, rds, wlz.
        Returns manifest dataframe. If `stomp` is true, overwrites existing template_folder."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        instances = self.oc.get_instances(class_expression,
                                          query_by_label=query_by_label,
                                          direct=direct)
        return self.neo_query_wrapper.get_images([gen_short_form(i) for i in instances],
                                                 template=template,
                                                 image_folder=image_folder,
                                                 image_type=image_type,
                                                 stomp=stomp)








