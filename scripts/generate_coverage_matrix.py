#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


SUPPORTED_TYPES = {
    "field_property",
    "required",
    "conditional_required",
    "conditional_visibility",
    "conditional_editability",
    "value_boundary",
    "invalid_input",
    "data_source_filter",
    "data_source_display",
    "data_source_order",
    "happy_path_combo",
}

COVERAGE_LEVELS = {"critical", "business", "structural", "audit_only"}
EMIT_MODES = {"main_testcase", "audit_item", "group_audit", "drop"}
METADATA_FIELD_NAMES = {
    "creator_name",
    "creator",
    "created_by",
    "create_time",
    "created_time",
    "created_at",
    "modifier_name",
    "modifier",
    "modified_by",
    "modify_time",
    "modified_time",
    "update_time",
    "updated_time",
    "updated_at",
}
METADATA_DISPLAY_NAMES = {
    "创建人",
    "创建时间",
    "修改时间",
    "更新时间",
    "更新人",
}
HIGH_PRIORITY_FIDELITY_KEYWORDS = (
    "5s自动轮播",
    "每tab最多5条",
    "每tab最多4条",
    "每tab最多3条",
    "不允许超过3条",
    "默认关闭",
    "从属于顶部tab",
    "顶部tab归属",
)


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def priority_from_text(text: str) -> str:
    if any(keyword in text for keyword in ["必须", "高风险", "关键", "上限", "越界", "过滤", "排序"]):
        return "high"
    if any(keyword in text for keyword in ["建议", "说明", "差异"]):
        return "medium"
    return "low"


