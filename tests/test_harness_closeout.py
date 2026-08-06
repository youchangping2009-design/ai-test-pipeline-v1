from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cleanup_derived_artifacts as cleanup  # noqa: E402
from run_harness_closeout import work_item_fingerprint  # noqa: E402


class HarnessCleanupCloseoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.item_root = (
            self.root
            / "assets"
            / "projects"
            / "DEMO"
            / "work_items"
            / "WI-001"
        )
        self.item_root.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _run_main(self, *arguments: str) -> int:
        argv = [
            "cleanup_derived_artifacts.py",
            "--project-code",
            "DEMO",
            "--work-item-id",
            "WI-001",
            *arguments,
        ]
        with patch.object(cleanup, "ROOT", self.root), patch.object(
            sys,
            "argv",
            argv,
        ):
            return cleanup.main()

    def test_cleanup_refuses_nonterminal_run(self) -> None:
        run_dir = (
            self.item_root / ".generation" / "runs" / "RUN-ACTIVE"
        )
        run_dir.mkdir(parents=True)
        (run_dir / "run_state.json").write_text(
            json.dumps({"status": "waiting_approval"}),
            encoding="utf-8",
        )
        approval_dir = run_dir / "approvals"
        approval_dir.mkdir()
        (approval_dir / "APPROVAL-1.json").write_text(
            json.dumps({"status": "pending"}),
            encoding="utf-8",
        )
        self.assertEqual(self._run_main(), 2)
        self.assertTrue(run_dir.exists())

    def test_cleanup_points_crashed_multi_role_to_recovery(self) -> None:
        run_dir = (
            self.item_root / ".generation" / "runs" / "RUN-ROLES-CRASH"
        )
        run_dir.mkdir(parents=True)
        (run_dir / "run_state.json").write_text(
            json.dumps({"mode": "multi_role", "status": "running"}),
            encoding="utf-8",
        )
        blockers = cleanup.harness_cleanup_blockers(self.item_root)
        self.assertTrue(
            any("recover-roles" in item for item in blockers)
        )

    def test_cleanup_refuses_unfinished_publish_transaction(self) -> None:
        run_dir = (
            self.item_root / ".generation" / "runs" / "RUN-RECOVERY"
        )
        run_dir.mkdir(parents=True)
        (run_dir / "run_state.json").write_text(
            json.dumps({"status": "cancelled"}),
            encoding="utf-8",
        )
        (run_dir / "publish_transaction.json").write_text(
            json.dumps({"status": "publishing"}),
            encoding="utf-8",
        )
        blockers = cleanup.harness_cleanup_blockers(self.item_root)
        self.assertTrue(any("必须先执行恢复" in item for item in blockers))
        self.assertEqual(self._run_main(), 2)
        self.assertTrue(run_dir.exists())

    def test_cleanup_refuses_unfinished_case_plan_transaction(self) -> None:
        run_dir = (
            self.item_root / ".generation" / "runs" / "RUN-CASE-PLAN"
        )
        run_dir.mkdir(parents=True)
        (run_dir / "run_state.json").write_text(
            json.dumps({"status": "completed"}),
            encoding="utf-8",
        )
        (run_dir / "case_plan_commit_transaction.json").write_text(
            json.dumps({"status": "committing"}),
            encoding="utf-8",
        )
        blockers = cleanup.harness_cleanup_blockers(self.item_root)
        self.assertTrue(
            any("recover-case-plan" in item for item in blockers)
        )
        self.assertEqual(self._run_main(), 2)
        self.assertTrue(run_dir.exists())

    def test_terminal_run_cleanup_archives_publish_backup(self) -> None:
        run_dir = (
            self.item_root / ".generation" / "runs" / "RUN-DONE"
        )
        backup = (
            run_dir / "publish_backup" / "testcases" / "testcases_main.md"
        )
        backup.parent.mkdir(parents=True)
        backup.write_text("old cases", encoding="utf-8")
        (run_dir / "run_state.json").write_text(
            json.dumps({"status": "completed"}),
            encoding="utf-8",
        )
        (run_dir / "publish_transaction.json").write_text(
            json.dumps({"status": "committed"}),
            encoding="utf-8",
        )
        self.assertEqual(self._run_main(), 0)
        self.assertFalse(
            (self.item_root / ".generation" / "runs").exists()
        )
        archived = (
            self.item_root
            / ".generation"
            / "backups"
            / "RUN-DONE"
            / "publish_backup"
            / "testcases"
            / "testcases_main.md"
        )
        self.assertEqual(archived.read_text(encoding="utf-8"), "old cases")
        self.assertTrue(
            (
                self.item_root
                / ".generation"
                / "backups"
                / "RUN-DONE"
                / "publish_transaction.json"
            ).is_file()
        )

    def test_closeout_fingerprint_excludes_generation_state_only(self) -> None:
        formal = self.item_root / "testcases" / "testcases_main.md"
        formal.parent.mkdir()
        formal.write_text("cases", encoding="utf-8")
        before = work_item_fingerprint(self.item_root)
        generated = self.item_root / ".generation" / "runs" / "RUN-1"
        generated.mkdir(parents=True)
        (generated / "events.jsonl").write_text("{}\n", encoding="utf-8")
        self.assertEqual(work_item_fingerprint(self.item_root), before)
        (self.item_root / ".DS_Store").write_bytes(b"finder metadata")
        self.assertEqual(work_item_fingerprint(self.item_root), before)
        formal.write_text("changed", encoding="utf-8")
        self.assertNotEqual(work_item_fingerprint(self.item_root), before)


if __name__ == "__main__":
    unittest.main()
