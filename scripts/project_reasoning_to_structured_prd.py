#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from structured_prd_markdown_utils import normalize_structured_prd
from structured_prd_markdown_utils import render_structured_prd_markdown


ROOT = Path(__file__).resolve().parents[1]


TARGET_FIELDS = {"display_day_x", "selected_activity", "link_url"}


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_condition_text(text: str, field_name: str, display_name: str) -> str:
    raw = str(text).strip()
    if not raw:
        return ""
    patterns = [
        r"(展示类型=.*?时(?:展示|配置))",
        r"(跳转类型=.*?时展示)",
        r"(活动中心场景只展示.*?不允许编辑(?:链接)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            return match.group(1).strip("；。 ")
    prefixes = [
        f"{display_name}在",
        f"{field_name}在",
        f"{display_name}",
        f"{field_name}",
    ]
    cleaned = raw
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip("：:，, ")
    return cleaned.strip("；。 ")


def is_field_specific_text(text: str, field_name: str, display_name: str) -> bool:
    stripped = str(text).strip()
    prefixes = [
        f"{display_name}在",
        f"{display_name}为",
        f"{display_name} ",
        f"{field_name}在",
        f"{field_name}=",
        f"{field_name} ",
    ]
    return any(stripped.startswith(prefix) for prefix in prefixes)


def infer_required_when(field_constraint: dict[str, Any]) -> str:
    normalized = field_constraint.get("normalized_constraints", {})
    display_name = str(field_constraint.get("display_name", "")).strip()
    field_name = str(field_constraint.get("field_name", "")).strip()

    candidate_values = []
    if normalized.get("required_when") not in ("", None):
        candidate_values.append(str(normalized.get("required_when")))
    if normalized.get("visible_when") not in ("", None):
        candidate_values.append(str(normalized.get("visible_when")))
    for text in field_constraint.get("raw_rule_texts", []):
        if (
            ("时展示" in text or "时配置" in text)
            and ("必填" in text or "必选" in text)
            and is_field_specific_text(text, field_name, display_name)
        ):
            candidate_values.append(str(text))
    for text in field_constraint.get("raw_rule_texts", []):
        if ("时展示" in text or "时配置" in text) and is_field_specific_text(text, field_name, display_name):
            candidate_values.append(str(text))

    for value in candidate_values:
        cleaned = clean_condition_text(value, field_name, display_name)
        if "时" in cleaned:
            return cleaned
    return ""


def infer_visible_when(field_constraint: dict[str, Any]) -> str:
    normalized = field_constraint.get("normalized_constraints", {})
    display_name = str(field_constraint.get("display_name", "")).strip()
    field_name = str(field_constraint.get("field_name", "")).strip()
    candidates = []
    if normalized.get("visible_when") not in ("", None):
        candidates.append(str(normalized.get("visible_when")))
    for text in field_constraint.get("raw_rule_texts", []):
        if ("时展示" in text or "时配置" in text) and is_field_specific_text(text, field_name, display_name):
            candidates.append(str(text))
    for value in candidates:
        cleaned = clean_condition_text(value, field_name, display_name)
        if "时" in cleaned:
            return cleaned
    return ""


def infer_readonly_when(field_constraint: dict[str, Any]) -> str:
    normalized = field_constraint.get("normalized_constraints", {})
    display_name = str(field_constraint.get("display_name", "")).strip()
    field_name = str(field_constraint.get("field_name", "")).strip()
    candidates = []
    if normalized.get("readonly_when") not in ("", None):
        candidates.append(str(normalized.get("readonly_when")))
    for text in field_constraint.get("raw_rule_texts", []):
        if "不允许编辑" in text or "不可编辑" in text or "只展示" in text:
            candidates.append(str(text))
    for value in candidates:
        cleaned = clean_condition_text(value, field_name, display_name)
        if cleaned:
            return cleaned
    return ""


def find_feature(data: dict[str, Any], module_name: str, feature_name: str) -> dict[str, Any] | None:
    for module in data.get("modules", []):
        if module.get("module_name") != module_name:
            continue
        for feature in module.get("features", []):
            if feature.get("feature_name") == feature_name:
                return feature
    return None


def build_field_index(feature: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for field in feature.get("fields", []):
        if isinstance(field, dict) and field.get("field_name"):
            index[str(field["field_name"]).strip()] = field
    for field in feature.get("field_definitions", []):
        if isinstance(field, dict) and field.get("field_name"):
            index.setdefault(str(field["field_name"]).strip(), field)
    return index


def upsert_rule(feature: dict[str, Any], new_rule: dict[str, Any]) -> None:
    rules = feature.setdefault("rules", [])
    new_name = str(new_rule.get("name", "")).strip()
    field_name = str(new_rule.get("field_name", "")).strip()
    rule_type = str(new_rule.get("rule_type", "")).strip()
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        if new_name and rule.get("name") == new_name:
            rules[index] = new_rule
            return
        if (
            field_name
            and rule.get("field_name") == field_name
            and rule.get("rule_type") == rule_type
        ):
            rules[index] = new_rule
            return
    rules.append(new_rule)


def remove_placeholder_data_source_rules(feature: dict[str, Any], field_name: str) -> None:
    rules = []
    for rule in feature.get("rules", []):
        if not isinstance(rule, dict):
            rules.append(rule)
            continue
        if (
            rule.get("field_name") == field_name
            and rule.get("rule_type") == "data_source_constraint"
            and all(rule.get(key) in ("", None, []) for key in ("data_source", "filter", "order_by"))
        ):
            continue
        rules.append(rule)
    feature["rules"] = rules


def remove_field_rule_type(feature: dict[str, Any], field_name: str, rule_type: str) -> None:
    rules = []
    for rule in feature.get("rules", []):
        if isinstance(rule, dict) and rule.get("field_name") == field_name and rule.get("rule_type") == rule_type:
            continue
        rules.append(rule)
    feature["rules"] = rules


def matching_data_source_rules(
    reasoning_pack: dict[str, Any],
    page_name: str,
    field_name: str,
    display_name: str,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for rule in reasoning_pack.get("data_source_rules", []):
        if rule.get("page_name") != page_name:
            continue
        text = str(rule.get("statement", ""))
        if display_name and display_name in text:
            matches.append(rule)
            continue
        if field_name and field_name in text:
            matches.append(rule)
    return matches


def apply_field_projection(
    feature: dict[str, Any],
    field: dict[str, Any],
    field_constraint: dict[str, Any],
    data_source_rules: list[dict[str, Any]],
) -> None:
    field_name = str(field.get("field_name", "")).strip()
    display_name = str(field.get("display_name", "")).strip() or field_name
    normalized = field_constraint.get("normalized_constraints", {})

    visible_when = infer_visible_when(field_constraint)
    required_when = infer_required_when(field_constraint)
    readonly_when = infer_readonly_when(field_constraint)

    if field_name == "display_day_x":
        remove_field_rule_type(feature, field_name, "conditional_visibility")
        remove_field_rule_type(feature, field_name, "conditional_required")
        if visible_when:
            field["visible_when"] = visible_when
            field["conditional_visibility"] = visible_when
        if required_when:
            field["required_when"] = required_when
        if normalized.get("min") is not None:
            field["min"] = normalized.get("min")
        if normalized.get("max") is not None:
            field["max"] = normalized.get("max")
        if normalized.get("integer_only") is not None:
            field["integer_only"] = normalized.get("integer_only")
        field["required"] = True
        upsert_rule(
            feature,
            {
                "name": f"{field_name}_conditional_required",
                "rule_type": "conditional_required",
                "field_name": field_name,
                "required_when": required_when or visible_when,
                "rule_text": required_when or visible_when,
            },
        )
        upsert_rule(
            feature,
            {
                "name": f"{field_name}_value_constraint",
                "rule_type": "value_constraint",
                "field_name": field_name,
                "min": field.get("min"),
                "max": field.get("max"),
                "integer_only": field.get("integer_only"),
                "formats": field.get("formats", []),
                "rule_text": f"{field_name}; value_constraint; min={field.get('min')}; max={field.get('max')}; integer_only={field.get('integer_only')}",
            },
        )
        remove_placeholder_data_source_rules(feature, field_name)

    if field_name == "selected_activity":
        remove_field_rule_type(feature, field_name, "data_source_constraint")
        remove_field_rule_type(feature, field_name, "conditional_visibility")
        remove_field_rule_type(feature, field_name, "conditional_required")
        if visible_when:
            field["visible_when"] = visible_when
            field["conditional_visibility"] = visible_when
        if required_when:
            field["required_when"] = required_when
        field["required"] = True
        meaningful_rule = next(
            (
                rule
                for rule in data_source_rules
                if rule.get("filters") or rule.get("order_by") or rule.get("data_source")
            ),
            None,
        )
        if meaningful_rule:
            if meaningful_rule.get("data_source"):
                field["data_source"] = meaningful_rule.get("data_source")
            if meaningful_rule.get("filters"):
                field["filter"] = meaningful_rule.get("filters")
            if meaningful_rule.get("order_by"):
                order_by = meaningful_rule.get("order_by")
                field["order_by"] = order_by[0] if isinstance(order_by, list) and len(order_by) == 1 else order_by
        upsert_rule(
            feature,
            {
                "name": f"{field_name}_conditional_required",
                "rule_type": "conditional_required",
                "field_name": field_name,
                "required_when": required_when or visible_when,
                "rule_text": required_when or visible_when,
            },
        )
        upsert_rule(
            feature,
            {
                "name": f"{field_name}_data_source_constraint",
                "rule_type": "data_source_constraint",
                "field_name": field_name,
                "data_source": field.get("data_source"),
                "filter": field.get("filter"),
                "order_by": field.get("order_by"),
                "display": display_name,
                "rule_text": f"{field_name}; data_source_constraint; data_source={field.get('data_source')}; filter={field.get('filter')}; order_by={field.get('order_by')}",
            },
        )

    if field_name == "link_url":
        remove_field_rule_type(feature, field_name, "conditional_visibility")
        remove_field_rule_type(feature, field_name, "conditional_required")
        remove_field_rule_type(feature, field_name, "conditional_readonly")
        if visible_when:
            field["visible_when"] = visible_when
            field["conditional_visibility"] = visible_when
        if required_when:
            field["required_when"] = required_when
        if readonly_when:
            field["readonly_when"] = readonly_when
            field["conditional_editability"] = readonly_when
        if normalized.get("max_length") is not None:
            field["max_length"] = normalized.get("max_length")
        field["required"] = True
        upsert_rule(
            feature,
            {
                "name": f"{field_name}_conditional_required",
                "rule_type": "conditional_required",
                "field_name": field_name,
                "required_when": required_when or visible_when,
                "rule_text": required_when or visible_when,
            },
        )
        if readonly_when:
            upsert_rule(
                feature,
                {
                    "name": f"{field_name}_conditional_readonly",
                    "rule_type": "conditional_readonly",
                    "field_name": field_name,
                    "readonly_when": readonly_when,
                    "rule_text": readonly_when,
                },
            )
        upsert_rule(
            feature,
            {
                "name": f"{field_name}_value_constraint",
                "rule_type": "value_constraint",
                "field_name": field_name,
                "max_length": field.get("max_length"),
                "rule_text": f"{field_name}; value_constraint; max_length={field.get('max_length')}",
            },
        )
        remove_placeholder_data_source_rules(feature, field_name)


def apply_reasoning_projection(data: dict[str, Any], reasoning_pack: dict[str, Any]) -> dict[str, Any]:
    projected = json.loads(json.dumps(data, ensure_ascii=False))

    field_constraints = [
        item
        for item in reasoning_pack.get("field_constraints", [])
        if item.get("field_name") in TARGET_FIELDS
    ]
    page_to_module = {
        "小程序banner配置页": "小程序banner配置",
        "小程序瓷片区配置页": "小程序瓷片区配置",
        "小程序金刚区配置页": "小程序金刚区配置",
        "小程序弹窗配置页": "小程序弹窗配置",
    }
    page_to_feature = {
        "小程序banner配置页": "banner配置录入与状态字段",
        "小程序瓷片区配置页": "瓷片区配置录入与状态字段",
        "小程序金刚区配置页": "金刚区配置录入与状态字段",
        "小程序弹窗配置页": "弹窗配置录入与状态字段",
    }

    for constraint in field_constraints:
        page_name = str(constraint.get("page_name", "")).strip()
        module_name = page_to_module.get(page_name)
        feature_name = page_to_feature.get(page_name)
        if not module_name or not feature_name:
            continue
        feature = find_feature(projected, module_name, feature_name)
        if not feature:
            continue
        field_index = build_field_index(feature)
        field_name = str(constraint.get("field_name", "")).strip()
        field = field_index.get(field_name)
        if not field:
            continue
        ds_rules = matching_data_source_rules(
            reasoning_pack,
            page_name=page_name,
            field_name=field_name,
            display_name=str(constraint.get("display_name", "")).strip(),
        )
        apply_field_projection(feature, field, constraint, ds_rules)

    return normalize_structured_prd(projected)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 reasoning_pack 投影到 structured_prd 规则层")
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--structured-prd", required=False, help="structured_prd.json 路径")
    parser.add_argument("--reasoning-pack", required=False, help="reasoning_pack.json 路径")
    parser.add_argument("--output-json", required=False, help="输出 structured_prd.json 路径")
    parser.add_argument("--output-md", required=False, help="输出 structured_prd.md 路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.project_code and args.work_item_id:
        item_root = resolve_work_item_root(normalize_code(args.project_code), normalize_code(args.work_item_id))
        structured_prd_path = Path(args.structured_prd).resolve() if args.structured_prd else item_root / "structured_prd" / "structured_prd.json"
        reasoning_pack_path = Path(args.reasoning_pack).resolve() if args.reasoning_pack else item_root / "analysis" / "reasoning_pack.json"
        output_json = Path(args.output_json).resolve() if args.output_json else structured_prd_path
        output_md = Path(args.output_md).resolve() if args.output_md else item_root / "structured_prd" / "structured_prd.md"
    else:
        if not args.structured_prd or not args.reasoning_pack or not args.output_json:
            raise SystemExit("必须提供 --project-code + --work-item-id，或显式提供 --structured-prd --reasoning-pack --output-json")
        structured_prd_path = Path(args.structured_prd).resolve()
        reasoning_pack_path = Path(args.reasoning_pack).resolve()
        output_json = Path(args.output_json).resolve()
        output_md = Path(args.output_md).resolve() if args.output_md else None

    structured_prd = load_json(structured_prd_path)
    reasoning_pack = load_json(reasoning_pack_path)
    projected = apply_reasoning_projection(structured_prd, reasoning_pack)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_json, projected)
    if output_md:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_structured_prd_markdown(projected), encoding="utf-8")

    print(f"structured_prd: {output_json}")
    if output_md:
        print(f"structured_prd_markdown: {output_md}")
    print("projection_fields: display_day_x, selected_activity, link_url")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
