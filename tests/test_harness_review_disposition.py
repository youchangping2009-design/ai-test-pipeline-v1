from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.audit import HarnessRunAuditor  # noqa: E402
from harness.orchestrator import DeterministicOrchestrator  # noqa: E402
from harness.review_disposition import ReviewDispositionService  # noqa: E402
from harness.stage_registry import StageSpec, _strict_gate_commands  # noqa: E402
from harness.state_store import HarnessStateError  # noqa: E402


ALL_LEVELS = frozenset({"S", "M", "L"})


def no_commands(
    _item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return []


def review_validator(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    marker = item_root / "review-ok"
    code = (
        "from pathlib import Path; import sys; "
        f"sys.exit(0 if Path({str(marker)!r}).exists() else 7)"
    )
    return [[sys.executable, "-c", code]]


class HarnessReviewDispositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.item_root = Path(self.temporary.name) / "work_item"
        (self.item_root / "code_reviews").mkdir(parents=True)
        (self.item_root / "manifest.json").write_text(
            json.dumps(
                {
                    "project_code": "DEMO",
                    "work_item_id": "WI-001",
                    "work_item_level": "S",
                    "pipeline_policy": {"review_disposition_required": True},
                    "artifacts": {
                        "code_reviews": {
                            "scope": "code_reviews/code_review_scope.json"
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        self._write_scope()
        (self.item_root / "trace.txt").write_text("trace\n", encoding="utf-8")
        (self.item_root / "review.txt").write_text("review\n", encoding="utf-8")
        self.plan = [
            StageSpec("traceability", "validation", ALL_LEVELS, ("trace.txt",), no_commands),
            StageSpec("review", "validation", ALL_LEVELS, ("review.txt",), review_validator),
            StageSpec("strict_gate", "gate", ALL_LEVELS, ("manifest.json",), no_commands),
        ]
        self.orchestrator = DeterministicOrchestrator(
            self.item_root,
            "DEMO",
            "WI-001",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_scope(self, *, frontend: list[str] | None = None) -> None:
        payload = {
            "status": "awaiting_code_directories",
            "frontend_code_dirs": frontend or [],
            "backend_code_dirs": [],
            "next_action": "提供代码目录或明确声明本次无代码映证。",
            "updated_at": "2026-09-22T00:00:00Z",
        }
        (self.item_root / "code_reviews" / "code_review_scope.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def _start_to_traceability(self, run_id: str = "RUN-REVIEW-NA") -> None:
        with (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["traceability", "review", "strict_gate"],
            ),
        ):
            code, state = self.orchestrator.start(
                run_id=run_id,
                work_item_level="S",
                strict=True,
                stop_at="traceability",
            )
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "paused")

    def test_not_applicable_runs_review_validators_then_reaches_strict(self) -> None:
        self._start_to_traceability()
        service = ReviewDispositionService(self.item_root)
        _, receipt = service.declare_not_applicable(
            run_id="RUN-REVIEW-NA",
            declared_by="qa.owner",
            reason="本需求仅生成测试资产，未提供业务代码目录。",
        )
        self.assertEqual(receipt["disposition"], "not_applicable")

        with (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["traceability", "review", "strict_gate"],
            ),
        ):
            code, failed = self.orchestrator.resume(run_id="RUN-REVIEW-NA")
        self.assertEqual(code, 7)
        self.assertEqual(failed["stages"][1]["status"], "failed")

        (self.item_root / "review-ok").write_text("ok\n", encoding="utf-8")
        with (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["traceability", "review", "strict_gate"],
            ),
        ):
            code, completed = self.orchestrator.resume(run_id="RUN-REVIEW-NA")
        self.assertEqual(code, 0)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["stages"][1]["status"], "skipped")
        self.assertEqual(completed["stages"][1]["attempts"], 2)

        audit_code, report = HarnessRunAuditor(self.item_root).audit("RUN-REVIEW-NA")
        self.assertEqual(audit_code, 0, report["errors"])
        self.assertEqual(report["counts"]["review_dispositions"], 1)

    def test_declaration_is_idempotent_but_conflicts_are_rejected(self) -> None:
        self._start_to_traceability()
        service = ReviewDispositionService(self.item_root)
        _, first = service.declare_not_applicable(
            run_id="RUN-REVIEW-NA",
            declared_by="qa.owner",
            reason="无代码输入。",
        )
        _, repeated = service.declare_not_applicable(
            run_id="RUN-REVIEW-NA",
            declared_by="qa.owner",
            reason="无代码输入。",
        )
        self.assertEqual(first, repeated)
        with self.assertRaisesRegex(HarnessStateError, "声明内容冲突"):
            service.declare_not_applicable(
                run_id="RUN-REVIEW-NA",
                declared_by="another.owner",
                reason="无代码输入。",
            )

    def test_declaration_after_successful_review_reopens_and_reruns_review(self) -> None:
        self._start_to_traceability()
        (self.item_root / "review-ok").write_text("ok\n", encoding="utf-8")
        with (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["traceability", "review", "strict_gate"],
            ),
        ):
            code, reviewed = self.orchestrator.resume(
                run_id="RUN-REVIEW-NA",
                stop_at="review",
            )
        self.assertEqual(code, 0)
        self.assertEqual(reviewed["stages"][1]["status"], "succeeded")

        state, _ = ReviewDispositionService(self.item_root).declare_not_applicable(
            run_id="RUN-REVIEW-NA",
            declared_by="qa.owner",
            reason="无代码输入。",
        )
        self.assertEqual(state["stages"][1]["status"], "pending")
        self.assertEqual(state["stages"][2]["status"], "pending")

        with (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["traceability", "review", "strict_gate"],
            ),
        ):
            code, completed = self.orchestrator.resume(run_id="RUN-REVIEW-NA")
        self.assertEqual(code, 0)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["stages"][1]["status"], "skipped")
        self.assertEqual(completed["stages"][1]["attempts"], 2)

        audit_code, report = HarnessRunAuditor(self.item_root).audit("RUN-REVIEW-NA")
        self.assertEqual(audit_code, 0, report["errors"])

    def test_rejects_before_traceability_code_dirs_and_ci(self) -> None:
        service = ReviewDispositionService(self.item_root)
        with patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan):
            self.orchestrator.store.create(
                run_id="RUN-PENDING",
                project_code="DEMO",
                work_item_id="WI-001",
                work_item_level="S",
                strict=True,
                stop_at="traceability",
                stages=self.plan,
            )
        with self.assertRaisesRegex(HarnessStateError, "必须暂停"):
            service.declare_not_applicable(
                run_id="RUN-PENDING",
                declared_by="qa.owner",
                reason="无代码输入。",
            )

        self._start_to_traceability("RUN-HAS-CODE")
        self._write_scope(frontend=["frontend"])
        with self.assertRaisesRegex(HarnessStateError, "目录均为空"):
            service.declare_not_applicable(
                run_id="RUN-HAS-CODE",
                declared_by="qa.owner",
                reason="错误声明。",
            )

        self._write_scope()
        with patch.dict(os.environ, {"CI": "true"}):
            with self.assertRaisesRegex(HarnessStateError, "CI 环境不得"):
                service.declare_not_applicable(
                    run_id="RUN-HAS-CODE",
                    declared_by="ci-bot",
                    reason="自动跳过。",
                )

    def test_scope_drift_invalidates_disposition(self) -> None:
        self._start_to_traceability()
        service = ReviewDispositionService(self.item_root)
        service.declare_not_applicable(
            run_id="RUN-REVIEW-NA",
            declared_by="qa.owner",
            reason="无代码输入。",
        )
        self._write_scope(frontend=["frontend"])
        with self.assertRaisesRegex(HarnessStateError, "scope 已漂移"):
            service.validate("RUN-REVIEW-NA")

    def test_strict_gate_requires_code_review_or_valid_disposition(self) -> None:
        command_without_receipt = _strict_gate_commands(
            self.item_root,
            "DEMO",
            "WI-001",
            "S",
            True,
        )
        self.assertNotIn("--skip-code-reviews", command_without_receipt[-1])

        self._start_to_traceability()
        ReviewDispositionService(self.item_root).declare_not_applicable(
            run_id="RUN-REVIEW-NA",
            declared_by="qa.owner",
            reason="无代码输入。",
        )
        commands = _strict_gate_commands(
            self.item_root,
            "DEMO",
            "WI-001",
            "S",
            True,
        )
        self.assertEqual(len(commands), 2)
        self.assertIn("validate_review_disposition.py", commands[0][1])
        self.assertIn("--skip-code-reviews", commands[1])


if __name__ == "__main__":
    unittest.main()
