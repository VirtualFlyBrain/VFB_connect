import json
import os
import sys
from typing import Iterable, List, Optional, Union
import navis
import numpy as np
import pandas
import requests
import tempfile

from ..neo.neo4j_tools import chunks, Neo4jConnect, dict_cursor, escape_string

import webbrowser

neuron_containing_anatomy_tags = [
            "Painted_domain",
            "Synaptic_neuropil_domain",
            "Synaptic_neuropil_subdomain",
            "Neuron_projection_bundle",
            "Split",
            "Expression_pattern",
            "Muscle",
            "Neuromere",
            "Ganglion",
        ]

def is_notebook():
    """Check if the environment is a Jupyter notebook."""
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            if IProgress is None:
                return False
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
        """
        Initialize a MinimalEntityInfo object.

        :param short_form: Short form identifier of the entity.
        :param iri: Internationalized Resource Identifier (IRI) of the entity.
        :param label: Human-readable label of the entity.
        :param types: List of types associated with the entity.
        :param unique_facets: Optional list of unique facets associated with the entity.
        :param symbol: Optional symbol representing the entity.
        """
        self.short_form = short_form
        self.iri = iri
        self.label = label
        self.types = types
        self.unique_facets = unique_facets
        self.symbol = symbol
        if self.symbol and isinstance(self.symbol, list):
            self.symbol = self.symbol[0]
        self.name = self.get_name()

    def get_name(self):
        """
        Get the name of the entity, prioritizing the symbol if available.

        :return: The name of the entity.
        """
        return self.symbol if self.symbol else self.label

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __str__(self):
        """
        Return the string representation of the entity's name.

        :return: The name of the entity.
        """
        return f"{self.name}"

    def __repr__(self):
        """
        Return a string representation of the MinimalEntityInfo object.

        :return: A string representation of the MinimalEntityInfo object.
        """
        return f"MinimalEntityInfo(name={self.name}, short_form={self.short_form})"


class MinimalEdgeInfo:
    def __init__(self, iri: str, label: str, type: str, short_form: Optional[str] = None, confidence_value: Optional[str] = None, database_cross_reference: Optional[List[str]] = None):
        """
        Initialize a MinimalEdgeInfo object representing a relationship between entities.

        :param iri: Internationalized Resource Identifier (IRI) of the edge.
        :param label: Label describing the relationship.
        :param type: Type of the relationship.
        :param short_form: Optional short form identifier of the edge.
        :param confidence_value: Optional confidence value associated with the relationship.
        :param database_cross_reference: Optional list of database cross-references.
        """
        self.short_form = short_form
        self.iri = iri
        self.label = label
        self.type = type
        self.confidence_value = confidence_value if confidence_value else None
        self.database_cross_reference = database_cross_reference

    def __repr__(self):
        """
        Return a string representation of the MinimalEdgeInfo object.

        :return: A string representation of the MinimalEdgeInfo object.
        """
        if self.confidence_value and self.database_cross_reference:
            return f"MinimalEdgeInfo(label={self.label}, confidence={self.confidence_value}, reference={'; '.join(self.database_cross_reference)})"
        if self.confidence_value:
            return f"MinimalEdgeInfo(label={self.label}, confidence={self.confidence_value})"
        if self.database_cross_reference:
            return f"MinimalEdgeInfo(label={self.label}, reference={'; '.join(self.database_cross_reference)})"
        return f"MinimalEdgeInfo(label={self.label}, type={self.type})"


class Term:
    def __init__(self, core: MinimalEntityInfo, description: Optional[List[str]] = None, comment: Optional[List[str]] = None, link: Optional[str] = None, icon: Optional[str] = None):
        """
        Initialize a Term object.

        :param core: A MinimalEntityInfo object representing the core information of the term.
        :param description: Optional description of the term.
        :param comment: Optional comments about the term.
        :param link: Optional link to more information about the term.
        :param icon: Optional icon representing the term.
        """
        if isinstance(core, dict):
            self.core = MinimalEntityInfo(**core)
        elif isinstance(core, MinimalEntityInfo):
            self.core = core
        else:
            raise ValueError("core must be a MinimalEntityInfo object")
        self.description = ", ".join(description) if description else ""
        self.comment = ", ".join(comment) if comment else ""
        self.link = (
            link
            if link
            else "https://n2t.net/vfb:" + str(self.core.short_form)
            if hasattr(self.core, 'short_form') and self.core.short_form is not None
            else ""
        )
        self.icon = icon if icon else ""

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __len__(self):
        """
        Return the length of the Term object. Always 1 as it represents a single term.

        :return: The length of the Term object.
        """
        return 1

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        """
        Return a string representation of the Term object.

        :return: A string representation of the Term object.
        """
        return f"Term(term={repr(self.core)}, link={self.link})"

    def open(self, verbose=False):
        """
        Open the term's link in a web browser.

        :param verbose: If True, print the link being opened.
        """
        print(f"Opening {self.link}...") if verbose else None
        webbrowser.open(self.link)

class Publication:
    def __init__(self, core: MinimalEntityInfo, description: Optional[List[str]] = None, comment: Optional[List[str]] = None, link: Optional[str] = None, icon: Optional[str] = None, FlyBase: Optional[str] = None, PubMed: Optional[str] = None, DOI: Optional[str] = None, verbose=False):
        """
        Initialize a Publication object.

        :param core: A MinimalEntityInfo object representing the core information of the publication.
        :param description: Optional description of the publication.
        :param comment: Optional comments about the publication.
        :param link: Optional link to more information about the publication.
        :param icon: Optional icon representing the publication.
        :param FlyBase: Optional FlyBase ID associated with the publication.
        :param PubMed: Optional PubMed ID associated with the publication.
        :param DOI: Optional DOI associated with the publication.
        """
        if isinstance(core, dict):
            self.core = MinimalEntityInfo(**core)
        elif isinstance(core, MinimalEntityInfo):
            self.core = core
        elif isinstance(core, VFBTerm):
            print(f"Received a VFBTerm object: {core}") if verbose else None
            if hasattr(core, 'publications') and isinstance(core.publications[0], Publication):
                self.__dict__.update(core.publications[0].__dict__)
            else:
                print(f"Received a VFBTerm object without a publication: {core}") if verbose else None
                raise ValueError("core must be a MinimalEntityInfo object")
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

        self.name = self.core.name if hasattr(self, 'core') and hasattr(self.core, 'name') else None

    def __repr__(self):
        """
        Return a string representation of the Publication object.

        :return: A string representation of the Publication object.
        """
        return f"Publication(pub={repr(self.core)}, link={self.link})"

    def __len__(self):
        """
        Return the length of the Publication object. Always 1 as it represents a single publication.

        :return: The length of the Publication object.
        """
        return 1

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __setitem__(self, key, value):
        """
        Enable dictionary-like item assignment.

        :param key: The attribute name to set.
        :param value: The value to set for the given attribute.
        :raises KeyError: If the attribute does not exist.
        """
        setattr(self, key, value)

class Syn:
    def __init__(self, scope: str, label: str, type: Optional[str] = None):
        """
        Initialize a Syn object representing a synonym.

        :param scope: The scope of the synonym (e.g., exact, broad).
        :param label: The label of the synonym.
        :param type: Optional type of the synonym.
        """
        self.scope = scope
        self.label = label
        if type:
            self.type = type

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __len__(self):
        """
        Return the length of the Syn object. Always 1 as it represents a single synonym.

        :return: The length of the Syn object.
        """
        return 1

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        """
        Return a string representation of the Syn object.

        :return: A string representation of the Syn object.
        """
        if hasattr(self, 'type'):
            return f"Syn(scope={self.scope}, label={self.label}, type={self.type})"
        if self.scope:
            return f"Syn(scope={self.scope}, label={self.label})"
        return f"Syn(label={self.label})"

class Synonym:
    def __init__(self, synonym: Syn, pub: Optional[Publication] = None):
        """
        Initialize a Synonym object.

        :param synonym: A Syn object representing the synonym.
        :param pub: Optional Publication object associated with the synonym.
        :raises ValueError: If the synonym is not a Syn object.
        """
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
        """
        Return a string representation of the Synonym object.

        :return: A string representation of the Synonym object.
        """
        if hasattr(self, 'pub'):
            return f"Synonym(synonym={repr(self.synonym)}, pub={repr(self.pub)})"
        return f"Synonym(synonym={repr(self.synonym)})"

    def __len__(self):
        """
        Return the length of the Synonym object. Always 1 as it represents a single synonym.

        :return: The length of the Synonym object.
        """
        return 1

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")


class Xref:
    def __init__(self, core: MinimalEntityInfo, is_data_source: bool = False, link: Optional[str] = None, icon: Optional[str] = None, accession: Optional[str] = None, link_text: Optional[str] = None, homepage: Optional[str] = None):
        """
        Initialize an Xref object representing a cross-reference.

        :param core: A MinimalEntityInfo object representing the core information of the cross-reference.
        :param is_data_source: Whether this cross-reference is a data source.
        :param link: Optional link to more information.
        :param icon: Optional icon representing the cross-reference.
        :param accession: Optional accession number for the cross-reference.
        :param link_text: Optional text to display for the link.
        :param homepage: Optional homepage URL associated with the cross-reference.
        """
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
        self.site_id = self.core.short_form if hasattr(self.core, 'short_form') else self.core.iri if hasattr(self.core, 'iri') else None
        self.id = self.site_id + ':' + self.accession if hasattr(self, 'accession') else self.site_id
        self.site_name = self.core.symbol if hasattr(self.core, 'symbol') else self.core.label if hasattr(self.core, 'label') else self.site_id
        self.name = self.link_text if hasattr(self, 'link_text') and self.link_text else self.site_name

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __len__(self):
        """
        Return the length of the Xref object. Always 1 as it represents a single cross-reference.

        :return: The length of the Xref object.
        """
        return 1

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        """
        Return a string representation of the Xref object.

        :return: A string representation of the Xref object.
        """
        return f"Xref(link_text={self.link_text if hasattr(self, 'link_text') else self.core.name}, link={self.link if hasattr(self,'link') else self.homepage if hasattr(self,'homepage') else self.core.iri}, accession={self.accession if hasattr(self,'accession') else self.core.short_form})"

class Rel:
    def __init__(self, relation: MinimalEdgeInfo, object: str, object_name: str = None):
        """
        Initialize a Rel object representing a relationship between entities.

        :param relation: A MinimalEdgeInfo object representing the relationship type.
        :param object: The ID of the related object.
        """
        if isinstance(relation, dict):
            self.relation = MinimalEdgeInfo(**relation)
        elif isinstance(relation, MinimalEdgeInfo):
            self.relation = relation
        else:
            raise ValueError("relation must be a MinimalEdgeInfo object")
        self._object_id = object
        self._object = None
        if object_name:
            self._object_name = object_name
        else:
            self._object_name = self.vfb.lookup_name(self._object_id)

    @property
    def object(self):
        """
        Lazy-load the related object as a VFBTerm.

        :return: The related VFBTerm object.
        """
        if self._object is None:
            self._object = VFBTerm(id=self._object_id)
            self._object_name = self._object.name
            self._object_id = self._object.id
        return self._object

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __len__(self):
        """
        Return the length of the Rel object. Always 1 as it represents a single relationship.

        :return: The length of the Rel object.
        """
        return 1

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        """
        Return a string representation of the Rel object.

        :return: A string representation of the Rel object.
        """
        result = f"Rel(relation={repr(self.relation)}, object={repr(self.object)})"
        if hasattr(self.relation, 'confidence_value'):
            result = result[:-1] + f", confidence={self.relation.confidence_value})"
        return result

    def where(self, relation: str):
        """
        Get the object of the relation if the relation matches the specified label.

        :param relation: The label of the relation to match.
        :return: The related VFBTerm object if the relation matches, otherwise None.
        """
        if self.relation.label == relation:
            return self.object
        return None

    def get_summary(self, return_dataframe=True):
        """
        Get a summary of the relations.

        :param return_dataframe: Whether to return the summary as a pandas DataFrame.
        :return: A summary of the relations, either as a DataFrame or a list of dictionaries.
        """
        summary = {}
        summary['relation'] = self.relation.label
        summary['object'] = self._object_name
        if hasattr(self.relation, 'confidence_value'):
            summary['confidence'] = self.relation.confidence_value
        if hasattr(self.relation, 'database_cross_reference'):
            summary['reference'] = "; ".join(self.relation.database_cross_reference)
        if return_dataframe:
            return pandas.DataFrame(summary)
        return summary


class Relations:
    def __init__(self, relations: Union[List[Rel], List[dict], 'Relations']):
        """
        Initialize a Relations object.

        :param relations: A list of Rel objects, dictionaries, or another Relations object.
        :raises ValueError: If the input is not of the expected type.
        """
        self._summary = None
        if isinstance(relations, list):
            if all(isinstance(rel, Rel) for rel in relations):
                self.relations = relations
            elif all(isinstance(rel, dict) for rel in relations):
                self.relations = [Rel(**rel) for rel in relations]
            else:
                raise ValueError("All elements in the list must be of type Rel or dict")
        elif isinstance(relations, Relations):
            self.relations = relations.relations
        else:
            raise ValueError("relations must be a list of Rel objects, a list of dicts, or a Relations object")

    @property
    def summary(self):
        """
        Get the summary of the term.
        """
        if self._summary is None:
            self._summary = self.get_summary()
        return self._summary

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes or list-like access to relations.

        :param key: The key or index to retrieve.
        :return: The related object or relation.
        :raises KeyError: If the key is out of range or not found.
        """
        if isinstance(key, int):
            # If the key is an integer, treat it as a list index
            if key < 0 or key >= len(self.relations):
                raise IndexError(f"Index '{key}' out of range for Relations")
            return self.relations[key]
        else:
            # Otherwise, treat it as a dictionary key for relation labels
            for rel in self.relations:
                if rel.relation.label == key:
                    return rel.object
            raise KeyError(f"Attribute '{key}' not found in Relations")

    def __len__(self):
        """
        Return the number of relations.

        :return: The number of relations.
        """
        return len(self.relations)

    def __repr__(self):
        """
        Return a string representation of the Relations object.

        :return: A string representation of the Relations object.
        """
        if len(self.relations) > 0:
            return f"Relations({', '.join([repr(rel) for rel in self.relations])})"
        return "Relations([])"

    def where(self, relation: str):
        """
        Get the objects of all relations that match the specified label.

        :param relation: The label of the relation to match.
        :return: A VFBTerms object containing the matching objects.
        """
        results = []
        for rel in self.relations:
            if rel.relation.label == relation:
                results.append(rel.object)
        return VFBTerms(results)

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The relation label to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The related object if found, otherwise the default value.
        """
        for rel in self.relations:
            if rel.relation.label == key:
                return rel.object
        return default

    def get_terms(self):
        """
        Get all the related terms as a VFBTerms object.

        :return: A VFBTerms object containing all the related terms.
        """
        return VFBTerms([rel.object for rel in self.relations], query_by_label=False)

    def get_relations(self):
        """
        Get all the relations as a list of MinimalEdgeInfo objects.

        :return: A list of MinimalEdgeInfo objects.
        """
        return [rel.get('relation') for rel in self.relations]

    def get_summary(self, return_dataframe=True):
        """
        Get a summary of the relations.

        :param return_dataframe: Whether to return the summary as a pandas DataFrame.
        :return: A summary of the relations, either as a DataFrame or a list of dictionaries.
        """
        summary = [rel.get_summary(return_dataframe=False) for rel in self.relations]
        if return_dataframe:
            return pandas.DataFrame(summary).fillna('')
        return summary

