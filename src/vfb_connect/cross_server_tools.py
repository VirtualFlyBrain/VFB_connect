import json
import os
import warnings
from string import Template
from typing import List
from xml.sax import saxutils

import pkg_resources
from .owl.owlery_query_tools import OWLeryConnect
from .neo.neo4j_tools import Neo4jConnect, re, dict_cursor
from .neo.query_wrapper import QueryWrapper, batch_query
from .default_servers import get_default_servers
from .schema.vfb_term import VFBTerm, VFBTerms, Partner
import pandas as pd
import numpy as np
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color
from scipy.spatial import KDTree


def gen_short_form(iri):
    """Generate short_form (string) from an IRI string.

    :param iri: A full IRI (Internationalized Resource Identifier) string.
    :return: The short form of the IRI (typically the last part after '/' or '#').
    :rtype: str
    """
    return re.split('/|#', iri)[-1]


def dequote(string):
    """Remove single quotes from around a string.

    :param string: A string that may have single quotes around it.
    :return: The string without surrounding single quotes.
    :rtype: str
    """
    qm = re.match("^'(.+)'$", string)
    if qm:
        return qm.group(1)
    else:
        return string

NT_NTR_pairs = {'Cholinergic': 'Acetylcholine_receptor', 'Dopaminergic': 'Dopamine_receptor',  
    'GABAergic': 'GABA_receptor', 'Glutamatergic': 'Glutamate_receptor', 'GABAergic': 'GABA_receptor',
    'Histaminergic': 'Histamine_receptor', 'Octopaminergic': 'Octopamine_receptor',
    'Serotonergic': 'Serotonin_receptor', 'Tyraminergic': 'Tyramine_receptor'}

