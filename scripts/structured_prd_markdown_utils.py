from __future__ import annotations

import copy
import json
import re
from typing import Any

try:
    from backend_config_utils import classify_backend_config_field
except ImportError:  # pragma: no cover
    from scripts.backend_config_utils import classify_backend_config_field


TOP_LEVEL_SECTIONS = [
    "project_info",
    "requirement_info",
    "pages",
    "modules",
    "flows",
]


class StructuredPrdMarkdownError(ValueError):
    pass


def _strip_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _looks_readonly(condition_text: str) -> bool:
    return any(keyword in condition_text for keyword in ("不可编辑", "只读", "不允许编辑", "仅展示"))


def _infer_max_length(length_rule: str) -> int | None:
    if not length_rule:
        return None
    patterns = [
        r"varchar\((\d+)\)",
        r"最多(\d+)位",
        r"最大长度(?:为)?(\d+)",
        r"长度(?:不超过|<=?)(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, length_rule, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _infer_numeric_constraints(format_rule: str) -> dict[str, Any]:
    if not format_rule:
        return {}

    inferred: dict[str, Any] = {}
    range_match = re.search(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]", format_rule)
    if range_match:
        inferred["min"] = int(range_match.group(1))
        inferred["max"] = int(range_match.group(2))

    if any(keyword in format_rule for keyword in ("整数", "integer", "整型")):
        inferred["integer_only"] = True

    return inferred


def _infer_filter_and_order(field: dict[str, Any]) -> None:
    data_source = _strip_string(field.get("data_source"))
    if not data_source:
        return

    parts = [part.strip() for part in re.split(r"[，,；;]", data_source) if part.strip()]
    if not parts:
        return

    if "filter" not in field:
        filters = [
            part
            for part in parts
            if ("=" in part or ">" in part or "<" in part or "包含" in part or "来源于" in part or "来源自" in part)
            and not re.search(r"按.+(序|排序)", part)
        ]
        if filters:
            field["filter"] = filters if len(filters) > 1 else filters[0]

    if "order_by" not in field:
        orders = [part for part in parts if re.search(r"按.+(序|排序)", part)]
        if orders:
            field["order_by"] = orders if len(orders) > 1 else orders[0]


def _normalize_field(field: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(field)

    name = _strip_string(normalized.get("name"))
    field_name = _strip_string(normalized.get("field_name"))
    canonical_name = name or field_name
    if canonical_name:
        normalized["name"] = canonical_name
        normalized["field_name"] = canonical_name

    control_type = _strip_string(normalized.get("control_type"))
    short_type = _strip_string(normalized.get("type"))
    canonical_type = short_type or control_type
    if canonical_type:
        normalized["type"] = canonical_type
        normalized["control_type"] = canonical_type

    if "default" in normalized and "default_value" not in normalized:
        normalized["default_value"] = normalized.get("default")
    if "default_value" in normalized and "default" not in normalized:
        normalized["default"] = normalized.get("default_value")

    conditional_visibility = _strip_string(normalized.get("conditional_visibility"))
    if conditional_visibility and "visible_when" not in normalized:
        normalized["visible_when"] = conditional_visibility

    conditional_editability = _strip_string(normalized.get("conditional_editability"))
    if conditional_editability and "editable_when" not in normalized and "readonly_when" not in normalized:
        if _looks_readonly(conditional_editability):
            normalized["readonly_when"] = conditional_editability
        else:
            normalized["editable_when"] = conditional_editability

    length_rule = _strip_string(normalized.get("length_rule"))
    if "max_length" not in normalized:
        inferred_max_length = _infer_max_length(length_rule)
        if inferred_max_length is not None:
            normalized["max_length"] = inferred_max_length

    format_rule = _strip_string(normalized.get("format_rule"))
    if format_rule and "formats" not in normalized:
        normalized["formats"] = [format_rule]

    for key, value in _infer_numeric_constraints(format_rule).items():
        normalized.setdefault(key, value)

    if "display" not in normalized:
        display_name = _strip_string(normalized.get("display_name"))
        if display_name:
            normalized["display"] = display_name

    _infer_filter_and_order(normalized)
    return normalized


def _build_rule_text(rule: dict[str, Any]) -> str:
    rule_text = _strip_string(rule.get("rule_text"))
    if rule_text:
        return rule_text

    field_name = _strip_string(rule.get("field_name")) or _strip_string(rule.get("target"))
    rule_type = _strip_string(rule.get("rule_type"))
    for key in ("required_when", "visible_when", "editable_when", "readonly_when", "condition"):
        value = rule.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    parts: list[str] = []
    if field_name:
        parts.append(field_name)
    if rule_type:
        parts.append(rule_type)
    for key in ("max_length", "min", "max", "integer_only", "max_count", "data_source"):
        if key in rule and rule.get(key) not in ("", None, []):
            parts.append(f"{key}={rule.get(key)}")
    if "filter" in rule and rule.get("filter") not in ("", None, []):
        parts.append(f"filter={rule.get('filter')}")
    if "order_by" in rule and rule.get("order_by") not in ("", None, []):
        parts.append(f"order_by={rule.get('order_by')}")
    return "; ".join(str(part) for part in parts if str(part).strip())


def _rule_key(rule: Any) -> tuple[str, str, str]:
    if isinstance(rule, str):
        return ("string", "", rule.strip())
    if isinstance(rule, dict):
        return (
            _strip_string(rule.get("rule_type")),
            _strip_string(rule.get("field_name")) or _strip_string(rule.get("target")),
            _build_rule_text(rule),
        )
    return ("", "", "")


def _normalize_rule(rule: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(rule)
    rule_type = _strip_string(normalized.get("rule_type"))
    condition = normalized.get("condition")

    if rule_type == "conditional_required" and "required_when" not in normalized and condition is not None:
        normalized["required_when"] = condition
    if rule_type == "conditional_visibility" and "visible_when" not in normalized and condition is not None:
        normalized["visible_when"] = condition
    if rule_type == "conditional_editability" and "editable_when" not in normalized and condition is not None:
        normalized["editable_when"] = condition
    if rule_type == "conditional_readonly" and "readonly_when" not in normalized and condition is not None:
        normalized["readonly_when"] = condition

    normalized["rule_text"] = _build_rule_text(normalized)
    return normalized


def _field_classification_for_rule(
    rule: dict[str, Any],
    merged_fields: dict[str, dict[str, Any]],
) -> str:
    field_name = _strip_string(rule.get("field_name")) or _strip_string(rule.get("target"))
    if not field_name:
        return "other_field"
    field = merged_fields.get(field_name)
    if not isinstance(field, dict):
        return "other_field"
    return classify_backend_config_field(field)


def _should_keep_rule(
    rule: dict[str, Any],
    merged_fields: dict[str, dict[str, Any]],
) -> bool:
    if _strip_string(rule.get("rule_type")) != "data_source_constraint":
        return True
    if _field_classification_for_rule(rule, merged_fields) != "selection_source_field":
        return False
    return any(rule.get(key) not in ("", None, []) for key in ("data_source", "filter", "order_by"))


def _feature_field_map(feature: dict[str, Any]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for source_key in ("field_definitions", "fields"):
        for raw_field in feature.get(source_key, []):
            if not isinstance(raw_field, dict):
                continue
            normalized_field = _normalize_field(raw_field)
            field_name = _strip_string(normalized_field.get("field_name")) or _strip_string(normalized_field.get("name"))
            if not field_name:
                continue
            target = merged.setdefault(field_name, {})
            target.update(normalized_field)

    return merged


def _derived_rules_from_field(field: dict[str, Any]) -> list[dict[str, Any]]:
    field_name = _strip_string(field.get("field_name")) or _strip_string(field.get("name"))
    if not field_name:
        return []

    derived: list[dict[str, Any]] = []
    condition_mappings = [
        ("conditional_required", "required_when"),
        ("conditional_visibility", "visible_when"),
        ("conditional_editability", "editable_when"),
        ("conditional_readonly", "readonly_when"),
    ]
    for rule_type, key in condition_mappings:
        value = field.get(key)
        if value not in ("", None, []):
            derived.append(
                {
                    "name": f"{field_name}_{rule_type}",
                    "rule_type": rule_type,
                    "field_name": field_name,
                    key: value,
                }
            )

    value_constraint_keys = ("max_length", "min", "max", "integer_only", "formats", "max_count")
    if any(field.get(key) not in ("", None, [], False) for key in value_constraint_keys):
        rule: dict[str, Any] = {
            "name": f"{field_name}_value_constraint",
            "rule_type": "value_constraint",
            "field_name": field_name,
        }
        for key in value_constraint_keys:
            if field.get(key) not in ("", None, []):
                rule[key] = field.get(key)
        derived.append(rule)

    field_classification = classify_backend_config_field(field)
    data_source_keys = ("data_source", "filter", "order_by")
    if field_classification == "selection_source_field" and any(
        field.get(key) not in ("", None, []) for key in data_source_keys
    ):
        rule = {
            "name": f"{field_name}_data_source_constraint",
            "rule_type": "data_source_constraint",
            "field_name": field_name,
        }
        for key in (*data_source_keys, "display"):
            if field.get(key) not in ("", None, []):
                rule[key] = field.get(key)
        derived.append(rule)

    return derived


def _sync_field_rules(
    feature: dict[str, Any],
    rules: list[Any],
    merged_fields: dict[str, dict[str, Any]],
) -> None:
    field_rules = [
        copy.deepcopy(rule)
        for rule in feature.get("field_rules", [])
        if isinstance(rule, dict)
        and (
            _strip_string(rule.get("rule_type")) != "data_source_constraint"
            or _field_classification_for_rule(rule, merged_fields) == "selection_source_field"
        )
    ]
    existing_keys = {
        (
            _strip_string(rule.get("field_name")),
            _strip_string(rule.get("rule_text")),
        )
        for rule in field_rules
    }

    rule_type_map = {
        "conditional_required": "conditional_required_rule",
        "conditional_visibility": "conditional_visibility_rule",
        "conditional_editability": "conditional_editability_rule",
        "conditional_readonly": "conditional_editability_rule",
        "value_constraint": "range_constraint",
        "data_source_constraint": "data_source_constraint",
    }

    for raw_rule in rules:
        if not isinstance(raw_rule, dict):
            continue
        field_name = _strip_string(raw_rule.get("field_name"))
        rule_text = _strip_string(raw_rule.get("rule_text"))
        if not field_name or not rule_text:
            continue
        key = (field_name, rule_text)
        if key in existing_keys:
            continue
        field_rules.append(
            {
                "rule_id": _strip_string(raw_rule.get("rule_id")),
                "field_name": field_name,
                "rule_text": rule_text,
                "rule_type": rule_type_map.get(_strip_string(raw_rule.get("rule_type")), "other"),
                "must_cover": True,
            }
        )
        existing_keys.add(key)

    feature["field_rules"] = field_rules


def normalize_structured_prd(data: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(data)

    for module in normalized.get("modules", []):
        if not isinstance(module, dict):
            continue
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue

            merged_fields = _feature_field_map(feature)
            if merged_fields:
                field_values = list(merged_fields.values())
                feature["fields"] = copy.deepcopy(field_values)
                feature["field_definitions"] = copy.deepcopy(field_values)

            normalized_rules: list[Any] = []
            seen_rule_keys: set[tuple[str, str, str]] = set()
            for raw_rule in feature.get("rules", []):
                if isinstance(raw_rule, str):
                    key = _rule_key(raw_rule)
                    if key not in seen_rule_keys:
                        normalized_rules.append(raw_rule)
                        seen_rule_keys.add(key)
                    continue
                if not isinstance(raw_rule, dict):
                    continue
                normalized_rule = _normalize_rule(raw_rule)
                if not _should_keep_rule(normalized_rule, merged_fields):
                    continue
                key = _rule_key(normalized_rule)
                if key not in seen_rule_keys:
                    normalized_rules.append(normalized_rule)
                    seen_rule_keys.add(key)

            for field in merged_fields.values():
                for derived_rule in _derived_rules_from_field(field):
                    normalized_rule = _normalize_rule(derived_rule)
                    key = _rule_key(normalized_rule)
                    if key not in seen_rule_keys:
                        normalized_rules.append(normalized_rule)
                        seen_rule_keys.add(key)

            feature["rules"] = normalized_rules
            _sync_field_rules(feature, normalized_rules, merged_fields)

    return normalized


def render_structured_prd_markdown(data: dict[str, Any]) -> str:
    data = normalize_structured_prd(data)
    lines: list[str] = ["# Structured PRD", ""]
    for section_name in TOP_LEVEL_SECTIONS:
        value = data.get(section_name, {} if section_name.endswith("_info") else [])
        lines.extend(
            [
                f"## {section_name}",
                "```json",
                json.dumps(value, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_structured_prd_markdown(text: str) -> dict[str, Any]:
    pattern = re.compile(
        r"^##\s+(project_info|requirement_info|pages|modules|flows)\s*$"
        r"\n```json\s*\n(.*?)\n```",
        re.MULTILINE | re.DOTALL,
    )
    matches = pattern.findall(text)
    section_map = {name: body for name, body in matches}

    missing = [name for name in TOP_LEVEL_SECTIONS if name not in section_map]
    if missing:
        raise StructuredPrdMarkdownError(
            f"structured_prd.md 缺少必要 section: {', '.join(missing)}"
        )

    data: dict[str, Any] = {}
    for name in TOP_LEVEL_SECTIONS:
        try:
            data[name] = json.loads(section_map[name])
        except json.JSONDecodeError as exc:
            raise StructuredPrdMarkdownError(
                f"section `{name}` 不是合法 JSON: {exc}"
            ) from exc

    if not isinstance(data["project_info"], dict):
        raise StructuredPrdMarkdownError("section `project_info` 必须为 JSON object")
    if not isinstance(data["requirement_info"], dict):
        raise StructuredPrdMarkdownError("section `requirement_info` 必须为 JSON object")
    for section_name in ("pages", "modules", "flows"):
        if not isinstance(data[section_name], list):
            raise StructuredPrdMarkdownError(
                f"section `{section_name}` 必须为 JSON array"
            )

    return normalize_structured_prd(data)
