from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.orchestrator import DeterministicOrchestrator  # noqa: E402
from harness.stage_registry import resolve_stage_plan  # noqa: E402
from scripts.validate_oracle_review import validate_oracle_review  # noqa: E402


class OracleReviewValidationTests(unittest.TestCase):
    def _copy_item(self, project: str, work_item: str) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        source = ROOT / "assets" / "projects" / project / "work_items" / work_item
        target = Path(temporary.name) / "work_item"
        shutil.copytree(source, target, ignore=shutil.ignore_patterns(".generation"))
        return temporary, target

    def test_validates_intact_blind_baseline(self) -> None:
        item_root = (
            ROOT
            / "assets"
            / "projects"
            / "OSS-BLIND-R3"
            / "work_items"
            / "DJANGO-21801"
        )
        result = validate_oracle_review(item_root)
        self.assertEqual(result["status"], "frozen_baseline_intact")
        self.assertEqual(result["freeze_mismatch_count"], 0)

    def test_allows_historical_freeze_after_all_feedback_is_applied(self) -> None:
        item_root = (
            ROOT
            / "assets"
            / "projects"
            / "OSS-BLIND"
            / "work_items"
            / "APPSMITH-42244"
        )
        result = validate_oracle_review(item_root)
        self.assertEqual(result["status"], "post_feedback_regeneration")
        self.assertGreater(result["freeze_mismatch_count"], 0)

    def test_rejects_freeze_drift_before_feedback_is_applied(self) -> None:
        temporary, item_root = self._copy_item("OSS-BLIND-R3", "CELERY-10668")
        self.addCleanup(temporary.cleanup)
        feedback_path = item_root / "design" / "design_feedback.json"
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        feedback["feedback_items"][0]["status"] = "accepted"
        feedback_path.write_text(
            json.dumps(feedback, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        testcase_path = item_root / "testcases" / "testcases_main.md"
        testcase_path.write_text(
            testcase_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "冻结资产漂移"):
            validate_oracle_review(item_root)

    def test_rejects_stale_oracle_score(self) -> None:
        temporary, item_root = self._copy_item("OSS-BLIND-R3", "DJANGO-21801")
        self.addCleanup(temporary.cleanup)
        score_path = item_root / "reviews" / "oracle_delta_score.json"
        score = json.loads(score_path.read_text(encoding="utf-8"))
        score["requirement_oracle_coverage_rate"] = 0.0
        score_path.write_text(
            json.dumps(score, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "重新计算结果不一致"):
            validate_oracle_review(item_root)

    def test_review_stage_runs_deterministic_validators_and_tracks_oracle_files(self) -> None:
        item_root = (
            ROOT
            / "assets"
            / "projects"
            / "OSS-BLIND-R3"
            / "work_items"
            / "DJANGO-21801"
        )
        review_stage = next(
            stage
            for stage in resolve_stage_plan("M")
            if stage.stage_id == "review"
        )
        commands = review_stage.commands(
            item_root,
            "OSS-BLIND-R3",
            "DJANGO-21801",
            "M",
            True,
        )
        self.assertEqual(len(commands), 4)
        self.assertTrue(commands[0][1].endswith("validate_design_feedback.py"))
        self.assertTrue(commands[1][1].endswith("validate_feedback_application.py"))
        self.assertTrue(commands[2][1].endswith("validate_feedback_action_journal.py"))
        self.assertTrue(commands[3][1].endswith("validate_oracle_review.py"))

        temporary, copied_root = self._copy_item("OSS-BLIND-R3", "DJANGO-21801")
        self.addCleanup(temporary.cleanup)
        orchestrator = DeterministicOrchestrator(
            copied_root,
            "OSS-BLIND-R3",
            "DJANGO-21801",
        )
        before = orchestrator._stage_fingerprint({}, review_stage)
        score_path = copied_root / "reviews" / "oracle_delta_score.json"
        score_path.write_text(
            score_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        after = orchestrator._stage_fingerprint({}, review_stage)
        self.assertNotEqual(before, after)

        before_journal = after
        action_dir = (
            copied_root / ".generation" / "feedback_applications" / "actions"
        )
        action_dir.mkdir(parents=True)
        (action_dir / "ACT-001.intent.json").write_text("{}\n", encoding="utf-8")
        after_journal = orchestrator._stage_fingerprint({}, review_stage)
        self.assertNotEqual(before_journal, after_journal)

    def test_review_stage_validates_feedback_application_when_present(self) -> None:
        item_root = (
            ROOT
            / "assets"
            / "projects"
            / "OSS-BLIND-R3"
            / "work_items"
            / "CELERY-10668"
        )
        review_stage = next(
            stage
            for stage in resolve_stage_plan("M")
            if stage.stage_id == "review"
        )
        commands = review_stage.commands(
            item_root,
            "OSS-BLIND-R3",
            "CELERY-10668",
            "M",
            True,
        )
        self.assertEqual(len(commands), 4)
        self.assertTrue(commands[1][1].endswith("validate_feedback_application.py"))
        self.assertTrue(commands[2][1].endswith("validate_feedback_action_journal.py"))


if __name__ == "__main__":
    unittest.main()
