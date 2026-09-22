#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from harness.review_disposition import ReviewDispositionService  # noqa: E402
from harness.state_store import HarnessStateError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 Harness Review disposition")
    parser.add_argument("--item-root", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        receipt = ReviewDispositionService(Path(args.item_root).resolve()).validate(args.run_id)
    except (HarnessStateError, ValueError) as exc:
        print(f"Review disposition validation failed: {exc}")
        return 1
    print(
        "Review disposition validated: "
        f"{receipt['disposition']} by {receipt['declared_by']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
