from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.multi_role_runtime import MultiRoleAgentRuntime  # noqa: E402
from harness.model_gateway import CommandModelGateway  # noqa: E402
from harness.parallel_reviewer_runtime import ParallelReviewerRuntime  # noqa: E402


class SimulatedCrashGateway:
    def next_action(self, request):
        raise RuntimeError(
            "simulated multi-role process crash at "
            + str(request["stage_id"])
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--work-item-level", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--crash-at",
        choices=("first-role", "parallel-reviewer"),
        default="first-role",
    )
    args = parser.parse_args()
    item_root = (
        ROOT
        / "assets"
        / "projects"
        / args.project_code
        / "work_items"
        / args.work_item_id
    )
    gateway = (
        SimulatedCrashGateway()
        if args.crash_at == "first-role"
        else CommandModelGateway(
            (
                sys.executable,
                str(ROOT / "tests" / "fixtures" / "parallel_reviewer_adapter.py"),
            )
        )
    )
    runtime = MultiRoleAgentRuntime(
        item_root=item_root,
        project_code=args.project_code,
        work_item_id=args.work_item_id,
        work_item_level=args.work_item_level,
        gateway=gateway,
        parallel_reviewers=args.crash_at == "parallel-reviewer",
    )
    if args.crash_at == "parallel-reviewer":
        def crash_parallel_review():
            partial = (
                runtime.store.run_dir(args.run_id)
                / "parallel_review"
                / "evidence"
                / "actions"
            )
            partial.mkdir(parents=True, exist_ok=True)
            (partial / "in_flight.txt").write_text(
                "simulated in-flight reviewer evidence",
                encoding="utf-8",
            )
            raise RuntimeError(
                "simulated multi-role process crash at parallel-reviewer"
            )

        with patch.object(
            ParallelReviewerRuntime,
            "execute",
            side_effect=crash_parallel_review,
        ):
            runtime.run(run_id=args.run_id)
    else:
        runtime.run(run_id=args.run_id)
    raise AssertionError("simulated crash gateway unexpectedly returned")


if __name__ == "__main__":
    raise SystemExit(main())
