#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.backend_config_utils import BACKEND_CONFIG_PAGES, has_backend_config_family_pages
from scripts.testcase_markdown_utils import parse_testcase_document

REQUIRED_SECTION_TYPES = {
    "filter_area",
    "list_area",
    "action_area",
    "edit_modal",
    "sort_modal",
}

PRIMARY_STRUCTURED_SECTION_TYPES = {
    "edit_modal",
}

PRIMARY_TESTCASE_SECTION_NAMES = {
    "添加弹窗",
}

LIMIT_PATTERNS = {
    "banner": "5条",
    "tile": "4条",
    "icon": "4条",
    "popup": "3条",
}

KEYWORD_RULES = {
    "icon": ["展示企微单人单码", "付费未添加企微用户"],
    "popup": ["展示规则", "每日首次进入小程序"],
}

DELETE_KEYWORDS = ("被引用", "不可删除", "无法删除")
DEFAULT_PATTERNS = ("默认关闭", "默认每日首次进入小程序")
GENERIC_LIST_SKIP = {"", "ID", "操作"}
GENERIC_OPS = {"添加", "编辑", "复用", "复制", "删除", "排序"}
SEMANTIC_TOKEN_SKIP = ("", "无需附加字段", "无附加字段")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(value: str) -> str:
    return "".join(str(value).strip().split())


def read_testcase_context(testcase_path: Path) -> tuple[dict[str, list[dict[str, str]]], dict[str, str]]:
    parsed = parse_testcase_document(testcase_path.read_text(encoding="utf-8"), strict=False)
    section_rows: dict[str, list[dict[str, str]]] = {}
    page_texts: dict[str, list[str]] = {}
    for table in parsed.get("tables", []):
        page_name = str(table.get("page_name", "")).strip()
        section_name = str(table.get("section_name", "")).strip()
        if not page_name or not section_name:
            continue
        key = f"{page_name}::{section_name}"
        rows = table.get("rows", [])
        if rows:
            section_rows.setdefault(key, []).extend(rows)
            page_texts.setdefault(page_name, []).append(
                " ".join(
                    " ".join(str(v) for k, v in row.items() if not k.startswith("__"))
                    for row in rows
                )
            )
    return section_rows, {page: " ".join(chunks) for page, chunks in page_texts.items()}


