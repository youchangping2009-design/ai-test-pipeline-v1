#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
create_work_item.py

用途：
- 在既有项目下创建独立工作项目录
- 为单次需求/迭代沉淀输入、structured_prd、testcases、reviews 等资产
- 支持一个项目下多次需求独立管理

推荐用法：
python scripts/create_work_item.py --project-code WX-YYPT --work-item-id REQ-001
python scripts/create_work_item.py --project-code wx-yypt --work-item-id spring release --title 春季版本需求
python scripts/create_work_item.py --project-code WX-YYPT --work-item-id REQ-001 --force
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import List

from work_item_policy import DEFAULT_WORK_ITEM_LEVEL
from work_item_policy import VALID_WORK_ITEM_LEVELS

TESTCASE_HEADER = (
    "# 页面：待补充\n"
    "## 板块：待补充\n"
    "| 用例编号 | 所属模块 | 所属功能点 | 用例标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 标签 | 测试类型 | 备注 |\n"
    "|---------|---------|-----------|---------|---------|---------|---------|-------|------|---------|------|\n"
)


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_project_code(project_code: str) -> str:
    normalized = project_code.strip().upper()
    if not normalized:
        raise ValueError("project_code 不能为空")
    return normalized


def normalize_work_item_id(work_item_id: str) -> str:
    normalized = "-".join(work_item_id.strip().split()).upper()
    if not normalized:
        raise ValueError("work_item_id 不能为空")
    return normalized


def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def ensure_directory(path: Path, created_dirs: List[Path]) -> None:
    if path.exists():
        return
    path.mkdir(parents=True, exist_ok=True)
    created_dirs.append(path)


def write_file(
    path: Path,
    content: str,
    force: bool,
    written_files: List[Path],
    skipped_files: List[Path],
) -> None:
    if path.exists() and not force:
        skipped_files.append(path)
        return

    path.write_text(content, encoding="utf-8")
    written_files.append(path)


def build_readme(
    project_code: str,
    work_item_id: str,
    title: str,
    requirement_version: str,
    work_item_level: str,
) -> str:
    return (
        f"# {work_item_id}\n\n"
        f"- 项目编码：{project_code}\n"
        f"- 工作项 ID：{work_item_id}\n"
        f"- 标题：{title or '待补充'}\n"
        f"- 需求版本：{requirement_version or '待补充'}\n"
        f"- 工作项级别：{work_item_level}\n\n"
        "## 目录说明\n\n"
        "- `inputs/`：该工作项原始资料与补充输入\n"
        "- `image_evidence/`：图片类 PRD 的中间证据层\n"
        "- `analysis/`：AI 推理层产物，先落 `analysis_report.md` 与 `reasoning_pack.json`\n"
        "- `coverage/`：coverage planner 产物，沉淀 `coverage_matrix.json`\n"
        "- `evidence/`：从原始输入抽取的证据清单\n"
        "- `structured_prd/`：该工作项结构化 PRD 产物，其中 `structured_prd.md` 是结构化 Markdown 真源，`structured_prd.json` 是从其编译出的机器投影\n"
        "- `acceptance/`：testability gate 与 acceptance examples 产物\n"
        "- `design/`：责任划分、测试设计矩阵与 code review 映证反馈产物\n"
        "- `traceability/`：证据、结构化产物与 testcase 的追踪矩阵\n"
        "- `testcases/`：该工作项测试用例产物\n"
        "- `reviews/`：该工作项评审记录\n"
        "- `code_reviews/`：前端/后端代码评审与人工确认产物\n"
        "- `.generation/`：该工作项的重生成任务包\n\n"
        "## 建议流程\n\n"
        "1. 将该需求原始资料放入 `inputs/`\n"
        "2. 生成 `inputs/requirement_summary.md` 与 `inputs/source_manifest.json`\n"
        "3. 若输入主要是截图，产出 `image_evidence/image_evidence_inventory.json`\n"
        "4. 生成 `analysis/analysis_report.md` 与 `analysis/reasoning_pack.json`\n"
        "5. 生成 structured_prd、测试设计决策层与 `case_plan`\n"
        "6. 同步生成 `testpoints.md/json` 与 `testcases_main.md`\n"
        "7. 生成 traceability、review 和导出产物\n"
        "8. 使用 `scripts/validate_work_item.py --strict` 执行工作项级统一校验\n"
    )


