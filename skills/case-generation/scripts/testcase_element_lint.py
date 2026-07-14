#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lightweight testcase element notation lint.

The checker intentionally avoids complex NLP. It catches obvious unmarked
page/button/field/prompt expressions and keeps non-strict mode warning-only for
legacy compatibility.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.testcase_markdown_utils import parse_testcase_document


CHECK_FIELDS = ["用例标题", "前置条件", "测试步骤", "预期结果"]


@dataclass
class Finding:
    severity: str
    row_index: int
    case_id: str
    field: str
    message: str
    text: str


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def normalize_cell(text: str) -> str:
    return text.replace("<br>", "。").replace("<br/>", "。").replace("<br />", "。")


def split_clauses(text: str) -> List[str]:
    parts = re.split(r"[。；;\n]+", normalize_cell(text))
    return [part.strip() for part in parts if part.strip()]


def marked_with(text: str, left: str, right: str) -> bool:
    return left in text and right in text


def add_finding(
    findings: List[Finding],
    severity: str,
    row_index: int,
    row: Dict[str, str],
    field: str,
    message: str,
    text: str,
) -> None:
    findings.append(
        Finding(
            severity=severity,
            row_index=row_index,
            case_id=row.get("用例编号", "").strip() or "(unknown)",
            field=field,
            message=message,
            text=text.strip(),
        )
    )


def lint_button_notation(row_index: int, row: Dict[str, str], field: str, text: str, findings: List[Finding]) -> None:
    for clause in split_clauses(text):
        for match in re.finditer(r"点击([^。；;，,]+)", clause):
            target = match.group(1).strip()
            if not target or marked_with(target, "【", "】"):
                continue
            if target.startswith(("目标记录", "该", "其")) and "【" in clause:
                continue
            add_finding(
                findings,
                "error",
                row_index,
                row,
                field,
                "点击动作的操作入口应使用【】标注",
                clause,
            )


def lint_page_tab_notation(row_index: int, row: Dict[str, str], field: str, text: str, findings: List[Finding]) -> None:
    patterns = [
        r"(进入|打开|返回|定位到)([^。；;，,]{1,30}?(?:页|页面))",
        r"(切换到|查看)([^。；;，,]{1,30}?(?:Tab|tab))",
    ]
    for clause in split_clauses(text):
        for pattern in patterns:
            for match in re.finditer(pattern, clause):
                target = match.group(2).strip()
                if marked_with(target, "[", "]") or marked_with(clause, "[", "]"):
                    continue
                if "弹窗" in target or "抽屉" in target or "面板" in target:
                    continue
                add_finding(
                    findings,
                    "error",
                    row_index,
                    row,
                    field,
                    "页面 / Tab 应使用[]标注",
                    clause,
                )


def lint_field_notation(row_index: int, row: Dict[str, str], field: str, text: str, findings: List[Finding]) -> None:
    patterns = [
        r"(填写|选择)([^。；;，,]{1,24})",
        r"(查看|校验|断言)([^。；;，,]{0,24}(?:字段|列表列|列|表单项|筛选项)[^。；;，,]{0,16})",
    ]
    skip_targets = {"其余必填字段", "所有必填字段", "合法字段", "目标记录", "该记录"}
    for clause in split_clauses(text):
        for pattern in patterns:
            for match in re.finditer(pattern, clause):
                target = match.group(2).strip()
                if not target or target in skip_targets:
                    continue
                if marked_with(target, "“", "”") or marked_with(clause, "“", "”"):
                    continue
                if any(keyword in target for keyword in ["图片", "价格", "状态", "类型", "区域", "名称", "排序", "库存", "时长", "字段", "参数"]):
                    add_finding(
                        findings,
                        "error",
                        row_index,
                        row,
                        field,
                        "字段 / 表单项 / 列表列应使用“”标注",
                        clause,
                    )


def lint_prompt_notation(row_index: int, row: Dict[str, str], field: str, text: str, findings: List[Finding]) -> None:
    for clause in split_clauses(text):
        if not re.search(r"(提示|Toast|toast|校验文案|提示语)", clause):
            continue
        if marked_with(clause, "「", "」"):
            continue
        add_finding(
            findings,
            "error",
            row_index,
            row,
            field,
            "提示语 / Toast / 校验文案应使用「」标注",
            clause,
        )


