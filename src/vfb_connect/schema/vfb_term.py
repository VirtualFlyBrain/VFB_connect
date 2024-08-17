import json
import os
from typing import List, Optional
import navis
import requests
from vfb_connect import VfbConnect
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

    def get_skeleton(self):
        if self.image_swc:
            return navis.read_swc(self.image_swc)
        if self.image_obj and 'volume_man.obj' in self.image_swc:
            return navis.read_mesh(self.image_obj, output='neuron', errors='ignore')
            return navis.TreeNeuron.from_mesh(mesh)
        if self.image_nrrd:
            return navis.read_nrrd(self.image_nrrd, output='dotprops', errors='ignore')
        return None

    def get_mesh(self):
        if self.image_obj and 'volume_man.obj' in self.image_swc:
            return navis.read_mesh(self.image_obj, output='neuron', errors='ignore')
        if self.image_swc:
            return navis.read_swc(self.image_swc, read_meta=False)
        return None

    def get_volume(self):
        if self.image_nrrd:
            local_file = self.create_temp_file(suffix=".nrrd")
            self.download_file(self.image_nrrd, local_file.name)
            mesh = navis.read_nrrd(local_file.name, output='voxels', errors='log')
            if mesh:
                self.delete_temp_file(local_file.name)
                return mesh 
        return None

    def create_temp_file(self, suffix=".nrrd", delete=False):
        # Create a temporary file with a specific extension
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=delete)
        print(f"Temporary file created: {temp_file.name}")
        return temp_file

    def download_file(self, url, local_filename):
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return local_filename
        else:
            print(f"Failed to download file from {url}")
            return None

    def delete_temp_file(self, file_path):
        """
        Deletes the temporary file at the specified path.

        :param file_path: The path to the temporary file to be deleted.
        :return: None
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Temporary file deleted: {file_path}")
            else:
                print(f"File not found: {file_path}")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

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
    def __init__(self, term: Term, related_terms: Optional[List[Rel]] = None, channel_images: Optional[List[ChannelImage]] = None):
        self.term = term
        self.related_terms = related_terms
        self.channel_images = channel_images
        self.summary = self.get_summary()
        self.name = self.term.core.name
        self.id = self.term.core.short_form
        self.description = self.term.description
        self.url = self.term.link

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

    def __repr__(self):
        return f"VFBTerm(term={self.term})"

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
    
    def load_skeleton(self, template=None):
        """
        Load the navis skeleton from each available image in the term.
        """
        if template:
            print("Loading skeleton for ", self.name, " aligned to ", template)
            selected_template = VfbConnect.lookup_id(template)
            self.skeleton = [ci.image.get_skeleton() for ci in self.channel_images if ci.image.template_channel.short_form == selected_template][0] if self.channel_images else None
        else:
            print("Loading skeletons for ", self.name)
            print("Processinng channel images: ", self.channel_images)
            self.skeleton = [ci.image.get_skeleton() for ci in self.channel_images] if self.channel_images else None
        if self.skeleton:
            if isinstance(self.skeleton, list):
                for skeleton in self.skeleton:
                    skeleton.name = self.name
                    skeleton.label = self.name
                    skeleton.id = self.id

                if len(self.skeleton) > 1:
                    print("Multiple skeletons found for ", self.name, ". Please specify a template.")
                    print("Available templates: ", [ci.image.template_channel.name for ci in self.channel_images])
                elif len(self.skeleton) == 1:
                    print("Skeleton found for ", self.name)
                    self.skeleton = self.skeleton[0]
            else:
                print("Skeleton found for ", self.name)
                self.skeleton.name = self.name
                self.skeleton.label = self.name
                self.skeleton.id = self.id
 

    def load_mesh(self, template=None):
        """
        Load the navis mesh from each available image in the term.
        """
        if template:
            selected_template = VfbConnect.lookup_id(template)
            self.mesh = [ci.image.get_mesh() for ci in self.channel_images if ci.image.template_channel.short_form == selected_template][0] if self.channel_images else None
        else:
            self.mesh = [ci.image.get_mesh() for ci in self.channel_images] if self.channel_images else None
        if self.mesh:
            if isinstance(self.mesh, list):
                for mesh in self.mesh:
                    mesh.name = self.name
                    mesh.label = self.name
                    mesh.id = self.id
                    mesh.meta=self.summary
                if len(self.mesh) > 1:
                    print("Multiple meshes found for ", self.name, ". Please specify a template.")
                    print("Available templates: ", [ci.image.template_channel.name for ci in self.channel_images])
                elif len(self.mesh) == 1:
                    self.mesh = self.mesh[0]
            else:
                self.mesh.name = self.name
                self.mesh.label = self.name
                self.mesh.id = self.id


    def load_volume(self, template=None):
        """
        Load the navis volume from each available image in the term.
        """
        if template:
            selected_template = VfbConnect.lookup_id(template)
            self.volume = [ci.image.get_volume() for ci in self.channel_images if ci.image.template_channel.short_form == selected_template][0] if self.channel_images else None
        else:
            self.volume = [ci.image.get_volume() for ci in self.channel_images] if self.channel_images else None
        if self.volume:
            if isinstance(self.volume, list):
                for volume in self.volume:
                        volume.name = self.name
                        volume.label = self.name
                        volume.id = self.id

                if len(self.volume) > 1:
                    print("Multiple volumes found for ", self.name, ". Please specify a template.")
                    print("Available templates: ", [ci.image.template_channel.name for ci in self.channel_images])
                elif len(self.volume) == 1:
                    self.volume = self.volume[0]
            else:
                self.volume.name = self.name
                self.volume.label = self.name
                self.volume.id = self.id

class VFBTerms:
    def __init__(self, terms: List[VFBTerm]):
        self.terms = terms

    def __repr__(self):
        return f"VFBTerms(terms={self.terms})"

    def __getitem__(self, index):
        return self.terms[index]
    
    def __len__(self):
        return len(self.terms)

    def load_skeletons(self, template=None):
        """
        Load the navis skeleton from each available image in the term.
        """
        for term in self.terms:
            term.load_skeleton(template=template)

    def load_meshes(self, template=None):
        """
        Load the navis mesh from each available image in the term.
        """
        for term in self.terms:
            term.load_mesh(template=template)

    def load_volumes(self, template=None):
        """
        Load the navis volume from each available image in the term.
        """
        for term in self.terms:
            term.load_volume(template=template)

    def plot3d(self, template=None):
        """
        Plot the 3D representation of the term's skeleton.
        """
        skeletons=[]
        for term in self.terms:
            if not hasattr(term, 'skeleton'):
                term.load_skeleton(template=template)
            if term.skeleton:
                skeletons.append(term.skeleton)
        if skeletons:
            print(f"Plotting 3D representation of {len(skeletons)} skeletons")
            navis.plot3d(skeletons, backend='auto')

    def get_ids(self):
        return [term.id for term in self.terms]
    
    def get_names(self):
        return [term.name for term in self.terms]
    
    def get_summaries(self):
        return [term.summary for term in self.terms]

def create_vfbterm_list_from_json(json_data):
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

    return VFBTerms([create_vfbterm_from_json(term) for term in data])

# Helper function to create a VFBTerm object from JSON
def create_vfbterm_from_json(json_data):
    """
    Create a VFBTerm object from JSON data.

    :param json_data: JSON data as a string or dictionary.
    :return: A VFBTerm object.
    """
    data = None
    if isinstance(json_data, str):
        data = json.loads(json_data)
    if isinstance(json_data, dict):
        data = json_data
    if isinstance(json_data, list):
        return create_vfbterm_list_from_json(json_data)

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
            print(f"Loaded {len(channel_images)} channel images")

        return VFBTerm(term=term, related_terms=related_terms, channel_images=channel_images)
    else:
        return None

def load_skeletons(vfb_term, template=None):
    """
    Load the navis skeleton from each available image in the term.

    :param vfb_term: A VFBTerm object or list of VFBTerm objects.
    :param template: The short form of the template to load skeletons for.
    :return: None
    """
    if template:
        selected_template = lookup_id(template)
    if isinstance(vfb_term, VFBTerm):
        print("Loading skeletons for ", vfb_term.name) if template == None else print("Loading skeleton for ", vfb_term.name, " aligned to ", template)
        vfb_term.load_skeleton(template=template)
    if isinstance(vfb_term, list):
        for term in vfb_term:
            print("Loading skeletons for ", vfb_term.name) if template == None else print("Loading skeleton for ", vfb_term.name, " aligned to ", template)
            term.load_skeleton(template=template)

