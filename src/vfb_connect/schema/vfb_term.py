import json
import os
import sys
from typing import List, Optional, Union
import navis
import numpy as np
import pandas
import requests
import tempfile

import webbrowser

def is_notebook():
    """Check if the environment is a Jupyter notebook."""
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True  # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
    except NameError:
        return False  # Probably standard Python interpreter

if is_notebook():
    try:
        from tqdm.notebook import tqdm  # Use notebook-specific tqdm if available
    except ImportError:
        from tqdm import tqdm
else:
    from tqdm import tqdm

class MinimalEntityInfo:
    def __init__(self, short_form: str, iri: str, label: str, types: List[str], unique_facets: Optional[List[str]] = None, symbol: Optional[str] = None):
        self.short_form = short_form
        self.iri = iri
        self.label = label
        self.types = types
        self.unique_facets = unique_facets
        self.symbol = symbol
        self.name = self.get_name()

    def get_name(self):
        return self.symbol if self.symbol else self.label

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return f"MinimalEntityInfo(name={self.name}, short_form={self.short_form})"


class MinimalEdgeInfo:
    def __init__(self, iri: str, label: str, type: str, short_form: Optional[str] = None, confidence_value: Optional[str] = None, database_cross_reference: Optional[List[str]] = None):
        self.short_form = short_form
        self.iri = iri
        self.label = label
        self.type = type
        self.confidence_value = confidence_value if confidence_value else None
        self.database_cross_reference = database_cross_reference

    def __repr__(self):
        if self.confidence_value and self.database_cross_reference:
            return f"MinimalEdgeInfo(label={self.label}, confidence={self.confidence_value}, reference={'; '.join(self.database_cross_reference)})"
        if self.confidence_value:
            return f"MinimalEdgeInfo(label={self.label}, confidence={self.confidence_value})"
        if self.database_cross_reference:
            return f"MinimalEdgeInfo(label={self.label}, reference={'; '.join(self.database_cross_reference)})"
        return f"MinimalEdgeInfo(label={self.label}, type={self.type})"


class Term:
    def __init__(self, core: MinimalEntityInfo, description: Optional[List[str]] = None, comment: Optional[List[str]] = None, link: Optional[str] = None, icon: Optional[str] = None):
        if isinstance(core, dict):
            self.core = MinimalEntityInfo(**core)
        elif isinstance(core, MinimalEntityInfo):
            self.core = core
        else:
            raise ValueError("core must be a MinimalEntityInfo object")
        self.description = ", ".join(description) if description else ""
        self.comment = ", ".join(comment) if comment else ""
        self.link = link if link else "https://n2t.net/vfb:" + self.core.short_form
        self.icon = icon if icon else ""

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        return f"Term(term={repr(self.core)}, link={self.link})"

    def open(self, verbose=False):
        print(f"Opening {self.link}...") if verbose else None
        webbrowser.open(self.link)

class Publication:
    def __init__(self, core: MinimalEntityInfo, description: Optional[List[str]] = None, comment: Optional[List[str]] = None, link: Optional[str] = None, icon: Optional[str] = None, FlyBase: Optional[str] = None, PubMed: Optional[str] = None, DOI: Optional[str] = None):
        if isinstance(core, dict):
            self.core = MinimalEntityInfo(**core)
        elif isinstance(core, MinimalEntityInfo):
            self.core = core
        else:
            raise ValueError("core must be a MinimalEntityInfo object")
        if description:
            self.description = ", ".join(description) if description else ""
        if comment:
            self.comment = ", ".join(comment) if comment else ""
        self.link = self.core.get('iri', "https://n2t.net/vfb:" + self.core['short_form'])
        if FlyBase:
            self.FlyBase = FlyBase
        if PubMed:
            self.PubMed = PubMed
        if DOI:
            self.DOI = DOI

    def __repr__(self):
        return f"Publication(pub={repr(self.core)}, link={self.link})"
    
    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")


class Syn:
    def __init__(self, scope: str, label: str, type: Optional[str] = None):
        self.scope = scope
        self.label = label
        if type:
            self.type = type

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        if hasattr(self, 'type'):
            return f"Syn(scope={self.scope}, label={self.label}, type={self.type})"
        if self.scope:
            return f"Syn(scope={self.scope}, label={self.label})"
        return f"Syn(label={self.label})"
class Synonym:
    def __init__(self, synonym: Syn, pub: Optional[Publication] = None):
        if isinstance(synonym, dict):
            self.synonym = Syn(**synonym)
        elif isinstance(synonym, Syn):
            self.synonym = synonym
        else:
            raise ValueError("synonym must be a Syn object")
        if pub and pub.core.short_form != 'Unattributed':
            if isinstance(pub, dict):
                self.pub = Publication(**pub)
            elif isinstance(pub, Publication):
                self.pub = pub
            else:
                raise ValueError("pub must be a Publication object")

    def __repr__(self):
        if hasattr(self, 'pub'):
            return f"Synonym(synonym={repr(self.synonym)}, pub={repr(self.pub)})"
        return f"Synonym(synonym={repr(self.synonym)})"

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")


