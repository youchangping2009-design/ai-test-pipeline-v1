#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    from jsonschema import Draft7Validator
except ImportError:
    Draft7Validator = None

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.testcase_markdown_utils import parse_testcase_document
from scripts.testcase_markdown_utils import parse_testcase_ids_from_content
from scripts.testcase_markdown_utils import parse_testcase_rows_as_text


BACKEND_CONFIG_PAGES = {
    "小程序导航配置页",
    "小程序banner配置页",
    "小程序瓷片区配置页",
    "小程序金刚区配置页",
    "小程序弹窗配置页",
}
BACKEND_MODAL_SECTIONS = {"添加弹窗", "编辑弹窗"}
FIELD_ATTRIBUTE_SOURCE_KEYS = (
    "control_type",
    "required",
    "editable",
    "default_value",
    "length_rule",
    "format_rule",
    "data_source",
    "enum_values",
    "content_values",
    "conditional_visibility",
    "conditional_editability",
)
CONTROL_TYPE_LABELS = {
    "text_input": "文本输入框",
    "upload_image": "图片上传",
    "select_single": "下拉菜单，单选",
    "select_multi": "下拉菜单，多选",
    "number_input": "数字输入框",
    "switch": "开关",
    "radio": "单选",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_testcase_ids(path: Path) -> set[str]:
    return parse_testcase_ids_from_content(path.read_text(encoding="utf-8"), strict=False)


def parse_testcase_rows(path: Path) -> dict[str, str]:
    return parse_testcase_rows_as_text(path.read_text(encoding="utf-8"), strict=False)


def format_json_path(error_path: List[Any]) -> str:
    if not error_path:
        return "$"
    result = "$"
    for item in error_path:
        if isinstance(item, int):
            result += f"[{item}]"
        else:
            result += f".{item}"
    return result


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    if Draft7Validator is None:
        return []
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return [
        f"[Schema校验失败] {format_json_path(list(err.path))}: {err.message}"
        for err in errors
    ]


def build_structured_index(structured_prd: dict[str, Any]) -> dict[str, Any]:
    module_names: set[str] = set()
    page_names: set[str] = set()
    section_pairs: set[tuple[str, str]] = set()
    feature_pairs: set[tuple[str, str]] = set()
    rule_keys: set[tuple[str, str, str]] = set()
    field_keys: set[tuple[str, str, str]] = set()
    field_attribute_keys: set[tuple[str, str, str, str, str]] = set()
    field_rule_keys: set[tuple[str, str, str, str]] = set()
    field_rule_table_row_keys: set[tuple[str, str, str, str, str]] = set()
    flow_ids: set[str] = set()
    field_display_names: dict[tuple[str, str, str], str] = {}

    for page in structured_prd.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_name = page.get("page_name")
        if isinstance(page_name, str) and page_name.strip():
            page_name = page_name.strip()
            page_names.add(page_name)
        else:
            page_name = ""
        for section in page.get("sections", []):
            if not isinstance(section, dict):
                continue
            section_name = section.get("section_name")
            if page_name and isinstance(section_name, str) and section_name.strip():
                section_pairs.add((page_name, section_name.strip()))

    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_name = module.get("module_name")
        if not isinstance(module_name, str) or not module_name.strip():
            continue
        module_name = module_name.strip()
        module_names.add(module_name)

        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            feature_name = feature.get("feature_name")
            if not isinstance(feature_name, str) or not feature_name.strip():
                continue
            feature_name = feature_name.strip()
            feature_pairs.add((module_name, feature_name))

            for rule in feature.get("rules", []):
                if isinstance(rule, str) and rule.strip():
                    rule_keys.add((module_name, feature_name, rule.strip()))

            for field in feature.get("field_definitions", []):
                if not isinstance(field, dict):
                    continue
                field_name_value = str(field.get("field_name", "")).strip()
                display_name_value = str(field.get("display_name", "")).strip()
                for candidate_key in ("field_name", "display_name"):
                    candidate = field.get(candidate_key)
                    if isinstance(candidate, str) and candidate.strip():
                        field_keys.add((module_name, feature_name, candidate.strip()))
                if field_name_value:
                    field_display_names[(module_name, feature_name, field_name_value)] = display_name_value
                    for attribute_name, target_name in derive_field_attribute_targets(field):
                        field_attribute_keys.add(
                            (
                                module_name,
                                feature_name,
                                field_name_value,
                                attribute_name,
                                target_name,
                            )
                        )

            for field_rule in feature.get("field_rules", []):
                if not isinstance(field_rule, dict):
                    continue
                field_name = field_rule.get("field_name")
                rule_text = field_rule.get("rule_text")
                if isinstance(field_name, str) and field_name.strip() and isinstance(rule_text, str) and rule_text.strip():
                    field_rule_keys.add((module_name, feature_name, field_name.strip(), rule_text.strip()))

            for field_rule_table in feature.get("field_rule_tables", []):
                if not isinstance(field_rule_table, dict):
                    continue
                field_name = field_rule_table.get("field_name")
                table_name = field_rule_table.get("table_name")
                if not isinstance(field_name, str) or not field_name.strip():
                    continue
                if not isinstance(table_name, str) or not table_name.strip():
                    continue
                for row in field_rule_table.get("rows", []):
                    if not isinstance(row, dict):
                        continue
                    row_name = row.get("row_name")
                    if isinstance(row_name, str) and row_name.strip():
                        field_rule_table_row_keys.add(
                            (
                                module_name,
                                feature_name,
                                field_name.strip(),
                                table_name.strip(),
                                row_name.strip(),
                            )
                        )

    for flow in structured_prd.get("flows", []):
        if isinstance(flow, dict):
            flow_id = flow.get("flow_id")
            if isinstance(flow_id, str) and flow_id.strip():
                flow_ids.add(flow_id.strip())

    return {
        "pages": page_names,
        "sections": section_pairs,
        "modules": module_names,
        "features": feature_pairs,
        "rules": rule_keys,
        "fields": field_keys,
        "field_attributes": field_attribute_keys,
        "field_rules": field_rule_keys,
        "field_rule_table_rows": field_rule_table_row_keys,
        "flows": flow_ids,
        "field_display_names": field_display_names,
    }


def derive_field_attribute_targets(field: dict[str, Any]) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []

    control_type = field.get("control_type")
    if isinstance(control_type, str) and control_type.strip():
        targets.append(("control_type", CONTROL_TYPE_LABELS.get(control_type.strip(), control_type.strip())))

    if "required" in field and isinstance(field.get("required"), bool):
        targets.append(("required", "必填" if field["required"] else "非必填"))

    if "editable" in field and isinstance(field.get("editable"), bool):
        targets.append(("editable", "可编辑" if field["editable"] else "不可编辑"))

    if "default_value" in field:
        default_value = field.get("default_value")
        if default_value == "":
            targets.append(("default_value", "默认为空"))
        elif default_value is not None:
            targets.append(("default_value", f"默认{default_value}"))

    length_rule = field.get("length_rule")
    if isinstance(length_rule, str) and length_rule.strip():
        targets.append(("length_rule", length_rule.strip()))

    format_rule = field.get("format_rule")
    if isinstance(format_rule, str) and format_rule.strip():
        targets.append(("format_rule", format_rule.strip()))

    data_source = field.get("data_source")
    if isinstance(data_source, str) and data_source.strip():
        targets.append(("data_source", data_source.strip()))

    enum_values = field.get("enum_values")
    if isinstance(enum_values, list):
        enum_items = [str(item).strip() for item in enum_values if str(item).strip()]
        for item in enum_items:
            targets.append(("enum_values", item))

    content_values = field.get("content_values")
    if isinstance(content_values, list):
        content_items = [str(item).strip() for item in content_values if str(item).strip()]
        for item in content_items:
            targets.append(("content_values", item))

    conditional_visibility = field.get("conditional_visibility")
    if isinstance(conditional_visibility, str) and conditional_visibility.strip():
        targets.append(("conditional_visibility", conditional_visibility.strip()))

    conditional_editability = field.get("conditional_editability")
    if isinstance(conditional_editability, str) and conditional_editability.strip():
        targets.append(("conditional_editability", conditional_editability.strip()))

    return targets


def normalize_text(value: str) -> str:
    return value.replace(" ", "").replace("　", "").strip()


def infer_fidelity_points_from_rule(rule: dict[str, Any]) -> list[dict[str, Any]]:
    rule_text = rule.get("rule_text")
    if not isinstance(rule_text, str) or not rule_text.strip():
        return []

    points: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    patterns: list[tuple[str, str]] = [
        ("time_constraint", r"\d+\s*(?:ms|秒|分钟|小时|天|s)\b"),
        ("quantity_constraint", r"(?:前|后|满|不足|至少|至多|不超过)\s*\d+\s*(?:个|条|位|次|页|项)"),
        ("quantity_constraint", r"(?:排序值|权重|优先级)?\s*(?:前|后)\s*\d+\s*(?:的|名|位|个|条|项)?"),
        ("quantity_constraint", r"\d+\s*-\s*\d+\s*位"),
        ("state_constraint", r"状态\s*[=：:]\s*[^\s，。,；;]+"),
        ("source_constraint", r"(?:数据来源|来源)\s*[：:]\s*[^，。,；;]+"),
        ("source_constraint", r"(?:数据来源|来源|排序值来源)\s*(?:于|自|来自)\s*[^，。,；;]+"),
        ("source_constraint", r"后管(?:-[^-，。,；;]+)+"),
        ("order_constraint", r"(?:升序|降序|倒序|正序|小值在前|大值在前)"),
        ("order_constraint", r"排序值相同[^，。,；;]*"),
        ("fallback_constraint", r"(?:不足|为空|缺失)[^，。,；;]*?(?:补齐|默认|回退)"),
        ("copy_constraint", r"[「『【][^」』】]+[」』】]"),
        ("copy_constraint", r"(?:标题|文案|按钮|入口)[^，。,；;]*?(?:写死|固定|必须为|文案为)[^，。,；;]*"),
        ("style_constraint", r"(?:样式|颜色|高亮|置顶|特殊展示|一行展示|超出省略)[^，。,；;]*?(?:不同|区别|特殊|高亮|置顶|省略|截断)?"),
        ("container_constraint", r"(?:弹窗|详情层|浮层|抽屉|tab|标签页|面板)[^，。,；;]*?(?:展示|打开|出现|选中|实现)[^，。,；;]*"),
        ("selection_constraint", r"(?:默认选中|默认展示|默认展开|默认打开)[^，。,；;]*"),
        ("sequence_constraint", r"点击[^，。,；;]*?(?:按钮|入口|标题|链接)?[^，。,；;]*?(?:弹窗|详情|跳转|打开|展示)"),
        ("extensibility_constraint", r"(?:后期|后续|未来|预留|扩展|增加)[^，。,；;]*?(?:类型|能力|功能|配置|场景)"),
    ]

    for constraint_type, pattern in patterns:
        for match in re.finditer(pattern, rule_text):
            value = match.group(0).strip()
            key = (constraint_type, value)
            if key in seen:
                continue
            seen.add(key)
            point: dict[str, Any] = {
                "constraint_type": constraint_type,
                "value": value,
                "must_preserve": True,
            }
            if constraint_type == "state_constraint":
                point["forbidden_rewrites"] = ["可展示状态", "有效状态", "启用状态集合"]
            elif constraint_type == "order_constraint":
                point["forbidden_rewrites"] = ["排序规则一致", "顺序稳定"]
            elif constraint_type == "style_constraint":
                point["forbidden_rewrites"] = ["展示正确", "样式正常", "显示正常"]
            elif constraint_type == "container_constraint":
                point["forbidden_rewrites"] = ["打开详情", "展示详情", "跳转成功"]
            elif constraint_type == "selection_constraint":
                point["forbidden_rewrites"] = ["默认正确", "默认展示正确"]
            points.append(point)

    return points


def pick_candidate_rows(
    testcase_rows: dict[str, str], applies_to: str | None, expected_items: list[str] | None
) -> list[str]:
    if not testcase_rows:
        return []

    normalized_rows = list(testcase_rows.values())
    candidate_rows = normalized_rows

    applies_to_value = normalize_text(applies_to) if isinstance(applies_to, str) and applies_to.strip() else ""
    if applies_to_value:
        matched = [row for row in normalized_rows if applies_to_value in normalize_text(row)]
        if matched:
            candidate_rows = matched

    expected_values = [
        normalize_text(item)
        for item in (expected_items or [])
        if isinstance(item, str) and item.strip()
    ]
    if expected_values:
        matched = [
            row
            for row in candidate_rows
            if any(expected_value in normalize_text(row) for expected_value in expected_values)
        ]
        if matched:
            candidate_rows = matched

    return candidate_rows


def validate_explicit_rule_fidelity(
    structured_prd: dict[str, Any], testcase_rows: dict[str, str]
) -> list[str]:
    errors: list[str] = []
    explicit_rules = structured_prd.get("requirement_info", {}).get("explicit_rules", [])

    for rule in explicit_rules:
        if not isinstance(rule, dict):
            continue
        if rule.get("priority") != "high":
            continue

        fidelity_points = rule.get("fidelity_points", [])
        if not isinstance(fidelity_points, list) or not fidelity_points:
            fidelity_points = infer_fidelity_points_from_rule(rule)
        if not fidelity_points:
            continue

        candidate_rows = pick_candidate_rows(
            testcase_rows,
            rule.get("applies_to"),
            rule.get("expected_items"),
        )
        if not candidate_rows:
            candidate_rows = list(testcase_rows.values())

        for fidelity_point in fidelity_points:
            if not isinstance(fidelity_point, dict):
                continue

            value = fidelity_point.get("value")
            if not isinstance(value, str) or not value.strip():
                continue

            must_preserve = fidelity_point.get("must_preserve")
            should_preserve = True if must_preserve is None else bool(must_preserve)
            normalized_value = normalize_text(value)

            if should_preserve and not any(
                normalized_value in normalize_text(row_text) for row_text in candidate_rows
            ):
                errors.append(
                    f"[ExplicitRule校验失败] {rule.get('rule_id', 'UNKNOWN')} 的 fidelity value 未在 testcase 中保留: {value}"
                )

            forbidden_rewrites = fidelity_point.get("forbidden_rewrites", [])
            for forbidden in forbidden_rewrites:
                if isinstance(forbidden, str) and forbidden.strip():
                    normalized_forbidden = normalize_text(forbidden)
                    if any(normalized_forbidden in normalize_text(row_text) for row_text in candidate_rows):
                        errors.append(
                            f"[ExplicitRule校验失败] {rule.get('rule_id', 'UNKNOWN')} 命中了禁止泛化表述: {forbidden}"
                        )

    return errors


def validate_target_exists(target: dict[str, Any], index: dict[str, Any]) -> str | None:
    target_type = target.get("target_type")
    module_name = target.get("module_name")
    feature_name = target.get("feature_name")
    target_name = target.get("target_name")

    if target_type == "module":
        if module_name not in index["modules"]:
            return f"module 不存在: {module_name}"
        return None

    if target_type == "page":
        if target_name not in index["pages"]:
            return f"page 不存在: {target_name}"
        return None

    if target_type == "section":
        page_name = module_name or feature_name
        if (page_name, target_name) not in index["sections"]:
            return f"section 不存在: page={page_name}, section={target_name}"
        return None

    if target_type == "feature":
        if (module_name, feature_name) not in index["features"]:
            return f"feature 不存在: module={module_name}, feature={feature_name}"
        return None

    if target_type == "rule":
        if (module_name, feature_name, target_name) not in index["rules"]:
            return f"rule 不存在: module={module_name}, feature={feature_name}, rule={target_name}"
        return None

    if target_type == "field_definition":
        if (module_name, feature_name, target_name) not in index["fields"]:
            return (
                "field_definition 不存在: "
                f"module={module_name}, feature={feature_name}, field={target_name}"
            )
        return None

    if target_type == "field_attribute":
        field_name = target.get("field_name")
        attribute_name = target.get("attribute_name")
        if (module_name, feature_name, field_name, attribute_name, target_name) not in index["field_attributes"]:
            return (
                "field_attribute 不存在: "
                f"module={module_name}, feature={feature_name}, field={field_name}, attribute={attribute_name}, value={target_name}"
            )
        return None

    if target_type == "field_rule":
        field_name = target.get("field_name")
        if (module_name, feature_name, field_name, target_name) not in index["field_rules"]:
            return (
                "field_rule 不存在: "
                f"module={module_name}, feature={feature_name}, field={field_name}, rule={target_name}"
            )
        return None

    if target_type == "field_rule_table_row":
        field_name = target.get("field_name")
        table_name = target.get("table_name")
        if (module_name, feature_name, field_name, table_name, target_name) not in index["field_rule_table_rows"]:
            return (
                "field_rule_table_row 不存在: "
                f"module={module_name}, feature={feature_name}, field={field_name}, table={table_name}, row={target_name}"
            )
        return None

    if target_type == "flow":
        if target_name not in index["flows"]:
            return f"flow 不存在: {target_name}"
        return None

    return f"未知 target_type: {target_type}"


def validate_evidence_and_traceability(
    evidence: dict[str, Any],
    traceability: dict[str, Any],
    structured_prd: dict[str, Any],
    testcase_ids: set[str],
    testcase_rows: dict[str, str],
) -> List[str]:
    errors: List[str] = []
    index = build_structured_index(structured_prd)
    errors.extend(validate_explicit_rule_fidelity(structured_prd, testcase_rows))

    evidence_items = evidence.get("evidence_items", [])
    evidence_by_id: dict[str, dict[str, Any]] = {}

    for item in evidence_items:
        evidence_id = item.get("evidence_id")
        if evidence_id in evidence_by_id:
            errors.append(f"[Evidence校验失败] evidence_id 重复: {evidence_id}")
            continue
        evidence_by_id[evidence_id] = item

        status = item.get("status")
        targets = item.get("structured_targets", [])
        actionability = item.get("actionability")

        if status in {"covered", "mapped"} and not targets:
            errors.append(f"[Evidence校验失败] {evidence_id} 已映射但缺少 structured_targets")

        for target in targets:
            target_error = validate_target_exists(target, index)
            if target_error:
                errors.append(f"[Evidence校验失败] {evidence_id}: {target_error}")

        if actionability in {"interaction", "input", "display", "data_rule", "state_rule"} and status == "covered":
            record = next(
                (row for row in traceability.get("records", []) if row.get("evidence_id") == evidence_id),
                None,
            )
            if record is None or not record.get("testcase_ids"):
                errors.append(f"[Evidence校验失败] {evidence_id} 为可测试证据，但未在 traceability 中关联 testcase")

        if item.get("evidence_source_type") == "explicit_text" and item.get("priority") == "high":
            record = next(
                (row for row in traceability.get("records", []) if row.get("evidence_id") == evidence_id),
                None,
            )
            linked_rows = [
                testcase_rows[testcase_id]
                for testcase_id in (record.get("testcase_ids", []) if record else [])
                if testcase_id in testcase_rows
            ]
            assert_keywords = item.get("assert_keywords", [])
            if assert_keywords and linked_rows:
                if not any(all(keyword in row_text for keyword in assert_keywords) for row_text in linked_rows):
                    errors.append(
                        f"[Evidence校验失败] {evidence_id} 高优先级显式规则未在关联 testcase 中完整体现关键词: {assert_keywords}"
                    )
            forbidden_keywords = item.get("forbidden_keywords", [])
            for keyword in forbidden_keywords:
                if any(keyword in row_text for row_text in linked_rows):
                    errors.append(
                        f"[Evidence校验失败] {evidence_id} 高优先级显式规则命中了禁止关键词: {keyword}"
                    )

    seen_record_ids: set[str] = set()
    for record in traceability.get("records", []):
        record_id = record.get("record_id")
        evidence_id = record.get("evidence_id")

        if record_id in seen_record_ids:
            errors.append(f"[Traceability校验失败] record_id 重复: {record_id}")
        seen_record_ids.add(record_id)

        if evidence_id not in evidence_by_id:
            errors.append(f"[Traceability校验失败] evidence_id 不存在: {evidence_id}")
            continue

        for target in record.get("structured_targets", []):
            target_error = validate_target_exists(target, index)
            if target_error:
                errors.append(f"[Traceability校验失败] {record_id}: {target_error}")

        for testcase_id in record.get("testcase_ids", []):
            if testcase_id not in testcase_ids:
                errors.append(f"[Traceability校验失败] {record_id} 引用了不存在的 testcase: {testcase_id}")

        coverage_level = record.get("coverage_level")
        if coverage_level == "full" and not record.get("testcase_ids"):
            errors.append(f"[Traceability校验失败] {record_id} coverage_level=full 但未关联 testcase")

    return errors


def extract_feature_rows_by_context(testcase_path: Path) -> dict[tuple[str, str], list[dict[str, str]]]:
    parsed = parse_testcase_document(testcase_path.read_text(encoding="utf-8"), strict=False)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in parsed["rows"]:
        key = (row.get("所属模块", "").strip(), row.get("所属功能点", "").strip())
        grouped.setdefault(key, []).append(row)
    return grouped


def build_feature_index(structured_prd: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
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


def build_feature_candidate_text(feature: dict[str, Any], grouped_rows: dict[tuple[str, str], list[dict[str, str]]]) -> str:
    module_name = str(feature.get("module_name", "")).strip()
    feature_name = str(feature.get("feature_name", "")).strip()
    candidate_rows = grouped_rows.get((module_name, feature_name), [])
    return normalize_text(
        " ".join(
            " ".join(str(v) for k, v in row.items() if not k.startswith("__"))
            for row in candidate_rows
        )
    )


def normalize_condition_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return ""


def iter_canonical_fields(feature: dict[str, Any]) -> list[dict[str, Any]]:
    fields = feature.get("fields", [])
    if isinstance(fields, list) and fields:
        return [field for field in fields if isinstance(field, dict)]
    field_definitions = feature.get("field_definitions", [])
    if isinstance(field_definitions, list):
        return [field for field in field_definitions if isinstance(field, dict)]
    return []


def build_feature_rule_requirements(feature: dict[str, Any]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    field_label_map: dict[str, str] = {}

    for field in iter_canonical_fields(feature):
        field_name = str(field.get("field_name") or field.get("name") or "").strip()
        display_name = str(field.get("display_name") or field.get("display") or "").strip()
        if not field_name and not display_name:
            continue

        field_label = display_name or field_name
        if field_name:
            field_label_map[field_name] = field_label
        condition_specs = [
            ("conditional_required", "required_when", "条件必填"),
            ("conditional_visibility", "visible_when", "条件展示"),
            ("conditional_editability", "editable_when", "条件可编辑"),
            ("conditional_readonly", "readonly_when", "条件只读"),
        ]
        for rule_type, key, label in condition_specs:
            condition_text = normalize_condition_value(field.get(key))
            if condition_text:
                requirements.append(
                    {
                        "source": "field",
                        "rule_type": rule_type,
                        "module_name": str(feature.get("module_name", "")).strip(),
                        "feature_name": str(feature.get("feature_name", "")).strip(),
                        "field_name": field_name,
                        "field_label": field_label,
                        "required_tokens": [field_label, condition_text],
                        "message": f"{label}规则未被 testcase 承接",
                    }
                )

        constraint_tokens: list[str] = []
        if field.get("max_length") not in ("", None):
            constraint_tokens.append(str(field.get("max_length")))
        if field.get("min") not in ("", None):
            constraint_tokens.append(str(field.get("min")))
        if field.get("max") not in ("", None):
            constraint_tokens.append(str(field.get("max")))
        if field.get("integer_only") is True:
            constraint_tokens.append("整数")
        formats = field.get("formats", [])
        if isinstance(formats, list):
            constraint_tokens.extend(str(item).strip() for item in formats if str(item).strip())
        if field.get("max_count") not in ("", None):
            constraint_tokens.append(str(field.get("max_count")))
        if constraint_tokens:
            requirements.append(
                {
                    "source": "field",
                    "rule_type": "value_constraint",
                    "module_name": str(feature.get("module_name", "")).strip(),
                    "feature_name": str(feature.get("feature_name", "")).strip(),
                    "field_name": field_name,
                    "field_label": field_label,
                    "required_tokens": [field_label, *constraint_tokens],
                    "message": "数值/长度约束未被 testcase 承接",
                }
            )

        data_source_tokens: list[str] = []
        for key in ("data_source", "filter", "display", "order_by"):
            value = normalize_condition_value(field.get(key))
            if value:
                data_source_tokens.append(value)
        if data_source_tokens:
            requirements.append(
                {
                    "source": "field",
                    "rule_type": "data_source_constraint",
                    "module_name": str(feature.get("module_name", "")).strip(),
                    "feature_name": str(feature.get("feature_name", "")).strip(),
                    "field_name": field_name,
                    "field_label": field_label,
                    "required_tokens": [field_label, *data_source_tokens],
                    "message": "数据源过滤/展示/排序规则未被 testcase 承接",
                }
            )

    for rule in feature.get("rules", []):
        if not isinstance(rule, dict):
            continue
        rule_type = str(rule.get("rule_type", "")).strip()
        if rule_type not in {
            "conditional_required",
            "conditional_visibility",
            "conditional_editability",
            "conditional_readonly",
            "value_constraint",
            "data_source_constraint",
        }:
            continue
        field_name = str(rule.get("field_name", "")).strip()
        field_label = field_label_map.get(field_name, "") or str(rule.get("target", "")).strip() or str(rule.get("name", "")).strip() or field_name
        tokens = [field_label] if field_label else []
        if rule_type == "conditional_required":
            condition_text = normalize_condition_value(rule.get("required_when") or rule.get("condition"))
            if condition_text:
                tokens.append(condition_text)
        elif rule_type == "conditional_visibility":
            condition_text = normalize_condition_value(rule.get("visible_when") or rule.get("condition"))
            if condition_text:
                tokens.append(condition_text)
        elif rule_type == "conditional_editability":
            condition_text = normalize_condition_value(rule.get("editable_when") or rule.get("condition"))
            if condition_text:
                tokens.append(condition_text)
        elif rule_type == "conditional_readonly":
            condition_text = normalize_condition_value(rule.get("readonly_when") or rule.get("condition"))
            if condition_text:
                tokens.append(condition_text)
        elif rule_type == "value_constraint":
            for key in ("max_length", "min", "max"):
                value = normalize_condition_value(rule.get(key))
                if value:
                    tokens.append(value)
            if rule.get("integer_only") is True:
                tokens.append("整数")
            for item in rule.get("formats", []) if isinstance(rule.get("formats", []), list) else []:
                if str(item).strip():
                    tokens.append(str(item).strip())
            if rule.get("max_count") not in ("", None):
                tokens.append(str(rule.get("max_count")))
        elif rule_type == "data_source_constraint":
            for key in ("data_source", "filter", "display", "order_by"):
                value = normalize_condition_value(rule.get(key))
                if value:
                    tokens.append(value)
        requirements.append(
            {
                "source": "rule",
                "rule_type": rule_type,
                "module_name": str(feature.get("module_name", "")).strip(),
                "feature_name": str(feature.get("feature_name", "")).strip(),
                "field_name": field_name,
                "field_label": field_label,
                "required_tokens": [token for token in tokens if token],
                "message": f"{rule_type} 规则未被 testcase 承接",
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for requirement in requirements:
        key = (
            requirement.get("rule_type", ""),
            requirement.get("module_name", ""),
            requirement.get("feature_name", ""),
            " | ".join(requirement.get("required_tokens", [])),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(requirement)
    return deduped


def validate_high_value_rule_projection(
    evidence: dict[str, Any],
    structured_prd: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    structured_text = normalize_text(json.dumps(structured_prd, ensure_ascii=False))
    projected_text = normalize_text(
        json.dumps(
            {
                "pages": structured_prd.get("pages", []),
                "modules": structured_prd.get("modules", []),
                "flows": structured_prd.get("flows", []),
            },
            ensure_ascii=False,
        )
    )

    for item in evidence.get("evidence_items", []):
        if not isinstance(item, dict):
            continue
        if item.get("evidence_source_type") != "explicit_text" or item.get("priority") != "high":
            continue
        evidence_id = str(item.get("evidence_id", "")).strip() or "UNKNOWN"
        assert_keywords = [str(keyword).strip() for keyword in item.get("assert_keywords", []) if str(keyword).strip()]
        if assert_keywords and not all(normalize_text(keyword) in structured_text for keyword in assert_keywords):
            errors.append(
                f"[规则承接告警] {evidence_id} 高价值原始规则未完整进入 structured_prd: {assert_keywords}"
            )
        if assert_keywords and not any(normalize_text(keyword) in projected_text for keyword in assert_keywords):
            errors.append(
                f"[规则投影告警] {evidence_id} 高价值原始规则未投影到 pages/modules/flows 可执行结构: {assert_keywords}"
            )

    for rule in structured_prd.get("requirement_info", {}).get("explicit_rules", []):
        if not isinstance(rule, dict) or rule.get("priority") != "high":
            continue
        rule_id = str(rule.get("rule_id", "")).strip() or "UNKNOWN"
        fidelity_values = [
            str(point.get("value", "")).strip()
            for point in rule.get("fidelity_points", [])
            if isinstance(point, dict) and str(point.get("value", "")).strip()
        ]
        if not fidelity_values:
            rule_text = str(rule.get("rule_text", "")).strip()
            if rule_text:
                fidelity_values = [rule_text]
        if fidelity_values and not any(normalize_text(value) in projected_text for value in fidelity_values):
            errors.append(
                f"[规则投影告警] {rule_id} 高优先级 explicit_rule 未投影到 pages/modules/flows 可执行结构: {fidelity_values}"
            )

    return errors


def validate_backend_modal_traceability(structured_prd: dict[str, Any], traceability: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    trace_field_attributes: set[tuple[str, str, str, str, str]] = set()
    trace_field_rules: set[tuple[str, str, str, str]] = set()

    for record in traceability.get("records", []):
        if not isinstance(record, dict):
            continue
        for target in record.get("structured_targets", []):
            if not isinstance(target, dict):
                continue
            target_type = target.get("target_type")
            module_name = str(target.get("module_name", "")).strip()
            feature_name = str(target.get("feature_name", "")).strip()
            field_name = str(target.get("field_name", "")).strip()
            target_name = str(target.get("target_name", "")).strip()
            attribute_name = str(target.get("attribute_name", "")).strip()
            if target_type == "field_attribute" and all([module_name, feature_name, field_name, attribute_name, target_name]):
                trace_field_attributes.add((module_name, feature_name, field_name, attribute_name, target_name))
            if target_type == "field_rule" and all([module_name, feature_name, field_name, target_name]):
                trace_field_rules.add((module_name, feature_name, field_name, target_name))

    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            page_name = str(feature.get("page_name", "")).strip()
            section_name = str(feature.get("section_name", "")).strip()
            feature_name = str(feature.get("feature_name", "")).strip()
            if page_name not in BACKEND_CONFIG_PAGES or section_name not in BACKEND_MODAL_SECTIONS:
                continue
            for field in feature.get("field_definitions", []):
                if not isinstance(field, dict):
                    continue
                field_name = str(field.get("field_name", "")).strip()
                if not field_name:
                    continue
                for attribute_name, target_name in derive_field_attribute_targets(field):
                    if (module_name, feature_name, field_name, attribute_name, target_name) not in trace_field_attributes:
                        errors.append(
                            "[Traceability校验失败] 后台配置页字段属性未建立 traceability: "
                            f"module={module_name}, feature={feature_name}, field={field_name}, "
                            f"attribute={attribute_name}, value={target_name}"
                        )
            for field_rule in feature.get("field_rules", []):
                if not isinstance(field_rule, dict):
                    continue
                field_name = str(field_rule.get("field_name", "")).strip()
                rule_text = str(field_rule.get("rule_text", "")).strip()
                if field_name and rule_text and (module_name, feature_name, field_name, rule_text) not in trace_field_rules:
                    errors.append(
                        "[Traceability校验失败] 后台配置页字段规则未建立 traceability: "
                        f"module={module_name}, feature={feature_name}, field={field_name}, rule={rule_text}"
                    )

    return errors


def validate_page_section_structure(structured_prd: dict[str, Any], testcase_path: Path) -> list[str]:
    errors: list[str] = []
    pages = structured_prd.get("pages", [])
    if not isinstance(pages, list) or not pages:
        return errors

    parsed = parse_testcase_document(testcase_path.read_text(encoding="utf-8"), strict=False)
    testcase_pages = set(parsed["page_names"])
    testcase_sections = {
        (table.get("page_name", ""), table.get("section_name", ""))
        for table in parsed["tables"]
        if table.get("rows")
    }

    expected_pages = set()
    expected_sections = set()
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_name = page.get("page_name")
        if not isinstance(page_name, str) or not page_name.strip():
            continue
        page_name = page_name.strip()
        expected_pages.add(page_name)
        for section in page.get("sections", []):
            if not isinstance(section, dict):
                continue
            section_name = section.get("section_name")
            if isinstance(section_name, str) and section_name.strip():
                expected_sections.add((page_name, section_name.strip()))

    if len(expected_pages) > 1:
        for page_name in sorted(expected_pages - testcase_pages):
            errors.append(f"[页面结构校验失败] testcase 未按页面分组输出: {page_name}")

    if len(expected_sections) > 1:
        for page_name, section_name in sorted(expected_sections - testcase_sections):
            errors.append(f"[板块结构校验失败] testcase 未按板块分组输出: 页面={page_name}, 板块={section_name}")

    return errors


def validate_field_rule_coverage(structured_prd: dict[str, Any], testcase_path: Path) -> list[str]:
    errors: list[str] = []
    grouped_rows = extract_feature_rows_by_context(testcase_path)

    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            feature_name = str(feature.get("feature_name", "")).strip()
            candidate_rows = grouped_rows.get((module_name, feature_name), [])
            candidate_text = normalize_text(
                " ".join(
                    " ".join(str(v) for k, v in row.items() if not k.startswith("__"))
                    for row in candidate_rows
                )
            )

            for field_rule in feature.get("field_rules", []):
                if not isinstance(field_rule, dict):
                    continue
                field_name = str(field_rule.get("field_name", "")).strip()
                rule_text = str(field_rule.get("rule_text", "")).strip()
                rule_type = str(field_rule.get("rule_type", "")).strip()
                if not field_name or not rule_text:
                    continue
                if not candidate_rows:
                    errors.append(
                        f"[字段覆盖校验失败] feature 未生成任何用例承接字段规则: module={module_name}, feature={feature_name}, field={field_name}"
                    )
                    continue
                page_name = str(feature.get("page_name", "")).strip()
                section_name = str(feature.get("section_name", "")).strip()
                if page_name in BACKEND_CONFIG_PAGES and section_name in BACKEND_MODAL_SECTIONS:
                    matched_field = next(
                        (
                            field
                            for field in feature.get("field_definitions", [])
                            if isinstance(field, dict) and str(field.get("field_name", "")).strip() == field_name
                        ),
                        None,
                    )
                    attribute_targets = derive_field_attribute_targets(matched_field or {})
                    if rule_type not in {
                        "conditional_visibility_rule",
                        "conditional_editability_rule",
                        "conditional_required_rule",
                    } and attribute_targets:
                        field_display_name = str((matched_field or {}).get("display_name", "")).strip()
                        if (
                            normalize_text(field_display_name or field_name) in candidate_text
                            and any(normalize_text(target_name) in candidate_text for _, target_name in attribute_targets)
                        ):
                            continue
                if normalize_text(rule_text) not in candidate_text and normalize_text(field_name) not in candidate_text:
                    errors.append(
                        f"[字段覆盖校验失败] 字段规则未被 testcase 承接: module={module_name}, feature={feature_name}, field={field_name}, rule={rule_text}"
                    )

            for field_rule_table in feature.get("field_rule_tables", []):
                if not isinstance(field_rule_table, dict):
                    continue
                field_name = str(field_rule_table.get("field_name", "")).strip()
                table_name = str(field_rule_table.get("table_name", "")).strip()
                for row in field_rule_table.get("rows", []):
                    if not isinstance(row, dict):
                        continue
                    row_name = str(row.get("row_name", "")).strip()
                    rule_text = str(row.get("rule_text", "")).strip()
                    if not row_name:
                        continue
                    if not candidate_rows:
                        errors.append(
                            f"[字段覆盖校验失败] 字段说明表未生成任何用例承接: module={module_name}, feature={feature_name}, table={table_name}"
                        )
                        continue
                    if normalize_text(row_name) not in candidate_text and (rule_text and normalize_text(rule_text) not in candidate_text):
                        errors.append(
                            f"[字段覆盖校验失败] 字段说明表行未被 testcase 承接: module={module_name}, feature={feature_name}, field={field_name}, row={row_name}"
                        )

    return errors


def validate_field_attribute_coverage(
    structured_prd: dict[str, Any],
    traceability: dict[str, Any],
    testcase_rows: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    index = build_structured_index(structured_prd)
    feature_index = build_feature_index(structured_prd)

    for record in traceability.get("records", []):
        if not isinstance(record, dict):
            continue
        linked_texts = [
            testcase_rows[testcase_id]
            for testcase_id in record.get("testcase_ids", [])
            if testcase_id in testcase_rows
        ]
        candidate_text = normalize_text(" ".join(linked_texts))
        for target in record.get("structured_targets", []):
            if not isinstance(target, dict):
                continue
            if target.get("target_type") != "field_attribute":
                continue
            module_name = str(target.get("module_name", "")).strip()
            feature_name = str(target.get("feature_name", "")).strip()
            field_name = str(target.get("field_name", "")).strip()
            target_name = str(target.get("target_name", "")).strip()
            display_name = index["field_display_names"].get((module_name, feature_name, field_name), "")
            feature = feature_index.get((module_name, feature_name), {})
            if not candidate_text:
                grouped_text = " ".join(
                    testcase_rows[testcase_id]
                    for testcase_id, row_text in testcase_rows.items()
                    if normalize_text(module_name) in normalize_text(row_text)
                    and normalize_text(feature_name) in normalize_text(row_text)
                )
                candidate_text = normalize_text(grouped_text)
            if target_name and normalize_text(target_name) not in candidate_text:
                errors.append(
                    "[字段属性覆盖校验失败] 字段属性未被 testcase 原词承接: "
                    f"module={module_name}, feature={feature_name}, field={field_name}, value={target_name}"
                )
            if display_name and normalize_text(display_name) not in candidate_text and normalize_text(field_name) not in candidate_text:
                errors.append(
                    "[字段属性覆盖校验失败] testcase 未显式提及字段名: "
                    f"module={module_name}, feature={feature_name}, field={display_name or field_name}, "
                    f"attribute={target.get('attribute_name', '')}"
                )

    return errors


def validate_rule_structure_coverage(structured_prd: dict[str, Any], testcase_path: Path) -> list[str]:
    errors: list[str] = []
    grouped_rows = extract_feature_rows_by_context(testcase_path)

    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            feature = dict(feature)
            feature["module_name"] = module_name
            feature_name = str(feature.get("feature_name", "")).strip()
            candidate_text = build_feature_candidate_text(feature, grouped_rows)
            page_name = str(feature.get("page_name", "")).strip()
            section_name = str(feature.get("section_name", "")).strip()
            backend_prefix = "后台配置页" if page_name in BACKEND_CONFIG_PAGES and section_name in BACKEND_MODAL_SECTIONS else "通用"

            for requirement in build_feature_rule_requirements(feature):
                tokens = [normalize_text(token) for token in requirement.get("required_tokens", []) if normalize_text(token)]
                if not tokens:
                    continue
                missing_tokens = [token for token in tokens if token not in candidate_text]
                if not missing_tokens:
                    continue

                rule_type = str(requirement.get("rule_type", "")).strip()
                if rule_type == "conditional_required":
                    label = "conditional_required"
                elif rule_type == "conditional_visibility":
                    label = "conditional_visibility"
                elif rule_type in {"conditional_editability", "conditional_readonly"}:
                    label = "conditional_editability/readonly"
                elif rule_type == "value_constraint":
                    label = "value_constraint"
                elif rule_type == "data_source_constraint":
                    label = "data_source_constraint"
                else:
                    label = rule_type or "rule"

                field_name = str(requirement.get("field_name", "")).strip()
                field_label = str(requirement.get("field_label", "")).strip() or field_name
                errors.append(
                    f"[规则覆盖告警] {backend_prefix} {label} 缺失: "
                    f"module={module_name}, feature={feature_name}, field={field_label}, "
                    f"missing_tokens={requirement.get('required_tokens', [])}"
                )

    return errors


def validate_coverage_first_traceability(
    coverage_first_traceability: dict[str, Any],
    testcase_ids: set[str],
    coverage_ids: set[str],
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    invalid_record_count = 0
    seen_record_ids: set[str] = set()

    for record in coverage_first_traceability.get("records", []):
        record_id = str(record.get("record_id", "")).strip()
        if record_id in seen_record_ids:
            errors.append(f"[CoverageFirstTraceability校验失败] record_id 重复: {record_id}")
            invalid_record_count += 1
        seen_record_ids.add(record_id)

        if str(record.get("coverage_id", "")).strip() not in coverage_ids:
            errors.append(f"[CoverageFirstTraceability校验失败] coverage_id 不存在: {record.get('coverage_id', '')}")
            invalid_record_count += 1
        if not str(record.get("rule_id", "")).strip():
            errors.append(f"[CoverageFirstTraceability校验失败] rule_id 为空: {record_id}")
            invalid_record_count += 1
        testcase_id = str(record.get("testcase_id", "")).strip()
        if not testcase_id or testcase_id not in testcase_ids:
            errors.append(f"[CoverageFirstTraceability校验失败] {record_id} 引用了不存在的 testcase: {testcase_id}")
            invalid_record_count += 1

    total = len(coverage_first_traceability.get("records", []))
    summary = {
        "record_count": total,
        "invalid_record_count": invalid_record_count,
        "false_traceability_rate": round((invalid_record_count / total), 4) if total else 0.0,
    }
    return errors, summary


def validate_traceability_adapter(
    traceability_adapter: dict[str, Any],
    testcase_ids: set[str],
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    invalid_record_count = 0
    for record in traceability_adapter.get("records", []):
        gap_notes = str(record.get("gap_notes", "")).strip()
        if "adapter_source=coverage_first_traceability" not in gap_notes:
            errors.append(f"[TraceabilityAdapter校验失败] 缺少 adapter_source 标记: {record.get('record_id', '')}")
            invalid_record_count += 1
        for testcase_id in record.get("testcase_ids", []):
            if testcase_id not in testcase_ids:
                errors.append(f"[TraceabilityAdapter校验失败] 引用了不存在的 testcase: {testcase_id}")
                invalid_record_count += 1
    total = len(traceability_adapter.get("records", []))
    summary = {
        "record_count": total,
        "invalid_record_count": invalid_record_count,
    }
    return errors, summary


def validate_enum_fidelity(structured_prd: dict[str, Any], testcase_path: Path) -> list[str]:
    errors: list[str] = []
    has_page_section_model = bool(structured_prd.get("pages"))
    has_field_rule_model = False
    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            if feature.get("field_rules") or feature.get("field_rule_tables"):
                has_field_rule_model = True
                break
        if has_field_rule_model:
            break

    if not has_page_section_model and not has_field_rule_model:
        return errors

    grouped_rows = extract_feature_rows_by_context(testcase_path)

    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            feature_name = str(feature.get("feature_name", "")).strip()
            candidate_rows = grouped_rows.get((module_name, feature_name), [])
            candidate_text = normalize_text(
                " ".join(
                    " ".join(str(v) for k, v in row.items() if not k.startswith("__"))
                    for row in candidate_rows
                )
            )
            for field in feature.get("field_definitions", []):
                if not isinstance(field, dict):
                    continue
                display_name = str(field.get("display_name", "")).strip()
                field_name = str(field.get("field_name", "")).strip()
                enum_values = field.get("enum_values", [])
                if not isinstance(enum_values, list) or not enum_values:
                    continue
                if "状态" not in display_name and "status" not in field_name:
                    continue
                for enum_value in enum_values:
                    if isinstance(enum_value, str) and enum_value.strip():
                        if normalize_text(enum_value) not in candidate_text:
                            errors.append(
                                f"[枚举保真校验失败] 状态字段枚举未在 testcase 中原词保留: module={module_name}, feature={feature_name}, field={display_name or field_name}, enum={enum_value}"
                            )

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 evidence_inventory 与 traceability_matrix")
    parser.add_argument("--evidence", required=True, help="evidence_inventory.json 路径")
    parser.add_argument("--traceability", required=False, help="traceability_matrix.json 路径")
    parser.add_argument("--structured-prd", required=True, help="structured_prd.json 路径")
    parser.add_argument("--testcases", required=True, help="testcases.md 路径")
    parser.add_argument("--evidence-schema", required=False, help="evidence schema 路径")
    parser.add_argument("--traceability-schema", required=False, help="traceability schema 路径")
    parser.add_argument("--coverage-matrix", required=False, help="coverage_matrix.json 路径")
    parser.add_argument("--coverage-first-traceability", required=False, help="coverage_first_traceability.json 路径")
    parser.add_argument("--coverage-first-schema", required=False, help="coverage-first traceability schema 路径")
    parser.add_argument("--traceability-adapter", required=False, help="traceability_adapter.json 路径")
    parser.add_argument("--primary-only", action="store_true", help="只校验 coverage_first / adapter 主链，跳过 legacy traceability 对照")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    evidence_schema_path = (
        Path(args.evidence_schema).resolve()
        if args.evidence_schema
        else root / "schemas" / "evidence_inventory.schema.json"
    )
    traceability_schema_path = (
        Path(args.traceability_schema).resolve()
        if args.traceability_schema
        else root / "schemas" / "traceability_matrix.schema.json"
    )
    coverage_first_schema_path = (
        Path(args.coverage_first_schema).resolve()
        if args.coverage_first_schema
        else root / "schemas" / "coverage_first_traceability.schema.json"
    )

    try:
        evidence = load_json(Path(args.evidence).resolve())
        if not args.traceability and not args.primary_only:
            raise ValueError("非 primary-only 模式必须提供 --traceability")
        traceability = load_json(Path(args.traceability).resolve()) if args.traceability else {"records": []}
        structured_prd = load_json(Path(args.structured_prd).resolve())
        evidence_schema = load_json(evidence_schema_path)
        traceability_schema = load_json(traceability_schema_path) if args.traceability or args.traceability_adapter else {}
        testcase_path = Path(args.testcases).resolve()
        testcase_ids = parse_testcase_ids(testcase_path)
        testcase_rows = parse_testcase_rows(testcase_path)
        coverage_matrix = load_json(Path(args.coverage_matrix).resolve()) if args.coverage_matrix else None
        coverage_first_traceability = load_json(Path(args.coverage_first_traceability).resolve()) if args.coverage_first_traceability else None
        coverage_first_schema = load_json(coverage_first_schema_path) if args.coverage_first_traceability else None
        traceability_adapter = load_json(Path(args.traceability_adapter).resolve()) if args.traceability_adapter else None
    except Exception as exc:
        print(f"读取输入失败: {exc}", file=sys.stderr)
        return 1

    primary_errors: List[str] = []
    legacy_errors: List[str] = []
    primary_errors.extend(validate_schema(evidence, evidence_schema))
    if not args.primary_only:
        legacy_errors.extend(validate_schema(traceability, traceability_schema))
        legacy_errors.extend(validate_high_value_rule_projection(evidence, structured_prd))
        legacy_errors.extend(validate_evidence_and_traceability(evidence, traceability, structured_prd, testcase_ids, testcase_rows))
        legacy_errors.extend(validate_backend_modal_traceability(structured_prd, traceability))
        legacy_errors.extend(validate_page_section_structure(structured_prd, testcase_path))
        legacy_errors.extend(validate_field_rule_coverage(structured_prd, testcase_path))
        legacy_errors.extend(validate_field_attribute_coverage(structured_prd, traceability, testcase_rows))
        legacy_errors.extend(validate_rule_structure_coverage(structured_prd, testcase_path))
        legacy_errors.extend(validate_enum_fidelity(structured_prd, testcase_path))
    coverage_first_summary: dict[str, Any] | None = None
    traceability_adapter_summary: dict[str, Any] | None = None
    if coverage_first_traceability is not None:
        primary_errors.extend(validate_schema(coverage_first_traceability, coverage_first_schema))
        coverage_ids = {
            str(entry.get("coverage_id", "")).strip()
            for entry in (coverage_matrix or {}).get("entries", [])
            if str(entry.get("coverage_id", "")).strip()
        }
        extra_errors, coverage_first_summary = validate_coverage_first_traceability(
            coverage_first_traceability,
            testcase_ids,
            coverage_ids,
        )
        primary_errors.extend(extra_errors)
    if traceability_adapter is not None:
        primary_errors.extend(validate_schema(traceability_adapter, traceability_schema))
        adapter_errors, traceability_adapter_summary = validate_traceability_adapter(traceability_adapter, testcase_ids)
        primary_errors.extend(adapter_errors)

    has_primary_mode = coverage_first_traceability is not None or traceability_adapter is not None or args.primary_only

    if args.primary_only and coverage_first_traceability is None and traceability_adapter is None:
        primary_errors.append("primary-only 模式必须提供 coverage_first_traceability 或 traceability_adapter")

    if primary_errors:
        print("❌ Traceability 资产校验失败", file=sys.stderr)
        if coverage_first_summary is not None:
            print(
                f"[CoverageFirstTraceability对照] records={coverage_first_summary['record_count']}, "
                f"false_traceability_rate={coverage_first_summary['false_traceability_rate']}",
                file=sys.stderr,
            )
        if traceability_adapter_summary is not None:
            print(
                f"[TraceabilityAdapter对照] records={traceability_adapter_summary['record_count']}, "
                f"invalid_record_count={traceability_adapter_summary['invalid_record_count']}",
                file=sys.stderr,
            )
        for error in primary_errors:
            print(error, file=sys.stderr)
        return 1

    if legacy_errors and has_primary_mode:
        print("⚠️ Traceability 主校验通过，legacy 对照仍存在噪音", file=sys.stderr)
        if coverage_first_summary is not None:
            print(
                f"[CoverageFirstTraceability主结果] records={coverage_first_summary['record_count']}, "
                f"false_traceability_rate={coverage_first_summary['false_traceability_rate']}",
                file=sys.stderr,
            )
        if traceability_adapter_summary is not None:
            print(
                f"[TraceabilityAdapter兼容层] records={traceability_adapter_summary['record_count']}, "
                f"invalid_record_count={traceability_adapter_summary['invalid_record_count']}",
                file=sys.stderr,
            )
        print(f"[LegacyTraceability对照] issue_count={len(legacy_errors)}", file=sys.stderr)
        for error in legacy_errors:
            print(error, file=sys.stderr)
        print("✅ Traceability 资产主校验通过")
        print(f"evidence_items: {len(evidence.get('evidence_items', []))}")
        print(f"traceability_records: {len(traceability.get('records', []))}")
        print(f"testcase_ids: {len(testcase_ids)}")
        if coverage_first_summary is not None:
            print(f"coverage_first_traceability_records: {coverage_first_summary['record_count']}")
            print(f"coverage_first_false_traceability_rate: {coverage_first_summary['false_traceability_rate']}")
        if traceability_adapter_summary is not None:
            print(f"traceability_adapter_records: {traceability_adapter_summary['record_count']}")
        return 0

    if legacy_errors:
        print("❌ Traceability 资产校验失败", file=sys.stderr)
        for error in legacy_errors:
            print(error, file=sys.stderr)
        return 1

    print("✅ Traceability 资产校验通过")
    print(f"evidence_items: {len(evidence.get('evidence_items', []))}")
    print(f"traceability_records: {len(traceability.get('records', []))}")
    print(f"testcase_ids: {len(testcase_ids)}")
    if coverage_first_summary is not None:
        print(f"coverage_first_traceability_records: {coverage_first_summary['record_count']}")
        print(f"coverage_first_false_traceability_rate: {coverage_first_summary['false_traceability_rate']}")
    if traceability_adapter_summary is not None:
        print(f"traceability_adapter_records: {traceability_adapter_summary['record_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
