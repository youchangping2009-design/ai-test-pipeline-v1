from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.audit import HarnessRunAuditor  # noqa: E402
from harness.model_gateway import ModelGatewayError, ModelTurnResult  # noqa: E402
from harness.parallel_reviewer_runtime import ParallelReviewerRuntime  # noqa: E402
from harness.review_aggregator import (  # noqa: E402
    aggregate_review_bundle,
    canonicalize_finding,
)
from harness.role_workspace import MultiRoleArtifactWorkspace  # noqa: E402
from harness.telemetry import BudgetConfig, RunTelemetry  # noqa: E402


SOURCE_ITEM = ROOT / "tests" / "fixtures" / "runtime_work_item"


def reviewer_action(request, action_type, arguments):
    return {
        "action_id": "%s-%s-%s"
        % (request["reviewer"], request["turn"], action_type),
        "action_type": action_type,
        "reviewer": request["reviewer"],
        "arguments": arguments,
        "expected_outcome": "parallel reviewer unit test",
    }


class ReviewerGateway:
    targets = {
        "evidence": "traceability/coverage_first_traceability.json",
        "flow": "structured_prd/structured_prd.json",
        "testcase": "testcases/testcases_main.md",
    }

    def __init__(
        self,
        *,
        delay=0.05,
        fail_reviewer=None,
        illegal_reviewer=None,
        forbidden_path_reviewer=None,
        malformed_once=False,
        mutate=None,
    ):
        self.delay = delay
        self.fail_reviewer = fail_reviewer
        self.illegal_reviewer = illegal_reviewer
        self.forbidden_path_reviewer = forbidden_path_reviewer
        self.malformed_once = malformed_once
        self.mutate = mutate
        self.starts = {}
        self._lock = threading.Lock()
        self._mutated = False

    def next_action(self, request):
        reviewer = request["reviewer"]
        turn = int(request["turn"])
        if reviewer == self.fail_reviewer:
            raise ModelGatewayError("fixture reviewer failure")
        if turn == 1:
            with self._lock:
                self.starts[reviewer] = time.monotonic()
                should_mutate = self.mutate is not None and not self._mutated
                if should_mutate:
                    self._mutated = True
            time.sleep(self.delay)
            if should_mutate:
                self.mutate()
            if reviewer == self.illegal_reviewer:
                action = reviewer_action(request, "shell", {"command": "false"})
            else:
                path = (
                    "../manifest.json"
                    if reviewer == self.forbidden_path_reviewer
                    else self.targets[reviewer]
                )
                action = reviewer_action(request, "read_artifact", {"path": path})
        elif turn == 2:
            if self.malformed_once and reviewer == "testcase":
                findings = [{"severity": "high"}]
            else:
                findings = [
                    {
                        "finding_type": "%s_check" % reviewer,
                        "artifact_path": self.targets[reviewer],
                        "location": "fixture location",
                        "severity": "low",
                        "message": "%s finding" % reviewer,
                        "suggestion": "复核对应追溯关系",
                        "trace_ids": ["FIXTURE-RUNTIME-001", "CP-001"],
                    }
                ]
            action = reviewer_action(
                request,
                "submit_findings",
                {"findings": findings},
            )
        elif turn == 3 and self.malformed_once and reviewer == "testcase":
            action = reviewer_action(
                request,
                "submit_findings",
                {
                    "findings": [
                        {
                            "finding_type": "testcase_check",
                            "artifact_path": self.targets[reviewer],
                            "location": "fixture location",
                            "severity": "low",
                            "message": "testcase repaired finding",
                            "suggestion": "复核对应追溯关系",
                            "trace_ids": ["FIXTURE-RUNTIME-001"],
                        }
                    ]
                },
            )
        else:
            action = reviewer_action(request, "finish_review", {})
        return ModelTurnResult(
            action=action,
            usage={
                "input_tokens": 2,
                "output_tokens": 1,
                "total_tokens": 3,
                "cost_usd": 0.0001,
            },
            runtime={"provider": "unit-test", "model": "parallel-reviewer"},
        )


class ParallelReviewerRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.item_root = Path(self.temporary.name) / "work_item"
        shutil.copytree(
            SOURCE_ITEM,
            self.item_root,
            ignore=lambda _directory, names: {".generation"}.intersection(names),
        )
        self.run_dir = (
            self.item_root / ".generation" / "runs" / "RUN-PARALLEL-TEST"
        )
        self.workspace = MultiRoleArtifactWorkspace(
            item_root=self.item_root,
            run_dir=self.run_dir,
            project_code="FIXTURE",
            work_item_id="FIXTURE-RUNTIME-001",
            work_item_level="M",
            base_bundle=self._base_bundle(),
        )

    def tearDown(self):
        self.temporary.cleanup()

    def _base_bundle(self):
        prefix = "assets/projects/FIXTURE/work_items/FIXTURE-RUNTIME-001/"
        artifacts = {}
        allowed_prefixes = (
            "analysis/",
            "evidence/",
            "image_evidence/",
            "structured_prd/",
            "coverage/",
            "acceptance/",
            "design/",
            "testcases/",
            "traceability/",
            "reviews/",
        )
        allowed_files = {
            "inputs/requirement_summary.md",
            "inputs/source_manifest.json",
            "feishu_ready.md",
        }
        for path in sorted(
            candidate for candidate in self.item_root.rglob("*") if candidate.is_file()
        ):
            relative = path.relative_to(self.item_root).as_posix()
            if relative.startswith(".generation/"):
                continue
            if relative not in allowed_files and not relative.startswith(
                allowed_prefixes
            ):
                continue
            artifacts[prefix + relative] = path.read_text(encoding="utf-8")
        return {
            "provider": "existing",
            "work_item_level": "M",
            "cleanup_targets": list(artifacts),
            "artifacts": artifacts,
        }

    def _execute(
        self,
        gateway,
        *,
        budget=None,
        timeout=2,
        max_turns=4,
        max_repairs=2,
    ):
        events = []
        telemetry = RunTelemetry(
            run_id="RUN-PARALLEL-TEST",
            run_dir=self.run_dir,
            budget=budget or BudgetConfig(max_model_calls=48, require_usage=True),
        )
        telemetry.write()
        runtime = ParallelReviewerRuntime(
            run_id="RUN-PARALLEL-TEST",
            run_dir=self.run_dir,
            gateway=gateway,
            workspace=self.workspace,
            telemetry=telemetry,
            append_event=lambda event_type, payload: events.append(
                {"event_type": event_type, "payload": payload}
            ),
            max_turns_per_reviewer=max_turns,
            max_repairs_per_reviewer=max_repairs,
            reviewer_timeout_seconds=timeout,
        )
        return runtime.execute(), events

    def test_real_concurrency_and_three_of_three_barrier(self):
        gateway = ReviewerGateway(delay=0.15)
        started = time.monotonic()
        result, events = self._execute(gateway)
        elapsed = time.monotonic() - started
        self.assertTrue(result["succeeded"])
        self.assertEqual(result["runtime_state"]["barrier"]["succeeded"], 3)
        self.assertLess(max(gateway.starts.values()) - min(gateway.starts.values()), 0.1)
        self.assertLess(elapsed, 0.7)
        self.assertTrue((self.run_dir / "parallel_review" / "review_bundle.json").is_file())
        self.assertTrue(
            (
                self.workspace.staging_root
                / "reviews"
                / "review_record.md"
            ).is_file()
        )
        self.assertIn(
            "parallel_review_barrier_passed",
            [event["event_type"] for event in events],
        )

    def test_shared_call_budget_stops_without_bundle(self):
        result, _events = self._execute(
            ReviewerGateway(delay=0.01),
            budget=BudgetConfig(max_model_calls=2, require_usage=True),
        )
        self.assertFalse(result["succeeded"])
        self.assertFalse(
            (self.run_dir / "parallel_review" / "review_bundle.json").exists()
        )
        self.assertLess(result["runtime_state"]["barrier"]["succeeded"], 3)

    def test_failure_illegal_action_and_forbidden_path_stop_barrier(self):
        for gateway in (
            ReviewerGateway(fail_reviewer="flow"),
            ReviewerGateway(illegal_reviewer="evidence"),
            ReviewerGateway(forbidden_path_reviewer="testcase"),
        ):
            with self.subTest(gateway=gateway.__dict__):
                self.tearDown()
                self.setUp()
                result, _events = self._execute(gateway)
                self.assertFalse(result["succeeded"])
                self.assertFalse(
                    (self.run_dir / "parallel_review" / "review_bundle.json").exists()
                )

    def test_timeout_stops_barrier(self):
        result, _events = self._execute(
            ReviewerGateway(delay=1.2),
            timeout=1,
        )
        self.assertFalse(result["succeeded"])
        statuses = {
            reviewer["status"] for reviewer in result["runtime_state"]["reviewers"]
        }
        self.assertIn("timed_out", statuses)
        time.sleep(0.25)

    def test_findings_repair_succeeds_within_limit(self):
        result, _events = self._execute(
            ReviewerGateway(malformed_once=True),
        )
        self.assertTrue(result["succeeded"])
        testcase = next(
            reviewer
            for reviewer in result["runtime_state"]["reviewers"]
            if reviewer["reviewer"] == "testcase"
        )
        self.assertEqual(testcase["repair_rounds_used"], 1)

    def test_staging_drift_fails_before_aggregation(self):
        target = self.workspace.staging_root / "testcases" / "testcases_main.md"

        def mutate():
            target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")

        result, _events = self._execute(ReviewerGateway(mutate=mutate))
        self.assertFalse(result["succeeded"])
        self.assertFalse(
            (self.run_dir / "parallel_review" / "review_bundle.json").exists()
        )
        self.assertTrue(
            any(
                reviewer["error"] == "reviewer_staging_drift"
                for reviewer in result["runtime_state"]["reviewers"]
            )
        )

    def test_aggregation_is_order_independent_and_records_conflict(self):
        raw = {
            "finding_type": "coverage",
            "artifact_path": "testcases/testcases_main.md",
            "location": "  TC-001  ",
            "severity": "medium",
            "message": "缺少   边界断言",
            "suggestion": "补充边界值",
            "trace_ids": ["CP-001"],
        }
        evidence = canonicalize_finding("evidence", raw)
        testcase = canonicalize_finding("testcase", {**raw, "severity": "high"})
        first = aggregate_review_bundle(
            "RUN-X",
            {"evidence": [evidence], "flow": [], "testcase": [testcase]},
        )
        second = aggregate_review_bundle(
            "RUN-X",
            {"testcase": [testcase], "evidence": [evidence], "flow": []},
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first["findings"]), 1)
        self.assertEqual(len(first["conflicts"]), 1)
        self.assertEqual(first["findings"][0]["severity"], "high")

    def test_audit_detects_bundle_tampering(self):
        result, events = self._execute(ReviewerGateway())
        self.assertTrue(result["succeeded"])
        auditor = HarnessRunAuditor(self.item_root)
        errors = []
        checks = []
        counts = {
            "parallel_review_runtime_states": 0,
            "parallel_review_actions": 0,
            "parallel_review_findings": 0,
            "parallel_review_bundles": 0,
        }
        auditor._audit_parallel_review(
            self.run_dir,
            {"mode": "multi_role"},
            events,
            checks,
            errors,
            counts,
        )
        self.assertEqual(errors, [])
        bundle_path = self.run_dir / "parallel_review" / "review_bundle.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        bundle["findings"][0]["message"] = "tampered"
        bundle_path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        errors = []
        auditor._audit_parallel_review(
            self.run_dir,
            {"mode": "multi_role"},
            events,
            [],
            errors,
            {
                "parallel_review_runtime_states": 0,
                "parallel_review_actions": 0,
                "parallel_review_findings": 0,
                "parallel_review_bundles": 0,
            },
        )
        self.assertTrue(any("bundle hash" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
