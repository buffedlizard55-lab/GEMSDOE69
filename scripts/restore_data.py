#!/usr/bin/env python3
"""Restore every pinned input into $GEMS_DATA (default /tmp/gems_data) and verify SHA-256.

Sources are the owner's public mirrors (the DrivenData data tab is login-walled):
  * training_features.tif  = concatenation of five parts in
    buffedlizard55-lab/GEMSDOE @ c0c06ac82178f26b94fce3397036ef8f12a2f3a0 (data/bridge/)
    -- the mirror manifest records the organizer Dropbox links it was copied from
  * existing_faults.tif, sample_submission.tif and the external layers from
    buffedlizard55-lab/60GEMSDOE @ 32024716f218d06a94e01464157392119c03cb15 (data/)
Blob-less partial clones are used (no per-file REST calls -> no API rate limit).
Pins prove mirror consistency, NOT organizer authentication.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems69.data import DATA, PINS, sha256  # noqa: E402

FEAT_REPO = "https://github.com/buffedlizard55-lab/GEMSDOE.git"
FEAT_REF = "c0c06ac82178f26b94fce3397036ef8f12a2f3a0"
FEAT_PARTS = [f"data/bridge/gems-geodawn-numerical-features.tif.part-00{i}" for i in range(5)]
AUX_REPO = "https://github.com/buffedlizard55-lab/60GEMSDOE.git"
AUX_REF = "32024716f218d06a94e01464157392119c03cb15"
AUX = {
    "existing_faults.tif": "data/bridge/existing_faults.tif",
    "labels.tif": "data/labels.tif",
    "sample_submission.tif": "data/sample_submission.tif",
    "external/lidar_scarp_features_u8.tif": "data/external/lidar_scarp_features_u8.tif",
    "external/trace_segments_utm11.csv": "data/external/trace_segments_utm11.csv",
    "external/qfault_attributes.csv": "data/external/qfault_attributes.csv",
    "external/geodawn_dem_a2_100m.tif": "data/geodawn_dem_a2_100m.tif",
    "external/derived_sgmc_faults_100m_u8.tif": "data/external/derived_sgmc_faults_100m_u8.tif",
}


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True)


def blob(repo_dir: Path, ref: str, path: str) -> bytes:
    return subprocess.run(["git", "cat-file", "blob", f"{ref}:{path}"], cwd=repo_dir, check=True,
                          capture_output=True).stdout


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "external").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        if not all((DATA / k).exists() and sha256(DATA / k) == PINS[k] for k in AUX):
            git("clone", "-q", "--filter=blob:none", "--no-checkout", AUX_REPO, str(td / "aux"))
            for dest, src in AUX.items():
                (DATA / dest).write_bytes(blob(td / "aux", AUX_REF, src))
        dest = DATA / "training_features.tif"
        if not dest.exists() or sha256(dest) != PINS["training_features.tif"]:
            git("clone", "-q", "--filter=blob:none", "--no-checkout", FEAT_REPO, str(td / "feat"))
            with open(dest, "wb") as f:
                for part in FEAT_PARTS:
                    f.write(blob(td / "feat", FEAT_REF, part))
    bad = 0
    for k, pin in PINS.items():
        got = sha256(DATA / k)
        ok = got == pin
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {k} {got}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
