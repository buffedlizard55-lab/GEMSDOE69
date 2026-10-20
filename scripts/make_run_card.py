#!/usr/bin/env python3
"""Compatibility entry point for the single fail-closed run card writer."""
import json
from release_gate import write_card

if __name__ == "__main__":
    print(json.dumps(write_card()["release_policy"], indent=2))
