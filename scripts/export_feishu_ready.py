#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
export_feishu_ready.py

用途：
- 将 structured_prd / testcases / review_record 整理为适合直接贴到飞书文档的 Markdown
- 支持基于工作项自动推断输入路径
- 也支持显式传入文件路径
- `feishu_ready.md` 为派生产物，不作为业务真源
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.testcase_markdown_utils import TESTCASE_HEADERS
from scripts.testcase_markdown_utils import parse_testcase_document

FLOW_TEST_TYPES = {"流程验证", "状态流转", "数据校验"}
FLOW_TYPE_CODES = {"FL", "ST", "DV"}


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


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def extract_type_code(case_id: str) -> Optional[str]:
    parts = case_id.strip().split("-")
    if len(parts) < 2:
        return None

    candidate = parts[-2]
    if candidate in FLOW_TYPE_CODES or candidate in {"FN", "BD", "AB", "PM"}:
        return candidate

    return None


def render_markdown_table(headers: List[str], rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "暂无内容。"

    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "|" + "|".join(["---"] * len(headers)) + "|"
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(row.get(header, "") for header in headers) + " |")
    return "\n".join([header_line, separator_line, *body_lines])


def resolve_work_item_root(repo_root: Path, project_code: str, work_item_id: str) -> Path:
    return repo_root / "assets" / "projects" / project_code / "work_items" / work_item_id


def resolve_traceability_consumer_path(root: Path) -> Path:
    adapter = root / "traceability" / "traceability_adapter.json"
    if adapter.exists():
        return adapter
    return root / "traceability" / "traceability_matrix.json"


def resolve_testcases_consumer_path(root: Path) -> Path:
    main = root / "testcases" / "testcases_main.md"
    if main.exists():
        return main
    return root / "testcases" / "testcases.md"


def resolve_from_work_item(
    repo_root: Path,
    project_code: str,
    work_item_id: str,
) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    root = resolve_work_item_root(repo_root, project_code, work_item_id)
    return (
        root / "manifest.json",
        root / "evidence" / "evidence_inventory.json",
        root / "structured_prd" / "structured_prd.json",
        resolve_traceability_consumer_path(root),
        resolve_testcases_consumer_path(root),
        root / "reviews" / "review_record.md",
        root / "feishu_ready.md",
    )


def extract_review_summary(review_text: str) -> tuple[List[str], str]:
    lines = review_text.splitlines()
    decision_lines: List[str] = []
    issue_table = ""

    in_decision = False
    in_issue = False
    issue_lines: List[str] = []

    for line in lines:
        if line.startswith("## "):
            in_decision = line.strip() == "## 评审结论"
            in_issue = line.strip() == "## 问题清单"
            continue

        if in_decision:
            if line.strip():
                decision_lines.append(line)

        if in_issue and line.strip():
            issue_lines.append(line)

    if issue_lines:
        issue_table = "\n".join(issue_lines)

    return decision_lines, issue_table


def parse_review_issue_rows(review_text: str) -> List[List[str]]:
    lines = review_text.splitlines()
    issue_lines: List[str] = []
    in_issue = False

    for line in lines:
        if line.startswith("## "):
            in_issue = line.strip() == "## 问题清单"
            continue
        if in_issue and line.strip().startswith("|"):
            issue_lines.append(line.strip())

    if len(issue_lines) < 3:
        return []

    rows: List[List[str]] = []
    for line in issue_lines[2:]:
        cols = [col.strip() for col in line.strip("|").split("|")]
        if len(cols) >= 5:
            rows.append(cols[:5])
    return rows


def summarize_structured_prd(data: dict[str, Any]) -> List[str]:
    project_info = data.get("project_info", {})
    requirement_info = data.get("requirement_info", {})
    modules = data.get("modules", [])
    flows = data.get("flows", [])

    summary = [
        f"- 项目编码：{project_info.get('project_code', '') or '待补充'}",
        f"- 项目名称：{project_info.get('project_name', '') or '待补充'}",
        f"- 业务线：{project_info.get('business_line', '') or '待补充'}",
        f"- 需求标题：{requirement_info.get('requirement_title', '') or '待补充'}",
        f"- 模块数量：{len(modules) if isinstance(modules, list) else 0}",
        f"- Flow 数量：{len(flows) if isinstance(flows, list) else 0}",
    ]
    return summary


