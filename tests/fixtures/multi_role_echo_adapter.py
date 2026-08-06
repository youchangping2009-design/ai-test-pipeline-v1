#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


TARGETS = {
    "prd_structurer": "structured_prd/structured_prd.json",
    "case_generator": "testcases/testcases_main.md",
    "case_reviewer": "reviews/review_record.md",
    "asset_formatter": "feishu_ready.md",
}


def action(
    request: dict,
    action_type: str,
    arguments: dict,
) -> dict:
    return {
        "action_id": (
            f"{request['stage_id']}-turn-{request['turn']}-{action_type}"
        ),
        "action_type": action_type,
        "stage_id": request["stage_id"],
        "arguments": arguments,
        "expected_outcome": "echo current validated artifact",
    }


def main() -> int:
    request = json.load(sys.stdin)
    stage_id = request["stage_id"]
    turn = int(request["turn"])
    target = TARGETS[stage_id]
    if stage_id == "prd_structurer" and turn == 1:
        selected = action(
            request,
            "read_artifact",
            {"path": "structured_prd/structured_prd.md"},
        )
    elif stage_id == "prd_structurer" and turn == 2:
        selected = action(
            request,
            "read_artifact",
            {"path": "structured_prd/structured_prd.json"},
        )
    elif stage_id == "prd_structurer" and turn == 3:
        markdown = request["observations"][-2]["result"]["content"]
        json_content = request["observations"][-1]["result"]["content"]
        selected = action(
            request,
            "propose_artifacts",
            {
                "artifacts": {
                    "structured_prd/structured_prd.md": markdown,
                    "structured_prd/structured_prd.json": json_content,
                }
            },
        )
    elif stage_id == "prd_structurer" and turn == 4:
        selected = action(request, "run_stage_validation", {})
    elif stage_id == "prd_structurer":
        selected = action(request, "finish_stage", {})
    elif turn == 1:
        selected = action(request, "read_artifact", {"path": target})
    elif turn == 2:
        content = request["observations"][-1]["result"]["content"]
        selected = action(
            request,
            "propose_artifacts",
            {"artifacts": {target: content}},
        )
    elif turn == 3:
        selected = action(request, "run_stage_validation", {})
    else:
        selected = action(request, "finish_stage", {})
    print(
        json.dumps(
            {
                "action": selected,
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                    "cost_usd": 0.0001,
                },
                "runtime": {
                    "provider": "fixture-command",
                    "model": "multi-role-echo",
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
