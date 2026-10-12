#!/usr/bin/env python3
"""Report local prerequisites for the GEMS corridor experiment; never downloads or writes rasters."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

INPUT_CANDIDATES = {
    "training_features": (
        "data/training_features.tif",
        "data/raw/training_features.tif",
    ),
    "labels": (
        "data/labels.tif",
        "data/raw/labels.tif",
    ),
    "existing_faults": (
        "data/existing_faults.tif",
        "data/raw/existing_faults.tif",
    ),
    "dem_links": (
        "data/1m_DEM_links.csv",
        "data/raw/1m_DEM_links.csv",
    ),
    "sample_submission": (
        "data/sample_submission.tif",
        "data/raw/sample_submission.tif",
    ),
}
HELPER_CANDIDATES = {
    # vendor/gems57 = byte-identical copy of the shared template 60GEMSDOE/src/gems57
    # (registry/template_pin.json), added when PR #5 merged the data-backed lane run.
    "holdout_evaluator": (
        "scripts/evaluate_holdout.py",
        "evaluate_holdout.py",
        "vendor/gems57/evaluate_holdout.py",
    ),
    "submission_writer": (
        "scripts/submission_writer.py",
        "submission_writer.py",
        "vendor/gems57/submission_writer.py",
    ),
}
MODULES = ("numpy", "rasterio", "osgeo", "scipy", "geopandas", "pytest")
PROJECT_TOOL_CANDIDATES = {
    "dti_metric": ("src/gems/metric.py",),
    "format_validator": ("src/gems/validate_submission.py",),
    "promotion_gate": ("src/gems/gate.py",),
    "status_script": ("scripts/status.py",),
}


def first_existing(root: Path, candidates: tuple[str, ...]) -> str | None:
    for relative in candidates:
        if (root / relative).is_file():
            return relative
    return None


def build_report(root: Path = ROOT) -> dict[str, Any]:
    inputs = {
        name: {
            "present": (found := first_existing(root, candidates)) is not None,
            "path": found,
            "checked_paths": list(candidates),
        }
        for name, candidates in INPUT_CANDIDATES.items()
    }
    helpers = {
        name: {
            "present": (found := first_existing(root, candidates)) is not None,
            "path": found,
            "checked_paths": list(candidates),
        }
        for name, candidates in HELPER_CANDIDATES.items()
    }
    project_tools = {
        name: {
            "present": (found := first_existing(root, candidates)) is not None,
            "path": found,
            "checked_paths": list(candidates),
        }
        for name, candidates in PROJECT_TOOL_CANDIDATES.items()
    }

    feature_caches = [
        relative
        for relative in (
            "data/cache",
            "data/features.zarr",
            "cache/features",
            "features.zarr",
        )
        if (root / relative).exists()
    ]
    registry_dirs = [
        relative
        for relative in ("registry", "data/prior_rasters", "prior_rasters")
        if (root / relative).is_dir()
    ]
    download_candidates = [
        "scripts/download_competition_data.sh",
        "scripts/prepare_data.py",
    ]
    downloads = {
        path: (root / path).is_file()
        for path in download_candidates
    }
    missing = [
        f"input:{name}" for name, item in inputs.items() if not item["present"]
    ] + [
        f"shared_tool:{name}" for name, item in helpers.items() if not item["present"]
    ]

    return {
        "repository_root": str(root),
        "python": sys.version.split()[0],
        "inputs": inputs,
        "shared_tools": helpers,
        "project_tools": project_tools,
        "feature_cache_locations": feature_caches,
        "registry_directories": registry_dirs,
        "referenced_data_scripts": downloads,
        "available_python_modules": {
            name: importlib.util.find_spec(name) is not None for name in MODULES
        },
        "nvidia_smi_available": shutil.which("nvidia-smi") is not None,
        "missing_prerequisites": missing,
        "status": "ready" if not missing else "blocked",
        "safety": "This audit only reads filesystem metadata; it does not fetch data or create a submission.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit with status 2 when a required competition input or shared tool is missing",
    )
    args = parser.parse_args()

    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and report["status"] != "ready":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
