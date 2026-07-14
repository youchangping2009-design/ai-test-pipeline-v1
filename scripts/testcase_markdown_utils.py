#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from typing import Dict, List


TESTCASE_HEADERS = [
    "用例编号",
    "所属模块",
    "所属功能点",
    "用例标题",
    "前置条件",
    "测试步骤",
    "预期结果",
    "优先级",
    "标签",
    "测试类型",
    "备注",
]

PAGE_HEADING_PATTERN = re.compile(r"^#{1,6}\s*页面[:：]\s*(.+?)\s*$")
SECTION_HEADING_PATTERN = re.compile(r"^#{1,6}\s*板块[:：]\s*(.+?)\s*$")


def parse_testcase_document(content: str, strict: bool = True) -> Dict[str, object]:
    lines = content.splitlines()
    current_page: str | None = None
    current_section: str | None = None
    tables: List[Dict[str, object]] = []
    all_rows: List[Dict[str, str]] = []
    page_names: List[str] = []
    section_names: List[str] = []

    idx = 0
    while idx < len(lines):
        raw_line = lines[idx].rstrip()
        stripped = raw_line.strip()

        if not stripped:
            idx += 1
            continue

        page_match = PAGE_HEADING_PATTERN.match(stripped)
        if page_match:
            current_page = page_match.group(1).strip()
            current_section = None
            if current_page:
                page_names.append(current_page)
            idx += 1
            continue

        section_match = SECTION_HEADING_PATTERN.match(stripped)
        if section_match:
            current_section = section_match.group(1).strip()
            if current_section:
                section_names.append(current_section)
            idx += 1
            continue

        if not stripped.startswith("|"):
            idx += 1
            continue

        if idx + 1 >= len(lines):
            if strict:
                raise ValueError(f"第 {idx + 1} 行表格缺少分隔行")
            break

        header_line = lines[idx].rstrip()
        separator_line = lines[idx + 1].rstrip()
        if not separator_line.strip().startswith("|"):
            if strict:
                raise ValueError(f"第 {idx + 2} 行不是合法表格分隔行")
            idx += 1
            continue

        headers = [col.strip() for col in header_line.strip().strip("|").split("|")]
        if headers != TESTCASE_HEADERS:
            if strict:
                raise ValueError(
                    f"表头不匹配。\n期望: {TESTCASE_HEADERS}\n实际: {headers}"
                )
            idx += 1
            continue

        table_rows: List[Dict[str, str]] = []
        row_idx = idx + 2
        while row_idx < len(lines):
            row_line = lines[row_idx].rstrip()
            row_stripped = row_line.strip()
            if not row_stripped:
                break
            if not row_stripped.startswith("|"):
                break
            cols = [col.strip() for col in row_line.strip().strip("|").split("|")]
            if len(cols) != len(TESTCASE_HEADERS):
                if strict:
                    raise ValueError(
                        f"第 {row_idx + 1} 行列数不匹配。期望 {len(TESTCASE_HEADERS)} 列，实际 {len(cols)} 列"
                    )
                break
            row = dict(zip(TESTCASE_HEADERS, cols))
            row["__page_name"] = current_page or ""
            row["__section_name"] = current_section or ""
            table_rows.append(row)
            all_rows.append(row)
            row_idx += 1

        tables.append(
            {
                "page_name": current_page or "",
                "section_name": current_section or "",
                "rows": table_rows,
                "start_line": idx + 1,
            }
        )
        idx = row_idx

    return {
        "tables": tables,
        "rows": all_rows,
        "page_names": list(dict.fromkeys(page_names)),
        "section_names": list(dict.fromkeys(section_names)),
    }


def parse_testcase_rows_as_text(content: str, strict: bool = False) -> Dict[str, str]:
    parsed = parse_testcase_document(content, strict=strict)
    rows = parsed["rows"]
    result: Dict[str, str] = {}
    for row in rows:
        testcase_id = row.get("用例编号", "").strip()
        if not testcase_id:
            continue
        page_name = row.get("__page_name", "").strip()
        section_name = row.get("__section_name", "").strip()
        meta_parts = [part for part in [page_name, section_name] if part]
        result[testcase_id] = " ".join(meta_parts + [str(v) for k, v in row.items() if not k.startswith("__")])
    return result


def parse_testcase_ids_from_content(content: str, strict: bool = False) -> set[str]:
    parsed = parse_testcase_document(content, strict=strict)
    return {
        row.get("用例编号", "").strip()
        for row in parsed["rows"]
        if row.get("用例编号", "").strip()
    }
