#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LOW_SIGNAL_SECTION_TYPES = {
    "filter_area",
    "list_area",
    "action_area",
    "sort_modal",
    "tab_area",
    "popup_area",
    "field_rule_table",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(value: str) -> str:
    return "".join(str(value).strip().lower().split())


def build_feature_index(structured_prd: dict[str, Any]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            page_name = str(feature.get("page_name", "")).strip()
            section_name = str(feature.get("section_name", "")).strip()
            index.setdefault((page_name, section_name, module_name), []).append(feature)
    return index


def build_module_feature_name_index(structured_prd: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            feature_name = str(feature.get("feature_name", "")).strip()
            if module_name and feature_name:
                index[(module_name, feature_name)] = feature
    return index


def build_page_section_index(structured_prd: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for page in structured_prd.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_name = str(page.get("page_name", "")).strip()
        for section in page.get("sections", []):
            if not isinstance(section, dict):
                continue
            section_name = str(section.get("section_name", "")).strip()
            index[(page_name, section_name)] = section
    return index


def candidate_features(
    feature_index: dict[tuple[str, str, str], list[dict[str, Any]]],
    page_name: str,
    section_name: str,
    module_name: str,
) -> list[dict[str, Any]]:
    direct = feature_index.get((page_name, section_name, module_name), [])
    if direct:
        return direct
    fallback: list[dict[str, Any]] = []
    for (page, section, _module), features in feature_index.items():
        if page == page_name and section == section_name:
            fallback.extend(features)
    return fallback


def validate_mapping(image_evidence: dict[str, Any], structured_prd: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    page_section_index = build_page_section_index(structured_prd)
    feature_index = build_feature_index(structured_prd)
    module_feature_name_index = build_module_feature_name_index(structured_prd)
    full_structured_text = normalize_text(json.dumps(structured_prd, ensure_ascii=False))

    for image in image_evidence.get("images", []):
        if not isinstance(image, dict):
            continue
        page_name = str(image.get("page_name", "")).strip()
        image_id = str(image.get("image_id", "")).strip() or "<unknown>"
        if page_name and not any(page_name == str(page.get("page_name", "")).strip() for page in structured_prd.get("pages", [])):
            errors.append(f"[映射校验失败] image={image_id} page 未在 structured_prd.pages 中承接: {page_name}")

        for section in image.get("sections", []):
            if not isinstance(section, dict):
                continue
            section_name = str(section.get("section_name", "")).strip()
            section_type = str(section.get("section_type", "")).strip()
            has_page_section = (page_name, section_name) in page_section_index
            if (
                section_type != "other"
                and not has_page_section
                and section_type not in LOW_SIGNAL_SECTION_TYPES
            ):
                errors.append(
                    f"[映射校验失败] image={image_id} section 未在 structured_prd.pages 中承接: page={page_name}, section={section_name}"
                )
                continue

            module_name = ""
            feature_names: list[str] = []
            if has_page_section:
                section_node = page_section_index[(page_name, section_name)]
                module_name = str(section_node.get("module_name", "")).strip()
                feature_names = [str(item).strip() for item in section_node.get("feature_names", []) if str(item).strip()]

            features = candidate_features(feature_index, page_name, section_name, module_name)
            if not features and module_name and feature_names:
                features = [
                    module_feature_name_index[(module_name, feature_name)]
                    for feature_name in feature_names
                    if (module_name, feature_name) in module_feature_name_index
                ]
            feature_text = normalize_text(
                " ".join(
                    " ".join(
                        str(value)
                        for key, value in feature.items()
                        if key not in {"actors", "entry_conditions", "dependencies"}
                    )
                    for feature in features
                )
            )
            target_text = feature_text or full_structured_text
            section_text = normalize_text(json.dumps(section, ensure_ascii=False))

            for field in section.get("field_candidates", []):
                if not isinstance(field, dict):
                    continue
                control_type = str(field.get("control_type", "")).strip()
                if section_type == "filter_area":
                    continue
                if section_type == "list_area" and control_type == "table_column":
                    continue
                display_name = str(field.get("display_name", "")).strip()
                field_name = str(field.get("field_name", "")).strip()
                if not display_name and not field_name:
                    continue
                if normalize_text(display_name or field_name) not in target_text and normalize_text(field_name or display_name) not in target_text:
                    errors.append(
                        f"[映射校验失败] image={image_id} section={section_name} field 未在 structured_prd feature 中承接: {display_name or field_name}"
                    )

            for rule in section.get("field_rules", []):
                if not isinstance(rule, dict):
                    continue
                rule_text = str(rule.get("rule_text", "")).strip()
                display_name = str(rule.get("display_name", "")).strip()
                rule_target_text = full_structured_text if section_type == "other" else target_text
                if rule_text and normalize_text(rule_text) not in rule_target_text and normalize_text(display_name) not in rule_target_text:
                    errors.append(
                        f"[映射校验失败] image={image_id} section={section_name} field_rule 未在 structured_prd 中承接: {rule_text}"
                    )

            for table in section.get("field_rule_tables", []):
                if not isinstance(table, dict):
                    continue
                table_name = str(table.get("table_name", "")).strip()
                if section_type == "field_rule_table" and not features:
                    continue
                if table_name and normalize_text(table_name) not in target_text:
                    errors.append(
                        f"[映射校验失败] image={image_id} section={section_name} field_rule_table 未在 structured_prd 中承接: {table_name}"
                    )
                for row in table.get("rows", []):
                    if not isinstance(row, dict):
                        continue
                    row_name = str(row.get("row_name", "")).strip()
                    rule_text = str(row.get("rule_text", "")).strip()
                    if (
                        row_name
                        and normalize_text(row_name) not in target_text
                        and (rule_text and normalize_text(rule_text) not in target_text)
                        and normalize_text(table_name) not in target_text
                    ):
                        errors.append(
                            f"[映射校验失败] image={image_id} section={section_name} field_rule_table row 未在 structured_prd 中承接: {row_name}"
                        )

            if section_type == "other":
                if "删除" in section_text or "引用" in section_text or "无法删除" in section_text:
                    if "删除" not in json.dumps(structured_prd, ensure_ascii=False) and "引用" not in json.dumps(structured_prd, ensure_ascii=False):
                        errors.append(
                            f"[映射校验失败] image={image_id} 便签/补充规则未在 structured_prd 中承接: {section_name}"
                        )

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 image_evidence_inventory 与 structured_prd 的映射关系")
    parser.add_argument("--image-evidence", required=True, help="image_evidence_inventory.json 路径")
    parser.add_argument("--structured-prd", required=True, help="structured_prd.json 路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_evidence_path = Path(args.image_evidence).resolve()
    structured_prd_path = Path(args.structured_prd).resolve()

    try:
        image_evidence = load_json(image_evidence_path)
        structured_prd = load_json(structured_prd_path)
    except Exception as exc:
        print(f"读取输入失败: {exc}", file=sys.stderr)
        return 1

    errors = validate_mapping(image_evidence, structured_prd)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(
        "Image evidence to structured PRD mapping validation passed: "
        f"{image_evidence_path} -> {structured_prd_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