class Xref:
    def __init__(self, core: MinimalEntityInfo, is_data_source: bool = False, link: Optional[str] = None, icon: Optional[str] = None, accession: Optional[str] = None, link_text: Optional[str] = None, homepage: Optional[str] = None):
        if isinstance(core, dict):
            self.core = MinimalEntityInfo(**core)
        elif isinstance(core, MinimalEntityInfo):
            self.core = core
        else:
            raise ValueError("core must be a MinimalEntityInfo object")
        self.is_data_source = is_data_source
        if link:
            self.link = link
        if icon:
            self.icon = icon
        if accession:
            self.accession = accession
        if link_text:
            self.link_text = link_text
        if homepage:
            self.homepage = homepage

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")


    def __repr__(self):
        return f"Xref(link_text={self.link_text if hasattr(self, 'link_text') else self.core.name}, link={self.link if hasattr(self,'link') else self.homepage if hasattr(self,'homepage') else self.core.iri}, accession={self.accession if hasattr(self,'accession') else self.core.short_form})"

class Rel:
    def __init__(self, relation: MinimalEdgeInfo, object: str):
        self.relation = relation
        self._object_id = object
        self._object = None

    @property
    def object(self):
        if self._object is None:
            self._object = VFBTerm(id=self._object_id)
        return self._object
    
    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        return f"Rel(relation={repr(self.relation)}, object={repr(self.object)})"


