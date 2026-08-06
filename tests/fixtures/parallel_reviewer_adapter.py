#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import sys


ROLE_TARGETS = {
    "prd_structurer": "structured_prd/structured_prd.json",
    "case_generator": "testcases/testcases_main.md",
    "asset_formatter": "feishu_ready.md",
}
REVIEW_TARGETS = {
    "evidence": "traceability/coverage_first_traceability.json",
    "flow": "structured_prd/structured_prd.json",
    "testcase": "testcases/testcases_main.md",
}


def envelope(action):
    return {
        "action": action,
        "usage": {
            "input_tokens": 3,
            "output_tokens": 2,
            "total_tokens": 5,
            "cost_usd": 0.0001,
        },
        "runtime": {
            "provider": "fixture-command",
            "model": "parallel-reviewer-fixture",
        },
    }


def role_action(request, action_type, arguments):
    return {
        "action_id": "%s-%s-%s"
        % (request["stage_id"], request["turn"], action_type),
        "action_type": action_type,
        "stage_id": request["stage_id"],
        "arguments": arguments,
        "expected_outcome": "trusted fixture role action",
    }


def reviewer_action(request, action_type, arguments):
    return {
        "action_id": "%s-%s-%s"
        % (request["reviewer"], request["turn"], action_type),
        "action_type": action_type,
        "reviewer": request["reviewer"],
        "arguments": arguments,
        "expected_outcome": "trusted fixture reviewer action",
    }


def main():
    request = json.load(sys.stdin)
    turn = int(request["turn"])
    if request.get("mode") == "parallel_reviewer":
        reviewer = request["reviewer"]
        if turn == 1:
            time.sleep(0.05)
            selected = reviewer_action(
                request,
                "read_artifact",
                {"path": REVIEW_TARGETS[reviewer]},
            )
        elif turn == 2:
            selected = reviewer_action(
                request,
                "submit_findings",
                {
                    "findings": [
                        {
                            "finding_type": "%s_check" % reviewer,
                            "artifact_path": REVIEW_TARGETS[reviewer],
                            "location": "fixture",
                            "severity": "low",
                            "message": "%s fixture finding" % reviewer,
                            "suggestion": "人工复核 fixture 位置",
                            "trace_ids": ["PT083"],
                        }
                    ]
                },
            )
        else:
            selected = reviewer_action(request, "finish_review", {})
        print(json.dumps(envelope(selected), ensure_ascii=False))
        return 0

    stage_id = request["stage_id"]
    target = ROLE_TARGETS[stage_id]
    if stage_id == "prd_structurer" and turn == 1:
        selected = role_action(
            request,
            "read_artifact",
            {"path": "structured_prd/structured_prd.md"},
        )
    elif stage_id == "prd_structurer" and turn == 2:
        selected = role_action(
            request,
            "read_artifact",
            {"path": "structured_prd/structured_prd.json"},
        )
    elif stage_id == "prd_structurer" and turn == 3:
        selected = role_action(
            request,
            "propose_artifacts",
            {
                "artifacts": {
                    "structured_prd/structured_prd.md": request["observations"][-2][
                        "result"
                    ]["content"],
                    "structured_prd/structured_prd.json": request["observations"][-1][
                        "result"
                    ]["content"],
                }
            },
        )
    elif stage_id == "prd_structurer" and turn == 4:
        selected = role_action(request, "run_stage_validation", {})
    elif stage_id == "prd_structurer":
        selected = role_action(request, "finish_stage", {})
    elif turn == 1:
        selected = role_action(request, "read_artifact", {"path": target})
    elif turn == 2:
        selected = role_action(
            request,
            "propose_artifacts",
            {
                "artifacts": {
                    target: request["observations"][-1]["result"]["content"]
                }
            },
        )
    elif turn == 3:
        selected = role_action(request, "run_stage_validation", {})
    else:
        selected = role_action(request, "finish_stage", {})
    print(json.dumps(envelope(selected), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
