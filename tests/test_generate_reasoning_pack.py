from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_reasoning_pack import (  # noqa: E402
    build_ambiguities,
    build_business_risks,
    build_coverage_candidates,
    build_edge_cases,
    build_implicit_rules,
    build_test_dimensions,
    parse_requirement_summary,
)


class TextRequirementReasoningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.requirement_doc = {
            "source_path": "inputs/requirement_summary.md",
            "sections": {
                "6. 面向测试的验收关注点": [
                    "值为 0 和 false 时必须保持原类型。",
                    "既有合法配置不应因本次修改回退。",
                ],
                "8. 风险与兼容性": [
                    "字符串与数值类型不一致可能导致筛选结果错误。"
                ],
                "9. 待确认问题": ["历史字符串值是否需要迁移？"],
            },
        }
        self.explicit_rules = [
            {
                "id": "ER-001",
                "statement": "值为 0 和 false 时必须保持原类型。",
            }
        ]

    def test_text_requirement_uses_its_own_risks_and_open_questions(self) -> None:
        risks = build_business_risks([], [], [], [], self.requirement_doc)
        ambiguities = build_ambiguities({"images": []}, [], self.requirement_doc)

        self.assertEqual(len(risks), 1)
        self.assertIn("类型不一致", risks[0]["risk_statement"])
        self.assertEqual(len(ambiguities), 1)
        self.assertIn("历史字符串值", ambiguities[0]["description"])
        self.assertNotIn("banner", str(risks) + str(ambiguities))

    def test_text_requirement_produces_edges_dimensions_and_coverage(self) -> None:
        risks = build_business_risks([], [], [], [], self.requirement_doc)
        ambiguities = build_ambiguities({"images": []}, [], self.requirement_doc)
        edges = build_edge_cases([], self.requirement_doc)
        dimensions = build_test_dimensions(
            self.explicit_rules, [], [], risks, ambiguities
        )
        candidates = build_coverage_candidates(
            {"images": []}, [], [], self.explicit_rules
        )

        self.assertEqual(len(edges), 1)
        self.assertTrue(any(item["dimension"] == "输入类型与边界" for item in dimensions))
        self.assertEqual(candidates[0]["source_reasoning_ids"], ["ER-001"])

    def test_security_url_requirement_stays_domain_specific(self) -> None:
        rules = [{"id": "ER-URL", "statement": "非 Databricks URL 必须被拒绝。"}]
        dimensions = build_test_dimensions(rules, [], [], [], [])
        names = {item["dimension"] for item in dimensions}
        self.assertIn("异常与失败处理", names)
        self.assertIn("输入类型与边界", names)
        self.assertNotIn("字段必填与默认值", names)

    def test_frontend_falsy_requirement_keeps_type_boundary(self) -> None:
        rules = [{"id": "ER-TYPE", "statement": "number 的 0 与 checkbox 的 false 必须保持原类型。"}]
        dimensions = build_test_dimensions(rules, [], [], [], [])
        boundary = next(item for item in dimensions if item["dimension"] == "输入类型与边界")
        self.assertEqual(boundary["related_reasoning_ids"], ["ER-TYPE"])

    def test_relationship_requirement_keeps_consistency_dimension(self) -> None:
        rules = [{"id": "ER-REL", "statement": "追加新关系时必须保留历史成员集合。"}]
        dimensions = build_test_dimensions(rules, [], [], [], [])
        consistency = next(
            item for item in dimensions if item["dimension"] == "数据一致性与状态保留"
        )
        self.assertEqual(consistency["related_reasoning_ids"], ["ER-REL"])

    def test_image_requirement_builds_dynamic_terms_without_sample_template(self) -> None:
        evidence = {
            "images": [
                {
                    "page_name": "库存管理后台",
                    "source_file": "inputs/images/backend-a.png",
                    "sections": [
                        {
                            "section_type": "form",
                            "field_candidates": [{"field_name": "status"}],
                        }
                    ],
                },
                {
                    "page_name": "价格管理后台",
                    "source_file": "inputs/images/backend-b.png",
                    "sections": [
                        {
                            "section_type": "form",
                            "field_candidates": [{"field_name": "status"}],
                        }
                    ],
                },
                {
                    "page_name": "商品详情页",
                    "source_file": "inputs/images/frontend.png",
                    "sections": [],
                },
            ]
        }
        rules = build_implicit_rules(evidence, [])
        payload = str(rules)
        self.assertIn("库存管理后台", payload)
        self.assertIn("商品详情页", payload)
        for forbidden in ["banner", "瓷片", "金刚区", "企微"]:
            self.assertNotIn(forbidden, payload)

    def test_mixed_requirement_coverage_references_existing_reasoning(self) -> None:
        rules = [
            {
                "id": "ER-MIXED",
                "statement": "保存后详情页展示新名称。",
                "source_refs": [
                    {
                        "page_name": "详情页",
                        "section_name": "基础信息",
                    }
                ],
            }
        ]
        evidence = {
            "images": [
                {
                    "page_name": "详情页",
                    "sections": [{"section_name": "基础信息"}],
                }
            ]
        }
        candidates = build_coverage_candidates(evidence, [], [], rules)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_reasoning_ids"], ["ER-MIXED"])

    def test_requirement_summary_metadata_does_not_become_explicit_rule(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            summary = Path(temp_dir) / "requirement_summary.md"
            summary.write_text(
                "# Demo\n\n"
                "## 5. 面向研发的需求拆解\n\n"
                "- 保存后必须返回成功状态。\n\n"
                "## 7. 数据 / 埋点 / 接口 / 配置要求\n\n"
                "- 关键数据：状态和更新时间。\n"
                "- 关键契约：保存接口。\n"
                "- 关键公开 API：`save`。\n"
                "- 资源字段：`status`。\n"
                "- PR 未声明新增数据库迁移或埋点。\n"
                "- 输出契约：失败时返回错误状态。\n"
                ,
                encoding="utf-8",
            )

            parsed = parse_requirement_summary(summary)

        self.assertEqual(
            parsed["rule_lines"],
            ["保存后必须返回成功状态。", "输出契约：失败时返回错误状态。"],
        )


if __name__ == "__main__":
    unittest.main()
