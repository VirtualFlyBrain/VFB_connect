import json
import os
import re
import shutil
from inspect import getfullargspec
from string import Template
from xml.sax import saxutils
import pandas as pd
import pkg_resources
import requests
from functools import wraps
import pysolr
from itertools import chain



# from jsonpath_rw import parse as parse_jpath
from vfb_connect.neo.neo4j_tools import chunks, Neo4jConnect, dict_cursor, escape_string

# Connect to the VFB SOLR server
vfb_solr = pysolr.Solr('http://solr.virtualflybrain.org/solr/vfb_json/', always_commit=False, timeout=990)


def batch_query(func):
    """Decorator to batch the first argument of the function (assumed to be an iterable) and apply the function to each batch.
    
    Assumes the first argument is to be batched and that the return value is a list. Only works on class methods.
    
    :param func: The function to be wrapped and batched.
    :return: A wrapper function that processes the input in batches.
    """
    @wraps(func)
    def wrapper_batch(*args, **kwargs):
        arg_names = getfullargspec(func).args

        if len(args) > 1:
            arg1v = args[1]
            arg1typ = 'a'
        else:
            arg1v = kwargs.get(arg_names[1])
            arg1typ = 'k'

        cs = chunks(arg1v, 2500)
        out = []
        for c in cs:
            if arg1typ == 'a':
                arglist = list(args)
                arglist[1] = c
                subargs = tuple(arglist)
                out.extend(func(*subargs, **kwargs))
            elif arg1typ == 'k':
                kwargdict = dict(kwargs)
                kwargdict[arg_names[1]] = c
                out.extend(func(*args, **kwargdict))
        # Check if return_dataframe is requested and summary is requested
        if out and isinstance(out, list) and len(out) > 0 and dict(kwargs).get('return_dataframe', 'return_dataframe' in arg_names) and dict(kwargs).get('summary', True):
            try:
                return pd.DataFrame.from_records(out)
            except TypeError as e:
                # Debugging information
                print("TypeError encountered during DataFrame conversion.")
                print(f"Error message: {e}")
                print("Data attempted to convert to DataFrame:")
                print(f"Data (first 5 records): {out[:5] if out else 'No data available'}")
                print("Arguments provided:")
                print(f"kwargs: {kwargs}")
                print(f"arg_names: {arg_names}")
                raise e
        return out
    return wrapper_batch



# def pop_from_jpath(jpath, json, join=True):
#     expr = parse_jpath(jpath)
#     if join:
#         return '|'.join([match.value for match in expr.find(json)])
#     else:
#         return [match.value for match in expr.find(json)]


def _populate_minimal_summary_tab(TermInfo):
    d = dict()
    d['label'] = TermInfo['term']['core']['label']
    d['symbol'] = TermInfo['term']['core'].get('symbol', '')
    d['id'] = TermInfo['term']['core']['short_form']
    d['tags'] = TermInfo['term']['core']['types']
    return d

def _populate_data_source_id(TermInfo, d = dict()):
    # Populate data source summary tab if source xrefs
    if 'xrefs' in TermInfo.keys():
        data_sources = []
        ds_accessions = []

        for p in TermInfo['xrefs']:
            # Check if 'is_data_source' is set and truthy
            if p.get('is_data_source') and p.get('is_data_source') is True:
                # Add site short_form or symbol to data_sources
                symbol = p['site'].get('symbol')
                if not symbol:  # This covers both None and empty string
                    symbol = p['site']['short_form']
                data_sources.append(symbol)
                # Add accession if available
                if 'accession' in p.keys():
                    ds_accessions.append(p['accession'])

        # Join the results with '|'
        d['data_source'] = data_sources
        d['accession'] = ds_accessions
    return d


def _populate_anatomical_entity_summary(TermInfo):
    d = _populate_minimal_summary_tab(TermInfo)
    d = _populate_data_source_id(TermInfo, d)
#   d['parents_symbol'] = pop_from_jpath("$.parents[*].symbol", TermInfo)
#   d['parents_label'] = pop_from_jpath("$.parents[*].label", TermInfo)
    d['parents_label'] = [str(p['label']) for p in TermInfo['parents']]
