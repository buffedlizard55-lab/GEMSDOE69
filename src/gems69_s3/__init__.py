"""GEMSDOE69 lane: relay-ramp and pull-apart corridor generator.

Proposes hidden faults from *catalogue geometry* (tip graph of mapped fault
polylines) rather than pixel statistics.  Shared-template scoring machinery is
reused byte-pinned from ``vendor/template66`` (GEMSDOE66 ``src/gems57`` +
``src/gems``); nothing here re-implements the official DTI arithmetic.

Lane provenance: GEMSDOE69 parallel-run lane, prompt method paragraph
(relay-ramp / pull-apart corridor generator, Giddens & Faulds 2025 SGP-TR-229
step-over inventory as cited in the standing prompt).
"""

__version__ = "0.1.0"