def textify(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(textify(item) for item in value)
    if isinstance(value, dict):
        return " ".join(textify(item) for item in value.values())
    return str(value or "").strip()


def feature_iter(structured_prd: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    results: list[tuple[str, dict[str, Any]]] = []
    for module in structured_prd.get("modules", []):
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if isinstance(feature, dict):
                results.append((module_name, feature))
    return results


def feature_context_map(structured_prd: dict[str, Any]) -> dict[str, tuple[str, str, str, str]]:
    contexts: dict[str, tuple[str, str, str, str]] = {}
    for module_name, feature in feature_iter(structured_prd):
        feature_name = str(feature.get("feature_name", "")).strip()
        page_name = str(feature.get("page_name", "")).strip()
        section_name = str(feature.get("section_name", "")).strip()
        if feature_name:
            contexts[feature_name] = (page_name, section_name, module_name, feature_name)
    return contexts


def is_metadata_field(field_name: str, title: str) -> bool:
    normalized_field = field_name.strip()
    normalized_title = title.strip()
    if normalized_field in METADATA_FIELD_NAMES:
        return True
    return any(keyword in normalized_title for keyword in METADATA_DISPLAY_NAMES)


def is_high_priority_fidelity_text(text: str) -> bool:
    if any(keyword in text for keyword in HIGH_PRIORITY_FIDELITY_KEYWORDS):
        return True
    return bool(re.search(r"(每tab最多\d+条|单tab下[^；，。]*不允许超过\d+条)", text))


def coverage_text(entry: dict[str, Any]) -> str:
    parts = [
        entry.get("title", ""),
        entry.get("rationale", ""),
        entry.get("page_name", ""),
        entry.get("module_name", ""),
        entry.get("feature_name", ""),
        entry.get("field_name", ""),
        entry.get("rule_name", ""),
        textify(entry.get("planned_assertions", [])),
        textify(entry.get("structured_refs", [])),
    ]
    return " ".join(str(part).strip() for part in parts if str(part).strip())


def infer_coverage_level(entry: dict[str, Any]) -> str:
    text = coverage_text(entry)
    coverage_type = str(entry.get("coverage_type", "")).strip()
    field_name = str(entry.get("field_name", "")).strip()
    title = str(entry.get("title", "")).strip()

    if is_high_priority_fidelity_text(text):
        return "critical"
    if coverage_type in {
        "conditional_required",
        "conditional_visibility",
        "conditional_editability",
        "value_boundary",
        "invalid_input",
        "data_source_filter",
        "data_source_order",
    }:
        return "critical"
    if coverage_type == "happy_path_combo":
        return "business"
    if is_metadata_field(field_name, title):
        return "audit_only"
    if coverage_type == "field_property":
        return "structural"
    if coverage_type in {"required"}:
        return "business"
    if coverage_type in {"data_source_display"}:
        return "structural"
    return "business"


def infer_emit_mode(entry: dict[str, Any]) -> str:
    coverage_level = str(entry.get("coverage_level", "")).strip()
    field_name = str(entry.get("field_name", "")).strip()
    title = str(entry.get("title", "")).strip()

    if is_metadata_field(field_name, title):
        return "group_audit"
    if coverage_level in {"critical", "business"}:
        return "main_testcase"
    if coverage_level == "audit_only":
        return "group_audit"
    if coverage_level == "structural":
        return "audit_item"
    return "drop"


def with_semantics(entry: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(entry)
    enriched["coverage_level"] = infer_coverage_level(enriched)
    enriched["emit_mode"] = infer_emit_mode(enriched)
    return enriched


def next_coverage_id(prefix: str, counter: int) -> str:
    return f"{prefix}-{counter:04d}"


def extract_rule_text(rule: Any) -> str:
    if isinstance(rule, str):
        return rule.strip()
    if isinstance(rule, dict):
        return str(rule.get("rule_text", "")).strip()
    return ""


def infer_fidelity_coverage_type(value: str) -> str:
    if any(keyword in value for keyword in ["每tab最多", "不允许超过", "最多5条", "最多4条", "最多3条"]):
        return "happy_path_combo"
    if "默认关闭" in value:
        return "field_property"
    if "顶部tab" in value:
        return "happy_path_combo"
    if "5s自动轮播" in value:
        return "happy_path_combo"
    return "happy_path_combo"


def add_entry(entries: list[dict[str, Any]], seen: set[tuple[Any, ...]], entry: dict[str, Any]) -> None:
    enriched = with_semantics(entry)
    key = (
        enriched.get("coverage_type"),
        enriched.get("source_origin"),
        enriched.get("page_name"),
        enriched.get("module_name"),
        enriched.get("feature_name"),
        enriched.get("field_name"),
        enriched.get("title"),
    )
    if key in seen:
        return
    seen.add(key)
    entries.append(enriched)


def build_structured_entries(structured_prd: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    counter = 1
    for module_name, feature in feature_iter(structured_prd):
        page_name = str(feature.get("page_name", "")).strip()
        section_name = str(feature.get("section_name", "")).strip()
        feature_name = str(feature.get("feature_name", "")).strip()
        for field in feature.get("fields", []):
            if not isinstance(field, dict):
                continue
            field_name = str(field.get("field_name", "")).strip()
            display_name = str(field.get("display_name", "")).strip() or field_name
            if not field_name:
                continue

            add_entry(
                entries,
                seen,
                {
                    "coverage_id": f"COV-EX-{counter:04d}",
                    "coverage_type": "field_property",
                    "source_origin": "explicit_rule",
                    "source_type": "structured_field",
                    "title": f"{display_name} 字段属性",
                    "page_name": page_name,
                    "section_name": section_name,
                    "module_name": module_name,
                    "feature_name": feature_name,
                    "field_name": field_name,
                    "priority": "medium",
                    "rationale": f"字段 `{display_name}` 已在 structured_prd 中显式建模，需要基础属性覆盖。",
                    "planned_assertions": [
                        f"校验 `{display_name}` 的控件类型、默认值或枚举定义与结构化规则一致。"
                    ],
                    "structured_refs": [f"{module_name}.{feature_name}.{field_name}"],
                    "reasoning_refs": []
                }
            )
            counter += 1

            if field.get("required") is True and field.get("required_when") in ("", None):
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": f"COV-EX-{counter:04d}",
                        "coverage_type": "required",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_field",
                        "title": f"{display_name} 必填",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": field_name,
                        "priority": "high",
                        "rationale": f"`{display_name}` 为显式必填字段。",
                        "planned_assertions": [
                            f"`{display_name}` 为空时应阻止提交或保存。"
                        ],
                        "structured_refs": [f"{module_name}.{feature_name}.{field_name}.required"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

            if field.get("required_when") not in ("", None):
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": f"COV-EX-{counter:04d}",
                        "coverage_type": "conditional_required",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": f"{display_name} 条件必填",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": field_name,
                        "priority": "high",
                        "rationale": f"`{display_name}` 已显式落出 `required_when`。",
                        "planned_assertions": [
                            f"当 `{field.get('required_when')}` 时，`{display_name}` 为空应阻止提交。"
                        ],
                        "structured_refs": [f"{module_name}.{feature_name}.{field_name}.required_when"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

            if field.get("visible_when") not in ("", None):
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": f"COV-EX-{counter:04d}",
                        "coverage_type": "conditional_visibility",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": f"{display_name} 条件展示",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": field_name,
                        "priority": "high",
                        "rationale": f"`{display_name}` 已显式落出 `visible_when`。",
                        "planned_assertions": [
                            f"仅当 `{field.get('visible_when')}` 时展示 `{display_name}`。"
                        ],
                        "structured_refs": [f"{module_name}.{feature_name}.{field_name}.visible_when"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

            edit_condition = field.get("editable_when") or field.get("readonly_when")
            if edit_condition not in ("", None):
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": f"COV-EX-{counter:04d}",
                        "coverage_type": "conditional_editability",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": f"{display_name} 条件编辑性",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": field_name,
                        "priority": "high",
                        "rationale": f"`{display_name}` 存在条件可编辑/只读规则。",
                        "planned_assertions": [
                            f"当 `{edit_condition}` 时，`{display_name}` 应表现为只读或可编辑约束。"
                        ],
                        "structured_refs": [f"{module_name}.{feature_name}.{field_name}.editable_when", f"{module_name}.{feature_name}.{field_name}.readonly_when"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

            if any(field.get(key) not in ("", None, []) for key in ("min", "max", "max_length")):
                planned = []
                if field.get("min") not in ("", None):
                    planned.append(f"`{display_name}` 最小值边界={field.get('min')}")
                if field.get("max") not in ("", None):
                    planned.append(f"`{display_name}` 最大值边界={field.get('max')}")
                if field.get("max_length") not in ("", None):
                    planned.append(f"`{display_name}` 长度上限={field.get('max_length')}")
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": f"COV-EX-{counter:04d}",
                        "coverage_type": "value_boundary",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": f"{display_name} 边界值",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": field_name,
                        "priority": "high",
                        "rationale": f"`{display_name}` 存在数值或长度边界约束。",
                        "planned_assertions": planned,
                        "structured_refs": [f"{module_name}.{feature_name}.{field_name}.min", f"{module_name}.{feature_name}.{field_name}.max", f"{module_name}.{feature_name}.{field_name}.max_length"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

            if field.get("filter") not in ("", None, []):
                filters = field.get("filter")
                filters_text = filters if isinstance(filters, list) else [filters]
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": f"COV-EX-{counter:04d}",
                        "coverage_type": "data_source_filter",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": f"{display_name} 数据源过滤",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": field_name,
                        "priority": "high",
                        "rationale": f"`{display_name}` 存在显式过滤规则。",
                        "planned_assertions": [f"`{display_name}` 候选项只保留满足 `{item}` 的数据。" for item in filters_text],
                        "structured_refs": [f"{module_name}.{feature_name}.{field_name}.filter"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

            if field.get("content_values"):
                display_hints = [item for item in field.get("content_values", []) if any(keyword in str(item) for keyword in ["展示", "id", "名称"])]
                if display_hints:
                    add_entry(
                        entries,
                        seen,
                        {
                            "coverage_id": f"COV-EX-{counter:04d}",
                            "coverage_type": "data_source_display",
                            "source_origin": "explicit_rule",
                            "source_type": "structured_field",
                            "title": f"{display_name} 数据源展示格式",
                            "page_name": page_name,
                            "section_name": section_name,
                            "module_name": module_name,
                            "feature_name": feature_name,
                            "field_name": field_name,
                            "priority": "medium",
                            "rationale": f"`{display_name}` 的候选项展示格式已在结构层保留。",
                            "planned_assertions": [f"`{display_name}` 候选项展示应包含 `{item}`。" for item in display_hints],
                            "structured_refs": [f"{module_name}.{feature_name}.{field_name}.content_values"],
                            "reasoning_refs": []
                        }
                    )
                    counter += 1

            if field.get("order_by") not in ("", None, []):
                order = field.get("order_by")
                order_text = order if isinstance(order, list) else [order]
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": f"COV-EX-{counter:04d}",
                        "coverage_type": "data_source_order",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": f"{display_name} 数据源排序",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": field_name,
                        "priority": "high",
                        "rationale": f"`{display_name}` 存在显式排序规则。",
                        "planned_assertions": [f"`{display_name}` 候选项应满足 `{item}`。" for item in order_text],
                        "structured_refs": [f"{module_name}.{feature_name}.{field_name}.order_by"],
                        "reasoning_refs": []
                    }
                )
                counter += 1
    return entries


def build_rule_signal_entries(structured_prd: dict[str, Any], start_counter: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    counter = start_counter
    contexts = feature_context_map(structured_prd)

    for rule in structured_prd.get("requirement_info", {}).get("explicit_rules", []):
        if not isinstance(rule, dict) or str(rule.get("priority", "")).strip() != "high":
            continue
        context = contexts.get(str(rule.get("applies_to", "")).strip(), ("", "", "", ""))
        page_name, section_name, module_name, feature_name = context
        rule_id = str(rule.get("rule_id", "")).strip()
        for fidelity_point in rule.get("fidelity_points", []):
            if not isinstance(fidelity_point, dict):
                continue
            value = str(fidelity_point.get("value", "")).strip()
            if not value:
                continue
            coverage_type = infer_fidelity_coverage_type(value)
            field_name = "status" if "默认关闭" in value else ""
            add_entry(
                entries,
                seen,
                {
                    "coverage_id": next_coverage_id("COV-EX", counter),
                    "coverage_type": coverage_type,
                    "source_origin": "explicit_rule",
                    "source_type": "coverage_candidate",
                    "title": value,
                    "page_name": page_name,
                    "section_name": section_name,
                    "module_name": module_name,
                    "feature_name": feature_name,
                    "field_name": field_name,
                    "rule_name": rule_id,
                    "priority": "high",
                    "rationale": f"高优 explicit_rule `{rule_id}` 的 fidelity point 需要直接进入 coverage 主链。",
                    "planned_assertions": [value],
                    "structured_refs": [f"requirement_info.explicit_rules.{rule_id}"],
                    "reasoning_refs": []
                }
            )
            counter += 1

    quantity_pattern = re.compile(r"(每tab最多\d+条|最多配置\d+条数据|单tab下[^；，。]*不允许超过\d+条)")
    for module_name, feature in feature_iter(structured_prd):
        page_name = str(feature.get("page_name", "")).strip()
        section_name = str(feature.get("section_name", "")).strip()
        feature_name = str(feature.get("feature_name", "")).strip()
        for rule in feature.get("rules", []):
            rule_text = extract_rule_text(rule)
            if not rule_text:
                continue

            if "默认关闭" in rule_text and "状态" in rule_text:
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": next_coverage_id("COV-EX", counter),
                        "coverage_type": "field_property",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": "状态默认关闭",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": "status",
                        "rule_name": rule_text,
                        "priority": "high",
                        "rationale": "默认状态属于高优保真对象，需要单独建立 coverage。",
                        "planned_assertions": [rule_text],
                        "structured_refs": [f"{module_name}.{feature_name}.status.default_value"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

            if "5s自动轮播" in rule_text:
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": next_coverage_id("COV-EX", counter),
                        "coverage_type": "happy_path_combo",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": "5s自动轮播",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": "",
                        "rule_name": rule_text,
                        "priority": "high",
                        "rationale": "自动轮播属于高优行为 fidelity，需要建立 coverage。",
                        "planned_assertions": [rule_text],
                        "structured_refs": [f"{module_name}.{feature_name}.rules"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

            if "从属于顶部tab" in rule_text:
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": next_coverage_id("COV-EX", counter),
                        "coverage_type": "happy_path_combo",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": "顶部tab归属",
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": "",
                        "rule_name": rule_text,
                        "priority": "high",
                        "rationale": "容器归属属于高优行为 fidelity，需要建立 coverage。",
                        "planned_assertions": [rule_text],
                        "structured_refs": [f"{module_name}.{feature_name}.rules"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

            quantity_match = quantity_pattern.search(rule_text)
            if quantity_match:
                quantity_text = quantity_match.group(1)
                add_entry(
                    entries,
                    seen,
                    {
                        "coverage_id": next_coverage_id("COV-EX", counter),
                        "coverage_type": "happy_path_combo",
                        "source_origin": "explicit_rule",
                        "source_type": "structured_rule",
                        "title": quantity_text,
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "field_name": "",
                        "rule_name": rule_text,
                        "priority": "high",
                        "rationale": "数量上限属于高优 fidelity，需要单独建立 coverage。",
                        "planned_assertions": [quantity_text],
                        "structured_refs": [f"{module_name}.{feature_name}.rules"],
                        "reasoning_refs": []
                    }
                )
                counter += 1

    return entries


def build_reasoning_entries(reasoning_pack: dict[str, Any], structured_prd: dict[str, Any], start_counter: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    counter = start_counter

    for edge_case in reasoning_pack.get("edge_cases", []):
        related_field = str(edge_case.get("related_field", "")).strip()
        if related_field == "display_day_x":
            add_entry(
                entries,
                seen,
                {
                    "coverage_id": f"COV-AI-{counter:04d}",
                    "coverage_type": "invalid_input",
                    "source_origin": "ai_reasoning",
                    "source_type": "edge_case",
                    "title": "X 非法输入",
                    "page_name": edge_case["source_refs"][0].get("page_name", ""),
                    "module_name": "",
                    "feature_name": "",
                    "field_name": related_field,
                    "priority": "high",
                    "rationale": edge_case.get("scenario", ""),
                    "planned_assertions": [
                        "X 应覆盖小于最小值、超过最大值、非整数输入三类非法输入。"
                    ],
                    "structured_refs": [],
                    "reasoning_refs": [edge_case.get("edge_case_id", "")]
                }
            )
            counter += 1
        if related_field == "link_url":
            add_entry(
                entries,
                seen,
                {
                    "coverage_id": f"COV-AI-{counter:04d}",
                    "coverage_type": "invalid_input",
                    "source_origin": "ai_reasoning",
                    "source_type": "edge_case",
                    "title": "链接 长度越界",
                    "page_name": edge_case["source_refs"][0].get("page_name", ""),
                    "module_name": "",
                    "feature_name": "",
                    "field_name": related_field,
                    "priority": "high",
                    "rationale": edge_case.get("scenario", ""),
                    "planned_assertions": [
                        "链接长度超过 1000 时应提示越界并阻止提交。"
                    ],
                    "structured_refs": [],
                    "reasoning_refs": [edge_case.get("edge_case_id", "")]
                }
            )
            counter += 1

    risk_text = " ".join(risk.get("risk_statement", "") for risk in reasoning_pack.get("business_risks", []))
    if "排序" in risk_text and "条数上限" in risk_text:
        add_entry(
            entries,
            seen,
            {
                "coverage_id": f"COV-AI-{counter:04d}",
                "coverage_type": "happy_path_combo",
                "source_origin": "ai_reasoning",
                "source_type": "business_risk",
                "title": "banner 合法组合场景",
                "page_name": "小程序banner配置页",
                "module_name": "小程序banner配置",
                "feature_name": "banner配置录入与状态字段",
                "field_name": "",
                "priority": "high",
                "rationale": "排序、容量与条件字段共同作用，单规则覆盖不足以验证真实可配置成功路径。",
                "planned_assertions": [
                    "展示类型选择“后X天（自然日）内展示”时，X 使用合法整数。",
                    "跳转类型选择“活动中心”时，选择活动只出现满足过滤条件且排序正确的候选项。",
                    "展示tab 选择有效导航，状态设置为开启后，可形成一条合法可保存的配置。"
                ],
                "structured_refs": [
                    "小程序banner配置.banner配置录入与状态字段.display_day_x",
                    "小程序banner配置.banner配置录入与状态字段.selected_activity",
                    "小程序banner配置.banner配置录入与状态字段.status"
                ],
                "reasoning_refs": [risk.get("risk_id", "") for risk in reasoning_pack.get("business_risks", [])[:2]]
            }
        )
        counter += 1

    for dimension in reasoning_pack.get("recommended_test_dimensions", []):
        title = str(dimension.get("dimension", "")).strip()
        if title == "数据来源、过滤与排序":
            add_entry(
                entries,
                seen,
                {
                    "coverage_id": f"COV-AI-{counter:04d}",
                    "coverage_type": "data_source_order",
                    "source_origin": "ai_reasoning",
                    "source_type": "recommended_test_dimension",
                    "title": "选择活动 排序口径复核",
                    "page_name": "小程序banner配置页",
                    "module_name": "小程序banner配置",
                    "feature_name": "banner配置录入与状态字段",
                    "field_name": "selected_activity",
                    "priority": "high",
                    "rationale": dimension.get("rationale", ""),
                    "planned_assertions": [
                        "选择活动 不仅要过滤正确，还要按活动创建时间倒序展示。"
                    ],
                    "structured_refs": ["小程序banner配置.banner配置录入与状态字段.selected_activity.order_by"],
                    "reasoning_refs": [dimension.get("dimension_id", "")]
                }
            )
            counter += 1
        if title == "条件展示与条件只读":
            add_entry(
                entries,
                seen,
                {
                    "coverage_id": f"COV-AI-{counter:04d}",
                    "coverage_type": "conditional_editability",
                    "source_origin": "ai_reasoning",
                    "source_type": "recommended_test_dimension",
                    "title": "链接 只读规则复核",
                    "page_name": "小程序banner配置页",
                    "module_name": "小程序banner配置",
                    "feature_name": "banner配置录入与状态字段",
                    "field_name": "link_url",
                    "priority": "high",
                    "rationale": dimension.get("rationale", ""),
                    "planned_assertions": [
                        "活动中心场景下，链接字段虽然可见，但不允许编辑。"
                    ],
                    "structured_refs": ["小程序banner配置.banner配置录入与状态字段.link_url.readonly_when"],
                    "reasoning_refs": [dimension.get("dimension_id", "")]
                }
            )
            counter += 1

    return entries


def build_matrix(structured_prd: dict[str, Any], reasoning_pack: dict[str, Any]) -> dict[str, Any]:
    explicit_entries = build_structured_entries(structured_prd)
    rule_signal_entries = build_rule_signal_entries(structured_prd, len(explicit_entries) + 1)
    reasoning_entries = build_reasoning_entries(
        reasoning_pack,
        structured_prd,
        len(explicit_entries) + len(rule_signal_entries) + 1,
    )
    return {
        "project_code": reasoning_pack.get("project_code") or structured_prd.get("project_info", {}).get("project_code", ""),
        "work_item_id": reasoning_pack.get("work_item_id", ""),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_from": [
            "structured_prd/structured_prd.json",
            "analysis/reasoning_pack.json"
        ],
        "entries": explicit_entries + rule_signal_entries + reasoning_entries,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 coverage_matrix.json")
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--structured-prd", required=False, help="structured_prd.json 路径")
    parser.add_argument("--reasoning-pack", required=False, help="reasoning_pack.json 路径")
    parser.add_argument("--output", required=False, help="coverage_matrix.json 输出路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.project_code and args.work_item_id:
        root = resolve_work_item_root(normalize_code(args.project_code), normalize_code(args.work_item_id))
        structured_prd_path = Path(args.structured_prd).resolve() if args.structured_prd else root / "structured_prd" / "structured_prd.json"
        reasoning_pack_path = Path(args.reasoning_pack).resolve() if args.reasoning_pack else root / "analysis" / "reasoning_pack.json"
        output_path = Path(args.output).resolve() if args.output else root / "coverage" / "coverage_matrix.json"
    else:
        if not (args.structured_prd and args.reasoning_pack and args.output):
            raise SystemExit("必须提供 --project-code + --work-item-id，或显式提供 --structured-prd --reasoning-pack --output")
        structured_prd_path = Path(args.structured_prd).resolve()
        reasoning_pack_path = Path(args.reasoning_pack).resolve()
        output_path = Path(args.output).resolve()

    structured_prd = load_json(structured_prd_path)
    reasoning_pack = load_json(reasoning_pack_path)
    matrix = build_matrix(structured_prd, reasoning_pack)
    write_json(output_path, matrix)

    print(f"coverage_matrix: {output_path}")
    print(f"entries: {len(matrix['entries'])}")
    type_counter: dict[str, int] = {}
    for entry in matrix["entries"]:
        coverage_type = entry["coverage_type"]
        type_counter[coverage_type] = type_counter.get(coverage_type, 0) + 1
    for coverage_type in sorted(SUPPORTED_TYPES):
        print(f"{coverage_type}: {type_counter.get(coverage_type, 0)}")
    level_counter: dict[str, int] = {}
    mode_counter: dict[str, int] = {}
    for entry in matrix["entries"]:
        coverage_level = entry.get("coverage_level", "")
        emit_mode = entry.get("emit_mode", "")
        level_counter[coverage_level] = level_counter.get(coverage_level, 0) + 1
        mode_counter[emit_mode] = mode_counter.get(emit_mode, 0) + 1
    for coverage_level in sorted(COVERAGE_LEVELS):
        print(f"coverage_level.{coverage_level}: {level_counter.get(coverage_level, 0)}")
    for emit_mode in sorted(EMIT_MODES):
        print(f"emit_mode.{emit_mode}: {mode_counter.get(emit_mode, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
