#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from coverage_testcase_generator import generate_testcases_markdown
from structured_prd_markdown_utils import normalize_structured_prd


ROOT = Path(__file__).resolve().parents[1]

HEADERS = [
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

PAGE_CODE_MAP = {
    "小程序导航配置页": "MPCONFIG",
    "小程序banner配置页": "MPCONFIG",
    "小程序瓷片区配置页": "MPCONFIG",
    "小程序金刚区配置页": "MPCONFIG",
    "小程序弹窗配置页": "MPCONFIG",
    "小程序首页改版页": "MINIHOME",
    "小程序首页-企微单人单码弹窗页": "MINIHOME",
    "小程序首页-营销弹窗页": "MKTPOP",
}

MODULE_CODE_MAP = {
    "小程序导航配置": "NAVCFG",
    "小程序banner配置": "BANNER",
    "小程序瓷片区配置": "TILE",
    "小程序金刚区配置": "ICON",
    "小程序弹窗配置": "POPUP",
    "小程序首页分发页": "BANNER",
    "企微单人单码弹窗": "QRCODEPOP",
    "营销弹窗": "MKTPOP",
}

TYPE_CODE_MAP = {
    "功能": "FN",
    "边界": "BD",
    "异常": "AB",
    "权限": "PM",
    "流程验证": "FL",
    "状态流转": "ST",
    "数据校验": "DV",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_code(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper()) or "GEN"


def page_code(page_name: str) -> str:
    for key, value in PAGE_CODE_MAP.items():
        if key in page_name:
            return value
    return normalize_code(page_name)[:12]


def module_code(module_name: str) -> str:
    for key, value in MODULE_CODE_MAP.items():
        if key in module_name:
            return value
    return normalize_code(module_name)[:12]


def terminal_code(page_name: str) -> str:
    return "ADMIN" if "配置页" in page_name else "MINI"


def case_tags(case_type: str, is_flow: bool = False) -> str:
    if case_type == "数据校验":
        base = ["AI-API用例", "开发必测"]
    else:
        base = ["AI-UI用例"]
    if is_flow:
        base = ["核心链路", "黄金用例", "AI-UI用例", "开发必测", "测试必测"]
    return ",".join(base)


def case_priority(case_type: str, is_flow: bool = False) -> str:
    if is_flow:
        return "P0"
    if case_type == "边界":
        return "P1"
    if case_type == "数据校验":
        return "P1"
    return "P1"


def case_id(project_code: str, page_name: str, module_name: str, case_type: str, seq: int) -> str:
    return f"{project_code}-{page_code(page_name)}-{module_code(module_name)}-{terminal_code(page_name)}-{TYPE_CODE_MAP[case_type]}-{seq:03d}"


def html_lines(lines: list[str]) -> str:
    return "<br>".join(f"{idx}. {line}" for idx, line in enumerate(lines, start=1))


def field_label(field: dict[str, Any]) -> str:
    return str(field.get("display_name") or field.get("display") or field.get("field_name") or field.get("name") or "字段").strip()


def field_name(field: dict[str, Any]) -> str:
    return str(field.get("field_name") or field.get("name") or "").strip()


def condition_text(value: Any) -> str:
    if value in (None, "", []):
        return ""
    if isinstance(value, str):
        text = value.strip()
        return "" if text.lower() == "none" else text
    if isinstance(value, list):
        return "、".join(str(item).strip() for item in value if str(item).strip())
    text = str(value).strip()
    return "" if text.lower() == "none" else text


def infer_required_when(field: dict[str, Any]) -> str:
    explicit = condition_text(field.get("required_when"))
    if explicit:
        return explicit
    if field.get("required") is True and field.get("visible_when"):
        return condition_text(field.get("visible_when"))
    return ""


def normalize_condition_for_title(text: str) -> str:
    normalized = condition_text(text)
    replacements = [
        ("时展示", ""),
        ("时显示", ""),
        ("时可编辑", ""),
        ("时只读", ""),
        ("时可配置当前项", ""),
        ("时，可配置当前项", ""),
        ("时允许编辑", ""),
        ("时不允许编辑", ""),
    ]
    for old, new in replacements:
        normalized = normalized.replace(old, new)
    return normalized.strip("，,；; ")


def normalized_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [condition_text(item) for item in value if condition_text(item)]
    text = condition_text(value)
    return [text] if text else []


def order_title_text(value: Any) -> str:
    text = condition_text(value)
    if not text:
        return ""
    return text if text.startswith("按") else f"按{text}"


def field_lookup(feature: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        field_name(field): field
        for field in feature_fields(feature)
        if field_name(field)
    }


def rule_objects(feature: dict[str, Any]) -> list[dict[str, Any]]:
    return [rule for rule in feature.get("rules", []) if isinstance(rule, dict)]


def label_for_rule(rule: dict[str, Any], fields: dict[str, dict[str, Any]]) -> str:
    fname = str(rule.get("field_name") or rule.get("target") or "").strip()
    if fname and fname in fields:
        return field_label(fields[fname])
    return fname or "字段"


def add_case(
    cases: list[dict[str, str]],
    case_keys: set[tuple[str, str]],
    case_data: dict[str, str],
) -> None:
    key = (case_data["用例标题"], case_data["备注"])
    if key in case_keys:
        return
    case_keys.add(key)
    cases.append(case_data)


def feature_fields(feature: dict[str, Any]) -> list[dict[str, Any]]:
    fields = feature.get("fields", [])
    if isinstance(fields, list) and fields:
        return [field for field in fields if isinstance(field, dict)]
    return [field for field in feature.get("field_definitions", []) if isinstance(field, dict)]


def build_atomic_cases(project_code: str, module_name: str, feature: dict[str, Any]) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    page_name = str(feature.get("page_name", "")).strip()
    section_name = str(feature.get("section_name", "")).strip() or "未分组"
    feature_name = str(feature.get("feature_name", "")).strip()
    seq_counter = {"功能": 0, "边界": 0, "数据校验": 0}
    case_keys: set[tuple[str, str]] = set()
    fields = field_lookup(feature)

    def next_id(case_type: str) -> str:
        seq_counter[case_type] += 1
        return case_id(project_code, page_name, module_name, case_type, seq_counter[case_type])

    for field in feature_fields(feature):
        label = field_label(field)
        fname = field_name(field)
        required_when = infer_required_when(field)
        if required_when:
            condition = normalize_condition_for_title(required_when)
            add_case(
                cases,
                case_keys,
                {
                    "__page_name": page_name,
                    "__section_name": section_name,
                    "用例编号": next_id("功能"),
                    "所属模块": module_name,
                    "所属功能点": feature_name,
                    "用例标题": f"验证{condition}时{label}必填",
                    "前置条件": f"已进入{page_name}并打开{section_name}",
                    "测试步骤": html_lines(
                        [
                            f"设置页面条件满足`{required_when}`",
                            f"保持`{label}`为空并点击保存",
                            "观察页面校验提示与保存结果",
                        ]
                    ),
                    "预期结果": html_lines(
                        [
                            f"条件满足`{required_when}`时`{label}`按必填处理",
                            f"`{label}`为空时本次保存失败",
                            f"页面明确提示需补充`{label}`",
                        ]
                    ),
                    "优先级": case_priority("功能"),
                    "标签": case_tags("功能"),
                    "测试类型": "功能",
                    "备注": f"来源结构：fields.required_when/required+visible_when；field={fname}",
                },
            )
        elif field.get("required") is True:
            add_case(
                cases,
                case_keys,
                {
                    "__page_name": page_name,
                    "__section_name": section_name,
                    "用例编号": next_id("功能"),
                    "所属模块": module_name,
                    "所属功能点": feature_name,
                    "用例标题": f"验证{label}为空时保存失败",
                    "前置条件": f"已进入{page_name}并打开{section_name}",
                    "测试步骤": html_lines(
                        [
                            f"保持`{label}`为空",
                            "点击保存",
                            "观察页面校验提示与保存结果",
                        ]
                    ),
                    "预期结果": html_lines(
                        [
                            f"`{label}`按必填字段处理",
                            f"`{label}`为空时本次保存失败",
                            f"页面明确提示需补充`{label}`",
                        ]
                    ),
                    "优先级": case_priority("功能"),
                    "标签": case_tags("功能"),
                    "测试类型": "功能",
                    "备注": f"来源结构：fields.required=true；field={fname}",
                },
            )

    for rule in rule_objects(feature):
        rule_type = str(rule.get("rule_type", "")).strip()
        fname = str(rule.get("field_name") or rule.get("target") or "").strip()
        if not fname:
            continue
        label = label_for_rule(rule, fields)

        if rule_type == "conditional_required":
            required_when = condition_text(rule.get("required_when"))
            if not required_when:
                continue
            condition = normalize_condition_for_title(required_when)
            add_case(
                cases,
                case_keys,
                {
                    "__page_name": page_name,
                    "__section_name": section_name,
                    "用例编号": next_id("功能"),
                    "所属模块": module_name,
                    "所属功能点": feature_name,
                    "用例标题": f"验证{condition}时{label}必填",
                    "前置条件": f"已进入{page_name}并打开{section_name}",
                    "测试步骤": html_lines(
                        [
                            f"设置页面条件满足`{required_when}`",
                            f"保持`{label}`为空并点击保存",
                            "观察页面校验提示与保存结果",
                        ]
                    ),
                    "预期结果": html_lines(
                        [
                            f"条件满足`{required_when}`时`{label}`按必填处理",
                            f"`{label}`为空时本次保存失败",
                            f"页面明确提示需补充`{label}`",
                        ]
                    ),
                    "优先级": case_priority("功能"),
                    "标签": case_tags("功能"),
                    "测试类型": "功能",
                    "备注": f"来源结构：rules.conditional_required；field={fname}",
                },
            )
            continue

        if rule_type == "conditional_visibility":
            visible_when = condition_text(rule.get("visible_when"))
            if not visible_when:
                continue
            condition = normalize_condition_for_title(visible_when)
            add_case(
                cases,
                case_keys,
                {
                    "__page_name": page_name,
                    "__section_name": section_name,
                    "用例编号": next_id("功能"),
                    "所属模块": module_name,
                    "所属功能点": feature_name,
                    "用例标题": f"验证{condition}时展示{label}",
                    "前置条件": f"已进入{page_name}并打开{section_name}",
                    "测试步骤": html_lines(
                        [
                            f"先设置页面条件不满足`{visible_when}`",
                            f"再切换到满足`{visible_when}`",
                            f"观察`{label}`字段显隐变化",
                        ]
                    ),
                    "预期结果": html_lines(
                        [
                            f"条件不满足`{visible_when}`时页面不展示`{label}`",
                            f"条件满足`{visible_when}`时页面展示`{label}`",
                            f"`{label}`显隐与规则保持一致",
                        ]
                    ),
                    "优先级": case_priority("功能"),
                    "标签": case_tags("功能"),
                    "测试类型": "功能",
                    "备注": f"来源结构：rules.conditional_visibility；field={fname}",
                },
            )
            continue

        if rule_type == "conditional_editability":
            editable_when = condition_text(rule.get("editable_when"))
            if not editable_when:
                continue
            condition = normalize_condition_for_title(editable_when)
            add_case(
                cases,
                case_keys,
                {
                    "__page_name": page_name,
                    "__section_name": section_name,
                    "用例编号": next_id("功能"),
                    "所属模块": module_name,
                    "所属功能点": feature_name,
                    "用例标题": f"验证{condition}时{label}可编辑",
                    "前置条件": f"已进入{page_name}并打开{section_name}",
                    "测试步骤": html_lines(
                        [
                            f"设置页面条件满足`{editable_when}`",
                            f"尝试修改`{label}`的值",
                            "观察字段是否允许编辑并生效",
                        ]
                    ),
                    "预期结果": html_lines(
                        [
                            f"条件满足`{editable_when}`时`{label}`进入可编辑状态",
                            f"用户可以修改`{label}`的值",
                            f"`{label}`编辑行为与规则保持一致",
                        ]
                    ),
                    "优先级": case_priority("功能"),
                    "标签": case_tags("功能"),
                    "测试类型": "功能",
                    "备注": f"来源结构：rules.conditional_editability；field={fname}",
                },
            )
            continue

        if rule_type == "conditional_readonly":
            readonly_when = condition_text(rule.get("readonly_when"))
            if not readonly_when:
                continue
            condition = normalize_condition_for_title(readonly_when)
            add_case(
                cases,
                case_keys,
                {
                    "__page_name": page_name,
                    "__section_name": section_name,
                    "用例编号": next_id("功能"),
                    "所属模块": module_name,
                    "所属功能点": feature_name,
                    "用例标题": f"验证{condition}时{label}只读",
                    "前置条件": f"已进入{page_name}并打开{section_name}",
                    "测试步骤": html_lines(
                        [
                            f"设置页面条件满足`{readonly_when}`",
                            f"尝试修改`{label}`的值",
                            "观察字段是否仍保持只读",
                        ]
                    ),
                    "预期结果": html_lines(
                        [
                            f"条件满足`{readonly_when}`时`{label}`进入只读状态",
                            f"用户无法修改`{label}`的值",
                            f"`{label}`只读行为与规则保持一致",
                        ]
                    ),
                    "优先级": case_priority("功能"),
                    "标签": case_tags("功能"),
                    "测试类型": "功能",
                    "备注": f"来源结构：rules.conditional_readonly；field={fname}",
                },
            )
            continue

        if rule_type == "value_constraint":
            max_length = rule.get("max_length")
            if max_length not in ("", None):
                next_length = int(max_length) + 1 if str(max_length).isdigit() else f"{max_length}+1"
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("边界"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}长度等于{max_length}时允许保存",
                        "前置条件": f"已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"向`{label}`输入{max_length}个字符",
                                "点击保存",
                                "观察保存结果",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`输入长度等于{max_length}时可提交保存请求",
                                "本次提交不触发长度告警",
                                f"`{label}`长度上限仍保持为{max_length}",
                            ]
                        ),
                        "优先级": case_priority("边界"),
                        "标签": case_tags("边界"),
                        "测试类型": "边界",
                        "备注": f"来源结构：rules.value_constraint.max_length={max_length}；field={fname}",
                    },
                )
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("边界"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}长度超过{max_length}时保存失败",
                        "前置条件": f"已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"向`{label}`输入{next_length}个字符",
                                "点击保存",
                                "观察校验提示与保存结果",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`长度超过{max_length}时触发长度校验",
                                "本次保存失败",
                                f"页面提示`{label}`超出允许长度",
                            ]
                        ),
                        "优先级": case_priority("边界"),
                        "标签": case_tags("边界"),
                        "测试类型": "边界",
                        "备注": f"来源结构：rules.value_constraint.max_length={max_length}；field={fname}",
                    },
                )

            min_v = rule.get("min")
            max_v = rule.get("max")
            integer_only = rule.get("integer_only") is True
            if min_v not in ("", None):
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("边界"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}等于{min_v}时允许保存",
                        "前置条件": f"已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"向`{label}`输入`{min_v}`",
                                "点击保存",
                                "观察保存结果",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`输入`{min_v}`时满足最小边界",
                                "本次提交可继续写入保存请求",
                                f"`{label}`最小值约束保持为`{min_v}`",
                            ]
                        ),
                        "优先级": case_priority("边界"),
                        "标签": case_tags("边界"),
                        "测试类型": "边界",
                        "备注": f"来源结构：rules.value_constraint.min={min_v}；field={fname}",
                    },
                )
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("边界"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}小于{min_v}时保存失败",
                        "前置条件": f"已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"向`{label}`输入小于`{min_v}`的值",
                                "点击保存",
                                "观察校验提示与保存结果",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`输入值小于`{min_v}`时触发下限校验",
                                "本次保存失败",
                                f"页面提示`{label}`不能小于`{min_v}`",
                            ]
                        ),
                        "优先级": case_priority("边界"),
                        "标签": case_tags("边界"),
                        "测试类型": "边界",
                        "备注": f"来源结构：rules.value_constraint.min={min_v}；field={fname}",
                    },
                )

            if max_v not in ("", None):
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("边界"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}等于{max_v}时允许保存",
                        "前置条件": f"已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"向`{label}`输入`{max_v}`",
                                "点击保存",
                                "观察保存结果",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`输入`{max_v}`时满足最大边界",
                                "本次提交可继续写入保存请求",
                                f"`{label}`最大值约束保持为`{max_v}`",
                            ]
                        ),
                        "优先级": case_priority("边界"),
                        "标签": case_tags("边界"),
                        "测试类型": "边界",
                        "备注": f"来源结构：rules.value_constraint.max={max_v}；field={fname}",
                    },
                )
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("边界"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}大于{max_v}时保存失败",
                        "前置条件": f"已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"向`{label}`输入大于`{max_v}`的值",
                                "点击保存",
                                "观察校验提示与保存结果",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`输入值大于`{max_v}`时触发上限校验",
                                "本次保存失败",
                                f"页面提示`{label}`不能大于`{max_v}`",
                            ]
                        ),
                        "优先级": case_priority("边界"),
                        "标签": case_tags("边界"),
                        "测试类型": "边界",
                        "备注": f"来源结构：rules.value_constraint.max={max_v}；field={fname}",
                    },
                )

            if integer_only:
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("边界"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}输入非整数时保存失败",
                        "前置条件": f"已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"向`{label}`输入小数或非整数值",
                                "点击保存",
                                "观察校验提示与保存结果",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`仅接受整数输入",
                                "输入非整数时本次保存失败",
                                f"页面提示`{label}`需满足整数约束",
                            ]
                        ),
                        "优先级": case_priority("边界"),
                        "标签": case_tags("边界"),
                        "测试类型": "边界",
                        "备注": f"来源结构：rules.value_constraint.integer_only=True；field={fname}",
                    },
                )

            max_count = rule.get("max_count")
            if max_count not in ("", None):
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("边界"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}超过{max_count}项时保存失败",
                        "前置条件": f"已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"为`{label}`选择超过`{max_count}`项的数据",
                                "点击保存",
                                "观察校验提示与保存结果",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`选择数量超过`{max_count}`项时触发上限校验",
                                "本次保存失败",
                                f"页面提示`{label}`选择数量不可超过`{max_count}`项",
                            ]
                        ),
                        "优先级": case_priority("边界"),
                        "标签": case_tags("边界"),
                        "测试类型": "边界",
                        "备注": f"来源结构：rules.value_constraint.max_count={max_count}；field={fname}",
                    },
                )
            continue

        if rule_type == "data_source_constraint":
            data_source = condition_text(rule.get("data_source"))
            filters = normalized_list(rule.get("filter"))
            orders = normalized_list(rule.get("order_by"))
            has_filter_or_order = False

            if data_source and not filters and not orders:
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("数据校验"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}候选数据来源于{data_source}",
                        "前置条件": f"系统已准备候选数据，且已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"打开`{label}`候选列表",
                                "核对候选数据来源说明",
                                "抽查候选数据是否来自指定来源",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`候选数据来源于`{data_source}`",
                                "候选数据范围与来源说明一致",
                                f"`{label}`未混入其他来源数据",
                            ]
                        ),
                        "优先级": case_priority("数据校验"),
                        "标签": case_tags("数据校验"),
                        "测试类型": "数据校验",
                        "备注": f"来源结构：rules.data_source_constraint.data_source；field={fname}",
                    },
                )

            for filter_item in filters:
                has_filter_or_order = True
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("数据校验"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}列表仅展示满足{filter_item}的数据",
                        "前置条件": f"系统已准备满足与不满足`{filter_item}`的候选数据，且已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"打开`{label}`候选列表",
                                f"检查列表中每一项是否满足`{filter_item}`",
                                "观察是否存在不符合条件的数据",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`列表只展示满足`{filter_item}`的数据",
                                "不满足该条件的数据不会出现在候选列表中",
                                f"`{label}`过滤结果与规则保持一致",
                            ]
                        ),
                        "优先级": case_priority("数据校验"),
                        "标签": case_tags("数据校验"),
                        "测试类型": "数据校验",
                        "备注": f"来源结构：rules.data_source_constraint.filter={filter_item}；field={fname}",
                    },
                )

            for order_item in orders:
                has_filter_or_order = True
                order_title = order_title_text(order_item)
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("数据校验"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}{order_title}排列",
                        "前置条件": f"系统已准备满足排序比较条件的候选数据，且已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"打开`{label}`候选列表",
                                f"记录候选项的排序顺序",
                                f"校验候选项是否满足`{order_item}`",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`候选项按`{order_item}`排序",
                                "列表顺序与规则要求一致",
                                f"`{label}`排序结果稳定且可复现",
                            ]
                        ),
                        "优先级": case_priority("数据校验"),
                        "标签": case_tags("数据校验"),
                        "测试类型": "数据校验",
                        "备注": f"来源结构：rules.data_source_constraint.order_by={order_item}；field={fname}",
                    },
                )

            if data_source and has_filter_or_order:
                add_case(
                    cases,
                    case_keys,
                    {
                        "__page_name": page_name,
                        "__section_name": section_name,
                        "用例编号": next_id("数据校验"),
                        "所属模块": module_name,
                        "所属功能点": feature_name,
                        "用例标题": f"验证{label}候选数据来源于{data_source}",
                        "前置条件": f"系统已准备候选数据，且已进入{page_name}并打开{section_name}",
                        "测试步骤": html_lines(
                            [
                                f"打开`{label}`候选列表",
                                "核对候选数据来源说明",
                                "抽查候选数据是否来自指定来源范围",
                            ]
                        ),
                        "预期结果": html_lines(
                            [
                                f"`{label}`候选数据来源于`{data_source}`",
                                "候选数据来源与过滤、排序规则一致",
                                f"`{label}`未混入不相关来源数据",
                            ]
                        ),
                        "优先级": case_priority("数据校验"),
                        "标签": case_tags("数据校验"),
                        "测试类型": "数据校验",
                        "备注": f"来源结构：rules.data_source_constraint.data_source；field={fname}",
                    },
                )

    # Legal combination scenario for the feature.
    target_fields = [field for field in feature_fields(feature) if field_name(field) in {"display_day_x", "selected_activity", "link_url"}]
    if target_fields:
        add_case(
            cases,
            case_keys,
            {
                "__page_name": page_name,
                "__section_name": section_name,
                "用例编号": next_id("功能"),
                "所属模块": module_name,
                "所属功能点": feature_name,
                "用例标题": f"验证{feature_name}合法组合场景可提交",
                "前置条件": f"已进入{page_name}并打开{section_name}",
                "测试步骤": html_lines(
                    [
                        "设置展示类型和跳转类型为满足条件的合法组合",
                        "填写所有条件必填字段并选择符合过滤规则的数据",
                        "点击保存并观察结果",
                    ]
                ),
                "预期结果": html_lines(
                    [
                        "条件展示字段按规则出现，可填写字段进入可操作状态",
                        "候选数据来源、过滤和排序符合结构化规则",
                        "点击保存后页面不再提示必填或边界错误，新增记录写入当前输入值",
                    ]
                ),
                "优先级": case_priority("功能"),
                "标签": case_tags("功能"),
                "测试类型": "功能",
                "备注": "来源结构：合法组合场景；不替代原子规则用例",
            },
        )

    return cases


def build_flow_cases(project_code: str, structured_prd: dict[str, Any]) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    seqs: defaultdict[tuple[str, str], int] = defaultdict(int)
    for flow in structured_prd.get("flows", []):
        if not isinstance(flow, dict):
            continue
        flow_id = str(flow.get("flow_id", "")).strip()
        flow_name = str(flow.get("flow_name", "")).strip() or flow_id
        steps = flow.get("steps", [])
        if not steps:
            continue
        first_step = steps[0]
        page_name = "小程序首页改版页"
        module_name = str(first_step.get("module_name", "")).strip() or "流程模块"
        feature_name = flow_name
        seqs[(page_name, module_name)] += 1
        cid = case_id(project_code, page_name, module_name, "流程验证", seqs[(page_name, module_name)])
        step_lines = [str(step.get("action") or step.get("step_name") or "").strip() for step in steps if str(step.get("action") or step.get("step_name") or "").strip()]
        exp_lines = [str(item).strip() for item in flow.get("success_criteria", []) if str(item).strip()]
        if not exp_lines:
            exp_lines = ["主流程关键结果达成"]
        cases.append(
            {
                "__page_name": page_name,
                "__section_name": "跨板块主流程",
                "用例编号": cid,
                "所属模块": module_name,
                "所属功能点": feature_name,
                "用例标题": f"验证{flow_name}主流程打通",
                "前置条件": f"{flow_name}涉及的页面和配置均可访问",
                "测试步骤": html_lines(step_lines[:3] or ["执行主流程关键步骤"]),
                "预期结果": html_lines(exp_lines[:3]),
                "优先级": case_priority("流程验证", is_flow=True),
                "标签": case_tags("流程验证", is_flow=True),
                "测试类型": "流程验证",
                "备注": f"来源 Flow：{flow_id}",
            }
        )
    return cases


def render_markdown(cases: list[dict[str, str]]) -> str:
    grouped: defaultdict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for case in cases:
        grouped[(case["__page_name"], case["__section_name"])].append(case)

    lines: list[str] = []
    for (page_name, section_name), section_cases in grouped.items():
        lines.append(f"# 页面：{page_name}")
        lines.append(f"## 板块：{section_name}")
        lines.append("| " + " | ".join(HEADERS) + " |")
        lines.append("|" + "|".join(["---"] * len(HEADERS)) + "|")
        for case in section_cases:
            lines.append("| " + " | ".join(case.get(header, "") for header in HEADERS) + " |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_bundle(work_item_root: Path, run_manifest: dict) -> dict[str, Any]:
    structured_prd_path = work_item_root / "structured_prd" / "structured_prd.json"
    coverage_matrix_path = work_item_root / "coverage" / "coverage_matrix.json"
    evidence_path = work_item_root / "evidence" / "evidence_inventory.json"
    image_evidence_path = work_item_root / "image_evidence" / "image_evidence_inventory.json"
    traceability_path = work_item_root / "traceability" / "traceability_matrix.json"
    review_path = work_item_root / "reviews" / "review_record.md"
    structured_md_path = work_item_root / "structured_prd" / "structured_prd.md"

    structured_prd = normalize_structured_prd(read_json(structured_prd_path))
    project_code = str(structured_prd.get("project_info", {}).get("project_code", "DEMO")).strip() or "DEMO"

    if coverage_matrix_path.exists():
        coverage_matrix = read_json(coverage_matrix_path)
        testcase_markdown = generate_testcases_markdown(structured_prd, coverage_matrix)
    else:
        cases: list[dict[str, str]] = []
        for module in structured_prd.get("modules", []):
            if not isinstance(module, dict):
                continue
            module_name = str(module.get("module_name", "")).strip()
            for feature in module.get("features", []):
                if not isinstance(feature, dict):
                    continue
                section_name = str(feature.get("section_name", "")).strip()
                if section_name != "添加弹窗":
                    continue
                cases.extend(build_atomic_cases(project_code, module_name, feature))

        cases.extend(build_flow_cases(project_code, structured_prd))
        cases.sort(key=lambda item: (item["__page_name"], item["__section_name"], item["用例编号"]))
        testcase_markdown = render_markdown(cases)

    artifacts: dict[str, str] = {}
    cleanup_targets = run_manifest.get("cleanup_targets", [])
    for relative_path in cleanup_targets:
        target_path = ROOT / relative_path
        if relative_path.endswith("testcases/testcases.md"):
            artifacts[relative_path] = testcase_markdown
            continue
        if target_path.exists():
            artifacts[relative_path] = read_text(target_path)

    # Ensure required artifacts always exist in bundle.
    for path in (
        evidence_path,
        structured_prd_path,
        traceability_path,
        review_path,
        image_evidence_path,
        structured_md_path,
    ):
        rel_path = str(path.relative_to(ROOT))
        if rel_path not in artifacts and path.exists():
            artifacts[rel_path] = read_text(path)

    return {
        "cleanup_targets": cleanup_targets,
        "artifacts": artifacts,
    }


def main() -> int:
    run_manifest_path = os.environ.get("ATP_RUN_MANIFEST")
    output_bundle = os.environ.get("ATP_OUTPUT_BUNDLE")
    work_item_root = os.environ.get("ATP_WORK_ITEM_ROOT")
    if not run_manifest_path or not output_bundle or not work_item_root:
        print("缺少 ATP_RUN_MANIFEST / ATP_OUTPUT_BUNDLE / ATP_WORK_ITEM_ROOT", file=sys.stderr)
        return 1

    run_manifest = read_json(Path(run_manifest_path))
    bundle = build_bundle(Path(work_item_root), run_manifest)
    output_path = Path(output_bundle)
    output_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成规则驱动 testcase bundle: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
