from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TEST_DESIGN_SCRIPTS = ROOT / "skills" / "test-design" / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(TEST_DESIGN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TEST_DESIGN_SCRIPTS))

from scripts.review_and_score_testcases import (  # noqa: E402
    build_weak_cases,
    compute_duplicate_metrics,
    load_legacy_traceability_metric,
)
from scripts.validate_work_item import (  # noqa: E402
    source_manifest_requires_image_evidence,
    validate_dev_self_testcases,
)
from validate_design_feedback import validate_feedback  # noqa: E402


class ReviewScoreRetentionTests(unittest.TestCase):
    def test_applied_invalid_case_can_reference_removed_case_plan(self) -> None:
        payload = {
            "feedback_items": [{
                "feedback_id": "DF-001",
                "source_review_stage": "manual_review",
                "source_confirmation_file": "reviews/review_record.md",
                "source_case_plan_ids": ["CP-006"],
                "feedback_type": "invalid_case",
                "target_layer": "testability_gate",
                "title": "移出超出范围的计划",
                "finding": "该计划仅来自上下文背景。",
                "recommended_action": "标记范围外并删除正式计划。",
                "must_not_directly_overwrite_testcase": True,
                "status": "applied",
            }]
        }
        self.assertEqual(validate_feedback(payload, {"CP-001"}), [])

    def test_open_case_gap_still_requires_existing_case_plan(self) -> None:
        payload = {
            "feedback_items": [{
                "feedback_id": "DF-001",
                "source_review_stage": "manual_review",
                "source_confirmation_file": "reviews/review_record.md",
                "source_case_plan_ids": ["CP-006"],
                "feedback_type": "case_gap",
                "target_layer": "case_plan",
                "title": "补充分支",
                "finding": "现有分支未覆盖。",
                "recommended_action": "增加原子计划。",
                "must_not_directly_overwrite_testcase": True,
                "status": "open",
            }]
        }
        self.assertTrue(validate_feedback(payload, {"CP-001"}))

    def test_text_only_source_manifest_does_not_require_image_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source_manifest.json"
            path.write_text(json.dumps({
                "sources": [{
                    "source_id": "SRC-001",
                    "source_type": "public_doc",
                    "location": "https://example.test/pr/1",
                    "status": "available",
                }]
            }))
            self.assertFalse(source_manifest_requires_image_evidence(path))

    def test_available_image_source_requires_image_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source_manifest.json"
            path.write_text(json.dumps({
                "sources": [{
                    "source_id": "SRC-001",
                    "source_type": "image",
                    "location": "inputs/images/prototype.png",
                    "status": "available",
                }]
            }))
            self.assertTrue(source_manifest_requires_image_evidence(path))

    def test_missing_legacy_traceability_is_valid_for_minimal_retention(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "traceability_matrix.json"

            rate, invalid_records = load_legacy_traceability_metric(
                missing,
                {},
                {"TC-001"},
            )

        self.assertEqual(rate, 0.0)
        self.assertEqual(invalid_records, [])

    def test_strict_validation_rejects_missing_dev_self_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            testcase_path = root / "testcases_main.md"
            testcase_path.write_text("# Testcases\n", encoding="utf-8")

            ok, message = validate_dev_self_testcases(
                testcase_path,
                root / "dev_self_testcases.md",
                required=True,
            )

        self.assertFalse(ok)
        self.assertIn("strict 要求 dev_self_testcases 存在", message)

    def test_non_strict_validation_keeps_legacy_missing_projection_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            testcase_path = root / "testcases_main.md"
            testcase_path.write_text("# Testcases\n", encoding="utf-8")

            ok, message = validate_dev_self_testcases(
                testcase_path,
                root / "dev_self_testcases.md",
            )

        self.assertTrue(ok)
        self.assertIn("跳过一致性校验", message)

    def test_weak_case_review_detects_template_language_and_semantic_mismatch(self) -> None:
        weak_cases = build_weak_cases(
            [
                {
                    "用例编号": "TC-001",
                    "用例标题": "宣传口号超过一行时在C端换行展示",
                    "测试步骤": "1. 准备业务值并填写或选择“规则对应字段”。\n2. 点击【保存】。",
                    "预期结果": "1. 不能写入本次配置。\n2. 直接展示或响应以下结果。",
                    "所属模块": "商品",
                    "所属功能点": "宣传口号",
                    "__page_name": "C端商品详情页",
                }
            ]
        )

        self.assertEqual(len(weak_cases), 1)
        self.assertEqual(
            set(weak_cases[0]["issue_types"]),
            {
                "generic_step_placeholder",
                "generic_expected_placeholder",
                "action_oracle_mismatch",
                "page_responsibility_mismatch",
            },
        )

    def test_duplicate_metrics_recheck_final_testcase_titles(self) -> None:
        metrics = compute_duplicate_metrics(
            {
                "residual_duplicate_case_count": 0,
                "residual_duplicate_group_count": 0,
                "total_cases_after_flow_append": 2,
            },
            [
                {
                    "用例编号": "TC-001",
                    "用例标题": "确认宣传口号展示（场景1）",
                    "__page_name": "C端商品详情页",
                    "__section_name": "基础信息",
                },
                {
                    "用例编号": "TC-002",
                    "用例标题": "确认宣传口号展示（场景2）",
                    "__page_name": "C端商品详情页",
                    "__section_name": "基础信息",
                },
            ],
        )

        self.assertEqual(metrics["duplicate_case_count"], 1)
        self.assertEqual(metrics["duplicate_group_count"], 1)
        self.assertEqual(
            metrics["duplicate_metric_basis"],
            "final_testcase_semantic_signature",
        )

    def test_weak_case_review_detects_compound_failure_branches(self) -> None:
        weak_cases = build_weak_cases(
            [
                {
                    "用例编号": "TC-002",
                    "用例标题": "连接失败处理",
                    "前置条件": "分别构造前缀非法、driver 拒绝和空连接三类结果。",
                    "测试步骤": "1. 发起连接。",
                    "预期结果": "1. 每类结果均返回连接错误。",
                    "所属模块": "连接",
                    "所属功能点": "失败处理",
                    "__page_name": "连接页",
                }
            ]
        )

        self.assertEqual(len(weak_cases), 1)
        self.assertIn("compound_branch_case", weak_cases[0]["issue_types"])

    def test_weak_case_review_accepts_explicit_before_after_comparison(self) -> None:
        weak_cases = build_weak_cases(
            [
                {
                    "用例编号": "TC-003",
                    "用例标题": "迁移前已有合法数据保持不变",
                    "前置条件": "记录迁移前的记录数量、主键与业务字段值。",
                    "测试步骤": "1. 应用迁移。",
                    "预期结果": (
                        "1. 迁移后的记录数量与迁移前一致。<br>"
                        "2. 各记录的主键和业务字段值与迁移前一致。"
                    ),
                    "所属模块": "数据库迁移",
                    "所属功能点": "数据保持",
                    "__page_name": "迁移执行入口",
                },
                {
                    "用例编号": "TC-004",
                    "用例标题": "重试不改变最终状态",
                    "前置条件": "记录首次请求对应 run 的最终状态。",
                    "测试步骤": "1. 使用相同 request ID 重试。",
                    "预期结果": "1. 原 run 的最终状态与重试前一致。",
                    "所属模块": "幂等",
                    "所属功能点": "关闭后重试",
                    "__page_name": "Workflow API",
                },
            ]
        )

        self.assertEqual(weak_cases, [])


if __name__ == "__main__":
    unittest.main()
