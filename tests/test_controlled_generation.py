from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.generation_workspace import (  # noqa: E402
    ControlledGenerationError,
    ControlledGenerationWorkspace,
    aggregate_hash,
    file_hash,
)
from harness.audit import HarnessRunAuditor  # noqa: E402
from harness.controlled_generation import ControlledGenerationService  # noqa: E402
from harness.stage_registry import StageSpec  # noqa: E402
from harness.state_store import StateStore, atomic_write_json  # noqa: E402


class ControlledGenerationWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.item_root = root / "work_item"
        self.run_dir = self.item_root / ".generation" / "runs" / "RUN-GEN"
        self.item_root.mkdir(parents=True)
        atomic_write_json(
            self.item_root / "manifest.json",
            {
                "project_code": "DEMO",
                "work_item_id": "WI-001",
                "work_item_level": "S",
            },
        )
        (self.item_root / "inputs").mkdir()
        (self.item_root / "inputs" / "prd.md").write_text(
            "raw input\n",
            encoding="utf-8",
        )
        self.workspace = ControlledGenerationWorkspace(
            item_root=self.item_root,
            run_dir=self.run_dir,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="S",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _seed_candidate(
        self,
        files: dict[str, tuple[str | None, str]],
    ) -> dict:
        records = []
        for relative, (formal_content, candidate_content) in files.items():
            target = self.item_root / relative
            if formal_content is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(formal_content, encoding="utf-8")
            staged = self.workspace.staging_root / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(candidate_content, encoding="utf-8")
            records.append(
                {
                    "path": relative,
                    "sha256": file_hash(staged),
                    "size_bytes": staged.stat().st_size,
                    "expected_target_hash": file_hash(target),
                }
            )
        candidate = {
            "schema_version": "1.0.0",
            "run_id": "RUN-GEN",
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "work_item_level": "S",
            "provider": "existing",
            "created_at": "2026-08-05T00:00:00+00:00",
            "bundle_hash": "a" * 64,
            "candidate_hash": aggregate_hash(
                [(entry["path"], entry["sha256"]) for entry in records]
            ),
            "expected_target_hash": aggregate_hash(
                [
                    (entry["path"], entry["expected_target_hash"])
                    for entry in records
                ]
            ),
            "expected_upstream_fingerprint": (
                self.workspace.upstream_fingerprint()
            ),
            "files": records,
            "validation": {
                "passed": True,
                "exit_code": 0,
                "log_path": "validation.log",
            },
        }
        atomic_write_json(self.workspace.candidate_manifest_path, candidate)
        return candidate

    def test_bundle_path_traversal_is_rejected(self) -> None:
        prefix = "assets/projects/DEMO/work_items/WI-001/"
        required = {
            prefix + "inputs/requirement_summary.md": "summary",
            prefix + "inputs/source_manifest.json": "{}",
            prefix + "evidence/evidence_inventory.json": "{}",
            prefix + "structured_prd/structured_prd.json": "{}",
            prefix + "traceability/traceability_matrix.json": "{}",
            prefix + "acceptance/testability_gate.json": "{}",
            prefix + "testcases/case_plan.json": "{}",
            prefix + "testcases/testcases_main.md": "cases",
            prefix + "reviews/review_record.md": "review",
        }
        bundle = {
            "cleanup_targets": list(required),
            "artifacts": {
                **required,
                prefix + "../OTHER/testcases/testcases_main.md": "escape",
            },
        }
        with self.assertRaises(ControlledGenerationError):
            self.workspace._validate_bundle_paths(bundle)

    def test_target_drift_rejects_candidate(self) -> None:
        self._seed_candidate(
            {"structured_prd/structured_prd.json": ("old", "new")}
        )
        (
            self.item_root / "structured_prd" / "structured_prd.json"
        ).write_text("drift", encoding="utf-8")
        with self.assertRaises(ControlledGenerationError):
            self.workspace.verify_candidate()

    def test_publish_commits_all_candidate_files(self) -> None:
        self._seed_candidate(
            {
                "structured_prd/structured_prd.json": ("old-prd", "new-prd"),
                "testcases/testcases_main.md": ("old-cases", "new-cases"),
            }
        )
        transaction = self.workspace.publish(
            formal_validator=lambda: (True, "strict passed"),
        )
        self.assertEqual(transaction["status"], "committed")
        self.assertEqual(
            (
                self.item_root / "structured_prd" / "structured_prd.json"
            ).read_text(encoding="utf-8"),
            "new-prd",
        )
        self.assertEqual(
            (
                self.item_root / "testcases" / "testcases_main.md"
            ).read_text(encoding="utf-8"),
            "new-cases",
        )

    def test_publish_failure_rolls_back_applied_files(self) -> None:
        self._seed_candidate(
            {
                "structured_prd/structured_prd.json": ("old-prd", "new-prd"),
                "testcases/testcases_main.md": ("old-cases", "new-cases"),
            }
        )
        calls = 0

        def fail_second_replace(source, target) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated publish interruption")
            os.replace(source, target)

        with self.assertRaises(OSError):
            self.workspace.publish(
                formal_validator=lambda: (True, "unused"),
                replace_func=fail_second_replace,
            )
        self.assertEqual(
            (
                self.item_root / "structured_prd" / "structured_prd.json"
            ).read_text(encoding="utf-8"),
            "old-prd",
        )
        self.assertEqual(
            (
                self.item_root / "testcases" / "testcases_main.md"
            ).read_text(encoding="utf-8"),
            "old-cases",
        )
        transaction = json.loads(
            self.workspace.transaction_path.read_text(encoding="utf-8")
        )
        self.assertEqual(transaction["status"], "rolled_back")
        self.assertFalse(
            list(self.item_root.rglob(".*.RUN-GEN.tmp"))
        )

    def test_formal_strict_failure_rolls_back(self) -> None:
        self._seed_candidate(
            {
                "testcases/testcases_main.md": ("old-cases", "new-cases"),
                "reviews/new_report.json": (None, "{}"),
            }
        )
        with self.assertRaises(ControlledGenerationError):
            self.workspace.publish(
                formal_validator=lambda: (False, "strict failed"),
            )
        self.assertEqual(
            (
                self.item_root / "testcases" / "testcases_main.md"
            ).read_text(encoding="utf-8"),
            "old-cases",
        )
        self.assertFalse(
            (self.item_root / "reviews" / "new_report.json").exists()
        )
        transaction = json.loads(
            self.workspace.transaction_path.read_text(encoding="utf-8")
        )
        self.assertEqual(transaction["status"], "rolled_back")

    def test_recover_unfinished_transaction_restores_backup(self) -> None:
        target = self.item_root / "testcases" / "testcases_main.md"
        target.parent.mkdir(parents=True)
        target.write_text("partially-published", encoding="utf-8")
        backup = (
            self.run_dir
            / "publish_backup"
            / "testcases"
            / "testcases_main.md"
        )
        backup.parent.mkdir(parents=True)
        backup.write_text("original", encoding="utf-8")
        transaction = {
            "schema_version": "1.0.0",
            "transaction_id": "RUN-GEN-publish",
            "run_id": "RUN-GEN",
            "status": "publishing",
            "created_at": "2026-08-05T00:00:00+00:00",
            "updated_at": "2026-08-05T00:00:00+00:00",
            "files": [
                {
                    "path": "testcases/testcases_main.md",
                    "existed": True,
                    "backup_path": str(backup),
                    "candidate_path": str(
                        self.workspace.staging_root
                        / "testcases"
                        / "testcases_main.md"
                    ),
                    "applied": True,
                }
            ],
            "error": None,
        }
        atomic_write_json(self.workspace.transaction_path, transaction)
        publish_temporary = target.with_name(
            ".testcases_main.md.RUN-GEN.tmp"
        )
        publish_temporary.write_text("orphan", encoding="utf-8")
        self.assertTrue(self.workspace.recover_unfinished())
        self.assertEqual(target.read_text(encoding="utf-8"), "original")
        self.assertFalse(publish_temporary.exists())
        recovered = json.loads(
            self.workspace.transaction_path.read_text(encoding="utf-8")
        )
        self.assertEqual(recovered["status"], "rolled_back")

    def test_recovery_refuses_partial_restore_when_backup_is_missing(self) -> None:
        first = self.item_root / "testcases" / "testcases_main.md"
        second = self.item_root / "reviews" / "review_record.md"
        first.parent.mkdir(parents=True)
        second.parent.mkdir(parents=True)
        first.write_text("partial-first", encoding="utf-8")
        second.write_text("partial-second", encoding="utf-8")
        first_backup = (
            self.run_dir
            / "publish_backup"
            / "testcases"
            / "testcases_main.md"
        )
        first_backup.parent.mkdir(parents=True)
        first_backup.write_text("original-first", encoding="utf-8")
        missing_backup = (
            self.run_dir
            / "publish_backup"
            / "reviews"
            / "review_record.md"
        )
        transaction = {
            "schema_version": "1.0.0",
            "transaction_id": "RUN-GEN-publish",
            "run_id": "RUN-GEN",
            "status": "publishing",
            "created_at": "2026-08-05T00:00:00+00:00",
            "updated_at": "2026-08-05T00:00:00+00:00",
            "files": [
                {
                    "path": "testcases/testcases_main.md",
                    "existed": True,
                    "backup_path": str(first_backup),
                    "candidate_path": "candidate-first",
                    "applied": True,
                },
                {
                    "path": "reviews/review_record.md",
                    "existed": True,
                    "backup_path": str(missing_backup),
                    "candidate_path": "candidate-second",
                    "applied": True,
                },
            ],
            "error": None,
        }
        atomic_write_json(self.workspace.transaction_path, transaction)
        with self.assertRaisesRegex(
            ControlledGenerationError,
            "缺少回滚备份",
        ):
            self.workspace.recover_unfinished()
        self.assertEqual(first.read_text(encoding="utf-8"), "partial-first")
        self.assertEqual(second.read_text(encoding="utf-8"), "partial-second")

    def test_service_approval_publishes_and_audits_completed_run(self) -> None:
        candidate = self._seed_candidate(
            {"testcases/testcases_main.md": ("old-cases", "new-cases")}
        )
        store = StateStore(self.item_root)
        stage = StageSpec(
            "full_pipeline",
            "generation",
            frozenset({"S", "M", "L"}),
            ("manifest.json",),
            lambda *_args: [],
        )
        state = store.create(
            run_id="RUN-GEN",
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="S",
            strict=True,
            stop_at="full_pipeline",
            stages=[stage],
            mode="generation",
        )
        state["status"] = "waiting_approval"
        state["stages"][0]["status"] = "waiting_approval"
        state["stages"][0]["attempts"] = 1
        store.save(state)
        approval = {
            "approval_id": "RUN-GEN-full-pipeline-publish",
            "run_id": "RUN-GEN",
            "stage_id": "full_pipeline",
            "status": "pending",
            "reason": "unit test publish",
            "options": ["approve_publish", "reject_publish"],
            "recommended_option": "approve_publish",
            "affected_truth_sources": [
                entry["path"] for entry in candidate["files"]
            ],
            "requested_action": "publish_generation",
            "expected_target_hash": candidate["expected_target_hash"],
            "expected_upstream_fingerprint": candidate[
                "expected_upstream_fingerprint"
            ],
            "candidate_hash": candidate["candidate_hash"],
            "requested_at": "2026-08-05T00:00:00+00:00",
            "resolved_at": None,
            "resolved_by": None,
            "resolution_note": None,
        }
        approval_path = (
            self.run_dir
            / "approvals"
            / f"{approval['approval_id']}.json"
        )
        atomic_write_json(approval_path, approval)
        store.append_event(
            state,
            "approval_requested",
            "full_pipeline",
            {
                "approval_id": approval["approval_id"],
                "requested_action": "publish_generation",
            },
        )
        service = ControlledGenerationService(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="S",
        )
        service._formal_strict_validator = lambda: (True, "strict passed")
        completed, resolved = service.approve(
            run_id="RUN-GEN",
            approval_id=approval["approval_id"],
            candidate_hash=candidate["candidate_hash"],
            approved_by="unit-test",
        )
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(resolved["status"], "approved")
        self.assertEqual(
            (
                self.item_root / "testcases" / "testcases_main.md"
            ).read_text(encoding="utf-8"),
            "new-cases",
        )
        audit_code, report = HarnessRunAuditor(self.item_root).audit("RUN-GEN")
        self.assertEqual(audit_code, 0)
        self.assertTrue(report["passed"])
        self.assertEqual(report["counts"]["publish_transactions"], 1)
        tampered = json.loads(approval_path.read_text(encoding="utf-8"))
        tampered["candidate_hash"] = "f" * 64
        atomic_write_json(approval_path, tampered)
        audit_code, report = HarnessRunAuditor(self.item_root).audit("RUN-GEN")
        self.assertEqual(audit_code, 1)
        self.assertTrue(
            any(
                "candidate_hash" in error
                for error in report["errors"]
            )
        )


if __name__ == "__main__":
    unittest.main()