class Image:
    def __init__(self, image_folder: str, template_channel: MinimalEntityInfo, template_anatomy: MinimalEntityInfo, index: Optional[List[int]] = None, image_nrrd: Optional[str] = None, image_thumbnail: Optional[str] = None, image_swc: Optional[str] = None, image_obj: Optional[str] = None, image_wlz: Optional[str] = None):
        """
        Initialize an Image object.

        :param image_folder: The folder where the image is stored.
        :param template_channel: The template channel associated with the image.
        :param template_anatomy: The template anatomy associated with the image.
        :param index: Optional list of indices for the image.
        :param image_nrrd: Optional path to the NRRD file.
        :param image_thumbnail: Optional path to the thumbnail image.
        :param image_swc: Optional path to the SWC file.
        :param image_obj: Optional path to the OBJ file.
        :param image_wlz: Optional path to the WLZ file.
        """
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

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __len__(self):
        """
        Return the length of the Image object. Always 1 as it represents a single image.

        :return: The length of the Image object.
        """
        return 1

    def __repr__(self):
        """
        Return a string representation of the Image object.

        :return: A string representation of the Image object.
        """
        return f"Image(image_thumbnail={self.image_thumbnail})"

    def get_skeleton(self, verbose=False):
        """
        Get the skeleton representation from the image.

        :param verbose: If True, print additional information.
        :return: The skeleton as a navis object or None if not found.
        """
        if self.image_swc:
            return navis.read_swc(self.image_swc)
        if self.image_obj and 'volume_man.obj' in self.image_obj:
            mesh = None
            local_file = self.create_temp_file(suffix=".obj", verbose=verbose)
            file = self.download_file(self.image_obj, local_file.name, verbose=verbose)
            if file:
                mesh = navis.read_mesh(local_file.name, output='neuron', errors='ignore' if not verbose else 'log')
                self.delete_temp_file(local_file.name, verbose=verbose)
            if mesh:
                return mesh
        if self.image_nrrd:
            dotprops = None
            local_file = self.create_temp_file(suffix=".nrrd", verbose=verbose)
            file = self.download_file(self.image_nrrd, local_file.name, verbose=verbose)
            if file:
                dotprops = navis.read_nrrd(local_file.name, output='dotprops', errors='ignore' if not verbose else 'log')
                self.delete_temp_file(local_file.name, verbose=verbose)
            if dotprops:
                return dotprops
        return None

    def get_mesh(self, verbose=False, output='neuron'):
        """
        Get the mesh representation from the image.

        :param verbose: If True, print additional information.
        :param output: The type of output desired ('neuron' or 'volume').
        :return: The mesh as a navis object or None if not found.
        """
        if self.image_obj and 'volume_man.obj' in self.image_obj:
            mesh = None
            print("Reading mesh from ", self.image_obj) if verbose else None
            local_file = self.create_temp_file(suffix=".obj", verbose=verbose)
            file = self.download_file(self.image_obj, local_file.name, verbose=verbose)
            if file:
                mesh = navis.read_mesh(local_file.name, output=output, errors='ignore' if not verbose else 'log')
                self.delete_temp_file(local_file.name, verbose=verbose)
            if mesh:
                return mesh
        if self.image_swc:
            print("Falling back to skeleton version from ", self.image_swc) if verbose else None
            return navis.read_swc(self.image_swc, read_meta=False, errors='ignore' if not verbose else 'log')
        return None

    def get_volume(self, verbose=False):
        """
        Get the volume representation from the image.

        :param verbose: If True, print additional information.
        :return: The volume as a navis object or None if not found.
        """
        if self.image_nrrd:
            mesh = None
            print("Reading volume from ", self.image_nrrd) if verbose else None
            local_file = self.create_temp_file(suffix=".nrrd", verbose=verbose)
            file = self.download_file(self.image_nrrd, local_file.name, verbose=verbose)
            if file:
                mesh = navis.read_nrrd(local_file.name, output='voxels', errors='ignore' if not verbose else 'log')
                self.delete_temp_file(local_file.name, verbose=verbose)
            if mesh:
                return mesh
        else:
            print("No nrrd file associated") if verbose else None
        return None

    def create_temp_file(self, suffix=".nrrd", delete=False, verbose=False):
        """
        Create a temporary file with a specific extension.

        :param suffix: The file extension for the temporary file.
        :param delete: Whether to delete the file automatically.
        :param verbose: If True, print additional information.
        :return: The temporary file object.
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=delete)
        print(f"Temporary file created: {temp_file.name}") if verbose else None
        return temp_file

    def download_file(self, url, local_filename, verbose=False):
        """
        Download a file from a URL to a local file.

        :param url: The URL of the file to download.
        :param local_filename: The path to save the downloaded file.
        :param verbose: If True, print additional information.
        :return: The path to the downloaded file, or None if the download failed.
        """
        try:
            response = requests.get(url, stream=True, allow_redirects=True)
            if response.status_code == 200:
                with open(local_filename, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return local_filename
            else:
                print(f"Failed to download file from {url}") if verbose else None
                return None
        except Exception as e:
            print(f"\033[31mError:\033[0m downloading file from {url}: {e}")
            return None

    def delete_temp_file(self, file_path, verbose=False):
        """
        Delete the temporary file at the specified path.

        :param file_path: The path to the temporary file to be deleted.
        :param verbose: If True, print additional information.
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Temporary file deleted: {file_path}") if verbose else None
            else:
                print(f"File not found: {file_path}") if verbose else None
        except Exception as e:
            print(f"\033[31mError:\033[0m deleting file {file_path}: {e}") if verbose else None

    def show(self, transparent=False, verbose=False):
        """
        Display the image, with optional transparency.

        :param transparent: If True, use a transparent version of the image.
        :param verbose: If True, print additional information.
        """
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
            print("\033[31mError:\033[0m displaying thumbnail: ", e)


class ChannelImage:
    def __init__(self, image: Image, channel: MinimalEntityInfo, imaging_technique: Optional[MinimalEntityInfo] = None):
        """
        Initialize a ChannelImage object.

        :param image: An Image object representing the image.
        :param channel: A MinimalEntityInfo object representing the channel information.
        :param imaging_technique: Optional MinimalEntityInfo object representing the imaging technique.
        """
        self.image = image
        self.channel = channel
        self.imaging_technique = imaging_technique

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __len__(self):
        """
        Return the length of the ChannelImage object. Always 1 as it represents a single image.

        :return: The length of the ChannelImage object.
        """
        return 1

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        """
        Return a string representation of the ChannelImage object.

        :return: A string representation of the ChannelImage object.
        """
        return f"ChannelImage(image={repr(self.image)}, imaging_technique={self.imaging_technique.name}, aligned_to={self.image.template_anatomy.name})"


class AnatomyChannelImage:
    def __init__(self, anatomy: MinimalEntityInfo, channel_image: ChannelImage):
        """
        Initialize an AnatomyChannelImage object.

        :param anatomy: A MinimalEntityInfo object representing the anatomy.
        :param channel_image: A ChannelImage object representing the channel image.
        """
        self.anatomy = anatomy
        self.channel_image = channel_image

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __len__(self):
        """
        Return the length of the AnatomyChannelImage object. Always 1 as it represents a single anatomy-channel relationship.

        :return: The length of the AnatomyChannelImage object.
        """
        return 1

    def __repr__(self):
        """
        Return a string representation of the AnatomyChannelImage object.

        :return: A string representation of the AnatomyChannelImage object.
        """
        return f"AnatomyChannelImage(anatomy={self.anatomy})"

class Expression:
    def __init__(self, term: str = None, term_name: Optional[str] = None, term_type: Optional[str] = None, type: Optional[str] = None, type_name: Optional[str] = None, 
                 reference: Optional[Union[Publication,List[Publication],List[str],str]] = None, dataset: Optional['VFBTerm'] = None , expression_extent: Optional[float] = None, expression_level: Optional[float] = None, 
                 probability: Optional[float] = None, probability_type: Optional[str] = None, function: Optional[List[str]] = None, sex: Optional[str] = None, tissue: Optional[List[str]] = None):
        """
        Initialize an Expression object representing expression data.

        :param term: The ID of the term.
        :param expression_extent: The extent of expression.
        :param expression_level: The level of expression.
        """
        self._percentage_terms = ['confidence value'] # List of probability types that should be displayed as percentages
        self._term_id = term
        self._term = None # Initialize as None, will be loaded on first access
        self.id = term
        if term_name:
            self.name = term_name
        self._type_id = type
        self._type = None # Initialize as None, will be loaded on first access
        if type_name:
            self.type_name = type_name
        self.expression_extent = expression_extent
        self.expression_level = expression_level
        self.probability = probability
        self.probability_type = probability_type
        self.term_type = term_type if term_type else None

        self.function = function
        self.sex = sex
        self.tissue = tissue

        if reference:
            if isinstance(reference, list):
                if all(isinstance(ref, dict) for ref in reference):
                    self.reference = [Publication(**ref) for ref in reference]
                elif all(isinstance(ref, Publication) for ref in reference):
                    self.reference = reference
                elif all(isinstance(ref, str) for ref in reference):
                    self.reference = reference
                else:
                    raise ValueError("All elements in the list must be of type Publication or dict")
            elif isinstance(reference, dict):
                self.reference = Publication(**reference)
            elif isinstance(reference, Publication):
                self.reference = reference
            elif isinstance(reference, str):
                self.reference = [reference]
            else:
                raise ValueError("reference must be a Publication object")

        if dataset:
            if isinstance(dataset, dict):
                self.dataset = VFBTerm(**dataset)
            elif isinstance(dataset, VFBTerm):
                self.dataset = dataset
            elif isinstance(dataset, str):
                self.dataset = VFBTerm(id=dataset)
            else:
                raise ValueError("dataset must be a VFBTerm object")

        if term_type == 'gene':
            self.add_gene_properties()
        if term_type == 'cluster':
            self.add_cluster_properties()

    def add_gene_properties(self):
        @property
        def gene(self):
            """
            Lazy-load the related term as a VFBTerm.

            :return: The related VFBTerm object.
            """
            if self._term is None:
                self._term = VFBTerm(id=self._term_id)
                self.name = self._term.name
            return self._term
    
        # Dynamically add the property to the instance
        setattr(self.__class__, 'gene', gene)

    def add_cluster_properties(self):
        @property
        def cluster(self):
            """
            Lazy-load the related term as a VFBTerm.

            :return: The related VFBTerm object.
            """
            if self._term is None:
                self._term = VFBTerm(id=self._term_id)
                self.name = self._term.name
            return self._term
    
        # Dynamically add the property to the instance
        setattr(self.__class__, 'cluster', cluster)

    @property
    def cell_type(self):
        """
        Lazy-load the related type as a VFBTerm.

        :return: The related VFBTerm object.
        """
        if self._type is None:
            self._type = VFBTerm(id=self._type_id)
            self.type_name = self._type.name
        return self._type

    @property
    def summary(self):
        """
        Return a summary of the expression data.

        :return: A dictionary containing the expression data.
        """
        result = {}
        if hasattr(self, 'name') and self.name:
            result[self.term_type if self.term_type else 'term'] = self.name if hasattr(self, 'name') else self.term.name
        if hasattr(self, 'type_name') and self.type_name:
            result['cell_type'] = self.type_name if hasattr(self, 'type_name') else self.gene.name
        if hasattr(self, 'sex') and self.sex:
            result['sample_sex'] = self.sex
        if hasattr(self, 'tissue') and self.tissue:
            result['sample_tissue'] = self.tissue
        if hasattr(self, 'expression_extent') and self.expression_extent:
            result['extent'] = self.expression_extent
        if hasattr(self, 'expression_level') and self.expression_level:
            result['level'] = self.expression_level
        if hasattr(self, 'probability') and self.probability:
            if hasattr(self, 'probability_type') and self.probability_type:
                if self.probability_type in self._percentage_terms:
                    result[self.probability_type] = f"{round(self.probability * 100, 2)}%"
                else:
                    result[self.probability_type] = self.probability
            else:
                result['probability'] = self.probability
        if hasattr(self, 'reference') and self.reference:
            if isinstance(self.reference, Publication):
                result['reference'] = self.reference.name
            elif isinstance(self.reference, list) and all(isinstance(ref, Publication) for ref in self.reference):
                result['reference'] = '; '.join([ref.name for ref in self.reference])
            else:
                result['reference'] = '; '.join(self.reference)
        if hasattr(self, 'dataset') and self.dataset:
            result['dataset'] = self.dataset.name
        return result

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)
    
    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")
        
    def __len__(self):
        """
        Return the length of the Expression object. Always 1 as it represents a single expression.

        :return: The length of the Expression object.
        """
        return 1

    def __repr__(self):
        """
        Return a string representation of the Expression object.

        :return: A string representation of the Expression object.
        """
        result = ""
        if hasattr(self, 'term_type') and self.term_type:
            result += f"{self.term_type}="
        else:
            result += "term="
        if hasattr(self, 'name') and self.name:
            result += f"{self.name}"
        else:
            result += f"{self.term.name}"
        if hasattr(self, 'type_name') and self.type_name:
            result += f"{', ' if result else ''}cell_type={self.type_name}"
        if hasattr(self, 'sex') and self.sex:
            result += f"{', ' if result else ''}sample_sex={self.sex}"
        if hasattr(self, 'tissue') and self.tissue:
            result += f"{', ' if result else ''}sample_tissue={self.tissue}"
        if hasattr(self, 'function') and self.function:
            result += f"{', ' if result else ''}function={self.function}"
        if hasattr(self, 'expression_extent') and self.expression_extent:
            result += f"{', ' if result else ''}extent={self.expression_extent}"
        if hasattr(self, 'expression_level') and self.expression_level:
            result += f"{', ' if result else ''}level={self.expression_level}"
        if hasattr(self, 'probability') and self.probability:
            if hasattr(self, 'probability_type') and self.probability_type:
                if self.probability_type in self._percentage_terms:
                    result += f"{', ' if result else ''}{self.probability_type}={round(self.probability * 100, 2)}%"
                else:
                    result += f"{', ' if result else ''}{self.probability_type}={self.probability}"
            else:
                result += f"{', ' if result else ''}probability={self.probability}"
        if hasattr(self, 'reference') and self.reference:
            if isinstance(self.reference, Publication):
                result += f"{', ' if result else ''}reference={self.reference.name}"
            elif isinstance(self.reference, list) and all(isinstance(ref, Publication) for ref in self.reference):
                result += f"{', ' if result else ''}reference={'; '.join([ref.name for ref in self.reference])}"
            else:
                result += f"{', ' if result else ''}reference={'; '.join(self.reference)}"
        if hasattr(self, 'dataset') and self.dataset:
            result += f"{', ' if result else ''}dataset={self.dataset.name}"
        return f"Expression({result})"

class ExpressionList:
    def __init__(self, expressions: Union[List[Expression], List[dict], 'ExpressionList']):
        """
        Initialize an ExpressionList object.

        :param expressions: A list of Expression objects, dictionaries, or another ExpressionList object.
        :raises ValueError: If the input is not of the expected type.
        """
        self._summary = None
        if isinstance(expressions, list):
            if all(isinstance(exp, Expression) for exp in expressions):
                self.expressions = expressions
            elif all(isinstance(exp, dict) for exp in expressions):
                self.expressions = [Expression(**exp) for exp in expressions]
            else:
                raise ValueError("All elements in the list must be of type Expression or dict")
        elif isinstance(expressions, ExpressionList):
            self.expressions = expressions.expressions
        else:
            raise ValueError("expressions must be a list of Expression objects, a list of dicts, or an ExpressionList object")

    @property
    def summary(self):
        """
        Get the summary of the term.
        """
        if self._summary is None:
            self._summary = self.get_summary()
        return self._summary

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes or list-like access to expressions.

        :param key: The key or index to retrieve.
        :return: The related object or expression.
        :raises KeyError: If the key is out of range or not found.
        """
        if isinstance(key, int):
            # If the key is an integer, treat it as a list index
            if key < 0 or key >= len(self.expressions):
                raise IndexError(f"Index '{key}' out of range for ExpressionList")
            return self.expressions[key]
        else:
            # Otherwise, treat it as a dictionary key for term IDs
            for exp in self.expressions:
                if exp.id == key:
                    return exp
            raise KeyError(f"Attribute '{key}' not found in ExpressionList")

    def __len__(self):
        """
        Return the number of expressions.

        :return: The number of expressions.
        """
        return len(self.expressions)

    def __repr__(self):
        """
        Return a string representation of the ExpressionList object.

        :return: A string representation of the ExpressionList object.
        """
        if len(self.expressions) > 0:
            return f"ExpressionList({', '.join([repr(exp) for exp in self.expressions])})"
        return "ExpressionList([])"

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method

        :param key: The term ID to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The related object if found, otherwise the default value.
        """
        for exp in self.expressions:
            if exp.id == key:
                return exp
        return default

    def get_terms(self):
        """
        Get all the related terms as a VFBTerms object.

        :return: A VFBTerms object containing all the related terms.
        """
        return VFBTerms([exp.term for exp in self.expressions], query_by_label=False)

    def get_summary(self, return_dataframe=True):
        """
        Get a summary of the expressions.

        :param return_dataframe: Whether to return the summary as a pandas DataFrame.
        :return: A summary of the expressions, either as a DataFrame or a list of dictionaries.
        """
        summary = [exp.summary for exp in self.expressions]
        if return_dataframe:
            return pandas.DataFrame(summary)
        return summary

    def where(self, term: str):
        """
        Get the expression data for a specific term.

        :param term: The term ID to match.
        :return: The related Expression object if found, otherwise None.
        """
        for exp in self.expressions:
            if exp.id == term:
                return exp
        return None

