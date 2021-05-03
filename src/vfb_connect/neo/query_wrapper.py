import json
import os
import re
import shutil
import warnings
from inspect import getfullargspec
from string import Template
from xml.sax import saxutils
import pandas as pd
import pkg_resources
import requests
from functools import wraps


# from jsonpath_rw import parse as parse_jpath
from vfb_connect.neo.neo4j_tools import chunks, Neo4jConnect, dict_cursor, escape_string



def batch_query(func):
    # Assumes first arg is to be batches and that return value is list. Only works on class methods.
    # There has to be a better way to work with the values of args and kwargs than this!!!!
    @wraps(func)  # Boilerplate required for Sphinx autodoc
    def wrapper_batch(*args, **kwargs):
        arg_names = getfullargspec(func).args
        if len(args) > 1:
            arg1v = args[1]
            arg1typ = 'a'
        else:
            arg1v = kwargs[arg_names[1]]
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
    d['symbol'] = TermInfo['term']['core']['symbol']
    d['id'] = TermInfo['term']['core']['short_form']
    d['tags'] = '|'.join(TermInfo['term']['core']['types'])
    return d


def _populate_anatomical_entity_summary(TermInfo):
    d = _populate_minimal_summary_tab(TermInfo)
#   d['parents_symbol'] = pop_from_jpath("$.parents[*].symbol", TermInfo)
#   d['parents_label'] = pop_from_jpath("$.parents[*].label", TermInfo)

    d['parents_label'] = '|'.join([str(p['label']) for p in TermInfo['parents']])
#    d['parents_id'] = pop_from_jpath("$.parents[*].short_form", TermInfo)
    d['parents_id'] = '|'.join([str(p['short_form']) for p in TermInfo['parents']])

    return d


def _populate_instance_summary_tab(TermInfo):
    d = _populate_anatomical_entity_summary(TermInfo)
#    site_expr = "$.xrefs.[*].site.short_form"
#    acc_expr = "$.xrefs.[*].accession"
#    is_data_source_expr = "$.xrefs.[*].is_data_source"
#   sites = pop_from_jpath(site_expr, TermInfo, join=False)
    sites = [str(p['site']['short_form']) for p in TermInfo['xrefs']]
    accessions = [str(p['accession']) for p in TermInfo['xrefs']
                           if 'accession' in p.keys()]
    is_data_source = [p['is_data_source'] for p in TermInfo['xrefs']
                               if 'is_data_source' in p.keys()]

    i = 0
    data_sources = []
    ds_accessions = []
    for ids in is_data_source:
        if ids:
            data_sources.append(sites[i])
            ds_accessions.append(accessions[i])
        i += 1
    d['data_source'] = '|'.join(data_sources)
    d['accession'] = '|'.join(ds_accessions)
    d['templates'] = '|'.join([str(x['image']['template_anatomy']['label']) for x in TermInfo['channel_image']])
    d['dataset'] = '|'.join([str(x['dataset']['core']['short_form']) for x in TermInfo['dataset_license']])
    d['license'] = '|'.join([str(x['license']['link']) for x in TermInfo['dataset_license']
                             if 'link' in x['license'].keys()])
    return d


def _populate_dataset_summary_tab(TermInfo):
    d = _populate_minimal_summary_tab(TermInfo)
    d['description'] = TermInfo['term']['description']
    d['miniref'] = '|'.join([str(x['core']['label']) for x in TermInfo['pubs']])
    d['FlyBase'] = '|'.join([str(x['FlyBase']) for x in TermInfo['pubs'] if 'FlyBase' in x])
    d['PMID'] = '|'.join([str(x['PubMed']) for x in TermInfo['pubs'] if 'PubMed' in x])
    d['DOI'] = '|'.join([str(x['DOI']) for x in TermInfo['pubs'] if 'PubMed' in x])
    return d


def _populate_manifest(filename, instance):
    d = _populate_instance_summary_tab(instance)
    d['filename'] = filename
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