def build_structured_page_index(structured_prd: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for page in structured_prd.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_name = str(page.get("page_name", "")).strip()
        if page_name:
            index[page_name] = page
    return index


def build_page_structured_text(structured_prd: dict[str, Any], page_name: str) -> str:
    chunks: list[str] = []
    for page in structured_prd.get("pages", []):
        if isinstance(page, dict) and str(page.get("page_name", "")).strip() == page_name:
            chunks.append(json.dumps(page, ensure_ascii=False))
    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        matched_features = [
            feature
            for feature in module.get("features", [])
            if isinstance(feature, dict) and str(feature.get("page_name", "")).strip() == page_name
        ]
        if matched_features:
            chunks.append(
                json.dumps(
                    {
                        "module_name": module.get("module_name"),
                        "features": matched_features,
                    },
                    ensure_ascii=False,
                )
            )
    return " ".join(chunks)


def section_type_index(page: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for section in page.get("sections", []):
        if not isinstance(section, dict):
            continue
        section_type = str(section.get("section_type", "")).strip()
        if section_type:
            index[section_type] = section
    return index


def collect_section_text(section: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in ("section_name", "raw_text", "ocr_text"):
        value = section.get(key)
        if isinstance(value, str) and value.strip():
            chunks.append(value.strip())
    for key in ("visual_elements", "interactive_entries", "section_rules"):
        values = section.get(key, [])
        if isinstance(values, list):
            chunks.extend(str(item).strip() for item in values if str(item).strip())
    for field in section.get("field_candidates", []):
        if not isinstance(field, dict):
            continue
        for key in (
            "display_name",
            "field_name",
            "default_value",
            "data_source",
            "conditional_visibility",
            "conditional_editability",
        ):
            value = field.get(key)
            if isinstance(value, str) and value.strip():
                chunks.append(value.strip())
    for rule in section.get("field_rules", []):
        if not isinstance(rule, dict):
            continue
        for key in ("rule_text", "error_message"):
            value = rule.get(key)
            if isinstance(value, str) and value.strip():
                chunks.append(value.strip())
    for table in section.get("field_rule_tables", []):
        if not isinstance(table, dict):
            continue
        table_name = table.get("table_name")
        if isinstance(table_name, str) and table_name.strip():
            chunks.append(table_name.strip())
        for row in table.get("rows", []):
            if not isinstance(row, dict):
                continue
            for key in ("row_name", "rule_text", "expected_effect"):
                value = row.get(key)
                if isinstance(value, str) and value.strip():
                    chunks.append(value.strip())
    return " ".join(chunks)


def extract_required_list_keywords(section: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    for value in section.get("visual_elements", []):
        text = str(value).strip()
        if text.endswith("列") and len(text) > 1:
            text = text[:-1]
        if text and text not in GENERIC_LIST_SKIP:
            keywords.append(text)
    for field in section.get("field_candidates", []):
        if not isinstance(field, dict):
            continue
        display_name = str(field.get("display_name", "")).strip()
        if display_name.endswith("列") and len(display_name) > 1:
            display_name = display_name[:-1]
        if display_name and display_name not in GENERIC_LIST_SKIP:
            keywords.append(display_name)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in keywords:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def extract_operation_keywords(action_section: dict[str, Any], list_section: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    for section in (action_section, list_section):
        for item in section.get("interactive_entries", []):
            text = str(item).strip()
            if text:
                keywords.append(text.replace("点击", ""))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in keywords:
        if item in GENERIC_OPS and item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def build_section_testcase_text(
    testcase_sections: dict[str, list[dict[str, str]]],
    page_name: str,
    section_names: list[str],
) -> str:
    chunks: list[str] = []
    for section_name in section_names:
        key = f"{page_name}::{section_name}"
        for row in testcase_sections.get(key, []):
            chunks.append(
                " ".join(str(value) for key, value in row.items() if not key.startswith("__"))
            )
    return " ".join(chunks)


def extract_feature_semantic_tokens(feature: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for field in feature.get("field_definitions", []):
        if not isinstance(field, dict):
            continue
        for key in ("display_name", "enum_values", "format_rule"):
            value = field.get(key)
            if isinstance(value, list):
                tokens.extend(str(item).strip() for item in value if str(item).strip())
            else:
                text = str(value).strip()
                if text and text not in SEMANTIC_TOKEN_SKIP:
                    tokens.append(text)
    for rule in feature.get("field_rules", []):
        if not isinstance(rule, dict):
            continue
        value = str(rule.get("rule_text", "")).strip()
        if value and value not in SEMANTIC_TOKEN_SKIP:
            tokens.append(value)
    for table in feature.get("field_rule_tables", []):
        if not isinstance(table, dict):
            continue
        table_name = str(table.get("table_name", "")).strip()
        if table_name:
            tokens.append(table_name)
        for row in table.get("rows", []):
            if not isinstance(row, dict):
                continue
            for key in ("row_name", "rule_text", "expected_effect", "enum_value"):
                value = str(row.get(key, "")).strip()
                if value and value not in SEMANTIC_TOKEN_SKIP:
                    tokens.append(value)
    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = normalize_text(token)
        if normalized and normalized not in seen:
            deduped.append(token)
            seen.add(normalized)
    return deduped


def collect_field_rule_table_binding_checks(
    structured_prd: dict[str, Any],
    page: dict[str, Any],
    page_name: str,
) -> list[tuple[str, list[str], list[str]]]:
    checks: list[tuple[str, list[str], list[str]]] = []
    section_refs: dict[str, set[str]] = {}
    for section in page.get("sections", []):
        if not isinstance(section, dict):
            continue
        section_name = str(section.get("section_name", "")).strip()
        if not section_name:
            continue
        refs = {
            str(item).strip()
            for item in section.get("field_rule_table_refs", [])
            if str(item).strip()
        }
        if refs:
            section_refs[section_name] = refs

    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            if str(feature.get("page_name", "")).strip() != page_name:
                continue
            tables = feature.get("field_rule_tables", [])
            if not tables:
                continue
            for table in tables:
                if not isinstance(table, dict):
                    continue
                table_name = str(table.get("table_name", "")).strip()
                if not table_name:
                    continue
                owner_sections = [
                    section_name
                    for section_name, refs in section_refs.items()
                    if table_name in refs
                ]
                if not owner_sections:
                    continue
                checks.append((table_name, owner_sections, extract_feature_semantic_tokens(feature)))
    return checks


def validate_backend_chain(
    image_evidence: dict[str, Any],
    evidence: dict[str, Any],
    structured_prd: dict[str, Any],
    testcase_path: Path,
) -> list[str]:
    errors: list[str] = []
    structured_pages = build_structured_page_index(structured_prd)
    testcase_sections, testcase_page_texts = read_testcase_context(testcase_path)
    evidence_items = evidence.get("evidence_items", [])
    if not has_backend_config_family_pages(image_evidence):
        return errors

    for image in image_evidence.get("images", []):
        if not isinstance(image, dict):
            continue
        page_name = str(image.get("page_name", "")).strip()
        family = BACKEND_CONFIG_PAGES.get(page_name)
        if not family:
            continue

        image_id = str(image.get("image_id", "")).strip() or page_name
        sections = [section for section in image.get("sections", []) if isinstance(section, dict)]
        image_text = " ".join(collect_section_text(section) for section in sections)
        image_section_types = {str(section.get("section_type", "")).strip() for section in sections}
        structured_page = structured_pages.get(page_name)
        structured_text = build_page_structured_text(structured_prd, page_name)
        page_evidence_text = " ".join(
            f"{item.get('area_name', '')} {item.get('element_name', '')} {item.get('element_text', '')}"
            for item in evidence_items
            if isinstance(item, dict) and str(item.get("page_name", "")).strip() == page_name
        )
        testcase_page_text = testcase_page_texts.get(page_name, "")

        for section_type in sorted(REQUIRED_SECTION_TYPES):
            if section_type not in image_section_types:
                errors.append(f"[后台配置页校验失败] image={image_id} 缺少 section_type: {section_type}")
            if not structured_page:
                continue
            if section_type in PRIMARY_STRUCTURED_SECTION_TYPES and section_type not in section_type_index(structured_page):
                errors.append(f"[后台配置页校验失败] page={page_name} structured_prd 缺少 section_type: {section_type}")

        has_field_rule_table_hint = "说明表" in image_text or "field_rule_table" in image_section_types
        if has_field_rule_table_hint and "field_rule_table" not in image_section_types:
            errors.append(f"[后台配置页校验失败] image={image_id} 存在字段说明表线索但未抽取 field_rule_table")

        list_section = next((section for section in sections if str(section.get("section_type", "")).strip() == "list_area"), {})
        action_section = next((section for section in sections if str(section.get("section_type", "")).strip() == "action_area"), {})
        list_keywords = extract_required_list_keywords(list_section)
        op_keywords = extract_operation_keywords(action_section, list_section)

        for section_name in PRIMARY_TESTCASE_SECTION_NAMES:
            section_key = f"{page_name}::{section_name}"
            if section_key not in testcase_sections:
                errors.append(f"[后台配置页校验失败] page={page_name} testcase 缺少板块承接: {section_name}")

        for required_token in {LIMIT_PATTERNS[family], *KEYWORD_RULES.get(family, [])}:
            normalized = normalize_text(required_token)
            if normalized and normalized not in normalize_text(image_text):
                continue
            if normalized and normalized not in normalize_text(page_evidence_text):
                errors.append(f"[后台配置页校验失败] page={page_name} evidence 未保留关键规则: {required_token}")
            if normalized and normalized not in normalize_text(structured_text):
                errors.append(f"[后台配置页校验失败] page={page_name} structured_prd 未保留关键规则: {required_token}")

        for pattern in DEFAULT_PATTERNS:
            normalized = normalize_text(pattern)
            if normalized in normalize_text(image_text):
                if normalized not in normalize_text(page_evidence_text):
                    errors.append(f"[后台配置页校验失败] page={page_name} evidence 未保留默认值规则: {pattern}")
                if normalized not in normalize_text(structured_text):
                    errors.append(f"[后台配置页校验失败] page={page_name} structured_prd 未保留默认值规则: {pattern}")

        if any(keyword in image_text for keyword in DELETE_KEYWORDS):
            if not any(keyword in page_evidence_text for keyword in DELETE_KEYWORDS):
                errors.append(f"[后台配置页校验失败] page={page_name} evidence 未承接删除/引用限制")
            if not any(keyword in structured_text for keyword in DELETE_KEYWORDS):
                errors.append(f"[后台配置页校验失败] page={page_name} structured_prd 未承接删除/引用限制")

        if structured_page:
            for table_name, owner_sections, semantic_tokens in collect_field_rule_table_binding_checks(
                structured_prd,
                structured_page,
                page_name,
            ):
                owner_section_text = build_section_testcase_text(testcase_sections, page_name, owner_sections)
                if semantic_tokens and owner_section_text:
                    if not any(
                        normalize_text(token) in normalize_text(owner_section_text)
                        for token in semantic_tokens
                    ):
                        joined_sections = " / ".join(owner_sections)
                        errors.append(
                            f"[后台配置页校验失败] page={page_name} testcase 未将字段说明表 `{table_name}` 的语义规则回挂到所属板块: {joined_sections}"
                        )

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验后台配置页家族在 image_evidence/evidence/structured_prd/testcases 间的承接链路")
    parser.add_argument("--image-evidence", required=True, help="image_evidence_inventory.json 路径")
    parser.add_argument("--evidence", required=True, help="evidence_inventory.json 路径")
    parser.add_argument("--structured-prd", required=True, help="structured_prd.json 路径")
    parser.add_argument("--testcases", required=True, help="testcases.md 路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        image_evidence = load_json(Path(args.image_evidence).resolve())
        evidence = load_json(Path(args.evidence).resolve())
        structured_prd = load_json(Path(args.structured_prd).resolve())
        testcase_path = Path(args.testcases).resolve()
    except Exception as exc:
        print(f"读取输入失败: {exc}", file=sys.stderr)
        return 1

    errors = validate_backend_chain(image_evidence, evidence, structured_prd, testcase_path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("Backend config chain validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
