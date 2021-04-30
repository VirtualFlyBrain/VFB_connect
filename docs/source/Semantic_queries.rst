VFB Semantic queries
====================

A variety of methods on ``VfbConnect`` and ``VFBConnect.oc`` take an OWL class expression using labels
or symbols as input.  The simplest expression is just a class (type), e.g. ``nodulus`` or ``DL1_adPN``.
More extended queries are also possible.

* ``'GABAergic neuron' that 'overlaps' some 'nodulus'``
* ``'neuron' that 'overlaps' some 'adult antennal lobe glomerulus DL1'``

Note that all entities, including the relation (in this case ``overlaps``) must be in single quotes.


