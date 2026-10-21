"""Radiometric-augmented joint scoring for H2.

Combines H1 joint grav+mag coincidence with K depletion / Th/K halo inside
corridor interiors. Targets hydrothermally altered fault damage zones that
lack scarps but show demagnetization + K leaching.

Weights pre-registered before holdout look:
  S = 0.30*min(E_grav,E_mag) +0.10*max(E_grav,E_mag) +0.12*E_low_w +0.12*E_lidar +0.08*W_orient +0.08*W_geom +0.20*E_rad

E_rad = max(rad_K_neg, rad_ThK_pos, rad_Th_pos)  # K depletion or Th enrichment
"""
from __future__ import annotations

import numpy as np

from .corridors import Corridor
from .physics import TRANSFORM_NAMES
from .scoring import GRAV_LAYERS, LIDAR_LAYERS, MAG_LAYERS, MAGLOW_LAYERS, GEOM_PRIOR, orientation_weight, propensity_from_score, S0_DEFAULT
from .radiometric import NAMES as RAD_NAMES

RAD_LAYERS = ["rad_K_neg", "rad_ThK_pos", "rad_Th_pos"]  # TC_neg optional


def score_corridor_rad(corridor: Corridor, evidence: dict[str, float]) -> dict:
    e_grav = max((evidence.get(n, 0.0) for n in GRAV_LAYERS), default=0.0)
    e_mag = max((evidence.get(n, 0.0) for n in MAG_LAYERS), default=0.0)
    e_low = max((evidence.get(n, 0.0) for n in MAGLOW_LAYERS), default=0.0)
    e_lid = max((evidence.get(n, 0.0) for n in LIDAR_LAYERS), default=0.0)
    e_rad = max((evidence.get(n, 0.0) for n in RAD_LAYERS), default=0.0)
    w_o = orientation_weight(corridor.pair.mean_az)
    w_g = GEOM_PRIOR.get(corridor.subtype, 0.6)

    joint = min(max(e_grav, 0.0), max(e_mag, 0.0))
    single_max = max(max(e_grav, 0.0), max(e_mag, 0.0))
    low_w = max(e_low, 0.0) * (1.0 if joint > 0.5 else 0.6)

    S = 0.30 * joint + 0.10 * single_max + 0.12 * low_w + 0.12 * max(e_lid, 0.0) + 0.08 * w_o + 0.08 * w_g + 0.20 * max(e_rad, 0.0)

    corridor.rationale["layers"] = [{"name": n, "z": round(evidence.get(n, 0.0), 3)} for n in (TRANSFORM_NAMES + RAD_NAMES)]
    corridor.rationale["evidence_groups"] = {
        "E_grav": round(e_grav, 3),
        "E_mag": round(e_mag, 3),
        "E_joint_min": round(joint, 3),
        "E_single_max": round(single_max, 3),
        "E_maglow_w": round(low_w, 3),
        "E_lidar": round(e_lid, 3),
        "E_rad": round(e_rad, 3),
        "W_orient": round(w_o, 3),
        "W_geom": round(w_g, 3),
    }
    corridor.rationale["score_S"] = round(float(S), 4)
    corridor.rationale["scoring_mode"] = "H2_joint_rad_v1"
    corridor.rationale["orientation_az_deg"] = round(corridor.pair.mean_az, 2)
    return {"S": float(S), "E_grav": e_grav, "E_mag": e_mag, "E_joint": joint, "E_rad": e_rad}


def build_propensity_rad(corridors, shape, s0=S0_DEFAULT):
    p = np.zeros(shape, np.float32)
    for c in corridors:
        pc = propensity_from_score(c.rationale.get("score_S", 0.0), s0)
        c.render_into(p, pc)
    return p
