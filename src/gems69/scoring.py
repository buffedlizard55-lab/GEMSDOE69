"""Corridor scoring: multi-physics evidence + strike concordance + stress field
+ joint multi-modality phase coherence.
"""
from __future__ import annotations

import numpy as np

from .corridors import Corridor
from .physics import TRANSFORM_NAMES

# Pre-registered H69-E modal weights (registry/preregistration_h69e.json)
W_GRAV = 0.14
W_MAG = 0.14
W_MAGLOW = 0.12
W_LIDAR = 0.10
W_STRAIGHT = 0.16
W_RAD = 0.12
W_ORIENT = 0.10
W_GEOM = 0.12

GRAV_LAYERS = [
    "grav_upward_edge", "grav_hg_s1", "grav_hg_s2", "grav_hg_s4",
    "grav_tilt_s2", "grav_hg_prov", "grav_vg_prov",
]
MAG_LAYERS = [
    "mag_upward_edge", "mag_hg_s1", "mag_hg_s2", "mag_hg_s4",
    "mag_tilt_s2", "mag_hg_prov", "mag_vg_prov", "tc_prov",
]
MAGLOW_LAYERS = ["mag_low_rtp_res", "mag_low_tmi", "mag_low_rtp"]
SCARP_LAYERS = ["lidar_scarp", "elev_curv_ridge", "det_elev_slope"]
EXT_LAYERS = ["basement_step", "cond_step", "rad_kth_local_excess", "thermal_conduit"]

GEOM_PRIOR = {
    "pull-apart": 1.00,
    "relay-ramp": 0.92,
    "termination-splay": 0.86,
    "transfer-overlap": 0.60,
}
NNE_AXES = (0.0, 22.5, 45.0)
ORIENT_SIGMA_DEG = 30.0
S0_DEFAULT = 0.72


def axial_distance(az: float, axes=NNE_AXES) -> float:
    best = 90.0
    for a in axes:
        d = abs(az - a) % 180.0
        best = min(best, min(d, 180.0 - d))
    return best


def orientation_weight(mean_az: float) -> float:
    return float(np.exp(-(axial_distance(mean_az) / ORIENT_SIGMA_DEG) ** 2))


def score_corridor(corridor: Corridor, evidence: dict[str, float],
                   include_extended: bool = True) -> dict:
    """Compute corridor physics/geometry score S and record geologist rationale."""
    e_grav = max((evidence.get(n, 0.0) for n in GRAV_LAYERS), default=0.0)
    e_mag = max((evidence.get(n, 0.0) for n in MAG_LAYERS), default=0.0)
    e_low = max((evidence.get(n, 0.0) for n in MAGLOW_LAYERS), default=0.0)
    e_scarp = max((evidence.get(n, 0.0) for n in SCARP_LAYERS), default=0.0)
    st_align = float(evidence.get("lidar_strike_concordance", 0.0))
    c_phase = float(evidence.get("joint_phase_coherence", 0.0))
    w_o = orientation_weight(corridor.pair.mean_az)
    w_g = GEOM_PRIOR.get(corridor.subtype, 0.60)

    S = (0.20 * max(e_grav, 0.0)
         + 0.18 * max(e_mag, 0.0)
         + 0.14 * max(e_low, 0.0)
         + 0.20 * (max(e_scarp, 0.0) + 0.55 * st_align)
         + 0.12 * (2.0 * c_phase)
         + 0.08 * w_o
         + 0.08 * w_g)

    e_ext = 0.0
    if include_extended:
        e_base = max(evidence.get("basement_step", 0.0), 0.0)
        e_cond = max(evidence.get("cond_step", 0.0), 0.0)
        e_rad = max(evidence.get("rad_kth_local_excess", 0.0), 0.0)
        e_th = max(evidence.get("thermal_conduit", 0.0), 0.0)
        e_ext = 0.35 * e_base + 0.20 * e_cond + 0.25 * e_rad + 0.20 * e_th
        S = 0.86 * S + 0.14 * e_ext

    corridor.rationale["layers"] = [
        {"name": n, "z": round(float(evidence.get(n, 0.0)), 3)}
        for n in TRANSFORM_NAMES if n in evidence
    ]
    corridor.rationale["evidence_groups"] = {
        "E_grav": round(float(e_grav), 3),
        "E_mag": round(float(e_mag), 3),
        "E_maglow": round(float(e_low), 3),
        "E_scarp": round(float(e_scarp), 3),
        "lidar_strike_concordance": round(st_align, 3),
        "joint_phase_coherence": round(c_phase, 3),
        "E_extended": round(float(e_ext), 3),
        "W_orient": round(float(w_o), 3),
        "W_geom": round(float(w_g), 3),
    }
    corridor.rationale["score_S"] = round(float(S), 4)
    corridor.rationale["orientation_az_deg"] = round(corridor.pair.mean_az, 2)
    corridor.rationale["orientation_note"] = (
        "N-NE axial family best oriented for dilation under WNW (~112.5 deg) extension"
    )
    return {
        "S": float(S), "E_grav": e_grav, "E_mag": e_mag, "E_maglow": e_low,
        "E_scarp": e_scarp, "C_phase": c_phase, "W_orient": w_o, "W_geom": w_g,
    }


def propensity_from_score(S: float, s0: float = S0_DEFAULT) -> float:
    return float(1.0 / (1.0 + np.exp(-1.5 * (S - s0))))


def build_propensity(corridors: list[Corridor], shape: tuple[int, int],
                     s0: float = S0_DEFAULT) -> np.ndarray:
    """Max over corridors of propensity(score) * distance-graded trace weight."""
    p = np.zeros(shape, np.float32)
    for c in corridors:
        pc = propensity_from_score(c.rationale.get("score_S", 0.0), s0)
        c.render_into(p, pc)
    return p


def build_corridor_fields(corridors: list[Corridor], shape: tuple[int, int],
                          s0: float = S0_DEFAULT) -> dict[str, np.ndarray]:
    """Render pixel-level corridor structural fields for OOF calibration."""
    prop = np.zeros(shape, np.float32)
    core_w = np.zeros(shape, np.float32)
    phase_map = np.zeros(shape, np.float32)
    mult = np.zeros(shape, np.uint16)
    for c in corridors:
        sc = float(c.rationale.get("score_S", 0.0))
        pc = propensity_from_score(sc, s0)
        ph = float(c.rationale.get("evidence_groups", {}).get("joint_phase_coherence", 0.0))
        r0, r1, c0, c1 = c.bbox
        m = c.local_mask
        w = c.local_weight
        sl_p = prop[r0:r1, c0:c1]
        sl_p[m] = np.maximum(sl_p[m], pc * w[m])
        sl_w = core_w[r0:r1, c0:c1]
        sl_w[m] = np.maximum(sl_w[m], w[m])
        sl_ph = phase_map[r0:r1, c0:c1]
        sl_ph[m] = np.maximum(sl_ph[m], ph * w[m])
        mult[r0:r1, c0:c1][m] += 1
    core_mask = core_w >= 0.72
    if core_mask.any():
        dist_trace = np.minimum(ndi.distance_transform_edt(~core_mask), 40.0).astype(np.float32)
    else:
        dist_trace = np.full(shape, 40.0, np.float32)
    return {
        "corridor_propensity": prop,
        "corridor_core_weight": core_w,
        "corridor_phase": phase_map,
        "corridor_multiplicity": np.minimum(mult, 12).astype(np.float32),
        "neg_dist_corridor_trace": -dist_trace,
    }


from scipy import ndimage as ndi  # noqa: E402