def gen_simple_report(terms):
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
            raise Exception('Query failed.')
        else:
            r = dict_cursor(qr)
            if not r:
                warnings.warn('No results returned')
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
                warnings.warn("Not deleting %s, stomp option not supported on this system for security reasons,"
                              "please delete manually." % image_folder)
        os.mkdir(image_folder)
        inds = self.get_anatomical_individual_TermInfo(short_forms=short_forms)
        for i in inds:
            if not ('has_image' in i['term']['core']['types']):
                continue
            label = i['term']['core']['label']
            image_matches = [x['image'] for x in i['channel_image']]
            if not image_matches:
                continue
            for imv in image_matches:
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

    def get_dbs(self):
        """Get a list of available database IDs

        :return: list of VFB IDs."""
        query = "MATCH (i:Individual) " \
                "WHERE 'Site' in labels(i) OR 'API' in labels(i)" \
                "return i.short_form"
        return [d['i.short_form'] for d in self._query(query)]

    def get_datasets(self, summary=False):
        """Generate JSON report of all datsets.

            :param summary: Optional.  Returns summary reports if `True`. Default `False`
            :return: Returns a list of terms as nested python data structures following VFB_json or a summary_report_json
            :return type: list of VFB_json or summary_report_json
            """

        dc = self._query("MATCH (ds:DataSet) "
                         "RETURN ds.short_form AS sf")
        short_forms = [d['sf'] for d in dc]
        return self.get_DataSet_TermInfo(short_forms, summary=summary)

    def get_templates(self, summary=False):
        """Generate JSON report of all available templates.

            :param summary: Optional.  Returns summary reports if `True`. Default `False`
            :return: Returns a list of terms as nested python data structures following VFB_json or a summary_report_json
            :return type: list of VFB_json or summary_report_json
            """
        dc = self._query("MATCH (i:Individual:Template:Anatomy) "
                         "RETURN i.short_form as sf")
        short_forms = [d['sf'] for d in dc]
        return self.get_anatomical_individual_TermInfo(short_forms, summary=summary)

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
            warnings.warn("The following IDs do not match DB &/or id_type constraints: %s" % str(unmapped))
        return mapping

    def vfb_id_2_neuprint_bodyID(self, vfb_id, db=''):
        mapping = self.vfb_id_2_xrefs(vfb_id, db=db, reverse_return=True)
        return [int(k) for k, v in mapping.items()]

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
#        print(q)
        dc = self._query(q)
        return {d['key']: d['mapping'] for d in dc}

    @batch_query
    def get_terms_by_xref(self, acc, db='', id_type=''):
        """
        Generate JSON report for terms specified by a list of IDs

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms)
        :return: list of term metadata as VFB_json
        """
        return self.get_TermInfo(list(self.xref_2_vfb_id(acc,
                                                         db=db,
                                                         id_type=id_type,
                                                         reverse_return=True).keys()))

    def get_images_by_filename(self, filenames, dataset=None):
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
                                                        for d in dc])

    @batch_query
    def get_TermInfo(self, short_forms: iter):
        """Generate JSON report for terms specified by a list of IDs

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms)
        :param db: optionally specify the VFB id (short_form) of external DB.
        :param id_type: optionally specify an external id_type
        :return: list of term metadata as VFB_json

        """
        pre_query = "MATCH (e:Entity) " \
                    "WHERE e.short_form in %s " \
                    "RETURN e.short_form as short_form, labels(e) as labs " % str(short_forms)
        r = self._query(pre_query)
        out = []
        for e in r:
            if 'Class' in e['labs']:
                out.extend(self.get_type_TermInfo([e['short_form']]))
            elif 'Individual' in e['labs'] and 'Anatomy' in e['labs']:
                out.extend(self.get_anatomical_individual_TermInfo([e['short_form']]))
            elif 'DataSet' in e['labs']:
                out.extend(self.get_DataSet_TermInfo([e['short_form']]))
        return out

    @batch_query
    def _get_TermInfo(self, short_forms: iter, typ, show_query=False, summary=False):
        short_forms = list(short_forms)
        sfl = "', '".join(short_forms)
        qs = Template(self.queries[typ]).substitute(ID=sfl)
        if show_query:
            print(qs)
        if summary:
            return self._termInfo_2_summary(self._query(qs), typ=typ)
        else:
            return self._query(qs)

    def _get_anatomical_individual_TermInfo_by_type(self, classification, summary=False):
        typ = 'Get JSON for Individual:Anatomy_by_type'
        qs = Template(self.queries[typ]).substitute(ID=classification)
        if summary:
            return self._termInfo_2_summary(self._query(qs), typ='Get JSON for Individual:Anatomy')
        else:
            return self._query(qs)

    def _termInfo_2_summary(self, TermInfo, typ):
        # type_2_summary = {
        #     'Get JSON for Individual:Anatomy': '_populate_instance_summary_tab',
        #     'Get JSON for Class': '_populate_anatomical_entity_summary',
        # }
        dc = []
        for r in TermInfo:
            if typ == 'Get JSON for Individual:Anatomy':
                dc.append(_populate_instance_summary_tab(r))
            elif typ == 'Get JSON for Class':
                dc.append(_populate_anatomical_entity_summary(r))
            elif typ == 'Get JSON for DataSet':
                dc.append(_populate_dataset_summary_tab(r))
        return dc

    def get_anatomical_individual_TermInfo(self, short_forms, summary=False):
        """
        Generate JSON reports for anatomical individuals from a list of VFB IDs (short_forms)

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of anatomical individuals
        :param summary: Optional.  Returns summary reports if `True`. Default `False`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for Individual:Anatomy', summary=summary)

    def get_type_TermInfo(self, short_forms, summary=False):
        """
        Generate JSON reports for types from a list of VFB IDs (short_forms) of classes/types.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of types
        :param summary: Optional.  Returns summary reports if `True`. Default `False`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for Class', summary=summary)

    def get_DataSet_TermInfo(self, short_forms, summary=False):
        """
        Generate JSON reports for types from a list of VFB IDs (short_forms) of DataSets.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of types
        :param summary: Optional.  Returns summary reports if `True`. Default `False`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for DataSet', summary=summary)

    def get_template_TermInfo(self, short_forms):
        """
        Generate JSON reports for types from a list of VFB IDs (short_forms) of templates.

        :param short_forms: An iterable (e.g. a list) of VFB IDs (short_forms) of types
        :param summary: Optional.  Returns summary reports if `True`. Default `False`
        :rtype: list of VFB_json or summary_report_json
        """
        return self._get_TermInfo(short_forms, typ='Get JSON for Template')