def lint_technical_field_warning(row_index: int, row: Dict[str, str], field: str, text: str, findings: List[Finding]) -> None:
    for clause in split_clauses(text):
        has_technical_context = re.search(r"(接口|字段名|枚举code|技术字段)", clause)
        has_code_like_param = "参数" in clause and re.search(r"[A-Za-z_][A-Za-z0-9_]{2,}", clause)
        if not has_technical_context and not has_code_like_param:
            continue
        if "`" in clause:
            continue
        add_finding(
            findings,
            "warning",
            row_index,
            row,
            field,
            "接口 / 参数 / 技术字段建议使用反引号标注",
            clause,
        )


def lint_dialog_field_ambiguity(row_index: int, row: Dict[str, str], field: str, text: str, findings: List[Finding]) -> None:
    for clause in split_clauses(text):
        if re.search(r"“[^”]*(弹窗|抽屉|面板)[^”]*”", clause):
            add_finding(
                findings,
                "warning",
                row_index,
                row,
                field,
                "弹窗 / 抽屉 / 面板应使用《》，不要与字段“”混用",
                clause,
            )


def lint_over_notation(row_index: int, row: Dict[str, str], field: str, text: str, findings: List[Finding]) -> None:
    suspicious_patterns = [
        (r"\[后台\]", "页面标注疑似过泛，建议标注具体页面"),
        (r"【进行】", "按钮标注疑似过泛，建议标注真实操作入口"),
        (r"《系统》", "弹窗 / 面板标注疑似过泛，建议标注具体容器"),
        (r"“相关内容”", "字段标注疑似过泛，建议标注具体字段"),
    ]
    for pattern, message in suspicious_patterns:
        if re.search(pattern, text):
            add_finding(findings, "warning", row_index, row, field, message, text)


def lint_rows(rows: Iterable[Dict[str, str]]) -> List[Finding]:
    findings: List[Finding] = []
    for row_index, row in enumerate(rows, start=1):
        for field in CHECK_FIELDS:
            text = row.get(field, "")
            if not text.strip():
                continue
            lint_button_notation(row_index, row, field, text, findings)
            lint_page_tab_notation(row_index, row, field, text, findings)
            lint_field_notation(row_index, row, field, text, findings)
            lint_prompt_notation(row_index, row, field, text, findings)
            lint_technical_field_warning(row_index, row, field, text, findings)
            lint_dialog_field_ambiguity(row_index, row, field, text, findings)
            lint_over_notation(row_index, row, field, text, findings)
    return findings


def print_findings(findings: List[Finding], strict: bool) -> None:
    if not findings:
        print("✅ 测试用例元素标注检查通过")
        return

    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    if strict and errors:
        print("❌ 测试用例元素标注检查失败")
    else:
        print("⚠️ 测试用例元素标注检查存在 warning")
    print("-" * 80)
    for item in findings:
        print(
            f"[{item.severity}] 第 {item.row_index} 条 {item.case_id} / {item.field}: "
            f"{item.message} -> {item.text}"
        )
    print("-" * 80)
    print(f"errors={len(errors)}, warnings={len(warnings)}")
    if not strict and errors:
        print("非 strict 模式：以上 error 级问题仅作为 warning 输出，不阻塞旧流程")


def main() -> int:
    parser = argparse.ArgumentParser(description="轻量检查测试用例元素统一标注")
    parser.add_argument("--input", required=True, help="待检查的 testcases_main.md 路径")
    parser.add_argument("--strict", action="store_true", help="将明显未标注问题作为阻塞错误")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    try:
        content = read_text(input_path)
        parsed = parse_testcase_document(content, strict=True)
        rows = parsed["rows"]
    except Exception as exc:
        print(f"读取或解析输入文件失败: {exc}", file=sys.stderr)
        return 1

    if not rows:
        print("✅ 测试用例元素标注检查通过")
        print("当前文件没有真实用例，跳过元素标注检查")
        return 0

    findings = lint_rows(rows)
    print_findings(findings, strict=args.strict)
    if args.strict and any(item.severity == "error" for item in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
