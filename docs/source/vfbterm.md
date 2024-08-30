# VFB_connect object formats

## VFBTerm Class Properties

### Fixed Properties

These properties are initialized directly when an object of `VFBTerm` is created:

1. **`vfb`**: Reference to the `vfb_connect` module for accessing shared functionalities.
2. **`debug`**: Boolean to enable or disable verbose/debug output.
3. **`id`**: The ID of the term.
4. **`name`**: The name of the term, initialized to "unresolved" if not set.
5. **`description`**: A string that describes the term.
6. **`url`**: The URL link to more information about the term.
7. **`thumbnail`**: Thumbnail image for the term.
8. **`counts`**: A dictionary holding count information, typically about related data or entities.
9. **`publications`**: A list of `Publication` objects associated with the term.
10. **`license`**: A `Term` object representing the license associated with the term.
11. **`xrefs`**: A list of `Xref` objects containing cross-reference information.
12. **`synonyms`**: A `Synonym` object representing synonyms for the term.
13. **`related_terms`**: A `Relations` object representing relationships with other terms.
14. **`channel_images`**: A list of `ChannelImage` objects associated with the term.
15. **`_load_complete`**: Boolean flag to indicate whether the term has been fully loaded.
16. **`types`**: Represents different types or classifications of the term.
17. **`has_image`**: Boolean indicating if the term has associated images.
18. **`has_scRNAseq`**: Boolean indicating if the term has associated single-cell RNA sequencing data.
19. **`has_neuron_connectivity`**: Boolean indicating if the term has neuron connectivity data.
20. **`has_region_connectivity`**: Boolean indicating if the term has region connectivity data.
21. **`_gene_function_filters`**: List of gene function filters obtained from `vfb`.
22. **`is_type`, `is_instance`, `is_template`, `is_dataset`, `is_neuron`**: Boolean flags to indicate different categories or types of terms.

### Lazy-Loaded Properties

These properties are loaded on first access, with the loaded data stored in internal attributes prefixed with an underscore (`_X`). Users should access the properties using the official names listed below:

1. **`parents`**: Returns a `VFBTerms` object representing the parent terms.
   - **Internal Storage**: `_parents`

2. **`subtypes`**: Returns subtypes of this term.
   - **Internal Storage**: `_subtypes`

3. **`subparts`**: Returns subparts of this term.
   - **Internal Storage**: `_subparts`

4. **`children`**: Returns a combination of subtypes and subparts.
   - **Internal Storage**: `_children`

5. **`regions`**: Returns a `VFBTerms` object representing regions associated with the term.
   - **Internal Storage**: `_regions`

6. **`instances`**: Returns a `VFBTerms` object representing instances of this term.
   - **Internal Storage**: `_instances`

7. **`skeleton`**: Returns the neuron skeleton associated with the term.
   - **Internal Storage**: `_skeleton`

8. **`mesh`**: Returns the 3D mesh associated with the term.
   - **Internal Storage**: `_mesh`

9. **`volume`**: Returns the volume data associated with the term.
   - **Internal Storage**: `_volume`

10. **`summary`**: Returns a summary of the term's information.
    - **Internal Storage**: `_summary`

11. **`scRNAseq_expression`**: Returns single-cell RNA sequencing expression data.
    - **Internal Storage**: `_scRNAseq_expression`

12. **`neurons_that_overlap`**: Returns neurons that overlap with this region.
    - **Internal Storage**: `_neurons_that_overlap`

13. **`neurons_with_synaptic_terminals_here`**: Returns neurons with synaptic terminals in this region.
    - **Internal Storage**: `_neurons_with_synaptic_terminals_here`

14. **`upstream_neurons`**: Returns neurons upstream of this term.
    - **Internal Storage**: `_upstream_neurons`

15. **`downstream_neurons`**: Returns neurons downstream of this term.
    - **Internal Storage**: `_downstream_neurons`

16. **`upstream_neuron_types`**: Returns types of neurons upstream of this term.
    - **Internal Storage**: `_upstream_neuron_types`

17. **`downstream_neuron_types`**: Returns types of neurons downstream of this term.
    - **Internal Storage**: `_downstream_neuron_types`

18. **`neuron_types_that_overlap`**: Returns neuron types overlapping with this region.
    - **Internal Storage**: `_neuron_types_that_overlap`

19. **`neuron_types_with_synaptic_terminals_here`**: Returns neuron types with synaptic terminals in this region.
    - **Internal Storage**: `_neuron_types_with_synaptic_terminals_here`

20. **`similar_neurons_nblast`**: Returns neurons similar to this neuron based on NBLAST scores.
    - **Internal Storage**: `_similar_neurons_nblast`

21. **`potential_drivers_nblast`**: Returns potential drivers of this neuron based on NBLAST scores.
    - **Internal Storage**: `_potential_drivers_nblast`

22. **`potential_drivers_neuronbridge`**: Returns potential drivers of this neuron based on NeuronBridge scores.
    - **Internal Storage**: `_potential_drivers_neuronbridge`

23. **`lineage_clones`**: Returns lineage clones associated with this term.
    - **Internal Storage**: `_lineage_clones`

24. **`lineage_clone_types`**: Returns lineage clone types associated with this term.
    - **Internal Storage**: `_lineage_clone_types`

25. **`scRNAseq_genes`**: Returns genes associated with this cluster.
    - **Internal Storage**: `_scRNAseq_genes`

26. **`transgene_expression`**: Returns transgene expression data associated with this term.
    - **Internal Storage**: `_transgene_expression`

27. **`innervating`**: Returns nerves or tracts innervating this term.
    - **Internal Storage**: `_innervating`

### Special Methods and Utilities

