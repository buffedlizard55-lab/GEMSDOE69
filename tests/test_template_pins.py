"""Byte-pin and grid-fact verification (run line by line; no network)."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "vendor" / "template66") not in sys.path:
    sys.path.append(str(ROOT / "vendor" / "template66"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_template_sha256_pins():
    pins = (ROOT / "vendor" / "template66" / "TEMPLATE_SHA256.txt").read_text().splitlines()
    for line in pins:
        digest, rel = line.split()
        p = ROOT / "vendor" / "template66" / rel
        assert p.exists(), rel
        assert sha256(p) == digest, f"pin drift: {rel}"


def test_bridge_hashes_match_gemsdoe32_manifest():
    man = json.loads((ROOT / "registry" / "data_manifest_gemsdoe32.json").read_text())
    want = {
        "labels.tif": ("labels", ROOT / "data" / "bridge" / "labels.tif"),
        "existing_faults.tif": ("existing_faults", ROOT / "data" / "bridge" / "existing_faults.tif"),
        "sample_submission.tif": ("sample_submission", ROOT / "data" / "bridge" / "sample_submission.tif"),
        "derived_sgmc_faults_100m_u8.tif": ("ext_derived_sgmc_faults_100m_u8",
                                            ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"),
    }
    by_id = {f["id"]: f["sha256"] for f in man["files"]}
    for name, (fid, path) in want.items():
        assert path.exists(), name
        assert sha256(path) == by_id[fid], f"bridge hash mismatch: {name}"


def test_grid_facts_match_official_constants():
    import rasterio
    from gems.constants import EPSG, SHAPE_HW
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as src:
        assert src.crs.to_epsg() == int(EPSG.split(":")[1])
        assert (src.height, src.width) == tuple(SHAPE_HW)
        assert tuple(src.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert src.count == 1
        assert src.dtypes[0] == "float32"


if __name__ == "__main__":
    test_template_sha256_pins()
    print("template pins OK")
    test_bridge_hashes_match_gemsdoe32_manifest()
    print("bridge hashes OK")
    test_grid_facts_match_official_constants()
    print("grid facts OK")
    print("ALL PIN TESTS PASSED")
