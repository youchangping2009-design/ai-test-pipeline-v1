#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


ROOT_DIR = Path(__file__).resolve().parents[3]
PRIMARY_SCHEMA_PATH = ROOT_DIR / "schemas" / "image_evidence_inventory.schema.json"
SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
REQUIRED_SECTION_TYPES = {"filter_area", "list_area", "action_area", "edit_modal", "sort_modal"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_against_schema(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    if jsonschema is None:
        return []
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return [
        f"Schema校验失败: {'/'.join(map(str, err.path)) or '$'} -> {err.message}"
        for err in errors
    ]


def unique_items(values: list[str]) -> bool:
    return len(values) == len(set(values))


def detect_family(image: dict[str, Any]) -> str:
    page_name = str(image.get("page_name", "")).strip()
    if page_name == "小程序banner配置页":
        return "banner"
    if page_name == "小程序瓷片区配置页":
        return "tile"
    if page_name == "小程序金刚区配置页":
        return "icon"
    if page_name == "小程序弹窗配置页":
        return "popup"
    return ""


def section_text(section: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ["section_name", "raw_text", "ocr_text"]:
        value = section.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    for key in ["visual_elements", "interactive_entries", "section_rules"]:
        values = section.get(key, [])
        if isinstance(values, list):
            parts.extend(str(v).strip() for v in values if str(v).strip())
    for field in section.get("field_candidates", []):
        if isinstance(field, dict):
            parts.extend(
                str(field.get(name, "")).strip()
                for name in [
                    "display_name",
                    "field_name",
                    "data_type",
                    "control_type",
                    "data_source",
                    "conditional_visibility",
                    "conditional_editability",
                    "notes",
                ]
                if str(field.get(name, "")).strip()
            )
    for rule in section.get("field_rules", []):
        if isinstance(rule, dict):
            parts.extend(
                str(rule.get(name, "")).strip()
                for name in ["display_name", "field_name", "rule_text", "error_message", "notes"]
                if str(rule.get(name, "")).strip()
            )
    return " ".join(parts)


def validate_inventory(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    images = data.get("images", [])
    if not isinstance(images, list) or not images:
        return ["业务校验失败: images 不能为空"]

    image_ids = [str(image.get("image_id", "")).strip() for image in images if isinstance(image, dict)]
    if not unique_items([image_id for image_id in image_ids if image_id]):
        errors.append("业务校验失败: image_id 不能重复")

    for image in images:
        if not isinstance(image, dict):
            continue
        image_id = str(image.get("image_id", "")).strip() or "<unknown>"
        family = detect_family(image)
        sections = image.get("sections", [])
        if not isinstance(sections, list) or not sections:
            errors.append(f"业务校验失败: image={image_id} 未抽取到任何 section")
            continue

        section_names = [
            str(section.get("section_name", "")).strip()
            for section in sections
            if isinstance(section, dict) and str(section.get("section_name", "")).strip()
        ]
        if not unique_items(section_names):
            errors.append(f"业务校验失败: image={image_id} section_name 重复")

        section_types = [
            str(section.get("section_type", "")).strip()
            for section in sections
            if isinstance(section, dict)
        ]

        has_list_area = "list_area" in section_types
        has_edit_modal = "edit_modal" in section_types
        has_sort_modal = "sort_modal" in section_types
        has_field_rule_table = "field_rule_table" in section_types

        all_interactions: list[str] = []
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_name = str(section.get("section_name", "")).strip() or "<unknown>"
            section_type = str(section.get("section_type", "")).strip()
            text = section_text(section)
            field_candidates = section.get("field_candidates", [])
            field_rules = section.get("field_rules", [])
            rule_tables = section.get("field_rule_tables", [])
            visual_elements = section.get("visual_elements", [])
            interactive_entries = section.get("interactive_entries", [])
            section_rules = section.get("section_rules", [])

            if isinstance(interactive_entries, list):
                all_interactions.extend(str(item).strip() for item in interactive_entries if str(item).strip())

            if section_type == "list_area":
                if not visual_elements:
                    errors.append(f"业务校验失败: image={image_id} section={section_name} 列表区缺少 visual_elements")
                if not field_candidates and "列" not in text and "操作" not in text:
                    errors.append(f"业务校验失败: image={image_id} section={section_name} 列表区未承接列头或字段")

            if section_type == "edit_modal":
                if not isinstance(field_candidates, list) or not field_candidates:
                    errors.append(f"业务校验失败: image={image_id} section={section_name} 添加/编辑弹窗未抽取字段矩阵")
                for field in field_candidates:
                    if not isinstance(field, dict):
                        continue
                    display_name = str(field.get("display_name", "")).strip() or "<unknown>"
                    field_name = str(field.get("field_name", "")).strip()
                    if field_name and not SNAKE_CASE_PATTERN.match(field_name):
                        errors.append(
                            f"业务校验失败: image={image_id} section={section_name} field={display_name} field_name 不是 snake_case: {field_name}"
                        )
                    for required_key in ["control_type", "required", "editable"]:
                        if required_key not in field:
                            errors.append(
                                f"业务校验失败: image={image_id} section={section_name} field={display_name} 缺少 {required_key}"
                            )
                    if "状态" in display_name and not field.get("enum_values"):
                        errors.append(
                            f"业务校验失败: image={image_id} section={section_name} field={display_name} 缺少 enum_values"
                        )
                    if display_name in {"展示类型", "跳转类型", "触达用户类型"} and not (
                        field.get("enum_values") or field.get("content_values")
                    ):
                        errors.append(
                            f"业务校验失败: image={image_id} section={section_name} field={display_name} 缺少枚举/内容定义"
                        )
                    if field_name in {"selected_activity", "show_tab", "link_url"} and not (
                        field.get("data_source") or field.get("conditional_visibility") or field.get("conditional_editability")
                    ):
                        errors.append(
                            f"业务校验失败: image={image_id} section={section_name} field={display_name} 缺少来源或条件规则"
                        )

            if section_type == "sort_modal" and not section_rules:
                errors.append(f"业务校验失败: image={image_id} section={section_name} 排序弹窗缺少 section_rules")

            if section_type == "field_rule_table":
                if not isinstance(rule_tables, list) or not rule_tables:
                    errors.append(f"业务校验失败: image={image_id} section={section_name} 说明表缺少 field_rule_tables")

            if ("删除" in text or "引用" in text or "无法删除" in text) and not field_rules and not section_rules:
                errors.append(f"业务校验失败: image={image_id} section={section_name} 删除/引用限制未被结构化承接")

        joined_interactions = " ".join(all_interactions)
        image_text = " ".join(section_text(section) for section in sections if isinstance(section, dict))
        if family and not REQUIRED_SECTION_TYPES.issubset(set(section_types)):
            missing = sorted(REQUIRED_SECTION_TYPES - set(section_types))
            errors.append(f"业务校验失败: image={image_id} 后台配置页缺少标准 section_type: {', '.join(missing)}")
        if has_list_area and "编辑" in joined_interactions and not has_edit_modal:
            errors.append(f"业务校验失败: image={image_id} 存在编辑入口但未抽取 edit_modal")
        if has_list_area and "排序" in joined_interactions and not has_sort_modal:
            errors.append(f"业务校验失败: image={image_id} 存在排序入口但未抽取 sort_modal")
        if has_edit_modal and "触达用户类型" in image_text and not has_field_rule_table:
            errors.append(f"业务校验失败: image={image_id} 存在字段说明表线索但未抽取 field_rule_table")

        if family == "tile":
            if "tile_name" not in image_text or "tile_style" not in image_text:
                errors.append(f"业务校验失败: image={image_id} 瓷片区页面缺少 tile_name/tile_style 关键信息")
            if "4条" not in image_text:
                errors.append(f"业务校验失败: image={image_id} 瓷片区页面缺少 4条上限信息")

        if family == "icon":
            if "icon_name" not in image_text or "icon_style" not in image_text:
                errors.append(f"业务校验失败: image={image_id} 金刚区页面缺少 icon_name/icon_style 关键信息")
            if "展示企微单人单码" not in image_text:
                errors.append(f"业务校验失败: image={image_id} 金刚区页面缺少“展示企微单人单码”跳转类型")
            if "付费未添加企微用户" not in image_text:
                errors.append(f"业务校验失败: image={image_id} 金刚区页面缺少“付费未添加企微用户”说明表行")
            if "4条" not in image_text:
                errors.append(f"业务校验失败: image={image_id} 金刚区页面缺少 4条上限信息")

        if family == "banner":
            if "5条" not in image_text:
                errors.append(f"业务校验失败: image={image_id} banner 页面缺少 5条上限信息")

        if family == "popup":
            if "popup_name" not in image_text or "popup_image" not in image_text:
                errors.append(f"业务校验失败: image={image_id} 弹窗页面缺少 popup_name/popup_image 关键信息")
            if "3条" not in image_text:
                errors.append(f"业务校验失败: image={image_id} 弹窗页面缺少 3条上限信息")
            if "展示规则" in image_text and "display_rule" not in image_text:
                errors.append(f"业务校验失败: image={image_id} 弹窗页面出现展示规则但未结构化为 display_rule")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 image_evidence_inventory.json")
    parser.add_argument("--input", required=True, help="image_evidence_inventory.json 路径")
    parser.add_argument("--schema", required=False, help="schema 路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    schema_path = Path(args.schema).resolve() if args.schema else PRIMARY_SCHEMA_PATH

    try:
        data = load_json(input_path)
        schema = load_json(schema_path)
    except Exception as exc:  # pragma: no cover
        print(f"读取文件失败: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    errors.extend(validate_against_schema(data, schema))
    errors.extend(validate_inventory(data))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Image evidence validation passed: {input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