class Image:
    def __init__(self, image_folder: str, template_channel: MinimalEntityInfo, template_anatomy: MinimalEntityInfo, index: Optional[List[int]] = None, image_nrrd: Optional[str] = None, image_thumbnail: Optional[str] = None, image_swc: Optional[str] = None, image_obj: Optional[str] = None, image_wlz: Optional[str] = None):
        self.image_folder = image_folder
        self.template_channel = template_channel
        self.template_anatomy = template_anatomy
        self.index = index if index else None
        self.image_nrrd = image_nrrd if image_nrrd else None
        self.image_thumbnail = image_thumbnail if image_thumbnail else None
        self.image_swc = image_swc if image_swc else None
        self.image_obj = image_obj if image_obj else None
        self.image_wlz = image_wlz if image_wlz else None

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")


    def __repr__(self):
        return f"Image(image_thmbnail={self.image_thumbnail})"

    def get_skeleton(self, verbose=False):
        if self.image_swc:
            return navis.read_swc(self.image_swc)
        if self.image_obj and 'volume_man.obj' in self.image_obj:
            local_file = self.create_temp_file(suffix=".obj", verbose=verbose)
            self.download_file(self.image_obj, local_file.name, verbose=verbose)
            mesh = navis.read_mesh(local_file.name, output='neuron', errors='ignore' if not verbose else 'log')
            self.delete_temp_file(local_file.name, verbose=verbose)
            if mesh:
                return mesh
        if self.image_nrrd:
            local_file = self.create_temp_file(suffix=".nrrd", verbose=verbose)
            self.download_file(self.image_nrrd, local_file.name, verbose=verbose)
            dotprops = navis.read_nrrd(local_file.name, output='dotprops', errors='ignore' if not verbose else 'log')
            self.delete_temp_file(local_file.name, verbose=verbose)
            if dotprops:
                return dotprops
        return None

    def get_mesh(self, verbose=False, output='neuron'):
        if self.image_obj and 'volume_man.obj' in self.image_obj:
            print("Reading mesh from ", self.image_obj) if verbose else None
            local_file = self.create_temp_file(suffix=".obj", verbose=verbose)
            self.download_file(self.image_obj, local_file.name, verbose=verbose)
            mesh = navis.read_mesh(local_file.name, output=output, errors='ignore' if not verbose else 'log')
            self.delete_temp_file(local_file.name, verbose=verbose)
            if mesh:
                return mesh
        if self.image_swc:
            print("Falling back to skeleton version from ", self.image_swc) if verbose else None
            return navis.read_swc(self.image_swc, read_meta=False, errors='ignore' if not verbose else 'log')
        return None

    def get_volume(self, verbose=False):
        if self.image_nrrd:
            print("Reading volume from ", self.image_nrrd) if verbose else None
            local_file = self.create_temp_file(suffix=".nrrd", verbose=verbose)
            self.download_file(self.image_nrrd, local_file.name, verbose=verbose)
            mesh = navis.read_nrrd(local_file.name, output='voxels', errors='ignore' if not verbose else 'log')
            self.delete_temp_file(local_file.name, verbose=verbose)
            if mesh:
                return mesh
        else:
            print("No nrrd file associated") if verbose else None
        return None

    def create_temp_file(self, suffix=".nrrd", delete=False, verbose=False):
        # Create a temporary file with a specific extension
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=delete)
        print(f"Temporary file created: {temp_file.name}") if verbose else None
        return temp_file

    def download_file(self, url, local_filename, verbose=False):
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return local_filename
        else:
            print(f"Failed to download file from {url}") if verbose else None
            return None

    def delete_temp_file(self, file_path, verbose=False):
        """
        Deletes the temporary file at the specified path.

        :param file_path: The path to the temporary file to be deleted.
        :return: None
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Temporary file deleted: {file_path}") if verbose else None
            else:
                print(f"File not found: {file_path}") if verbose else None
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}") if verbose else None

    def show(self, transparent=False, verbose=False):
        from PIL import Image
        import requests
        from io import BytesIO

        try:
            print("Fetching image: ", self.image_thumbnail if not transparent else self.image_thumbnail.replace('thumbnail.png', 'thumbnailT.png')) if verbose else None

            # Fetch the image
            response = requests.get(self.image_thumbnail if not transparent else self.image_thumbnail.replace('thumbnail.png', 'thumbnailT.png'))
            print("Response: ", response) if verbose else None
            print("Content: ", response.content) if verbose else None

            img = Image.open(BytesIO(response.content))

            # Try to display the image in a notebook environment
            try:
                from IPython.display import display
                print("Displaying thumbnail in notebook...") if verbose else None
                display(img)
            except ImportError:
                # If not in a notebook, fall back to PIL's image viewer
                print("IPython not available, using PIL to show the image.") if verbose else None
                img.show()

        except Exception as e:
            print("Error displaying thumbnail: ", e)


class ChannelImage:
    def __init__(self, image: Image, channel: MinimalEntityInfo, imaging_technique: Optional[MinimalEntityInfo] = None):
        self.image = image
        self.channel = channel
        self.imaging_technique = imaging_technique

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        return f"ChannelImage(image={repr(self.image)}, imaging_technique={self.imaging_technique.name}, aligned_to={self.image.template_anatomy.name})"


class AnatomyChannelImage:
    def __init__(self, anatomy: MinimalEntityInfo, channel_image: ChannelImage):
        self.anatomy = anatomy
        self.channel_image = channel_image

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        return f"AnatomyChannelImage(anatomy={self.anatomy})"


class VFBTerm:
    def __init__(self, id=None, term: Optional[Term] = None, related_terms: Optional[List[Rel]] = None, channel_images: Optional[List[ChannelImage]] = None, parents: Optional[List[str]] = None, regions: Optional[List[str]] = None, counts: Optional[dict] = None, publications: Optional[List[Publication]] = None, license: Optional[Term] = None, xrefs: Optional[List[Xref]] = None, dataset: Optional[List[str]] = None, synonyms: Optional[Synonym] = None, verbose=False):
        from vfb_connect import vfb
        self.vfb = vfb
        if id is not None:
            if isinstance(id, list):
                id = id[0]
            self.id = id
            self.name = "unresolved"
            json_data = self.vfb.get_TermInfo([id], summary=False)
            print("Got JSON data: ", json_data) if verbose else None
            if json_data is None:
                print("No JSON data found for ", id) if verbose else None
            else:
                if isinstance(json_data, list): # If multiple terms are returned
                    print("Multiple terms found for ", id) if verbose else None
                    term_object = create_vfbterm_from_json(json_data[0], verbose=verbose)
                    self.__dict__.update(term_object.__dict__)  # Copy attributes from the fetched term object
                elif isinstance(json_data, dict):
                    term_object = create_vfbterm_from_json(json_data, verbose=verbose)
                    self.__dict__.update(term_object.__dict__)
                elif isinstance(json_data, str):
                    print("String found for ", id) if verbose else None
                    term_object = create_vfbterm_from_json(json_data, verbose=verbose)
                    self.__dict__.update(term_object.__dict__)
                elif isinstance(json_data, VFBTerm):
                    print("Term found for ", id) if verbose else None
                    self.term = json_data
                    self.__dict__.update(term_object.__dict__)
                elif isinstance(json_data, pandas.core.frame.DataFrame):
                    print("Dataframe found for ", id) if verbose else None
                    term_object = VFBTerm(id=json_data['id'].values[0], verbose=verbose)
                    self.__dict__.update(term_object.__dict__)
                else:
                    print("Unable to resolve term for ", id) if verbose else None
        elif term is not None:
            self.term = term
            self.related_terms = related_terms
            self.channel_images = channel_images
            self._summary = None
            self.name = self.term.core.name
            self.id = self.term.core.short_form
            self.description = self.term.description
            self.url = self.term.link

            self._parents_ids = parents
            self._parents = None  # Initialize as None, will be loaded on first access

            self._regions_ids = regions
            self._regions = None  # Initialize as None, will be loaded on first access

            self._dataset_ids = dataset
            self._datasets = None  # Initialize as None, will be loaded on first access

            self._subtypes = None # Initialize as None, will be loaded on first access

            self._subparts = None # Initialize as None, will be loaded on first access

            self._children = None # Initialize as None, will be loaded on first access

            if self.term.icon:
                self.thumbnail = self.term.icon
            elif channel_images and len(channel_images) > 0 and channel_images[0].image.image_thumbnail:
                self.thumbnail = channel_images[0].image.image_thumbnail

            if counts:
                self.counts = counts

            if publications:
                self.publications = publications

            if license:
                self.license = license

            if xrefs:
                self.xrefs = xrefs

            if synonyms:
                self.synonyms = synonyms

            self._instances = None

            # Set flags for different types of terms
            self.is_type = self.has_tag('Class')
            self.is_instance = self.has_tag('Individual')
            self.is_dataset = self.has_tag('DataSet')
            self.is_neuron = self.has_tag('Neuron')
            self.has_image = self.has_tag('has_image')
            self.has_scRNAseq = self.has_tag('hasScRNAseq')
            self.has_neuron_connectivity = self.has_tag('has_neuron_connectivity')
            self.has_region_connectivity = self.has_tag('has_region_connectivity')

    @property
    def parents(self, verbose=False):
        if self._parents is None:
            print("Loading parents for the first time...") if verbose else None
            self._parents = VFBTerms(self._parents_ids) if self._parents_ids else None
        return self._parents

    @property
    def regions(self):
        if self._regions is None:
            print("Loading regions for the first time...") if self.has_tag('DataSet') else None
            self._regions = VFBTerms(self._regions_ids) if self._regions_ids else None
        return self._regions

    @property
    def instances(self):
        if self._instances is None:
            print("Loading instances for the first time...")
            if self.has_tag('Class'):
                self._instances = VFBTerms(self.vfb.get_instances(class_expression=f"'{self.id}'", return_id_only=True))
            elif self.has_tag('DataSet'):
                print(f"Loading {self.counts['images'] if self.counts and 'images' in self.counts.keys() else ''} instances for dataset: {self.name}...")
                self._instances = VFBTerms(self.vfb.get_instances_by_dataset(dataset=self.id, return_id_only=True))
            if self._instances and len(self._instances) > 0:
                self.has_image = True
        return self._instances

    @property
    def summary(self):
        if self._summary is None:
            self._summary = self.get_summary()
        return self._summary

    @property
    def datasets(self):
        if self._datasets is None:
            self._datasets = VFBTerms(self._dataset_ids) if self._dataset_ids else None
        return self._datasets

    @property
    def subtypes(self):
        if self._subtypes is None:
            self._subtypes = VFBTerms(self.vfb.oc.get_subclasses(query=f"'{self.id}'"))
        return self._subtypes

    @property
    def subparts(self):
        if self._subparts is None:
            self._subparts = VFBTerms(self.vfb.oc.get_subclasses(query=f"'BFO_0000050' some '{self.id}'"))
        return self._subparts

    @property
    def children(self):
        if self._children is None:
            self._children = self.subtypes + self.subparts
        return self._children

    def __repr__(self):
        return f"VFBTerm(term={repr(self.term)})"

    def __getitem__(self, index):
        if index != 0:
            print("VFBTerm only has one item")
            return VFBTerms([self])
        return self

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)

    def __len__(self):
        return 1

    def __add__(self, other):
        if isinstance(other, VFBTerms):
            combined_terms = [self.term] + other.terms
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        if isinstance(other, VFBTerm):
            combined_terms = [self.term] + [other]
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        raise TypeError("Unsupported operand type(s) for +: 'VFBTerms' and '{}'".format(type(other).__name__))

    def __sub__(self, other, verbose=False):
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("Removing ", other_ids) if verbose else None
            remaining_terms = VFBTerms([term for term in [self.term] if term.id not in other_ids])
            print ("Remaining ", remaining_terms.get_ids()) if verbose else None
            return remaining_terms
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("Removing ", other.id) if verbose else None
            remaining_terms = VFBTerms([term for term in [self.term] if term.id != other.id])
            return remaining_terms
        raise TypeError("Unsupported operand type(s) for -: 'VFBTerms' and '{}'".format(type(other).__name__))

    def get_summary(self, return_dataframe=True, verbose=False):
        """
        Returns a summary of the term's information.
        """
        summary = {
            "ID": getattr(self.term.core, "short_form", None),
            "Name": getattr(self.term.core, "name", None),
            "Description": f"{getattr(self.term, 'description', '')} {getattr(self.term, 'comment', '')}".strip(),
            "URL": getattr(self, "url", None),
        }

        if hasattr(self, "related_terms") and self.related_terms:
            summary["Related Terms"] = [str(rel) for rel in self.related_terms]
        if hasattr(self, "_instances") and self._instances:
            summary["instances"] = self.instances.get_names()
        if hasattr(self, "parents") and self.parents:
            summary["Parents"] = self.parents.get_names()
        if hasattr(self, "regions") and self.regions:
            summary["Regions"] = self.regions.get_names()
        if hasattr(self, "counts") and self.counts:
            summary["Counts"] = self.counts
        if hasattr(self, "publications") and self.publications:
            summary["Publications"] = [str(pub.core.name) for pub in self.publications]
        if hasattr(self, "license") and self.license:
            summary["License"] = self.license.core.name
        if hasattr(self, "xrefs") and self.xrefs:
            summary["Cross References"] = [str(xref.link) for xref in self.xrefs]

        if return_dataframe:
            return pandas.DataFrame([summary])

        return summary

    def has_tag(self, tag):
        return tag in self.term.core.types

    def load_skeleton(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load the navis skeleton from each available image in the term.
        """
        if self.has_tag('Neuron'):
            if template:
                if query_by_label:
                    selected_template = self.vfb.lookup_id(template)
                    print("Template (", template, ") resolved to id ", selected_template) if verbose else None
                    selected_template = selected_template
                else:
                    selected_template = template
                print("Loading skeleton for ", self.name, " aligned to ", template) if verbose else None
                skeletons = [ci.image.get_skeleton() for ci in self.channel_images if ci.image.template_anatomy.short_form == selected_template] if self.channel_images else None
                if skeletons:
                    self.skeleton = skeletons[0] if skeletons else None
            else:
                print("Loading skeletons for ", self.name) if verbose else None
                print("Processinng channel images: ", self.channel_images) if verbose else None
                self.skeleton = [ci.image.get_skeleton() for ci in self.channel_images] if self.channel_images else None
            if hasattr(self, 'skeleton') and self.skeleton:
                if isinstance(self.skeleton, list):
                    self.skeleton = [item for item in self.skeleton if item is not None]
                    for skeleton in self.skeleton:
                        skeleton.name = self.name
                        skeleton.label = self.name
                        skeleton.id = self.id

                    if len(self.skeleton) > 1:
                        print("Multiple skeletons found for ", self.name, ". Please specify a template.")
                        print("Available templates: ", [ci.image.template_anatomy.name for ci in self.channel_images])
                    elif len(self.skeleton) == 1:
                        print("Skeleton found for ", self.name) if verbose else None
                        self.skeleton = self.skeleton[0]
                else:
                    print("Skeleton found for ", self.name) if verbose else None
                    self.skeleton.name = self.name
                    self.skeleton.label = self.name
                    self.skeleton.id = self.id
        else:
            print(f"{self.name} is not a neuron") if verbose else None

    def load_mesh(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load the navis mesh from each available image in the term.
        """
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
                selected_template = selected_template
            else:
                selected_template = template
            print("Loading mesh for ", self.name, " aligned to ", template) if verbose else None
            mesh = [ci.image.get_mesh(verbose=verbose, output='neuron' if self.has_tag('Neuron') else 'volume') for ci in self.channel_images if ci.image.template_anatomy.short_form == selected_template] if self.channel_images else None
            if mesh:
                self.mesh = mesh[0]
        else:
            print("Loading meshes for ", self.name) if verbose else None
            self.mesh = [ci.image.get_mesh(verbose=verbose, output='neuron' if self.has_tag('Neuron') else 'volume') for ci in self.channel_images] if self.channel_images else None
        if hasattr(self, 'mesh') and self.mesh:
            if isinstance(self.mesh, list):
                print("Processing meshes: ", self.mesh) if verbose else None
                self.mesh = [item for item in self.mesh if item is not None]
                print(len(self.mesh), " Meshes found: ", self.mesh) if verbose else None
                for mesh in self.mesh:
                    mesh.name = self.name
                    mesh.label = self.name
                    mesh.id = self.id
                if len(self.mesh) > 1:
                    print("Multiple meshes found for ", self.name, ". Please specify a template.")
                    print("Available templates: ", [ci.image.template_anatomy.name.replace('_c','') for ci in self.channel_images])
                elif len(self.mesh) == 1:
                    print("Single mesh loaded for ", self.name) if verbose else None
                    self.mesh = self.mesh[0]
            else:
                self.mesh.name = self.name
                self.mesh.label = self.name
                self.mesh.id = self.id


    def load_volume(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load the navis volume from each available image in the term.
        """
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
                selected_template = selected_template
            else:
                selected_template = template
            volume = [ci.image.get_volume() for ci in self.channel_images if ci.image.template_anatomy.short_form == selected_template] if self.channel_images else None
            if volume:
                self.volume = volume[0] if volume else None
        else:
            print("Loading volumes for ", self.name) if verbose else None
            self.volume = [ci.image.get_volume() for ci in self.channel_images] if self.channel_images else None
        if hasattr(self, 'volume') and self.volume:
            if isinstance(self.volume, list):
                print("Processing volumes: ", self.volume) if verbose else None
                self.volume = [item for item in self.volume if item is not None]
                print(len(self.volume), " Volumes found: ", self.volume) if verbose else None
                for volume in self.volume:
                        volume.name = self.name
                        volume.label = self.name
                        volume.id = self.id

                if len(self.volume) > 1:
                    print("Multiple volumes found for ", self.name, ". Please specify a template.")
                    print("Available templates: ", [ci.image.template_anatomy.name for ci in self.channel_images])
                elif len(self.volume) == 1:
                    self.volume = self.volume[0]
            else:
                self.volume.name = self.name
                self.volume.label = self.name
                self.volume.id = self.id

    def plot3d(self, template=None, verbose=False, query_by_label=True, force_reload=False, **kwargs):
        """
        Plot the 3D representation of any neuron, expression or regions.
        """
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
                query_by_label = False
            else:
                selected_template = template
        else:
                selected_template = template
        if self.has_tag('Individual'):
            if not hasattr(self, 'skeleton') or force_reload:
                self.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
            if hasattr(self, 'skeleton') and self.skeleton:
                print(f"Skeleton found for {self.name}") if verbose else None
                self.skeleton.plot3d(**kwargs)
                return
            else:
                print(f"No skeleton found for {self.name} check for a mesh") if verbose else None
                if not hasattr(self, 'mesh') or force_reload:
                    self.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label)
                if hasattr(self, 'mesh') and self.mesh:
                    print(f"Mesh found for {self.name}") if verbose else None
                    self.mesh.plot3d(**kwargs)
                    return
                else:
                    print(f"No mesh found for {self.name} check for a volume") if verbose else None
                    if not hasattr(self, 'volume') or force_reload:
                        self.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label)
                    if hasattr(self, 'volume') and self.volume:
                        print(f"Volume found for {self.name}") if verbose else None
                        self.volume.plot3d(**kwargs)
                        return
                    else:
                        print(f"No volume found for {self.name}") if verbose else None
        else:
            print(f"{self.name} is not a instance") if verbose else None
        if self.instances and len(self._instances) > 0:
            print(f"Loading instances for {self.name}") if verbose else None
            self.instances.plot3d(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload, **kwargs)
            return

    def show(self, template=None, transparent=False, verbose=False):
        # First, try to show the image of the current object
        if self.channel_images:
            if template:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
            else:
                selected_template = None

            for ci in self.channel_images:
                if selected_template is None or ci.image.template_anatomy.short_form == selected_template:
                    print("Loading thumbnail for", self.name)
                    print(repr(ci.image)) if verbose else None
                    ci.image.show(transparent=transparent, verbose=verbose)
                    return  # Successfully displayed, so exit the method

        # If the current object has instances, try to show the image for one of them
        if self.instances and len(self.instances) > 0:
            for instance in self.instances:
                if instance.channel_images and len(instance.channel_images) > 0:
                    print("Calling instance thumbnail for", instance.name) if verbose else None
                    instance.show(template=template, transparent=transparent, verbose=verbose)
                    return  # Successfully displayed, so exit the method

        print(f"No images found to display for {self.name}") if verbose else None

    def open(self, verbose=False):
        print("Opening ", self.url) if verbose else None
        webbrowser.open(self.url)

