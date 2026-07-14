#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from testcase_markdown_utils import TESTCASE_HEADERS, parse_testcase_document


DEV_SELF_TAG = "开发必测"


def split_tags(value: str) -> list[str]:
    parts = re.split(r"[,，、]", value or "")
    return [part.strip() for part in parts if part.strip()]


def markdown_row(row: dict[str, Any]) -> str:
    values = [str(row.get(header, "")).strip() for header in TESTCASE_HEADERS]
    return "| " + " | ".join(values) + " |"


def render_table(rows: list[dict[str, Any]]) -> list[str]:
    return [
        "| " + " | ".join(TESTCASE_HEADERS) + " |",
        "| " + " | ".join(["---"] * len(TESTCASE_HEADERS)) + " |",
        *[markdown_row(row) for row in rows],
    ]


def build_dev_self_markdown(testcase_path: Path) -> tuple[str, int]:
    parsed = parse_testcase_document(testcase_path.read_text(encoding="utf-8"), strict=True)
    lines: list[str] = ["# 开发自测用例", ""]
    total = 0

    for table in parsed.get("tables", []):
        if not isinstance(table, dict):
            continue
        rows = [
            row
            for row in table.get("rows", [])
            if isinstance(row, dict) and DEV_SELF_TAG in split_tags(str(row.get("标签", "")))
        ]
        if not rows:
            continue

        page_name = str(table.get("page_name", "")).strip()
        section_name = str(table.get("section_name", "")).strip()
        if page_name:
            lines.extend([f"# 页面：{page_name}", ""])
        if section_name:
            lines.extend([f"## 板块：{section_name}", ""])
        lines.extend(render_table(rows))
        lines.append("")
        total += len(rows)

    if total == 0:
        lines.extend(["暂无开发必测用例。", ""])

    return "\n".join(lines).rstrip() + "\n", total


def main() -> int:
    parser = argparse.ArgumentParser(description="从 testcases_main.md 派生开发自测用例 Markdown")
    parser.add_argument("--testcases", required=True, help="testcases_main.md 路径")
    parser.add_argument("--output", required=True, help="dev_self_testcases.md 输出路径")
    args = parser.parse_args()

    testcase_path = Path(args.testcases).resolve()
    output_path = Path(args.output).resolve()
    markdown, count = build_dev_self_markdown(testcase_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"dev_self_testcases written: {output_path}")
    print(f"case_count: {count}")
    print("truth_source: testcases/testcases_main.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