def summarize_evidence(evidence_data: Optional[dict[str, Any]], traceability_data: Optional[dict[str, Any]]) -> List[str]:
    evidence_count = 0
    needs_confirmation_count = 0
    traceability_count = 0

    if evidence_data:
        evidence_items = evidence_data.get("evidence_items", [])
        if isinstance(evidence_items, list):
            evidence_count = len(evidence_items)
            needs_confirmation_count = sum(
                1
                for item in evidence_items
                if isinstance(item, dict) and item.get("status") == "needs_confirmation"
            )

    if traceability_data:
        records = traceability_data.get("records", [])
        if isinstance(records, list):
            traceability_count = len(records)

    return [
        f"- Evidence 条数：{evidence_count}",
        f"- Traceability 条数：{traceability_count}",
        f"- 待确认证据数：{needs_confirmation_count}",
    ]


def summarize_testcases(rows: List[Dict[str, str]]) -> List[str]:
    flow_cases = 0
    api_cases = 0
    ui_cases = 0
    p0_cases = 0
    for row in rows:
        test_type = row.get("测试类型", "")
        remark = row.get("备注", "")
        type_code = extract_type_code(row.get("用例编号", ""))
        is_flow = (
            test_type == "流程验证"
            or "来源 Flow：" in remark
            or "来源Flow：" in remark
            or type_code == "FL"
        )
        if is_flow:
            flow_cases += 1
        tag_text = row.get("标签", "")
        if "AI-API用例" in tag_text:
            api_cases += 1
        if "AI-UI用例" in tag_text:
            ui_cases += 1
        if row.get("优先级") == "P0":
            p0_cases += 1

    return [
        f"- 用例总数：{len(rows)}",
        f"- 流程型用例数：{flow_cases}",
        f"- AI-API用例数：{api_cases}",
        f"- AI-UI用例数：{ui_cases}",
        f"- P0 用例数：{p0_cases}",
    ]


def is_flow_case(row: Dict[str, str]) -> bool:
    test_type = row.get("测试类型", "")
    remark = row.get("备注", "")
    type_code = extract_type_code(row.get("用例编号", ""))
    return (
        test_type == "流程验证"
        or "来源 Flow：" in remark
        or "来源Flow：" in remark
        or type_code == "FL"
    )


def select_case_columns() -> List[str]:
    return [
        "用例编号",
        "所属模块",
        "所属功能点",
        "用例标题",
        "优先级",
        "标签",
        "测试类型",
        "备注",
    ]