class Score:
    def __init__(self, score: float = 0.0, method: Optional[str] = None, term: Optional[str] = None):
        """
        Initialize a Score object representing a similarity score.

        :param score: The similarity score.
        :param method: The method used to compute the score.
        :param term: The ID of the related term.
        """
        self.score = score
        self.method = method
        self._term_id = term
        self._term = None # Initialize as None, will be loaded on first access

    @property
    def term(self):
        """
        Lazy-load the related term as a VFBTerm.

        :return: The related VFBTerm object.
        """
        if self._term is None:
            self._term = VFBTerm(id=self._term_id)
        return self._term

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __len__(self):
        """
        Return the length of the Score object. Always 1 as it represents a single score.

        :return: The length of the Score object.
        """
        return 1

    def __repr__(self):
        """
        Return a string representation of the Score object.

        :return: A string representation of the Score object.
        """
        return f"Score(score={self.score}, method={self.method}, term={self.term.name})"

class Partner:
    def __init__(self, weight: str = None, partner: str = None, partner_name: Optional[str] = None):
        """
        Initialize a Partner object representing a neural connection partner.

        :param weight: The connection weight.
        :param partner: The ID of the partner neuron.
        :param partner_name: Optional name of the partner neuron.
        """
        self.weight = weight
        self.id = partner
        self._partner = None # Initialize as None, will be loaded on first access
        self._partner_name = partner_name
        self._name = None # Initialize as None, will be loaded on first access

    @property
    def partner(self):
        """
        Lazy-load the partner neuron as a VFBTerm.

        :return: The related VFBTerm object.
        """
        if self._partner is None:
            self._partner = VFBTerm(id=self.id)
        return self._partner

    @property
    def name(self):
        """
        Get the name of the partner neuron.

        :return: The name of the partner neuron.
        """
        if self._name is None:
            self._name = self._partner_name if self._partner_name else self.partner.name
        return self._name

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.

        :param key: The attribute name to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The value of the attribute, or the default value if not found.
        """
        return getattr(self, key, default)

    def __len__(self):
        """
        Return the length of the Partner object. Always 1 as it represents a single partner relationship.

        :return: The length of the Partner object.
        """
        return 1

    def __getitem__(self, key):
        """
        Enable dictionary-like access to attributes.

        :param key: The attribute name to retrieve.
        :return: The value of the attribute.
        :raises KeyError: If the attribute does not exist.
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Attribute '{key}' not found in MinimalEntityInfo")

    def __repr__(self):
        """
        Return a string representation of the Partner object.

        :return: A string representation of the Partner object.
        """
        return f"Partner(weight={self.weight}, partner={self.name})"

