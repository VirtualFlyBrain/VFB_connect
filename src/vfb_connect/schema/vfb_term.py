import json
import os
from typing import List, Optional
import navis
import requests
import tempfile

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
        return f"MinimalEdgeInfo(label={self.label}, type={self.type})"


class Term:
    def __init__(self, core: MinimalEntityInfo, description: Optional[List[str]] = None, comment: Optional[List[str]] = None, link: Optional[str] = None, icon: Optional[str] = None):
        self.core = core
        self.description = ", ".join(description) if description else ""
        self.comment = ", ".join(comment) if comment else ""
        self.link = link if link else "https://n2t.net/vfb:" + self.core.short_form
        self.icon = icon if icon else ""

    def __repr__(self):
        return f"Term({self.core})"


class Rel:
    def __init__(self, relation: MinimalEdgeInfo, object: MinimalEntityInfo):
        self.relation = relation
        self.object = object

    def __repr__(self):
        return f"Rel(relation={self.relation}, object={self.object})"


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

    def __repr__(self):
        return f"Image(image_folder={self.image_folder})"

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

class ChannelImage:
    def __init__(self, image: Image, channel: MinimalEntityInfo, imaging_technique: MinimalEntityInfo):
        self.image = image
        self.channel = channel
        self.imaging_technique = imaging_technique

    def __repr__(self):
        return f"ChannelImage(channel={self.channel}, imaging_technique={self.imaging_technique})"


class AnatomyChannelImage:
    def __init__(self, anatomy: MinimalEntityInfo, channel_image: ChannelImage):
        self.anatomy = anatomy
        self.channel_image = channel_image

    def __repr__(self):
        return f"AnatomyChannelImage(anatomy={self.anatomy})"


class VFBTerm:
    def __init__(self, id=None, term: Optional[Term] = None, related_terms: Optional[List[Rel]] = None, channel_images: Optional[List[ChannelImage]] = None, parents: Optional[List[str]] = None, verbose=False):
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
                term_object = create_vfbterm_from_json(json_data[0], verbose=verbose)
                self.__dict__.update(term_object.__dict__)  # Copy attributes from the fetched term object
        elif term is not None:
            self.term = term
            self.related_terms = related_terms
            self.channel_images = channel_images
            self.summary = self.get_summary()
            self.name = self.term.core.name
            self.id = self.term.core.short_form
            self.description = self.term.description
            self.url = self.term.link

            self._parents_ids = parents
            self._parents = None  # Initialize as None, will be loaded on first access
        
            if self.term.icon:
                self.thumbnail = self.term.icon
            elif channel_images and len(channel_images) > 0 and channel_images[0].image.image_thumbnail:
                self.thumbnail = channel_images[0].image.image_thumbnail

            # Set flags for different types of terms
            self.is_type = self.has_tag('Class')
            self.is_instance = self.has_tag('Individual')
            self.is_neuron = self.has_tag('Neuron')
            self.has_image = self.has_tag('has_image')
            self.has_scRNAseq = self.has_tag('hasScRNAseq')
            self.has_neuron_connectivity = self.has_tag('has_neuron_connectivity')
            self.has_region_connectivity = self.has_tag('has_region_connectivity')

    @property
    def parents(self):
        if self._parents is None:
            print("Loading parents for the first time...")
            self._parents = VFBTerms(self._parents_ids) if self._parents_ids else None
        return self._parents

    def __repr__(self):
        return f"VFBTerm(term={self.term})"
    
    def __getitem__(self, index):
        if index != 0:
            raise IndexError("VFBTerm only has one item")
        return self
    
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

    def get_summary(self):
        """
        Returns a summary of the term's information.
        """
        summary = {
            "ID": self.term.core.short_form,
            "Name": self.term.core.name,
            "Description": self.term.description + " " + self.term.comment if self.term.comment else self.term.description,
            "URL": self.term.link,
        }
        if self.related_terms:
            summary["Related Terms"] = [str(rel) for rel in self.related_terms]
        if self.channel_images:
            summary["Channel Images"] = [str(ci) for ci in self.channel_images]

        return summary
    
    def has_tag(self, tag):
        return tag in self.term.core.types
    
    def load_skeleton(self, template=None, verbose=False, query_by_label=True):
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

    def load_mesh(self, template=None, verbose=False, query_by_label=True):
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
                    mesh.meta=self.summary
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


    def load_volume(self, template=None, verbose=False, query_by_label=True):
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