def build_feishu_markdown(
    manifest: Optional[dict[str, Any]],
    evidence_data: Optional[dict[str, Any]],
    structured_prd: Optional[dict[str, Any]],
    traceability_data: Optional[dict[str, Any]],
    testcase_rows: List[Dict[str, str]],
    testcase_raw: str,
    review_text: Optional[str],
    source_paths: Dict[str, Path],
) -> str:
    lines: List[str] = []

    title = "飞书同步稿"
    if manifest and manifest.get("title"):
        title = f"飞书同步稿 - {manifest['title']}"

    lines.append(f"# {title}")
    lines.append("")

    lines.append("## 真源说明")
    lines.append("")
    lines.append("- `structured_prd.md` 是结构化 PRD 真源。")
    lines.append("- `structured_prd.json` 是从 Markdown 编译出的机器投影，用于后续流水线消费。")
    lines.append("- `testcases.md`、`review_record.md` 与本文件都是面向阅读和协作的派生产物。")
    lines.append("- 若发现内容不一致，优先回到 `structured_prd.md` 和对应产出链修正，再重新编译/导出。")
    lines.append("")

    lines.append("## 基本信息")
    lines.append("")
    if manifest:
        lines.append(f"- 项目编码：{manifest.get('project_code', '待补充')}")
        lines.append(f"- 工作项 ID：{manifest.get('work_item_id', '待补充')}")
        lines.append(f"- 标题：{manifest.get('title', '待补充') or '待补充'}")
        lines.append(f"- 需求版本：{manifest.get('requirement_version', '待补充') or '待补充'}")
        lines.append(f"- 状态：{manifest.get('status', '待补充')}")
        lines.append(f"- 创建时间：{manifest.get('created_at', '待补充')}")
    else:
        lines.append("- 未提供 manifest 信息")
    lines.append("")

    if structured_prd:
        lines.append("## Structured PRD 摘要")
        lines.append("")
        lines.extend(summarize_structured_prd(structured_prd))
        lines.append("")

    if evidence_data is not None or traceability_data is not None:
        lines.append("## Evidence / Traceability 摘要")
        lines.append("")
        lines.extend(summarize_evidence(evidence_data, traceability_data))
        lines.append("")

    lines.append("## 测试用例摘要")
    lines.append("")
    lines.extend(summarize_testcases(testcase_rows))
    lines.append("")

    flow_rows = [row for row in testcase_rows if is_flow_case(row)]
    p0_rows = [row for row in testcase_rows if row.get("优先级") == "P0"]
    compact_headers = select_case_columns()

    lines.append("## 流程型用例")
    lines.append("")
    lines.append(render_markdown_table(compact_headers, flow_rows))
    lines.append("")

    lines.append("## P0 用例")
    lines.append("")
    lines.append(render_markdown_table(compact_headers, p0_rows))
    lines.append("")

    lines.append("## 测试用例明细")
    lines.append("")
    lines.append(testcase_raw.strip() if testcase_raw.strip() else "当前暂无测试用例内容。")
    lines.append("")

    lines.append("## 来源文件")
    lines.append("")
    for label, path in source_paths.items():
        lines.append(f"- {label}：`{path}`")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出适合直接贴到飞书文档的 Markdown")
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--manifest", required=False, help="显式指定 manifest.json 路径")
    parser.add_argument("--evidence", required=False, help="显式指定 evidence_inventory.json 路径")
    parser.add_argument("--structured-prd", required=False, help="显式指定 structured_prd.json 路径")
    parser.add_argument("--traceability", required=False, help="显式指定 traceability_matrix.json 路径")
    parser.add_argument("--testcases", required=False, help="显式指定 testcases.md 路径")
    parser.add_argument("--review-record", required=False, help="显式指定 review_record.md 路径")
    parser.add_argument("--output", required=False, help="导出文件路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = get_repo_root()

    manifest_path: Optional[Path] = Path(args.manifest).resolve() if args.manifest else None
    evidence_path: Optional[Path] = Path(args.evidence).resolve() if args.evidence else None
    structured_prd_path: Optional[Path] = Path(args.structured_prd).resolve() if args.structured_prd else None
    traceability_path: Optional[Path] = Path(args.traceability).resolve() if args.traceability else None
    testcases_path: Optional[Path] = Path(args.testcases).resolve() if args.testcases else None
    review_record_path: Optional[Path] = Path(args.review_record).resolve() if args.review_record else None
    output_path: Optional[Path] = Path(args.output).resolve() if args.output else None

    if args.project_code and args.work_item_id:
        try:
            project_code = normalize_project_code(args.project_code)
            work_item_id = normalize_work_item_id(args.work_item_id)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        default_manifest, default_evidence, default_structured, default_traceability, default_testcases, default_review, default_output = (
            resolve_from_work_item(repo_root, project_code, work_item_id)
        )
        manifest_path = manifest_path or default_manifest
        evidence_path = evidence_path or default_evidence
        structured_prd_path = structured_prd_path or default_structured
        traceability_path = traceability_path or default_traceability
        testcases_path = testcases_path or default_testcases
        review_record_path = review_record_path or default_review
        output_path = output_path or default_output

    if not testcases_path:
        print("必须提供 testcase 文件，可通过 --testcases 或 --project-code + --work-item-id 指定。", file=sys.stderr)
        return 1

    if not output_path:
        output_path = (repo_root / "feishu_ready.md").resolve()

    manifest_data: Optional[dict[str, Any]] = None
    evidence_data: Optional[dict[str, Any]] = None
    structured_prd_data: Optional[dict[str, Any]] = None
    traceability_data: Optional[dict[str, Any]] = None
    review_text: Optional[str] = None

    try:
        testcase_raw = read_text(testcases_path)
        testcase_rows = parse_testcase_document(testcase_raw, strict=False)["rows"]
        if manifest_path and manifest_path.exists():
            manifest_data = load_json(manifest_path)
        if evidence_path and evidence_path.exists():
            evidence_data = load_json(evidence_path)
        if structured_prd_path and structured_prd_path.exists():
            structured_prd_data = load_json(structured_prd_path)
        if traceability_path and traceability_path.exists():
            traceability_data = load_json(traceability_path)
        if review_record_path and review_record_path.exists():
            review_text = read_text(review_record_path)
    except Exception as exc:
        print(f"导出失败: {exc}", file=sys.stderr)
        return 1

    source_paths: Dict[str, Path] = {"testcases": testcases_path}
    if manifest_path:
        source_paths["manifest"] = manifest_path
    if evidence_path:
        source_paths["evidence"] = evidence_path
    if structured_prd_path:
        source_paths["structured_prd"] = structured_prd_path
    if traceability_path:
        source_paths["traceability"] = traceability_path
    if review_record_path:
        source_paths["review_record"] = review_record_path

    result = build_feishu_markdown(
        manifest=manifest_data,
        evidence_data=evidence_data,
        structured_prd=structured_prd_data,
        traceability_data=traceability_data,
        testcase_rows=testcase_rows,
        testcase_raw=testcase_raw,
        review_text=review_text,
        source_paths=source_paths,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result, encoding="utf-8")

    print("✅ 飞书文档导出完成")
    print(f"输出文件: {output_path}")
    print(f"测试用例数: {len(testcase_rows)}")
    if manifest_data:
        print(f"工作项: {manifest_data.get('work_item_id', '待补充')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
