#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from typing import Any


def action(
    action_id: str,
    action_type: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "action_type": action_type,
        "stage_id": "case_plan",
        "arguments": arguments,
        "expected_outcome": "验证受限 Case Plan Agent Loop",
    }


def main() -> int:
    request = json.loads(sys.stdin.read())
    turn = int(request["turn"])
    if turn == 1:
        payload = action(
            "ACT-READ",
            "read_artifact",
            {"path": "testcases/case_plan.json"},
        )
    elif turn == 2:
        content = request["observations"][-1]["result"]["content"]
        payload = action(
            "ACT-PROPOSE",
            "propose_artifacts",
            {
                "path": "testcases/case_plan.json",
                "content": json.loads(content),
            },
        )
    elif turn == 3:
        payload = action("ACT-VALIDATE", "run_stage_validation", {})
    else:
        payload = action("ACT-COMMIT", "commit_stage", {})
    print(
        json.dumps(
            {
                "action": payload,
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "total_tokens": 120,
                    "cost_usd": 0.001,
                },
                "runtime": {
                    "provider": "fixture-command",
                    "model": "fixture-model",
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

