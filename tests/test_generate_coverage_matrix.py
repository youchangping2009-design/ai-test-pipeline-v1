from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
COVERAGE_SCRIPTS = ROOT / "skills" / "coverage-planning" / "scripts"
if str(COVERAGE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(COVERAGE_SCRIPTS))

from scripts.generate_coverage_matrix import build_matrix  # noqa: E402
from validate_coverage_matrix import validate_semantics  # noqa: E402


class CoverageMatrixGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.structured_prd = {
            "project_info": {"project_code": "DEMO", "project_name": "Demo"},
            "requirement_info": {
                "requirement_title": "Typed matching",
                "explicit_rules": [
                    {
                        "rule_id": "REQ-001",
                        "rule_text": "false 是有效值，不得按空值丢弃。",
                        "rule_type": "data_rule",
                        "priority": "high",
                        "applies_to": "类型化匹配",
                    }
                ],
            },
            "pages": [],
            "modules": [
                {
                    "module_name": "会话筛选",
                    "features": [
                        {
                            "feature_name": "类型化匹配",
                            "page_name": "会话列表页",
                            "section_name": "高级筛选",
                            "fields": [
                                {
                                    "field_name": "filter_value",
                                    "display_name": "筛选值",
                                },
                                {
                                    "field_name": "result_count",
                                    "display_name": "返回数量",
                                    "editable": False,
                                    "min": 0,
                                }
                            ],
                            "rules": [
                                {
                                    "rule_id": "RULE-001",
                                    "name": "保留 false",
                                    "rule_type": "value_constraint",
                                    "field_name": "filter_value",
                                    "rule_text": "false 是有效值，不得按空值丢弃。",
                                }
                            ],
                        }
                    ],
                }
            ],
            "flows": [],
        }

    def test_feature_rules_enter_main_coverage(self) -> None:
        matrix = build_matrix(
            self.structured_prd,
            {"project_code": "DEMO", "work_item_id": "WI-001"},
        )

        entry = next(item for item in matrix["entries"] if item.get("rule_name") == "REQ-001")
        self.assertEqual(entry["source_origin"], "explicit_rule")
        self.assertEqual(entry["emit_mode"], "main_testcase")
        self.assertEqual(entry["planned_assertions"], ["false 是有效值，不得按空值丢弃。"])

    def test_explicit_rule_applies_to_maps_multi_feature_context(self) -> None:
        self.structured_prd["modules"][0]["features"].append(
            {
                "feature_name": "结果导出",
                "page_name": "会话列表页",
                "section_name": "导出区",
                "fields": [],
                "rules": [],
            }
        )

        matrix = build_matrix(
            self.structured_prd,
            {"project_code": "DEMO", "work_item_id": "WI-001"},
        )
        entry = next(item for item in matrix["entries"] if item.get("rule_name") == "REQ-001")

        self.assertEqual(entry["page_name"], "会话列表页")
        self.assertEqual(entry["section_name"], "高级筛选")
        self.assertEqual(entry["module_name"], "会话筛选")
        self.assertEqual(entry["feature_name"], "类型化匹配")

    def test_distinct_rules_for_same_feature_are_not_deduplicated(self) -> None:
        self.structured_prd["requirement_info"]["explicit_rules"].append(
            {
                "rule_id": "REQ-002",
                "rule_text": "数值 0 必须保留并参与筛选。",
                "rule_type": "data_rule",
                "priority": "high",
                "applies_to": "类型化匹配",
            }
        )

        matrix = build_matrix(
            self.structured_prd,
            {"project_code": "DEMO", "work_item_id": "WI-001"},
        )
        entries = [
            item
            for item in matrix["entries"]
            if item.get("rule_name") in {"REQ-001", "REQ-002"}
        ]

        self.assertEqual(len(entries), 2)
        self.assertEqual(
            {item["title"] for item in entries},
            {"false 是有效值，不得按空值丢弃。", "数值 0 必须保留并参与筛选。"},
        )

    def test_readonly_output_does_not_become_input_boundary(self) -> None:
        matrix = build_matrix(
            self.structured_prd,
            {"project_code": "DEMO", "work_item_id": "WI-001"},
        )

        boundaries = [
            item
            for item in matrix["entries"]
            if item["coverage_type"] == "value_boundary"
        ]
        self.assertEqual(boundaries, [])

    def test_confirmed_medium_rule_stays_main_but_pending_rule_is_audit(self) -> None:
        self.structured_prd["requirement_info"]["explicit_rules"].extend(
            [
                {
                    "rule_id": "REQ-002",
                    "rule_text": "列表数量与最终结果一致。",
                    "rule_type": "state_constraint",
                    "priority": "medium",
                },
                {
                    "rule_id": "REQ-003",
                    "rule_text": "具体性能阈值待确认。",
                    "rule_type": "coverage_constraint",
                    "priority": "medium",
                },
            ]
        )
        matrix = build_matrix(
            self.structured_prd,
            {"project_code": "DEMO", "work_item_id": "WI-001"},
        )
        by_rule = {item.get("rule_name"): item for item in matrix["entries"]}

        self.assertEqual(by_rule["REQ-002"]["emit_mode"], "main_testcase")
        self.assertEqual(by_rule["REQ-003"]["emit_mode"], "audit_item")

    def test_context_only_rule_never_enters_main_coverage(self) -> None:
        self.structured_prd["requirement_info"]["explicit_rules"][0]["source_scope"] = "context_only"
        matrix = build_matrix(
            self.structured_prd,
            {"project_code": "DEMO", "work_item_id": "WI-001"},
        )
        entry = next(item for item in matrix["entries"] if item.get("rule_name") == "REQ-001")
        self.assertEqual(entry["source_scope"], "context_only")
        self.assertEqual(entry["coverage_level"], "audit_only")
        self.assertEqual(entry["emit_mode"], "audit_item")

    def test_compound_rule_expands_atomic_assertions(self) -> None:
        rule = self.structured_prd["requirement_info"]["explicit_rules"][0]
        rule["atomic_assertions"] = [
            "空值在连接创建前被拒绝。",
            "driver 返回空连接时报告连接错误。",
        ]
        matrix = build_matrix(
            self.structured_prd,
            {"project_code": "DEMO", "work_item_id": "WI-001"},
        )
        entries = [item for item in matrix["entries"] if item.get("rule_name") == "REQ-001"]
        self.assertEqual(len(entries), 2)
        self.assertEqual([item["atomic_assertion_index"] for item in entries], [1, 2])
        self.assertEqual(entries[0]["planned_assertions"], ["空值在连接创建前被拒绝。"])
        self.assertEqual(entries[1]["planned_assertions"], ["driver 返回空连接时报告连接错误。"])

    def test_confirmed_atomic_assertions_do_not_inherit_unrelated_pending_note(self) -> None:
        rule = self.structured_prd["requirement_info"]["explicit_rules"][0]
        rule["rule_text"] = "无效或空值不得建立会话；具体错误文案待确认。"
        rule["atomic_assertions"] = [
            "无效值不得建立会话。",
            "空值不得建立会话。",
        ]

        matrix = build_matrix(
            self.structured_prd,
            {"project_code": "DEMO", "work_item_id": "WI-001"},
        )
        entries = [item for item in matrix["entries"] if item.get("rule_name") == "REQ-001"]

        self.assertEqual(len(entries), 2)
        self.assertTrue(all(item["emit_mode"] == "main_testcase" for item in entries))
        self.assertTrue(all(item["coverage_level"] == "business" for item in entries))

    def test_validator_rejects_context_only_main_coverage(self) -> None:
        matrix = build_matrix(
            self.structured_prd,
            {"project_code": "DEMO", "work_item_id": "WI-001"},
        )
        entry = next(item for item in matrix["entries"] if item.get("rule_name") == "REQ-001")
        entry["source_scope"] = "context_only"
        entry["coverage_level"] = "business"
        entry["emit_mode"] = "main_testcase"

        errors = validate_semantics(matrix)

        self.assertTrue(any("context_only 来源不得进入 main_testcase" in error for error in errors))

    def test_reasoning_risks_and_edges_remain_audit_only(self) -> None:
        reasoning = {
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "business_risks": [
                {"risk_id": "RISK-001", "risk_statement": "并发一致性尚未确认。"}
            ],
            "edge_cases": [
                {"edge_case_id": "EC-001", "scenario": "空对象语义尚未确认。"}
            ],
        }
        matrix = build_matrix(self.structured_prd, reasoning)
        audit_entries = [
            item for item in matrix["entries"] if item["source_origin"] == "ai_reasoning"
        ]

        self.assertEqual(len(audit_entries), 2)
        self.assertTrue(all(item["coverage_level"] == "audit_only" for item in audit_entries))
        self.assertTrue(all(item["emit_mode"] == "audit_item" for item in audit_entries))

    def test_cross_domain_risk_does_not_inject_historical_sample_terms(self) -> None:
        reasoning = {
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "business_risks": [
                {
                    "risk_id": "RISK-001",
                    "risk_statement": "排序和条数上限组合存在风险。",
                }
            ],
            "edge_cases": [],
        }
        matrix = build_matrix(self.structured_prd, reasoning)
        payload = str(matrix)

        for forbidden in ["banner", "瓷片", "金刚区", "小程序banner配置页"]:
            self.assertNotIn(forbidden, payload)


if __name__ == "__main__":
    unittest.main()