class VFBTerms:
    def __init__(self, terms: List[VFBTerm], verbose=False):
        from vfb_connect import vfb
        self.vfb = vfb
        self.terms = terms

    def __init__(self, terms: List[str], verbose=False):
        from vfb_connect import vfb
        self.vfb = vfb
        self.terms = [VFBTerm(id=term, verbose=verbose) for term in terms]

    def __repr__(self):
        return f"VFBTerms(terms={self.terms})"

    def __getitem__(self, index):
        if isinstance(index, slice):
            # If the index is a slice, return a new VFBTerms object with the sliced terms
            return VFBTerms(self.terms[index])
        else:
            # Otherwise, return the specific item from the list
            return self.terms[index]
    
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


    def load_skeletons(self, template=None, verbose=False, query_by_label=True):
        """
        Load the navis skeleton from each available image in the term.
        """
        for term in self.terms:
            term.load_skeleton(template=template, verbose=verbose, query_by_label=query_by_label) 

    def load_meshes(self, template=None, verbose=False, query_by_label=True):
        """
        Load the navis mesh from each available image in the term.
        """
        for term in self.terms:
            term.load_mesh(template=template, verbose=verbose, query_by_label=query_by_label)

    def load_volumes(self, template=None, verbose=False, query_by_label=True):
        """
        Load the navis volume from each available image in the term.
        """
        for term in self.terms:
            term.load_volume(template=template, verbose=verbose, query_by_label=query_by_label)

    def plot3d(self, template=None, verbose=False, query_by_label=True):
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
        for term in self.terms:
            if term.has_tag('Individual'):
                print(f"{term.name} is an instance") if verbose else None
            else:
                print(f"{term.name} is not an instance soo won't have a skeleton, mesh or volume") if verbose else None
                continue
            if not hasattr(term, 'skeleton'):
                term.load_skeleton(template=selected_template, verbose=verbose, query_by_label=query_by_label)
            if hasattr(term, 'skeleton') and term.skeleton:
                print(f"Skeleton found for {term.name}") if verbose else None
                skeletons.append(term.skeleton)
            else:
                print(f"No skeleton found for {term.name} check for a mesh") if verbose else None
                if not hasattr(term, 'mesh'):
                    term.load_mesh(template=selected_template, verbose=verbose, query_by_label=query_by_label)
                if hasattr(term, 'mesh') and term.mesh:
                    skeletons.append(term.mesh)
                else:
                    print(f"No mesh found for {term.name} check for a volume") if verbose else None
                    if not hasattr(term, 'volume'):
                        term.load_volume(template=selected_template, verbose=verbose, query_by_label=query_by_label)
                    if hasattr(term, 'volume') and term.volume:
                        skeletons.append(term.volume)
                    else:
                        print(f"No volume found for {term.name}") if verbose else None

        if skeletons:
            print(f"Plotting 3D representation of {len(skeletons)} items")
            navis.plot3d(skeletons, backend='auto')
        else:
            print("Nothing found to plot")

    def get_ids(self):
        return [term.id for term in self.terms]
    
    def get_names(self):
        return [term.name for term in self.terms]
    
    def get_summaries(self):
        return [term.summary for term in self.terms]

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

        # Handle related terms (relations)
        related_terms = None
        if 'related_terms' in data:
            related_terms = [Rel(relation=MinimalEdgeInfo(**rel['relation']), object=MinimalEntityInfo(**rel['object'])) for rel in data['related_terms']]

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

        return VFBTerm(term=term, related_terms=related_terms, channel_images=channel_images, parents=parents, verbose=verbose)
    else:
        return None

def load_skeletons(vfb_term, template=None, verbose=False, query_by_label=True):
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
        vfb_term.load_skeleton(template=selected_template)
    if isinstance(vfb_term, list):
        for term in vfb_term:
            print("Loading skeletons for ", vfb_term.name) if template == None else print("Loading skeleton for ", vfb_term.name, " aligned to ", template)
            term.load_skeleton(template=selected_template)