class VFBTerm:
    """
    A class representing a Virtual Fly Brain term.
    """
    def __init__(self, id=None, term: Optional[Term] = None, related_terms: Optional[Relations] = None, channel_images: Optional[List[ChannelImage]] = None, parents: Optional[List[str]] = None, regions: Optional[List[str]] = None, counts: Optional[dict] = None, publications: Optional[List[Publication]] = None, license: Optional[Term] = None, xrefs: Optional[List[Xref]] = None, dataset: Optional[List[str]] = None, synonyms: Optional[Synonym] = None, verbose=False):
        """
        Initialize a VFBTerm object representing a Virtual Fly Brain term.

        :param id: The ID of the term.
        :param term: An optional Term object representing the core term information.
        :param related_terms: An optional Relations object representing related terms.
        :param channel_images: Optional list of ChannelImage objects.
        :param parents: Optional list of parent term IDs.
        :param regions: Optional list of region IDs.
        :param counts: Optional dictionary of term counts.
        :param publications: Optional list of Publication objects.
        :param license: Optional Term object representing the license.
        :param xrefs: Optional list of Xref objects.
        :param dataset: Optional list of dataset IDs.
        :param synonyms: Optional Synonym object.
        :param verbose: If True, print additional information.
        """
        from vfb_connect import vfb
        self.vfb = vfb
        self.debug = verbose
        if id is not None:
            if isinstance(id, list):
                id = id[0]
            print(f"\033[32mINFO:\033[0m Fetching term for {id}") if verbose else None
            self.id = id
            self.name = "unresolved"
            if self.vfb._use_cache and self.vfb._term_cache and isinstance(self.vfb._term_cache, VFBTerms) and id in self.vfb._term_cache.get_ids():
                print(f"\033[32mINFO:\033[0m Term found in cache for {id}") if verbose else None
                term_object = self.vfb._term_cache.get(id)
                if term_object:
                    self.__dict__.update(term_object.__dict__)
                    return
            json_data = self.vfb.get_TermInfo([id], summary=False)
            print("Got JSON data: ", json_data) if verbose else None
            if json_data is None:
                print("No JSON data found for ", id) if verbose else None
            else:
                if isinstance(json_data, list): # If multiple terms are returned
                    if len(json_data) > 0:
                        print(f"\033[33mWarning:\033[0m {len(id)} terms found for {id}") if len(json_data) > 1 else None
                        term_object = create_vfbterm_from_json(json_data[0], verbose=verbose)
                        self.__dict__.update(term_object.__dict__)  # Copy attributes from the fetched term object
                    else:
                        print("\033[33mWarning:\033[0m No term found for ", id) if verbose else None
                        return None
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
                    print("\033[33mWarning:\033[0m Unable to resolve term for ", id)
                    return None
        elif term is not None:
            self.term = term
            if related_terms:
                if isinstance(related_terms, list):
                    if all(isinstance(rel, Rel) for rel in related_terms):
                        self.related_terms = Relations(related_terms)
                    elif all(isinstance(rel, dict) for rel in related_terms):
                        self.related_terms = Relations([Rel(**rel) for rel in related_terms])
                    else:
                        raise ValueError("All elements in the list must be of type Rel")
                elif isinstance(related_terms, Relations):
                    self.related_terms = related_terms
            else:
                self.related_terms = Relations([])
            for rel in self.related_terms:
                attr_name = rel.relation.type.replace(' ', '_')
                if not hasattr(self, attr_name):
                    if verbose:
                        print(f"Adding related_term as a property for {attr_name}")
                    setattr(self, attr_name, [rel._object_name])
                else:
                    if verbose:
                        print(f"Adding term to {attr_name}")
                    getattr(self, attr_name).append(rel._object_name)
            self.channel_images = channel_images
            self._summary = None
            self.name = self.term.core.name
            self.id = self.term.core.short_form
            self.types = self.term.core.unique_facets
            self.description = self.term.description
            self.url = self.term.link

            self._parents_ids = parents
            self._parents = None  # Initialize as None, will be loaded on first access

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
                for xref in xrefs:
                    if xref.is_data_source:
                        self.data_source = xref.site_name
                        self.xref_id = xref.id
                        self.xref_accession = xref.accession if hasattr(xref, 'accession') else None
                        self.xref_url = xref.link if hasattr(xref, 'link') and xref.link else xref.homepage
                        self.xref_name = xref.name

            if synonyms:
                self.synonyms = synonyms

            self._instances = None
            self._instances_ids = None
            self._instances_names = None
            self._return_type = self.vfb._return_type # Default to global version but can be set to id, name (list) or full (VFBTerms)
            self._skeleton = None
            self._mesh = None
            self._volume = None

            # Set flags for different types of terms
            self.is_type = self.has_tag('Class')
            self.is_instance = self.has_tag('Individual')
            self.is_template = self.has_tag('Template')
            self.is_dataset = self.has_tag('DataSet')
            self.is_neuron = self.has_tag('Neuron')
            self.has_image = self.has_tag('has_image')
            self.has_scRNAseq = self.has_tag('hasScRNAseq')
            self.has_neuron_connectivity = self.has_tag('has_neuron_connectivity')
            self.has_region_connectivity = self.has_tag('has_region_connectivity')

            self._gene_function_filters = self.vfb.get_gene_function_filters()

            if self.is_template:
                self._regions_ids = regions
                self._regions = None  # Initialize as None, will be loaded on first access
                self.add_template_properties()

            if self.is_instance:
                self._dataset_ids = dataset
                self._datasets = None  # Initialize as None, will be loaded on first access
                self.add_instance_properties()
                if self.channel_images and len(self.channel_images) > 0:
                    for ci in self.channel_images:
                        if hasattr(ci.image, 'image_obj') and ci.image.image_obj and 'volume_man.obj' in ci.image.image_obj:
                            if not self._mesh:
                                self.add_mesh_property()
                        if hasattr(ci.image, 'image_nrrd') and ci.image.image_nrrd and 'volume.nrrd' in ci.image.image_nrrd:
                            if not self._volume:
                                self.add_volume_property()
                        if self._volume and self._mesh:
                            break

            if self.is_type:
                self._subtypes = None  # Initialize as None, will be loaded on first access
                self._subparts = None  # Initialize as None, will be loaded on first access
                self._children = None  # Initialize as None, will be loaded on first access
                self.add_type_properties()

            if self.is_neuron:
                self._similar_neurons_nblast = None  # Initialize as None, will be loaded on first access
                self._potential_drivers_nblast = None  # Initialize as None, will be loaded on first access
                self._potential_drivers_neuronbridge = None  # Initialize as None, will be loaded on first access
                self.add_neuron_properties()

            if any(self.has_tag(tag) for tag in neuron_containing_anatomy_tags):
                self._neurons_that_overlap = None
                self._neurons_with_synaptic_terminals_here = None
                self._downstream_neurons = None
                self._upstream_neurons = None
                self._upstream_neuron_types = None
                self._downstream_neuron_types = None
                self._neuron_types_that_overlap = None
                self._neuron_types_with_synaptic_terminals_here = None
                self.add_anatomy_containing_neurons()

            if self.has_tag('Cluster'):
                self._scRNAseq_genes = None
                self.add_cluster_properties()

            if self.has_tag('hasScRNAseq'):
                self._scRNAseq_expression = None
                self.add_scRNAseq_expression_properties()

            if self.has_tag('Anatomy') and self.is_type:
                self._transgene_expression = None
                self._innervating = None
                self.add_anatomy_type_properties()
                self._lineage_clones = None
                self._lineage_clone_types = None
                self.add_lineage_clone_properties()

            # Set the lineage property if it has a lineage tag
            if 'lineage_' in ''.join(self.term.core.types):
                for tag in self.term.core.types:
                    if 'lineage_' in tag:
                        lineage = tag.split('_')[1]
                        id = self.vfb.lookup_id(lineage + ' lineage neuron')
                        if id:
                            self.lineage = self.vfb.term(id)
                            print(f"Lineage term: {self.lineage}") if verbose else None
                            break

            if self.vfb._use_cache:
                if isinstance(self.vfb._term_cache, VFBTerms):
                    print("Adding term to cache...") if verbose else None
                    self.vfb._term_cache.append(self)
                else:
                    print("Creating new cache...") if verbose else None
                    self.vfb._term_cache = VFBTerms(self)
            self._load_complete = True

    @property
    def parents(self):
        """
        Get the parents of this term. In order of specificity.
        """
        if self._parents is None:
            print("Loading parents for the first time...") if self.debug else None
            self._parents = VFBTerms(self._parents_ids, query_by_label=False) if self._parents_ids else None
        return self._parents

    def add_anatomy_type_properties(self):
        @property
        def transgene_expression(self):
            """
            Get the transgene expression data associated with this anatomy type term.
            """
            if self._transgene_expression is None:
                print("Loading transgene expression for the first time...") if self.debug else None
                subclasses = self.vfb.oc.get_subclasses(query=f"'{self.id}'", verbose=self.debug)
                print("Subclasses: ", subclasses) if self.debug else None
                overlapping_cells = self.vfb.oc.get_subclasses(query=f"'cell' that 'overlaps' some '{self.id}'", verbose=self.debug)
                print("Overlapping cells: ", overlapping_cells) if self.debug else None
                part_of = self.vfb.oc.get_subclasses(query=f"'is part of' some '{self.id}'", verbose=self.debug)
                print("Part of: ", part_of) if self.debug else None
                all_anatomy = subclasses + overlapping_cells + part_of + [self.id]
                print("All anatomy: ", all_anatomy) if self.debug else None
                result = dict_cursor(self.vfb.nc.commit_list([f"MATCH (ep:Class:Expression_pattern)<-[ar:overlaps|part_of]-(:Individual)-[:INSTANCEOF]->(anat:Class) WHERE anat.short_form in {all_anatomy} WITH DISTINCT collect(DISTINCT ar.pub[0]) as pubs, anat, ep OPTIONAL MATCH (pub:pub) WHERE pub.short_form IN pubs RETURN distinct ep.short_form as term, coalesce(ep.symbol, ep.label) as term_name, anat.short_form as type, coalesce(anat.symbol, anat.label) as type_name, collect(pub) as pubs"]))
                print("Result: ", result) if self.debug else None
                if result:
                    self._transgene_expression = ExpressionList([Expression(term=exp['term'], term_name=exp['term_name'], term_type='transgene', type=exp['type'], type_name=exp['type_name'], reference=[Publication(FlyBase=pub.get('FlyBase',''), PubMed=pub.get('PMID',''), DOI=pub.get('DOI', ''), core=MinimalEntityInfo(short_form=pub['short_form'], label=pub['label'], iri=pub['iri'], types=pub['label'], symbol=','.join(pub['miniref'][0].split(',')[:2])), description=pub['title']) for pub in exp['pubs']]) for exp in result])
                else:
                    self._transgene_expression = ExpressionList([])
                print(f"Transgene expression: {repr(self._transgene_expression)}") if self.debug else None
            return self._transgene_expression

        @property
        def innervating(self):
            """
            Get the innervating nerves or tracts associated with this term.
            """
            if self._innervating is None:
                print("Loading innervating neurons/tracts for the first time...") if self.debug else None
                self._innervating = self.vfb.owl_subclasses(query=f"'neuron projection bundle' and 'innervates' some '{self.id}'", return_dataframe=False, verbose=self.debug)
            return self._innervating

        # Dynamically add the property to the instance
        setattr(self.__class__, 'transgene_expression', transgene_expression)
        setattr(self.__class__, 'innervating', innervating)

    def add_lineage_clone_properties(self):
        @property
        def lineage_clones(self):
            """
            Get the lineage clones associated with this term.
            """
            if self._lineage_clones is None:
                print("Loading lineage clones for the first time...") if self.debug else None
                ids = self.vfb.oc.get_instances(query=f"'neuroblast lineage clone' and 'overlaps' some '{self.id}'", verbose=self.debug)
                self._lineage_clones = VFBTerms(ids, verbose=self.debug)
            return self._lineage_clones

        @property
        def lineage_clone_types(self):
            """
            Get the lineage clone types associated with this term.
            """
            if self._lineage_clone_types is None:
                print("Loading lineage clones for the first time...") if self.debug else None
                ids = self.vfb.oc.get_subclasses(query=f"'neuroblast lineage clone' and 'overlaps' some '{self.id}'", verbose=self.debug)
                self._lineage_clone_types = VFBTerms(ids, verbose=self.debug)
            return self._lineage_clone_types

        # Dynamically add the property to the instance
        setattr(self.__class__, 'lineage_clones', lineage_clones)
        setattr(self.__class__, 'lineage_clone_types', lineage_clone_types)

    def add_template_properties(self):
        @property
        def regions(self):
            if self._regions is None:
                print("Loading regions for the first time...") if self.debug else None
                self._regions = VFBTerms(self._regions_ids, query_by_label=False) if self._regions_ids else None
            return self._regions

        # Dynamically add the property to the instance
        setattr(self.__class__, 'regions', regions)

    def add_scRNAseq_expression_properties(self):
        @property
        def scRNAseq_expression(self):
            """
            Get the scRNAseq expression data associated with this term.
            """
            if self._scRNAseq_expression is None:
                print("Loading scRNAseq expression for the first time...") if self.debug else None
                exp_list = ExpressionList([Expression(term=exp['cluster']['short_form'], 
                                                      term_name=exp['cluster']['symbol'] if exp['cluster']['symbol'] else exp['cluster']['label'], 
                                                      term_type='cluster', reference=Publication(**exp['pubs'][0]), dataset=VFBTerm(exp['dataset']['short_form'])
                                                      ) for exp in self.vfb.get_scRNAseq_expression(id=self.id, return_id_only=False, return_dataframe=False)])
                self._scRNAseq_expression = exp_list
            return self._scRNAseq_expression

        # Dynamically add the property to the instance
        setattr(self.__class__, 'scRNAseq_expression', scRNAseq_expression)


    def add_cluster_properties(self):
        @property
        def scRNAseq_genes(self):
            """
            Get the genes associated with this cluster.
            """
            if self._scRNAseq_genes is None:
                print("Loading scRNAseq genes for the first time...") if self.debug else None
                exp_list = self.vfb.get_scRNAseq_gene_expression(cluster=self.id, return_id_only=False, return_dataframe=False)
                self._scRNAseq_genes = ExpressionList([Expression(term=exp['gene']['short_form'], term_name=exp['gene']['symbol'] if exp['gene']['symbol'] else exp['gene']['label'], term_type='gene', type=exp['anatomy']['short_form'], type_name=exp['anatomy']['symbol'] if exp['anatomy']['symbol'] else exp['anatomy']['label'], expression_extent=float(exp['expression_extent']), expression_level=float(exp['expression_level'])) for exp in exp_list])
            return self._scRNAseq_genes

        # Dynamically add the property to the instance
        setattr(self.__class__, 'scRNAseq_genes', scRNAseq_genes)

    @property
    def instances(self, return_type=None):
        """
        Get the instances of this term. The return type can be specified to 
        return only IDs, only names, or the full instance details.
        
        Parameters:
        - return_type (str): Determines the type of data to return. 
        Options are 'full', 'id', or 'name'. Default is 'full'.
        
        Returns:
        - list: A list of instances or their IDs/names based on the return_type.
        """
        if not return_type:
            return_type = self._return_type
        print(f"Getting {return_type}...") if self.debug else None
        if self._instances_ids is None:
            print("Loading instances ids for the first time...")
            if self.has_tag('Class'):
                print("Loading instances for class: ", self.name) if self.debug else None
                self._instances_ids = self.vfb.get_instances(class_expression=f"'{self.id}'", return_id_only=True)
            elif self.has_tag('DataSet'):
                print("Loading instances for dataset: ", self.name) if self.debug else None
                print(f"Loading {self.counts['images'] if self.counts and 'images' in self.counts.keys() else ''} instances for dataset: {self.name}...")
                self._instances_ids = self.vfb.get_instances_by_dataset(dataset=self.id, return_id_only=True)
            elif self.has_tag('API'):
                print("Loading instances for API: ", self.name) if self.debug else None
                self._instances_ids = [r['id'] for r in self.vfb.cypher_query(query="MATCH (a:API {short_form:'" + self.id + "'})<-[:database_cross_reference]-(i:Individual) RETURN i.short_form as id", return_dataframe=False)]
            elif self.has_tag('Site'):
                print("Loading instances for site: ", self.name) if self.debug else None
                results = self.vfb.cypher_query(query="MATCH (a:Site {short_form:'" + self.id + "'})<-[:database_cross_reference]-(i:Individual) RETURN i.short_form as id", return_dataframe=False)
                print(f"Results: {results}") if self.debug else None
                self._instances_ids = [r['id'] for r in results]
            if self._instances_ids and len(self._instances_ids) > 0:
                self.has_image = True
        print(f"Got {len(self._instances_ids)} instances...") if self.debug else None
        if return_type == 'id':
            return self._instances_ids
        if return_type == 'name':
            if not self._instances_names:
                self._instances_names = self.vfb.lookup_name(self._instances_ids)
            print(f"Got {len(self._instances_names)} instance names...") if self.debug else None
            return self._instances_names
        if self._instances is None:
            print("Creating instances for the first time...")
            self._instances = VFBTerms(self._instances_ids, verbose=self.debug, query_by_label=False)
        print(f"Got {len(self._instances)} instances...") if self.debug else None
        return self._instances

    @property
    def summary(self):
        """
        Get the summary of the term.
        """
        if self._summary is None:
            self._summary = self.get_summary()
        return self._summary

    def add_instance_properties(self):
        @property
        def datasets(self):
            """
            Get the datasets associated with this instance.
            """
            if self._datasets is None:
                print("Loading datasets for the first time...") if self.debug else None
                self._datasets = VFBTerms(self._dataset_ids, query_by_label=False) if self._dataset_ids else None
            return self._datasets

        # Dynamically add the property to the instance
        setattr(self.__class__, 'datasets', datasets)

    def add_type_properties(self):
        @property
        def subtypes(self):
            """
            Get the subtypes of this term.
            """
            if self._subtypes is None:
                print("Loading subtypes for the first time...") if self.debug else None
                self._subtypes = VFBTerms(self.vfb.oc.get_subclasses(query=f"'{self.id}'", ), query_by_label=False)
            return self._subtypes

        @property
        def subparts(self):
            """
            Get the subparts of this term.
            """
            if self._subparts is None:
                print("Loading subparts for the first time...") if self.debug else None
                self._subparts = VFBTerms(self.vfb.oc.get_subclasses(query=f"'is part of' some '{self.id}'"), query_by_label=False)
            return self._subparts

        @property
        def children(self):
            """
            Get the children of this term. This is a combination or subtypes and subparts.
            """
            if self._children is None:
                print("Loading children for the first time...") if self.debug else None
                self._children = self.subtypes + self.subparts
            return self._children

        # Dynamically add the property to the instance
        setattr(self.__class__, 'subtypes', subtypes)
        setattr(self.__class__, 'subparts', subparts)
        setattr(self.__class__, 'children', children)

    def add_anatomy_containing_neurons(self):
        @property
        def neuron_types_that_overlap(self):
            """
            Get the types of neurons that overlap this region.
            """
            # If not a type then run the query against the first parent type
            if self._neuron_types_that_overlap is None:
                # If not a type then run the query against the first parent type
                if self.is_type:
                    id = self.id
                else:
                    id = self.parents[0].id
                    print("Running query against parent type: ", self.parents[0].name)
                print(f"Loading neuron types that overlap {self.name} for the first time...") if self.debug else None
                self._neuron_types_that_overlap = VFBTerms(terms=self.vfb.oc.get_subclasses(f"'neuron' that 'overlaps' some '{id}'", query_by_label=True))
            return self._neuron_types_that_overlap

        @property
        def neuron_types_with_synaptic_terminals_here(self):
            """
            Get the types of neurons that have synaptic terminals in this region.
            """
            # If not a type then run the query against the first parent type
            if self._neuron_types_with_synaptic_terminals_here is None:
                # If not a type then run the query against the first parent type
                if self.is_type:
                    id = self.id
                else:
                    id = self.parents[0].id
                    print("Running query against parent type: ", self.parents[0].name)
                print(f"Loading neuron types with synaptic terminals in {self.name} for the first time...") if self.debug else None
                self._neuron_types_with_synaptic_terminals_here = VFBTerms(terms=self.vfb.oc.get_subclasses(f"'neuron' that 'has synaptic terminal in' some '{id}'", query_by_label=True))
            return self._neuron_types_with_synaptic_terminals_here

        @property
        def neurons_that_overlap(self):
            """
            Get the neurons that overlap this region.
            """
            # If not a type then run the query against the first parent type
            if self._neurons_that_overlap is None:
                # If not a type then run the query against the first parent type
                if self.is_type:
                    id = self.id
                else:
                    id = self.parents[0].id
                    print("Running query against parent type: ", self.parents[0].name)
                print(f"Loading neurons that overlap {self.name} for the first time...") if self.debug else None
                self._neurons_that_overlap = VFBTerms(terms=self.vfb.oc.get_instances(f"'neuron' that 'overlaps' some '{id}'", query_by_label=True))
            return self._neurons_that_overlap

        @property
        def neurons_with_synaptic_terminals_here(self):
            """
            Get the neurons that have synaptic terminals in this region. Based on literature.
            """
            if self._neurons_with_synaptic_terminals_here is None:
                # If not a type then run the query against the first parent type
                if self.is_type:
                    id = self.id
                else:
                    id = self.parents[0].id
                    print("Running query against parent type: ", self.parents[0].name)
                print(f"Loading neurons with synaptic terminals in {self.name} for the first time...") if self.debug else None
                self._neurons_with_synaptic_terminals_here = VFBTerms(terms=self.vfb.oc.get_instances(f"'neuron' that 'has synaptic terminal in' some '{id}'", query_by_label=True))
            return self._neurons_with_synaptic_terminals_here

        @property
        def downstream_neurons(self):
            """
            Get the neurons that have presynaptic terminals in this region. Based on literature.
            """
            if self._downstream_neurons is None:
                # If not a type then run the query against the first parent type
                if self.is_type:
                    id = self.id
                else:
                    id = self.parents[0].id
                    print("Running query against parent type: ", self.parents[0].name)
                print(f"Loading downstream neurons for the first time...") if self.debug else None
                self._downstream_neurons = VFBTerms(terms=self.vfb.oc.get_instances(f"'neuron' that 'has presynaptic terminals in' some '{id}'", query_by_label=True))
            return self._downstream_neurons

        @property
        def upstream_neurons(self):
            """
            Get the neurons that have postsynaptic terminals in this region. Based on literature.
            """

            if self._upstream_neurons is None:
                # If not a type then run the query against the first parent type
                if self.is_type:
                    id = self.id
                else:
                    id = self.parents[0].id
                    print("Running query against parent type: ", self.parents[0].name)
                print(f"Loading upstream neurons for the first time...") if self.debug else None
                self._upstream_neurons = VFBTerms(terms=self.vfb.oc.get_instances(f"'neuron' that 'has postsynaptic terminal in' some '{id}'", query_by_label=True))
            return self._upstream_neurons

        @property
        def downstream_neuron_types(self):
            """
            Get the types of neurons that have presynaptic terminals in this region. Based on literature.
            """
            if self._downstream_neuron_types is None:
                # If not a type then run the query against the first parent type
                if self.is_type:
                    id = self.id
                else:
                    id = self.parents[0].id
                    print("Running query against parent type: ", self.parents[0].name)
                print(f"Loading downstream neuron types for the first time...") if self.debug else None
                self._downstream_neuron_types = VFBTerms(terms=self.vfb.oc.get_subclasses(f"'neuron' that 'has presynaptic terminals in' some '{id}'", query_by_label=True))
            return self._downstream_neuron_types

        @property
        def upstream_neuron_types(self):
            """
            Get the types of neurons that have postsynaptic terminals in this region. Based on literature.
            """
            if self._upstream_neuron_types is None:
                # If not a type then run the query against the first parent type
                if self.is_type:
                    id = self.id
                else:
                    id = self.parents[0].id
                    print("Running query against parent type: ", self.parents[0].name)
                print(f"Loading upstream neuron types for the first time...") if self.debug else None
                self._upstream_neuron_types = VFBTerms(terms=self.vfb.oc.get_subclasses(f"'neuron' that 'has postsynaptic terminal in' some '{id}'", query_by_label=True))
            return self._upstream_neuron_types

        # Dynamically add the property to the instance
        setattr(self.__class__, 'neurons_that_overlap', neurons_that_overlap)
        setattr(self.__class__, 'neurons_with_synaptic_terminals_here', neurons_with_synaptic_terminals_here)
        setattr(self.__class__, 'downstream_neurons', downstream_neurons)
        setattr(self.__class__, 'upstream_neurons', upstream_neurons)
        setattr(self.__class__, 'neuron_types_that_overlap', neuron_types_that_overlap)
        setattr(self.__class__, 'neuron_types_with_synaptic_terminals_here', neuron_types_with_synaptic_terminals_here)
        setattr(self.__class__, 'downstream_neuron_types', downstream_neuron_types)
        setattr(self.__class__, 'upstream_neuron_types', upstream_neuron_types)

    def add_neuron_properties(self):
        @property
        def similar_neurons_nblast(self):
            """
            Get neurons similar to this neuron based on NBLAST scores.
            """
            if self._similar_neurons_nblast is None:
                print("Loading similar neurons for the first time...") if self.debug else None
                if not self.has_tag('NBLAST'):
                    return None
                method = 'NBLAST_score'
                results = self.vfb.get_similar_neurons(neuron=self.id, similarity_score=method, query_by_label=False, return_dataframe=False)
                results_dict = [{"score": item['score'], "method": method, "term": item['id']} for item in results]
                self._similar_neurons_nblast = [Score(**dict) for dict in results_dict]
                if not self._similar_neurons_nblast:
                    print("No similar neurons found!")
                    self._similar_neurons_nblast = []
            return self._similar_neurons_nblast

        # @property
        # def similar_neurons_neuronbridge(self):
        #     """
        #     Get neurons similar to this neuron based on NeuronBridge scores.
        #     """
        #     if self._similar_neurons_neuronbridge is None:
        #         print("Loading similar neurons for the first time...") if self.debug else None
        #         if not self.has_tag('neuronbridge'):
        #             return None
        #         method = 'neuronbridge_score'
        #         results = self.vfb.get_similar_neurons(neuron=self.id, similarity_score=method, query_by_label=False, return_dataframe=False)
        #         results_dict = [{"score": item['score'], "method": method, "term": item['id']} for item in results]
        #         self._similar_neurons_neuronbridge = [Score(**dict) for dict in results_dict]
        #     return self._similar_neurons_neuronbridge

        @property
        def potential_drivers_nblast(self):
            """
            Get neurons that are potential drivers of this neuron based on NBLAST scores.
            """
            if self._potential_drivers_nblast is None:
                print("Loading potential drivers for the first time...") if self.debug else None
                if not self.has_tag('NBLASTexp'):
                    return None
                method = 'NBLAST_score'
                results = self.vfb.get_potential_drivers(neuron=self.id, similarity_score=method, query_by_label=False, return_dataframe=False)
                results_dict = [{"score": item['score'], "method": method, "term": item['id']} for item in results]
                self._potential_drivers_nblast = [Score(**dict) for dict in results_dict]
                if not self._potential_drivers_nblast:
                    print("No potential drivers found!")
                    self._potential_drivers_nblast = []
            return self._potential_drivers_nblast

        @property
        def potential_drivers_neuronbridge(self):
            """
            Get neurons that are potential drivers of this neuron based on NeuronBridge scores.
            """
            if self._potential_drivers_neuronbridge is None:
                print("Loading potential drivers for the first time...") if self.debug else None
                if not self.has_tag('neuronbridge'):
                    return None
                method = 'neuronbridge_score'
                results = self.vfb.get_potential_drivers(neuron=self.id, similarity_score=method, query_by_label=False, return_dataframe=False)
                results_dict = [{"score": item['score'], "method": method, "term": item['id']} for item in results]
                self._potential_drivers_neuronbridge = [Score(**dict) for dict in results_dict]
                if not self._potential_drivers_neuronbridge:
                    print("No potential drivers found!")
                    self._potential_drivers_neuronbridge = []
            return self._potential_drivers_neuronbridge

        @property
        def skeleton(self):
            """
            Get the skeleton of this neuron.
            """
            if not self._skeleton:
                print("Loading skeleton for the first time...") if self.debug else None
                self.load_skeleton()
            return self._skeleton

        # Dynamically add the property to the instance
        setattr(self.__class__, 'similar_neurons_nblast', similar_neurons_nblast)
        # setattr(self.__class__, 'similar_neurons_neuronbridge', similar_neurons_neuronbridge)
        setattr(self.__class__, 'potential_drivers_nblast', potential_drivers_nblast)
        setattr(self.__class__, 'potential_drivers_neuronbridge', potential_drivers_neuronbridge)
        setattr(self.__class__, 'skeleton', skeleton)

    def add_mesh_property(self):
        @property
        def mesh(self):
            """
            Get the mesh of this neuron.
            """
            if not self._mesh:
                print("Loading mesh for the first time...") if self.debug else None
                self.load_mesh()
            return self._mesh

        setattr(self.__class__, 'mesh', mesh)

    def add_volume_property(self):
        @property
        def volume(self):
            """
            Get the volume of this neuron.
            """
            if not self._volume:
                print("Loading volume for the first time...") if self.debug else None
                self.load_volume()
            return self._volume

        setattr(self.__class__, 'volume', volume)

    def __repr__(self):
        return f"VFBTerm(term={repr(self.term)})"

    def __getitem__(self, index):
        if index != 0:
            print("VFBTerm only has one item")
            return VFBTerms([self])
        return self

    def __setattr__(self, name, value):
        # Set the attribute using the parent class's method
        super().__setattr__(name, value)

        # If use_cache is enabled, update the cache with the latest attribute changes
        if hasattr(self,'_load_complete') and self.vfb._use_cache and self._load_complete:
            print(f"Updating cache due to change in attribute '{name}'...") if self.debug else None
            self.update_cache()

    def update_cache(self):
        # Logic to update the cache with the current object state
        if self.vfb._use_cache:
            if isinstance(self.vfb._term_cache, VFBTerms):
                existing_term = self.vfb._term_cache.get(self.id)
                if existing_term:
                    existing_term.__dict__.update(self.__dict__)
                else:
                    self.vfb._term_cache.append(self)
            else:
                self.vfb._term_cache = VFBTerms()
                self.vfb._term_cache.append(self)

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)

    def __len__(self):
        """
        Get the length of the term.
        """
        return 1

    def __eq__(self, other):
        """
        Check if two terms are equal.
        """
        if isinstance(other, VFBTerm):
            return self.id == other.id
        return False

    def __hash__(self):
        """
        Get the hash of the term.
        """
        return hash(self.id)

    def __str__(self):
        """
        Get the string representation of the term.
        """
        return self.name

    def __lt__(self, other):
        """
        Check if one term is less than another.
        """
        if isinstance(other, VFBTerm):
            return self.name < other.name
        return False

    def __gt__(self, other):
        """
        Check if one term is greater than another.
        """
        if isinstance(other, VFBTerm):
            return self.name > other.name
        return False

    def __le__(self, other):
        """
        Check if one term is less than or equal to another.
        """
        if isinstance(other, VFBTerm):
            return self.name <= other.name
        return False

    def __ge__(self, other):
        """
        Check if one term is greater than or equal to another.
        """
        if isinstance(other, VFBTerm):
            return self.name >= other.name
        return False

    def __ne__(self, other):
        """
        Check if two terms are not equal.
        """
        return not self.__eq__(other)

    def __contains__(self, item):
        """
        Check if an item is in the term.
        """
        return item in self.__dict__.keys()

    def __eq__(self, value: object) -> bool:
        """
        Check if two terms are equal.
        """
        if isinstance(value, VFBTerm):
            return self.id == value.id
        if isinstance(value, str):
            if self.id == value:
                return True
            if self.name == value:
                return True
            if self.core.label == value:
                return True
            if self.core.symbol == value:
                return True
        return False

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
            remaining_terms = VFBTerms([term for term in [self.term] if term.id not in other_ids], query_by_label=False)
            print ("Remaining ", remaining_terms.get_ids()) if verbose else None
            return remaining_terms
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("Removing ", other.id) if verbose else None
            remaining_terms = VFBTerms([term for term in [self.term] if term.id != other.id], query_by_label=False)
            return remaining_terms
        raise TypeError("Unsupported operand type(s) for -: 'VFBTerms' and '{}'".format(type(other).__name__))

    def __dir__(self):
        return [attr for attr in list(self.__dict__.keys()) if not attr.startswith('_')] + [attr for attr in dir(self.__class__) if not attr.startswith('_') and not attr.startswith('get') and not attr.startswith('add_')]

    def downstream_partners(self, weight=0, classification=None, verbose=False):
        """
        Get neurons downstream of this neuron. Based on individual connectomic data.
        """
        print("Getting downstream partners for ", self.name) if verbose else None
        results = self.vfb.get_neurons_downstream_of(neuron=self.id, weight=weight, classification=classification, query_by_label=False,
                                  return_dataframe=False,verbose=verbose)
        print("Results: ", results) if verbose else None
        dicts = [{"weight": item['weight'], "partner": item['target_neuron_id'], "partner_name": item['target_neuron_name']} for item in results]
        print("Dict: ", dict) if verbose else None
        return [Partner(**dict) for dict in dicts]

    def upstream_partners(self, weight=0, classification=None, verbose=False):
        """
        Get neurons upstream of this neuron. Based on individual connectomic data.
        """
        print("Getting upstream partners for ", self.name) if verbose else None
        results = self.vfb.get_neurons_upstream_of(neuron=self.id, weight=weight, classification=classification, query_by_label=False,
                                  return_dataframe=False,verbose=verbose)
        print("Results: ", results) if verbose else None
        dicts = [{"weight": item['weight'], "partner": item['query_neuron_id'], "partner_name": item['query_neuron_name']} for item in results]
        print("Dict: ", dict) if verbose else None
        return [Partner(**dict) for dict in dicts]
    
    def get_transcriptomic_profile(self, gene_type=False, query_by_label=True, return_dataframe=False, verbose=False):
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
        if gene_type:
            print(f"Getting transcriptomic profile filterd by {gene_type}") if verbose else None
            if gene_type not in self._gene_function_filters:
                raise KeyError(f"Gene function '{gene_type}' not found. Please use one of: {', '.join(self._gene_function_filters)}")
        if self.is_type:
            cell_type = self.id
            print(f"Getting transcriptomic profile for {self.name} ({cell_type})") if verbose else None
        else:
            cell_type = self.parents[0].id
            print("Running query against parent type: ", self.parents[0].name)
        result = self.vfb.get_transcriptomic_profile(cell_type=cell_type, gene_type=gene_type, query_by_label=query_by_label, return_dataframe=False)
        print("Result: ", result) if verbose else None
        expression_list = ExpressionList([Expression(term=exp['gene_id'], term_name=exp['gene'], term_type='gene', type=exp['cell_type_id'], type_name=exp['cell_type'], 
                                                     expression_extent=exp['extent'], expression_level=exp['level'], sex=exp['sample_sex'], tissue=exp['sample_tissue'], 
                                                     reference=exp['ref'], function=exp['function']) for exp in result])
        print("Expression list: ", expression_list) if verbose else None
        if return_dataframe:
            return expression_list.get_summary(return_dataframe=True)
        return expression_list

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
        if hasattr(self, "_instances_names") and self._instances_names:
            summary["instances"] = self._instances_names
        elif hasattr(self, "_instances_ids") and self._instances_ids:
            summary["instances"] = self.vfb.lookup_name(self._instances_ids)
        if hasattr(self, "_parents") and self._parents:
            summary["Parents"] = self.parents.get_names()
        elif hasattr(self, "_parents_ids") and self._parents_ids:
            summary["Parents"] = self.vfb.lookup_name(self._parents_ids)
        if hasattr(self, "_regions") and self._regions:
            summary["Regions"] = self.regions.get_names()
        elif hasattr(self, "_regions_ids") and self._regions_ids:
            summary["Regions"] = self.vfb.lookup_name(self._regions_ids)
        if hasattr(self, "counts") and self.counts:
            summary["Counts"] = self.counts
        if hasattr(self, "publications") and self.publications:
            summary["Publications"] = [str(pub.core.name) for pub in self.publications]
        if hasattr(self, "license") and self.license:
            summary["License"] = self.license.core.name
        if hasattr(self, "xrefs") and self.xrefs:
            summary["Cross References"] = [str(xref.link) for xref in self.xrefs]
        if hasattr(self, "_datasets") and self._datasets:
            summary["Datasets"] = self.datasets.get_names()
        elif hasattr(self, "_dataset_ids") and self._dataset_ids:
            summary["Datasets"] = self.vfb.lookup_name(self._dataset_ids)
        if return_dataframe:
            return pandas.DataFrame([summary])

        return summary

    def has_tag(self, tag):
        return tag in self.term.core.types

    def load_skeleton(self, template=None, verbose=False, query_by_label=True, force_reload=False, allow_multiple=False):
        """
        Load the navis skeleton from each available image in the term.

        Parameters
        ----------
        template : str
            The template to load the skeleton for. If not provided, the first available skeleton will be loaded.
        verbose : bool
            Whether to print out information about the loading process.
        query_by_label : bool
            Whether to resolve the template by label.
        force_reload : bool
            Whether to force a reload of the skeleton.
        allow_multiple : bool
            Whether to allow multiple skeletons to be loaded.
        """
        selected_template = None
        template = self.get_default_template(template=template)
        if self.has_tag('Neuron'):
            if template:
                if query_by_label:
                    selected_template = self.vfb.lookup_id(template)
                    print("Template (", template, ") resolved to id ", selected_template) if verbose else None
                else:
                    selected_template = template
                print("Loading skeleton for ", self.name, " aligned to ", template) if verbose else None
                skeletons = [ci.image.get_skeleton() for ci in self.channel_images if ci.image.template_anatomy.short_form == selected_template] if self.channel_images else None
                if skeletons:
                    self._skeleton = skeletons[0]
                    self._skeleton_template = selected_template
            else:
                print("Loading skeletons for ", self.name) if verbose else None
                print("Processinng channel images: ", self.channel_images) if verbose else None
                if self.channel_images:
                    self._skeleton = [ci.image.get_skeleton() for ci in self.channel_images]
                    self._skeleton_template = self.channel_images[0].image.template_anatomy.short_form
                else:
                    self._skeleton = None
            if self._skeleton:
                if isinstance(self._skeleton, list):
                    self._skeleton = [item for item in self._skeleton if item is not None]
                    for skeleton in self._skeleton:
                        skeleton.name = self.name
                        skeleton.label = self.name
                        skeleton.id = self.id
                    if len(self._skeleton) > 1:
                        if not allow_multiple:
                            print("Multiple skeletons found for", self.name, "Please run \033[35mZZZZ.load_skeleton(template='XXXX')\033[0m to load the correct neuron skeleton.")
                            print("Available templates:", [ci.image.template_anatomy.name for ci in self.channel_images])
                            self._skeleton = None
                    elif len(self._skeleton) == 1:
                        print("Skeleton found for", self.name) if verbose else None
                        self._skeleton = self._skeleton[0]
                else:
                    print("Skeleton found for", self.name) if verbose else None
                    self._skeleton.name = self.name
                    self._skeleton.label = self.name
                    self._skeleton.id = self.id
        else:
            print(f"{self.name} is not a neuron") if verbose else None

    def load_mesh(self, template=None, verbose=False, query_by_label=True, force_reload=False, allow_multiple=False):
        """
        Load the navis mesh from each available image in the term.

        Parameters
        ----------
        template : str
            The template to load the mesh for. If not provided, the first available mesh will be loaded.
        verbose : bool
            Whether to print out information about the loading process.
        query_by_label : bool
            Whether to resolve the template by label.
        force_reload : bool
            Whether to force a reload of the mesh.
        allow_multiple : bool
            Whether to allow multiple meshes to be loaded.
        """
        selected_template = None
        template = self.get_default_template(template=template)
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
            else:
                selected_template = template
            print("Loading mesh for ", self.name, " aligned to ", template) if verbose else None
            mesh = [ci.image.get_mesh(verbose=verbose, output='neuron' if self.has_tag('Neuron') else 'volume') for ci in self.channel_images if ci.image.template_anatomy.short_form == selected_template] if self.channel_images else None
            if mesh:
                self._mesh = mesh[0]
        else:
            print("Loading meshes for ", self.name) if verbose else None
            self._mesh = [ci.image.get_mesh(verbose=verbose, output='neuron' if self.has_tag('Neuron') else 'volume') for ci in self.channel_images] if self.channel_images else None
        if self._mesh:
            if isinstance(self._mesh, list):
                print("Processing meshes: ", self._mesh) if verbose else None
                self._mesh = [item for item in self._mesh if item is not None]
                print(len(self._mesh), " Meshes found: ", self._mesh) if verbose else None
                for mesh in self._mesh:
                    mesh.name = self.name
                    mesh.label = self.name
                    mesh.id = self.id
                if len(self._mesh) > 1:
                    if not allow_multiple:
                        print("Multiple meshes found for ", self.name, ". Please run \033[35mZZZZ.load_mesh(template='XXXX')\033[0m to load the correct mesh.")
                        print("Available templates: ", [ci.image.template_anatomy.name.replace('_c','') for ci in self.channel_images])
                        self._mesh = None
                elif len(self._mesh) == 1:
                    print("Single mesh loaded for ", self.name) if verbose else None
                    self._mesh = self._mesh[0]
            else:
                self._mesh.name = self.name
                self._mesh.label = self.name
                self._mesh.id = self.id

    def load_volume(self, template=None, verbose=False, query_by_label=True, force_reload=False, allow_multiple=False):
        """
        Load the navis volume from each available image in the term.

        Parameters
        ----------
        template : str
            The template to load the volume for. If not provided, the first available volume will be loaded.
        verbose : bool
            Whether to print out information about the loading process.
        query_by_label : bool
            Whether to resolve the template by label.
        force_reload : bool
            Whether to force a reload of the volume.
        allow_multiple : bool
            Whether to allow multiple volumes to be loaded.
        """
        selected_template = None
        template = self.get_default_template(template=template)
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
            else:
                selected_template = template
            volume = [ci.image.get_volume() for ci in self.channel_images if ci.image.template_anatomy.short_form == selected_template] if self.channel_images else None
            if volume:
                self._volume = volume[0] if volume else None
        else:
            print("Loading volumes for ", self.name) if verbose else None
            self._volume = [ci.image.get_volume() for ci in self.channel_images] if self.channel_images else None
        if self._volume:
            if isinstance(self._volume, list):
                print("Processing volumes: ", self._volume) if verbose else None
                self._volume = [item for item in self._volume if item is not None]
                print(len(self._volume), " Volumes found: ", self._volume) if verbose else None
                for volume in self._volume:
                        volume.name = self.name
                        volume.label = self.name
                        volume.id = self.id

                if len(self._volume) > 1:
                    if not allow_multiple:
                        print("Multiple volumes found for ", self.name, ". Please run \033[35mZZZZ.load_volume(template='XXXX')\033[0m to load the aligned volume.")
                        print("Available templates: ", [ci.image.template_anatomy.name for ci in self.channel_images])
                        self._volume = None
                elif len(self._volume) == 1:
                    self._volume = self._volume[0]
            else:
                self._volume.name = self.name
                self._volume.label = self.name
                self._volume.id = self.id

    def load_skeleton_synaptic_connections(self, template=None, verbose=False):
        """
        Load the synaptic connections for the neuron's skeleton.
        """
        template = self.get_default_template(template=template)
        if not self._skeleton or self._skeleton_template != template:
            print(f"No skeleton loaded yet for {self.name} so loading...") if verbose else None
            template = self.get_default_template(template=template)
            self.load_skeleton(template=template, verbose=verbose)
        if self._skeleton:
            print(f"Loading synaptic connections for {self.name}...") if verbose else None
            xref = self.xref
            # TODO: Load synaptic connections
            # see https://github.com/navis-org/navis/blob/1eead062710af6adabc9e9c40196ad7be029cb52/navis/interfaces/neuprint.py#L491
        print("FEATURE NOT YET IMPLEMENTED")


    def get_default_template(self, template=None):
        """
        Get the default template for the term.
        """
        if template:
            return self.vfb.lookup_id(template)
        else:
            if isinstance(self, VFBTerms):
                templates = [ci.image.template_anatomy.short_form for t in self.terms for ci in t.channel_images] if any(t.channel_images for t in self.terms) else None
            else:
                templates = [ci.image.template_anatomy.short_form for ci in self.channel_images] if self.channel_images else None
            if templates:
                if 'VFB_00101567' in templates:
                    template = 'VFB_00101567' #Default to JRC2018Unisex if available
                    print("Defaulting to JRC2018Unisex template")
                if 'VFB_00200000' in templates:
                    template = 'VFB_00200000' #Default to JRC2018UnisexVNC if available
                    print("Defaulting to JRC2018UnisexVNC template")
        return template

    def plot3d(self, template=None, verbose=False, query_by_label=True, force_reload=False, include_template=False, **kwargs):
        """
        Plot the 3D representation of any neuron, expression or regions.

        This is calling the navis.plot3d method.
        for help and extra options see https://navis.readthedocs.io/en/latest/source/tutorials/plotting.html#plot-intro

        Parameters
        ----------
        template : str
            The template to plot the 3D representation for. If not provided, the first available 3D representation will be plotted.
        verbose : bool
            Whether to print out information about the plotting process.
        query_by_label : bool
            Whether to resolve the template by label.
        force_reload : bool
            Whether to force a reload of the 3D representation.
        include_template : bool
            Whether to include the template in the plot.
        kwargs : dict
            Additional keyword arguments to pass to the plot
        """
        selected_template = None
        template = self.get_default_template(template=template)
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
                query_by_label = False
            else:
                selected_template = template
        if self.has_tag('Individual'):
            if not self._skeleton or force_reload or self._skeleton_template != selected_template:
                self.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
            if self._skeleton:
                print(f"Skeleton found for {self.name}") if verbose else None
                if include_template:
                    combined = VFBTerms([selected_template if selected_template else self.channel_images[0].image.template_anatomy.short_form], query_by_label=False) + self
                    combined.plot3d(template=selected_template if selected_template else self.channel_images[0].image.template_anatomy.short_form, **kwargs)
                    return
                return self._skeleton.plot3d(**kwargs)
            else:
                print(f"No skeleton found for {self.name} check for a mesh") if verbose else None
                if not self._mesh or force_reload:
                    self.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label)
                if self._mesh:
                    print(f"Mesh found for {self.name}") if verbose else None
                    if include_template:
                        combined = VFBTerms([selected_template if selected_template else self.channel_images[0].image.template_anatomy.short_form], query_by_label=False) + self.term
                        combined.plot3d(template=selected_template if selected_template else self.channel_images[0].image.template_anatomy.short_form, **kwargs)
                        return
                    return self._mesh.plot3d(**kwargs)
                else:
                    print(f"No mesh found for {self.name} check for a volume") if verbose else None
                    if not self._volume or force_reload:
                        self.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label)
                    if self._volume:
                        print(f"Volume found for {self.name}") if verbose else None
                        if include_template:
                            combined = VFBTerms([selected_template if selected_template else self.channel_images[0].image.template_anatomy.short_form], query_by_label=False) + self.term
                            combined.plot3d(template=selected_template if selected_template else self.channel_images[0].image.template_anatomy.short_form, **kwargs)
                            return
                        return self._volume.plot3d(**kwargs)
                    else:
                        print(f"No volume found for {self.name}") if verbose else None
        else:
            print(f"{self.name} is not a instance") if verbose else None
        temp = self._return_type
        self._return_type = 'full'
        if self.instances and len(self._instances) > 0:
            print(f"Loading instances for {self.name}") if verbose else None
            if include_template:
                combined = VFBTerms([selected_template if selected_template else self.instances[0].channel_images[0].image.template_anatomy.short_form], query_by_label=False) + self.instances
                combined.plot3d(template=selected_template if selected_template else self.instances[0].channel_images[0].image.template_anatomy.short_form, **kwargs)
                self._return_type = temp
                return
            self.instances.plot3d(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload, **kwargs)
            self._return_type = temp
            return
        self._return_type = temp

    def plot2d(self, template=None, verbose=False, query_by_label=True, force_reload=False, **kwargs):
        """
        Plot the 2D representation of any neuron, expression or regions.

        This is calling the navis.plot2d method.
        for help and extra options see https://navis.readthedocs.io/en/latest/source/tutorials/plotting.html#plot-intro

        Parameters
        ----------
        template : str
            The template to plot the 2D representation for. If not provided, the first available 2D representation will be plotted.
        verbose : bool
            Whether to print out information about the plotting process.
        query_by_label : bool
            Whether to resolve the template by label.
        force_reload : bool
            Whether to force a reload of the 2D representation.
        kwargs : dict
            Additional keyword arguments to pass to the plot
        """
        selected_template = None
        template = self.get_default_template(template=template)
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
            else:
                selected_template = template
        if self.has_tag('Individual'):
            if not self._skeleton or force_reload or self._skeleton_template != selected_template:
                self.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
            if self._skeleton:
                print(f"Skeleton found for {self.name}") if verbose else None
                return self._skeleton.plot2d(**kwargs)
            else:
                print(f"No skeleton found for {self.name} check for a mesh") if verbose else None
                if not self._mesh or force_reload:
                    self.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label)
                if self._mesh:
                    print(f"Mesh found for {self.name}") if verbose else None
                    return self._mesh.plot2d(**kwargs)
                else:
                    print(f"No mesh found for {self.name} check for a volume") if verbose else None
                    if not self._volume or force_reload:
                        self.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label)
                    if self._volume:
                        print(f"Volume found for {self.name}") if verbose else None
                        return self._volume.plot2d(**kwargs)
                    else:
                        print(f"No volume found for {self.name}") if verbose else None
        else:
            print(f"{self.name} is not a instance") if verbose else None
        temp=self._return_type
        self._return_type = 'full'
        if self.instances and len(self._instances) > 0:
            print(f"Loading instances for {self.name}") if verbose else None
            self.instances.plot2d(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload, **kwargs)
            self._return_type = temp
            return
        self._return_type = temp
        print(f"No images found for {self.name}") if verbose else None

    def show(self, template=None, transparent=False, verbose=False):
        """
        Display the image of the term or its instances.

        :param template: Template short form to match for image display.
        :param transparent: Display the image with transparency if True.
        :param verbose: Print additional information if True.
        """
        template = self.get_default_template(template=template)
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
        temp = self._return_type
        self._return_type = 'full'
        if self.instances and len(self.instances) > 0:
            for instance in self.instances:
                if instance.channel_images and len(instance.channel_images) > 0:
                    print("Calling instance thumbnail for", instance.name) if verbose else None
                    instance.show(template=template, transparent=transparent, verbose=verbose)
                    self._return_type = temp
                    return  # Successfully displayed, so exit the method
        print(f"No images found to display for {self.name}") if verbose else None

    def open(self, verbose=False):
        """
        Open the term's URL in the default web browser.

        :param verbose: Print additional information if True.
        """
        print("Opening ", self.url) if verbose else None
        webbrowser.open(self.url)

    def plot_partners(self, partners: List[Partner], min_weight=False, include_self=True, template=None, include_template=False, verbose=False, **kwargs):
        """Plot a network of neuron partners.

        :param partners: List of Partner objects to plot, usually the output from the downstream_partners or upstream_partners methods.
        :param include_self: Include the neuron itself in the plot if True.
        :param template: Template short form to match for image display.
        :param verbose: Print additional information if True.
        """
        template = self.get_default_template(template=template)
        if min_weight:
            print(f"Filtering partners with weight greater than {min_weight}") if verbose else None
            partners = [partner for partner in partners if partner.weight > min_weight]
        if partners and len(partners) > 0:
            neurons = [self] if include_self else []
            neurons = neurons + [partner.partner for partner in partners]
            print(f"Plotting {len(neurons)} neurons") if verbose else None
            weights = [np.float32(partner.weight) for partner in partners]
            max_weight = max(weights)
            min_weight = min(weights)
            normalized_weights = [(weight - min_weight) / (max_weight - min_weight) for weight in weights]
            colours = self.vfb.generate_lab_colors(len(neurons)-1)
            colours = [(0,0,0)] + colours  # Reverse the colours to match the order of the neurons
            alphas = []
            max_alpha = int(255)
            for i, neuron in enumerate(neurons):
                if i == 0:
                    alpha = max_alpha
                    colours[i]= colours[i] + (max_alpha,)
                else:
                    alpha = int(max_alpha*normalized_weights[i-1])
                    colours[i]= colours[i] + (alpha,)
                alphas.append(alpha)
            print("Colours: ", colours) if verbose else None
            VFBTerms(neurons).plot3d(verbose=verbose, template=template, include_template=include_template, colors=colours, **kwargs)

        else:
            print(f"No partners found for {self.name}") if verbose else None

    def plot_similar(self, similar: List[Score], min_weight=False, template=None, include_template=False, verbose=False, **kwargs):
        """Plot a network of similar neurons or potential drivers.

        :param similar: List of Score objects to plot, usually the output from the similar_neurons_nblast or potential_drivers methods.
        :param template: Template short form to match for image display.
        :param verbose: Print additional information if True.
        """
        if min_weight:
            print(f"Filtering similar neurons with score greater than {min_weight}") if verbose else None
            similar = [score for score in similar if score.score > min_weight]
        if similar and len(similar) > 0:
            neurons = [self] + [score.term for score in similar]
            print(f"Plotting {len(neurons)} neurons") if verbose else None
            weights = [np.float32(score.score) for score in similar]
            max_weight = max(weights)
            min_weight = min(weights)
            normalized_weights = [(weight - min_weight) / (max_weight - min_weight) for weight in weights]
            colours = self.vfb.generate_lab_colors(len(neurons)-1)
            colours = [(0,0,0)] + colours
            alphas = []
            max_alpha = int(255)
            for i, neuron in enumerate(neurons):
                if i == 0:
                    alpha = max_alpha
                    colours[i]= colours[i] + (max_alpha,)
                else:
                    alpha = int(max_alpha*normalized_weights[i-1])
                    colours[i]= colours[i] + (alpha,)
                alphas.append(alpha)
            print("Colours: ", colours) if verbose else None
            VFBTerms(neurons).plot3d(verbose=verbose, template=template, include_template=include_template, colors=colours, **kwargs)

        else:
            print(f"No similar neurons found for {self.name}") if verbose else None


