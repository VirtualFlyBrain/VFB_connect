VFB Semantic queries
====================

A variety of methods on ``VfbConnect`` and ``VFBConnect.oc`` take an OWL class expression using labels, symbols
or short form IDs as input.  The simplest expression is just a class (type), e.g. ``nodulus`` or ``DL1_adPN``.
More extended queries are also possible.

* ``'GABAergic neuron' that 'overlaps' some 'nodulus'``
* ``'neuron' that 'overlaps' some 'adult antennal lobe glomerulus DL1'``
* ``'ALad1 lineage neuron' that 'overlaps' some 'adult antennal lobe'``

Note that all entities, including the relation (in this case ``overlaps``) must be in single quotes.

For most neuron query use cases `overlaps` is likely to be sufficient

relations guide
---------------

TBA




