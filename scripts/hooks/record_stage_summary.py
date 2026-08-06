#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def main() -> int:
    request = json.load(sys.stdin)
    print(
        json.dumps(
            {
                "recorded": True,
                "event": request.get("event"),
                "stage_id": request.get("stage_id"),
                "run_id": request.get("run_id"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