def build_manifest(
    project_code: str,
    work_item_id: str,
    title: str,
    requirement_version: str,
    work_item_level: str,
) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "title": title or "",
        "requirement_version": requirement_version or "",
        "work_item_level": work_item_level,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "initialized",
        "pipeline_policy": {
            "requirement_intake_required": True,
            "testpoints_required": True,
        },
        "quality_gate": {
            "enabled": False,
            "mode": "soft",
            "rollout_source": "new_work_item",
            "thresholds": {
                "false_traceability_rate_fail": 0.05,
                "generalized_case_rate_warn": 0.03,
                "generalized_case_count_warn": 5,
                "duplicate_case_rate_warn": 0.005,
                "duplicate_case_count_warn": 1
            }
        },
        "artifacts": {
            "inputs": "inputs/",
            "requirement_summary": "inputs/requirement_summary.md",
            "source_manifest": "inputs/source_manifest.json",
            "image_evidence": "image_evidence/image_evidence_inventory.json",
            "analysis": {
                "analysis_report": "analysis/analysis_report.md",
                "reasoning_pack": "analysis/reasoning_pack.json"
            },
            "coverage": "coverage/coverage_matrix.json",
            "evidence": "evidence/evidence_inventory.json",
            "structured_prd_markdown": "structured_prd/structured_prd.md",
            "structured_prd_json": "structured_prd/structured_prd.json",
            "structured_prd": "structured_prd/structured_prd.json",
            "testability_gate_markdown": "acceptance/testability_gate.md",
            "testability_gate_json": "acceptance/testability_gate.json",
            "acceptance_examples_markdown": "acceptance/acceptance_examples.md",
            "acceptance_examples_json": "acceptance/acceptance_examples.json",
            "verification_responsibility_map_markdown": "design/verification_responsibility_map.md",
            "verification_responsibility_map_json": "design/verification_responsibility_map.json",
            "test_design_matrix_markdown": "design/test_design_matrix.md",
            "test_design_matrix_json": "design/test_design_matrix.json",
            "design_feedback_markdown": "design/design_feedback.md",
            "design_feedback_json": "design/design_feedback.json",
            "traceability_primary": "traceability/coverage_first_traceability.json",
            "traceability_adapter": "traceability/traceability_adapter.json",
            "traceability_legacy": "traceability/traceability_matrix.json",
            "traceability": "traceability/traceability_matrix.json",
            "case_plan_markdown": "testcases/case_plan.md",
            "case_plan_json": "testcases/case_plan.json",
            "testpoints_markdown": "testcases/testpoints.md",
            "testpoints_json": "testcases/testpoints.json",
            "testcases_main": "testcases/testcases_main.md",
            "testcase_bundle_json": "testcases/testcase_bundle.json",
            "field_audit": "testcases/field_audit.json",
            "grouped_audit": "testcases/grouped_audit.json",
            "testcases": "testcases/testcases.md",
            "reviews": "reviews/review_record.md",
            "review_artifacts": {
                "missing_rules": "reviews/missing_rules.json",
                "missing_fidelity_points": "reviews/missing_fidelity_points.json",
                "fidelity_hit_locations": "reviews/fidelity_hit_locations.json",
                "duplicate_case_report": "reviews/duplicate_case_report.json",
                "weak_cases": "reviews/weak_cases.json",
                "generalized_cases": "reviews/generalized_cases.json",
                "quality_report": "reviews/quality_report.json"
            },
            "code_reviews": {
                "scope": "code_reviews/code_review_scope.json",
                "request": "code_reviews/code_review_request.md",
                "frontend_review": "code_reviews/frontend_code_review.md",
                "frontend_confirmation": "code_reviews/frontend_confirmation.json",
                "backend_review": "code_reviews/backend_code_review.md",
                "backend_confirmation": "code_reviews/backend_confirmation.json"
            }
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_inputs_readme() -> str:
    return (
        "# Inputs\n\n"
        "请在此目录放置本次工作项的原始输入资料，例如：\n\n"
        "- PRD 原文\n"
        "- 截图原件（推荐放入 `images/` 子目录）\n"
        "- 原型图\n"
        "- 补充说明\n\n"
        "推荐约定：\n\n"
        "- `inputs/images/`：存放原始截图、标注图、原型导出图片\n"
        "- `inputs/received_screenshots.md`：记录图片说明、页名、补充口述、OCR 修正和图片文件对应关系\n"
        "- 后续重新增强图片识别时，优先直接消费 `inputs/images/` 中的本地图片文件\n"
    )


def build_requirement_summary_placeholder(work_item_id: str, title: str) -> str:
    return (
        f"# {work_item_id} {title or '需求'}需求整理\n\n"
        "整理时间：待补充\n\n"
        "## 1. 资料来源\n\n"
        "- 待补充\n\n"
        "## 2. 需求结论\n\n"
        "- 待补充\n\n"
        "## 3. 前置条件 / 准备工作\n\n"
        "- 待补充\n\n"
        "## 4. 业务范围与不做范围\n\n"
        "- 待补充\n\n"
        "## 5. 面向研发的需求拆解\n\n"
        "- 待补充\n\n"
        "## 6. 面向测试的验收关注点\n\n"
        "- 待补充\n\n"
        "## 7. 数据 / 埋点 / 接口 / 配置要求\n\n"
        "- 待补充\n\n"
        "## 8. 风险与兼容性\n\n"
        "- 待补充\n\n"
        "## 9. 待确认问题\n\n"
        "- 待补充\n\n"
        "## 10. 本轮整理边界\n\n"
        "- 待补充\n"
    )


def build_source_manifest_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "manifest_type": "requirement_source_manifest",
        "summary_artifact": "inputs/requirement_summary.md",
        "sources": [],
        "unresolved_sources": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_input_images_readme() -> str:
    return (
        "# Input Images\n\n"
        "请在此目录放置本次工作项的原始图片输入，例如：\n\n"
        "- 页面截图\n"
        "- 标注图\n"
        "- 原型导出图\n"
        "- 补充说明截图\n\n"
        "建议命名：\n\n"
        "- `01-banner-config.png`\n"
        "- `02-tile-config.png`\n"
        "- `03-icon-config.png`\n"
        "- `04-popup-config.png`\n\n"
        "建议配套维护：\n\n"
        "- 在上级目录的 `received_screenshots.md` 中记录每张图的用途、页名、备注和文件名映射\n"
        "- `image_evidence_inventory.json` 的 `source_file` 优先引用这里的相对路径\n"
    )


def build_evidence_inventory_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "generated_from": [],
        "evidence_items": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_reasoning_pack_placeholder(project_code: str, work_item_id: str, title: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "generated_at": "",
        "generated_from": [],
        "requirement_summary": {
            "title": title or "",
            "summary_text": "",
            "primary_pages": [],
            "primary_user_surfaces": [],
            "source_notes": []
        },
        "explicit_rules": [],
        "implicit_rules": [],
        "field_constraints": [],
        "data_source_rules": [],
        "business_risks": [],
        "edge_cases": [],
        "ambiguities": [],
        "recommended_test_dimensions": [],
        "coverage_candidates": []
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_analysis_report_placeholder(title: str) -> str:
    return (
        "# Analysis Report\n\n"
        "## Requirement Summary\n"
        f"- 标题：`{title or '待补充'}`\n"
        "- 摘要：待补充\n\n"
        "## Reasoning Snapshot\n"
        "- explicit_rules：0\n"
        "- implicit_rules：0\n"
        "- field_constraints：0\n"
        "- data_source_rules：0\n"
        "- business_risks：0\n"
        "- edge_cases：0\n"
        "- ambiguities：0\n"
        "- recommended_test_dimensions：0\n"
        "- coverage_candidates：0\n"
    )


def build_coverage_matrix_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "generated_at": "",
        "generated_from": [],
        "entries": []
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_empty_json_list() -> str:
    return "[]\n"


def build_testability_gate_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {"project_code": project_code, "work_item_id": work_item_id, "items": []}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_testability_gate_markdown_placeholder() -> str:
    return (
        "# Testability Gate\n\n"
        "| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )


def build_acceptance_examples_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {"project_code": project_code, "work_item_id": work_item_id, "examples": []}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_acceptance_examples_markdown_placeholder() -> str:
    return (
        "# Acceptance Examples\n\n"
        "| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
    )


def build_verification_responsibility_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {"project_code": project_code, "work_item_id": work_item_id, "responsibilities": []}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_verification_responsibility_markdown_placeholder() -> str:
    return (
        "# Verification Responsibility Map\n\n"
        "| responsibility_id | source_rule_id | primary_verification_side | primary_verification_method | consumer_verification_required | api_guard_required | risk_note_required | rule_text | reason |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )


def build_test_design_matrix_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {"project_code": project_code, "work_item_id": work_item_id, "items": []}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_test_design_matrix_markdown_placeholder() -> str:
    return (
        "# Test Design Matrix\n\n"
        "| matrix_id | source_rule_id | gate_id | example_id | responsibility_id | case_plan_id | verification_side | case_type | coverage_focus | assertion | risk_level | note |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )


def build_design_feedback_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {"project_code": project_code, "work_item_id": work_item_id, "feedback_items": []}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_design_feedback_markdown_placeholder() -> str:
    return (
        "# Design Feedback\n\n"
        "| feedback_id | source_review_stage | source_confirmation_file | source_case_plan_ids | feedback_type | target_layer | title | finding | recommended_action | must_not_directly_overwrite_testcase | status |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
    )


def build_case_plan_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {"project_code": project_code, "work_item_id": work_item_id, "case_plans": []}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_case_plan_markdown_placeholder() -> str:
    return (
        "# Case Plan\n\n"
        "| case_plan_id | source_gate_ids | source_example_ids | source_responsibility_ids | source_coverage_ids | generated_testcase_ids | title | verification_side | case_type | priority | assertion | validation_path | should_generate_case |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )


def build_testcase_bundle_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "truth_source": "testcases/testcases_main.md",
        "projection_only": True,
        "generated_from": ["testcases/testcases_main.md"],
        "cases": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_testpoints_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "truth_source": "testcases/case_plan.json",
        "projection_only": True,
        "generated_from": ["testcases/case_plan.json", "testcases/testcases_main.md"],
        "testpoints": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_testpoints_markdown_placeholder(project_code: str, work_item_id: str) -> str:
    return (
        "# Testpoints View\n\n"
        f"- Project: `{project_code}`\n"
        f"- Work Item: `{work_item_id}`\n"
        "- Truth Source: `testcases/case_plan.json`\n"
        "- Projection Only: `true`\n\n"
        "| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
    )


def build_quality_report_placeholder() -> str:
    payload = {
        "generated_at": "",
        "total_cases": 0,
        "total_coverage_entries": 0,
        "rule_coverage_rate": 0.0,
        "atomic_case_rate": 0.0,
        "boundary_coverage_rate": 0.0,
        "data_source_rule_coverage_rate": 0.0,
        "generalized_case_count": 0,
        "generalized_case_rate": 0.0,
        "duplicate_case_count": 0,
        "duplicate_case_rate": 0.0,
        "missing_fidelity_points": 0,
        "high_priority_fidelity_missing": 0,
        "false_traceability_rate": 0.0,
        "false_traceability_rate_primary": 0.0,
        "false_traceability_rate_legacy": 0.0,
        "traceability_metric_source": "coverage_first_traceability",
        "quality_gate": {
            "enabled": False,
            "mode": "soft",
            "rollout_source": "new_work_item",
            "status": "report_only",
            "thresholds": {
                "false_traceability_rate_fail": 0.05,
                "generalized_case_rate_warn": 0.03,
                "generalized_case_count_warn": 5,
                "duplicate_case_rate_warn": 0.005,
                "duplicate_case_count_warn": 1
            },
            "warnings": [],
            "failures": []
        },
        "unresolved_issues": []
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_image_evidence_inventory_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "generated_from": [],
        "images": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_traceability_matrix_placeholder(project_code: str, work_item_id: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "records": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_structured_prd_placeholder(
    project_code: str,
    title: str,
    requirement_version: str,
) -> str:
    payload = {
        "project_info": {
            "project_code": project_code,
            "project_name": "",
            "business_line": "",
            "prd_source": "",
            "prd_version": requirement_version or "",
        },
        "requirement_info": {
            "requirement_title": title or "",
            "requirement_background": "",
            "requirement_goal": "",
            "scope": {
                "in_scope": [],
                "out_of_scope": [],
            },
        },
        "pages": [],
        "modules": [],
        "flows": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_structured_prd_markdown_placeholder(
    project_code: str,
    title: str,
    requirement_version: str,
) -> str:
    payload = {
        "project_info": {
            "project_code": project_code,
            "project_name": "",
            "business_line": "",
            "prd_source": "",
            "prd_version": requirement_version or "",
        },
        "requirement_info": {
            "requirement_title": title or "",
            "requirement_background": "",
            "requirement_goal": "",
            "scope": {
                "in_scope": [],
                "out_of_scope": [],
            },
        },
        "pages": [],
        "modules": [],
        "flows": [],
    }
    return (
        "# Structured PRD\n\n"
        "## project_info\n"
        "```json\n"
        f"{json.dumps(payload['project_info'], ensure_ascii=False, indent=2)}\n"
        "```\n\n"
        "## requirement_info\n"
        "```json\n"
        f"{json.dumps(payload['requirement_info'], ensure_ascii=False, indent=2)}\n"
        "```\n\n"
        "## pages\n"
        "```json\n[]\n```\n\n"
        "## modules\n"
        "```json\n[]\n```\n\n"
        "## flows\n"
        "```json\n[]\n```\n"
    )


def build_review_record() -> str:
    return (
        "# Review Record\n\n"
        "## 评审结论\n\n"
        "- 结论：待评审\n"
        "- 评审人：\n"
        "- 评审时间：\n\n"
        "## 问题清单\n\n"
        "| 序号 | 类型 | 问题描述 | 严重级别 | 建议修改 |\n"
        "|------|------|----------|----------|----------|\n"
        "| 1 | 结构化PRD / Flow / 用例 / 规则 |  | P0/P1/P2/P3 |  |\n"
    )


def build_code_review_markdown(stage_title: str, review_type: str) -> str:
    return (
        "# Code Review\n\n"
        f"- stage: `{stage_title}`\n"
        f"- review_type: `{review_type}`\n"
        "- manual_confirmation_required: `true`\n"
        "- review_policy: `不得修改业务代码，不得修改历史产出物`\n\n"
        "## Review Scope\n\n"
        "- 对照对象：结构化 PRD / testcase / 当前阶段代码实现\n"
        "- 输出目标：识别代码缺口、用例缺口、无效用例、仅 PRD 存在但代码未落地项\n"
        "- 本阶段不得修改业务代码，不得修改历史产出物\n\n"
        "## Findings\n\n"
        "| 序号 | 类型 | 描述 | 严重级别 | 证据 |\n"
        "|------|------|------|----------|------|\n"
        "| 1 | 待补充 |  | P1/P2/P3 |  |\n\n"
        "## Coverage Mapping\n\n"
        "- 补充需要映证的 `implementation_binding / recommended_cr_stage / manual_confirmation_required / cr_focus_points`\n\n"
        "## Invalid Or Stale Cases\n\n"
        "- 标记当前代码下无效、过期、无法由本阶段代码证明的用例\n\n"
        "## Manual Confirmation\n\n"
        "- 需要人工确认后才能作为正式 CR 结论进入流水线\n"
        "- 人工确认完成后，请同步填写对应 confirmation JSON\n"
    )


def build_code_review_confirmation(stage: str, review_type: str) -> str:
    payload = {
        "stage": stage,
        "review_type": review_type,
        "manual_confirmation_required": True,
        "confirmation_status": "pending",
        "confirmed_by": "",
        "confirmed_at": "",
        "confirmation_note": "",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_code_review_scope() -> str:
    payload = {
        "status": "awaiting_code_directories",
        "frontend_code_dirs": [],
        "backend_code_dirs": [],
        "next_action": "请补充前端或后端代码目录后进入代码映证流程。",
        "updated_at": "",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_code_review_request() -> str:
    return (
        "# Code Review Request\n\n"
        "- status: `awaiting_code_directories`\n"
        "- next_action: `请补充对应的前端/后端代码目录后进入代码映证流程`\n\n"
        "## Required Code Directories\n\n"
        "- frontend_code_dirs: 待补充\n"
        "- backend_code_dirs: 待补充\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="在项目下初始化 AI Test Pipeline 工作项目录与占位文件")
    parser.add_argument("--project-code", required=True, help="项目编码，脚本会自动转为大写")
    parser.add_argument("--work-item-id", required=True, help="工作项 ID，空格会替换为中划线并转为大写")
    parser.add_argument("--title", required=False, help="工作项标题")
    parser.add_argument("--requirement-version", required=False, help="需求版本")
    parser.add_argument(
        "--work-item-level",
        choices=sorted(VALID_WORK_ITEM_LEVELS),
        default=None,
        help="工作项复杂度级别；未指定时读取 project_manifest.default_work_item_level，缺失回退 M",
    )
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        project_code = normalize_project_code(args.project_code)
        work_item_id = normalize_work_item_id(args.work_item_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    title = (args.title or "").strip()
    requirement_version = (args.requirement_version or "").strip()
    repo_root = get_repo_root()
    project_root = repo_root / "assets" / "projects" / project_code
    if not project_root.exists():
        print(
            f"项目目录不存在: {project_root}\n"
            "请先执行 init_project.py 初始化项目。",
            file=sys.stderr,
        )
        return 1
    project_manifest_path = project_root / "project_manifest.json"
    if not project_manifest_path.exists():
        print(
            f"项目缺少轻量壳 manifest: {project_manifest_path}\n"
            "请先执行 init_project.py 初始化或迁移项目。",
            file=sys.stderr,
        )
        return 1
    project_manifest = json.loads(project_manifest_path.read_text(encoding="utf-8"))
    work_item_level = (
        args.work_item_level
        or str(project_manifest.get("default_work_item_level", "")).strip().upper()
        or DEFAULT_WORK_ITEM_LEVEL
    )
    if work_item_level not in VALID_WORK_ITEM_LEVELS:
        print(
            f"项目默认 work_item_level 非法: {work_item_level}",
            file=sys.stderr,
        )
        return 1

    work_item_root = project_root / "work_items" / work_item_id
    inputs_dir = work_item_root / "inputs"
    input_images_dir = inputs_dir / "images"
    image_evidence_dir = work_item_root / "image_evidence"
    analysis_dir = work_item_root / "analysis"
    coverage_dir = work_item_root / "coverage"
    evidence_dir = work_item_root / "evidence"
    structured_prd_dir = work_item_root / "structured_prd"
    acceptance_dir = work_item_root / "acceptance"
    design_dir = work_item_root / "design"
    traceability_dir = work_item_root / "traceability"
    testcases_dir = work_item_root / "testcases"
    reviews_dir = work_item_root / "reviews"
    code_reviews_dir = work_item_root / "code_reviews"

    created_dirs: List[Path] = []
    written_files: List[Path] = []
    skipped_files: List[Path] = []

    for directory in [
        project_root / "work_items",
        work_item_root,
        inputs_dir,
        input_images_dir,
        image_evidence_dir,
        analysis_dir,
        coverage_dir,
        evidence_dir,
        structured_prd_dir,
        acceptance_dir,
        design_dir,
        traceability_dir,
        testcases_dir,
        reviews_dir,
        code_reviews_dir,
    ]:
        ensure_directory(directory, created_dirs)

    write_file(
        work_item_root / "README.md",
        build_readme(project_code, work_item_id, title, requirement_version, work_item_level),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        work_item_root / "manifest.json",
        build_manifest(project_code, work_item_id, title, requirement_version, work_item_level),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        inputs_dir / "README.md",
        build_inputs_readme(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        inputs_dir / "requirement_summary.md",
        build_requirement_summary_placeholder(work_item_id, title),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        inputs_dir / "source_manifest.json",
        build_source_manifest_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        input_images_dir / "README.md",
        build_input_images_readme(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        image_evidence_dir / "image_evidence_inventory.json",
        build_image_evidence_inventory_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        analysis_dir / "analysis_report.md",
        build_analysis_report_placeholder(title),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        analysis_dir / "reasoning_pack.json",
        build_reasoning_pack_placeholder(project_code, work_item_id, title),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        coverage_dir / "coverage_matrix.json",
        build_coverage_matrix_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        evidence_dir / "evidence_inventory.json",
        build_evidence_inventory_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        structured_prd_dir / "structured_prd.md",
        build_structured_prd_markdown_placeholder(project_code, title, requirement_version),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        structured_prd_dir / "structured_prd.json",
        build_structured_prd_placeholder(project_code, title, requirement_version),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        acceptance_dir / "testability_gate.md",
        build_testability_gate_markdown_placeholder(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        acceptance_dir / "testability_gate.json",
        build_testability_gate_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        acceptance_dir / "acceptance_examples.md",
        build_acceptance_examples_markdown_placeholder(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        acceptance_dir / "acceptance_examples.json",
        build_acceptance_examples_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        design_dir / "verification_responsibility_map.md",
        build_verification_responsibility_markdown_placeholder(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        design_dir / "verification_responsibility_map.json",
        build_verification_responsibility_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        design_dir / "test_design_matrix.md",
        build_test_design_matrix_markdown_placeholder(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        design_dir / "test_design_matrix.json",
        build_test_design_matrix_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        design_dir / "design_feedback.md",
        build_design_feedback_markdown_placeholder(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        design_dir / "design_feedback.json",
        build_design_feedback_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        traceability_dir / "traceability_matrix.json",
        build_traceability_matrix_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        testcases_dir / "case_plan.md",
        build_case_plan_markdown_placeholder(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        testcases_dir / "case_plan.json",
        build_case_plan_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        testcases_dir / "testcases_main.md",
        TESTCASE_HEADER,
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        testcases_dir / "testpoints.json",
        build_testpoints_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        testcases_dir / "testpoints.md",
        build_testpoints_markdown_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        testcases_dir / "testcase_bundle.json",
        build_testcase_bundle_placeholder(project_code, work_item_id),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        testcases_dir / "testcases.md",
        TESTCASE_HEADER,
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        reviews_dir / "review_record.md",
        build_review_record(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        reviews_dir / "missing_rules.json",
        build_empty_json_list(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        reviews_dir / "weak_cases.json",
        build_empty_json_list(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        reviews_dir / "generalized_cases.json",
        build_empty_json_list(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        reviews_dir / "quality_report.json",
        build_quality_report_placeholder(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        code_reviews_dir / "code_review_scope.json",
        build_code_review_scope(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        code_reviews_dir / "code_review_request.md",
        build_code_review_request(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        code_reviews_dir / "frontend_code_review.md",
        build_code_review_markdown("frontend_code_review", "frontend_code"),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        code_reviews_dir / "frontend_confirmation.json",
        build_code_review_confirmation("frontend_code_review", "frontend_code"),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        code_reviews_dir / "backend_code_review.md",
        build_code_review_markdown("backend_code_review", "backend_code"),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        code_reviews_dir / "backend_confirmation.json",
        build_code_review_confirmation("backend_code_review", "backend_code"),
        args.force,
        written_files,
        skipped_files,
    )

    print_section("Work Item Init Summary")
    print(f"项目编码: {project_code}")
    print(f"工作项 ID: {work_item_id}")
    print(f"工作项级别: {work_item_level}")
    print(f"工作项目录: {work_item_root}")

    print("\n创建的目录：")
    if created_dirs:
        for item in created_dirs:
            print(f"- {item}")
    else:
        print("- 无")

    print("\n写入的文件：")
    if written_files:
        for item in written_files:
            print(f"- {item}")
    else:
        print("- 无")

    print("\n跳过的已存在文件：")
    if skipped_files:
        for item in skipped_files:
            print(f"- {item}")
    else:
        print("- 无")

    print("\n下一步建议操作：")
    print(f"1. 将本次需求原始资料放入 {inputs_dir}")
    print(f"   - 图片原件优先放入 {input_images_dir}")
    print(f"2. 生成 {inputs_dir / 'requirement_summary.md'} 与 {inputs_dir / 'source_manifest.json'}")
    print(f"3. 若输入主要是截图，补全 {image_evidence_dir / 'image_evidence_inventory.json'}")
    print(f"4. 生成 reasoning、structured_prd、coverage 与测试设计决策层")
    print(f"5. 补全 {testcases_dir / 'case_plan.json'}")
    print(f"6. 同步生成 {testcases_dir / 'testpoints.md'}、{testcases_dir / 'testpoints.json'} 与 {testcases_dir / 'testcases_main.md'}")
    print(f"7. 生成 traceability、review、code review 与导出产物")
    print(
        "8. 执行工作项级校验："
        f" /usr/bin/python3 {repo_root / 'scripts' / 'validate_work_item.py'}"
        f" --project-code {project_code}"
        f" --work-item-id {work_item_id}"
        f" --work-item-level {work_item_level}"
        " --strict"
    )

    if project_manifest_path.exists():
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "scripts" / "refresh_project_views.py"),
                "--project-code",
                project_code,
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"项目视图刷新失败:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
            return 1
        print("9. 项目索引与质量汇总已刷新")

    return 0


if __name__ == "__main__":
    sys.exit(main())
