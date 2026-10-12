"""GEMSDOE69 lane: relay-ramp and pull-apart corridor generator.

Proposes candidate fault traces from the *geometry of the mapped catalogue*
(INGENIOUS Quaternary-fault polylines): relay ramps between same-dip fault
tips, pull-aparts at releasing steps of strike-slip faults and transfer zones
at strike-slip terminations.  Corridors are scored with geophysical evidence
(multi-scale gravity / magnetic edges, magnetic lows, lidar scarps) and the
dilation tendency of the corridor under WNW extension, then dots are placed by
the shared template's calibrated greedy marginal-DTI allocator.

Shared, pinned tools (evaluator, writer, validator, uniqueness, allocator) are
imported from ``vendor/gems57`` -- a byte-for-byte copy of
``buffedlizard55-lab/60GEMSDOE/src/gems57`` (see ``registry/template_pin.json``).
"""

__all__ = ["data", "evidence", "traces", "corridors", "calibrate"]
