"""Corridor scoring: multi-physics evidence + orientation consistency.

Pre-registered weights (fixed before any holdout look; only the single scalar
``S0`` in the propensity map may be calibrated on the holdout):

    S = 0.14 E_grav + 0.14 E_mag + 0.12 E_maglow + 0.10 E_lidar
        + 0.16 E_straight + 0.12 E_rad + 0.10 W_orient + 0.12 W_geom

E_grav / E_mag are the max robust-z mean across their multi-scale HG + tilt +
provided-edge layers; E_maglow the max of -tmi/-rtp z; E_lidar the lidar-scarp
z; E_straight is the max of conductivity and basement-depth structure-tensor
coherence (H69-E); E_rad is the max of K-depletion and Th/K (H69-E);
W_orient scores the corridor axis against the N-NE family best oriented for
dilation under WNW extension (standing prompt; GeoDAWN footprint is Walker
Lane); W_geom is the corridor-subtype prior (pull-apart and transfer zones
favoured in Walker Lane hot systems per the standing prompt).

Weights were rebalanced on 2026-10-20 *before* the H69-E holdout look and are
pinned in registry/preregistration_h69e.json. They are not fit to labels.
"""
from __future__ import annotations

import numpy as np

from .corridors import Corridor
from .physics import TRANSFORM_NAMES, LayerStats

GRAV_LAYERS = ["grav_hg_s1", "grav_hg_s2", "grav_hg_s4", "grav_tilt_s2",
               "grav_hg_prov", "grav_vg_prov", "geod_2ndinv"]
MAG_LAYERS = ["mag_hg_s1", "mag_hg_s2", "mag_hg_s4", "mag_tilt_s2",
              "mag_hg_prov", "mag_vg_prov", "tc_prov"]
MAGLOW_LAYERS = ["mag_low_tmi", "mag_low_rtp"]
LIDAR_LAYERS = ["lidar_scarp"]
STRAIGHT_LAYERS = ["cond_straight", "base_straight"]
RAD_LAYERS = ["rad_k_depl", "rad_thk"]

# Pre-registered 2026-10-20 (H69-E). Sum is 1.0. Not fit to the holdout.
W_GRAV, W_MAG, W_MAGLOW, W_LIDAR = 0.14, 0.14, 0.12, 0.10
W_STRAIGHT, W_RAD = 0.16, 0.12
W_ORIENT, W_GEOM = 0.10, 0.12
GEOM_PRIOR = {"pull-apart": 1.0, "relay-ramp": 0.9, "transfer-overlap": 0.7}
# Drop the bottom quartile after scoring. Fixed before the holdout look.
SCORE_FLOOR_QUANTILE = 0.25
NNE_AXES = (0.0, 22.5, 45.0)     # axial azimuths, deg
ORIENT_SIGMA_DEG = 30.0
S0_DEFAULT = 0.75                 # pre-registered scalar; the single parameter calibration may touch


def axial_distance(az: float, axes=NNE_AXES) -> float:
    best = 90.0
    for a in axes:
        d = abs(az - a) % 180.0
        best = min(best, min(d, 180.0 - d))
    return best


def orientation_weight(mean_az: float) -> float:
    return float(np.exp(-(axial_distance(mean_az) / ORIENT_SIGMA_DEG) ** 2))


def score_corridor(corridor: Corridor, evidence: dict[str, float]) -> dict:
    """Return the corridor score S and the per-layer rationale entries."""
    e_grav = max((evidence.get(n, 0.0) for n in GRAV_LAYERS), default=0.0)
    e_mag = max((evidence.get(n, 0.0) for n in MAG_LAYERS), default=0.0)
    e_low = max((evidence.get(n, 0.0) for n in MAGLOW_LAYERS), default=0.0)
    e_lid = max((evidence.get(n, 0.0) for n in LIDAR_LAYERS), default=0.0)
    e_str = max((evidence.get(n, 0.0) for n in STRAIGHT_LAYERS), default=0.0)
    e_rad = max((evidence.get(n, 0.0) for n in RAD_LAYERS), default=0.0)
    w_o = orientation_weight(corridor.pair.mean_az)
    w_g = GEOM_PRIOR.get(corridor.subtype, 0.6)
    S = (W_GRAV * max(e_grav, 0.0) + W_MAG * max(e_mag, 0.0)
         + W_MAGLOW * max(e_low, 0.0) + W_LIDAR * max(e_lid, 0.0)
         + W_STRAIGHT * max(e_str, 0.0) + W_RAD * max(e_rad, 0.0)
         + W_ORIENT * w_o + W_GEOM * w_g)
    corridor.rationale["layers"] = [
        {"name": n, "z": round(evidence.get(n, 0.0), 3)} for n in TRANSFORM_NAMES
    ]
    corridor.rationale["evidence_groups"] = {
        "E_grav": round(e_grav, 3), "E_mag": round(e_mag, 3),
        "E_maglow": round(e_low, 3), "E_lidar": round(e_lid, 3),
        "E_straight": round(e_str, 3), "E_rad": round(e_rad, 3),
        "W_orient": round(w_o, 3), "W_geom": round(w_g, 3),
    }
    corridor.rationale["score_S"] = round(float(S), 4)
    corridor.rationale["orientation_az_deg"] = round(corridor.pair.mean_az, 2)
    corridor.rationale["orientation_note"] = ("N-NE axial family best oriented for dilation "
                                              "under WNW extension (standing prompt)")
    return {"S": float(S), "E_grav": e_grav, "E_mag": e_mag, "E_maglow": e_low,
            "E_lidar": e_lid, "E_straight": e_str, "E_rad": e_rad,
            "W_orient": w_o, "W_geom": w_g}


def propensity_from_score(S: float, s0: float = S0_DEFAULT) -> float:
    """Monotone map corridor score -> per-pixel propensity in (0, 1)."""
    return float(1.0 / (1.0 + np.exp(-1.5 * (S - s0))))


def build_propensity(corridors: list[Corridor], shape: tuple[int, int],
                     s0: float = S0_DEFAULT) -> np.ndarray:
    """P(x) = max over corridors of propensity(score) * corridor membership weight."""
    p = np.zeros(shape, np.float32)
    for c in corridors:
        pc = propensity_from_score(c.rationale.get("score_S", 0.0), s0)
        c.render_into(p, pc)
    return p