#   d['parents_id'] = pop_from_jpath("$.parents[*].short_form", TermInfo)
    d['parents_id'] = [str(p['short_form']) for p in TermInfo['parents']]

    return d


def _populate_instance_summary_tab(TermInfo):
    d = _populate_anatomical_entity_summary(TermInfo)
#    site_expr = "$.xrefs.[*].site.short_form"
#    acc_expr = "$.xrefs.[*].accession"
#    is_data_source_expr = "$.xrefs.[*].is_data_source"
#   sites = pop_from_jpath(site_expr, TermInfo, join=False)
    i = 0
    if 'xrefs' in TermInfo.keys():
        d['xrefs'] = [
            f"{p['site']['symbol'] if p['site'].get('symbol') else p['site']['short_form']}:{p['accession']}"
            for p in TermInfo['xrefs']
        ]
    d['templates'] = [str(x['image']['template_anatomy']['label']) for x in TermInfo['channel_image']]
    d['dataset'] = [str(x['dataset']['core']['short_form']) for x in TermInfo['dataset_license']]
    d['license'] = [str(x['license']['link']) for x in TermInfo['dataset_license']
                             if 'link' in x['license'].keys()]
    return d


def _populate_dataset_summary_tab(TermInfo):
    d = _populate_minimal_summary_tab(TermInfo)
    d['description'] = TermInfo['term']['description']
    d['miniref'] = [str(x['core']['label']) for x in TermInfo['pubs']]
    d['FlyBase'] = [str(x['FlyBase']) for x in TermInfo['pubs'] if 'FlyBase' in x]
    d['PMID'] = [str(x['PubMed']) for x in TermInfo['pubs'] if 'PubMed' in x]
    d['DOI'] = [str(x['DOI']) for x in TermInfo['pubs'] if 'PubMed' in x]
    return d


def _populate_manifest(filename, instance):
    d = _populate_instance_summary_tab(instance)
    d['filename'] = filename
    return d

def _populate_summary(TermInfo):
    """
    Generalized function to populate a summary dictionary based on the fields available in the TermInfo JSON,
    including cross-reference (xref) terms formatted as 'DB:xxxxx'.

    :param TermInfo: The JSON object containing term information.
    :rtype: dict
    """
    def get_value(key, default=''):
        return TermInfo.get(key, default)
    
    d = dict()
    
    # Populate minimal summary tab
    d['label'] = get_value('term', {}).get('core', {}).get('label', '')
    d['symbol'] = get_value('term', {}).get('core', {}).get('symbol', '')
    d['id'] = get_value('term', {}).get('core', {}).get('short_form', '')
    d['tags'] = get_value('term', {}).get('core', {}).get('types', [])

    if get_value('term', {}).get('description', '') or get_value('term', {}).get('comment', ''):
        d['description'] = ' '.join(get_value('term', {}).get('description', '')) + ' ' + ' '.join(get_value('term', {}).get('comment', ''))
    
    # Populate anatomical entity summary if available
    if 'parents' in TermInfo.keys():
        d['parents_label'] = [str(p['label']) for p in TermInfo['parents']]
        d['parents_id'] = [str(p['short_form']) for p in TermInfo['parents']]

    d = _populate_data_source_id(TermInfo, d)

    # Populate instance summary tab if available
    if 'xrefs' in TermInfo.keys():
        d['xrefs'] = [
            f"{p['site']['symbol'] if p['site'].get('symbol') else p['site']['short_form']}:{p['accession']}"
            for p in TermInfo['xrefs']
        ]

    if 'channel_image' in TermInfo.keys():
        d['templates'] = [str(x['image']['template_anatomy']['label']) for x in TermInfo['channel_image']]
    
    if 'dataset_license' in TermInfo.keys():
        d['dataset'] = [str(x['dataset']['core']['short_form']) for x in TermInfo['dataset_license']]
        d['license'] = [str(x['license']['link']) for x in TermInfo['dataset_license'] if 'link' in x['license'].keys()]

    # Populate dataset summary tab if available
    if 'term' in TermInfo.keys() & 'description' in TermInfo['term'].keys():
        d['description'] = get_value('term', {}).get('description', '')
    
    if 'pubs' in TermInfo.keys():
        d['miniref'] = [str(x['core']['label']) for x in TermInfo['pubs']]
        d['FlyBase'] = [str(x['FlyBase']) for x in TermInfo['pubs'] if 'FlyBase' in x]
        d['PMID'] = [str(x['PubMed']) for x in TermInfo['pubs'] if 'PubMed' in x]
        d['DOI'] = [str(x['DOI']) for x in TermInfo['pubs'] if 'DOI' in x]

    return d