class VFBTerms:
    """
    A class to represent a list of VFBTerm objects.

    Parameters
    ----------
    terms : list of VFBTerm or list of str or pandas DataFrame
        A list of VFBTerm objects, a list of term IDs, or a DataFrame of term IDs.
    verbose : bool
        Whether to print out information about the loading process.
    """
    def __init__(self, terms: Union[List[VFBTerm], List[str], pandas.core.frame.DataFrame, List[dict]], verbose=False, query_by_label=True):
        from vfb_connect import vfb
        self.vfb = vfb
        self._summary = None

        if isinstance(terms, VFBTerm):
            self.terms = [terms]
            return

        if isinstance(terms, str):
            self.terms = [VFBTerm(id=terms, verbose=verbose)]
            return
        
        # Check if terms is a list of VFBTerm objects
        if isinstance(terms, list) and all(isinstance(term, VFBTerm) for term in terms):
            self.terms = terms
            return

        # Check if terms is a list of strings (IDs)
        if isinstance(terms, list) and all(isinstance(term, str) for term in terms):
            self.terms = []
            print(f"Changing {len(terms)} term names to ids") if verbose else None
            terms = [self.vfb.lookup_id(term) for term in terms if term]
            if self.vfb._load_limit and len(terms) > self.vfb._load_limit:
                print(f"More than the load limit of {self.vfb._load_limit} requested. Loading first {self.vfb._load_limit} terms out of {len(terms)}")
                terms = terms[:self.vfb._load_limit]
            print(f"Pulling {len(terms)} terms from VFB...")
            json_list = self.vfb.get_TermInfo(terms, summary=False, verbose=verbose, query_by_label=query_by_label)
            if len(json_list) < len(terms):
                print("Some terms not found in cache. Falling back to slower Neo4j queries.")
                loaded_ids = [j['term']['core']['short_form'] for j in json_list]
                missing_ids = [term for term in terms if term not in loaded_ids]
                missing_json = self.vfb.get_TermInfo(missing_ids, summary=False, cache=False, verbose=verbose, query_by_label=query_by_label)
                json_list = json_list + missing_json
                if len(json_list) < len(terms):
                    loaded_ids = [j['term']['core']['short_form'] for j in json_list]
                    missing_ids = [term for term in terms if term not in loaded_ids]
                    print(f"Failed to load {len(missing_ids)} terms: {missing_ids}")
            self.terms = create_vfbterm_list_from_json(json_list, verbose=verbose)
            return

        if isinstance(terms, list) and all(isinstance(term, type(None)) for term in terms):
            self.terms = []
            return

        # Check if terms is a DataFrame
        if isinstance(terms, pandas.core.frame.DataFrame):
            term_list = terms[:self.vfb._load_limit] if self.vfb._load_limit else terms
            self.terms = [VFBTerm(id=id, verbose=verbose) for id in self.tqdm_with_threshold(term_list['id'].values, threshold=10, desc="Loading terms")] if 'id' in terms.columns else []
            return

        # Check if terms is a numpy array
        if isinstance(terms, np.ndarray):
            term_list = terms[:self.vfb._load_limit] if self.vfb._load_limit else terms
            self.terms = [VFBTerm(id=id, verbose=verbose) for id in self.tqdm_with_threshold(term_list, threshold=10, desc="Loading terms")] if len(terms) > 0 and isinstance(terms[0], str) else []
            return

        # Check if terms is a list of dictionaries
        if isinstance(terms, list) and all(isinstance(term, dict) for term in terms):
            term_list = terms[:self.vfb._load_limit] if self.vfb._load_limit else terms
            self.terms = [VFBTerm(id=term['id'], verbose=verbose) for term in self.tqdm_with_threshold(term_list, threshold=10, desc="Loading terms")]
            return

        if isinstance(terms, VFBTerms):
            self.terms = terms.terms
            return

        raise ValueError(f"Invalid input type for terms. Expected a list of VFBTerm, a list of str, or a DataFrame. Got {type(terms)} : {terms}")

    @property
    def summary(self):
        """
        Get the summary of the term.
        """
        if self._summary is None:
            self._summary = self.get_summaries()
        return self._summary

    def __repr__(self):
        return f"VFBTerms(terms={self.terms})"

    def __getitem__(self, index):
        if isinstance(index, slice):
            # If the index is a slice, return a new VFBTerms object with the sliced terms
            return VFBTerms(self.terms[index])
        elif isinstance(index, str):
            # If the index is a string, return the term with the matching ID
            for term in self.terms:
                if term.id == index:
                    return term
            raise KeyError(f"Term with ID {index} not found.")
        else:
            # Otherwise, return the specific item from the list
            return self.terms[index]

    def get(self, key, default=None):
        """
        Mimics dictionary-like .get() method.
        """
        return getattr(self, key, default)

    def append(self, vfb_term, verbose=False):
        """
        Append a VFBTerm or VFBTerms object to the current VFBTerms.

        :param vfb_term: A VFBTerm or VFBTerms object to append.
        :param verbose: Print additional information if True.
        """
        if isinstance(vfb_term, VFBTerm):
            if vfb_term.id not in self.get_ids():
                self.terms.append(vfb_term)
                print("Appended ", vfb_term.name) if verbose else None
            else:
                print(f"Term with ID {vfb_term.id} already exists in the list. Not appending.") if verbose else None
            return
        if isinstance(vfb_term, VFBTerms):
            self.terms = self.terms + vfb_term.terms
            print("Appended ", len(vfb_term), " terms") if verbose else None
            return
        if isinstance(vfb_term, list) and all(isinstance(term, VFBTerm) for term in vfb_term):
            self.terms = self.terms + vfb_term
            print("Appended ", len(vfb_term), " terms from passed list") if verbose else None
            return
        if isinstance(vfb_term, list) and len(vfb_term) == 0:
            print("Empty list provided. No terms appended.") if verbose else None
            return
        else:
            raise TypeError("Only VFBTerm objects can be appended to VFBTerms.")

    def __len__(self):
        return len(self.terms)

    def __eq__(self, other):
        """
        Compare two VFBTerms objects for equality.
        Two VFBTerms objects are considered equal if they contain the same set of term IDs.

        :param other: The other VFBTerms object to compare.
        :return: True if the two VFBTerms objects are equal, False otherwise.
        """
        if not isinstance(other, VFBTerms):
            if isinstance(other, list) and all(isinstance(term, VFBTerm) for term in other):
                return set(self.get_ids()) == set([term.id for term in other])
            if isinstance(other, list) and all(isinstance(term, str) for term in other):
                if set(self.get_ids()) == set(other):
                    return True
                if set(self.get_names()) == set(other):
                    return True
            return False

        # Compare the sets of IDs for equality
        return set(self.get_ids()) == set(other.get_ids())

    def __contains__(self, item):
        """
        Check if a term is in the VFBTerms object.
        """
        if isinstance(item, VFBTerm):
            return item.id in self.get_ids()
        if isinstance(item, str):
            if item in self.get_ids():
                return True
            if item in self.get_names():
                return True
        return False

    def __hash__(self):
        """
        Return a hash value based on the set of term IDs.
        This makes the VFBTerms object hashable and suitable for use in sets and as dictionary keys.

        :return: Hash value.
        """
        # Use a frozenset of IDs for hashing since frozenset is hashable and immutable
        return hash(frozenset(self.get_ids()))

    def __str__(self) -> str:
        """
        Return a string representation of the VFBTerms object.
        """
        return f"VFBTerms({self.get_names()})"
    
    def __ne__(self, value: object) -> bool:
        """
        Compare two VFBTerms objects for inequality.
        """
        return not self.__eq__(value)

    def __add__(self, other):
        """
        Add two VFBTerms objects or a VFBTerm object and a VFBTerms object.

        :param other: The other VFBTerms or VFBTerm object to add.
        :return: A new VFBTerms object containing the combined terms.
        """
        if isinstance(other, VFBTerms):
            if isinstance(self.terms, VFBTerms):
                combined_terms = self.terms + other.terms
            else:
                combined_terms = VFBTerms(self.terms) + other.terms
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        if isinstance(other, VFBTerm):
            combined_terms = self.terms + VFBTerms(other)
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        if isinstance(other, list) and all(isinstance(term, VFBTerm) for term in other):
            combined_terms = self.terms + other
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        if isinstance(other, list) and all(isinstance(term, str) for term in other):
            combined_terms = self.terms + [VFBTerm(id=term) for term in other]
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        if isinstance(other, list) and all(isinstance(term, dict) for term in other):
            combined_terms = self.terms + [VFBTerm(id=term['id']) for term in other]
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        if isinstance(other, pandas.core.frame.DataFrame):
            combined_terms = self.terms + [VFBTerm(id=term) for term in other['id'].values]
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        if isinstance(other, list) and len(other) == 0:
            return self
        raise TypeError("Unsupported operand type(s) for +: 'VFBTerms' and '{}'".format(type(other).__name__))

    def __sub__(self, other, verbose=False):
        """
        Subtract a VFBTerms or VFBTerm object from the current VFBTerms.

        :param other: The VFBTerms or VFBTerm object to subtract.
        :param verbose: Print additional information if True.
        :return: A new VFBTerms object containing the remaining terms.
        """
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("Removing ", other_ids) if verbose else None
            remaining_terms = VFBTerms([term for term in self.terms if term.id not in other_ids], query_by_label=False)
            print ("Remaining ", remaining_terms.get_ids()) if verbose else None
            return remaining_terms
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("Removing ", other.id) if verbose else None
            remaining_terms = VFBTerms([term for term in self.terms if term.id != other.id], query_by_label=False)
            return remaining_terms
        raise TypeError("Unsupported operand type(s) for -: 'VFBTerms' and '{}'".format(type(other).__name__))

    def __dir__(self):
        """
        List available attributes and methods, excluding private and certain prefixed attributes.

        :return: List of attribute and method names.
        """
        return [attr for attr in list(self.__dict__.keys()) if not attr.startswith('_')] + [attr for attr in dir(self.__class__) if not attr.startswith('_') and not attr.startswith('add_')]

    def __eq__(self, other):
        """
        Compare two VFBTerms objects for equality.
        Two VFBTerms objects are considered equal if they contain the same set of term IDs.

        :param other: The other VFBTerms object to compare.
        :return: True if the two VFBTerms objects are equal, False otherwise.
        """
        if not isinstance(other, VFBTerms):
            return False

        # Compare the sets of IDs for equality
        return set(self.get_ids()) == set(other.get_ids())
    
    def __lt__(self, other):
        """
        Compare two VFBTerms objects based on their term IDs.

        :param other: The other VFBTerms object to compare.
        :return: True if the current VFBTerms object is less than the other, False otherwise.
        """
        if not isinstance(other, VFBTerms):
            if isinstance(other, list) and all(isinstance(term, VFBTerm) for term in other):
                return sorted(self.get_ids()) < sorted([term.id for term in other])
            if isinstance(other, list) and all(isinstance(term, str) for term in other):
                return sorted(self.get_ids()) < sorted(other)
            return NotImplemented
        # Compare based on sorted IDs
        return sorted(self.get_ids()) < sorted(other.get_ids())

    def __le__(self, other):
        """
        Compare two VFBTerms objects based on their term IDs.

        :param other: The other VFBTerms object to compare.
        :return: True if the current VFBTerms object is less than or equal to the other, False otherwise.
        """
        if not isinstance(other, VFBTerms):
            if isinstance(other, list) and all(isinstance(term, VFBTerm) for term in other):
                return sorted(self.get_ids()) <= sorted([term.id for term in other])
            if isinstance(other, list) and all(isinstance(term, str) for term in other):
                return sorted(self.get_ids()) <= sorted(other)
            return NotImplemented
        # Compare based on sorted IDs
        return sorted(self.get_ids()) <= sorted(other.get_ids())
    
    def __gt__(self, other):
        """
        Compare two VFBTerms objects based on their term IDs.

        :param other: The other VFBTerms object to compare.
        :return: True if the current VFBTerms object is greater than the other, False otherwise.
        """
        if not isinstance(other, VFBTerms):
            if isinstance(other, list) and all(isinstance(term, VFBTerm) for term in other):
                return sorted(self.get_ids()) > sorted([term.id for term in other])
            if isinstance(other, list) and all(isinstance(term, str) for term in other):
                return sorted(self.get_ids()) > sorted(other)
            return NotImplemented
        # Compare based on sorted IDs
        return sorted(self.get_ids()) > sorted(other.get_ids())
    
    def __ge__(self, other):
        """
        Compare two VFBTerms objects based on their term IDs.

        :param other: The other VFBTerms object to compare.
        :return: True if the current VFBTerms object is greater than or equal to the other, False otherwise.
        """
        if not isinstance(other, VFBTerms):
            if isinstance(other, list) and all(isinstance(term, VFBTerm) for term in other):
                return sorted(self.get_ids()) >= sorted([term.id for term in other])
            if isinstance(other, list) and all(isinstance(term, str) for term in other):
                return sorted(self.get_ids()) >= sorted(other)
            return NotImplemented
        # Compare based on sorted IDs
        return sorted(self.get_ids()) >= sorted(other.get_ids())
    
    def __iter__(self):
        """
        Make VFBTerms iterable by returning an iterator over the 'terms' list.

        :return: Iterator over the list of terms.
        """
        return iter(self.terms)

    def get_all(self, property_name='name', verbose=False, return_dict=False):
        """
        Get all values for a given property name.

        :param property_name: The property name to get values for.
        :param verbose: If set to True, print debug information.
        :param return_dict: If set to True, return a dictionary with values as keys and term IDs as lists.
        :return: A unique sorted list of values for the property or a dictionary.
        """
        result = set()  # Use a set to ensure uniqueness of values
        result_dict = {}  # Dictionary to map values to term IDs

        for term in self.terms:
            if hasattr(term, property_name):
                value = getattr(term, property_name)
                term_id = getattr(term, 'id', None)  # Assuming 'id' is the attribute holding the term ID
                if verbose:
                    print(f"Found property '{property_name}' in {term}: {value}")

                if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                    if verbose:
                        print(f"Property '{property_name}' is iterable. Adding items to result set: {value}")
                    result.update(value)
                    for item in value:
                        if item not in result_dict:
                            result_dict[item] = []
                        result_dict[item].append(term_id)
                else:
                    if verbose:
                        print(f"Property '{property_name}' is not iterable. Adding item to result set: {value}")
                    result.add(value)
                    if value not in result_dict:
                        result_dict[value] = []
                    result_dict[value].append(term_id)
            elif verbose:
                print(f"Property '{property_name}' not found in {term}. Skipping.")

        if return_dict:
            if verbose:
                print(f"Returning result as a dictionary: {result_dict}")
            return result_dict
        else:
            try:
                sorted_result = sorted(result)
            except TypeError:
                print("INFO: Result type can't be sorted")
                sorted_result = result
            if verbose:
                print(f"Final sorted result: {sorted_result}")
            return sorted_result

    def get_colours_for(self, property_name='name', verbose=False, take_first=False):
        """
        Get a list of colours for a given property name.

        :param property_name: The property name to get colours for.
        :param verbose: If set to True, print debug information.
        :param take_first: If set to True, take the first value from an iterable property.
        :return: A list of colours for each term, corresponding to their associated labels.
        """
        from collections.abc import Iterable

        result = set()  # To store unique property values
        term_colors_mapped = []  # List to store the color for each term

        # First pass: Collect unique property values and associate terms with these values
        for term in self.terms:
            if hasattr(term, property_name):
                value = getattr(term, property_name)

                if verbose:
                    print(f"Found property '{property_name}' in {term}: {value}")

                # If the property value is iterable, handle based on take_first flag
                if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                    print(f"Property '{property_name}' is iterable. Processing items: {value}") if verbose else None
                    if take_first:
                        value = next(iter(value), None)  # Take the first value
                        if verbose and value is not None:
                            print(f"Using first value: {value}")
                    else:
                        if isinstance(value, list) and all(isinstance(item, str) for item in value):
                            value = ' and '.join(value)  # Combine all values
                        elif isinstance(value, VFBTerms):
                            value = ' and '.join(value.get_names())
                        else:
                            value = ' and '.join([str(item) for item in value])

                # Add the value to the result set for unique values
                if value is not None:
                    result.add(value)

                # Append the value to term_colors_mapped for color mapping
                term_colors_mapped.append(value)
            else:
                if verbose:
                    print(f"Property '{property_name}' not found in {term}. Skipping.")
                term_colors_mapped.append(None)  # Append None for terms without the property

        # Generate colors for unique property values
        sorted_result = sorted(result)
        color_list = self.vfb.generate_lab_colors(len(sorted_result))
        value_to_color = dict(zip(sorted_result, color_list))

        # Map each term's property value to its corresponding color
        term_colors_mapped = [
            value_to_color.get(val, (0, 0, 0))  # Use the default color (black) if the value is None
            for val in term_colors_mapped
        ]

        # Print each label and its associated color
        print('Colour mapping:')
        for value, color in value_to_color.items():
            r, g, b = color

            # Calculate perceived luminance
            luminance = 0.299 * r + 0.587 * g + 0.114 * b

            # Choose text color based on luminance
            if luminance > 186:  # Threshold can be adjusted based on preference
                text_color = "0;0;0"  # Black text for light backgrounds
            else:
                text_color = "255;255;255"  # White text for dark backgrounds

            print(f"\033[48;2;{r};{g};{b}m\033[38;2;{text_color}m  {value}  \033[0m")
        if (0, 0, 0) in term_colors_mapped:
            print(f"\033[48;2;{0};{0};{0}m\033[38;2;255;255;255m  None  \033[0m")

        return term_colors_mapped  # Return the list of colors corresponding to each term


    def AND(self, other, verbose=False):
        """
        Perform a logical AND operation on two VFBTerms objects or a VFBTerm object and a VFBTerms object.

        :param other: The other VFBTerms or VFBTerm object to AND.
        :param verbose: Print additional information if True.
        :return: A new VFBTerms object containing the terms that are common to both.
        """
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("ANDing with ", other_ids) if verbose else None
            remaining_terms = VFBTerms([term for term in self.terms if term.id in other_ids], query_by_label=False)
            print ("Remaining ", remaining_terms.get_ids()) if verbose else None
            return remaining_terms
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("ANDing with ", other.id) if verbose else None
            remaining_terms = VFBTerms([term for term in self.terms if term.id == other.id], query_by_label=False)
            return remaining_terms
        raise TypeError("Unsupported operand type(s) for AND: 'VFBTerms' and '{}'".format(type(other).__name__))

    def OR(self, other, verbose=False):
        """
        Perform a logical OR operation on two VFBTerms objects or a VFBTerm object and a VFBTerms object.

        :param other: The other VFBTerms or VFBTerm object to OR.
        :param verbose: Print additional information if True.
        :return: A new VFBTerms object containing the combined terms.
        """
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("ORing with ", other_ids) if verbose else None
            combined_terms = self.terms + other.terms
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        if isinstance(other, VFBTerm):
            combined_terms = self.terms + [other]
            unique_terms = {term.id: term for term in combined_terms}.values()
            return VFBTerms(list(unique_terms))
        raise TypeError("Unsupported operand type(s) for OR: 'VFBTerms' and '{}'".format(type(other).__name__))
    
    def XOR(self, other, verbose=False):
        """
        Perform a logical XOR operation on two VFBTerms objects or a VFBTerm object and a VFBTerms object.

        :param other: The other VFBTerms or VFBTerm object to XOR.
        :param verbose: Print additional information if True.
        :return: A new VFBTerms object containing the terms that are unique to each.
        """
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("XORing with ", other_ids) if verbose else None
            combined_terms = self.terms + other.terms
            unique_terms = [term for term in combined_terms if term.id not in self.get_ids() or term.id not in other_ids]
            return VFBTerms(list(unique_terms))
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("XORing with ", other.id) if verbose else None
            unique_terms = [term for term in self.terms if term.id != other.id]
            return VFBTerms(list(unique_terms))
        raise TypeError("Unsupported operand type(s) for XOR: 'VFBTerms' and '{}'".format(type(other).__name__))

    def NAND(self, other, verbose=False):
        """
        Perform a logical NAND operation on two VFBTerms objects or a VFBTerm object and a VFBTerms object.

        :param other: The other VFBTerms or VFBTerm object to NAND.
        :param verbose: Print additional information if True.
        :return: A new VFBTerms object containing the terms that are unique to each.
        """
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("NANDing with ", other_ids) if verbose else None
            combined_terms = self.terms + other.terms
            unique_terms = [term for term in combined_terms if term.id not in self.get_ids() or term.id not in other_ids]
            return VFBTerms(list(unique_terms))
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("NANDing with ", other.id) if verbose else None
            unique_terms = [term for term in self.terms if term.id != other.id]
            return VFBTerms(list(unique_terms))
        raise TypeError("Unsupported operand type(s) for NAND: 'VFBTerms' and '{}'".format(type(other).__name__))

    def NOR(self, other, verbose=False):
        """
        Perform a logical NOR operation on two VFBTerms objects or a VFBTerm object and a VFBTerms object.

        :param other: The other VFBTerms or VFBTerm object to NOR.
        :param verbose: Print additional information if True.
        :return: A new VFBTerms object containing the terms that are unique to each.
        """
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("NORing with ", other_ids) if verbose else None
            combined_terms = self.terms + other.terms
            unique_terms = [term for term in combined_terms if term.id not in self.get_ids() or term.id not in other_ids]
            return VFBTerms(list(unique_terms))
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("NORing with ", other.id) if verbose else None
            unique_terms = [term for term in self.terms if term.id != other.id]
            return VFBTerms(list(unique_terms))
        raise TypeError("Unsupported operand type(s) for NOR: 'VFBTerms' and '{}'".format(type(other).__name__))

    def XNOR(self, other, verbose=False):
        """
        Perform a logical XNOR operation on two VFBTerms objects or a VFBTerm object and a VFBTerms object.

        :param other: The other VFBTerms or VFBTerm object to XNOR.
        :param verbose: Print additional information if True.
        :return: A new VFBTerms object containing the terms that are unique to each.
        """
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("XNORing with ", other_ids) if verbose else None
            combined_terms = self.terms + other.terms
            unique_terms = [term for term in combined_terms if term.id not in self.get_ids() or term.id not in other_ids]
            return VFBTerms(list(unique_terms))
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("XNORing with ", other.id) if verbose else None
            unique_terms = [term for term in self.terms if term.id != other.id]
            return VFBTerms(list(unique_terms))
        raise TypeError("Unsupported operand type(s) for XNOR: 'VFBTerms' and '{}'".format(type(other).__name__))

    def NOT(self, other, verbose=False):
        """
        Perform a logical NOT operation on the current VFBTerms object.

        :param other: The other VFBTerms or VFBTerm to remove from this VFBTerms.
        :param verbose: Print additional information if True.
        :return: A new VFBTerms object containing the terms that are not in the other object.
        """
        print("Starting with ", self.get_ids()) if verbose else None
        if isinstance(other, VFBTerms):
            other_ids = other.get_ids()
            print("NOTing with ", other_ids) if verbose else None
            remaining_terms = VFBTerms([term for term in self.terms if term.id not in other_ids], query_by_label=False)
            print ("Remaining ", remaining_terms.get_ids()) if verbose else None
            return remaining_terms
        if isinstance(other, VFBTerm):
            other_ids = [other.id]
            print("NOTing with ", other.id) if verbose else None
            remaining_terms = VFBTerms([term for term in self.terms if term.id != other.id], query_by_label=False)
            return remaining_terms
        raise TypeError("Unsupported operand type(s) for NOT: 'VFBTerms' and '{}'".format(type(other).__name__))

    def load_skeletons(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load the navis skeleton from each available image in the term.

        :param template: The short form of the template to load skeletons for.
        :param verbose: Print additional information if True.
        :param query_by_label: Query by label if True.
        :param force_reload: Force reload of skeletons if True.
        """
        for term in self.terms:
            term.load_skeleton(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)

    def load_meshes(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load the navis mesh from each available image in the term.

        :param template: The short form of the template to load meshes for.
        :param verbose: Print additional information if True.
        :param query_by_label: Query by label if True.
        :param force_reload: Force reload of meshes if True.
        """
        for term in self.terms:
            term.load_mesh(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)

    def load_volumes(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load the navis volume from each available image in the term.

        :param template: The short form of the template to load volumes for.
        :param verbose: Print additional information if True.
        :param query_by_label: Query by label if True.
        :param force_reload: Force reload of volumes if True.
        """
        for term in self.terms:
            term.load_volume(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)

    def plot3d(self, template=None, verbose=False, query_by_label=True, force_reload=False, include_template=False, limit=False, **kwargs):
        """
        Plot the 3D representation of any neuron or expression.

        This is calling the navis.plot3d method.
        for help and extra options see https://navis.readthedocs.io/en/latest/source/tutorials/plotting.html#plot-intro

        :param template: The short form of the template to plot 3D representations in.
        :param verbose: Print additional information if True.
        :param query_by_label: Query by label if True.
        :param force_reload: Force reload of 3D representations if True.
        :param kwargs: Additional arguments for plotting.
        """
        skeletons, selected_template = self._get_plot_images(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)

        if skeletons:
            if limit and len(skeletons) > limit:
                print(f"\033[32mINFO:\033[0m Limiting to {limit} items out of {len(skeletons)}")
                skeletons = skeletons[:limit]

            print(f"Plotting 3D representation of {len(skeletons)} items")
            if include_template:
                print(f"Adding template {selected_template} to the plot")
                temp = VFBTerm(selected_template)
                temp.load_mesh()
                if hasattr(temp, 'mesh') and temp.mesh:
                    skeletons.append(temp.mesh)
            return navis.plot3d(skeletons, **kwargs)
        else:
            print("Nothing found to plot")

    def plot2d(self, template=None, verbose=False, query_by_label=True, force_reload=False, include_template=False, limit=False, **kwargs):
        """
        Plot the 2D representation of any neuron or expression.

        This is calling the navis.plot3d method.
        for help and extra options see https://navis.readthedocs.io/en/latest/source/tutorials/plotting.html#plot-intro

        :param template: The short form of the template to plot 2D representations in.
        :param verbose: Print additional information if True.
        :param query_by_label: Query by label if True.
        :param force_reload: Force reload of 2D representations if True.
        :param include_template: Include the template in the plot if True.
        :param kwargs: Additional arguments for plotting.
        """
        skeletons, selected_template = self._get_plot_images(template=template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)

        if skeletons:
            if limit and len(skeletons) > limit:
                print(f"\033[32mINFO:\033[0m Limiting to {limit} items out of {len(skeletons)}")
                skeletons = skeletons[:limit]

            print(f"Plotting 2D representation of {len(skeletons)} items")
            if include_template:
                print(f"Adding template {selected_template} to the plot")
                temp = VFBTerm(selected_template)
                temp.load_mesh()
                if hasattr(temp, 'mesh') and temp.mesh:
                    skeletons.append(temp.mesh)
            return navis.plot2d(skeletons, **kwargs)

    def _get_plot_images(self, template=None, verbose=False, query_by_label=True, force_reload=False):
        """
        Load and return images for navis plot

        :param template: The short form of the template to load images for.
        :param verbose: Print additional information if True.
        :param query_by_label: Query by label if True.
        :param force_reload: Force reload of images if True.
        :return: A list of skeletons and the selected template.
        """
        selected_template = None
        template = VFBTerm.get_default_template(self, template)
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
                query_by_label = False
            else:
                selected_template = template
        skeletons=[]
        for term in VFBTerms.tqdm_with_threshold(self, self.terms, threshold=10, desc="Loading Images"):
            if term.has_tag('Individual'):
                print(f"{term.name} is an instance") if verbose else None
            else:
                print(f"{term.name} is not an instance soo won't have a skeleton, mesh or volume") if verbose else None
                continue
            if not term._skeleton or force_reload:
                term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload, allow_multiple=True)
            if term._skeleton:
                print(f"Skeleton found for {term.name}") if verbose else None
                if not selected_template:
                    if isinstance(term._skeleton, list):
                        print("Multiple skeletons found for ", term.name, ". Arbitarily taking the first template as the space to plot in. Specify a template to avoid this.")
                        selected_template = term.channel_images[0].image.template_anatomy.short_form
                        print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name}")
                        term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=True)
                    else:
                        selected_template = term.channel_images[0].image.template_anatomy.short_form
                        print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name} from the first skeleton found. Specify a template to avoid this.")
                skeletons.append(term._skeleton)
            else:
                print(f"No skeleton found for {term.name} check for a mesh") if verbose else None
                if not term._mesh or force_reload:
                    term.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload, allow_multiple=True)
                if term._mesh:
                    print(f"Mesh found for {term.name}") if verbose else None
                    if not selected_template:
                        if isinstance(term._mesh, list):
                            print("Multiple meshes found for ", term.name, ". Arbitarily taking the first template as the space to plot in. Specify a template to avoid this.")
                            selected_template = term.channel_images[0].image.template_anatomy.short_form
                            print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name}")
                            term.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=True)
                        else:
                            selected_template = term.channel_images[0].image.template_anatomy.short_form
                            print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name} from the first mesh found. Specify a template to avoid this.")
                    skeletons.append(term._mesh)
                else:
                    print(f"No mesh found for {term.name} check for a volume") if verbose else None
                    if not term._volume or force_reload:
                        term.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload, allow_multiple=True)
                    if term._volume:
                        if not selected_template:
                            if isinstance(term._volume, list):
                                print("Multiple volumes found for ", term.name, ". Arbitarily taking the first template as the space to plot in. Specify a template to avoid this.")
                                selected_template = term.channel_images[0].image.template_anatomy.short_form
                                print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name}")
                                term.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=True)
                            elif isinstance(term._volume, navis.core.volumes.Volume):
                                selected_template = term.channel_images[0].image.template_anatomy.short_form
                                print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name} from the first volume found. Specify a template to avoid this.")
                        skeletons.append(term._volume)
                    else:
                        print(f"No volume found for {term.name}") if verbose else None
        return (skeletons, selected_template)

    def plot3d_by_type(self, template=None, verbose=False, query_by_label=True, force_reload=False, **kwargs):
        """
        Plot the 3D representation of any neuron or expression coloured by it's parent type.

        :param template: The short form of the template to plot 3D representations in.
        :param verbose: Print additional information if True.
        :param query_by_label: Query by label if True.
        :param force_reload: Force reload of 3D representations if True.
        :param kwargs: Additional arguments for plotting.
        """
        selected_template = None
        template = VFBTerm.get_default_template(self, template)
        if template:
            if query_by_label:
                selected_template = self.vfb.lookup_id(template)
                print("Template (", template, ") resolved to id ", selected_template) if verbose else None
                query_by_label = False
            else:
                selected_template = template
        skeletons=[]
        types = []
        for term in VFBTerms.tqdm_with_threshold(self, self.terms, threshold=10, desc="Loading Images"):
            if term.has_tag('Individual'):
                print(f"{term.name} is an instance") if verbose else None
            else:
                print(f"{term.name} is not an instance soo won't have a skeleton, mesh or volume") if verbose else None
                continue
            if not term._skeleton or force_reload:
                term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload, allow_multiple=True)
            if term._skeleton:
                print(f"Skeleton found for {term.name}") if verbose else None
                if not selected_template:
                    if isinstance(term._skeleton, list):
                        print("Multiple skeletons found for ", term.name, ". Arbitarily taking the first template as the space to plot in. Specify a template to avoid this.")
                        selected_template = term.channel_images[0].image.template_anatomy.short_form
                        print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name}")
                        term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
                    else:
                        selected_template = term.channel_images[0].image.template_anatomy.short_form
                        print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name} from the first skeleton found. Specify a template to avoid this.")
                skeletons.append(term._skeleton)
                types.append({'text': term.parents[0].name})
            else:
                print(f"No skeleton found for {term.name} check for a mesh") if verbose else None
                if not term._mesh or force_reload:
                    term.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload, allow_multiple=True)
                if term._mesh:
                    print(f"Mesh found for {term.name}") if verbose else None
                    if not selected_template:
                        if isinstance(term._mesh, list):
                            print("Multiple meshes found for ", term.name, ". Arbitarily taking the first template as the space to plot in. Specify a template to avoid this.")
                            selected_template = term.channel_images[0].image.template_anatomy.short_form
                            print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name}")
                            term.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
                        else:
                            selected_template = term.channel_images[0].image.template_anatomy.short_form
                            print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name} from the first mesh found. Specify a template to avoid this.")
                    skeletons.append(term._mesh)
                    types.append({'text': term.parents[0].name})
                else:
                    print(f"No mesh found for {term.name} check for a volume") if verbose else None
                    if not term._volume or force_reload:
                        term.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload, allow_multiple=True)
                    if term._volume:
                        if not selected_template:
                            if isinstance(term._volume, list):
                                print("Multiple volumes found for ", term.name, ". Arbitarily taking the first template as the space to plot in. Specify a template to avoid this.")
                                selected_template = term.channel_images[0].image.template_anatomy.short_form
                                print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name}")
                                term.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label, force_reload=force_reload)
                            elif isinstance(term._volume, navis.core.volumes.Volume):
                                selected_template = term.channel_images[0].image.template_anatomy.short_form
                                print(f"Enforcing the display template space as {term.channel_images[0].image.template_anatomy.name} from the first volume found. Specify a template to avoid this.")
                        skeletons.append(term._volume)
                        types.append({'text': term.parents[0].name})
                    else:
                        print(f"No volume found for {term.name}") if verbose else None
        if skeletons:
            print(f"Plotting 3D representation of {len(skeletons)} items")
            return navis.plot3d(skeletons, legend_group=types)
        else:
            print("Nothing found to plot")

    def get_ids(self):
        """
        Get the IDs of the terms.

        :return: List of term IDs.
        """
        return [term.id for term in self.terms]

    def get_names(self):
        """
        Get the names of the terms.

        :return: List of term names.
        """
        return [term.name for term in self.terms]

    def get_summaries(self, return_dataframe=True, verbose=False, limit=None):
        """
        Get the summaries of the terms.

        :param return_dataframe: Return the summaries as a DataFrame if True.
        :return: List or DataFrame of term summaries.
        """
        summaries = []
        if not self.vfb._load_limit and not limit:
            for term in VFBTerms.tqdm_with_threshold(self, self.terms, threshold=10, desc="Loading Summaries"):
                summaries.append(term.get_summary(return_dataframe=return_dataframe, verbose=verbose))
        else:
            count = 0
            for term in VFBTerms.tqdm_with_threshold(self, self.terms, threshold=10, desc="Loading Summaries"):
                summaries.append(term.get_summary(return_dataframe=return_dataframe, verbose=verbose))
                count += 1
                if (self.vfb._load_limit and count >= self.vfb._load_limit) or (limit and count >= limit):
                    break

        if return_dataframe:
            return pandas.concat(summaries, ignore_index=True)
        return summaries

    def open(self, template=None, verbose=False):
        """
        Open the VFB browser with the terms' URLs.

        :param template: Template short form to include in the URL.
        :param verbose: Print additional information if True.
        """
        url = "https://v2.virtualflybrain.org/org.geppetto.frontend/geppetto"
        space = self.vfb.lookup_id(template) + "," if template else ""
        images = "?i=" + space + ",".join(self.get_ids())
        print("Opening VFB browser with URL: ", url + images) if verbose else None

        # Open the URL in the default browser
        webbrowser.open(url + images)

    def show(self, template=None, transparent=False, verbose=False):
        """
        Show a merged thumbnail for all terms in a Jupyter notebook.

        :param template: The template short form to display thumbnails for.
        :param transparent: Use transparent thumbnails if True.
        :param verbose: Print additional information if True.
        """
        template = VFBTerm.get_default_template(self, template)
        if template:
            template = self.vfb.lookup_id(template)

        thumbnails = []
        for term in self.terms:
            for ci in term.channel_images:
                if ci.image.image_thumbnail:
                    if not template or ci.image.template_anatomy.short_form == template:
                        if verbose:
                            print(f"Adding thumbnail for {term.name}")
                        thumbnails.append(ci.image.image_thumbnail)
                        if not template:
                            template = ci.image.template_anatomy.short_form
                            if verbose:
                                print(f"Fixing template to {template}. Please specify a template to avoid this.")

        if thumbnails:
            from PIL import Image
            import requests
            from io import BytesIO

            alpha = 1.0 / len(thumbnails)

            try:
                images = []
                for thumbnail in thumbnails:
                    if verbose:
                        print("Fetching image: ", thumbnail if not transparent else thumbnail.replace('thumbnail.png', 'thumbnailT.png'))

                    # Fetch the image
                    response = requests.get(thumbnail if not transparent else thumbnail.replace('thumbnail.png', 'thumbnailT.png'))
                    if verbose:
                        print("Response: ", response)
                        print("Content: ", response.content)

                    img = Image.open(BytesIO(response.content))
                    images.append(img)

                # Initialize overlay_img with the first image
                overlay_img = images[0]

                # Blend subsequent images
                for image in images[1:]:
                    overlay_img = Image.blend(overlay_img, image, alpha)

                # Try to display the image in a notebook environment
                try:
                    from IPython.display import display
                    if verbose:
                        print("Displaying thumbnail in notebook...")
                    display(overlay_img)
                except ImportError:
                    # If not in a notebook, fall back to PIL's image viewer
                    if verbose:
                        print("IPython not available, using PIL to show the image.")
                    overlay_img.show()

            except Exception as e:
                print("\033[31mError:\033[0m displaying thumbnail: ", e)
        else:
            print("No thumbnails found to display")



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
    :param verbose: Print additional information if True.
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

    return VFBTerms([create_vfbterm_from_json(term, verbose=verbose) for term in VFBTerms.tqdm_with_threshold(VFBTerms, data, threshold=10, desc="Loading Terms")], query_by_label=False)

def create_vfbterm_from_json(json_data, verbose=False):
    """
    Create a VFBTerm object from JSON data.

    :param json_data: JSON data as a string or dictionary.
    :param verbose: Print additional information if True.
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
                object_name = relation['object']['symbol'] if relation['object']['symbol'] else relation['object']['label']
                related_terms.append(Rel(relation=rel, object=object, object_name=object_name))
            print(f"Loaded {len(related_terms)} related terms from relationships") if verbose else None

        if 'related_individuals' in data:
            related_terms = [] if not related_terms else related_terms
            bc = len(related_terms)
            for relation in data['related_individuals']:
                rel = MinimalEdgeInfo(**relation['relation'])
                object = relation['object']['short_form']
                object_name = relation['object']['symbol'] if relation['object']['symbol'] else relation['object']['label']
                related_terms.append(Rel(relation=rel, object=object, object_name=object_name))
            print(f"Loaded {len(related_terms)-bc} related terms from related_individuals") if verbose else None

        if related_terms:
            related_terms = Relations(relations=related_terms)

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
            publications = [] if not publications else publications
            for pub in data['pubs']:
                publication = Publication(**pub)
                publications.append(publication)
            print(f"Loaded {len(publications)} publications") if verbose else None

        if 'def_pubs' in data:
            publications = [] if not publications else publications
            for pub in data['def_pubs']:
                publication = Publication(**pub)
                if hasattr(publication, 'comment'):
                    publication['comment'].append('Definition reference')
                else:
                    publication['comment'] = ['Definition reference']
                publications.append(publication)
            print(f"Loaded {len(publications)} definition publications") if verbose else None

        if 'pub_syn' in data:
            publications = [] if not publications else publications
            for pub in data['pub_syn']:
                publication = Publication(**pub['pub'])
                if hasattr(publication, 'comment'):
                    publication['comment'].append('Synonym reference')
                else:
                    publication['comment'] = ['Synonym reference']
                publications.append(publication)
            print(f"Loaded {len(publications)} synonym publications") if verbose else None

        if 'pub_specific_content' in data:
            publications = [] if not publications else publications
            p_core = MinimalEntityInfo(
                iri=term.core.iri,
                short_form=term.core.short_form,
                label=term.core.label,
                unique_facets=term.core.unique_facets,
                types=term.core.types,
                symbol=term.core.symbol
            )
            pub = Publication(
                core=p_core,
                description=[data['pub_specific_content'].get('title', '')],
                FlyBase=data['pub_specific_content'].get('FlyBase', ''),
                DOI=data['pub_specific_content'].get('DOI', ''),
                PubMed=data['pub_specific_content'].get('PubMed', ''),
                )
            publications.append(pub)
            print(f"Loaded {len(publications)} publication specific data") if verbose else None

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
    :param verbose: Print additional information if True.
    :param query_by_label: Query by label if True.
    :param force_reload: Force reload of skeletons if True.
    """
    from vfb_connect import vfb
    selected_template = None
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

