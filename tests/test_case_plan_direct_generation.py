from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from scripts.coverage_testcase_generator import build_direct_case_plan_rows  # noqa: E402
from scripts.refine_case_plan_semantics import refine  # noqa: E402


def structured_prd() -> dict:
    return {
        "modules": [
            {
                "module_name": "宣传内容管理",
                "features": [
                    {
                        "feature_name": "宣传内容编辑表单",
                        "page_name": "宣传内容编辑页",
                        "section_name": "基础信息",
                        "fields": [
                            {
                                "field_name": "promotion_slogan",
                                "display_name": "宣传口号",
                            }
                        ],
                        "rules": [],
                        "field_rules": [],
                    }
                ],
            }
        ]
    }


def coverage_matrix() -> dict:
    return {
        "entries": [
            {
                "coverage_id": "COV-001",
                "coverage_type": "display_rule",
                "title": "宣传口号换行展示",
                "page_name": "购买页",
                "section_name": "宣传区",
                "module_name": "购买页",
                "feature_name": "宣传区",
                "field_name": "promotion_slogan",
                "planned_assertions": ["宣传口号超过一行时在C端换行展示。"],
            }
        ]
    }


def plan(plan_id: str, testcase_id: str) -> dict:
    return {
        "case_plan_id": plan_id,
        "source_gate_ids": ["TG-001"],
        "source_example_ids": ["AE-001"],
        "source_responsibility_ids": [],
        "source_rule_ids": ["COV-001"],
        "source_coverage_ids": ["COV-001"],
        "generated_testcase_ids": [testcase_id],
        "page_name": "购买页",
        "section_name": "宣传区",
        "module_name": "购买页",
        "feature_name": "宣传区",
        "title": "约束判定：宣传口号换行展示",
        "verification_side": "B端写侧",
        "case_type": "save_block",
        "priority": "P0",
        "assertion": "不可保存",
        "validation_path": "product_acceptance",
        "should_generate_case": True,
    }