# def filter_term_content(func):
#     """Decorator function that wraps queries that return lists of JSON objects and which have
#      an arg named filters.  The filters arg takes a filter object, which specifics JPATH queries which are applied
#      as a filter to each returned JSON object so that the final result only contains the
#      specified paths and their values"""
#
#     type_2_summary = {
#         'individual': '_populate_instance_summary_tab',
#         'class': '_populate_anatomical_entity_summary',
#     }

    # def filter_wrapper(*args, **kwargs):
    #     func_ret = func(*args, **kwargs)
    #     # arg_names = getfullargspec(func).args # Potentially useful for capturing defaults
    #                                             # but some problem getting working with
    #                                             # nested decorators
    #     out = []
    #     if ('filters' in kwargs.keys()):
    #         for f in kwargs['filters']:
    #             expr = parse_jpath(f)
    #             for fr in func_ret:
    #                 matching_fields = [match for match in expr.find(fr)]
    #                 for mf in matching_fields:
    #                     out.append(mf.value)
    #         return out
    #     else:
    #         return func_ret
    #
    # return filter_wrapper


def gen_simple_report(terms, dataframe=True):
    nc = Neo4jConnect("https://pdb.virtualflybrain.org", "neo4j", "neo4j")
    query = """MATCH (n:Class) WHERE n.iri in %s WITH n 
                OPTIONAL MATCH  (n)-[r]->(p:pub) WHERE r.typ = 'syn' 
                WITH n, 
                COLLECT({ synonym: r.synonym, PMID: 'PMID:' + p.PMID, 
                    miniref: p.label}) AS syns 
                OPTIONAL MATCH (n)-[r]-(p:pub) WHERE r.typ = 'def' 
                with n, syns, 
                collect({ PMID: 'PMID:' + p.PMID, miniref: p.label}) as pubs
                OPTIONAL MATCH (n)-[:SUBCLASSOF]->(super:Class)
                RETURN n.short_form as short_form, n.label as label, 
                n.description as description, syns, pubs,
                super.label, super.short_form
                 """ % str(terms)
    q = nc.commit_list([query])
    # add check
    if not q:
        raise Exception('Query failed.')
    if dataframe:
        return pd.DataFrame.from_records(dict_cursor(q))
    return dict_cursor(q)


class QueryWrapper(Neo4jConnect):

    def __init__(self, *args, **kwargs):
        super(QueryWrapper, self).__init__(*args, **kwargs)
        query_json = pkg_resources.resource_filename(
                            "vfb_connect",
                            "resources/VFB_TermInfo_queries.json")
        with open(query_json, 'r') as f:
            self.queries = json.loads(saxutils.unescape(f.read()))