1. **`load_skeleton()`**: Method to load the skeleton representation.
2. **`load_mesh()`**: Method to load the mesh representation.
3. **`load_volume()`**: Method to load the volume representation.
4. **`plot3d()`**: Plot the 3D representation using Navis.
5. **`plot2d()`**: Plot the 2D representation using Navis.
6. **`show()`**: Display the term's associated image.
7. **`open()`**: Open the term's URL in the default web browser.
8. **`downstream_partners()`**: Get neurons downstream of this neuron.
9. **`upstream_partners()`**: Get neurons upstream of this neuron.
10. **`plot_partners()`**: Plot a network of neuron partners.
11. **`plot_similar()`**: Plot a network of similar neurons or potential drivers.
12. **`get_summary()`**: Returns a summary of the term's information.

## VFBTerms Class Properties

### Fixed Properties

These properties are initialized directly when an object of `VFBTerms` is created:

1. **`vfb`**: Reference to the `vfb_connect` module for accessing shared functionalities.
2. **`terms`**: A list of `VFBTerm` objects that this `VFBTerms` instance holds.
3. **`_summary`**: A cached summary of the terms, initially set to `None`.

### Lazy-Loaded Properties

These properties are computed on first access, with their data being stored in internal attributes prefixed with an underscore (`_X`). Users should access these properties using the official names listed below:

1. **`summary`**: Returns a summary of the terms, either as a DataFrame or a list of summaries, depending on the implementation.
   - **Internal Storage**: `_summary`

### Special Methods and Utilities

1. **`__init__`**: Initializes a `VFBTerms` object. The constructor supports initialization with different input types, including a list of `VFBTerm` objects, a list of term IDs (strings), a DataFrame, a list of dictionaries, or another `VFBTerms` object.
2. **`__repr__`**: Provides a string representation of the `VFBTerms` object.
3. **`__getitem__`**: Allows indexing and slicing of `VFBTerms` objects, returning either a single `VFBTerm` or a new `VFBTerms` object.
4. **`__len__`**: Returns the number of `VFBTerm` objects within this `VFBTerms` instance.
5. **`__eq__` and `__ne__`**: Compares two `VFBTerms` objects for equality or inequality based on their term IDs.
6. **`__contains__`**: Checks if a given `VFBTerm` or term ID is in the `VFBTerms` object.
7. **`__hash__`**: Provides a hash value based on the set of term IDs, making `VFBTerms` hashable and suitable for use in sets or as dictionary keys.
8. **`__str__`**: Returns a string representation of the `VFBTerms` object, specifically listing the term names.
9. **`__add__`, `__sub__`**: Implements addition and subtraction operations for `VFBTerms`, allowing combination or removal of terms.
10. **`__lt__`, `__le__`, `__gt__`, `__ge__`**: Provides comparison methods for sorting or ordering `VFBTerms` objects based on term IDs.
11. **`__iter__`**: Makes the `VFBTerms` object iterable, returning an iterator over its list of `VFBTerm` objects.
12. **`get_all()`**: Retrieves unique values for a given property from all terms, optionally returning a dictionary mapping values to term IDs.
13. **`get_colours_for()`**: Retrieves colors for visualizing terms based on a given property, optionally taking the first value from iterable properties.
14. **`AND()`, `OR()`, `XOR()`, `NAND()`, `NOR()`, `XNOR()`, `NOT()`**: Logical operations for combining or filtering `VFBTerms` based on sets of terms.
15. **`load_skeletons()`, `load_meshes()`, `load_volumes()`**: Load respective representations (skeletons, meshes, volumes) for all terms.
16. **`plot3d()`, `plot2d()`**: Plot 3D or 2D representations of terms using Navis.
17. **`plot3d_by_type()`**: Plot the 3D representation of terms, colored by their parent type.
18. **`_get_plot_images()`**: Helper method to retrieve images for plotting.
19. **`get_ids()`, `get_names()`**: Retrieve lists of term IDs or names.
20. **`get_summaries()`**: Retrieve summaries of all terms, returning a list or DataFrame.
21. **`open()`**: Opens the VFB browser with the terms' URLs.
22. **`show()`**: Displays a merged thumbnail for all terms, particularly useful in Jupyter notebooks.
23. **`tqdm_with_threshold()`**: Custom tqdm method to show progress bars only if the length of the iterable exceeds a certain threshold.

### Notes on Usage and Implementation

- **Initialization Flexibility**: The `__init__` method of `VFBTerms` provides flexibility by accepting different input types, including lists of `VFBTerm` objects, term IDs, DataFrames, and dictionaries. This allows users to create a `VFBTerms` object from various data sources seamlessly.

- **Lazy-Loaded Summaries**: The `summary` property is computed on first access, and its result is cached in `_summary` to improve performance on subsequent accesses. This design ensures that expensive computations are not repeated unnecessarily.

- **Logical Operations**: The class supports logical operations (AND, OR, XOR, etc.) for combining or filtering `VFBTerms` objects, making it easier to perform set-based manipulations on collections of terms.

- **Visualization Support**: Methods like `plot3d()`, `plot2d()`, and `plot3d_by_type()` provide integrated visualization capabilities using Navis, facilitating the exploration of term data in 3D and 2D formats.

- **Helper Methods**: Methods like `get_ids()`, `get_names()`, and `get_summaries()` provide convenient access to commonly needed information, streamlining the process of working with multiple terms.

### Error Handling

- **Type Checking**: The class checks input types during initialization and method operations, raising appropriate exceptions (`TypeError`, `ValueError`) when unsupported types are encountered.

- **ID-Based Operations**: Methods that rely on term IDs (`__contains__`, `__getitem__`, logical operations) ensure that IDs are handled consistently, preventing errors due to mismatched or missing data.
