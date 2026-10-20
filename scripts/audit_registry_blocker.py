#!/usr/bin/env python3
"""Reproduce one decisive literal registry failure, without a new experiment.

A single verified counterexample suffices to STOP, not to clear uniqueness.
No claim of a fresh exhaustive registry scan is made. The full source census and
all-prior comparison remain necessary for any hypothetical passing artifact.
Uses the pinned template's exact dot_overlap and surface_rho, not a private fork.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor' / 'template66'))

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from gems57.uniqueness import dot_overlap, surface_rho


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_grid(path, reference):
    with rasterio.open(path) as src:
        if (src.count != 1 or src.shape != reference['shape']
                or src.crs != reference['crs'] or src.transform != reference['transform']):
            raise ValueError(f'Grid mismatch: {path}')
        return src.read(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry-file', type=Path, default=ROOT / '.cache/review20261020/universal-registry.tif')
    parser.add_argument('--h33-file', type=Path, default=ROOT / '.cache/review20261020/h33-zeros.tif')
    args = parser.parse_args(argv)
    candidate = json.loads((ROOT / 'evidence/e3_receipt.json').read_text())['raster']['zeros']
    path = ROOT / candidate['path']
    if digest(path) != candidate['sha256']:
        raise ValueError('Candidate receipt SHA mismatch')
    registry = json.loads((ROOT / 'registry/registry_index_69.json').read_text())
    entry = next(r for r in registry['rasters'] if r['blob'] == '374c88b1da2b803e2ed160de467fd71ae114010d')
    if digest(args.registry_file) != entry['sha256']:
        raise ValueError('Registry SHA mismatch')
    with rasterio.open(ROOT / 'data/bridge/sample_submission.tif') as src:
        reference = dict(shape=src.shape, crs=src.crs, transform=src.transform)
        fp = np.isfinite(src.read(1))
    with rasterio.open(ROOT / 'data/bridge/existing_faults.tif') as src:
        cat = src.read(1) > 0
    mine = read_grid(path, reference)
    theirs = read_grid(args.registry_file, reference)
    support = np.isfinite(theirs) & (theirs > 0)
    dots = np.isfinite(mine) & (mine > 0)
    forward = dot_overlap(np.where(fp, mine, 0), np.where(fp, theirs, 0))
    rho = surface_rho(mine, theirs, fp)['spearman_full_footprint']
    rho = float(rho) if np.isfinite(rho) else None
    report = dict(
        evidence_class='REGISTRY-MEASUREMENT', checked_utc=datetime.now(timezone.utc).isoformat(),
        candidate_file=candidate['path'], candidate_sha256=digest(path), candidate_dots=int(dots.sum()),
        registry_source=entry['sources'][0], registry_blob_sha1=entry['blob'],
        registry_sha256=entry['sha256'], registry_bytes=args.registry_file.stat().st_size,
        registry_download=f"https://api.github.com/repos/buffedlizard55-lab/17GEMSDOE/git/blobs/{entry['blob']}",
        footprint_pixels=int(fp.sum()), registry_positive_footprint_pixels=int((fp & support).sum()),
        registry_covers_entire_footprint=bool(support[fp].all()),
        full_footprint_spearman=rho, candidate_dots_within_3px=forward,
        exact_bytes_equal=digest(path) == digest(args.registry_file),
        footprint_pixel_agreement=float((mine[fp] == theirs[fp]).mean()),
        literal_gate=dict(rho_ok=rho is not None and abs(rho) <= .90, overlap_ok=forward <= .70),
        stop_required=forward > .70 or (rho is not None and abs(rho) > .90),
        compared_this_review=1, registry_index_entries=registry['n_unique_grid_rasters'],
        exhaustive_scan=False,
        conclusion='One pinned universal-support registry raster is a decisive duplicate-and-stop counterexample. With the inherited positive-finite support definition, every nonempty in-footprint field has overlap 1 with this raster. This is a protocol/representation conflict, not proof of identical geological proposals.',
        surface_phase='No new surface or placement generated after the stop. Archived surface receipts are quarantined. Universal-support certificate applies to every nonempty in-footprint surface as well as dots.',
    )
    (ROOT / 'evidence/registry-blocker.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')

    local = []
    for prior in sorted((ROOT / 'submissions').glob('*.tif')):
        if prior == path or prior.name == path.name.replace('-zeros.tif', '-nan.tif'):
            continue
        arr = read_grid(prior, reference)
        local.append(dict(path=str(prior.relative_to(ROOT)), sha256=digest(prior),
            exact_bytes_equal=digest(prior) == candidate['sha256'],
            exact_footprint_pixels_equal=bool(np.array_equal(mine[fp], arr[fp])),
            footprint_pixel_agreement=float((mine[fp] == arr[fp]).mean()),
            dots_within_3px=dot_overlap(np.where(fp, mine, 0), np.where(fp, arr, 0))))
    (ROOT / 'evidence/local-prior-audit.json').write_text(json.dumps(dict(
        evidence_class='REGISTRY-MEASUREMENT', candidate_sha256=candidate['sha256'],
        scope='All other local archived TIFFs, excluding this emission and its NaN twin. No other file was generated.',
        n_files_compared=len(local),
        max_dot_overlap_3px=max(row['dots_within_3px'] for row in local),
        literal_overlap_failure=any(row['dots_within_3px'] > .70 for row in local),
        conclusion='Independent sparse local-prior failures also block the archived candidate; excluding the universal-support prior would not clear it.',
        rows=local), indent=2, allow_nan=False) + '\n')

    expected = 'c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9'
    if args.h33_file.exists():
        if digest(args.h33_file) != expected:
            raise ValueError('H33 pinned SHA mismatch')
        champ = read_grid(args.h33_file, reference)
        cdots = fp & np.isfinite(champ) & (champ > 0)
        distances = distance_transform_edt(~cat)[cdots]
        anatomy = dict(evidence_class='RASTER-MEASUREMENT', checked_utc=report['checked_utc'],
            source='https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif',
            sha256=expected, dots=int(cdots.sum()), values=sorted(map(float, np.unique(champ[fp]))),
            catalogue_collision_pixels=int((cdots & cat).sum()), nearest_catalogue_m=float(distances.min() * 100),
            median_catalogue_distance_m=float(np.median(distances) * 100), within_300m_fraction=float((distances <= 3).mean()),
            candidate_dot_overlap_3px=dot_overlap(np.where(fp, mine, 0), np.where(fp, champ, 0)),
            reported_dti=dict(value=.2778, evidence_class='USER-REPORTED-NOT-ORGANIZER-CONFIRMED',
                organizer_submission_receipt=None),
            known_fault_mask_caveat='DrivenData Staff states known USGS/INGENIOUS pixels are excluded from initial/final scoring; zero on-catalogue dots alone is not a scoring advantage. https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2',
            interpretation='Sparse off-catalogue dots are consistent with a precision/coverage tradeoff under max-kernel DTI. Their layout alone cannot prove why a hidden-label score was achieved or that another candidate beats it.')
        (ROOT / 'evidence/h33-audit-2026-10-20.json').write_text(json.dumps(anatomy, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