#    def get_sites(self):
#        return

    def _query(self, q):
        qr = self.commit_list([q])
        if not qr:
            raise Exception(f'Query failed: {q}')
        else:
            r = dict_cursor(qr)
            if not r:
                print(f'\033[33mWarning:\033[0m No results returned for query: {q} -> {qr} -> {r}')
                return []
            else:
                return r

    def get_images(self, short_forms: iter, template, image_folder, image_type='swc', stomp=False):
        """Given an iterable of `short_forms` for instances, find all images of specified `image_type`
        registered to `template`. Save these to `image_folder` along with a manifest.tsv.  Return manifest as
        pandas DataFrame.

        :param short_forms: iterable (e.g. list) of VFB IDs of Individuals with images
        :param template: template name
        :param image_folder: folder to save image files & manifest to.
        :param image_type: image type (file extension)
        :param stomp: Overwrite image_folder if already exists.
        :return: Manifest as Pandas DataFrame
        """

        # TODO - make image type into array
        short_forms = list(short_forms)
        manifest = []
        if stomp and os.path.isdir(image_folder):
            if shutil.rmtree.avoids_symlink_attacks:
                shutil.rmtree(image_folder)
            else:
                print(f"\033[33mWarning:\033[0m Not deleting {image_folder}, stomp option not supported on this system for security reasons,"
                              "please delete manually.")
        os.makedirs(image_folder, exist_ok=True)
        inds = self.get_anatomical_individual_TermInfo(short_forms=short_forms, summary=False)
        if not inds:
            print(f"\033[33mWarning:\033[0m No results returned for short_forms: {short_forms}")
        else:
            print(f"Got {len(inds)} results.")
            for i in inds:
                if not ('has_image' in i['term']['core']['types']):
                    continue
                label = i['term']['core']['label']
                image_matches = [x['image'] for x in i['channel_image']]
                if not image_matches:
                    continue
                for imv in image_matches:
                    if imv['template_anatomy']['label'] == template:
                        try:
                            r = requests.get(imv['image_folder'] + '/volume.' + image_type)
                        except requests.exceptions.RequestException as e:
                            print(f"\033[33mWarning:\033[0m No '{image_type}' file found for '{label}'. Error: {e}")
                            continue
                        if not r.ok:
                            print("33mWarning:\033[0m No '%s' file found for '%s'." % (image_type, label))
                            continue
                        filename = re.sub('\W', '_', label) + '.' + image_type
                        with open(image_folder + '/' + filename, 'w') as image_file:
                            image_file.write(r.text)
                        manifest.append(_populate_manifest(instance=i, filename=filename))
        manifest_df = pd.DataFrame.from_records(manifest)
        manifest_df.to_csv(image_folder + '/manifest.tsv', sep='\t')
        return manifest_df

    def get_dbs(self, include_symbols=False):
        """Get a list of available database IDs

        :return: list of VFB IDs."""
        query = "MATCH (i:Individual) " \
                "WHERE i:Site OR i:API " \
                "return i.short_form as id"
        results = self._query(query)
        dbs = [d['id'] for d in results]
        if include_symbols:
            query = "MATCH (i:Individual) " \
                    "WHERE i:Site OR i:API AND exists(i.symbol) and not i.symbol[0] = '' " \
                    "RETURN i.symbol[0] as symbol"
            results = self._query(query)
            dbs.extend([d['symbol'] for d in results if d['symbol']])
        return dbs

    def get_datasets(self, summary=True, return_dataframe=True):
        """
        Generate a report of all datasets available in the system.

        This method retrieves all datasets and returns their information as either full JSON data structures or summaries.
        The results can be returned as a list of dictionaries or as a pandas DataFrame, depending on the `return_dataframe` flag.

        :param summary: Optional. If `True`, returns summary reports instead of full metadata. Default is `True`.
        :param return_dataframe: Optional. If `True` and `summary` is also `True`, returns the results as a pandas DataFrame.
                                Default is `True`.
        :return: A list of terms as nested Python data structures (VFB_json or summary_report_json), or a pandas DataFrame if 
                `return_dataframe` is `True` and `summary` is `True`.
        :rtype: list of dicts or pandas.DataFrame
        """
        dc = self._query("MATCH (ds:DataSet) "
                        "RETURN ds.short_form AS sf")
        short_forms = [d['sf'] for d in dc]
        results = self.get_DataSet_TermInfo(short_forms, summary=summary, return_dataframe=False)
        if return_dataframe and summary:
            return pd.DataFrame.from_records(results)
        return results

    def get_templates(self, summary=True, return_dataframe=True, include_symbols=False):
        """Generate JSON report of all available templates.

            :param summary: Optional.  Returns summary reports if `True`. Default `True`
            :return: Returns a list of terms as nested python data structures following VFB_json or a summary_report_json
            :return type: list of VFB_json or summary_report_json
            """
        dc = self._query("MATCH (i:Individual:Template:Anatomy) "
                         "RETURN i.short_form as sf")
        short_forms = [d['sf'] for d in dc]
        if include_symbols:
            dc = self._query("MATCH (i:Individual:Template:Anatomy) ",
                             "WHERE exists(i.symbol) and not i.symbol[0] = '' "
                             "RETURN i.symbol[0] as s")
            short_forms.extend([d['s'] for d in dc if d['s']])
        return self.get_anatomical_individual_TermInfo(short_forms, summary=summary, return_dataframe=return_dataframe)

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
        vfb_id = list(set(vfb_id))
        match = "MATCH (s:Individual)<-[r:database_cross_reference]-(i:Entity) " \
                "WHERE i.short_form in %s" % str(vfb_id)
        clause1 = ''
        if db:
            clause1 = "AND s.short_form = '%s'" % db
        clause2 = ''
        if id_type:
            clause2 = "AND r.id_type = '%s'" % id_type
        ret = "RETURN i.short_form as key, " \
              "collect({ db: s.short_form, acc: r.accession[0]}) as mapping"
        if reverse_return:
            ret = "RETURN r.accession[0] as key, " \
                  "collect({ db: s.short_form, vfb_id: i.short_form }) as mapping"
        q = ' '.join([match, clause1, clause2, ret])
        dc = self._query(q)
        mapping = {d['key']: d['mapping'] for d in dc}
        unmapped = set(vfb_id)-set(mapping.keys())
        if unmapped:
            print("33mWarning:\033[0m The following IDs do not match DB &/or id_type constraints: %s" % str(unmapped))
        return mapping

    def vfb_id_2_neuprint_bodyID(self, vfb_id, db=''):
        mapping = self.vfb_id_2_xrefs(vfb_id, db=db, reverse_return=True)
        return [int(k) for k, v in mapping.items()]

    def xref_2_vfb_id(self, acc=None, db='', id_type='', reverse_return=False, verbose=False):
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
        if isinstance(acc, str):
            acc = [acc]
        match = "MATCH (s:Individual)<-[r:database_cross_reference]-(i:Entity) WHERE"
        conditions = []
        if not (acc is None):
            acc = [str(a) for a in set(acc)]
            conditions.append("r.accession[0] in %s" % str(acc))
        if db:
            conditions.append("s.short_form = '%s'" % db)
        if id_type:
            conditions.append("r.id_type = '%s'" % id_type)
        condition_clauses = ' AND '.join(conditions)
        ret = "RETURN r.accession[0] as key, " \
              "collect({ db: s.short_form, vfb_id: i.short_form }) as mapping"
        if reverse_return:
            ret = "RETURN i.short_form as key, " \
                  "collect({ db: s.short_form, acc: r.accession[0]}) as mapping"
        q = ' '.join([match, condition_clauses, ret])
        print(q) if verbose else None
        dc = self._query(q)
        print(dc) if verbose else None
        return {d['key']: d['mapping'] for d in dc}

    @batch_query
    def get_terms_by_xref(self, acc, db='', id_type='', summary=True, return_dataframe=True):
        """
        Generate a JSON report for terms specified by a list of cross-reference IDs (xrefs).

        This method maps external database IDs (xrefs) to VFB (Virtual Fly Brain) IDs and then retrieves detailed term 
        information for those VFB IDs. The information can be returned either as a summary or as full term metadata.

        :param acc: An iterable (e.g., a list) of external cross-reference IDs.
        :param db: Optional. Specify the VFB ID (short_form) of an external database to map to. (Use `get_dbs()` to find options).
        :param id_type: Optional. Specify an external ID type to filter the mapping results.
        :param summary: Optional. Returns summary reports if `True`. Default is `True`.
        :param return_dataframe: Optional. Includes related datasets in the report if `True`. Default is `True`.
        :return: A list of term metadata as VFB_json or summary_report_json.
        :rtype: list of dicts
        :raises Warning: If no VFB ID is found for a given xref.
        """
        # Fetch VFB IDs associated with the xref
        vfb_ids = self.xref_2_vfb_id(acc, db=db, id_type=id_type)

        # Extract the list of IDs from the response
        ids_to_query = []
        for key in acc:
            if key not in vfb_ids.keys():
                print("33mWarning:\033[0m No VFB ID found for %s" % key)
            else:
                ids_to_query.append(vfb_ids[key][0]['vfb_id'])

        # Retrieve term information for all IDs
        return self.get_TermInfo(ids_to_query, summary=summary, return_dataframe=False)

    def get_images_by_filename(self, filenames, dataset=None, summary=True, return_dataframe=True):
        """Takes a list of filenames as input and returns a list of image terminfo.
        Optionally restrict by dataset (improves speed)"""
        m = "MATCH (ds:DataSet)<-[has_source]-(ai:Individual)<-[:depicts]" \
            "-(channel:Individual)-[irw:in_register_with]-(tc:Template)"
        w = "WHERE irw.filename[0]in %s" % str([escape_string(f) for f in filenames])
        if dataset:
            w += "AND ds.short_form = '%s'" % dataset
        r = "RETURN ai.short_form"
        dc = self._query(' '.join([m, w, r]))
        return self.get_anatomical_individual_TermInfo([d['ai.short_form']
                                                        for d in dc], summary=summary, return_dataframe=return_dataframe)

    @batch_query
    def get_TermInfo(self, short_forms: iter, summary=True, cache=True, return_dataframe=True, limit=None, verbose=False):
        """
        Generate a JSON report or summary for terms specified by a list of VFB IDs.

        This method retrieves term information for a list of specified VFB IDs (short_forms). It can return either 
        full metadata or a summary of the terms. The results can be returned as a pandas DataFrame if `return_dataframe` 
        is set to `True`.

        :param short_forms: An iterable (e.g., a list) of VFB IDs (short_forms).
        :param summary: Optional. If `True`, returns a summary report instead of full metadata. Default is `True`.
        :param cache: Optional. If `True`, attempts to retrieve cached results before querying. Default is `True`.
        :param return_dataframe: Optional. If `True`, returns the results as a pandas DataFrame. Default is `True`.
        :return: A list of term metadata as VFB_json or summary_report_json, or a pandas DataFrame if `return_dataframe` is `True`.
        :rtype: list of dicts or pandas.DataFrame
        """
        from vfb_connect import vfb
        if cache:
            result = self._get_Cached_TermInfo(short_forms, summary=summary, return_dataframe=False, verbose=verbose)
            cn = len(set(short_forms))
            rn = len(result)
            if rn != cn:
                print(f"\033[33mWarning:\033[0m Cache didn't return all results. Got {rn} out of {cn}") if verbose else None
                missing = set(short_forms) - set([r['term']['core']['short_form'] for r in result])
                print(f"Missing: {missing}") if verbose else None
                for i in missing:
                    print(f"Checking: {i}") if verbose else None
                    if not i in vfb.lookup.values():
                        print(f"\033[33mWarning:\033[0m called a non existant id:{i}")
                        cn -= 1
            if rn == cn:
                print("Using cached results.") if verbose else None
                result = result[:limit] if limit else result
                if summary:
                    results = []
                    for r in result:
                        results.append(_populate_summary(r))
                    return results
                else:
                    return result
            else:
                print(f"\033[33mWarning:\033[0m Cache didn't return all results. Got {rn} out of {cn}. Falling back to slower query.")
                return self.get_TermInfo(short_forms, summary=summary, cache=False, return_dataframe=return_dataframe, limit=limit)
        print("Pulling results from VFB PDB (Neo4j): http://pdb.virtualflybrain.org") if verbose else None
        pre_query = "MATCH (e:Entity) " \
                    "WHERE e.short_form in %s " \
                    "RETURN e.short_form as short_form, labels(e) as labs " % str(short_forms)
        r = self._query(pre_query)
        out = []
        for e in r:
            if 'class' in e['labs'] and 'Neuron' in e['labs']:
                print(f"Getting Neuron: {e['short_form']}") if verbose else None
                out.extend(self.get_neuron_class_TermInfo([e['short_form']], summary=summary, return_dataframe=False))
            elif 'class' in e['labs'] and 'Split' in e['labs']:
                print(f"Getting Split: {e['short_form']}") if verbose else None
                out.extend(self.get_split_class_TermInfo([e['short_form']], summary=summary, return_dataframe=False))
            if 'Class' in e['labs']:
                print
                out.extend(self.get_type_TermInfo([e['short_form']], summary=summary, return_dataframe=False))
            elif 'DataSet' in e['labs']:
                print(f"Getting DataSet: {e['short_form']}") if verbose else None
                out.extend(self.get_DataSet_TermInfo([e['short_form']], summary=summary, return_dataframe=False))
            elif 'License' in e['labs']:
                print(f"Getting License: {e['short_form']}") if verbose else None
                out.extend(self.get_License_TermInfo([e['short_form']], summary=summary, return_dataframe=False))
            elif 'Template' in e['labs']:
                print(f"Getting Template: {e['short_form']}") if verbose else None
                out.extend(self.get_template_TermInfo([e['short_form']], summary=summary, return_dataframe=False))
            elif 'pub' in e['labs']:
                print(f"Getting Pub: {e['short_form']}") if verbose else None
                out.extend(self.get_pub_TermInfo([e['short_form']], summary=summary, return_dataframe=False))
            elif 'Individual' in e['labs']:
                print(f"Getting Individual: {e['short_form']}") if verbose else None
                out.extend(self.get_anatomical_individual_TermInfo([e['short_form']], summary=summary, return_dataframe=False))
        print(f"Got {len(out)} results.") if verbose else None
        return out[:limit] if limit else out

    @batch_query
    def _get_Cached_TermInfo(self, short_forms: iter, summary=True, return_dataframe=True, verbose=False):
        # Flatten the list of short_forms in case it's nested
        if isinstance(short_forms, str):
            short_forms = [short_forms]
        if isinstance(short_forms, list):
            short_forms = list(chain.from_iterable(short_forms)) if any(isinstance(i, list) for i in short_forms) else short_forms
        print(f"Checking cache for results: short_forms={short_forms}") if verbose else None
        print(f"Looking for {len(short_forms)} results.") if verbose else None
        results = self._serialize_solr_output(vfb_solr.search('*', **{'fl': 'term_info','df': 'id', 'defType': 'edismax', 'q.op': 'OR','rows': len(short_forms)+10,'fq':'{!terms f=id}'+ ','.join(short_forms)}))
        print(f"Got {len(results)} results.") if verbose else None
        if len(short_forms) != len(results):
            print(f"Warning: Cache didn't return all results. Got {len(results)} out of {len(short_forms)}") if verbose else None
            missing = set(short_forms) - set([r['term']['core']['short_form'] for r in results])
            print(f"Missing: {missing}") if verbose else None
        return results



    @batch_query
    def _get_TermInfo(self, short_forms: iter, typ, show_query=False, summary=True, return_dataframe=True):
        short_forms = list(short_forms)
        sfl = "', '".join(short_forms)
        qs = Template(self.queries[typ]).substitute(ID=sfl)
        if show_query:
            print(qs)
        if summary:
            return self._termInfo_2_summary(self._query(qs), typ=typ)
        else:
            return self._query(qs)

    def _get_anatomical_individual_TermInfo_by_type(self, classification, summary=True, return_dataframe=True, limit=None, verbose=False):
        # TODO use the limit parameter
        typ = 'Get JSON for Individual:Anatomy_by_type'
        qs = Template(self.queries[typ]).substitute(ID=classification)
        if summary:
            return self._termInfo_2_summary(self._query(qs), typ='Get JSON for Individual', verbose=verbose)
        else:
            return self._query(qs)

    def _termInfo_2_summary(self, TermInfo, typ, verbose=False):
        # type_2_summary = {
        #     'Get JSON for Individual': '_populate_instance_summary_tab',
        #     'Get JSON for Class': '_populate_anatomical_entity_summary',
        # }
        dc = []
        for r in TermInfo:
            if 'Class' in typ:
                print(f"Getting Class: {r['short_form']}") if verbose else None
                dc.append(_populate_anatomical_entity_summary(r))
            elif typ == 'Get JSON for DataSet':
                print(f"Getting DataSet: {r['short_form']}") if verbose else None
                dc.append(_populate_dataset_summary_tab(r))
            else:
                print(f"Getting Individual: {r['short_form']}") if verbose else None
                dc.append(_populate_instance_summary_tab(r))
        print(f"Got {len(dc)} results.") if verbose else None
        return dc
    
    def _query_2_summary(self, TermInfo, typ, verbose=False):
        # type_2_summary = {
        #     'Get JSON for Individual': '_populate_instance_summary_tab',
        #     'Get JSON for Class': '_populate_anatomical_entity_summary',
        # }
        dc = []
        for r in TermInfo:
            if 'Class' in typ:
                print(f"Getting Class: {r['short_form']}") if verbose else None
                dc.append(_populate_anatomical_entity_summary(r))
            elif typ == 'Get JSON for DataSet':
                print(f"Getting DataSet: {r['short_form']}") if verbose else None
                dc.append(_populate_dataset_summary_tab(r))
            else:
                print(f"Getting Individual: {r['short_form']}") if verbose else None
                dc.append(_populate_instance_summary_tab(r))
        print(f"Got {len(dc)} results.") if verbose else None
        return dc

    def _serialize_solr_output(self, results):
        """
        Serialize the sanitized dictionary to JSON for all documents returned by Solr.

        :param results: The results object containing multiple documents from Solr.
        :return: A list of deserialized JSON objects.
        """
        serialized_results = []

        for doc in results.docs:
            # Ensure 'term_info' exists and is not empty
            if 'term_info' in doc and doc['term_info']:
                json_string = doc['term_info'][0]
                result = json.loads(json_string)
                serialized_results.append(result)
        return serialized_results

    def get_anatomical_individual_TermInfo(self, short_forms, summary=True, return_dataframe=True):
        """
        Generate JSON reports for anatomical individuals from a list of VFB IDs (short_forms)

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of anatomical individuals
        :param summary: Optional.  Returns summary reports if `True`. Default `True`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for Individual', summary=summary, return_dataframe=return_dataframe)

    def get_type_TermInfo(self, short_forms, summary=True, return_dataframe=True):
        """
        Generate JSON reports for types from a list of VFB IDs (short_forms) of classes/types.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of types
        :param summary: Optional.  Returns summary reports if `True`. Default `True`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for Class', summary=summary, return_dataframe=return_dataframe)

    def get_neuron_class_TermInfo(self, short_forms, summary=True, return_dataframe=True):
        """
        Generate JSON reports for neuron classes from a list of VFB IDs (short_forms) of neuron classes.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of neuron classes
        :param summary: Optional.  Returns summary reports if `True`. Default `True`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for Neuron Class', summary=summary, return_dataframe=return_dataframe)

    def get_split_class_TermInfo(self, short_forms, summary=True, return_dataframe=True):
        """
        Generate JSON reports for split classes from a list of VFB IDs (short_forms) of split classes.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of split classes
        :param summary: Optional.  Returns summary reports if `True`. Default `True`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for Split Class', summary=summary, return_dataframe=return_dataframe)

    def get_DataSet_TermInfo(self, short_forms, summary=True, return_dataframe=True):
        """
        Generate JSON reports for datasets from a list of VFB IDs (short_forms) of datasets.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of datasets
        :param summary: Optional.  Returns summary reports if `True`. Default `True`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for DataSet', summary=summary, return_dataframe=return_dataframe)

    def get_license_TermInfo(self, short_forms, summary=True, return_dataframe=True):
        """
        Generate JSON reports for licenses from a list of VFB IDs (short_forms) of licenses.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of licenses
        :param summary: Optional.  Returns summary reports if `True`. Default `True`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for License', summary=summary, return_dataframe=return_dataframe)

    def get_template_TermInfo(self, short_forms, summary=True, return_dataframe=True):
        """
        Generate JSON reports for templates from a list of VFB IDs (short_forms) of templates.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of templates
        :param summary: Optional.  Returns summary reports if `True`. Default `True`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for Template', summary=summary, return_dataframe=return_dataframe)

    def get_pub_TermInfo(self, short_forms, summary=True, return_dataframe=True):
        """
        Generate JSON reports for publications from a list of VFB IDs (short_forms) of publications.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of publications
        :param summary: Optional.  Returns summary reports if `True`. Default `True`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for pub', summary=summary, return_dataframe=return_dataframe)

    def get_anatomy_by_type_TermInfo(self, short_forms, summary=True, return_dataframe=True):
        """
        Generate JSON reports for anatomical individuals by type from a list of VFB IDs (short_forms).

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of anatomical types
        :param summary: Optional.  Returns summary reports if `True`. Default `True`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for Individual:Anatomy_by_type', summary=summary, return_dataframe=return_dataframe)

