#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.testcase_markdown_utils import parse_testcase_document


WEAK_PAGE_NAMES = {
    "",
    "TODO",
    "TEMPLATE",
    "示例页面",
    "默认页面",
    "待补充页面",
    "未识别页面",
}
WEAK_SECTION_NAMES = {
    "",
    "TODO",
    "TEMPLATE",
    "示例板块",
    "默认板块",
    "其他",
    "未分类",
    "待补充板块",
    "未识别板块",
}
WEAK_SECTION_WARNING_NAMES = {
    "添加弹窗",
}


def normalize(value: str) -> str:
    return str(value or "").strip()


def is_weak_name(value: str, weak_names: set[str]) -> bool:
    text = normalize(value)
    if text in weak_names:
        return True
    return text.upper() in weak_names


def validate_grouping(content: str, strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    parsed = parse_testcase_document(content, strict=False)
    tables = parsed.get("tables", [])
    rows = parsed.get("rows", [])

    if not rows:
        warnings.append("testcase 文件没有正式用例行，跳过分组质量判断")
        return errors, warnings
    if not tables:
        message = "testcase 文件未识别到 Markdown 表格"
        (errors if strict else warnings).append(message)
        return errors, warnings

    for table_index, table in enumerate(tables, start=1):
        page_name = normalize(str(table.get("page_name", "")))
        section_name = normalize(str(table.get("section_name", "")))
        table_rows = table.get("rows", [])
        if not table_rows:
            continue
        if is_weak_name(page_name, WEAK_PAGE_NAMES):
            (errors if strict else warnings).append(
                f"第 {table_index} 张表 page_name 弱或缺失: {page_name or '(empty)'}"
            )
        if is_weak_name(section_name, WEAK_SECTION_NAMES):
            (errors if strict else warnings).append(
                f"第 {table_index} 张表 section_name 弱或缺失: {section_name or '(empty)'}"
            )

        row_modules = {
            normalize(str(row.get("所属模块", "")))
            for row in table_rows
            if normalize(str(row.get("所属模块", "")))
        }
        row_features = {
            normalize(str(row.get("所属功能点", "")))
            for row in table_rows
            if normalize(str(row.get("所属功能点", "")))
        }
        if not row_modules:
            (errors if strict else warnings).append(f"第 {table_index} 张表缺少有效所属模块")
        if not row_features:
            (errors if strict else warnings).append(f"第 {table_index} 张表缺少有效所属功能点")

    page_section_pairs = [
        (normalize(str(table.get("page_name", ""))), normalize(str(table.get("section_name", ""))))
        for table in tables
        if table.get("rows")
    ]
    pair_counts = Counter(page_section_pairs)
    for (page_name, section_name), count in pair_counts.items():
        if count > 1:
            warnings.append(f"页面/板块标题重复输出 {count} 次: {page_name} / {section_name}")

    section_counts = Counter(section for _, section in page_section_pairs)
    total_tables = len(page_section_pairs)
    for section_name in WEAK_SECTION_WARNING_NAMES:
        count = section_counts.get(section_name, 0)
        if count >= 3 or (total_tables >= 4 and count / max(total_tables, 1) >= 0.75):
            message = f"大量表格使用弱兜底板块 `{section_name}`: {count}/{total_tables}"
            (errors if strict else warnings).append(message)

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 testcase Markdown 的页面/板块分组质量")
    parser.add_argument("--input", required=True, help="testcases_main.md 或等价 testcase Markdown")
    parser.add_argument("--strict", action="store_true", help="strict 下弱页面/弱板块阻断")
    args = parser.parse_args()

    path = Path(args.input).resolve()
    if not path.exists():
        print(f"testcase 文件不存在: {path}", file=sys.stderr)
        return 1

    errors, warnings = validate_grouping(path.read_text(encoding="utf-8"), strict=args.strict)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        print("testcase grouping 校验失败:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("testcase grouping 校验通过")
    print(f"warnings: {len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
