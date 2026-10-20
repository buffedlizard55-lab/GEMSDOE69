#!/usr/bin/env python3
"""Write docs/status.json from the single fail-closed publication policy."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from release_gate import evaluate  # noqa: E402


def main() -> int:
    decision = evaluate(ROOT)
    out = ROOT / "docs" / "status.json"
    out.write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(decision, indent=2))
    # A negative release decision is a valid, expected project state.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
