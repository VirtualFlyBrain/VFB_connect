import warnings

import requests
from jsonpath_rw import parse as parse_jpath

from .owl.owlery_query_tools import OWLeryConnect
from .neo.neo4j_tools import Neo4jConnect, QueryWrapper, re, dict_cursor
from .default_servers import get_default_servers
import pandas as pd
import os


def gen_short_form(iri):
    """Generate short_form (string) from an iri string
    iri: An iri string"""
    return re.split('/|#', iri)[-1]

def _populate_instance_summary_tab(instance):
    d = dict()
    d['filename'] = ''
    d['label'] = instance['term']['core']['label']
    d['url'] = instance['term']['core']['iri']
    d['id'] = instance['term']['core']['short_form']
    d['type'] = instance['term']['core']['types']
    parents_expr = parse_jpath("$.parents[*].symbol,label,short_form")
    license_expr = parse_jpath("$.dataset_license.[*].license.link")
    dataset_expr = parse_jpath("$.dataset_license.[*].dataset.core.iri")
    d['classification'] = [match.value for match in parents_expr.find(instance)]
    d['license'] = [match.value for match in license_expr.find(instance)]
    d['dataset'] = [match.value for match in dataset_expr.find(instance)]
    return d

def _populate_manifest(filename, instance):
    d = _populate_instance_summary_tab(instance)
    d['filename'] = filename
    return d


class VfbConnect:
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

    def get_terms_by_region(self, region, cells_only=False, verbose=False, query_by_label=True):
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
        return self.neo_query_wrapper.get_type_TermInfo(list(map(gen_short_form, terms)))

    def get_subclasses(self, class_expression, query_by_label=True, direct=False):
        """Generate JSON report of all subclasses of class_expression."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_subclasses("%s" % class_expression, query_by_label=query_by_label)
        return self.neo_query_wrapper.get_type_TermInfo(list(map(gen_short_form, terms)))

    def get_superclasses(self, class_expression, query_by_label=True, direct=False):
        """Generate JSON report of all superclasses of class_expression."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_superclasses("%s" % class_expression, query_by_label=query_by_label)
        return self.neo_query_wrapper.get_type_TermInfo(list(map(gen_short_form, terms)))

    def get_instances(self, class_expression, query_by_label=True, direct=False):
        """Generate JSON report of all instances of class_expression. Instances are specific examples
        of a type/class of structure, e.g. a specific instance of the neuron DA1 adPN from the FAFB_catmaid
         database.  Instances are typically associated with registered 3D image data and may include
         connectomics data."""
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_instances("%s" % class_expression, query_by_label=query_by_label)
        return self.neo_query_wrapper.get_anatomical_individual_TermInfo(list(map(gen_short_form, terms)))

    def _get_neurons_connected_to(self, neuron, threshold, direction, classification=None, query_by_label=True):
        instances = []
        directions = ['upstream', 'downstream']
        if not (direction in directions):
            raise Exception(ValueError)  # Needs improving
        if classification:
            instances = self.oc.get_instances(classification, query_by_label=query_by_label)
        cypher_query = 'MATCH (upstream:Neuron)-[r:synapsed_to]->(downstream:Neuron) ' \
                       'WHERE r.weight[0] > %d ' % threshold
        if query_by_label:
            cypher_query += 'AND %s.label = "%s" ' % (direction, neuron)
        else:
            cypher_query += 'AND %s.short_form = "%s" ' % (direction, neuron)
        if classification and instances:
            directions.remove(direction)
            cypher_query += "AND %s.iri IN %s " % (directions[0], str(instances))
        cypher_query += "RETURN upstream.short_form as query_neuron_id, upstream.label as query_neuron_name, r.weight as weight, " \
                        "downstream.short_form as target_neuron_id, downstream.label as target_neuron_name"
        r = self.nc.commit_list([cypher_query])
        dc = dict_cursor(r)
        return pd.DataFrame.from_records(dc)

    def get_neurons_downstream_of(self, neuron, threshold, classification=None, query_by_label=True):
        return self._get_neurons_connected_to(neuron=neuron, threshold=threshold, direction='upstream',
                                              classification=classification, query_by_label=query_by_label)

    def get_neurons_upstream_of(self, neuron, threshold, classification=None, query_by_label=True):
        return self._get_neurons_connected_to(neuron=neuron, threshold=threshold, direction='downstream',
                                              classification=classification, query_by_label=query_by_label)

    def get_connected_neurons_by_type(self, upstream_type, downstream_type, weight, query_by_label=True):
        # Not doing the in-clause thing here in case of blow up
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

    def get_images(self, short_forms, template, image_folder, image_type='swc'):
        """Given an array of `short_forms` for instances, find all images of specified `image_type`
        registered to `template`. Save these to `image_folder` along with a manifest.tsv.  Return manifest as
        pandas DataFrame."""
        # TODO - make image type into array
        image_expr = parse_jpath("$.channel_image.[*].image")
        manifest = []
        os.mkdir(image_folder)
        inds = self.neo_query_wrapper.get_anatomical_individual_TermInfo(short_forms=short_forms)
        for i in inds:
            if not ('has_image' in i['term']['core']['types']):
                continue
            label = i['term']['core']['label']
            image_matches = image_expr.find(i)
            if not ([match.value for match in image_matches]):
                continue
            for im in image_matches:
                imv = im.value
                if imv['template_anatomy']['label'] == template:
                    r = requests.get(imv['image_folder'] + '/volume.' + image_type)
                    ### Slightly dodgy warning - could mask network errors
                    if not r.ok:
                        warnings.warn("No '%s' file found for '%s'." % (image_type, label))
                        continue
                    filename = re.sub('\W', '_', label) + '.' + image_type
                    with open(image_folder + '/' + filename, 'w') as image_file:
                        image_file.write(r.text)
                    manifest.append(_populate_manifest(instance=i, filename=filename))
        manifest_df = pd.DataFrame.from_records(manifest)
        manifest_df.to_csv(image_folder + '/manifest.tsv', sep='\t')
        return manifest_df

    def get_images_by_type(self, class_expression, template, image_folder,
                           image_type='swc', query_by_label=True, direct=False):
        """Retrieve images of instances of `class_expression` registered to `template` and save to disk,
        along with manifest and references, to `image_folder`. Default image type = swc. Also supported: obj, nrrd, rds, wlz.
        Returns manifest"""
        instances = self.oc.get_instances(class_expression,
                                          query_by_label=query_by_label,
                                          direct=direct)
        return self.get_images([gen_short_form(i) for i in instances],
                               template=template,
                               image_folder=image_folder,
                               image_type=image_type)








