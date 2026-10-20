"""Joint convergent edge scoring for H1 (before holdout look, pre-registered).

H1 hypothesis: relay connector requires coincident multi-scale edges on both
gravity and magnetics (AND logic), not just max over either physics (OR logic).
This should catch buried relay linkage between step-over tips that separates
two basement blocks, whereas lithologic contacts typically show only one physics.

Pre-registered weights (fixed before any holdout look; only S0 may be calibrated):
    S_joint = 0.35 * min(E_grav, E_mag)   # joint requirement (both must be strong)
            + 0.15 * max(E_grav, E_mag)   # bonus for strong single physics
            + 0.15 * E_maglow_weighted    # magnetic low only counts if joint strong
            + 0.15 * E_lidar
            + 0.10 * W_orient
            + 0.10 * W_geom

E_grav = max robust-z over GRAV_LAYERS (HG 1/2/4 + tilt + provided)
E_mag  = max over MAG_LAYERS
E_low  = max over MAGLOW_LAYERS (magnetic lows)
E_low_weighted = E_low * (1.0 if min(E_grav,E_mag) > 0.5 else 0.6)  # gate low by joint strength
E_lidar = lidar_scarp
W_orient = exp(-(axial_dist(az, N-NE)/30)^2)
W_geom = pull-apart 1.0, relay-ramp 0.9, transfer-overlap 0.6
S0 = 0.75 (logistic centre; the single calibrated scalar)

This differs from the baseline additive OR scoring:
  S_base = 0.20 E_grav +0.20 E_mag +0.18 E_low +0.15 E_lidar +0.10 W_orient +0.17 W_geom
which awards corridors with EITHER grav OR mag high. Joint scoring requires BOTH.
"""
from __future__ import annotations

import numpy as np

from .corridors import Corridor
from .physics import TRANSFORM_NAMES
from .scoring import (
    GRAV_LAYERS,
    LIDAR_LAYERS,
    MAG_LAYERS,
    MAGLOW_LAYERS,
    GEOM_PRIOR,
    NNE_AXES,
    ORIENT_SIGMA_DEG,
    S0_DEFAULT,
    axial_distance,
    orientation_weight,
    propensity_from_score,
)


def score_corridor_joint(corridor: Corridor, evidence: dict[str, float]) -> dict:
    e_grav = max((evidence.get(n, 0.0) for n in GRAV_LAYERS), default=0.0)
    e_mag = max((evidence.get(n, 0.0) for n in MAG_LAYERS), default=0.0)
    e_low = max((evidence.get(n, 0.0) for n in MAGLOW_LAYERS), default=0.0)
    e_lid = max((evidence.get(n, 0.0) for n in LIDAR_LAYERS), default=0.0)
    w_o = orientation_weight(corridor.pair.mean_az)
    w_g = GEOM_PRIOR.get(corridor.subtype, 0.6)

    # joint requirement: both grav and mag must be strong
    joint = min(max(e_grav, 0.0), max(e_mag, 0.0))
    single_max = max(max(e_grav, 0.0), max(e_mag, 0.0))
    # gate magnetic low by joint strength (alteration halos only count if structural linkage present)
    low_weighted = max(e_low, 0.0) * (1.0 if joint > 0.5 else 0.6)

    S = (0.35 * joint + 0.15 * single_max + 0.15 * low_weighted + 0.15 * max(e_lid, 0.0) + 0.10 * w_o + 0.10 * w_g)

    corridor.rationale["layers"] = [{"name": n, "z": round(evidence.get(n, 0.0), 3)} for n in TRANSFORM_NAMES]
    corridor.rationale["evidence_groups"] = {
        "E_grav": round(e_grav, 3),
        "E_mag": round(e_mag, 3),
        "E_joint_min": round(joint, 3),
        "E_single_max": round(single_max, 3),
        "E_maglow_raw": round(e_low, 3),
        "E_maglow_weighted": round(low_weighted, 3),
        "E_lidar": round(e_lid, 3),
        "W_orient": round(w_o, 3),
        "W_geom": round(w_g, 3),
    }
    corridor.rationale["score_S"] = round(float(S), 4)
    corridor.rationale["score_S_joint"] = round(float(S), 4)
    corridor.rationale["scoring_mode"] = "H1_convergent_joint_v1"
    corridor.rationale["orientation_az_deg"] = round(corridor.pair.mean_az, 2)
    corridor.rationale["orientation_note"] = "N-NE axial family best oriented for dilation under WNW extension; joint grav+mag required"

    return {"S": float(S), "E_grav": e_grav, "E_mag": e_mag, "E_joint": joint, "E_low": low_weighted, "E_lidar": e_lid, "W_orient": w_o, "W_geom": w_g}


def build_propensity_joint(corridors: list[Corridor], shape: tuple[int, int], s0: float = S0_DEFAULT) -> np.ndarray:
    p = np.zeros(shape, np.float32)
    for c in corridors:
        pc = propensity_from_score(c.rationale.get("score_S", 0.0), s0)
        c.render_into(p, pc)
    return p
