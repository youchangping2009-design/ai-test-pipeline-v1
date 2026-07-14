#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
init_project.py

用途：
- 为新项目初始化 assets/projects/<project_code>/ 目录结构
- 创建 evidence / structured_prd / traceability / testcase / review 所需占位文件
- 便于后续执行生成、评审与统一校验

推荐用法：
python scripts/init_project.py --project-code WX-YYPT
python scripts/init_project.py --project-code wx-yypt --project-name 测试项目 --business-line 玩心
python scripts/init_project.py --project-code WX-YYPT --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List


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


def build_project_readme(project_code: str, project_name: str, business_line: str) -> str:
    return (
        f"# {project_code}\n\n"
        f"- 项目编码：{project_code}\n"
        f"- 项目名称：{project_name or '待补充'}\n"
        f"- 业务线：{business_line or '待补充'}\n\n"
        "## 目录说明\n\n"
        "- `inputs/`：原始 PRD、截图、补充材料\n"
        "- `image_evidence/`：图片类 PRD 的中间证据层\n"
        "- `analysis/`：AI 推理层产物，先沉淀 `analysis_report.md` 与 `reasoning_pack.json`\n"
        "- `coverage/`：coverage planner 产物，沉淀 `coverage_matrix.json`\n"
        "- `evidence/`：原始输入证据清单\n"
        "- `structured_prd/`：结构化 PRD 产物，其中 `structured_prd.md` 是结构化 Markdown 真源，`structured_prd.json` 是从其编译出的机器投影\n"
        "- `traceability/`：证据、结构化结果与 testcase 的追踪矩阵\n"
        "- `testcases/`：测试用例产物\n"
        "- `reviews/`：评审记录与问题沉淀\n\n"
        "## 建议流程\n\n"
        "1. 将原始需求资料放入 `inputs/`\n"
        "2. 若输入主要是截图，先生成 `image_evidence/image_evidence_inventory.json`\n"
        "3. 先生成 `analysis/analysis_report.md` 与 `analysis/reasoning_pack.json`\n"
        "4. 生成 `coverage/coverage_matrix.json`\n"
        "5. 对具体需求先使用 `scripts/create_work_item.py` 初始化工作项\n"
        "6. 对工作项执行 `scripts/prepare_regeneration_run.py`\n"
        "7. 使用 `scripts/generate_regeneration_bundle.py` 生成 bundle\n"
        "8. 在工作项 `code_reviews/` 中完成前端代码 CR、后端代码 CR 与人工确认\n"
        "9. 运行 reviewer + scorer 产出质量报告\n"
        "10. 使用 `scripts/execute_regeneration_bundle.py` 执行 bundle，并自动编译 `structured_prd.json` / 导出 `feishu_ready.md`\n"
        "11. 使用 `scripts/validate_outputs.py` 或 `scripts/validate_work_item.py` 执行统一校验\n"
    )


def build_inputs_readme() -> str:
    return (
        "# Inputs\n\n"
        "请在此目录放置项目原始输入资料，例如：\n\n"
        "- PRD 原文\n"
        "- 截图原件（推荐放入 `images/` 子目录）\n"
        "- 补充说明\n"
        "- 业务规则附件\n\n"
        "推荐约定：\n\n"
        "- `inputs/images/`：存放原始截图、标注图、原型导出图片\n"
        "- 工作项级若需要补充截图说明，可在 `work_items/<WORK_ITEM_ID>/inputs/received_screenshots.md` 中维护文件映射\n"
        "- 后续重新增强图片识别时，优先直接消费 `inputs/images/` 中的本地图片文件\n"
    )


def build_input_images_readme() -> str:
    return (
        "# Input Images\n\n"
        "请在此目录放置项目级原始图片输入，例如：\n\n"
        "- 页面截图\n"
        "- 标注图\n"
        "- 原型导出图\n"
        "- 历史补充说明图\n\n"
        "建议命名时带上模块或页名，便于后续工作项复用。\n"
    )


