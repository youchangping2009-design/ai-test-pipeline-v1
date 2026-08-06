#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    request = json.load(sys.stdin)
    run_manifest = request["run_manifest"]
    artifacts: dict[str, str] = {}
    for relative in run_manifest["cleanup_targets"]:
        path = ROOT / relative
        if path.is_file():
            artifacts[relative] = path.read_text(encoding="utf-8")
    print(
        json.dumps(
            {
                "bundle": {
                    "cleanup_targets": run_manifest["cleanup_targets"],
                    "artifacts": artifacts,
                },
                "runtime": {
                    "provider": "fixture-command",
                    "model": "existing-replay",
                },
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
