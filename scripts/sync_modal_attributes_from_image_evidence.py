#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from structured_prd_markdown_utils import normalize_structured_prd


RULE_TYPE_MAP = {
    "required_rule": "required_constraint",
    "enum_rule": "enum_constraint",
    "format_rule": "format_constraint",
    "length_rule": "length_constraint",
    "range_rule": "range_constraint",
    "effect_rule": "effect_constraint",
    "status_rule": "status_constraint",
    "data_source_rule": "data_source_constraint",
    "conditional_visibility_rule": "conditional_visibility_rule",
    "conditional_editability_rule": "conditional_editability_rule",
    "conditional_required_rule": "conditional_required_rule",
}

SYNC_ATTRS = (
    "data_type",
    "control_type",
    "required",
    "editable",
    "default_value",
    "enum_values",
    "content_values",
    "format_rule",
    "length_rule",
    "data_source",
    "conditional_visibility",
    "conditional_editability",
    "required_when",
    "visible_when",
    "editable_when",
    "readonly_when",
    "max_length",
    "min",
    "max",
    "integer_only",
    "formats",
    "max_count",
    "filter",
    "display",
    "order_by",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def next_rule_id(existing_rule_ids: set[str]) -> str:
    idx = 1
    while True:
        candidate = f"FR-SYNC-{idx:03d}"
        if candidate not in existing_rule_ids:
            existing_rule_ids.add(candidate)
            return candidate
        idx += 1


def infer_image_field_extensions(image_field: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}

    conditional_visibility = str(image_field.get("conditional_visibility", "")).strip()
    if conditional_visibility:
        updates["visible_when"] = conditional_visibility

    conditional_editability = str(image_field.get("conditional_editability", "")).strip()
    if conditional_editability:
        if any(keyword in conditional_editability for keyword in ("不可编辑", "只读", "不允许编辑", "仅展示")):
            updates["readonly_when"] = conditional_editability
        else:
            updates["editable_when"] = conditional_editability

    length_rule = str(image_field.get("length_rule", "")).strip()
    length_match = re.search(r"varchar\((\d+)\)", length_rule, re.IGNORECASE)
    if length_match:
        updates["max_length"] = int(length_match.group(1))

    format_rule = str(image_field.get("format_rule", "")).strip()
    if format_rule:
        updates["formats"] = [format_rule]
        range_match = re.search(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]", format_rule)
        if range_match:
            updates["min"] = int(range_match.group(1))
            updates["max"] = int(range_match.group(2))
        if any(keyword in format_rule for keyword in ("整数", "integer", "整型")):
            updates["integer_only"] = True

    data_source = str(image_field.get("data_source", "")).strip()
    if data_source:
        parts = [part.strip() for part in re.split(r"[，,；;]", data_source) if part.strip()]
        filters = [
            part
            for part in parts
            if ("=" in part or ">" in part or "<" in part or "来源于" in part or "来源自" in part)
            and not re.search(r"按.+(序|排序)", part)
        ]
        orders = [part for part in parts if re.search(r"按.+(序|排序)", part)]
        if filters:
            updates["filter"] = filters if len(filters) > 1 else filters[0]
        if orders:
            updates["order_by"] = orders if len(orders) > 1 else orders[0]
        updates["display"] = str(image_field.get("display_name", "")).strip() or data_source

    return updates


def image_modal_field_map(image_evidence: dict[str, Any]) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    mapping: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for image in image_evidence.get("images", []):
        if not isinstance(image, dict):
            continue
        page_name = str(image.get("page_name", "")).strip()
        for section in image.get("sections", []):
            if not isinstance(section, dict):
                continue
            section_name = str(section.get("section_name", "")).strip()
            section_type = str(section.get("section_type", "")).strip()
            if section_type != "edit_modal":
                continue
            field_map: dict[str, dict[str, Any]] = {}
            for field in section.get("field_candidates", []):
                if not isinstance(field, dict):
                    continue
                field_name = str(field.get("field_name", "")).strip()
                if field_name:
                    field_map[field_name] = field
            mapping[(page_name, section_name)] = {
                "fields": field_map,
                "field_rules": section.get("field_rules", []),
            }
    return mapping


def sync_attributes(image_evidence: dict[str, Any], structured_prd: dict[str, Any]) -> tuple[dict[str, Any], int]:
    modal_map = image_modal_field_map(image_evidence)
    existing_rule_ids: set[str] = set()
    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            for field_rule in feature.get("field_rules", []):
                if isinstance(field_rule, dict):
                    rule_id = str(field_rule.get("rule_id", "")).strip()
                    if rule_id:
                        existing_rule_ids.add(rule_id)

    updated_fields = 0
    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            page_name = str(feature.get("page_name", "")).strip()
            section_name = str(feature.get("section_name", "")).strip()
            if (page_name, section_name) not in modal_map:
                continue

            modal_info = modal_map[(page_name, section_name)]
            field_map = modal_info["fields"]
            existing_field_rule_keys = {
                (str(rule.get("field_name", "")).strip(), str(rule.get("rule_text", "")).strip())
                for rule in feature.get("field_rules", [])
                if isinstance(rule, dict)
            }
            existing_field_names = {
                str(field.get("field_name", "")).strip()
                for field in feature.get("field_definitions", [])
                if isinstance(field, dict) and str(field.get("field_name", "")).strip()
            }
            feature.setdefault("fields", [])
            existing_feature_fields = {
                str(field.get("field_name", "")).strip() or str(field.get("name", "")).strip(): field
                for field in feature.get("fields", [])
                if isinstance(field, dict) and (str(field.get("field_name", "")).strip() or str(field.get("name", "")).strip())
            }

            for field in feature.get("field_definitions", []):
                if not isinstance(field, dict):
                    continue
                field_name = str(field.get("field_name", "")).strip()
                image_field = field_map.get(field_name)
                if not image_field:
                    continue
                for attr in SYNC_ATTRS:
                    if attr in image_field:
                        field[attr] = image_field.get(attr)
                field.setdefault("name", field_name)
                field.setdefault("type", field.get("control_type"))
                if "default_value" in field and "default" not in field:
                    field["default"] = field.get("default_value")
                for key, value in infer_image_field_extensions(image_field).items():
                    field.setdefault(key, value)
                updated_fields += 1

                mirrored_field = existing_feature_fields.get(field_name)
                if isinstance(mirrored_field, dict):
                    mirrored_field.update(field)
                else:
                    feature["fields"].append(dict(field))
                    existing_feature_fields[field_name] = feature["fields"][-1]

                for attr_name, rule_type in (
                    ("conditional_visibility", "conditional_visibility_rule"),
                    ("conditional_editability", "conditional_editability_rule"),
                ):
                    rule_text = str(image_field.get(attr_name, "")).strip()
                    if not rule_text:
                        continue
                    key = (field_name, rule_text)
                    if key in existing_field_rule_keys:
                        continue
                    feature.setdefault("field_rules", []).append(
                        {
                            "rule_id": next_rule_id(existing_rule_ids),
                            "field_name": field_name,
                            "display_name": str(field.get("display_name", "")).strip(),
                            "rule_text": rule_text,
                            "rule_type": rule_type,
                            "must_cover": True,
                        }
                    )
                    existing_field_rule_keys.add(key)

            for field_name, image_field in field_map.items():
                if field_name in existing_field_names:
                    continue
                new_field = {
                    "field_name": field_name,
                    "display_name": str(image_field.get("display_name", "")).strip(),
                    "description": str(image_field.get("notes", "")).strip(),
                    "terminal": "ADMIN",
                }
                for attr in SYNC_ATTRS:
                    if attr in image_field:
                        new_field[attr] = image_field.get(attr)
                new_field["name"] = field_name
                new_field["type"] = new_field.get("control_type")
                if "default_value" in new_field:
                    new_field["default"] = new_field.get("default_value")
                for key, value in infer_image_field_extensions(image_field).items():
                    new_field.setdefault(key, value)
                feature.setdefault("field_definitions", []).append(new_field)
                feature.setdefault("fields", []).append(dict(new_field))
                existing_field_names.add(field_name)
                updated_fields += 1

                for attr_name, rule_type in (
                    ("conditional_visibility", "conditional_visibility_rule"),
                    ("conditional_editability", "conditional_editability_rule"),
                ):
                    rule_text = str(image_field.get(attr_name, "")).strip()
                    if not rule_text:
                        continue
                    key = (field_name, rule_text)
                    if key in existing_field_rule_keys:
                        continue
                    feature.setdefault("field_rules", []).append(
                        {
                            "rule_id": next_rule_id(existing_rule_ids),
                            "field_name": field_name,
                            "display_name": str(image_field.get("display_name", "")).strip(),
                            "rule_text": rule_text,
                            "rule_type": rule_type,
                            "must_cover": True,
                        }
                    )
                    existing_field_rule_keys.add(key)

            for image_rule in modal_info.get("field_rules", []):
                if not isinstance(image_rule, dict):
                    continue
                field_name = str(image_rule.get("field_name", "")).strip()
                rule_text = str(image_rule.get("rule_text", "")).strip()
                if not field_name or not rule_text:
                    continue
                key = (field_name, rule_text)
                if key in existing_field_rule_keys:
                    continue
                feature.setdefault("field_rules", []).append(
                    {
                        "rule_id": next_rule_id(existing_rule_ids),
                        "field_name": field_name,
                        "display_name": str(image_rule.get("display_name", "")).strip(),
                        "rule_text": rule_text,
                        "rule_type": RULE_TYPE_MAP.get(str(image_rule.get("rule_type", "")).strip(), "other"),
                        "must_cover": True,
                    }
                )
                existing_field_rule_keys.add(key)

    return normalize_structured_prd(structured_prd), updated_fields


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 image_evidence 的 edit_modal 字段矩阵回填 structured_prd 字段属性")
    parser.add_argument("--image-evidence", required=True, help="image_evidence_inventory.json 路径")
    parser.add_argument("--structured-prd", required=True, help="structured_prd.json 路径")
    parser.add_argument("--write", action="store_true", help="直接覆盖写回 structured_prd 文件")
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

    synced, updated = sync_attributes(image_evidence, structured_prd)
    if args.write:
        write_json(structured_prd_path, synced)
        print(f"已写回 structured_prd: {structured_prd_path}")
    else:
        print(json.dumps(synced, ensure_ascii=False, indent=2))
    print(f"更新字段数: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