class VfbConnect:
    """API wrapper class for Virtual Fly Brain (VFB) connectivity. 

    This class wraps connections to the basal API endpoints (OWL, Neo4j) and provides higher-level methods to
    combine semantic queries that range across VFB content with Neo4j queries. It returns detailed metadata about
    anatomical classes and individuals that fulfill these queries.

    :param neo_endpoint: Specify a Neo4j REST endpoint.
    :param neo_credentials: Specify credentials for the Neo4j REST endpoint.
    :param owlery_endpoint: Specify OWLery server REST endpoint.
    :param lookup_prefixes: A list of ID prefixes to use for rolling name:ID lookups.

    :var nc: Provides direct access to Neo4j via the Neo4jConnect instance.
    :var neo_query_wrapper: Provides enriched query capabilities using the QueryWrapper instance.
    :var oc: Provides direct access to OWL queries via the OWLeryConnect instance.
    :var lookup: A lookup table for resolving names to IDs.
    :var vfb_base: Base URL for Virtual Fly Brain links.
    """

    def __init__(self, neo_endpoint=get_default_servers()['neo_endpoint'],
                 neo_credentials=get_default_servers()['neo_credentials'],
                 owlery_endpoint=get_default_servers()['owlery_endpoint'],
                 solr_endpoint=get_default_servers()['solr_endpoint'],
                 vfb_launch=False):
        """
        VFB connect constructor. All args optional.
        With no args wraps connections to default public servers.

        :neo_endpoint: Specify a neo4j REST endpoint.
        :neo_credentials: Specify credential for Neo4j Rest endpoint.
        :owlery_endpoint: specify owlery server REST endpoint.
        :lookup_prefixes: A list of id prefixes to use for rolling name:ID lookups."""
        # Print the connection message
        print("Welcome to the \033[36mVirtual Fly Brain\033[0m API")
        print("See the documentation at: https://virtualflybrain.org/docs/tutorials/apis/")
        print("")
        print("\033[32mEstablishing connections to https://VirtualFlyBrain.org services...\033[0m")

        connections = {
            'neo': {
                "endpoint": neo_endpoint,
                "usr": neo_credentials[0],
                "pwd": neo_credentials[1]
            }
        }
        self.solr_url = solr_endpoint
        self.nc = Neo4jConnect(**connections['neo'])
        self.neo_query_wrapper = QueryWrapper(**connections['neo'])
        self.cache_file = self.get_cache_file_path()
        self._dbs_cache = {}
        self.lookup = self.nc.get_lookup(cache=self.cache_file)
        self.normalized_lookup = self.preprocess_lookup()
        self.reverse_lookup = {v: k for k, v in self.lookup.items()}
        self.oc = OWLeryConnect(endpoint=owlery_endpoint,
                                lookup=self.lookup)
        self.vfb_base = "https://v2.virtualflybrain.org/org.geppetto.frontend/geppetto?id="

        multi_query_json = pkg_resources.resource_filename(
                            "vfb_connect",
                            "resources/VFB_results_multi_input.json")
        with open(multi_query_json, 'r') as f:
            self.queries = json.loads(saxutils.unescape(f.read()))

        self._term_cache = []
        self._use_cache = False
        self._load_limit = False
        self._dbs = None
        self._gene_function_filters = None
        self._return_type = 'full' # the default for property returns: full (VFBterms), name or id (lists)

        print("\033[32mSession Established!\033[0m")
        print("")
        print("\033[33mType \033[35mvfb. \033[33mand press \033[35mtab\033[33m to see available queries. You can run help against any query e.g. \033[35mhelp(vfb.terms)\033[0m")

    def __dir__(self):
        return [attr for attr in list(self.__dict__.keys()) if not attr.startswith('_')] + [attr for attr in dir(self.__class__) if not attr.startswith('_') and not attr.startswith('add_')]

    def setNeoEndpoint(self, endpoint, usr, pwd):
        """Set the Neo4j endpoint and credentials."""
        self.nc = Neo4jConnect(endpoint=endpoint, usr=usr, pwd=pwd)
        self.neo_query_wrapper = QueryWrapper(endpoint=endpoint, usr=usr, pwd=pwd)
        self.reload_lookup_cache()

    def setOwleryEndpoint(self, endpoint):
        """Set the OWLery endpoint."""
        self.oc = OWLeryConnect(endpoint=endpoint, lookup=self.lookup)

    def get_cache_file_path(self):
        """Determine a safe place to save the pickle file in the same directory as the module."""
        # Get the directory where this script/module is located
        module_dir = os.path.dirname(__file__)
        # Define the cache file name
        cache_file = os.path.join(module_dir, 'lookup_cache.pkl')
        return cache_file
    
    def reload_lookup_cache(self, verbose=False):
        """Clear the lookup cache file."""
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
            print("Cache file removed.")
        else:
            print("No cache file found.")
        self.lookup = self.nc.get_lookup(cache=self.cache_file, verbose=verbose)

    def lookup_name(self, ids):
        """
        Lookup the name for a given ID using the internal lookup table.

        :param ids: A single ID or list of IDs to look up.
        :return: The name associated with the ID or a list of names if input is a list.
        :rtype: str or list of str
        """
        if isinstance(ids, list):
            return [self.lookup_name(id) for id in ids]

        if ids not in self.reverse_lookup:
            return ids  # If not found, return the input

        return self.reverse_lookup[ids]

    def preprocess_lookup(self):
        """Preprocesses the lookup table to create a normalized lookup for faster access."""
        normalized_lookup = {}
        for k, v in self.lookup.items():
            norm_key = self.normalize_key(k)
            if norm_key not in normalized_lookup:
                normalized_lookup[norm_key] = v
        return normalized_lookup

    def normalize_key(self, key):
        """
        Normalize the key for comparison by making it lowercase and removing special characters.
        
        :param key: The key to normalize.
        :return: A normalized string.
        """
        return key.lower().replace('_', '').replace('-', '').replace(' ', '').replace(':', '').replace(';', '')


    def lookup_id(self, key, return_curie=False, allow_substitutions=True, substitution_stages=['adult', 'larval', 'pupal'], verbose=False):
        """Lookup the ID for a given key (label or symbol) using the internal lookup table.

        :param key: The label symbol, synonym, or potential ID to look up.
        :param allow_subsitutions: Optional. If `True`, allow for case-insensitive and character-insensitive lookups. Default `True`.
        :param subsitution_stages: Optional. A list of prefixes to try for substitutions. Default ['adult', 'larval', 'pupal'].
        :param return_curie: Optional. If `True`, return the ID in CURIE (Compact URI) format. Default `False`.
        :return: The ID associated with the key, or the key itself if it is already a valid ID. None is returned if the key is not found.
        :rtype: str
        """
        if not key:
            print("\033[31mError:\033[0m No key provided.")
            return ''

        if isinstance(key, VFBTerm):
            return key.id

        if isinstance(key, VFBTerms):
            return key.get_ids()

        if isinstance(key, list):
            return [self.lookup_id(k, return_curie=return_curie, allow_substitutions=allow_substitutions, substitution_stages=substitution_stages) for k in key]

        if isinstance(key, str):
            dbs = self.get_dbs()
            if ":" in key and any(key.startswith(db) for db in dbs):
                split_key = key.rsplit(':', 1)
                if verbose:
                    print(f"Split xref: {split_key}")
                if len(split_key) == 2:
                    id = self.xref_2_vfb_id(acc=split_key[1], db=split_key[0], return_just_ids=True)
                    if id and len(id) == 1:
                        return id[0]

        if key in self.lookup.values():
            return key if not return_curie else key.replace('_', ':')

        prefixes = ('CARO_', 'BFO_', 'UBERON_', 'GENO_', 'CL_', 'FB', 'VFB_', 'GO_', 'SO_', 'RO_', 'PATO_', 'CHEBI_', 'PR_', 'NCBITaxon_', 'ENVO_', 'OBI_', 'IAO_', 'OBI_')
        if key.startswith(prefixes) and key not in self.lookup.keys():
            return key if not return_curie else key.replace('_', ':')

        if key in self.lookup:
            out = self.lookup[key]
            return out if not return_curie else out.replace('_', ':')

        if allow_substitutions:
            normalized_key = self.normalize_key(key)
            if verbose:
                print(f"Normalized key: {normalized_key}")

            matches = {k: v for k, v in self.lookup.items() if self.normalize_key(k) == normalized_key}

            if isinstance(substitution_stages, str):
                substitution_stages = [substitution_stages]

            if not matches:
                for stage in substitution_stages:
                    stage_normalized_key = self.normalize_key(stage + key)
                    matches = {k: v for k, v in self.lookup.items() if self.normalize_key(k) == stage_normalized_key}
                    if matches:
                        break

            if matches:
                matched_key = min(matches.keys(), key=len)
                if verbose:
                    for k, v in matches.items():
                        print(f"Matched: {k} -> {v}")

                if len(matches) == 1:
                    print(f"\033[33mWarning:\033[0m Substitution made. '\033[33m{key}\033[0m' was matched to '\033[32m{matched_key}\033[0m'.")
                    return matches[matched_key] if not return_curie else matches[matched_key].replace('_', ':')

                all_matches = ", ".join([f"'{k}': '{v}'" for k, v in matches.items()])
                print(f"\033[33mWarning:\033[0m Ambiguous match for '\033[33m{key}\033[0m'. Using '{matched_key}' -> '\033[32m{matches[matched_key]}\033[0m'. Other possible matches: {all_matches}")
                return matches[matched_key] if not return_curie else matches[matched_key].replace('_', ':')

            starts_with_matches = {k: v for k, v in self.lookup.items() if k.lower().startswith(key.lower())}
            if starts_with_matches:
                all_matches = ", ".join([f"'\033[36m{k}\033[0m': '{v}'" for k, v in starts_with_matches.items()])
                print(f"Notice: No exact match found, but potential matches starting with '\033[31m{key}\033[0m': {all_matches}")
                return ''

            contains_matches = {k: v for k, v in self.lookup.items() if key.lower() in k.lower()}
            if contains_matches:
                all_matches = ", ".join([f"'\033[36m{k}\033[0m': '{v}'" for k, v in contains_matches.items()])
                print(f"Notice: No exact match found, but potential matches containing '\033[31m{key}\033[0m': {all_matches}")
                return ''

        print(f"\033[31mError:\033[0m Unrecognized value: \033[31m{key}\033[0m")
        return ''

    @property
    def __version__(self):
        from importlib.metadata import version, PackageNotFoundError
        return version('vfb_connect')
        try:
            return version('vfb_connect')
        except PackageNotFoundError:
            return '0.0.0'
        return '0.0.0'

    def get_terms_by_region(self, region, cells_only=False, verbose=False, query_by_label=True, summary=True, return_dataframe=True):
        """Generate TermInfo reports for all terms relevant to annotating a specific region, optionally limited to cells.

        :param region: The name (rdfs:label) of the brain region (or CURIE style ID if query_by_label is False).
        :param cells_only: Optional. Limits query to cell types if `True`. Default `False`.
        :param verbose: Optional. If `True`, prints the running query and found terms. Default `False`.
        :param query_by_label: Optional. Query using region labels if `True`, or IDs if `False`. Default `True`.
        :param summary: Optional. Returns summary reports if `True`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns a list of dicts. Default `True`.
        :return: A DataFrame or list of terms as nested Python data structures following VFB_json or summary_report_json.
        :rtype: pandas.DataFrame or list of dicts
        """
        preq = ''
        if cells_only:
            preq = "'cell' that "
        owl_query = preq + "'overlaps' some '%s'" % region
        if verbose:
            print("Running query: %s" % owl_query)

        terms = self.oc.get_subclasses(owl_query, query_by_label=query_by_label, verbose=verbose)
        if verbose:
            print("Found: %d terms" % len(terms))
        results = self.get_TermInfo(terms, summary=summary, return_dataframe=False)
        if return_dataframe and summary:
            return pd.DataFrame.from_records(results)
        return results

    def get_subclasses(self, class_expression, query_by_label=True, direct=False, summary=True, return_dataframe=True, verbose=False):
        """Generate JSON report of all subclasses of a given class expression.

        :param class_expression: A valid OWL class expression, e.g., the name of a class.
        :param query_by_label: Optional. Query using class labels if `True`, or IDs if `False`. Default `True`.
        :param direct: Optional. Return only direct subclasses if `True`. Default `False`.
        :param summary: Optional. Returns summary reports if `True`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns a list of dicts. Default `True`.
        :return: A DataFrame or list of terms as nested Python data structures following VFB_json or summary_report_json.
        :rtype: pandas.DataFrame or list of dicts
        """
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_subclasses("%s" % class_expression, direct=direct, query_by_label=query_by_label, verbose=verbose)
        results = self.get_TermInfo(terms, summary=summary, return_dataframe=False)
        if return_dataframe and summary:
            return pd.DataFrame.from_records(results)
        return results

    def get_superclasses(self, class_expression, query_by_label=True, direct=False, summary=True, return_dataframe=True):
        """Generate JSON report of all superclasses of a given class expression.

        :param class_expression: A valid OWL class expression, e.g., the name of a class.
        :param query_by_label: Optional. Query using class labels if `True`, or IDs if `False`. Default `True`.
        :param direct: Optional. Return only direct superclasses if `True`. Default `False`.
        :param summary: Optional. Returns summary reports if `True`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns a list of dicts. Default `True`.
        :return: A DataFrame or list of terms as nested Python data structures following VFB_json or summary_report_json.
        :rtype: pandas.DataFrame or list of dicts
        """
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        terms = self.oc.get_superclasses("%s" % class_expression, query_by_label=query_by_label, direct=direct)
        results = self.get_TermInfo(terms, summary=summary, return_dataframe=False)
        if return_dataframe and summary:
            return pd.DataFrame.from_records(results)
        return results

    def get_instances(self, class_expression, query_by_label=True, summary=True, return_dataframe=True, limit=None, return_id_only=False, verbose=False):
        """Generate JSON report of all instances of a given class expression.

        Instances are specific examples of a type/class, e.g., a neuron of type DA1 adPN from the FAFB_catmaid database.

        :param class_expression: A valid OWL class expression, e.g., the name of a class.
        :param query_by_label: Optional. Query using class labels if `True`, or IDs if `False`. Default `True`.
        :param summary: Optional. Returns summary reports if `True`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns a list of dicts. Default `True`.
        :return: A DataFrame or list of terms as nested Python data structures following VFB_json or summary_report_json.
        :rtype: pandas.DataFrame or list of dicts
        """
        if not re.search("'", class_expression):
            if query_by_label:
                class_expression = self.lookup[class_expression]
            out = self.neo_query_wrapper._get_anatomical_individual_TermInfo_by_type(class_expression,
                                                                                     summary=summary, return_dataframe=False, limit=limit, verbose=verbose)
        else:
            terms = self.oc.get_instances("%s" % class_expression, query_by_label=query_by_label, verbose=verbose)
            if return_id_only:
                return terms
            if limit:
                print(f"Limiting to {limit} terms out of {len(terms)}")
                terms = terms[:limit]
            out = self.get_TermInfo(terms, summary=summary, return_dataframe=False, limit=limit, verbose=verbose)
        if return_dataframe and summary:
            return pd.DataFrame.from_records(out)
        return out

    def _get_neurons_connected_to(self, neuron, weight, direction, classification=None, query_by_label=True,
                                  return_dataframe=True, verbose=False):
        """Private method to get all neurons connected to a specified neuron.

        :param neuron: The name or ID of a particular neuron (dependent on query_by_label setting).
        :param weight: The minimum weight of synaptic connections to include.
        :param direction: The direction of the connection, either 'upstream' or 'downstream'.
        :param classification: Optional. Restrict connections to neurons of a specified classification.
        :param query_by_label: Optional. Query using neuron labels if `True`, or IDs if `False`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame or list of neurons connected to the specified neuron.
        :rtype: pandas.DataFrame or list of dicts
        """
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
            cypher_query += "AND %s.short_form IN %s " % (directions[0], str(instances))
        cypher_query += "RETURN upstream.short_form as query_neuron_id, upstream.label as query_neuron_name, " \
                        "r.weight[0] as weight, " \
                        "downstream.short_form as target_neuron_id, downstream.label as target_neuron_name " \
                        "ORDER BY weight DESC"
        print(cypher_query) if verbose else None
        r = self.nc.commit_list([cypher_query])
        dc = dict_cursor(r)
        print(dc) if verbose else None
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        else:
            return dc

    def get_similar_neurons(self, neuron, similarity_score='NBLAST_score', query_by_label=True, return_dataframe=True, verbose=False):
        """Get JSON report of individual neurons similar to the input neuron.

        :param neuron: The neuron to find similar neurons to.
        :param similarity_score: Optional. Specify the similarity score to use (e.g., 'NBLAST_score'). Default 'NBLAST_score'.
        :param query_by_label: Optional. Query neuron by label if `True`, or by ID if `False`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame or list of similar neurons (id, label, tags, source (db) id, accession_in_source) + similarity score.
        :rtype: pandas.DataFrame or list of dicts
        """
        id = neuron if query_by_label else self.lookup_id(neuron)
        query = "MATCH (c1:Class)<-[:INSTANCEOF]-(n1:Individual)-[r:has_similar_morphology_to]-(n2:Individual)-[:INSTANCEOF]->(c2:Class) " \
                "WHERE n1.short_form = '%s'  and exists(r.%s) " \
                "WITH c1, n1, r, n2, c2 " \
                "OPTIONAL MATCH (n1)-[dbx1:database_cross_reference]->(s1:Site), " \
                "(n2)-[dbx2:database_cross_reference]->(s2:Site) " \
                "WHERE s1.is_data_source and s2.is_data_source " \
                "RETURN DISTINCT n2.short_form AS id, r.%s[0] AS score, n2.label AS label, " \
                "COLLECT(c2.label) AS tags, s2.short_form AS source_id, dbx2.accession[0] AS accession_in_source " \
                "ORDER BY score DESC" % (id, similarity_score, similarity_score)
        print(query) if verbose else None
        dc = self.neo_query_wrapper._query(query)
        print(dc) if verbose else None
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        else:
            return dc
        
    def get_potential_drivers(self, neuron, similarity_score='NBLAST_score', query_by_label=True, return_dataframe=True, verbose=False):
        """Get JSON report of driver expression likely to contain the input neuron.

        :param neuron: The neuron to find similar drivers for.
        :param similarity_score: Optional. Specify the similarity score to use (e.g., 'NBLAST_score', 'neuronbridge_score'). Default 'NBLAST_score'.
        :param query_by_label: Optional. Query neuron by label if `True`, or by ID if `False`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame or list of potranial drivers (id, label, tags) + similarity score.
        :rtype: pandas.DataFrame or list of dicts
        """
        id = neuron if query_by_label else self.lookup_id(neuron)
        query = "MATCH (c1:Class)<-[:INSTANCEOF]-(n1:Individual)-[r:has_similar_morphology_to_part_of]-(n2:Individual)-[:INSTANCEOF]->(c2:Class) " \
                "WHERE n1.short_form = '%s'  and exists(r.%s) " \
                "WITH c1, n1, r, n2, c2 " \
                "RETURN DISTINCT n2.short_form AS id, r.%s[0] AS score, n2.label AS label, " \
                "COLLECT(c2.label) AS tags " \
                "ORDER BY score DESC" % (id, similarity_score, similarity_score)
        print(query) if verbose else None
        dc = self.neo_query_wrapper._query(query)
        print(dc) if verbose else None
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        else:
            return dc

    def get_neurons_downstream_of(self, neuron, weight, classification=None, query_by_label=True,
                                  return_dataframe=True,verbose=False):
        """Get all neurons downstream of a specified neuron.

        :param neuron: The name or ID of a particular neuron (dependent on query_by_label setting).
        :param weight: Limit returned neurons to those connected by >= weight synapses.
        :param classification: Optional. Restrict downstream neurons by classification.
        :param query_by_label: Optional. Query neuron by label if `True`, or by ID if `False`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame or list of neurons downstream of the specified neuron.
        :rtype: pandas.DataFrame or list of dicts
        """
        return self._get_neurons_connected_to(neuron=neuron, weight=weight, direction='upstream',
                                              classification=classification, query_by_label=query_by_label,
                                              return_dataframe=return_dataframe, verbose=verbose)

    def get_neurons_upstream_of(self, neuron, weight, classification=None, query_by_label=True, return_dataframe=True, verbose=False):
        """Get all neurons upstream of a specified neuron.

        :param neuron: The name or ID of a particular neuron (dependent on query_by_label setting).
        :param weight: Limit returned neurons to those connected by >= weight synapses.
        :param classification: Optional. Restrict upstream neurons by classification.
        :param query_by_label: Optional. Query neuron by label if `True`, or by ID if `False`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame or list of neurons upstream of the specified neuron.
        :rtype: pandas.DataFrame or list of dicts
        """
        return self._get_neurons_connected_to(neuron=neuron, weight=weight, direction='downstream',
                                              classification=classification, query_by_label=query_by_label,
                                              return_dataframe=return_dataframe, verbose=verbose)

    def get_connected_neurons_by_type(self, weight, upstream_type=None, downstream_type=None, query_by_label=True,
                                      return_dataframe=True, verbose=False):

        """Get all synaptic connections between individual neurons of `upstream_type` and `downstream_type` where
             synapse count >= `weight`.  At least one of 'upstream_type' or downstream_type must be specified.

             :param upstream_type: The upstream neuron type (e.g., 'GABAergic neuron').
             :param downstream_type: The downstream neuron type (e.g., 'Descending neuron').
             :param query_by_label: Optional. Specify neuron type by label if `True` (default) or by short_form ID if `False`.
             :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
             :return: A DataFrame or list of synaptic connections between specified neuron types.
             :rtype: pandas.DataFrame or list of dicts
             """
        # TODO - chose not to do this with class expressions to avoid poor performance and blowing up results.
        # This might be confusing tough, given behavior of other, similar methods.
        # Might be better to refactor to work out if query is class expression or class & funnel query method
        # accordingly.

        if (upstream_type is None) and (downstream_type is None):
            print("At least one of upstream_type or downstream_type must be specified")
            return 1
        if query_by_label:
            if upstream_type: upstream_type = self.lookup_id(dequote(upstream_type))
            if downstream_type: downstream_type = self.lookup_id(dequote(downstream_type))
        cypher_ql = []
        if upstream_type:
            cypher_ql.append(
                "MATCH (up:Class)<-[:SUBCLASSOF*0..]-(c1:Class)<-[:INSTANCEOF]-(n1:has_neuron_connectivity)"
                " WHERE up.short_form = '%s' " % upstream_type)
        if downstream_type:
            cypher_ql.append(
                "MATCH (down:Class)<-[:SUBCLASSOF*0..]-(c2:Class)<-[:INSTANCEOF]-(n2:has_neuron_connectivity)"
                "WHERE down.short_form = '%s' " % downstream_type)
        if not upstream_type:
            cypher_ql.append(
                "MATCH (c1:Class)<-[:INSTANCEOF]-(n1)-[r:synapsed_to]->(n2) WHERE r.weight[0] >= %d " % weight)
        elif not downstream_type:
            cypher_ql.append(
                "MATCH (n1)-[r:synapsed_to]->(n2)-[:INSTANCEOF]->(c2:Class) WHERE r.weight[0] >= %d " % weight)
        else:
            cypher_ql.append("MATCH (n1)-[r:synapsed_to]->(n2) WHERE r.weight[0] >= %d " % weight)
        cypher_ql.append("OPTIONAL MATCH (n1)-[r1:database_cross_reference]->(s1:Site) "
                        "WHERE exists(s1.is_data_source) AND s1.is_data_source = [True] ")
        cypher_ql.append("OPTIONAL MATCH (n2)-[r2:database_cross_reference]->(s2:Site) " 
                        "WHERE exists(s2.is_data_source) AND s2.is_data_source = [True] " )
        cypher_ql.append("RETURN apoc.text.join(collect(distinct c1.label),'|') AS upstream_class, "
                         "apoc.text.join(collect(distinct c1.short_form),'|') AS upstream_class_id, "
                         "n1.short_form as upstream_neuron_id, n1.label as upstream_neuron_name,"
                         "r.weight[0] as weight, n2.short_form as downstream_neuron_id, "
                         "n2.label as downstream_neuron_name, "
                         "apoc.text.join(collect(distinct c2.label),'|') as downstream_class, "
                         "apoc.text.join(collect(distinct c2.short_form),'|') as downstream_class_id, "
                         "s1.short_form AS up_data_source, r1.accession[0] as up_accession, "
                         "s2.short_form AS down_source, r2.accession[0] AS down_accession")
        cypher_q = ' \n'.join(cypher_ql)
        print(cypher_q) if verbose else None
        r = self.nc.commit_list([cypher_q])
        if not r:
            warnings.warn("No results returned")
            return False
        dc = dict_cursor(r)
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        else:
            return dc

    def get_instances_by_dataset(self, dataset, query_by_label=True, summary=True, return_dataframe=True, return_id_only=False):
        """Get JSON report of all individuals in a specified dataset.

        :param dataset: The dataset ID.
        :param summary: Optional. Returns summary reports if `True`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns a list of dicts. Default `True`.
        :return: A DataFrame or list of terms as nested Python data structures following VFB_json or summary_report_json.
        :rtype: pandas.DataFrame or list of dicts
        """
        if query_by_label:
            dataset = self.lookup_id(dataset)
        if dataset:
            query = "MATCH (ds:DataSet)<-[:has_source]-(i:Individual) " \
                    "WHERE ds.short_form = '%s' " \
                    "RETURN collect(distinct i.short_form) as inds" % dataset
            dc = self.neo_query_wrapper._query(query) # TODO - Would better to use the original column oriented return!
            if return_id_only:
                return dc[0]['inds']
            return self.get_TermInfo(dc[0]['inds'], summary=summary, return_dataframe=return_dataframe)

    def get_vfb_link(self, short_forms: iter, template):
        """Generate a link to Virtual Fly Brain (VFB) that loads all available images of neurons on the specified template.

        :param short_forms: A list (or other iterable) of VFB short_form IDs for individuals with images.
        :param template: The name (label) of a template.
        :return: A URL for viewing images and metadata for specified individuals on VFB.
        :rtype: str
        :raises ValueError: If the template name is not recognized.
        """
        short_forms = list(short_forms)
        query = "MATCH (t:Template { label: '%s'}) return t.short_form" % template
        dc = self.neo_query_wrapper._query(query)
        if not dc:
            raise ValueError("Unrecognised template name %s" % template)
        else:
            results = self.vfb_base + short_forms.pop() + "&i=" + dc[0]['t.short_form'] + ',' + ','.join(short_forms)
            return results

    def get_images_by_type(self, class_expression, template, image_folder,
                           image_type='swc', query_by_label=True, direct=False, stomp=False):
        """Download all images of individuals specified by a class expression.

        :param class_expression: A valid OWL class expression, e.g., the name or symbol of a type of neuron (MBON01).
        :param template: The template name.
        :param image_folder: The folder to save image files and manifest to.
        :param image_type: The image file extension (e.g., 'swc').
        :param query_by_label: Optional. Query using class labels if `True`, or IDs if `False`. Default `True`.
        :param direct: Optional. Return only direct instances if `True`. Default `False`.
        :param stomp: Optional. Overwrite the image folder if it already exists. Default `False`.
        :return: A manifest of downloaded images as a pandas DataFrame.
        :rtype: pandas.DataFrame
        """
        if not re.search("'", class_expression):
            class_expression = "'" + class_expression + "'"
        instances = self.oc.get_instances(class_expression,
                                          query_by_label=query_by_label,
                                          direct=direct)
        return self.neo_query_wrapper.get_images(instances,
                                                 template=template,
                                                 image_folder=image_folder,
                                                 image_type=image_type,
                                                 stomp=stomp)

    def get_gene_function_filters(self):
        """Get a list of all gene function labels.

        :return: List of unique gene function labels in alphabetical order.
        :rtype: list
        """
        if not self._gene_function_filters:
            query = ("MATCH (g:Gene) RETURN DISTINCT apoc.coll.subtract(labels(g), "
                 "['Class', 'Entity', 'hasScRNAseq', 'Feature', 'Gene']) AS gene_labels")
            result = self.neo_query_wrapper._query(query)
            labels = []
            for r in result:
                labels.extend(r['gene_labels'])
            labels = sorted(list(set(labels)))
            self._gene_function_filters = labels
        return self._gene_function_filters

    def get_transcriptomic_profile(self, cell_type, gene_type=False, no_subtypes=False, query_by_label=True, return_dataframe=True):
        """Get gene expression data for a given cell type.

        Returns a DataFrame of gene expression data for clusters of cells annotated as the specified cell type (or subtypes).
        Optionally restricts to a gene type, which can be retrieved using `get_gene_function_filters`.
        If no data is found, returns False.

        :param cell_type: The ID, name, or symbol of a class in the Drosophila Anatomy Ontology (FBbt).
        :param gene_type: Optional. A gene function label retrieved using `get_gene_function_filters`.
        :param no_subtypes: Optional. If `True`, only clusters for the specified cell_type will be returned and not subtypes. Default `False`.
        :param query_by_label: Optional. Query using cell type labels if `True`, or IDs if `False`. Default `True`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame with gene expression data for clusters of cells annotated as the specified cell type.
        :rtype: pandas.DataFrame or list of dicts
        :raises KeyError: If the cell_type or gene_type is invalid.
        """
        if query_by_label:
            cell_type_short_form = self.lookup_id(cell_type)
        else:
            if cell_type in self.lookup.values():
                cell_type_short_form = cell_type
            else:
                raise KeyError("cell_type must be a valid ID from the Drosophila Anatomy Ontology")

        if not cell_type_short_form.startswith('FBbt'):
            raise KeyError("cell_type must be a valid ID, label or symbol from the Drosophila Anatomy Ontology")

        if gene_type:
            if gene_type not in self.get_gene_function_filters():
                raise KeyError("gene_type must be a valid gene function label, try running get_gene_function_filters()")
            else:
                gene_label = ':' + gene_type
        else:
            gene_label = ''

        if no_subtypes:
            equal_condition = 'AND c1.short_form = c2.short_form '
        else:
            equal_condition = ''

        query = ("MATCH (g:Gene:Class%s)<-[e:expresses]-(clus:Cluster:Individual)-"
                 "[:composed_primarily_of]->(c2:Class)-[:SUBCLASSOF*0..]->(c1:Neuron:Class) "
                 "WHERE c1.short_form = '%s' %s"
                 "MATCH (clus)-[:part_of]->()-[:has_part]->(sa:Sample:Individual) "
                 "OPTIONAL MATCH (sa)-[:part_of]->(sex:Class) "
                 "WHERE sex.short_form IN ['FBbt_00007011', 'FBbt_00007004'] "
                 "OPTIONAL MATCH (sa)-[:overlaps]->(tis:Class:Anatomy) "
                 "OPTIONAL MATCH (clus)-[:has_source]->(ds:DataSet:Individual) "
                 "OPTIONAL MATCH (ds)-[:has_reference]->(p:pub:Individual) "
                 "OPTIONAL MATCH (ds)-[dbxw:database_cross_reference]->(sw:Site:Individual "
                 "{short_form:'scExpressionAtlas'}) "
                 "OPTIONAL MATCH (ds)-[dbxd:database_cross_reference]->(sd:Site:Individual "
                 "{short_form:'scExpressionAtlasFTP'}) WHERE dbxd.accession[0] = dbxw.accession[0] "
                 "RETURN DISTINCT c2.label AS cell_type, c2.short_form AS cell_type_id, "
                 "sex.label AS sample_sex, COLLECT(tis.label) AS sample_tissue, "
                 "ds.short_form AS dataset_id, p.miniref[0] as ref, "
                 "sw.link_base[0] + dbxw.accession[0] AS website_linkout, "
                 "sd.link_base[0] + dbxd.accession[0] + sd.postfix[0] AS download_linkout, "
                 "g.label AS gene, g.short_form AS gene_id, "
                 "apoc.coll.subtract(labels(g), ['Class', 'Entity', 'hasScRNAseq', 'Feature', 'Gene']) AS function, "
                 "e.expression_extent[0] as extent, toFloat(e.expression_level[0]) as level "
                 "ORDER BY cell_type, g.label" % (gene_label, cell_type_short_form, equal_condition))
        r = self.nc.commit_list([query])
        dc = dict_cursor(r)
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        else:
            return dc

    def get_neuron_pubs(self, neuron, include_subclasses=True, include_nlp=False,
                        query_by_label=True, verbose=False):

        """Get publications about a neuron type

        :param neuron: An name, symbol, or ID of a neuron type
        :param include_subclasses: Include references for subclasses (subtypes) of this neuron type, default: True
        :param include_nlp: Include experimental matches from natural language processing. Default = False
        :param query_by_label: query using the label, symbol or ID of a neuron.
        :param verbose: Return underlying cypher query for debugging
        """

        if query_by_label:
            neuron = self.lookup_id(dequote(neuron))
        if include_subclasses:
            cypher_q = "MATCH (n:Neuron)<-[:SUBCLASSOF*0..]-() "
        else:
            cypher_q = "MATCH (n:Neuron) "
        cypher_q += """WHERE n.short_form = '%s'
                      MATCH (n)-[r:has_reference]-(pub) 
                      WHERE pub.title is not null """ % neuron
        if not include_nlp:
            cypher_q += "AND NOT (r.typ = 'nlp') "
        cypher_q += """WITH collect ({ type: r.typ, miniref: pub.miniref[0], PMID: pub.PMID[0], DOI: pub.DOI[0], FlyBase: pub.FlyBase, title: pub.title[0]}) as pubs1, n 
                      MATCH (ep:Expression_pattern:Class)<-[ar:part_of]-(anoni:Individual)-[:INSTANCEOF]->(n)
                      MATCH (pub:pub { short_form: ar.pub[0]}) 
                      WITH pubs1, collect({ type: 'expression', miniref: pub.miniref[0], PMID: pub.PMID[0], DOI: pub.DOI[0], FlyBase: pub.FlyBase }) as pubs2 
                      RETURN pubs1 + pubs2  as all_pubs"""
        r = self.nc.commit_list([cypher_q])
        dc = dict_cursor(r)
        print(cypher_q) if verbose else None
        return pd.DataFrame.from_records(dc[0]['all_pubs'])

    #  Wrapped neo_query_wrapper methods
    def get_datasets(self, summary=True, return_dataframe=True):
        """Get all datasets in the database.

        :return: List of datasets in the database.
        :rtype: list
        """
        return self.neo_query_wrapper.get_datasets(summary=summary, return_dataframe=return_dataframe)
    
    @batch_query
    def get_images(self, short_forms: iter, template=None, image_folder=None, image_type='swc', stomp=False):
        """Get images for a list of individuals.

        :param short_forms: List of short_form IDs for individuals.
        :param template: Optional. Template name.
        :param image_folder: Optional. Folder to save image files & manifest to.
        :param image_type: Optional. Image type (file extension).
        :param stomp: Optional. Overwrite image_folder if already exists.
        :return: Manifest as Pandas DataFrame
        """
        return self.neo_query_wrapper.get_images(short_forms, template=template, image_folder=image_folder,
                                                 image_type=image_type, stomp=stomp)
    
    def get_templates(self, summary=True, return_dataframe=True, include_symbols=False):
        """Get all templates in the database.

        :return: List of templates in the database.
        :rtype: list
        """
        return self.neo_query_wrapper.get_templates(summary=summary, return_dataframe=return_dataframe, include_symbols=include_symbols)
    
    @batch_query
    def get_terms_by_xref(self, xrefs: iter, db='', summary=True, return_dataframe=True):
        """
        Retrieve terms by cross-reference (xref) identifiers.

        This method takes a list of external cross-reference identifiers and returns the corresponding terms from the database.
        The terms can be returned either as full metadata or as summaries. Additionally, the results can be returned as a pandas
        DataFrame if `return_dataframe` is set to `True`.

        :param xrefs: An iterable (e.g., a list) of cross-reference identifiers (xrefs).
        :param db: Optional. The name of the external database to filter the results by. Default is an empty string, which means no filtering.
        :param summary: Optional. If `True`, returns summary reports instead of full metadata. Default is `True`.
        :param return_dataframe: Optional. If `True` and `summary` is also `True`, returns the results as a pandas DataFrame. Default is `True`.
        :return: A list of term metadata as nested Python data structures (VFB_json or summary_report_json), or a pandas DataFrame if
                `return_dataframe` is `True` and `summary` is `True`.
        :rtype: list of dicts or pandas.DataFrame
        """
        return self.neo_query_wrapper.get_terms_by_xref(xrefs, db=db, summary=summary, return_dataframe=False)

    def xref_2_vfb_id(self, acc=None, db='', id_type='', reverse_return=False, return_just_ids=True, verbose=False):
        """Map a list external DB IDs to VFB IDs

        :param acc: An iterable (e.g. a list) of external IDs (e.g. neuprint bodyIDs). Can be in the form of 'db:acc' or just 'acc'.
        :param db: optional specify the VFB id (short_form) of an external DB to map to. (use get_dbs to find options)
        :param id_type: optionally specify an external id_type
        :param reverse_return: Boolean: Optional (see return)
        :param return_just_ids: Boolean: Optional (see return)
        :param verbose: Optional. If `True`, prints the running query and found terms. Default `False`.
        :return: if `reverse_return` is False:
            dict { acc : [{ db: <db> : vfb_id : <VFB_id> }
            Return if `reverse_return` is `True`:
            dict { VFB_id : [{ db: <db> : acc : <acc> }
            if `return_just_ids` is `True`:
            return just the VFB_ids in a list
        """
        if isinstance(acc, str):
            if ':' in acc and db == '':
                db, acc = acc.split(':')
            acc = [acc]
        elif isinstance(acc, list) and all(isinstance(x, str) for x in acc):
            new_acc = []
            for xref in acc:
                if ':' in xref:
                    if db == '':
                        db, temp_acc = xref.split(':')
                        new_acc.append(temp_acc)
                    else:
                        new_acc.append(xref.split(':')[-1])
            acc = new_acc
        result = self.neo_query_wrapper.xref_2_vfb_id(acc=acc, db=db, id_type=id_type, reverse_return=reverse_return, verbose=verbose)
        if return_just_ids & reverse_return:
            return [x.key for x in result]
        if return_just_ids and not reverse_return:
            id_list = []
            for id in acc:
                id_list.append(result[id][0]['vfb_id']) # This takes the first match only
                if len(result[id]) > 1:
                    print(f"Multiple matches found for {id}: {result[id]}")
                    print(f"Using {result[id][0]['vfb_id']}")
            return id_list
        return result

    @batch_query
    def get_images_by_filename(self, filenames: iter, dataset=None, summary=True, return_dataframe=True):
        """Get images by filename.

        :param filenames: List of filenames.
        :param dataset: Optional. Dataset name.
        :return: List of images.
        :rtype: list
        """
        return self.neo_query_wrapper.get_images_by_filename(filenames, dataset=dataset, summary=summary,
                                                             return_dataframe=False)
    
    @batch_query
    def get_TermInfo(self, short_forms: iter, summary=True, cache=True, return_dataframe=True, query_by_label=True, limit=None, verbose=False):
        """
        Generate a JSON report or summary for terms specified by a list of VFB IDs.

        This method retrieves term information for a list of specified VFB IDs (short_forms). It can return either 
        full metadata or a summary of the terms. The results can be returned as a pandas DataFrame if `return_dataframe` 
        is set to `True`.

        :param short_forms: An iterable (e.g., a list) of VFB IDs (short_forms).
        :param summary: Optional. If `True`, returns a summary report instead of full metadata. Default is `True`.
        :param cache: Optional. If `True`, attempts to retrieve cached results before querying. Default is `True`.
        :param return_dataframe: Optional. If `True`, returns the results as a pandas DataFrame. Default is `True`.
        :param query_by_label: Optional. If `True`, it allows labels, symbols or synonyms as well as short_forms. Default is `True`.
        :return: A list of term metadata as VFB_json or summary_report_json, or a pandas DataFrame if `return_dataframe` is `True`.
        :rtype: list of dicts or pandas.DataFrame
        """
        # Convert single string to list
        if isinstance(short_forms, str):
            short_forms = [short_forms]
        if isinstance(short_forms, VFBTerm):
            short_forms = [short_forms.id]
        if isinstance(short_forms, VFBTerms):
            short_forms = short_forms.get_ids()
        print(short_forms) if verbose else None
        # Convert labels to IDs if use_labels is True
        if query_by_label:
            short_forms = [self.lookup_id(sf) for sf in short_forms]
        print(short_forms) if verbose else None
        return self.neo_query_wrapper.get_TermInfo(short_forms, summary=summary, cache=cache, return_dataframe=False, limit=limit, verbose=verbose) 

    @batch_query
    def vfb_id_2_xrefs(self, vfb_id: iter, db='', id_type='', reverse_return=False):
        """Map a list of short_form IDs in VFB to external DB IDs

        :param vfb_id: An iterable (e.g. a list) of VFB short_form IDs.
        :param db: optional specify the VFB id (short_form) of an external DB to map to. (use get_dbs to find options)
        :param id_type: optionally specify an external id_type
        :param reverse_return: Boolean: Optional (see return)
        :return: if `reverse_return` is False:
                dict { VFB_id : [{ db: <db> : acc : <acc> }
            Return if `reverse_return` is `True`:
                dict { acc : [{ db: <db> : vfb_id : <VFB_id> }
        """
        return self.neo_query_wrapper.vfb_id_2_xrefs(vfb_id=vfb_id, db=db, id_type=id_type, reverse_return=reverse_return)

    def get_dbs(self, include_symbols=True, data_sources_only=True, verbose=False):
        """Get all external databases in the database, optionally filtering by data sources and including symbols.

        :param include_symbols: If True, include the symbols of the databases.
        :type include_symbols: bool
        :param data_sources_only: If True, only include databases where is_data_source=True.
        :type data_sources_only: bool
        :return: List of external databases and optionally their symbols.
        :rtype: list
        """
        # Create a cache key based on the options to ensure unique cache for each option set
        cache_key = (include_symbols, data_sources_only)

        # Check if the result is already cached
        if cache_key in self._dbs_cache and self._dbs_cache[cache_key]:
            print("Returning cached results") if verbose else None
            return self._dbs_cache[cache_key]

        print("Querying for external database ids") if verbose else None
        # Base query to get all databases, filtering for data sources if needed
        query = "MATCH (i:Individual) "
        if data_sources_only:
            query += "WHERE i.is_data_source=[True] AND (i:Site OR i:API) "
        else:
            query += "WHERE i:Site OR i:API "
        query += "RETURN i.short_form as id"

        # Execute the query
        print("Querying for external database ids:", query) if verbose else None
        results = self.cypher_query(query, return_dataframe=False, verbose=verbose)
        dbs = [d['id'] for d in results]

        # Optionally include symbols
        if include_symbols:
            print("Querying for external database symbols") if verbose else None
            symbol_query = "MATCH (i:Individual) "
            if data_sources_only:
                symbol_query += "WHERE i.is_data_source=[True] AND (i:Site OR i:API) "
            else:
                symbol_query += "WHERE i:Site OR i:API "
            symbol_query += "AND exists(i.symbol) AND not i.symbol[0] = '' RETURN i.symbol[0] as symbol"

            print("Querying for external database symbols:",symbol_query) if verbose else None
            symbol_results = self.cypher_query(symbol_query, return_dataframe=False, verbose=verbose)
            dbs.extend([d['symbol'] for d in symbol_results])

        # Cache the results for this combination of parameters
        self._dbs_cache[cache_key] = dbs

        return dbs

    def get_scRNAseq_expression(self, id, query_by_label=True, return_id_only=False, return_dataframe=True, verbose=False):
        """
        Get scRNAseq expression data for a given anatomy term.

        Returns a DataFrame of scRNAseq clusters of cells that are shown to express the current anatomy term.
        If no data is found, returns False.

        :param id: The ID, name, or symbol of a class in the Drosophila Anatomy Ontology (FBbt).
        :param query_by_label: Optional. Query using cell type labels if `True`, or IDs if `False`. Default `True`.
        :param return_id_only: Optional. Return only the cluster IDs if `True`. Default `False`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame with scRNAseq expression data for clusters of cells annotated as the specified cell type.
        :rtype: pandas.DataFrame or list of dicts
        """
        typ = 'Get JSON for anat_scRNAseq query'
        query = self.queries.get(typ,None)
        if not query:
            print("\033[31mError:\033[0m Query not found for %s" % typ)
            return None
        if query_by_label:
            id = self.lookup_id(id)
        qs = Template(query).substitute(ID=id)
        print(f"Running query: {qs}") if verbose else None
        r = self.nc.commit_list([qs])
        dc = dict_cursor(r)
        print(dc) if verbose else None
        if return_id_only:
            return [d.get('cluster',{}).get('short_form', None) for d in dc if d.get('cluster',{}).get('short_form', None)]
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        return dc

    def get_scRNAseq_gene_expression(self, cluster, query_by_label=True, return_id_only=False, return_dataframe=True, verbose=False):
        """
        Get gene expression data for a given scRNAseq cluster.

        Returns a DataFrame of gene expression data for a cluster of cells annotated as the specified cluster.
        If no data is found, returns False.

        :param cluster: The ID, name, or symbol of a class in the Drosophila Anatomy Ontology (FBbt).
        :param query_by_label: Optional. Query using cell type labels if `True`, or IDs if `False`. Default `True`.
        :param return_id_only: Optional. Return only the gene IDs if `True`. Default `False`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame with gene expression data for clusters of cells annotated as the specified cell type.
        :rtype: pandas.DataFrame or list of dicts
        """
        typ = 'Get JSON for cluster_expression query'
        query = self.queries.get(typ,None)
        if not query:
            print("\033[31mError:\033[0m Query not found for %s" % typ)
            return None
        cluster_id = None
        if isinstance(cluster, VFBTerm):
            cluster_id = cluster.id
        if isinstance(cluster, VFBTerms):
            raise ValueError("VFBTerms object passed to get_scRNAseq_gene_expression method. Please pass a single id/label/VFBTerm object.")
        if isinstance(cluster, str):
            if query_by_label:
                cluster_id = self.lookup_id(cluster)
            else:
                cluster_id = cluster
        if not cluster_id:
            raise ValueError("Cluster ID not matched for %s" % cluster)
        qs = Template(query).substitute(ID=cluster_id)
        print(f"Running query: {qs}") if verbose else None
        r = self.nc.commit_list([qs])
        dc = dict_cursor(r)
        if return_id_only:
            return [d.get('gene',{}).get('short_form', None) for d in dc if d.get('gene',{}).get('short_form', None)]
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        return dc

    def owl_subclasses(self, query, query_by_label=True, return_id_only=False, return_dataframe=False, limit=False, verbose=False):
        """
        Get subclasses of a given term.

        Returns a VFBTerms of subclasses of the specified term.
        If no data is found, returns False.

        :param term: The ID, name, or symbol of a class in the Drosohila Anatomy Ontology (FBbt).
        :param query_by_label: Optional. Query using cell type labels if `True`, or IDs if `False`. Default `True`.
        :param return_id_only: Optional. Return only the subclass IDs if `True`. Default `False`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `False`.
        :param limit: Optional. Limit the number of instances returned. Default `False`.
        :param verbose: Optional. If `True`, prints the running query and found terms. Default `False`.
        :return: A VFBTerms or DataFrame with subclasses of the specified term.
        :rtype: dependant on the options a pandas.DataFrame, list of ids or VFBTerms. Default is VFBTerms
        """
        ids = self.oc.get_subclasses(query=query, query_by_label=query_by_label, verbose=verbose)
        if not ids:
            ids = []
        else:
            if limit:
                print(f"Limiting to {limit} instances out of {len(ids)}")
                ids = ids[:limit]
        if return_id_only:
            return ids
        if return_dataframe:
            return self.terms(ids, verbose=verbose).get_summaries(return_dataframe=return_dataframe)
        return self.terms(ids, verbose=verbose)


    def owl_superclasses(self, query, query_by_label=True, return_id_only=False, return_dataframe=False, limit=False, verbose=False):
        """
        Get superclasses of a given term.

        Returns a VFBTerms of superclasses of the specified term.
        If no data is found, returns False.

        :param term: The ID, name, or symbol of a class in the Drosohila Anatomy Ontology (FBbt).
        :param query_by_label: Optional. Query using cell type labels if `True`, or IDs if `False`. Default `True`.
        :param return_id_only: Optional. Return only the superclass IDs if `True`. Default `False`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `False`.
        :param limit: Optional. Limit the number of instances returned. Default `False`.
        :param verbose: Optional. If `True`, prints the running query and found terms. Default `False`.
        :return: A VFBTerms or DataFrame with superclasses of the specified term.
       :rtype: dependant on the options a pandas.DataFrame, list of ids or VFBTerms. Default is VFBTerms
        """
        ids = self.oc.get_superclasses(query=query, query_by_label=query_by_label, verbose=verbose)
        if not ids:
            ids = []
        else:
            if limit:
                print(f"Limiting to {limit} instances out of {len(ids)}")
                ids = ids[:limit]
        if return_id_only:
            return ids
        if return_dataframe:
            return self.terms(ids, verbose=verbose).get_summaries(return_dataframe=return_dataframe)
        return self.terms(ids, verbose=verbose)

    def owl_instances(self, query, query_by_label=True, return_id_only=False, return_dataframe=False, limit=False, verbose=False):
        """
        Get instances of a given term.

        Returns a VFBTerms of instances of the specified term.
        If no data is found, returns False.

        :param term: The ID, name, or symbol of a class in the Drosohila Anatomy Ontology (FBbt).
        :param query_by_label: Optional. Query using cell type labels if `True`, or IDs if `False`. Default `True`.
        :param return_id_only: Optional. Return only the instance IDs if `True`. Default `False`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns VFBTerms. Default `False`.
        :param limit: Optional. Limit the number of instances returned. Default `False`.
        :param verbose: Optional. If `True`, prints the running query and found terms. Default `False`.
        :return: A VFBTerms or DataFrame with instances of the specified query.
        :rtype: dependant on the options a pandas.DataFrame, list of ids or VFBTerms. Default is VFBTerms
        """
        ids = self.oc.get_instances(query=query, query_by_label=query_by_label, verbose=verbose)
        if not ids:
            ids = []
        else:
            if limit:
                print(f"Limiting to {limit} instances out of {len(ids)}")
                ids = ids[:limit]
        if return_id_only:
            return ids
        if return_dataframe:
            return self.terms(ids, verbose=verbose).get_summaries(return_dataframe=return_dataframe)
        return self.terms(ids, verbose=verbose)

    def cypher_query(self, query, return_dataframe=True, verbose=False):
        """
        Run a Cypher query.

        :param query: The Cypher query to run.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame or list of results.
        :rtype: pandas.DataFrame or list of dicts
        """
        print(f"Running query: {query}") if verbose else None
        r = self.nc.commit_list([query])
        print(r) if verbose else None
        dc = dict_cursor(r)
        print(dc) if verbose else None
        if return_dataframe:
            print("Returning DataFrame") if verbose else None
            return pd.DataFrame.from_records(dc)
        return dc

    def get_nt_predictions(self, term, verbose=False):
        """
        Find predicted neurotransmitter(s) for a single neuron or all neurons of a given type.
        If nothing is found, an empty DataFrame is returned.
        :param term: The ID, name, or symbol of a class in the Drosophila Anatomy Ontology (FBbt) or the ID or name of an individual neuron in VFB.
        :return: A DataFrame.
        :rtype: pandas.DataFrame
        """
        input_id = self.lookup_id(term)
        # check input type
        type_results = self.cypher_query(
            query="MATCH (n:Neuron {short_form:'%s'}) RETURN labels(n) AS labels" % input_id)
        input_labels = type_results.labels[0]

        def get_instance_predicted_nts(nt_search_ids, verbose=False):
            results = self.cypher_query(query="""
            MATCH (i:Individual:Neuron)-[c:capable_of]->(nt) 
            WHERE EXISTS(c.confidence_value) 
            AND i.short_form IN %s
            RETURN i.label AS individual, i.short_form AS individual_id, labels(i) AS instance_labels, 
            nt.label AS predicted_nt, c.confidence_value[0] AS confidence, c.database_cross_reference AS references
            """ % nt_search_ids)
            if results.empty:
                print(f"No predicted neurotransmitters found for {nt_search_ids}.") if verbose else None
            else:
                results['all_nts'] = results['instance_labels'].apply(
                    lambda x: [l for l in x if l in NT_NTR_pairs.keys()])  # needed by get_nt_receptors_in_downstream_neurons
                results = results.drop('instance_labels', axis=1)
            return results

        if 'Individual' in input_labels:
            output = get_instance_predicted_nts([input_id], verbose=verbose)
        elif 'Class' in input_labels:
            instances = self.get_instances(input_id, query_by_label=False)
            instance_ids = instances['id'].to_list()
            output = get_instance_predicted_nts(instance_ids, verbose=verbose)

        if output.empty:
            print(f"No predicted neurotransmitters found for {term}.") if verbose else None
        return output

    def get_nt_receptors_in_downstream_neurons(self, upstream_type, downstream_type='neuron', weight=0, use_predictions=True, return_dataframe=True, verbose=False):
        """
        Get neurotransmitter receptors in downstream neurons of a given neuron type.

        Returns a DataFrame of neurotransmitter receptors in downstream neurons of a specified neuron type.
        If no data is found, returns False.
        If use_predictions, an extra column ('nt_only_predicted') will indicate whether each receptor is for a neurotransmitter that is only predicted to be released by the upstream type.

        :param upstream_type: The ID, name, or symbol of a class in the Drosophila Anatomy Ontology (FBbt).
        :param downstream_type: Optional. The type of downstream neurons to search for. Default is 'neuron'.
        :param weight: Optional. Limit returned neurons to those connected by >= weight synapses. Default is 0.
        :param use_predictions: Optional. Use predicted neurotransmitters (from instances) in addition to known neurotransmitters. Default is True.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame with neurotransmitter receptors in downstream neurons of the specified neuron type.
        :rtype: pandas.DataFrame or list of dicts
        """
        upstream_type = self.lookup_id(upstream_type)
        downstream_type = self.lookup_id(downstream_type)

        # get all types of all connected neurons that are instances of downstream_type
        downstream = self.get_connected_neurons_by_type(upstream_type=upstream_type, downstream_type=downstream_type, weight=weight)
        downstream['downstream_class'] = downstream['downstream_class'].apply(
            lambda x: x.split('|') if isinstance(x, str) else x)
        downstream_classes = downstream.explode('downstream_class')['downstream_class'].drop_duplicates().to_list()

        # only keep downstream_classes that are subclasses of downstream_type
        subclass_check_query = self.cypher_query(
            query=("MATCH (c2:Neuron:Class)-[:SUBCLASSOF*0..]->(c1:Neuron:Class) "
                   "WHERE c2.label IN %s AND c1.short_form = '%s'"
                   "RETURN c2.label AS downstream_classes"
                    % (downstream_classes, downstream_type)))
        downstream_classes = subclass_check_query.downstream_classes.to_list()

        # get nts for upstream
        cell_type_short_form = self.lookup_id(upstream_type)
        known_nt_results = self.cypher_query(query="MATCH (n:Neuron {short_form:'%s'}) RETURN labels(n) AS labels" % cell_type_short_form)
        nts = [r for r in known_nt_results.labels[0] if r in NT_NTR_pairs.keys()]
        if use_predictions:
            predicted_nt_results = self.get_nt_predictions(upstream_type)
            if not predicted_nt_results.empty:
                pred_nts = predicted_nt_results.explode('all_nts')['all_nts'].drop_duplicates().to_list()
                pred_only_nts = [nt for nt in pred_nts if nt not in nts]
            else:
                pred_only_nts = []
            nts.extend(pred_only_nts)

        print(nts) if verbose else None
        if nts:
            ntr = [NT_NTR_pairs[n] for n in nts]
        elif not use_predictions:
            print(f"No known neurotransmitters for {upstream_type}, try setting use_predictions=True")
        else:
            print(f"No known or predicted neurotransmitters for {upstream_type}")

        if use_predictions:
            pred_only_ntrs = [NT_NTR_pairs[n] for n in pred_only_nts]

        # get expression for each ntr in each downstream class
        dataframes = []
        for c in downstream_classes:
            for n in ntr:
                # only exact match classes (no_subtypes=True)
                # to avoid specific-looking results based on general typing of connectomics data
                df = self.get_transcriptomic_profile(c, gene_type=n, no_subtypes=True)
                if use_predictions:
                    if n in pred_only_ntrs:
                        df['nt_only_predicted'] = True
                    else:
                        df['nt_only_predicted'] = False
                dataframes.append(df)
        receptor_expression = pd.concat(dataframes, ignore_index=True)
        if not return_dataframe:
            return receptor_expression.to_dict('records')
        return receptor_expression
    
    import json


    def search(self, query, return_dataframe=True, verbose=False, filter_by_has_tag=None, filter_by_not_tag=['Deprecated']):
        """
        Search for terms in the database using a complex Solr query configuration.

        :param query: The search query.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :param verbose: Optional. If `True`, prints the query for debugging purposes.
        :param filter_by_has_tag: Optional. List of tags to boost if present. These will be upvoted in the query.
        :param filter_by_not_tag: Optional. List of tags to downvote if present. These will be downvoted in the query.
        :return: A DataFrame or list of results.
        :rtype: pandas.DataFrame or list of dicts
        """
        import pysolr

        # Initialize the Solr client
        solr = pysolr.Solr(self.solr_url, always_commit=True)

        # Base search parameters
        search_params = {
            "q": f"({query} OR {query}* OR *{query} OR *{query}*)",
            "q.op": "OR",
            "defType": "edismax",
            "mm": "45%",
            "qf": "label^110 synonym^100 label_autosuggest synonym_autosuggest shortform_autosuggest",
            "fl": "short_form,label,synonym,id,facets_annotation,unique_facets",
            "start": "0",
            "pf": "true",
            "fq": [
                "(short_form:VFB* OR short_form:FB* OR facets_annotation:DataSet OR facets_annotation:pub) AND NOT short_form:VFBc_*"
            ],
            "rows": "150",
            "wt": "json",
            "bq": "short_form:VFBexp*^10.0 short_form:VFB*^100.0 short_form:FBbt*^100.0 short_form:FBbt_00003982^2"
        }

        # Adding 'has tag' filters to boost query (upvote)
        if filter_by_has_tag:
            for tag in filter_by_has_tag:
                search_params["bq"] += f" facets_annotation:{tag}^10.0"

        # Adding 'not tag' filters to boost query (downvote)
        if filter_by_not_tag:
            for tag in filter_by_not_tag:
                search_params["bq"] += f" facets_annotation:{tag}^0.001"

        # Convert the search parameters to JSON string for debugging
        search_json = json.dumps({"params": search_params})
        
        if verbose:
            print(f"Solr Search JSON: {search_json}")

        # Execute the search
        results = solr.search(**search_params)

        # Return results as a DataFrame or list of dictionaries
        if return_dataframe:
            return pd.DataFrame(results.docs)
        else:
            return results.docs


    def term(self, term, verbose=False):
        """Get a VFBTerm object for a given term id, name, symbol or synonym.

        :param term: The term to look up.
        :return: a VFBTerm object
        :rtype: dict
        """
        if isinstance(term, VFBTerm):
            return term
        if isinstance(term, VFBTerms):
            print("Warning: VFBTerms object passed to term method. Returning first term.")
            term = term[0]
        print(term) if verbose else None
        return VFBTerm(term, verbose=verbose)

    def terms(self, terms, verbose=False):
        """Get a list of VFBTerm objects for a given list of term id, name, symbol or synonym.

        :param terms: A list of terms to look up.
        :return: a VFBTerms list of VFBTerm objects
        :rtype: VFBTerms
        """
        if isinstance(terms, VFBTerm):
            return VFBTerms([terms], verbose=verbose)
        if isinstance(terms, VFBTerms):
            return terms
        print(terms) if verbose else None
        return VFBTerms(terms, verbose=verbose)

    def generate_lab_colors(self, num_colors, min_distance=100, verbose=False):
        """
        Generate a list of Lab colors and convert them to RGB tuples.

        :param num_colors: The number of colors to generate.
        :param min_distance: Minimum perceptual distance between colors.
        :return: A list of RGB tuples.
        """
        # Generate a large set of candidate colors in Lab space
        grid_size = int(np.ceil((num_colors * 5) ** (1 / 3)))  # Generating more candidates
        l_values = np.linspace(0, 100, grid_size)
        a_values = np.linspace(-100, 100, grid_size)
        b_values = np.linspace(-100, 100, grid_size)

        lab_colors = np.array(np.meshgrid(l_values, a_values, b_values)).T.reshape(-1, 3)

        # Shuffle the candidate colors to introduce randomness
        np.random.shuffle(lab_colors)

        selected_lab_colors = []
        rgb_colors = []

        # Select the first color
        lab_tree = KDTree([(0, 0, 0)])  # Start tree with black

        # Pick colors that are far apart from each other and from black
        for lab in lab_colors[0:]:
            distances, _ = lab_tree.query([lab], k=1)
            if distances[0] >= min_distance:
                selected_lab_colors.append(lab)
                lab_tree = KDTree(selected_lab_colors)  # Update tree with the new color
            if len(selected_lab_colors) >= num_colors:
                break

        # Convert Lab to RGB
        for lab in selected_lab_colors:
            lab_color = LabColor(lab[0], lab[1], lab[2])
            rgb_color = convert_color(lab_color, sRGBColor)
            rgb_tuple = (int(round(rgb_color.clamped_rgb_r * 255)),
                         int(round(rgb_color.clamped_rgb_g * 255)),
                         int(round(rgb_color.clamped_rgb_b * 255)))
            rgb_colors.append(rgb_tuple)

        if verbose:
            print(f"Generated RGB colors: {rgb_colors}")

        return rgb_colors

      