def build_evidence_inventory_placeholder(project_code: str) -> str:
    payload = {
        "project_code": project_code,
        "generated_from": [],
        "evidence_items": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_reasoning_pack_placeholder(project_code: str, project_name: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": "",
        "generated_at": "",
        "generated_from": [],
        "requirement_summary": {
            "title": project_name or "",
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


def build_analysis_report_placeholder(project_name: str) -> str:
    return (
        "# Analysis Report\n\n"
        "## Requirement Summary\n"
        f"- 标题：`{project_name or '待补充'}`\n"
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


def build_coverage_matrix_placeholder(project_code: str) -> str:
    payload = {
        "project_code": project_code,
        "work_item_id": "",
        "generated_at": "",
        "generated_from": [],
        "entries": []
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_empty_json_list() -> str:
    return "[]\n"


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
            "rollout_source": "legacy_report_only",
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


def build_image_evidence_inventory_placeholder(project_code: str) -> str:
    payload = {
        "project_code": project_code,
        "generated_from": [],
        "images": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_traceability_matrix_placeholder(project_code: str) -> str:
    payload = {
        "project_code": project_code,
        "records": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_structured_prd_placeholder(
    project_code: str,
    project_name: str,
    business_line: str,
) -> str:
    payload = {
        "project_info": {
            "project_code": project_code,
            "project_name": project_name or "",
            "business_line": business_line or "",
            "prd_source": "",
            "prd_version": "",
        },
        "requirement_info": {
            "requirement_title": "",
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
    project_name: str,
    business_line: str,
) -> str:
    payload = {
        "project_info": {
            "project_code": project_code,
            "project_name": project_name or "",
            "business_line": business_line or "",
            "prd_source": "",
            "prd_version": "",
        },
        "requirement_info": {
            "requirement_title": "",
            "requirement_background": "",
            "requirement_goal": "",
            "scope": {
                "in_scope": [],
                "out_of_scope": [],
            },
        },
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化 AI Test Pipeline 项目目录与占位文件")
    parser.add_argument("--project-code", required=True, help="项目编码，脚本会自动转为大写")
    parser.add_argument("--project-name", required=False, help="项目名称")
    parser.add_argument("--business-line", required=False, help="业务线")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        project_code = normalize_project_code(args.project_code)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    project_name = (args.project_name or "").strip()
    business_line = (args.business_line or "").strip()

    repo_root = get_repo_root()
    project_root = repo_root / "assets" / "projects" / project_code

    inputs_dir = project_root / "inputs"
    input_images_dir = inputs_dir / "images"
    image_evidence_dir = project_root / "image_evidence"
    analysis_dir = project_root / "analysis"
    coverage_dir = project_root / "coverage"
    evidence_dir = project_root / "evidence"
    structured_prd_dir = project_root / "structured_prd"
    traceability_dir = project_root / "traceability"
    testcases_dir = project_root / "testcases"
    reviews_dir = project_root / "reviews"

    created_dirs: List[Path] = []
    written_files: List[Path] = []
    skipped_files: List[Path] = []

    for directory in [
        project_root,
        inputs_dir,
        input_images_dir,
        image_evidence_dir,
        analysis_dir,
        coverage_dir,
        evidence_dir,
        structured_prd_dir,
        traceability_dir,
        testcases_dir,
        reviews_dir,
    ]:
        ensure_directory(directory, created_dirs)

    write_file(
        project_root / "README.md",
        build_project_readme(project_code, project_name, business_line),
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
        input_images_dir / "README.md",
        build_input_images_readme(),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        image_evidence_dir / "image_evidence_inventory.json",
        build_image_evidence_inventory_placeholder(project_code),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        analysis_dir / "analysis_report.md",
        build_analysis_report_placeholder(project_name),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        analysis_dir / "reasoning_pack.json",
        build_reasoning_pack_placeholder(project_code, project_name),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        coverage_dir / "coverage_matrix.json",
        build_coverage_matrix_placeholder(project_code),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        evidence_dir / "evidence_inventory.json",
        build_evidence_inventory_placeholder(project_code),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        structured_prd_dir / "structured_prd.md",
        build_structured_prd_markdown_placeholder(project_code, project_name, business_line),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        structured_prd_dir / "structured_prd.json",
        build_structured_prd_placeholder(project_code, project_name, business_line),
        args.force,
        written_files,
        skipped_files,
    )
    write_file(
        traceability_dir / "traceability_matrix.json",
        build_traceability_matrix_placeholder(project_code),
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

    print_section("Project Init Summary")
    print(f"项目编码: {project_code}")
    print(f"项目目录: {project_root}")

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
    print(f"1. 将原始需求资料放入 {inputs_dir}")
    print(f"   - 图片原件优先放入 {input_images_dir}")
    print(f"2. 若输入主要是截图，补全 {image_evidence_dir / 'image_evidence_inventory.json'}")
    print(f"3. 先生成 {analysis_dir / 'analysis_report.md'} 与 {analysis_dir / 'reasoning_pack.json'}")
    print(f"4. 生成 {coverage_dir / 'coverage_matrix.json'}")
    print(f"5. 补全 {evidence_dir / 'evidence_inventory.json'}")
    print(f"6. 先补全 {structured_prd_dir / 'structured_prd.md'}")
    print(f"7. 再编译生成 {structured_prd_dir / 'structured_prd.json'}")
    print(f"8. 补全 {traceability_dir / 'traceability_matrix.json'}")
    print(f"9. 运行 reviewer + scorer，产出 {reviews_dir / 'quality_report.json'} 等质量报告")
    print(f"10. 补全 {testcases_dir / 'testcases.md'}")
    print(
        "8. 执行统一校验："
        f" /usr/bin/python3 {repo_root / 'scripts' / 'validate_outputs.py'} --project-code {project_code}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
