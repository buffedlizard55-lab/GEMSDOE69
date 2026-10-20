#!/usr/bin/env python3
"""Fetch every prior submission GeoTIFF listed in registry/prior_rasters.json.

Primary transport: Git smart HTTP (`git clone --depth=1 --filter=blob:none --no-checkout`
per repository + `git cat-file --batch`), which uses ZERO GitHub REST API calls
and never triggers `gh api` 5,000-req/hour rate limits across parallel agents.
Fallback transport: `gh api repos/<repo>/git/blobs/<sha>` for any dangling blob
no longer reachable from a branch tip. Every file is verified against its
git-blob SHA-1 (`blob <len>\\0<bytes>`). Fails closed on any mismatch.
"""
from __future__ import annotations

import base64
from collections import defaultdict
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry" / "prior_rasters.json"
OUT = Path(os.environ.get("GEMS_REGISTRY_DIR", ROOT / ".cache" / "registry"))


def git_blob_sha1(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()


def fetch_blob_rest(repo: str, sha: str) -> bytes:
    r = subprocess.run(
        ["gh", "api", f"repos/{repo}/git/blobs/{sha}", "--jq", ".content"],
        check=True, capture_output=True, text=True, timeout=120,
    )
    return base64.b64decode(r.stdout.strip())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = json.loads(REG.read_text())
    entries = doc["rasters"]
    ok = cached = fetched = 0
    errors: list[dict] = []

    missing_by_repo: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        sha = e["git_blob_sha"]
        dest = OUT / f"{sha}.tif"
        if dest.exists() and git_blob_sha1(dest.read_bytes()) == sha:
            cached += 1
            ok += 1
        else:
            missing_by_repo[e["aliases"][0]["repository"]].append(e)

    if missing_by_repo:
        with tempfile.TemporaryDirectory() as td:
            for repo, repo_entries in sorted(missing_by_repo.items()):
                rdir = Path(td) / repo.replace("/", "__")
                rc = subprocess.run(
                    ["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
                     f"https://github.com/{repo}.git", str(rdir)],
                    capture_output=True, timeout=180,
                )
                for e in repo_entries:
                    sha = e["git_blob_sha"]
                    dest = OUT / f"{sha}.tif"
                    data = None
                    if rc.returncode == 0:
                        cat = subprocess.run(
                            ["git", "cat-file", "blob", sha],
                            cwd=rdir, capture_output=True, timeout=60,
                        )
                        if cat.returncode == 0 and git_blob_sha1(cat.stdout) == sha:
                            data = cat.stdout
                    if data is None:
                        for alias in e["aliases"]:
                            try:
                                cand = fetch_blob_rest(alias["repository"], sha)
                                if git_blob_sha1(cand) == sha:
                                    data = cand
                                    break
                            except Exception as exc:
                                last = str(exc)
                    if data is None:
                        errors.append({"sha": sha, "error": "unreachable via git and REST"})
                        continue
                    dest.write_bytes(data)
                    fetched += 1
                    ok += 1

    print(f"registry: {ok}/{len(entries)} ok (cached={cached}, fetched={fetched}, errors={len(errors)})")
    if errors:
        print(json.dumps(errors[:5], indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
