from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.score_oracle_delta import validate_and_score


class OracleDeltaScoringTests(unittest.TestCase):
    def test_scores_coverage_and_scope_separately(self) -> None:
        payload = {
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "oracle": {"source_url": "https://example.invalid/pr/1", "head_sha": "abc"},
            "assertions": [
                {"assertion_id": "OA-001", "summary": "行为一", "disposition": "covered", "testcase_ids": ["TC-001"]},
                {"assertion_id": "OA-002", "summary": "行为二", "disposition": "partial", "testcase_ids": ["TC-002"], "design_feedback_ids": ["DF-001"]},
                {"assertion_id": "OA-003", "summary": "行为三", "disposition": "missing", "testcase_ids": [], "design_feedback_ids": ["DF-002"]},
            ],
            "testcase_assessments": [
                {"testcase_id": "TC-001", "disposition": "direct_match"},
                {"testcase_id": "TC-002", "disposition": "requirement_regression"},
                {"testcase_id": "TC-003", "disposition": "context_overreach"},
            ],
        }
        result = validate_and_score(payload, {"TC-001", "TC-002", "TC-003"})
        self.assertEqual(result["oracle_coverage_rate"], 0.5)
        self.assertEqual(result["requirement_oracle_coverage_rate"], 0.5)
        self.assertIsNone(result["implementation_oracle_coverage_rate"])
        self.assertIsNone(result["risk_oracle_coverage_rate"])
        self.assertTrue(
            all(item["oracle_scope"] == "requirement" for item in result["assertions"])
        )
        self.assertEqual(result["testcase_relevance_rate"], 0.6667)
        self.assertEqual(result["assertion_disposition_counts"]["missing"], 1)

    def test_scores_requirement_implementation_and_risk_separately(self) -> None:
        payload = {
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "oracle": {"source_url": "https://example.invalid/pr/1", "head_sha": "abc"},
            "assertions": [
                {
                    "assertion_id": "OA-001",
                    "summary": "批准需求",
                    "oracle_scope": "requirement",
                    "disposition": "covered",
                    "testcase_ids": ["TC-001"],
                },
                {
                    "assertion_id": "OA-002",
                    "summary": "实现行为",
                    "oracle_scope": "implementation",
                    "disposition": "partial",
                    "testcase_ids": ["TC-001"],
                    "design_feedback_ids": ["DF-001"],
                },
                {
                    "assertion_id": "OA-003",
                    "summary": "风险路径",
                    "oracle_scope": "risk",
                    "disposition": "missing",
                    "testcase_ids": [],
                    "design_feedback_ids": ["DF-002"],
                },
            ],
            "testcase_assessments": [
                {"testcase_id": "TC-001", "disposition": "direct_match"},
            ],
        }
        result = validate_and_score(payload, {"TC-001"})
        self.assertEqual(result["oracle_coverage_rate"], 0.5)
        self.assertEqual(result["requirement_oracle_coverage_rate"], 1.0)
        self.assertEqual(result["implementation_oracle_coverage_rate"], 0.5)
        self.assertEqual(result["risk_oracle_coverage_rate"], 0.0)
        self.assertEqual(
            result["oracle_scope_metrics"]["implementation"]["assertion_count"],
            1,
        )

    def test_rejects_unknown_oracle_scope(self) -> None:
        payload = {
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "oracle": {"source_url": "https://example.invalid/pr/1", "head_sha": "abc"},
            "assertions": [
                {
                    "assertion_id": "OA-001",
                    "summary": "行为一",
                    "oracle_scope": "unknown",
                    "disposition": "covered",
                    "testcase_ids": ["TC-001"],
                }
            ],
            "testcase_assessments": [
                {"testcase_id": "TC-001", "disposition": "direct_match"}
            ],
        }
        with self.assertRaisesRegex(ValueError, "oracle_scope 非法"):
            validate_and_score(payload, {"TC-001"})

    def test_rejects_covered_assertion_without_testcase(self) -> None:
        payload = {
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "oracle": {"source_url": "https://example.invalid/pr/1", "head_sha": "abc"},
            "assertions": [{"assertion_id": "OA-001", "summary": "行为一", "disposition": "covered", "testcase_ids": []}],
            "testcase_assessments": [{"testcase_id": "TC-001", "disposition": "direct_match"}],
        }
        with self.assertRaisesRegex(ValueError, "没有 testcase_ids"):
            validate_and_score(payload, {"TC-001"})

    def test_requires_every_frozen_testcase_to_be_classified(self) -> None:
        payload = {
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "oracle": {"source_url": "https://example.invalid/pr/1", "head_sha": "abc"},
            "assertions": [{"assertion_id": "OA-001", "summary": "行为一", "disposition": "covered", "testcase_ids": ["TC-001"]}],
            "testcase_assessments": [{"testcase_id": "TC-001", "disposition": "direct_match"}],
        }
        with self.assertRaisesRegex(ValueError, "未完成 oracle 范围判定"):
            validate_and_score(payload, {"TC-001", "TC-002"})


if __name__ == "__main__":
    unittest.main()
