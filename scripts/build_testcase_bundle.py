#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from testcase_markdown_utils import parse_testcase_document


CASE_PLAN_MARKERS = [
    re.compile(r"来源\s*CasePlan[:：]\s*(CP-[0-9]{3,})"),
    re.compile(r"来源\s*计划\s*ID[:：]\s*(CP-[0-9]{3,})"),
    re.compile(r"来源计划ID[:：]\s*(CP-[0-9]{3,})"),
    re.compile(r"case_plan_id\s*=\s*(CP-[0-9]{3,})"),
    re.compile(r"case_plan[:：]\s*(CP-[0-9]{3,})", re.IGNORECASE),
]


def extract_case_plan_ids(remark: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for pattern in CASE_PLAN_MARKERS:
        for match in pattern.finditer(remark or ""):
            value = match.group(1)
            if value not in seen:
                result.append(value)
                seen.add(value)
    return result


def split_tags(value: str) -> list[str]:
    parts = re.split(r"[,，、]", value or "")
    return [part.strip() for part in parts if part.strip()]


def build_bundle(project_code: str, work_item_id: str, testcase_path: Path) -> dict:
    parsed = parse_testcase_document(testcase_path.read_text(encoding="utf-8"), strict=True)
    cases = []
    for row in parsed.get("rows", []):
        remark = str(row.get("备注", "")).strip()
        cases.append(
            {
                "testcase_id": str(row.get("用例编号", "")).strip(),
                "page_name": str(row.get("__page_name", "")).strip(),
                "section_name": str(row.get("__section_name", "")).strip(),
                "module": str(row.get("所属模块", "")).strip(),
                "feature": str(row.get("所属功能点", "")).strip(),
                "title": str(row.get("用例标题", "")).strip(),
                "preconditions": str(row.get("前置条件", "")).strip(),
                "steps": str(row.get("测试步骤", "")).strip(),
                "expected_results": str(row.get("预期结果", "")).strip(),
                "priority": str(row.get("优先级", "")).strip(),
                "tags": split_tags(str(row.get("标签", "")).strip()),
                "test_type": str(row.get("测试类型", "")).strip(),
                "remark": remark,
                "source_case_plan_ids": extract_case_plan_ids(remark),
            }
        )
    return {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "truth_source": "testcases/testcases_main.md",
        "projection_only": True,
        "generated_from": ["testcases/testcases_main.md"],
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="从 testcases_main.md 派生 testcase_bundle.json 投影")
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--testcases", required=True, help="testcases_main.md 路径")
    parser.add_argument("--output", required=True, help="testcase_bundle.json 输出路径")
    args = parser.parse_args()

    testcase_path = Path(args.testcases).resolve()
    output_path = Path(args.output).resolve()
    bundle = build_bundle(args.project_code.strip().upper(), args.work_item_id.strip().upper(), testcase_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"testcase_bundle written: {output_path}")
    print(f"case_count: {len(bundle['cases'])}")
    print("truth_source: testcases/testcases_main.md")
    print("projection_only: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
