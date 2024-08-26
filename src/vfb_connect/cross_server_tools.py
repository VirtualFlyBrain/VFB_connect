import json
import os
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
                 owlery_endpoint=get_default_servers()['owlery_endpoint']):
        """
        VFB connect constructor. All args optional.
        With no args wraps connectsions to default public servers.

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
        self.nc = Neo4jConnect(**connections['neo'])
        self.neo_query_wrapper = QueryWrapper(**connections['neo'])
        self.cache_file = self.get_cache_file_path()
        self.lookup = self.nc.get_lookup(cache=self.cache_file)
        self.oc = OWLeryConnect(endpoint=owlery_endpoint,
                                lookup=self.lookup)
        self.vfb_base = "https://v2.virtualflybrain.org/org.geppetto.frontend/geppetto?id="

        multi_query_json = pkg_resources.resource_filename(
                            "vfb_connect",
                            "resources/VFB_results_multi_input.json")
        with open(multi_query_json, 'r') as f:
            self.queries = json.loads(saxutils.unescape(f.read()))

        self._term_cache = []
        self._use_cache = True

        print("\033[32mSession Established!\033[0m")
        print("")
        print("\033[33mType \033[35mvfb. \033[33mand press \033[35mtab\033[33m to see available queries. You can run help against any query e.g. \033[35mhelp(vfb.terms)\033[0m")

    def __dir__(self):
        return [attr for attr in list(self.__dict__.keys()) if not attr.startswith('_')] + [attr for attr in dir(self.__class__) if not attr.startswith('_') and not attr.startswith('add_')]


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
        """Lookup the name for a given ID using the internal lookup table.

        :param ids: A single ID or list of IDs to look up.
        :return: The name associated with the ID.
        :rtype: str
        """
        if isinstance(ids, list):
            return [self.lookup_name(id) for id in ids]
        return {v: k for k, v in self.lookup.items()}[ids]

    def lookup_id(self, key, return_curie=False, allow_subsitutions=True, subsitution_stages=['adult', 'larval', 'pupal'], verbose=False):
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
        # Check if the key is a VFBTerm object
        if isinstance(key, VFBTerm):
            return key.id
        
        if isinstance(key, VFBTerms):
            return key.get_ids()
        
        if isinstance(key, list):
            return [self.lookup_id(k, return_curie=return_curie, allow_subsitutions=allow_subsitutions, subsitution_stages=subsitution_stages) for k in key]
        
        # Direct lookup: Check if the key is already a valid ID
        if key in self.lookup.values():
            return key if not return_curie else key.replace('_', ':')
        
        # CARO lookup: Check if the key is a CARO/BFO/UBERON/FBbt(obsolete) term; though not in the lookup they need to be handled if explicitly called
        prefixes = ('CARO_', 'BFO_', 'UBERON_', 'GENO_', 'CL_', 'FB', 'VFB_', 'GO_', 'SO_', 'RO_', 'PATO_', 'CHEBI_', 'PR_', 'NCBITaxon_', 'ENVO_', 'OBI_', 'IAO_', 'OBI_')
        if isinstance(key,str) and key.startswith(prefixes) and not key in self.lookup.keys():
            return key if not return_curie else key.replace('_', ':')
        
        # Direct lookup in the dictionary
        if key in self.lookup.keys():
            out = self.lookup[key]
            return out if not return_curie else out.replace('_', ':')
        else:
            print(f"No direct match found for {key}")

        if allow_subsitutions:
            matched_key = ''
            out = ''
            # Case-insensitive and character-insensitive lookup
            normalized_key = key.lower().replace('_', '').replace('-', '').replace(' ', '').replace(':','')
            print(f"Normalized key: {normalized_key}") if verbose else None
            matches = {k: v for k, v in self.lookup.items() if k.lower().replace('_', '').replace('-', '').replace(' ', '').replace(':','').replace(';','') == normalized_key}

            if isinstance(subsitution_stages, str):
                subsitution_stages = [subsitution_stages]
            if not matches:
                for stage in subsitution_stages:
                        stage_normalized_key = stage + normalized_key
                        matches = {k: v for k, v in self.lookup.items() if k.lower().replace('_', '').replace('-', '').replace(' ', '').replace(':','').replace(';','') == stage_normalized_key}
                        if matches:
                            break

            if matches:
                for k, v in matches.items():
                    print(f"Matched: {k} -> {v}") if verbose else None
                    if not matched_key:
                        matched_key = k

                # Warn if a case substitution or normalization was performed
                if matched_key:
                    if len(matches.keys()) < 2:
                        print(f"\033[33mWarning:\033[0m Substitution made. '\033[33m{key}\033[0m' was matched to '\033[32m{matched_key}\033[0m'.")
                        out = matches[matched_key]
                    else:
                        all_matches = ", ".join([f"'{k}': '{v}'" for k, v in matches.items()])
                        print(f"\033[33mWarning:\033[0m Ambiguous match for '\033[33m{key}\033[0m'. Using '{matched_key}' -> '\033[32m{out}\033[0m'. Other possible matches: {all_matches}")

                return out if not return_curie else out.replace('_', ':')

            # Check for partial matches: starts with
            starts_with_matches = {k: v for k, v in self.lookup.items() if k.lower().startswith(key.lower())}
            if starts_with_matches:
                all_matches = ", ".join([f"'\033[36m{k}\033[0m': '{v}'" for k, v in starts_with_matches.items()])
                print(f"Notice: No exact match found, but potential matches starting with '\033[31m{key}\033[0m': {all_matches}")
                return ''

            # Check for partial matches: contains
            contains_matches = {k: v for k, v in self.lookup.items() if key.lower() in k.lower()}
            if contains_matches:
                all_matches = ", ".join([f"'\033[36m{k}\033[0m': '{v}'" for k, v in contains_matches.items()])
                print(f"Notice: No exact match found, but potential matches containing '\033[31m{key}\033[0m': {all_matches}")
                return ''

        print(f"\033[31mError:\033[0m Unrecognized value: \033[31m{key}\033[0m")
        return ''

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
            terms = self.oc.get_instances("%s" % class_expression, query_by_label=query_by_label)
            if return_id_only:
                return terms
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

    def get_connected_neurons_by_type(self, upstream_type, downstream_type, weight, query_by_label=True,
                                      return_dataframe=True, verbose=False):
        """Get all synaptic connections between individual neurons of `upstream_type` and `downstream_type` where
        synapse count >= `weight`.

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
        if query_by_label:
            upstream_type = self.lookup_id(dequote(upstream_type))
            downstream_type = self.lookup_id(dequote(downstream_type))

        cypher_query = "MATCH (up:Class:Neuron)<-[:SUBCLASSOF|INSTANCEOF*..]-(n1:Neuron:Individual) " \
                       'WHERE up.short_form = "%s" ' % upstream_type
        cypher_query += "MATCH (n1)-[r:synapsed_to]->(n2:Neuron:Individual) " \
                        "WHERE r.weight[0] >= %d " % weight
        cypher_query += "MATCH (n2)-[:SUBCLASSOF|INSTANCEOF*..]->(down:Class:Neuron) " \
                        'WHERE down.short_form = "%s" ' % downstream_type
        cypher_query += "MATCH (c1:Class)<-[:INSTANCEOF]-(n1),  (c2:Class)<-[:INSTANCEOF]-(n2) " \
                        "OPTIONAL MATCH (n1)-[r1:database_cross_reference]->(s1:Site) " \
                        "WHERE exists(s1.is_data_source) AND s1.is_data_source = True " \
                        "OPTIONAL MATCH (n2)-[r2:database_cross_reference]->(s2:Site) " \
                        "WHERE exists(s2.is_data_source) AND s2.is_data_source = True " \
                        "RETURN n1.short_form as upstream_neuron_id, n1.label as upstream_neuron_name, " \
                        "r.weight[0] as weight, n2.short_form as downstream_neuron_id, " \
                        "n2.label as downstream_neuron_name, " \
                        "apoc.text.join(collect(distinct c1.label),'|') AS upstream_class, " \
                        "apoc.text.join(collect(distinct c2.label),'|') as downstream_class, " \
                        "s1.short_form AS up_data_source, r1.accession[0] as up_accession," \
                        "s2.short_form AS down_source, r2.accession[0] AS down_accession"
        print(cypher_query) if verbose else None
        r = self.nc.commit_list([cypher_query])
        dc = dict_cursor(r)
        print(dc) if verbose else None
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
                    "RETURN collect(i.short_form) as inds" % dataset
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
        query = ("MATCH (g:Gene) RETURN DISTINCT apoc.coll.subtract(labels(g), "
                 "['Class', 'Entity', 'hasScRNAseq', 'Feature', 'Gene']) AS gene_labels")
        result = self.neo_query_wrapper._query(query)
        labels = []
        for r in result:
            labels.extend(r['gene_labels'])
        labels = sorted(list(set(labels)))
        return labels

    def get_transcriptomic_profile(self, cell_type, gene_type=False, query_by_label=True, return_dataframe=True):
        """Get gene expression data for a given cell type.

        Returns a DataFrame of gene expression data for clusters of cells annotated as the specified cell type (or subtypes).
        Optionally restricts to a gene type, which can be retrieved using `get_gene_function_filters`.
        If no data is found, returns False.

        :param cell_type: The ID, name, or symbol of a class in the Drosophila Anatomy Ontology (FBbt).
        :param gene_type: Optional. A gene function label retrieved using `get_gene_function_filters`.
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

        query = ("MATCH (g:Gene:Class%s)<-[e:expresses]-(clus:Cluster:Individual)-"
                 "[:composed_primarily_of]->(c2:Class)-[:SUBCLASSOF*0..]->(c1:Neuron:Class) "
                 "WHERE c1.short_form = '%s' "
                 "MATCH (clus)-[:part_of]->()-[:has_part]->(sa:Sample:Individual) "
                 "OPTIONAL MATCH (sa)-[:part_of]->(sex:Class) "
                 "WHERE sex.short_form IN ['FBbt_00007011', 'FBbt_00007004'] "
                 "OPTIONAL MATCH (sa)-[:overlaps]->(tis:Class:Anatomy) "
                 "OPTIONAL MATCH (clus)-[:has_source]->(ds:DataSet:Individual) "
                 "OPTIONAL MATCH (ds)-[:has_reference]->(p:pub:Individual) "
                 "OPTIONAL MATCH (ds)-[dbx:database_cross_reference]->(s:Site:Individual) "
                 "RETURN DISTINCT c2.label AS cell_type, c2.short_form AS cell_type_id, "
                 "sex.label AS sample_sex, COLLECT(tis.label) AS sample_tissue, "
                 "p.miniref[0] as ref, g.label AS gene, g.short_form AS gene_id, "
                 "apoc.coll.subtract(labels(g), ['Class', 'Entity', 'hasScRNAseq', 'Feature', 'Gene']) AS function, "
                 "e.expression_extent[0] as extent, toFloat(e.expression_level[0]) as level "
                 "ORDER BY cell_type, g.label" % (gene_label, cell_type_short_form))
        r = self.nc.commit_list([query])
        dc = dict_cursor(r)
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        else:
            return dc

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
    
    def get_templates(self, summary=True, return_dataframe=True):
        """Get all templates in the database.

        :return: List of templates in the database.
        :rtype: list
        """
        return self.neo_query_wrapper.get_templates(summary=summary, return_dataframe=return_dataframe)
    
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

    def xref_2_vfb_id(self, acc=None, db='', id_type='', reverse_return=False):
        """Map a list external DB IDs to VFB IDs

        :param acc: An iterable (e.g. a list) of external IDs (e.g. neuprint bodyIDs).
        :param db: optional specify the VFB id (short_form) of an external DB to map to. (use get_dbs to find options)
        :param id_type: optionally specify an external id_type
        :param reverse_return: Boolean: Optional (see return)
        :return: if `reverse_return` is False:
            dict { acc : [{ db: <db> : vfb_id : <VFB_id> }
            Return if `reverse_return` is `True`:
            dict { VFB_id : [{ db: <db> : acc : <acc> }
        """
        return self.neo_query_wrapper.xref_2_vfb_id(acc=acc, db=db, id_type=id_type, reverse_return=reverse_return)
    
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

    def get_dbs(self, include_symbols=False):
        """Get all external databases in the database.

        :return: List of external databases in the database.
        :rtype: list
        """
        return self.neo_query_wrapper.get_dbs(include_symbols=include_symbols)

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

    def owl_subclasses(self, query, query_by_label=True, return_id_only=False, return_dataframe=True, verbose=False):
        """
        Get subclasses of a given term.

        Returns a VFBTerms of subclasses of the specified term.
        If no data is found, returns False.

        :param term: The ID, name, or symbol of a class in the Drosohila Anatomy Ontology (FBbt).
        :param query_by_label: Optional. Query using cell type labels if `True`, or IDs if `False`. Default `True`.
        :param return_id_only: Optional. Return only the subclass IDs if `True`. Default `False`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame with subclasses of the specified term.
        :rtype: dependant on the options a pandas.DataFrame, list of ids or VFBTerms. Default is VFBTerms
        """
        ids = self.oc.get_subclasses(query=query, query_by_label=query_by_label, verbose=verbose)
        if not ids:
            ids = []
        if return_id_only:
            return ids
        if return_dataframe:
            return self.terms(ids, verbose=verbose).get_summaries(return_dataframe=return_dataframe)
        return self.terms(ids, verbose=verbose)


    def owl_superclasses(self, query, query_by_label=True, return_id_only=False, return_dataframe=False, verbose=False):
        """
        Get superclasses of a given term.

        Returns a VFBTerms of superclasses of the specified term.
        If no data is found, returns False.

        :param term: The ID, name, or symbol of a class in the Drosohila Anatomy Ontology (FBbt).
        :param query_by_label: Optional. Query using cell type labels if `True`, or IDs if `False`. Default `True`.
        :param return_id_only: Optional. Return only the superclass IDs if `True`. Default `False`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame with superclasses of the specified term.
       :rtype: dependant on the options a pandas.DataFrame, list of ids or VFBTerms. Default is VFBTerms
        """
        ids = self.oc.get_superclasses(query=query, query_by_label=query_by_label, verbose=verbose)
        if not ids:
            ids = []
        if return_id_only:
            return ids
        if return_dataframe:
            return self.terms(ids, verbose=verbose).get_summaries(return_dataframe=return_dataframe)
        return self.terms(ids, verbose=verbose)

    def owl_instances(self, query, query_by_label=True, return_id_only=False, return_dataframe=True, verbose=False):
        """
        Get instances of a given term.

        Returns a VFBTerms of instances of the specified term.
        If no data is found, returns False.

        :param term: The ID, name, or symbol of a class in the Drosohila Anatomy Ontology (FBbt).
        :param query_by_label: Optional. Query using cell type labels if `True`, or IDs if `False`. Default `True`.
        :param return_id_only: Optional. Return only the instance IDs if `True`. Default `False`.
        :param return_dataframe: Optional. Returns pandas DataFrame if `True`, otherwise returns list of dicts. Default `True`.
        :return: A DataFrame with instances of the specified term.
        :rtype: dependant on the options a pandas.DataFrame, list of ids or VFBTerms. Default is VFBTerms
        """
        ids = self.oc.get_instances(query=query, query_by_label=query_by_label, verbose=verbose)
        if not ids:
            ids = []
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
        r = self.nc.commit_list([query])
        dc = dict_cursor(r)
        if return_dataframe:
            return pd.DataFrame.from_records(dc)
        return dc

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
    
    def generate_lab_colors(self, num_colors, verbose=False):
        """
        Generate a list of Lab colors and convert them to RGB tuples.
        
        :param num_colors: The number of colors to generate.
        :return: A list of RGB tuples.
        """
        # Calculate the grid size for each of L, a, and b components
        grid_size = int(np.ceil(num_colors ** (1/3)))

        # Generate linearly spaced values for L, a, and b components
        l_values = np.linspace(0, 100, grid_size)
        a_values = np.linspace(-100, 100, grid_size)
        b_values = np.linspace(-100, 100, grid_size)

        # Create a meshgrid and reshape to get all combinations
        lab_colors = np.array(np.meshgrid(l_values, a_values, b_values)).T.reshape(-1, 3)

        # If we generated more colors than needed, truncate the list
        if len(lab_colors) > num_colors:
            lab_colors = lab_colors[:num_colors]

        # Convert Lab to RGB
        rgb_colors = []
        for lab in lab_colors:
            lab_color = LabColor(lab[0], lab[1], lab[2])
            rgb_color = convert_color(lab_color, sRGBColor)
            rgb_tuple = (int(rgb_color.clamped_rgb_r * 255), 
                        int(rgb_color.clamped_rgb_g * 255), 
                        int(rgb_color.clamped_rgb_b * 255))
            rgb_colors.append(rgb_tuple)

        print(rgb_colors) if verbose else None
        return rgb_colors
