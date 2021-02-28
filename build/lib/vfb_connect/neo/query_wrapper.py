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
from jsonpath_rw import parse as parse_jpath
from vfb_connect.neo.neo4j_tools import chunks, Neo4jConnect, dict_cursor, escape_string



def batch_query(func):
    # Assumes first arg is to be batches and that return value is list. Only works on class methods.
    # There has to be a better way to work with the values of args and kwargs than this!!!!
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


def pop_from_jpath(jpath, json, join=True):
    expr = parse_jpath(jpath)
    if join:
        return '|'.join([match.value for match in expr.find(json)])
    else:
        return [match.value for match in expr.find(json)]


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
    d['parents_label'] = pop_from_jpath("$.parents[*].label", TermInfo)
    d['parents_id'] = pop_from_jpath("$.parents[*].short_form", TermInfo)
    return d


def _populate_instance_summary_tab(TermInfo):
    d = _populate_anatomical_entity_summary(TermInfo)
    site_expr = "$.xrefs.[*].site.short_form"
    acc_expr = "$.xrefs.[*].accession"
    is_data_source_expr = "$.xrefs.[*].is_data_source"
    sites = pop_from_jpath(site_expr, TermInfo, join=False)
    accessions = pop_from_jpath(acc_expr, TermInfo, join=False)
    is_data_source = pop_from_jpath(is_data_source_expr, TermInfo, join=False)
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
    d['templates'] = pop_from_jpath("$.channel_image.[*].image.template_anatomy.label", TermInfo)
    d['dataset'] = pop_from_jpath("$.dataset_license.[*].dataset.core.short_form", TermInfo)
    d['license'] = pop_from_jpath("$.dataset_license.[*].license.link", TermInfo)
    return d


def _populate_dataset_summary_tab(TermInfo):
    d = _populate_minimal_summary_tab(TermInfo)


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
        """Given an array of `short_forms` for instances, find all images of specified `image_type`
        registered to `template`. Save these to `image_folder` along with a manifest.tsv.  Return manifest as
        pandas DataFrame."""
        # TODO - make image type into array
        short_forms = list(short_forms)
        image_expr = parse_jpath("$.channel_image.[*].image")
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
            image_matches = image_expr.find(i)
            if not ([match.value for match in image_matches]):
                continue
            for im in image_matches:
                imv = im.value
                if imv['template_anatomy']['label'] == template:
                    if not image_type == 'obj':
                        r = requests.get(imv['image_folder'] + '/volume.' + image_type)
                        ### Slightly dodgy warning - could mask network errors
                        if not r.ok:
                            warnings.warn("No '%s' file found for '%s'." % (image_type, label))
                            continue
                    else:
                        r = requests.get(imv['image_folder'] + '/volume_man.' + image_type)
                        if not r.ok:
                            r = requests.get(imv['image_folder'] + '/volume.' + image_type)
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
        query = "MATCH (i:Individual) " \
                "WHERE 'Site' in labels(i) OR 'API' in labels(i)" \
                "return i.short_form"
        return [d['i.short_form'] for d in self._query(query)]

    def get_templates(self):
        query = "MATCH (i:Individual:Template:Anatomy) " \
                "RETURN i.short_form"
        return self._get_TermInfo([d['i.short_form'] for d in self._query(query)], typ='Individual')

    def vfb_id_2_xrefs(self, vfb_id: iter, db='', id_type='', reverse_return=False):
        """Map a list of node short_form IDs in VFB to external DB IDs
        Args:
         vfb_id: list of short_form IDs of nodes in the VFB KB
         db: {optional} database identifier (short_form) in VFB
         id_type: {optional} name of external id type (e.g. bodyId)
        Return if `reverse_return` is False:
            dict { VFB_id : [{ db: <db> : acc : <acc> }
        Return if `reverse_return` is True:
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
        """Map an external ID (acc) to a VFB_id
        args:
            acc: list of external DB IDs (accessions)
            db: {optional} database identifier (short_form) in VFB
            id_type: {optional} name of external id type (e.g. bodyId)
        Return:
            dict { VFB_id : [{ db: <db> : acc : <acc> }]}"""
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
        """Get terms in VFB corresponding to a
            acc: list of external DB IDs (accession)
            db: {optional} database identifier (short_form) in VFB
            id_type: {optional} name of external id type (e.g. bodyId)"""
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
    def get_TermInfo(self, short_forms):
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
        return dc

    def get_anatomical_individual_TermInfo(self, short_forms, summary=False):
        return self._get_TermInfo(short_forms, typ='Get JSON for Individual:Anatomy', summary=summary)

    def get_type_TermInfo(self, short_forms, summary=False):
        return self._get_TermInfo(short_forms, typ='Get JSON for Class', summary=summary)

    def get_DataSet_TermInfo(self, short_forms, summary=False):
        return self._get_TermInfo(short_forms, typ='Get JSON for DataSet')

    def get_template_TermInfo(self, short_forms, summary=False):
        return self._get_TermInfo(short_forms, typ='Get JSON for Template')
