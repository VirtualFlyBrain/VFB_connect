import json
from typing import List, Optional


class MinimalEntityInfo:
    def __init__(self, short_form: str, iri: str, label: str, types: List[str], unique_facets: Optional[List[str]] = None, symbol: Optional[str] = None):
        self.short_form = short_form
        self.iri = iri
        self.label = label
        self.types = types
        self.unique_facets = unique_facets
        self.symbol = symbol

    def name(self):
        return self.symbol if self.symbol else self.label
    
    def __str__(self):
        return f"{self.name()}"

    def __repr__(self):
        return f"MinimalEntityInfo(name={self.name()}, short_form={self.short_form})"


class MinimalEdgeInfo:
    def __init__(self, iri: str, label: str, type: str, short_form: Optional[str] = None, confidence_value: Optional[str] = None, database_cross_reference: Optional[List[str]] = None):
        self.short_form = short_form
        self.iri = iri
        self.label = label
        self.type = type
        self.confidence_value = confidence_value
        self.database_cross_reference = database_cross_reference

    def __repr__(self):
        return f"MinimalEdgeInfo(label={self.label}, type={self.type})"


class Term:
    def __init__(self, core: MinimalEntityInfo, description: Optional[List[str]] = None, comment: Optional[List[str]] = None, link: Optional[str] = None, icon: Optional[str] = None):
        self.core = core
        self.description = description
        self.comment = comment
        self.link = link
        self.icon = icon

    def __repr__(self):
        return f"Term(core={self.core}, link={self.link})"


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
        self.index = index
        self.image_nrrd = image_nrrd
        self.image_thumbnail = image_thumbnail
        self.image_swc = image_swc
        self.image_obj = image_obj
        self.image_wlz = image_wlz

    def __repr__(self):
        return f"Image(image_folder={self.image_folder})"


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

    def __repr__(self):
        return f"VFBTerm(term={self.term})"

    def get_summary(self):
        """
        Returns a summary of the term's information.
        """
        summary = {
            "ID": self.term.core.short_form,
            "Label": self.term.core.label,
            "Description": self.term.description,
            "Link": self.term.link,
            "Icon": self.term.icon,
        }
        if self.related_terms:
            summary["Related Terms"] = [str(rel) for rel in self.related_terms]
        if self.channel_images:
            summary["Channel Images"] = [str(ci) for ci in self.channel_images]

        return summary


# Helper function to create a VFBTerm object from JSON
def create_vfbterm_from_json(json_data):
    data = json.loads(json_data)
    
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
    if 'channel_images' in data:
        channel_images = []
        for ci in data['channel_images']:
            image_data = ci['image']
            image = Image(template_channel=MinimalEntityInfo(**image_data['template_channel']),
                          template_anatomy=MinimalEntityInfo(**image_data['template_anatomy']),
                          **image_data)
            channel_image = ChannelImage(image=image, channel=MinimalEntityInfo(**ci['channel']),
                                         imaging_technique=MinimalEntityInfo(**ci['imaging_technique']))
            channel_images.append(channel_image)

    return VFBTerm(term=term, related_terms=related_terms, channel_images=channel_images)