class VFBTerms:
    def __init__(self, terms: Union[List[VFBTerm], List[str], pandas.core.frame.DataFrame, List[dict]], verbose=False):
        from vfb_connect import vfb
        self.vfb = vfb

        # Check if terms is a list of VFBTerm objects
        if isinstance(terms, list) and all(isinstance(term, VFBTerm) for term in terms):
            self.terms = terms

        # Check if terms is a list of strings (IDs)
        elif isinstance(terms, list) and all(isinstance(term, str) for term in terms):
            self.terms = [VFBTerm(id=term, verbose=verbose) for term in self.tqdm_with_threshold(terms, threshold=10, desc="Loading terms")] if len(terms) > 0 else []

        # Check if terms is a DataFrame
        elif isinstance(terms, pandas.core.frame.DataFrame):
            self.terms = [VFBTerm(id=id, verbose=verbose) for id in self.tqdm_with_threshold(terms['id'].values, threshold=10, desc="Loading terms")] if 'id' in terms.columns else []

        # Check if terms is a numpy array
        elif isinstance(terms, np.ndarray):
            self.terms = [VFBTerm(id=id, verbose=verbose) for id in self.tqdm_with_threshold(terms, threshold=10, desc="Loading terms")] if len(terms) > 0 and isinstance(terms[0],str) else []

        # Check if terms is a list of dictionaries
        elif isinstance(terms, list) and all(isinstance(term, dict) for term in terms):
            self.terms = [VFBTerm(id=term['id'], verbose=verbose) for term in self.tqdm_with_threshold(terms, threshold=10, desc="Loading terms")]

        else:
            raise ValueError("Invalid input type for terms. Expected a list of VFBTerm, a list of str, or a DataFrame.")

    def __repr__(self):
        return f"VFBTerms(terms={self.terms})"

    def __getitem__(self, index):
        if isinstance(index, slice):
            # If the index is a slice, return a new VFBTerms object with the sliced terms
            return VFBTerms(self.terms[index])
        else:
            # Otherwise, return the specific item from the list
            return self.terms[index]

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)

    def __len__(self):
        return len(self.terms)

    def __add__(self, other):
        if isinstance(other, VFBTerms):
            combined_terms = self.terms + other.terms
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        if isinstance(other, VFBTerm):
            combined_terms = self.terms + [other]
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        raise TypeError("Unsupported operand type(s) for +: 'VFBTerms' and '{}'".format(type(other).__name__))

    def __sub__(self, other, verbose=False):
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("Removing ", other_ids) if verbose else None
            remaining_terms = VFBTerms([term for term in self.terms if term.id not in other_ids])
            print ("Remaining ", remaining_terms.get_ids()) if verbose else None
            return remaining_terms
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("Removing ", other.id) if verbose else None
            remaining_terms = VFBTerms([term for term in self.terms if term.id != other.id])
            return remaining_terms
        raise TypeError("Unsupported operand type(s) for -: 'VFBTerms' and '{}'".format(type(other).__name__))


    def load_skeletons(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load the navis skeleton from each available image in the term.
        """
        for term in self.terms:
            term.load_skeleton(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)

    def load_meshes(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load the navis mesh from each available image in the term.
        """
        for term in self.terms:
            term.load_mesh(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)

    def load_volumes(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load the navis volume from each available image in the term.
        """
        for term in self.terms:
            term.load_volume(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)

    def plot3d(self, template=None, verbose=False, query_by_label=True, force_reload=False, **kwargs):
        """
        Plot the 3D representation of any neuron or expression.
        """
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
                query_by_label = False
            else:
                selected_template = template
        else:
                selected_template = template
        skeletons=[]
        for term in VFBTerms.tqdm_with_threshold(self, self.terms, threshold=10, desc="Loading Images"):
            if term.has_tag('Individual'):
                print(f"{term.name} is an instance") if verbose else None
            else:
                print(f"{term.name} is not an instance soo won't have a skeleton, mesh or volume") if verbose else None
                continue  
            if not hasattr(term, 'skeleton') or force_reload:
                term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
            if hasattr(term, 'skeleton') and term.skeleton:
                print(f"Skeleton found for {term.name}") if verbose else None
                if not selected_template:
                    if isinstance(term.skeleton, list):
                        print("Multiple skeletons found for ", term.name, ". Arbitarily taking the first template as the space to plot in. Specify a template to avoid this.")
                        selected_template = term.channel_images[0].image.template_anatomy.short_form
                        print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name}")
                        term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=True)
                    else:
                        selected_template = term.channel_images[0].image.template_anatomy.short_form
                        print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name} from the first skeleton found. Specify a template to avoid this.")
                skeletons.append(term.skeleton)
            else:
                print(f"No skeleton found for {term.name} check for a mesh") if verbose else None
                if not hasattr(term, 'mesh') or force_reload:
                    term.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
                if hasattr(term, 'mesh') and term.mesh:
                    print(f"Mesh found for {term.name}") if verbose else None
                    if not selected_template:
                        if isinstance(term.mesh, list):
                            print("Multiple meshes found for ", term.name, ". Arbitarily taking the first template as the space to plot in. Specify a template to avoid this.")
                            selected_template = term.channel_images[0].image.template_anatomy.short_form
                            print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name}")
                            term.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=True)
                        else:
                            selected_template = term.channel_images[0].image.template_anatomy.short_form
                            print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name} from the first mesh found. Specify a template to avoid this.")
                    skeletons.append(term.mesh)
                else:
                    print(f"No mesh found for {term.name} check for a volume") if verbose else None
                    if not hasattr(term, 'volume') or force_reload:
                        term.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
                    if hasattr(term, 'volume') and term.volume:
                        if not selected_template:
                            if isinstance(term.volume, list):
                                print("Multiple volumes found for ", term.name, ". Arbitarily taking the first template as the space to plot in. Specify a template to avoid this.")
                                selected_template = term.channel_images[0].image.template_anatomy.short_form
                                print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name}")
                                term.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=True)
                            elif isinstance(term.volume, navis.core.volumes.Volume):
                                selected_template = term.channel_images[0].image.template_anatomy.short_form
                                print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name} from the first volume found. Specify a template to avoid this.")
                        skeletons.append(term.volume)
                    else:
                        print(f"No volume found for {term.name}") if verbose else None

        if skeletons:
            print(f"Plotting 3D representation of {len(skeletons)} items")
            navis.plot3d(skeletons, **kwargs)
        else:
            print("Nothing found to plot")

    def get_ids(self):
        return [term.id for term in self.terms]

    def get_names(self):
        return [term.name for term in self.terms]

    def get_summaries(self, return_dataframe=True):
        summaries = [term.get_summary(return_dataframe=return_dataframe) for term in self.terms]

        if return_dataframe:
            return pandas.concat(summaries, ignore_index=True)

        return summaries

    def open(self, template=None, verbose=False):
        # URL for VFB browser
        url = "https://v2.virtualflybrain.org/org.geppetto.frontend/geppetto"
        space = self.vfb.lookup_id(template) + "," if template else ""
        images = "?i=" + space + ",".join(self.get_ids())
        print("Opening VFB browser with URL: ", url + images) if verbose else None

        # Open the URL in the default browser
        webbrowser.open(url + images)

    def tqdm_with_threshold(self, iterable, threshold=10, **tqdm_kwargs):
        """
        Custom tqdm that only shows the progress bar if the length of the iterable exceeds the threshold.

        :param iterable: The iterable to process.
        :param threshold: The minimum length of the iterable to display the progress bar.
        :param tqdm_kwargs: Additional arguments to pass to tqdm.
        :return: An iterable, with or without a progress bar.
        """
        if len(iterable) > threshold:
            return tqdm(iterable, **tqdm_kwargs)
        else:
            return iterable

def create_vfbterm_list_from_json(json_data, verbose=False):
    """
    Create a list of VFBTerm objects from JSON data.

    :param json_data: JSON data as a string or list of dictionaries.
    :return: A list of VFBTerm objects.
    """
    if isinstance(json_data, str):
        if json_data.startswith('['):
            data = json.loads(json_data)
        else:
            data = [json.loads(json_data)]
    if isinstance(json_data, dict):
        data = [json_data]
    if isinstance(json_data, list):
        data = json_data

    return VFBTerms([create_vfbterm_from_json(term, verbose=verbose) for term in data])

# Helper function to create a VFBTerm object from JSON
def create_vfbterm_from_json(json_data, verbose=False):
    """
    Create a VFBTerm object from JSON data.

    :param json_data: JSON data as a string or dictionary.
    :return: A VFBTerm object.
    """
    data = None
    if not json_data:
        print("No JSON data provided") if verbose else None
        return None
    if isinstance(json_data, str):
        print("Loading JSON data from string") if verbose else None
        data = json.loads(json_data)
    if isinstance(json_data, dict):
        print("Loading JSON data from dictionary") if verbose else None
        data = json_data
    if isinstance(json_data, list):
        print("Loading JSON data from list") if verbose else None
        if len(json_data) > 1:
            return create_vfbterm_list_from_json(json_data, verbose=verbose)
        elif len(json_data) == 1:
            data = json_data[0]
            return create_vfbterm_from_json(data, verbose=verbose)
        return None

    if data:
        # Create the core Term object
        core = MinimalEntityInfo(**data['term']['core'])
        term = Term(core=core,
                    description=data['term'].get('description'),
                    comment=data['term'].get('comment'),
                    link=data['term'].get('link'),
                    icon=data['term'].get('icon'))
        print(f"Loaded term: {term.core.name}") if verbose else None

        # Handle related terms (relations)
        related_terms = None
        if 'relationships' in data:
            related_terms = []
            for relation in data['relationships']:
                rel = MinimalEdgeInfo(**relation['relation'])
                object = relation['object']['short_form']
                related_terms.append(Rel(relation=rel, object=object))
            print(f"Loaded {len(related_terms)} related terms from relationships") if verbose else None

        if 'related_individuals' in data:
            related_terms = [] if not related_terms else related_terms
            bc = len(related_terms)
            for relation in data['related_individuals']:
                rel = MinimalEdgeInfo(**relation['relation'])
                object = relation['object']['short_form']
                related_terms.append(Rel(relation=rel, object=object))
            print(f"Loaded {len(related_terms)-bc} related terms from related_individuals") if verbose else None

        # Handle channel images
        channel_images = None
        if 'channel_image' in data:
            channel_images = []
            for ci in data['channel_image']:
                image_data = ci['image']
                image = Image(
                    image_folder=image_data.get('image_folder', ''),
                    template_channel=MinimalEntityInfo(**image_data['template_channel']),
                    template_anatomy=MinimalEntityInfo(**image_data['template_anatomy']),
                    image_nrrd=image_data.get('image_nrrd'),
                    image_swc=image_data.get('image_swc'),
                    image_obj=image_data.get('image_obj'),
                    image_thumbnail=image_data.get('image_thumbnail')
                )
                channel_image = ChannelImage(
                    image=image,
                    channel=MinimalEntityInfo(**ci['channel']),
                    imaging_technique=MinimalEntityInfo(**ci['imaging_technique'])
                )
                channel_images.append(channel_image)
            print(f"Loaded {len(channel_images)} channel images") if verbose else None

        parents = None
        if 'parents' in data:
            parents_json = data['parents']
            print(f"Parents: {parents}") if verbose else None
            if isinstance(parents_json, list):
                parents = [parent['short_form'] for parent in parents_json]
                print(f"Parents: {parents}") if verbose else None
            elif isinstance(parents_json, VFBTerms):
                parents = parents_json.get_ids()
            else:
                print("Parents type not recognised", type(parents)) if verbose else None
            print(f"Parents: {parents}") if verbose else None

        domains = None
        if not channel_images and 'template_channel' in data:
            image_data = data['template_channel']
            image = Image(
                image_folder=image_data.get('image_folder', ''),
                template_channel=MinimalEntityInfo(**data['template_channel']['channel']),
                template_anatomy=MinimalEntityInfo(**data['term']['core']),
                image_nrrd=image_data.get('image_nrrd'),
                image_swc=image_data.get('image_swc'),
                image_obj=image_data.get('image_obj'),
                image_thumbnail=image_data.get('image_thumbnail')
            )
            channel_image = ChannelImage(
                image=image,
                channel=MinimalEntityInfo(**data['template_channel']['channel'])
            )
            channel_images = [channel_image]
            if 'template_domains' in data:
                domains = []
                for domain in data['template_domains']:
                    id = domain['anatomical_individual']['short_form']
                    domains.append(id)
            print(f"Loaded {len(channel_images)} channel images") if verbose else None

        counts = None
        if 'dataset_counts' in data:
            counts = data['dataset_counts']
            print(f"Counts: {counts}") if verbose else None

        publications = None
        if 'pubs' in data:
            publications = []
            for pub in data['pubs']:
                publication = Publication(**pub)
                publications.append(publication)
            print(f"Loaded {len(publications)} publications") if verbose else None

        license = None
        if 'license' in data and len(data['license']) > 0:
            license = Term(**data['license'][0])
            print(f"Loaded license: {license.core.name}") if verbose else None

        datasets = None
        if not license and 'dataset_license' in data:
            datasets = []
            for dl in data['dataset_license']:
                if 'license' in dl and not license: # assuming there is only one license per anatomical Individual
                    license = Term(**dl['license'])
                if 'dataset' in dl:
                    datasets.append(dl['dataset']['core']['short_form'])
            print(f"Loaded {len(datasets)} datasets") if verbose else None

        xrefs = None
        if 'xrefs' in data:
            xrefs = []
            for xref in data['xrefs']:
                xrefs.append(Xref(
                    core=MinimalEntityInfo(**xref['site']),
                    is_data_source=xref['is_data_source'],
                    icon=xref.get('icon', None),
                    homepage=xref.get('homepage', None),
                    accession=xref.get('accession', None),
                    link_text=xref.get('link_text', None),
                    link=xref.get('link_base', '') + xref.get('accession', '') + xref.get('link_postfix', ''),
                ))
            print(f"Loaded {len(xrefs)} cross references") if verbose else None

        synonyms = None
        if 'pub_syn' in data:
            synonyms = []
            for syn in data['pub_syn']:
                synonym = Synonym(synonym=Syn(**syn['synonym']), pub=Publication(**syn['pub']))
                synonyms.append(synonym)
            print(f"Loaded {len(synonyms)} synonyms") if verbose else None

        return VFBTerm(term=term, related_terms=related_terms, channel_images=channel_images, parents=parents, regions=domains, counts=counts, publications=publications, license=license, xrefs=xrefs, dataset=datasets, synonyms=synonyms, verbose=verbose)
    else:
        return None

def load_skeletons(vfb_term, template=None, verbose=False, query_by_label=True, force_reload=False):
    """
    Load the navis skeleton from each available image in the term.

    :param vfb_term: A VFBTerm object or list of VFBTerm objects.
    :param template: The short form of the template to load skeletons for.
    :return: None
    """
    from vfb_connect import vfb
    if template:
        if query_by_label:
            selected_template = vfb.lookup_id(template)
            print("Template (", template, ") resolved to id ", selected_template) if verbose else None
        else:
            selected_template = template
    if isinstance(vfb_term, VFBTerm):
        print("Loading skeletons for ", vfb_term.name) if template == None else print("Loading skeleton for ", vfb_term.name, " aligned to ", template)
        vfb_term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
    if isinstance(vfb_term, VFBTerms):
        for term in vfb_term:
            print("Loading skeletons for ", term.name) if template == None else print("Loading skeleton for ", term.name, " aligned to ", template)
            term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
    if isinstance(vfb_term, list):
        for term in vfb_term:
            print("Loading skeletons for ", vfb_term.name) if template == None else print("Loading skeleton for ", vfb_term.name, " aligned to ", template)
            term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)