class CasePlanDirectGenerationTests(unittest.TestCase):
    def test_refine_corrects_display_semantics_and_merges_duplicates(self) -> None:
        gate = {
            "items": [
                {
                    "gate_id": "TG-001",
                    "classification": "field_constraint",
                }
            ]
        }
        examples = {"examples": [{"example_id": "AE-001"}]}
        payload = {
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "case_plans": [
                plan("CP-001", "DEMO-BUY-PROMO-C-AB-001"),
                plan("CP-002", "DEMO-BUY-PROMO-C-AB-002"),
            ],
        }

        refined_gate, refined_examples, refined_plan, summary = refine(
            structured_prd(), coverage_matrix(), gate, examples, payload
        )

        self.assertEqual(summary, {"before": 2, "after": 1, "merged": 1})
        self.assertEqual(refined_plan["generation_mode"], "case_plan_direct")
        self.assertEqual(refined_plan["case_plans"][0]["case_type"], "ui_display")
        self.assertEqual(refined_plan["case_plans"][0]["verification_side"], "C端读侧")
        self.assertEqual(
            refined_plan["case_plans"][0]["generated_testcase_ids"],
            ["DEMO-BUY-PROMO-C-FN-001"],
        )
        self.assertEqual(refined_gate["items"][0]["classification"], "product_behavior")
        self.assertEqual(refined_examples["examples"][0]["oracle_strength"], "display_only")

    def test_direct_generator_uses_one_plan_for_one_human_readable_case(self) -> None:
        payload = {
            "generation_mode": "case_plan_direct",
            "case_plans": [plan("CP-001", "DEMO-BUY-PROMO-C-FN-001")],
        }
        payload["case_plans"][0].update(
            {
                "case_type": "ui_display",
                "verification_side": "C端读侧",
                "assertion": "“宣传口号”超过一行时在C端换行展示。",
            }
        )

        rows = build_direct_case_plan_rows(structured_prd(), coverage_matrix(), payload)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["用例编号"], "DEMO-BUY-PROMO-C-FN-001")
        self.assertIn("“宣传口号”", rows[0]["用例标题"])
        self.assertIn("C端换行展示", rows[0]["预期结果"])
        self.assertNotIn("promotion_slogan", rows[0]["用例标题"])
        self.assertIn("来源 CasePlan：CP-001", rows[0]["备注"])

    def test_direct_generator_uses_acceptance_given_when_then_and_api_tags(self) -> None:
        payload = {
            "generation_mode": "case_plan_direct",
            "case_plans": [plan("CP-001", "DEMO-API-CREATE-API-DV-001")],
        }
        payload["case_plans"][0].update(
            {
                "page_name": "GraphQL 接口",
                "section_name": "创建请求",
                "title": "复用已有标签时保留历史成员",
                "verification_side": "GraphQL API 与数据层",
                "case_type": "data_persistence",
                "assertion": "标签 T 同时关联成员 A 和 B；历史成员 A 不丢失。",
            }
        )
        examples = {
            "examples": [
                {
                    "example_id": "AE-001",
                    "given": ["标签 T 已关联历史成员 A。"],
                    "when": ["调用创建接口新增成员 B。"],
                    "then": ["标签 T 同时关联成员 A 和 B。"],
                }
            ]
        }

        rows = build_direct_case_plan_rows(
            structured_prd(), coverage_matrix(), payload, examples
        )

        self.assertEqual(rows[0]["前置条件"], "标签 T 已关联历史成员 A。")
        self.assertIn("调用创建接口新增成员 B", rows[0]["测试步骤"])
        self.assertIn("同时关联成员 A 和 B", rows[0]["预期结果"])
        self.assertIn("历史成员 A 不丢失", rows[0]["预期结果"])
        self.assertIn("AI-API用例", rows[0]["标签"])
        self.assertNotIn("AI-UI用例", rows[0]["标签"])
        self.assertEqual(rows[0]["测试类型"], "数据校验")

    def test_direct_generator_keeps_explicit_case_plan_type(self) -> None:
        payload = {
            "generation_mode": "case_plan_direct",
            "case_plans": [plan("CP-001", "DEMO-WORKER-REVOKE-SERVER-BD-001")],
        }
        payload["case_plans"][0].update(
            {
                "title": "边界：now 为 0 时撤销记录可加入和排序",
                "verification_side": "服务端 Worker 状态层",
                "case_type": "field_constraint",
                "assertion": "加入后撤销集合包含该任务 ID；排序过程不抛出异常。",
            }
        )

        rows = build_direct_case_plan_rows(structured_prd(), coverage_matrix(), payload)

        self.assertEqual(rows[0]["测试类型"], "边界")
        self.assertEqual(rows[0]["用例编号"], "DEMO-WORKER-REVOKE-SERVER-BD-001")

    def test_direct_generator_uses_server_terminal_as_api_tag_fallback(self) -> None:
        payload = {
            "generation_mode": "case_plan_direct",
            "case_plans": [plan("CP-001", "DEMO-AUDIO-DECODE-SERVER-ST-001")],
        }
        payload["case_plans"][0].update(
            {
                "verification_side": "TTS 音频解码层",
                "case_type": "backend_job",
                "assertion": "严格解码器产生至少一个非静音音频样本。",
            }
        )

        rows = build_direct_case_plan_rows(structured_prd(), coverage_matrix(), payload)

        self.assertIn("AI-API用例", rows[0]["标签"])
        self.assertNotIn("AI-UI用例", rows[0]["标签"])

    def test_direct_generator_does_not_treat_api_list_as_ui(self) -> None:
        payload = {
            "generation_mode": "case_plan_direct",
            "case_plans": [plan("CP-001", "DEMO-STORE-LIST-API-ST-001")],
        }
        payload["case_plans"][0].update(
            {
                "verification_side": "APIStore 列表读取与序列化调用层",
                "case_type": "backend_job",
                "assertion": "列表对象由指定 Serializer 解码。",
            }
        )

        rows = build_direct_case_plan_rows(structured_prd(), coverage_matrix(), payload)

        self.assertIn("AI-API用例", rows[0]["标签"])
        self.assertNotIn("AI-UI用例", rows[0]["标签"])


if __name__ == "__main__":
    unittest.main()
