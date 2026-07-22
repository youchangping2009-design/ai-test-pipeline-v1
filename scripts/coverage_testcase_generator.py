#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import hashlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


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
    "页游落地页管理": "LANDING",
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
    "页游落地页列表": "LIST",
    "落地页列表": "LIST",
    "单游戏落地页-主视觉图": "SINGLEHERO",
    "单游戏落地页-登录注册": "SINGLELOGIN",
    "单游戏落地页-底部说明": "SINGLEFOOT",
    "页游多游戏聚合页": "MULTI",
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

API_FIRST_COVERAGE_TYPES = {
    "data_source_filter",
    "data_source_display",
    "data_source_order",
    "data_rule",
}
API_UI_COVERAGE_TYPES = {
    "required",
    "conditional_required",
    "conditional_editability",
    "value_boundary",
    "invalid_input",
    "happy_path_combo",
}
API_CAPABLE_SOURCE_ORIGINS = {
    "general_backend_config_crud_rule",
    "general_backend_config_boundary_rule",
    "general_backend_config_capacity_rule",
    "general_cross_field_constraint_rule",
    "general_data_source_combination_rule",
}
DEV_MUST_SOURCE_ORIGINS = API_CAPABLE_SOURCE_ORIGINS | {
    "general_display_frequency_rule",
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
FIDELITY_LOCATION_RULES = {
    "5s自动轮播": "must_appear_in_title",
    "每tab最多5条": "must_appear_in_expected",
    "每tab最多4条": "must_appear_in_expected",
    "单tab下弹窗不允许超过3条": "must_appear_in_expected",
    "默认关闭": "must_appear_in_expected",
    "顶部tab归属": "must_appear_in_step_or_expected",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_code(text: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]", "", text.upper())
    if normalized:
        return normalized
    raw = str(text).strip()
    if raw:
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:6].upper()
        return f"CN{digest}"
    return "GEN"


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
    text = str(page_name)
    if any(keyword in text for keyword in ["配置页", "管理", "后台", "列表", "落地页管理"]):
        return "ADMIN"
    return "MINI"


def case_tags(
    case_type: str,
    source_origin: str | list[str],
    is_flow: bool = False,
    coverage_type: str = "",
) -> str:
    source_origins = [source_origin] if isinstance(source_origin, str) else list(source_origin)
    coverage_type = str(coverage_type).strip()
    if is_flow:
        base = ["核心链路", "黄金用例", "AI-UI用例", "开发必测", "测试必测"]
    elif case_type == "数据校验":
        base = ["AI-API用例"]
        if coverage_type in API_UI_COVERAGE_TYPES or any(origin in API_CAPABLE_SOURCE_ORIGINS for origin in source_origins):
            base.append("AI-UI用例")
        base.append("开发必测")
    else:
        api_capable = coverage_type in API_FIRST_COVERAGE_TYPES or any(origin in API_CAPABLE_SOURCE_ORIGINS for origin in source_origins)
        ui_needed = coverage_type not in API_FIRST_COVERAGE_TYPES or any(
            origin in {"general_frontend_capacity_rule", "general_display_frequency_rule"} for origin in source_origins
        )
        base = []
        if api_capable:
            base.append("AI-API用例")
        if ui_needed or not base:
            base.append("AI-UI用例")
        if any(origin in DEV_MUST_SOURCE_ORIGINS for origin in source_origins):
            base.append("开发必测")
    if "ai_reasoning" in source_origins and "评审用例" not in base:
        base.append("评审用例")
    return ",".join(dedupe_preserve_order(base))


def case_priority(case_type: str, priority: str, is_flow: bool = False) -> str:
    if is_flow:
        return "P0"
    if priority == "high":
        return "P1"
    if case_type == "异常":
        return "P1"
    return "P1"


def case_id(project_code: str, page_name: str, module_name: str, case_type: str, seq: int) -> str:
    type_code = TYPE_CODE_MAP.get(case_type, "FN")
    return f"{project_code}-{page_code(page_name)}-{module_code(module_name)}-{terminal_code(page_name)}-{type_code}-{seq:03d}"


def html_lines(lines: list[str]) -> str:
    return "<br>".join(f"{idx}. {line}" for idx, line in enumerate(lines, start=1))


def normalize_signature(text: str) -> str:
    collapsed = text.replace("<br>", " ")
    collapsed = re.sub(r"\s+", "", collapsed)
    return collapsed


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def build_remarks(
    coverage_ids: list[str],
    source_origins: list[str],
    reasoning_refs: list[str],
    case_plan_ids: list[str] | None = None,
    flow_ids: list[str] | None = None,
) -> str:
    parts: list[str] = []
    for flow_id in dedupe_preserve_order(flow_ids or []):
        parts.append(f"来源 Flow：{flow_id}")
    for coverage_id in dedupe_preserve_order(coverage_ids):
        parts.append(f"来源coverage：{coverage_id}")
    for source_origin in dedupe_preserve_order(source_origins):
        parts.append(f"source_origin={source_origin}")
    for reasoning_ref in dedupe_preserve_order(reasoning_refs):
        parts.append(f"reasoning_ref={reasoning_ref}")
    for case_plan_id in dedupe_preserve_order(case_plan_ids or []):
        parts.append(f"来源 CasePlan：{case_plan_id}")
    return "；".join(parts)


def compact_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "coverage_id": entry.get("coverage_id", ""),
        "coverage_type": entry.get("coverage_type", ""),
        "coverage_level": entry.get("coverage_level", ""),
        "emit_mode": entry.get("emit_mode", ""),
        "source_origin": entry.get("source_origin", ""),
        "source_type": entry.get("source_type", ""),
        "page_name": entry.get("page_name", ""),
        "section_name": entry.get("section_name", ""),
        "module_name": entry.get("module_name", ""),
        "feature_name": entry.get("feature_name", ""),
        "field_name": entry.get("field_name", ""),
        "title": entry.get("title", ""),
        "priority": entry.get("priority", ""),
        "planned_assertions": list(entry.get("planned_assertions", [])),
        "structured_refs": list(entry.get("structured_refs", [])),
        "reasoning_refs": list(entry.get("reasoning_refs", [])),
    }


def canonical_assertion_signature(entry: dict[str, Any], expected: list[str]) -> str:
    coverage_type = str(entry.get("coverage_type", "")).strip()
    source_text = " ".join(str(item).strip() for item in entry.get("planned_assertions", []))
    expected_text = " ".join(expected)
    corpus = f"{source_text} {expected_text}"

    if coverage_type == "data_source_order":
        if "创建时间倒序" in corpus:
            return "创建时间倒序"
        if "倒序" in corpus:
            return "倒序"
        if "升序" in corpus:
            return "升序"
    return normalize_signature(expected_text)


def infer_rule_variant(entry: dict[str, Any]) -> str:
    coverage_type = str(entry.get("coverage_type", "")).strip()
    if coverage_type != "conditional_editability":
        return coverage_type
    refs = " ".join(str(item) for item in entry.get("structured_refs", []))
    assertions = " ".join(str(item) for item in entry.get("planned_assertions", []))
    if "readonly_when" in refs or "只读" in assertions or "不允许编辑" in assertions:
        return "conditional_editability:readonly_when"
    if "editable_when" in refs or "可编辑" in assertions:
        return "conditional_editability:editable_when"
    return coverage_type


def is_high_priority_fidelity_entry(entry: dict[str, Any]) -> bool:
    source_origin = str(entry.get("source_origin", "")).strip()
    coverage_level = str(entry.get("coverage_level", "")).strip()
    text = " ".join(
        [
            str(entry.get("title", "")).strip(),
            str(entry.get("rationale", "")).strip(),
            " ".join(str(item).strip() for item in entry.get("planned_assertions", [])),
        ]
    )
    return source_origin == "explicit_rule" and coverage_level == "critical" and any(
        keyword in text for keyword in HIGH_PRIORITY_FIDELITY_KEYWORDS
    )


def infer_fidelity_binding(entry: dict[str, Any]) -> dict[str, Any] | None:
    text = " ".join(
        [
            str(entry.get("title", "")).strip(),
            str(entry.get("rationale", "")).strip(),
            str(entry.get("rule_name", "")).strip(),
            " ".join(str(item).strip() for item in entry.get("planned_assertions", [])),
        ]
    )
    feature_name = str(entry.get("feature_name", "")).strip()

    if "5s自动轮播" in text:
        return {
            "category": "5s自动轮播",
            "required_location": FIDELITY_LOCATION_RULES["5s自动轮播"],
            "term": "5s自动轮播",
            "expected_term": "5s自动轮播",
            "title": f"验证{feature_name}支持5s自动轮播" if feature_name else "验证5s自动轮播",
        }
    if "每tab最多5条" in text:
        return {
            "category": "每tab最多5条",
            "required_location": FIDELITY_LOCATION_RULES["每tab最多5条"],
            "term": "每tab最多5条",
            "expected_term": "每tab最多5条",
            "title": f"验证{feature_name}满足每tab最多5条" if feature_name else "验证每tab最多5条",
        }
    if "每tab最多4条" in text:
        return {
            "category": "每tab最多4条",
            "required_location": FIDELITY_LOCATION_RULES["每tab最多4条"],
            "term": "每tab最多4条",
            "expected_term": "每tab最多4条",
            "title": f"验证{feature_name}满足每tab最多4条" if feature_name else "验证每tab最多4条",
        }
    if "单tab下弹窗不允许超过3条" in text or "不允许超过3条" in text:
        return {
            "category": "单tab下弹窗不允许超过3条",
            "required_location": FIDELITY_LOCATION_RULES["单tab下弹窗不允许超过3条"],
            "term": "单tab下弹窗不允许超过3条",
            "expected_term": "单tab下弹窗不允许超过3条",
            "title": "验证单tab下弹窗不允许超过3条",
        }
    if "默认关闭" in text:
        return {
            "category": "默认关闭",
            "required_location": FIDELITY_LOCATION_RULES["默认关闭"],
            "term": "状态默认关闭",
            "expected_term": "状态默认关闭",
            "title": "验证状态默认关闭",
        }
    if "从属于顶部tab" in text or "顶部tab归属" in text:
        expected_term = ""
        for candidate in entry.get("planned_assertions", []):
            candidate_text = str(candidate).strip()
            if "从属于顶部tab" in candidate_text:
                expected_term = candidate_text
                break
        expected_term = expected_term or "顶部tab归属"
        return {
            "category": "顶部tab归属",
            "required_location": FIDELITY_LOCATION_RULES["顶部tab归属"],
            "term": expected_term,
            "expected_term": expected_term,
            "title": "验证顶部tab归属",
        }
    return None


def merge_bucket(case_data: dict[str, Any]) -> str:
    if case_data.get("__high_priority_fidelity"):
        return "explicit_high_priority_fidelity"
    return "normal"


def structured_feature_map(structured_prd: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for module in structured_prd.get("modules", []):
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            feature_name = str(feature.get("feature_name", "")).strip()
            if module_name and feature_name and isinstance(feature, dict):
                result[(module_name, feature_name)] = feature
    return result


def structured_field_map(structured_prd: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for module in structured_prd.get("modules", []):
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            feature_name = str(feature.get("feature_name", "")).strip()
            for field in feature.get("fields", []):
                if isinstance(field, dict):
                    field_name = str(field.get("field_name", "")).strip()
                    if module_name and feature_name and field_name:
                        result[(module_name, feature_name, field_name)] = field
    return result


def field_context_map(structured_prd: dict[str, Any]) -> dict[tuple[str, str], tuple[str, str]]:
    result: dict[tuple[str, str], tuple[str, str]] = {}
    for module in structured_prd.get("modules", []):
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            feature_name = str(feature.get("feature_name", "")).strip()
            page_name = str(feature.get("page_name", "")).strip()
            for field in feature.get("fields", []):
                if isinstance(field, dict):
                    field_name = str(field.get("field_name", "")).strip()
                    if page_name and field_name and module_name and feature_name:
                        result[(page_name, field_name)] = (module_name, feature_name)
    return result


def split_structured_ref(ref: str) -> tuple[str, str, str]:
    parts = str(ref).split(".")
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return "", "", ""


def weak_text(value: str) -> bool:
    normalized = str(value).strip().lower()
    return normalized in {"", "todo", "template", "example", "默认板块", "其他", "未分类", "示例板块"}


def infer_section_name(
    feature_map: dict[tuple[str, str], dict[str, Any]],
    module_name: str,
    feature_name: str,
    entry: dict[str, Any] | None = None,
) -> str:
    if entry:
        entry_section = str(entry.get("section_name", "")).strip()
        if not weak_text(entry_section):
            return entry_section
    feature = feature_map.get((module_name, feature_name), {})
    feature_section = str(feature.get("section_name", "")).strip()
    if not weak_text(feature_section):
        return feature_section
    entry = entry or {}
    coverage_type = str(entry.get("coverage_type", "")).strip()
    title = str(entry.get("title", "")).strip()
    rule_name = str(entry.get("rule_name", "")).strip()
    text = " ".join(
        [
            feature_name,
            title,
            rule_name,
            " ".join(str(item) for item in entry.get("planned_assertions", [])),
        ]
    )
    if "新增" in text or "添加" in text:
        return "添加弹窗"
    if "编辑" in text:
        return "编辑弹窗"
    if "删除" in text:
        return "删除确认弹窗"
    if coverage_type in {"value_boundary", "invalid_input"} or any(token in text for token in ["边界", "非法", "异常", "为空"]):
        return "字段异常与边界"
    if coverage_type in {"data_source_filter", "data_source_display", "data_source_order"}:
        return "数据源组合约束"
    if coverage_type == "happy_path_combo":
        return "跨板块主流程"
    if "列表" in text:
        return "列表区"
    if "筛选" in text:
        return "筛选区"
    return "未识别板块"


MACHINE_IDENTIFIER_PATTERN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
SPECIAL_FIELD_LABELS = {
    "r360_uc_filter_parity": "360实时报表筛选项",
    "r360_custom_columns_reuse": "自定义列",
    "ch_view_landing_page": "查看落地页",
    "ch_view_plan": "查看计划",
    "ch_agg_proration_rule": "聚合落地页版位注册均分规则",
}


def is_machine_identifier(value: str) -> bool:
    return bool(MACHINE_IDENTIFIER_PATTERN.fullmatch(str(value).strip()))


def strip_machine_identifiers(text: str, field_name: str = "") -> str:
    result = str(text or "")
    if field_name:
        result = re.sub(rf"`?{re.escape(field_name)}`?", "", result)
    result = MACHINE_IDENTIFIER_PATTERN.sub("", result)
    result = result.replace("`", "")
    result = re.sub(r"\s+", " ", result).strip(" ：:-，,。")
    return result


def compact_human_text(text: str) -> str:
    result = str(text or "").strip()
    result = result.replace(" ", "")
    result = re.sub(r"\s+", "", result)
    return result.strip("：:-，,。")


def readable_label_from_text(text: str, feature_name: str = "") -> str:
    text = strip_machine_identifiers(text)
    quoted = re.findall(r"[「“\"]([^」”\"]+)[」”\"]", text)
    for item in quoted:
        item = compact_human_text(item)
        if item and not is_machine_identifier(item):
            return item
    candidates = [
        r"新增(.+?)(?:筛选项|筛选|列|按钮)",
        r"自定义列中(.+?)可",
        r"列展示(.+?)(?:：|;|；|$)",
        r"(.+?)(?:筛选项|筛选)",
        r"(.+?)(?:单选|多选|模糊搜索|为空|候选项|默认|枚举)",
    ]
    source = text or feature_name
    for pattern in candidates:
        match = re.search(pattern, source)
        if not match:
            continue
        value = compact_human_text(match.group(1))
        value = re.sub(r"^(新增|验证|为|按|当|数据维度为计划时)", "", value).strip("：:-，,。")
        if value and not is_machine_identifier(value):
            return value
    feature = strip_machine_identifiers(feature_name)
    if "-" in feature:
        feature = feature.split("-", 1)[1]
    feature = re.sub(r"(筛选项|筛选|字段|列|按钮)$", "", compact_human_text(feature))
    if feature and not is_machine_identifier(feature):
        return feature
    return ""


def infer_display_name(field_map: dict[tuple[str, str, str], dict[str, Any]], module_name: str, feature_name: str, field_name: str) -> str:
    if field_name in SPECIAL_FIELD_LABELS:
        return SPECIAL_FIELD_LABELS[field_name]
    field = field_map.get((module_name, feature_name, field_name), {})
    display_name = str(field.get("display_name", "")).strip()
    if display_name and not is_machine_identifier(display_name):
        return display_name
    for source in [
        str(field.get("description", "")).strip(),
        str(field.get("label", "")).strip(),
        str(field.get("title", "")).strip(),
        feature_name,
    ]:
        label = readable_label_from_text(source, feature_name)
        if label:
            return label
    return field_name


def scoped_subject(module_name: str, label: str) -> str:
    module = str(module_name).strip()
    if not module:
        return label
    return f"{module}的{label}"


def stringify_value(value: Any) -> str:
    if isinstance(value, dict):
        return "、".join(f"{key}={val}" for key, val in value.items())
    if isinstance(value, list):
        return "、".join(str(item).strip() for item in value if str(item).strip())
    if value is True:
        return "true"
    if value is False:
        return "false"
    text = str(value).strip()
    value_aliases = {
        "last_7_days": "最近7天",
    }
    return value_aliases.get(text, text)


def has_value(value: Any) -> bool:
    return value is not None and value not in ("", [], {})


def has_explicit_required_signal(entry: dict[str, Any] | None, field: dict[str, Any] | None) -> bool:
    """只有需求文字或原型证据明确必填/必选时，才生成保存拦截类必填断言。"""
    entry = entry or {}
    field = field or {}
    texts = [
        str(entry.get("title", "")).strip(),
        str(entry.get("rationale", "")).strip(),
        " ".join(str(item).strip() for item in entry.get("planned_assertions", []) if str(item).strip()),
        str(field.get("description", "")).strip(),
        str(field.get("required_reason", "")).strip(),
        str(field.get("source_text", "")).strip(),
        str(field.get("raw_text", "")).strip(),
    ]
    for key in ("required_when", "required_source", "prototype_required_marker"):
        value = field.get(key)
        if has_value(value):
            texts.append(stringify_value(value))
    text = " ".join(item for item in texts if item)
    if not text:
        return False
    required_patterns = [
        r"必填",
        r"必选",
        r"不能为空",
        r"不可为空",
        r"必须填写",
        r"必须选择",
        r"必传",
        r"required\\s*[:=]\\s*true",
        r"\\*\\s*(?:必填|必选|字段|项|输入|选择)?",
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in required_patterns)


def field_format_texts(field: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    format_rule = str(field.get("format_rule", "")).strip()
    if format_rule:
        texts.append(format_rule)
    for item in field.get("formats", []) or []:
        item_text = str(item).strip()
        if item_text:
            texts.append(item_text)
    return dedupe_preserve_order(texts)


def field_constraint_fragments(field: dict[str, Any], entry: dict[str, Any] | None = None) -> list[str]:
    fragments: list[str] = []
    if field.get("required") is True and has_explicit_required_signal(entry, field):
        fragments.append("必填")
    if has_value(field.get("default_value")):
        fragments.append(f"默认值={stringify_value(field.get('default_value'))}")
    elif has_value(field.get("default")):
        fragments.append(f"默认值={stringify_value(field.get('default'))}")
    enum_values = [str(item).strip() for item in field.get("enum_values", []) or [] if str(item).strip()]
    if enum_values:
        fragments.append(f"枚举值={'、'.join(enum_values)}")
    if has_value(field.get("max_count")):
        unit = "张" if str(field.get("data_type", "")).strip() == "image" or "upload" in str(field.get("control_type", "")) else "个"
        fragments.append(f"最多{field.get('max_count')}{unit}")
    if has_value(field.get("max_length")):
        fragments.append(f"长度上限{field.get('max_length')}个字符")
    for text in field_format_texts(field):
        fragments.append(text)
    for key, label in [("data_source", "数据源"), ("filter", "过滤规则"), ("display", "展示"), ("description", "说明")]:
        value = str(field.get(key, "")).strip()
        if value:
            fragments.append(f"{label}={value}")
    return dedupe_preserve_order(fragments)


def humanized_entry_detail(entry: dict[str, Any], label: str) -> str:
    title = str(entry.get("title", "")).strip()
    field_name = str(entry.get("field_name", "")).strip()
    title = strip_machine_identifiers(title, field_name)
    title = title.strip("：:- ")
    if not title:
        return label
    if label and title.startswith(label):
        return title
    if label and label in title[: max(len(label) + 4, 8)]:
        return title
    if label.endswith("图") and title.startswith(label[:-1]):
        return label + title[len(label[:-1]) :]
    if label:
        return f"{label}{title}"
    return title


def readable_rule_summary(entry: dict[str, Any], field: dict[str, Any], label: str) -> str:
    texts = [
        str(field.get("description", "")).strip(),
        str(entry.get("title", "")).strip(),
        str(entry.get("rationale", "")).strip(),
        "；".join(str(item).strip() for item in entry.get("planned_assertions", []) if str(item).strip()),
    ]
    text = strip_machine_identifiers("；".join(item for item in texts if item), str(entry.get("field_name", "")).strip())
    text = re.sub(r"按\s+COV-[A-Z0-9-]+\s*验证.*?显式规则。?", "", text)
    text = re.sub(r"与 structured_prd.*$", "", text)
    text = text.strip("；。 ，,")
    if text:
        return text
    return humanized_entry_detail(entry, label)


def field_ref(label: str) -> str:
    return f"“{label}”"


def value_ref(value: Any) -> str:
    return f"{{{stringify_value(value)}}}"


def page_section_ref(page_name: str, section_name: str) -> str:
    page = f"[{page_name}]" if page_name else "目标页面"
    section = f"[{section_name}]板块" if section_name else "目标板块"
    return f"{page}的{section}"


def entry_signal_text(entry: dict[str, Any], field: dict[str, Any]) -> str:
    parts = [
        str(entry.get("title", "")).strip(),
        str(entry.get("rationale", "")).strip(),
        str(field.get("format_rule", "")).strip(),
        str(field.get("data_source", "")).strip(),
        " ".join(str(item).strip() for item in entry.get("planned_assertions", []) if str(item).strip()),
        " ".join(field_format_texts(field)),
    ]
    return " ".join(part for part in parts if part)


def high_signal_expected(label: str, detail: str, field: dict[str, Any], entry: dict[str, Any] | None = None) -> list[str]:
    text = " ".join([detail, " ".join(field_constraint_fragments(field, entry))])
    expected: list[str] = []
    enum_values = [str(item).strip() for item in field.get("enum_values", []) or [] if str(item).strip()]
    formats = field_format_texts(field)
    if "默认" in text and (has_value(field.get("default_value")) or has_value(field.get("default"))):
        default_value = field.get("default_value") if has_value(field.get("default_value")) else field.get("default")
        expected.append(f"{field_ref(label)}默认选中或填入{value_ref(default_value)}")
    elif "默认" in detail:
        expected.append(f"{field_ref(label)}按需求展示：{detail}")
    if enum_values:
        expected.append(f"{field_ref(label)}候选项只包含{'、'.join(value_ref(item) for item in enum_values)}")
    if "多选" in text or str(field.get("control_type", "")).strip() == "select_multi":
        expected.append(f"{field_ref(label)}支持多选，多个候选项可同时作为条件/配置值")
    if "单选" in text or str(field.get("control_type", "")).strip() == "select_single":
        expected.append(f"{field_ref(label)}为单选形态，同一时刻仅保留一个选中值")
    if "模糊" in text:
        expected.append(f"{field_ref(label)}按输入关键字进行模糊匹配，不要求完全等值")
    if field.get("required") is True and has_explicit_required_signal(entry, field):
        expected.append(f"{field_ref(label)}为空时不能提交，或页面明确提示该字段必填")
    elif field.get("required") is False and ("可空" in text or "非必填" in text or "允许为空" in text):
        expected.append(f"{field_ref(label)}留空时仍可保存，不出现强制必填提示")
    if has_value(field.get("max_count")):
        expected.append(f"{field_ref(label)}最多允许{value_ref(field.get('max_count'))}张/项，超过数量后列表或详情中不出现超出的值")
    if has_value(field.get("max_length")):
        expected.append(f"{field_ref(label)}长度超过{value_ref(field.get('max_length'))}个字符时不能保存或被限制输入")
    for format_text in formats:
        expected.append(f"{field_ref(label)}格式限制展示或拦截规则为：{format_text}")
    data_source = str(field.get("data_source", "")).strip()
    if data_source:
        expected.append(f"{field_ref(label)}候选项来自指定数据源：{data_source}")
    if not expected and detail:
        expected.append(f"{field_ref(label)}按需求展示或生效：{detail}")
    return dedupe_preserve_order(expected)


def is_image_field(field: dict[str, Any]) -> bool:
    return str(field.get("data_type", "")).strip() == "image" or "upload" in str(field.get("control_type", ""))


def build_image_constraint_case(label: str, detail: str, field: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    constraints = high_signal_expected(label, detail, field)
    title_bits = [label]
    if has_value(field.get("max_count")):
        title_bits.append(f"仅可上传{field.get('max_count')}张")
    if field_format_texts(field):
        title_bits.append("符合格式与大小约束")
    title = "验证" + "".join(title_bits)
    steps = [
        f"定位{field_ref(label)}上传控件",
        f"尝试上传超过数量、超过大小或不在允许格式内的{field_ref(label)}素材",
        "补充合法素材后观察保存结果",
    ]
    expected = constraints or [f"{field_ref(label)}数量、格式与大小限制均可观测"]
    return title, steps, expected


def data_source_condition_text(entry: dict[str, Any], field: dict[str, Any], label: str) -> str:
    data_source = str(field.get("data_source", "")).strip()
    if data_source:
        return data_source
    detail = humanized_entry_detail(entry, label)
    if "仅" in detail:
        return detail
    assertions = "；".join(str(item).strip() for item in entry.get("planned_assertions", []) if str(item).strip())
    match = re.search(r"满足 `(.+?)`", assertions)
    result = match.group(1) if match else detail
    return strip_machine_identifiers(result, str(entry.get("field_name", "")).strip())


def build_field_property_case_text(entry: dict[str, Any], field: dict[str, Any], label: str) -> tuple[str, list[str], list[str]]:
    detail = humanized_entry_detail(entry, label)
    rule_summary = readable_rule_summary(entry, field, label)
    enum_values = [str(item).strip() for item in field.get("enum_values", []) or [] if str(item).strip()]
    control_type = str(field.get("control_type", "")).strip()
    if enum_values and ("单选" in rule_summary or control_type == "select_single"):
        title = f"验证{label}为单选且候选项为{'、'.join(enum_values)}"
    elif enum_values and ("多选" in rule_summary or control_type == "select_multi"):
        title = f"验证{label}支持多选且候选项为{'、'.join(enum_values)}"
    elif enum_values:
        title = f"验证{label}候选项为{'、'.join(enum_values)}"
    elif "复用" in rule_summary and "UC" in rule_summary:
        title = f"验证{label}复用UC实时报表配置"
    elif "360" in label and "UC" in rule_summary and "筛选" in rule_summary:
        title = "验证360实时报表筛选项与UC实时报表保持一致"
    elif "新开" in rule_summary or "页签" in rule_summary or "新页面" in rule_summary:
        title = f"验证点击{label}后新开页面展示对应维度数据"
    elif "展示" in rule_summary:
        title = f"验证{label}按需求口径展示"
    else:
        title = f"验证{detail}"
    steps = [f"在目标区域查看{field_ref(label)}的展示、控件或入口", "对照需求规则执行对应选择、查看或点击操作"]
    expected = high_signal_expected(label, detail, field, entry)
    if not expected:
        expected = [f"{field_ref(label)}按需求展示或生效：{rule_summary or detail}"]
    return title, steps, expected


def build_conditional_required_case_text(entry: dict[str, Any], field: dict[str, Any], label: str) -> tuple[str, list[str], list[str]]:
    text = readable_rule_summary(entry, field, label)
    if "数据维度为计划" in text or "计划维度" in text:
        return (
            f"验证数据维度为计划时自定义列可勾选{label}",
            ["将数据维度切换为{计划}", "打开自定义列或列设置", f"查找并勾选{field_ref(label)}"],
            [f"自定义列中展示{field_ref(label)}且可勾选", f"勾选后列表展示{field_ref(label)}列"],
        )
    return (
        f"验证{label}在指定条件下必填",
        ["设置页面条件满足该字段的必填规则", f"保持{field_ref(label)}为空并点击保存", "观察校验提示与保存结果"],
        [f"条件满足时{field_ref(label)}按必填处理", f"{field_ref(label)}为空时点击【保存】后不能保存成功"],
    )


def build_data_source_filter_case_text(entry: dict[str, Any], field: dict[str, Any], label: str) -> tuple[str, list[str], list[str]]:
    signal_text = entry_signal_text(entry, field)
    if "模糊" in signal_text:
        return (
            f"验证{label}支持模糊搜索",
            [f"在{field_ref(label)}筛选项输入部分关键字", "点击查询", "观察列表结果集合"],
            [f"结果集合按{field_ref(label)}关键字模糊匹配", "不要求完全等值匹配才返回"],
        )
    if "默认全部" in signal_text or "默认不选" in signal_text:
        return (
            f"验证{label}默认不选时展示全部",
            [f"保持{field_ref(label)}筛选项不选择任何值", "点击查询或刷新列表", "观察列表结果集合"],
            [f"{field_ref(label)}未选择时不按计划类型收窄结果", "列表展示全部计划类型的数据"],
        )
    if "多选" in signal_text:
        return (
            f"验证{label}筛选项支持多选",
            [f"在{field_ref(label)}筛选项同时选择两个及以上值", "点击查询", "观察列表结果集合"],
            [f"{field_ref(label)}支持同时选择多个值", "查询结果按所选计划类型并集过滤"],
        )
    condition_text = data_source_condition_text(entry, field, label).strip().rstrip("。.")
    return (
        f"验证{label}候选项符合数据源过滤规则",
        [f"打开{field_ref(label)}候选列表", f"检查每一项是否满足{condition_text}", "观察是否存在不符合条件的数据"],
        [f"{field_ref(label)}候选项只保留满足{condition_text}的数据", "不符合条件的数据不会出现在候选列表中"],
    )


def feature_fields(feature: dict[str, Any]) -> list[dict[str, Any]]:
    return [field for field in feature.get("fields", []) if isinstance(field, dict)]


def field_display_name(field: dict[str, Any]) -> str:
    return str(field.get("display_name") or field.get("field_name") or "").strip()


def field_machine_name(field: dict[str, Any]) -> str:
    return str(field.get("field_name") or field.get("name") or "").strip()


def is_backend_config_page(page_name: str) -> bool:
    return "配置页" in str(page_name)


def is_managed_backend_config_feature(module_name: str, feature: dict[str, Any]) -> bool:
    """识别有列表管理语义的后台配置实体，而不是只匹配某个需求名称。"""
    page_name = str(feature.get("page_name", "")).strip()
    section_name = str(feature.get("section_name", "")).strip()
    fields = feature_fields(feature)
    field_names = {field_machine_name(field) for field in fields}
    display_names = {field_display_name(field) for field in fields}
    has_identity = any(
        field_machine_name(field).endswith("_name") or field_display_name(field).endswith("名称")
        for field in fields
    )
    has_status = "status" in field_names or "状态" in display_names
    has_distribution_controls = bool(
        field_names
        & {
            "show_tab",
            "jump_type",
            "display_type",
            "selected_activity",
            "link_url",
            "touch_user_type",
            "display_rule",
        }
    )
    return (
        is_backend_config_page(page_name)
        and section_name == "添加弹窗"
        and "配置" in module_name
        and bool(fields)
        and has_identity
        and has_status
        and has_distribution_controls
    )


def object_label_from_module(module_name: str, feature: dict[str, Any]) -> str:
    for field in feature_fields(feature):
        display = field_display_name(field)
        if display.endswith("名称"):
            return display.removesuffix("名称") or display
    label = module_name
    for token in ("小程序", "后台", "配置", "管理"):
        label = label.replace(token, "")
    return label.strip() or module_name


def primary_name_field(feature: dict[str, Any]) -> dict[str, Any] | None:
    for field in feature_fields(feature):
        display = field_display_name(field)
        name = field_machine_name(field)
        if display.endswith("名称") or name.endswith("_name"):
            return field
    return None


def important_field_labels(feature: dict[str, Any]) -> list[str]:
    preferred_names = {
        "show_tab",
        "jump_type",
        "display_type",
        "touch_user_type",
        "display_rule",
        "status",
    }
    labels: list[str] = []
    for field in feature_fields(feature):
        name = field_machine_name(field)
        display = field_display_name(field)
        if field.get("required") is True or name in preferred_names:
            labels.append(display or name)
    return dedupe_preserve_order(labels)


def find_consumer_feature(structured_prd: dict[str, Any], object_label: str) -> tuple[str, str, str] | None:
    for module in structured_prd.get("modules", []):
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            page_name = str(feature.get("page_name", "")).strip()
            feature_name = str(feature.get("feature_name", "")).strip()
            section_name = str(feature.get("section_name", "")).strip() or feature_name
            if is_backend_config_page(page_name):
                continue
            corpus = f"{module_name} {feature_name} {section_name}"
            if object_label and object_label in corpus:
                return page_name or "前台展示页", module_name or "前台展示", feature_name or section_name
    return None


def supplemental_case(
    page_name: str,
    section_name: str,
    module_name: str,
    feature_name: str,
    case_type: str,
    title: str,
    precondition: str,
    steps: list[str],
    expected: list[str],
    source_origin: str,
    priority: str = "P1",
    tags: str | None = None,
) -> dict[str, Any]:
    return {
        "__page_name": page_name,
        "__section_name": section_name,
        "__case_type": case_type,
        "__emit_mode": "main_testcase",
        "__coverage_level": "supplemental",
        "__coverage_type": "general_generation_rule",
        "__merge_rule_type": "general_generation_rule",
        "__target_field": title,
        "__title_signature": normalize_signature(title),
        "__expected_signature": normalize_signature(" ".join(expected)),
        "__step_signature": normalize_signature(" ".join(steps)),
        "__coverage_ids": [],
        "__source_origins": [source_origin],
        "__reasoning_refs": [],
        "__case_plan_ids": [],
        "__flow_ids": [],
        "__priority_candidates": ["high" if priority == "P1" else "medium"],
        "__high_priority_fidelity": False,
        "__fidelity_binding": None,
        "__merge_bucket": "supplemental",
        "用例编号": "",
        "所属模块": module_name,
        "所属功能点": feature_name,
        "用例标题": title,
        "前置条件": precondition,
        "测试步骤": html_lines(steps),
        "预期结果": html_lines(expected),
        "优先级": priority,
        "标签": tags or case_tags(case_type, source_origin, False, "general_generation_rule"),
        "测试类型": case_type,
        "备注": f"source_origin={source_origin}",
    }


def parse_capacity_rule(rule_text: str) -> tuple[str, int] | None:
    text = str(rule_text).strip()
    patterns = [
        r"单(?:个)?tab下(.+?)不允许超过(\d+)条",
        r"每tab最多(\d+)条(.+)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        if pattern.startswith("单"):
            return match.group(1).strip(), int(match.group(2))
        return (match.group(2) or "").strip(), int(match.group(1))
    return None


def build_structured_rule_supplements(structured_prd: dict[str, Any]) -> list[dict[str, Any]]:
    """从结构化 PRD 中抽象补齐后台配置页高信号业务用例。"""
    cases: list[dict[str, Any]] = []
    existing_titles: set[tuple[str, str, str]] = set()

    def append(case: dict[str, Any]) -> None:
        key = (case["所属模块"], case["所属功能点"], case["用例标题"])
        if key in existing_titles:
            return
        existing_titles.add(key)
        cases.append(case)

    for module in structured_prd.get("modules", []):
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            page_name = str(feature.get("page_name", "")).strip() or f"{module_name}页"
            feature_name = str(feature.get("feature_name", "")).strip() or "配置录入"
            rules_text = "；".join(str(rule) for rule in feature.get("rules", []) if str(rule).strip())
            if "前值" in rules_text and "后值" in rules_text and ("<=" in rules_text or "不允许大于" in rules_text):
                message_match = re.search(r"提示[“\"](.+?)[”\"]", rules_text)
                message = message_match.group(1) if message_match else "前值不允许大于后值"
                append(
                    supplemental_case(
                        page_name,
                        "字段异常与边界",
                        module_name,
                        feature_name,
                        "功能",
                        "验证充值金额前值大于后值时保存失败",
                        f"已进入{page_name}并打开添加弹窗或编辑弹窗，触达用户类型已选择需填写金额区间的选项",
                        [
                            "填写`充值金额前值`大于`充值金额后值`的金额区间",
                            "点击保存",
                            "观察校验提示与保存结果",
                        ],
                        [
                            "`充值金额前值`大于`充值金额后值`时本次保存失败",
                            f"页面提示`{message}`或等价金额区间错误信息",
                        ],
                        "general_cross_field_constraint_rule",
                    )
                )

            if not is_managed_backend_config_feature(module_name, feature):
                continue

            object_label = object_label_from_module(module_name, feature)
            name_field = primary_name_field(feature)
            name_label = field_display_name(name_field) if name_field else f"{object_label}名称"
            fill_labels = important_field_labels(feature)
            fill_text = "、".join(fill_labels[:8]) or "必填字段"
            precondition = f"已进入{page_name}，列表页和添加/编辑弹窗均可访问"

            append(
                supplemental_case(
                    page_name,
                    "真实CRUD链路",
                    module_name,
                    feature_name,
                    "功能",
                    f"验证{module_name}真实新增成功并回显到列表",
                    precondition,
                    [
                        "点击`添加`打开添加弹窗",
                        f"填写{fill_text}",
                        "点击保存并返回列表查询新增记录",
                    ],
                    [
                        "提交后添加弹窗关闭且列表记录数增加1条",
                        f"新增行的{name_label}、展示tab、跳转类型、状态与提交值逐项一致",
                        "新增行展示`编辑`和`删除`操作入口",
                    ],
                    "general_backend_config_crud_rule",
                )
            )
            append(
                supplemental_case(
                    page_name,
                    "真实CRUD链路",
                    module_name,
                    feature_name,
                    "功能",
                    (
                        f"验证{module_name}真实编辑成功并保留展示规则"
                        if any(field_machine_name(field) == "display_rule" for field in feature_fields(feature))
                        else f"验证{module_name}真实编辑成功并保留关联关系"
                    ),
                    f"列表中已存在一条{module_name}记录",
                    [
                        "点击目标记录`编辑`打开编辑弹窗",
                        f"修改{name_label}、展示tab、跳转类型或状态中的至少一项",
                        "点击保存并返回列表查询该记录",
                    ],
                    [
                        "原记录被更新且列表记录数不增加",
                        f"更新后的{name_label}、展示tab、跳转类型、状态与编辑提交值一致",
                        "未生成重复配置记录，原关联关系按编辑结果保留或更新",
                    ],
                    "general_backend_config_crud_rule",
                )
            )
            append(
                supplemental_case(
                    page_name,
                    "真实CRUD链路",
                    module_name,
                    feature_name,
                    "功能",
                    f"验证{module_name}真实删除成功并从列表移除",
                    f"列表中已存在一条可删除的{module_name}记录",
                    [
                        "点击目标记录`删除`",
                        "在确认弹窗中确认删除",
                        "返回列表查询该记录",
                    ],
                    [
                        "目标记录从列表中移除且列表记录数减少1条",
                        "再次查询不会展示已删除记录",
                        "删除后该记录不再作为前台展示或排序配置的有效数据",
                    ],
                    "general_backend_config_crud_rule",
                )
            )

            if name_field and name_field.get("max_length"):
                max_length = int(name_field["max_length"])
                append(
                    supplemental_case(
                        page_name,
                        "字段异常与边界",
                        module_name,
                        feature_name,
                        "边界",
                        f"验证{name_label}长度超过{max_length}时保存失败",
                        f"已进入{page_name}并打开添加弹窗或编辑弹窗",
                        [
                            f"向`{name_label}`输入长度为`{max_length + 1}`的内容",
                            "点击保存",
                            "观察校验提示与保存结果",
                        ],
                        [
                            f"`{name_label}`长度超过{max_length}时本次保存失败",
                            f"页面提示长度不符合`varchar({max_length})`限制或禁止继续输入超长内容",
                        ],
                        "general_backend_config_boundary_rule",
                    )
                )

            display_day_field = next((field for field in feature_fields(feature) if field_machine_name(field) == "display_day_x"), None)
            if display_day_field:
                condition = "展示类型已选择`用户满足触达用户类型后X天（自然日）内展示`"
                for title, value, expected in [
                    ("验证X小于1时保存失败", "0", "`X`小于1时本次保存失败"),
                    ("验证X大于99时保存失败", "100", "`X`大于99时本次保存失败"),
                ]:
                    append(
                        supplemental_case(
                            page_name,
                            "字段异常与边界",
                            module_name,
                            feature_name,
                            "边界",
                            title,
                            f"已进入{page_name}并打开添加弹窗或编辑弹窗，{condition}",
                            [f"向`X`输入`{value}`", "点击保存", "观察校验提示与保存结果"],
                            [expected, "页面提示`X`必须为`[1,99]`正整数"],
                            "general_backend_config_boundary_rule",
                        )
                    )

            display_rule_field = next((field for field in feature_fields(feature) if field_machine_name(field) == "display_rule" or field_display_name(field) == "展示规则"), None)
            if display_rule_field:
                enum_values = [str(item).strip() for item in display_rule_field.get("enum_values", []) if str(item).strip()]
                for value in enum_values[1:]:
                    append(
                        supplemental_case(
                            page_name,
                            "展示规则配置",
                            module_name,
                            feature_name,
                            "功能",
                            f"验证展示规则可配置为{value}",
                            f"已进入{page_name}并打开添加弹窗或编辑弹窗",
                            [
                                f"将`展示规则`选择为`{value}`",
                                "补齐其他必填字段后点击保存",
                                "重新打开该配置查看展示规则",
                            ],
                            [
                                f"保存后重新打开配置，`展示规则`保持为`{value}`",
                                "该展示规则参与前台弹窗展示频次判断",
                            ],
                            "general_display_frequency_rule",
                        )
                    )

                consumer = find_consumer_feature(structured_prd, "弹窗")
                if consumer:
                    consumer_page, consumer_module, consumer_feature = consumer
                    frequency_cases = {
                        "每日首次进入小程序": (
                            "验证每日首次进入小程序弹窗单日只展示一次",
                            [
                                "用户首次进入对应顶部tab",
                                "关闭弹窗后退出并再次进入小程序同一顶部tab",
                                "观察同一自然日内弹窗展示次数",
                            ],
                            [
                                "首次进入时展示该营销弹窗",
                                "同一自然日再次进入时不重复展示该弹窗",
                            ],
                        ),
                        "每次进入小程序": (
                            "验证每次进入小程序弹窗每次进入均可展示",
                            [
                                "用户进入对应顶部tab并关闭弹窗",
                                "退出后再次进入小程序同一顶部tab",
                                "观察弹窗展示次数",
                            ],
                            [
                                "每次进入小程序且满足触达条件时均可展示该弹窗",
                                "关闭弹窗不会导致后续进入永久不展示",
                            ],
                        ),
                        "仅一次": (
                            "验证仅一次弹窗展示后不再重复展示",
                            [
                                "用户首次进入对应顶部tab并触发展示弹窗",
                                "关闭弹窗后再次进入同一顶部tab",
                                "观察该弹窗是否重复展示",
                            ],
                            [
                                "首次命中条件时展示该弹窗",
                                "展示一次后再次进入不再重复展示该弹窗",
                            ],
                        ),
                    }
                    for value in enum_values:
                        if value not in frequency_cases:
                            continue
                        title, steps, expected = frequency_cases[value]
                        append(
                            supplemental_case(
                                consumer_page,
                                "展示频次",
                                consumer_module,
                                consumer_feature,
                                "功能",
                                title,
                                f"后台已配置展示规则为`{value}`且状态开启的弹窗，用户满足触达条件",
                                steps,
                                expected,
                                "general_display_frequency_rule",
                            )
                        )

            for rule in feature.get("rules", []):
                capacity = parse_capacity_rule(str(rule))
                if not capacity:
                    continue
                raw_label, limit = capacity
                capacity_label = raw_label or object_label
                append(
                    supplemental_case(
                        page_name,
                        "容量限制",
                        module_name,
                        feature_name,
                        "功能",
                        f"验证单tab下{capacity_label}超过{limit}条时B端保存拦截",
                        f"同一展示tab下已存在{limit}条开启状态的{capacity_label}配置",
                        [
                            f"继续新增第{limit + 1}条同tab {capacity_label}配置",
                            "补齐必填字段并点击保存",
                            "观察保存结果和列表数据",
                        ],
                        [
                            f"系统保持`单tab下{capacity_label}不允许超过{limit}条`",
                            "第{limit_plus_one}条配置不会写入列表".format(limit_plus_one=limit + 1),
                            "管理员可通过关闭旧配置或调整展示tab后重新保存",
                        ],
                        "general_backend_config_capacity_rule",
                    )
                )
                consumer = find_consumer_feature(structured_prd, capacity_label or object_label)
                if consumer:
                    consumer_page, consumer_module, consumer_feature = consumer
                    append(
                        supplemental_case(
                            consumer_page,
                            "容量展示",
                            consumer_module,
                            consumer_feature,
                            "功能",
                            f"验证首页{capacity_label}展示规则满足每tab最多{limit}条",
                            f"后台同一顶部tab下已配置超过或等于{limit}条候选{capacity_label}数据",
                            [
                                "进入小程序首页并切换到对应顶部tab",
                                f"统计当前tab下{capacity_label}展示数量",
                                "观察是否出现超过上限的数据项",
                            ],
                            [
                                f"当前tab展示结果满足`每tab最多{limit}条`",
                                "不会展示超过上限的数据项",
                            ],
                            "general_frontend_capacity_rule",
                        )
                    )

    return cases


def build_coverage_combination_supplements(coverage_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    grouped: defaultdict[tuple[str, str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for entry in coverage_matrix.get("entries", []):
        coverage_type = str(entry.get("coverage_type", "")).strip()
        if coverage_type not in {"data_source_filter", "data_source_order"}:
            continue
        key = (
            str(entry.get("page_name", "")).strip(),
            str(entry.get("module_name", "")).strip(),
            str(entry.get("feature_name", "")).strip(),
            str(entry.get("field_name", "")).strip(),
        )
        grouped[key][coverage_type] = entry

    for (page_name, module_name, feature_name, field_name), items in grouped.items():
        if "data_source_filter" not in items or "data_source_order" not in items:
            continue
        label = str(items["data_source_filter"].get("title", "")).split(" ")[0] or field_name or "候选项"
        filter_text = "；".join(str(item) for item in items["data_source_filter"].get("planned_assertions", []))
        order_text = "；".join(str(item) for item in items["data_source_order"].get("planned_assertions", []))
        case = supplemental_case(
            page_name or "后台配置页",
            "数据源组合约束",
            module_name or "后台配置",
            feature_name or "数据源约束",
            "数据校验",
            f"验证{label}候选项同时满足过滤与排序",
            f"已进入{page_name}并打开包含{field_ref(label)}的添加弹窗或编辑弹窗",
            [
                f"打开{field_ref(label)}候选列表",
                "核对候选项是否先过滤无效数据",
                "核对过滤后的候选项排序",
            ],
            [
                f"{field_ref(label)}候选项符合过滤规则：{filter_text}",
                f"{field_ref(label)}候选项符合排序规则：{order_text}",
                "过滤与排序同时生效，不因排序展示出不符合过滤条件的数据",
            ],
            "general_data_source_combination_rule",
            tags="AI-API用例,开发必测",
        )
        case["__coverage_ids"] = [
            str(items["data_source_filter"].get("coverage_id", "")).strip(),
            str(items["data_source_order"].get("coverage_id", "")).strip(),
        ]
        case["备注"] = build_remarks(case["__coverage_ids"], case["__source_origins"], [])
        cases.append(case)
    return cases


def add_case(cases: list[dict[str, Any]], seen: set[tuple[str, str]], case_data: dict[str, Any]) -> None:
    key = (case_data["用例标题"], case_data.get("备注", ""))
    if key in seen:
        return
    seen.add(key)
    cases.append(case_data)


def build_case_rows(entry: dict[str, Any], project_code: str, seqs: defaultdict[tuple[str, str, str], int], feature_map: dict[tuple[str, str], dict[str, Any]], field_map: dict[tuple[str, str, str], dict[str, Any]], field_context: dict[tuple[str, str], tuple[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    coverage_type = str(entry.get("coverage_type", "")).strip()
    source_origin = str(entry.get("source_origin", "")).strip()
    page_name = str(entry.get("page_name", "")).strip() or "待补充页面"
    field_name = str(entry.get("field_name", "")).strip()
    inferred_module, inferred_feature = field_context.get((page_name, field_name), ("", ""))
    module_name = str(entry.get("module_name", "")).strip() or inferred_module or "待补充模块"
    feature_name = str(entry.get("feature_name", "")).strip() or inferred_feature or "待补充功能点"
    label = infer_display_name(field_map, module_name, feature_name, field_name) if field_name else str(entry.get("title", "")).strip()
    section_name = infer_section_name(feature_map, module_name, feature_name, entry)
    priority = str(entry.get("priority", "medium")).strip()
    merge_rule_type = infer_rule_variant(entry)
    high_priority_fidelity = is_high_priority_fidelity_entry(entry)
    fidelity_binding = infer_fidelity_binding(entry) if high_priority_fidelity else None
    field_definition = field_map.get((module_name, feature_name, field_name), {}) if field_name else {}

    def next_id(case_type: str) -> str:
        seqs[(page_name, module_name, case_type)] += 1
        return case_id(project_code, page_name, module_name, case_type, seqs[(page_name, module_name, case_type)])

    def base_row(case_type: str, title: str, steps: list[str], expected: list[str], test_type: str | None = None) -> dict[str, Any]:
        location = page_section_ref(page_name, section_name)
        return {
            "__page_name": page_name,
            "__section_name": section_name,
            "__case_type": case_type,
            "__emit_mode": str(entry.get("emit_mode", "")).strip(),
            "__coverage_level": str(entry.get("coverage_level", "")).strip(),
            "__coverage_type": coverage_type,
            "__merge_rule_type": merge_rule_type,
            "__target_field": field_name or (fidelity_binding["category"] if fidelity_binding else "") or label or title,
            "__title_signature": normalize_signature(title),
            "__expected_signature": canonical_assertion_signature(entry, expected),
            "__step_signature": normalize_signature(" ".join(steps)),
            "__coverage_ids": [str(entry.get("coverage_id", "")).strip()],
            "__source_origins": [source_origin] if source_origin else [],
            "__reasoning_refs": [str(ref).strip() for ref in entry.get("reasoning_refs", []) if str(ref).strip()],
            "__case_plan_ids": [],
            "__flow_ids": [],
            "__priority_candidates": [priority],
            "__high_priority_fidelity": high_priority_fidelity,
            "__fidelity_binding": fidelity_binding,
            "__merge_bucket": "",
            "用例编号": "",
            "所属模块": module_name,
            "所属功能点": feature_name,
            "用例标题": title,
            "前置条件": (
                f"已进入{location}并打开添加弹窗或编辑弹窗"
                if section_name == "添加弹窗"
                else f"已进入{location}"
            ),
            "测试步骤": html_lines(steps),
            "预期结果": html_lines(expected),
            "优先级": "",
            "标签": "",
            "测试类型": test_type or case_type,
            "备注": "",
        }

    if fidelity_binding:
        category = fidelity_binding["category"]
        term = fidelity_binding["term"]
        expected_term = fidelity_binding["expected_term"]
        if category == "5s自动轮播":
            rows.append(
                base_row(
                    "功能",
                    fidelity_binding["title"],
                    [
                        "进入对应展示区域并保持当前tab停留",
                        "连续观察展示内容至少一个轮播周期",
                        "尝试手动切换当前展示内容",
                    ],
                    [
                        f"展示内容按`{expected_term}`节奏自动切换",
                        "用户仍可手动切换当前展示内容",
                    ],
                )
            )
            return rows
        if category in {"每tab最多5条", "每tab最多4条"}:
            rows.append(
                base_row(
                    "功能",
                    fidelity_binding["title"],
                    [
                        "切换到同一顶部tab并统计当前展示数量",
                        "检查当前tab内是否出现超过上限的展示数据",
                    ],
                    [
                        f"当前tab展示结果满足`{expected_term}`",
                        "不会展示超过上限的数据项",
                    ],
                )
            )
            return rows
        if category == "单tab下弹窗不允许超过3条":
            rows.append(
                base_row(
                    "功能",
                    fidelity_binding["title"],
                    [
                        "在同一tab下持续新增或调整开启状态的弹窗配置",
                        "尝试使当前tab弹窗数量超过上限后保存",
                    ],
                    [
                        f"系统保持`{expected_term}`",
                        "超过上限时不允许继续保存当前配置",
                    ],
                )
            )
            return rows
        if category == "默认关闭":
            rows.append(
                base_row(
                    "功能",
                    fidelity_binding["title"],
                    [
                        "打开添加弹窗并定位状态字段",
                        "观察状态字段初始值与默认选项",
                    ],
                    [
                        expected_term,
                        "状态字段初始值与规则定义一致",
                    ],
                )
            )
            return rows
        if category == "顶部tab归属":
            rows.append(
                base_row(
                    "功能",
                    fidelity_binding["title"],
                    [
                        "切换顶部tab并观察当前tab对应内容区域",
                        f"核对`{term}`是否成立",
                    ],
                    [
                        expected_term,
                        "切换顶部tab后仅展示对应归属内容",
                    ],
                )
            )
            return rows

    if coverage_type == "happy_path_combo" and any(str(ref).strip().startswith("flows.") for ref in entry.get("structured_refs", [])):
        return rows

    if coverage_type == "field_property":
        detail = humanized_entry_detail(entry, label)
        signal_text = entry_signal_text(entry, field_definition)
        if field_name == "row_edit" or "编辑弹窗带出" in signal_text or "带出原信息" in signal_text:
            rows.append(
                base_row(
                    "功能",
                    f"验证{label}打开弹窗时带出原落地页信息",
                    [f"点击行内{field_ref(label)}入口", "观察弹窗内落地页名称、游戏、落地页地址等字段"],
                    ["弹窗中关键字段从来源行回显", "可编辑/只读状态与产品定义一致"],
                )
            )
        elif "链接可配" in signal_text or "可配" in detail and "链接" in label:
            rows.append(
                base_row(
                    "功能",
                    f"验证{label}可配置且保存后可访问",
                    [f"在{field_ref(label)}输入可访问测试URL", "保存配置并进入预览或详情", f"点击{field_ref(label)}对应入口"],
                    [f"{field_ref(label)}按输入地址保存", "预览/详情中可打开到配置地址"],
                )
            )
        else:
            title, steps, expected = build_field_property_case_text(entry, field_definition, label)
            rows.append(
                base_row(
                    "功能",
                    title,
                    steps,
                    expected,
                )
            )
    elif coverage_type == "state_constraint":
        detail = humanized_entry_detail(entry, label)
        signal_text = entry_signal_text(entry, field_definition)
        if "删除" in signal_text and "二次确认" in signal_text:
            rows.append(
                base_row(
                    "功能",
                    "验证点击删除时先出二次确认且确认后记录消失",
                    [f"点击行内{field_ref(label)}入口", "在二次确认弹窗中确认", "回到列表观察目标行"],
                    ["首次点击不直接删除目标行", "确认后目标行从列表中移除或状态与产品规则一致"],
                )
            )
        elif "查看" in signal_text and ("新页" in signal_text or "新窗口" in signal_text or "页签" in signal_text):
            rows.append(
                base_row(
                    "功能",
                    "验证点击行内查看在新页签/新窗口打开展示落地页",
                    [f"点击行内{field_ref(label)}入口", "观察浏览器页签/窗口变化", "核对打开地址与当前行落地页的关系"],
                    ["新页签或新窗口展示该行落地页详情", "展示地址来自当前行预置落地页地址"],
                )
            )
        elif "复制" in signal_text and "新增" in signal_text:
            rows.append(
                base_row(
                    "功能",
                    "验证点击复制确认后在列表中新增一条落地页数据",
                    [f"点击行内{field_ref(label)}入口", "在复制弹窗中确认名称与游戏", "返回列表定位新行"],
                    ["列表新增一条落地页记录", "新行名称/游戏与弹窗确认值一致或符合产品合并规则"],
                )
            )
        else:
            rows.append(
                base_row(
                    "功能",
                    f"验证{detail}",
                    [f"触发{field_ref(label)}对应操作", "观察页面状态变化和最终结果"],
                    high_signal_expected(label, detail, field_definition, entry),
                )
            )
    elif coverage_type == "required":
        if not has_explicit_required_signal(entry, field_definition):
            title, steps, expected = build_field_property_case_text(entry, field_definition, label)
            rows.append(base_row("功能", title, steps, expected))
            return rows
        steps = [f"保持{field_ref(label)}为空", "点击保存", "观察校验提示与保存结果"]
        expected = [f"{field_ref(label)}为空时点击【保存】后不能保存成功", f"页面提示需要补充{field_ref(label)}"]
        title = f"验证{label}为空时保存失败"
        enum_values = [str(item).strip() for item in field_definition.get("enum_values", []) if str(item).strip()]
        default_value = str(field_definition.get("default_value", "") or field_definition.get("default", "")).strip()
        if field_name == "display_rule" and default_value:
            title = f"验证{label}默认为{default_value}且为空时保存失败"
            steps = [f"打开{field_ref(label)}并确认默认值为{value_ref(default_value)}", f"清空{field_ref(label)}后点击【保存】", "观察校验提示与保存结果"]
            expected = [f"{field_ref(label)}默认值为{value_ref(default_value)}", f"{field_ref(label)}为空时点击【保存】后不能保存成功"]
        elif field_name == "jump_type" and "展示企微单人单码" in enum_values:
            title = f"验证{scoped_subject(module_name, label)}为空时保存失败"
            expected = [f"{field_ref(label)}候选项包含{value_ref('展示企微单人单码')}", f"{field_ref(label)}为空时点击【保存】后不能保存成功"]
        elif field_name == "touch_user_type" and "付费未添加企微用户" in enum_values:
            title = f"验证{scoped_subject(module_name, label)}为空时保存失败"
            expected = [f"{field_ref(label)}候选项包含{value_ref('付费未添加企微用户')}", f"{field_ref(label)}为空时点击【保存】后不能保存成功"]
        elif enum_values:
            title = f"验证{label}未选择时无法保存并仅出现指定枚举"
            expected = [f"{field_ref(label)}为空时点击【保存】后不能保存成功", f"{field_ref(label)}候选项只包含{'、'.join(value_ref(item) for item in enum_values)}"]
        rows.append(base_row("功能", title, steps, expected))
    elif coverage_type == "conditional_required":
        signal_text = entry_signal_text(entry, field_definition)
        if has_explicit_required_signal(entry, field_definition) or ("自定义列" in signal_text and "计划" in signal_text):
            title, steps, expected = build_conditional_required_case_text(entry, field_definition, label)
        else:
            title, steps, expected = build_field_property_case_text(entry, field_definition, label)
        rows.append(
            base_row(
                "功能",
                title,
                steps,
                expected,
            )
        )
    elif coverage_type == "conditional_visibility":
        condition = str(entry.get("planned_assertions", [""])[0]).replace("仅当 `", "").split("`", 1)[0] or "条件满足"
        title = f"验证{label}在指定条件下展示"
        steps = [f"先设置页面条件不满足{value_ref(condition)}", f"再切换到满足{value_ref(condition)}", f"观察{field_ref(label)}字段显隐变化"]
        expected = [f"条件不满足{value_ref(condition)}时不展示{field_ref(label)}", f"条件满足{value_ref(condition)}时展示{field_ref(label)}"]
        if field_name == "display_day_x" and "用户满足触达用户类型后X天" in condition:
            title = "验证X在非后X天展示类型下不展示"
            steps = [
                "将`展示类型`切换为`用户满足符合触达用户类型时展示`",
                "观察`X`字段是否展示",
                "再切换为`用户满足触达用户类型后X天（自然日）内展示`",
            ]
            expected = [
                "非后X天展示类型下不展示`X`",
                "切换为后X天展示类型后才展示`X`并允许按`[1,99]`填写",
            ]
        rows.append(
            base_row(
                "功能",
                title,
                steps,
                expected,
            )
        )
    elif coverage_type == "conditional_editability":
        refs_text = " ".join(str(item).strip() for item in entry.get("structured_refs", []))
        assertion_text = " ".join(str(item).strip() for item in entry.get("planned_assertions", []))
        if "readonly_when" in refs_text or "只读" in assertion_text or "不允许编辑" in assertion_text:
            title = f"验证{scoped_subject(module_name, label)}在活动中心场景下保持只读"
            steps = [f"将“跳转类型”切换为{value_ref('活动中心')}", f"尝试编辑{field_ref(label)}字段", "观察字段编辑态和保存结果"]
            expected = [f"{field_ref(label)}在活动中心场景下只读，不能修改", "用户不可绕过只读约束修改字段"]
        else:
            title = f"验证{scoped_subject(module_name, label)}在指定条件下可编辑"
            steps = [f"设置页面条件满足{field_ref(label)}可编辑规则", f"尝试修改{field_ref(label)}的值", "观察字段是否允许编辑"]
            expected = [f"{field_ref(label)}在指定条件下允许编辑", "字段编辑态与需求中的可编辑限制一致"]
        rows.append(
            base_row(
                "功能",
                title,
                steps,
                expected,
            )
        )
    elif coverage_type == "value_boundary":
        for assertion in entry.get("planned_assertions", []):
            text = str(assertion)
            if "最小值边界=" in text:
                value = text.split("=", 1)[1]
                rows.append(
                    base_row(
                        "边界",
                        f"验证{label}等于{value}时允许保存",
                        [f"向{field_ref(label)}输入{value_ref(value)}", "点击保存", "观察保存结果"],
                        [f"{field_ref(label)}等于{value_ref(value)}时可提交", "本次提交不触发边界告警"],
                    )
                )
            elif "最大值边界=" in text:
                value = text.split("=", 1)[1]
                rows.append(
                    base_row(
                        "边界",
                        f"验证{label}等于{value}时允许保存",
                        [f"向{field_ref(label)}输入{value_ref(value)}", "点击保存", "观察保存结果"],
                        [f"{field_ref(label)}等于{value_ref(value)}时可提交", "本次提交不触发边界告警"],
                    )
                )
            elif "长度上限=" in text:
                value = text.split("=", 1)[1]
                rows.append(
                    base_row(
                        "边界",
                        f"验证{label}长度等于{value}时允许保存",
                        [f"向{field_ref(label)}输入长度等于{value_ref(value)}的内容", "点击保存", "观察保存结果"],
                        [f"{field_ref(label)}长度等于{value_ref(value)}时可提交", "本次提交不触发长度告警"],
                    )
                )
        if not rows:
            detail = humanized_entry_detail(entry, label)
            signal_text = entry_signal_text(entry, field_definition)
            if field_name == "row_copy" or ("复制" in signal_text and "新增" in signal_text):
                rows.append(
                    base_row(
                        "功能",
                        "验证点击复制确认后在列表中新增一条落地页数据",
                        [f"点击行内{field_ref(label)}入口", "在复制弹窗中确认名称与游戏", "返回列表定位新行"],
                        ["列表新增一条落地页记录", "新行名称/游戏与弹窗确认值一致或符合产品合并规则"],
                    )
                )
            elif is_image_field(field_definition):
                title, steps, expected = build_image_constraint_case(label, detail, field_definition)
                rows.append(base_row("功能", title, steps, expected))
            elif field_definition.get("control_type") == "checkbox" or "勾选" in signal_text:
                rows.append(
                    base_row(
                        "功能",
                        f"验证{label}未勾选时不可提交且文案固定",
                        [f"保持{field_ref(label)}未勾选并提交", f"查看{field_ref(label)}旁展示文案"],
                        high_signal_expected(label, detail, field_definition, entry),
                    )
                )
            elif has_value(field_definition.get("max_length")):
                max_length = int(field_definition["max_length"])
                rows.append(
                    base_row(
                        "功能",
                        f"验证{feature_name}{label}超过{max_length}个字符时不可保存",
                        [f"向{field_ref(label)}输入第{value_ref(max_length + 1)}个有效字符", "点击保存或进入下一步", "观察校验提示与保存结果"],
                        [f"{field_ref(label)}超过{value_ref(max_length)}个字符时不能保存或被限制输入", f"拦截提示或限制与{value_ref(max_length)}字上限一致"],
                    )
                )
            else:
                rows.append(
                    base_row(
                        "功能",
                    f"验证{detail}",
                    [f"按规则边界操作{field_ref(label)}", "点击保存或进入下一步", "观察校验提示与保存结果"],
                    high_signal_expected(label, detail, field_definition, entry),
                )
            )
    elif coverage_type == "invalid_input":
        if field_name == "display_day_x":
            invalid_cases = [
                ("验证X小于1时保存失败", "向`X`输入小于`1`的值", "`X`小于最小值时本次保存失败"),
                ("验证X大于99时保存失败", "向`X`输入大于`99`的值", "`X`大于最大值时本次保存失败"),
                ("验证X输入非整数时保存失败", "向`X`输入小数或非整数值", "`X`输入非整数时本次保存失败"),
            ]
            for title, step, result in invalid_cases:
                rows.append(
                    base_row(
                        "异常",
                        title,
                        [step, "点击保存", "观察校验提示与保存结果"],
                        [result, "页面提示输入值不符合整数边界要求"],
                    )
                )
        elif field_name == "link_url":
            rows.append(
                base_row(
                    "异常",
                    "验证链接长度超过1000时保存失败",
                    ["向`链接`输入长度超过`1000`的内容", "点击保存", "观察校验提示与保存结果"],
                    ["`链接`长度超过1000时本次保存失败", "页面提示链接长度超出允许范围"],
                )
            )
    elif coverage_type == "data_source_filter":
        title, steps, expected = build_data_source_filter_case_text(entry, field_definition, label)
        rows.append(base_row("功能" if "模糊" in entry_signal_text(entry, field_definition) or "多选" in entry_signal_text(entry, field_definition) or "默认" in entry_signal_text(entry, field_definition) else "数据校验", title, steps, expected))
    elif coverage_type == "data_source_display":
        expected_display = str(entry.get("planned_assertions", [""])[0]).replace(f"`{label}` 候选项展示应包含 `", "").rstrip("`。")
        rows.append(
            base_row(
                "数据校验",
                f"验证{label}候选项展示格式正确",
                [f"打开{field_ref(label)}候选列表", "抽查候选项展示文本", "核对展示内容是否符合规则"],
                [f"{field_ref(label)}候选项展示包含{value_ref(expected_display)}", "候选项展示格式与需求限制一致"],
            )
        )
    elif coverage_type == "data_source_order":
        order_text = str(entry.get("planned_assertions", [""])[0]).replace(f"`{label}` 候选项应满足 `", "").rstrip("`。")
        if "活动创建时间" in order_text and ("倒序" in order_text or "desc" in order_text.lower()):
            order_text = "活动创建时间倒序"
        elif "倒序" in order_text:
            order_text = "倒序"
        elif "升序" in order_text:
            order_text = "升序"
        rows.append(
            base_row(
                "数据校验",
                f"验证{scoped_subject(module_name, label)}按{order_text}展示",
                [f"打开{field_ref(label)}候选列表", "记录首屏候选项顺序", f"核对候选项是否按{value_ref(order_text)}展示"],
                [f"{field_ref(label)}候选项按{value_ref(order_text)}展示", "候选项顺序稳定且可复现"],
            )
        )
    elif coverage_type == "data_rule":
        detail = humanized_entry_detail(entry, label)
        signal_text = entry_signal_text(entry, field_definition)
        if "均分" in signal_text and ("注册" in signal_text or "版位" in signal_text):
            rows.append(
                base_row(
                    "数据校验",
                    "验证聚合落地页各版位注册类指标按子落地页注册数据均分",
                    [
                        "准备同一聚合落地页下多个版位及其子落地页注册样本",
                        "查询聚合落地页各版位数据",
                        "按各版位子落地页产生的注册数据重新计算均分结果",
                    ],
                    [
                        "各版位注册类指标与按子落地页注册数据均分后的结果一致",
                        "不存在将聚合父级总量直接重复计入每个版位的情况",
                    ],
                )
            )
        else:
            rows.append(
                base_row(
                    "数据校验",
                    f"验证{detail}",
                    ["准备覆盖该数据规则的样本数据", "查询页面或接口返回结果", "按需求规则独立复算结果"],
                    ["页面或接口返回结果与独立复算结果一致", "数据口径与需求中的计算规则一致"],
                )
            )
    elif coverage_type == "happy_path_combo":
        rows.append(
            base_row(
                "功能",
                f"验证{feature_name}合法组合场景可提交",
                list(entry.get("planned_assertions", [])) + ["点击保存并观察结果"],
                [
                    "组合条件下所有字段显隐、必填、过滤和排序规则同时成立",
                    "点击保存后页面不再提示必填、边界或数据源错误",
                    "保存后返回列表页可见新增配置且字段值与输入一致",
                ],
            )
        )
    return rows


def merge_group_key(case_data: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(case_data.get("__page_name", "")),
        str(case_data.get("所属模块", "")),
        str(case_data.get("所属功能点", "")),
        str(case_data.get("__target_field", "")),
        str(case_data.get("__merge_rule_type", "")),
        str(case_data.get("__title_signature", "")),
        str(case_data.get("__expected_signature", "")),
    )


def merge_case_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    base = dict(group[0])
    coverage_ids: list[str] = []
    source_origins: list[str] = []
    reasoning_refs: list[str] = []
    case_plan_ids: list[str] = []
    flow_ids: list[str] = []
    priority_candidates: list[str] = []
    for item in group:
        coverage_ids.extend(item.get("__coverage_ids", []))
        source_origins.extend(item.get("__source_origins", []))
        reasoning_refs.extend(item.get("__reasoning_refs", []))
        case_plan_ids.extend(item.get("__case_plan_ids", []))
        flow_ids.extend(item.get("__flow_ids", []))
        priority_candidates.extend(item.get("__priority_candidates", []))

    unique_source_origins = dedupe_preserve_order(source_origins)
    base["__coverage_ids"] = dedupe_preserve_order(coverage_ids)
    base["__source_origins"] = unique_source_origins
    base["__reasoning_refs"] = dedupe_preserve_order(reasoning_refs)
    base["__case_plan_ids"] = dedupe_preserve_order(case_plan_ids)
    base["__flow_ids"] = dedupe_preserve_order(flow_ids)
    base["__priority_candidates"] = dedupe_preserve_order(priority_candidates)
    merged_priority = "high" if "high" in priority_candidates else ("medium" if "medium" in priority_candidates else "low")
    base["优先级"] = case_priority(str(base.get("__case_type", "")), merged_priority, False)
    base["标签"] = case_tags(
        str(base.get("__case_type", "")),
        unique_source_origins,
        False,
        str(base.get("__coverage_type", "") or base.get("__merge_rule_type", "")),
    )
    base["备注"] = build_remarks(
        base["__coverage_ids"],
        unique_source_origins,
        base["__reasoning_refs"],
        base["__case_plan_ids"],
        base["__flow_ids"],
    )
    base["__merged_from"] = len(group)
    return base


def merge_case_drafts(case_drafts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: defaultdict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for case_data in case_drafts:
        grouped[merge_group_key(case_data)].append(case_data)

    merged_cases: list[dict[str, Any]] = []
    merged_groups: list[dict[str, Any]] = []

    for key, items in grouped.items():
        bucketed: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            bucketed[merge_bucket(item)].append(item)

        for bucket_name, bucket_items in bucketed.items():
            merged_case = merge_case_group(bucket_items)
            merged_cases.append(merged_case)
            if len(bucket_items) > 1:
                merged_groups.append(
                    {
                        "merge_key": {
                            "page_name": key[0],
                            "module_name": key[1],
                            "feature_name": key[2],
                            "target_field": key[3],
                            "rule_type": key[4],
                            "title_signature": key[5],
                            "expected_signature": key[6],
                            "bucket": bucket_name,
                        },
                        "title": merged_case.get("用例标题", ""),
                        "test_type": merged_case.get("测试类型", ""),
                        "case_count_before": len(bucket_items),
                        "case_count_after": 1,
                        "coverage_ids": merged_case.get("__coverage_ids", []),
                        "source_origins": merged_case.get("__source_origins", []),
                        "reasoning_refs": merged_case.get("__reasoning_refs", []),
                        "member_cases": [
                            {
                                "title": item.get("用例标题", ""),
                                "coverage_ids": item.get("__coverage_ids", []),
                                "source_origins": item.get("__source_origins", []),
                                "reasoning_refs": item.get("__reasoning_refs", []),
                            }
                            for item in bucket_items
                        ],
                    }
                )

    report = {
        "total_case_drafts_before_merge": len(case_drafts),
        "total_case_drafts_after_merge": len(merged_cases),
        "reduced_case_count": len(case_drafts) - len(merged_cases),
        "merged_group_count": len(merged_groups),
        "merged_groups": merged_groups,
    }
    return merged_cases, report


def compute_residual_duplicate_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: defaultdict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        key = (
            str(case.get("__page_name", "")).strip(),
            str(case.get("所属模块", "")).strip(),
            str(case.get("所属功能点", "")).strip(),
            normalize_signature(str(case.get("用例标题", ""))),
            normalize_signature(str(case.get("测试步骤", ""))),
            normalize_signature(str(case.get("预期结果", ""))),
        )
        grouped[key].append(case)

    duplicate_groups: list[dict[str, Any]] = []
    duplicate_case_count = 0
    for key, items in grouped.items():
        if len(items) <= 1:
            continue
        duplicate_case_count += len(items) - 1
        duplicate_groups.append(
            {
                "page_name": key[0],
                "module_name": key[1],
                "feature_name": key[2],
                "title": items[0].get("用例标题", ""),
                "case_ids": [item.get("用例编号", "") for item in items],
            }
        )

    return {
        "residual_duplicate_case_count": duplicate_case_count,
        "residual_duplicate_group_count": len(duplicate_groups),
        "residual_duplicate_groups": duplicate_groups,
    }


def assign_case_ids(cases: list[dict[str, Any]], project_code: str) -> list[dict[str, Any]]:
    seqs: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    used_ids: set[str] = set()
    for case in cases:
        page_name = str(case.get("__page_name", "")).strip()
        module_name = str(case.get("所属模块", "")).strip()
        case_type = str(case.get("__case_type", "")).strip() or str(case.get("测试类型", "")).strip()
        key = (page_name, module_name, case_type)
        while True:
            seqs[key] += 1
            candidate = case_id(project_code, page_name, module_name, case_type, seqs[key])
            if candidate not in used_ids:
                case["用例编号"] = candidate
                used_ids.add(candidate)
                break
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


def build_case_plan_index(case_plan: dict[str, Any] | None) -> dict[str, list[str]]:
    index: defaultdict[str, list[str]] = defaultdict(list)
    if not isinstance(case_plan, dict):
        return {}
    for plan in case_plan.get("case_plans", []) or []:
        if not isinstance(plan, dict) or not bool(plan.get("should_generate_case")):
            continue
        plan_id = str(plan.get("case_plan_id", "")).strip()
        if not plan_id:
            continue
        coverage_ids: list[str] = []
        if str(plan.get("source_coverage_id", "")).strip():
            coverage_ids.append(str(plan.get("source_coverage_id", "")).strip())
        for coverage_id in plan.get("source_coverage_ids", []) or []:
            if str(coverage_id).strip():
                coverage_ids.append(str(coverage_id).strip())
        for coverage_id in dedupe_preserve_order(coverage_ids):
            index[coverage_id].append(plan_id)
    return {key: dedupe_preserve_order(value) for key, value in index.items()}


def build_case_plan_testcase_index(
    case_plan: dict[str, Any] | None,
) -> dict[str, list[str]]:
    index: defaultdict[str, list[str]] = defaultdict(list)
    if not isinstance(case_plan, dict):
        return {}
    for plan in case_plan.get("case_plans", []) or []:
        if not isinstance(plan, dict) or not bool(plan.get("should_generate_case")):
            continue
        plan_id = str(plan.get("case_plan_id", "")).strip()
        if not plan_id:
            continue
        for testcase_id in plan.get("generated_testcase_ids", []) or []:
            testcase_id_text = str(testcase_id).strip()
            if testcase_id_text:
                index[testcase_id_text].append(plan_id)
    return {key: dedupe_preserve_order(value) for key, value in index.items()}


def apply_planned_testcase_trace(
    cases: list[dict[str, Any]],
    testcase_plan_index: dict[str, list[str]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for case in cases:
        testcase_id = str(case.get("用例编号", "")).strip()
        plan_ids = testcase_plan_index.get(testcase_id, [])
        if not plan_ids:
            continue
        case["__case_plan_ids"] = dedupe_preserve_order(
            [*case.get("__case_plan_ids", []), *plan_ids]
        )
        case["备注"] = build_remarks(
            case.get("__coverage_ids", []),
            case.get("__source_origins", []),
            case.get("__reasoning_refs", []),
            case["__case_plan_ids"],
            case.get("__flow_ids", []),
        )
        result.append(case)
    return result


def build_flow_coverage_map(coverage_matrix: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(coverage_matrix, dict):
        return result
    for entry in coverage_matrix.get("entries", []) or []:
        if not isinstance(entry, dict):
            continue
        for ref in entry.get("structured_refs", []) or []:
            ref_text = str(ref).strip()
            if ref_text.startswith("flows."):
                flow_id = ref_text.split(".", 1)[1]
                if flow_id:
                    result[flow_id] = entry
    return result


def build_generation_order(coverage_matrix: dict[str, Any]) -> tuple[dict[tuple[str, str], int], dict[str, int]]:
    section_order: dict[tuple[str, str], int] = {}
    coverage_order: dict[str, int] = {}
    for index, entry in enumerate(coverage_matrix.get("entries", []) or []):
        if not isinstance(entry, dict):
            continue
        coverage_id = str(entry.get("coverage_id", "")).strip()
        if coverage_id:
            coverage_order[coverage_id] = index
        page_name = str(entry.get("page_name", "")).strip()
        section_name = str(entry.get("section_name", "")).strip()
        if page_name and section_name:
            section_order.setdefault((page_name, section_name), len(section_order))
    return section_order, coverage_order


def infer_flow_context(structured_prd: dict[str, Any], flow: dict[str, Any], coverage_entry: dict[str, Any] | None) -> tuple[str, str, str, str]:
    if coverage_entry:
        page_name = str(coverage_entry.get("page_name", "")).strip()
        section_name = str(coverage_entry.get("section_name", "")).strip()
        module_name = str(coverage_entry.get("module_name", "")).strip()
        feature_name = str(coverage_entry.get("feature_name", "")).strip()
        if page_name and module_name and feature_name:
            return page_name, section_name or "跨板块主流程", module_name, feature_name

    steps = flow.get("steps", []) or []
    first_step = steps[0] if steps and isinstance(steps[0], dict) else {}
    step_module = str(first_step.get("module_name", "")).strip()
    step_feature = str(first_step.get("feature_name", "")).strip()
    for module in structured_prd.get("modules", []) or []:
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []) or []:
            if not isinstance(feature, dict):
                continue
            feature_name = str(feature.get("feature_name", "")).strip()
            if module_name == step_module and (not step_feature or feature_name == step_feature):
                return (
                    str(feature.get("page_name", "")).strip() or "待补充页面",
                    str(feature.get("section_name", "")).strip() or "跨板块主流程",
                    module_name or step_module or "流程模块",
                    feature_name or step_feature or str(flow.get("flow_name", "")).strip() or "流程",
                )

    for module in structured_prd.get("modules", []) or []:
        for feature in module.get("features", []) or []:
            if isinstance(feature, dict) and str(feature.get("page_name", "")).strip():
                return (
                    str(feature.get("page_name", "")).strip(),
                    str(feature.get("section_name", "")).strip() or "跨板块主流程",
                    step_module or str(module.get("module_name", "")).strip() or "流程模块",
                    step_feature or str(flow.get("flow_name", "")).strip() or "流程",
                )

    return "待补充页面", "跨板块主流程", step_module or "流程模块", step_feature or str(flow.get("flow_name", "")).strip() or "流程"


def apply_case_plan_trace(cases: list[dict[str, Any]], case_plan_index: dict[str, list[str]]) -> int:
    traced_count = 0
    for case in cases:
        coverage_ids = dedupe_preserve_order([str(item).strip() for item in case.get("__coverage_ids", []) if str(item).strip()])
        source_origins = dedupe_preserve_order([str(item).strip() for item in case.get("__source_origins", []) if str(item).strip()])
        reasoning_refs = dedupe_preserve_order([str(item).strip() for item in case.get("__reasoning_refs", []) if str(item).strip()])
        flow_ids = dedupe_preserve_order([str(item).strip() for item in case.get("__flow_ids", []) if str(item).strip()])
        case_plan_ids: list[str] = []
        for coverage_id in coverage_ids:
            case_plan_ids.extend(case_plan_index.get(coverage_id, []))
        case_plan_ids = dedupe_preserve_order(case_plan_ids)
        case["__coverage_ids"] = coverage_ids
        case["__source_origins"] = source_origins
        case["__reasoning_refs"] = reasoning_refs
        case["__flow_ids"] = flow_ids
        case["__case_plan_ids"] = case_plan_ids
        if case_plan_ids:
            traced_count += 1
        if coverage_ids or flow_ids or source_origins or reasoning_refs or case_plan_ids:
            case["备注"] = build_remarks(coverage_ids, source_origins, reasoning_refs, case_plan_ids, flow_ids)
    return traced_count


def build_flow_cases(
    structured_prd: dict[str, Any],
    coverage_matrix: dict[str, Any] | None = None,
    case_plan_index: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    project_code = str(structured_prd.get("project_info", {}).get("project_code", "DEMO")).strip() or "DEMO"
    cases: list[dict[str, Any]] = []
    seqs: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    flow_coverage = build_flow_coverage_map(coverage_matrix)
    require_case_plan_trace = bool(case_plan_index)
    for flow in structured_prd.get("flows", []):
        if not isinstance(flow, dict):
            continue
        flow_id = str(flow.get("flow_id", "")).strip()
        flow_name = str(flow.get("flow_name", "")).strip() or flow_id
        steps = flow.get("steps", [])
        if not steps:
            continue
        first_step = steps[0]
        coverage_entry = flow_coverage.get(flow_id)
        coverage_ids = [str(coverage_entry.get("coverage_id", "")).strip()] if coverage_entry else []
        coverage_ids = [coverage_id for coverage_id in coverage_ids if coverage_id]
        if require_case_plan_trace and not any(case_plan_index.get(coverage_id) for coverage_id in coverage_ids):
            continue
        page_name, section_name, module_name, feature_name = infer_flow_context(structured_prd, flow, coverage_entry)
        seqs[(page_name, module_name, "流程验证")] += 1
        cid = case_id(project_code, page_name, module_name, "流程验证", seqs[(page_name, module_name, "流程验证")])
        step_lines = [
            str(step.get("action") or step.get("step_name") or "").strip()
            for step in steps
            if str(step.get("action") or step.get("step_name") or "").strip()
        ]
        step_expected_lines = [
            str(step.get("expected_result") or "").strip()
            for step in steps
            if str(step.get("expected_result") or "").strip()
        ]
        expected_lines = step_expected_lines + [
            str(item).strip() for item in flow.get("success_criteria", []) if str(item).strip()
        ]
        expected_lines = [
            line.replace("保存成功", "保存后")
            .replace("成功展示", "展示")
            .replace("正确展示", "按规则展示")
            .replace("成功", "完成")
            .replace("正确", "按规则")
            for line in expected_lines
        ]
        if not expected_lines:
            expected_lines = ["主流程关键结果达成且页面展示与配置联动一致"]
        terminal_text = " ".join(expected_lines)
        if not any(keyword in terminal_text for keyword in ["状态", "生效", "可见", "完成", "流转", "回传", "展示", "进入游戏"]):
            expected_lines.append(f"{flow_name}流程完成，关键数据状态在目标页面可见")
        cases.append(
            {
                "__page_name": page_name,
                "__section_name": section_name or "跨板块主流程",
                "__case_type": "流程验证",
                "__emit_mode": "main_testcase",
                "__coverage_ids": coverage_ids,
                "__source_origins": ["explicit_rule"],
                "__reasoning_refs": [],
                "__case_plan_ids": [],
                "__flow_ids": [flow_id] if flow_id else [],
                "用例编号": cid,
                "所属模块": module_name,
                "所属功能点": feature_name or flow_name,
                "用例标题": f"验证{flow_name}主流程打通",
                "前置条件": f"{flow_name}涉及的配置与展示入口均可访问",
                "测试步骤": html_lines(step_lines[:4] or ["执行主流程关键步骤"]),
                "预期结果": html_lines(expected_lines[:4]),
                "优先级": "P0",
                "标签": case_tags("流程验证", ["explicit_rule"], True, "flow"),
                "测试类型": "流程验证",
                "备注": build_remarks(coverage_ids, ["explicit_rule"], [], [], [flow_id] if flow_id else []),
            }
        )
    return cases


def build_field_audit(coverage_matrix: dict[str, Any]) -> dict[str, Any]:
    entries = [
        compact_entry(entry)
        for entry in coverage_matrix.get("entries", [])
        if str(entry.get("emit_mode", "")).strip() == "audit_item"
    ]
    for index, item in enumerate(entries, start=1):
        item["audit_id"] = f"AUD-ITEM-{index:03d}"
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_code": coverage_matrix.get("project_code", ""),
        "work_item_id": coverage_matrix.get("work_item_id", ""),
        "item_count": len(entries),
        "items": entries,
    }


def build_grouped_audit(coverage_matrix: dict[str, Any]) -> dict[str, Any]:
    entries = [
        compact_entry(entry)
        for entry in coverage_matrix.get("entries", [])
        if str(entry.get("emit_mode", "")).strip() == "group_audit"
    ]

    page_metadata_groups: list[dict[str, Any]] = []
    page_buckets: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        page_buckets[str(entry.get("page_name", "")).strip()].append(entry)
    for index, (page_name, bucket) in enumerate(sorted(page_buckets.items()), start=1):
        page_metadata_groups.append(
            {
                "group_id": f"GA-PAGE-{index:03d}",
                "audit_type": "page_level_metadata_audit",
                "page_name": page_name,
                "coverage_ids": [item["coverage_id"] for item in bucket],
                "item_count": len(bucket),
                "items": bucket,
            }
        )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_code": coverage_matrix.get("project_code", ""),
        "work_item_id": coverage_matrix.get("work_item_id", ""),
        "group_count": len(page_metadata_groups),
        "groups_by_type": {
            "page_level_metadata_audit": page_metadata_groups,
            "module_level_field_property_audit": [],
            "table_header_audit": [],
        },
    }
    return payload


def generate_testcases_markdown(structured_prd: dict[str, Any], coverage_matrix: dict[str, Any], case_plan: dict[str, Any] | None = None) -> str:
    bundle = generate_testcases_bundle(structured_prd, coverage_matrix, case_plan)
    return bundle["markdown"]


def generate_testcases_bundle(
    structured_prd: dict[str, Any],
    coverage_matrix: dict[str, Any],
    case_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_code = str(structured_prd.get("project_info", {}).get("project_code", "DEMO")).strip() or "DEMO"
    feature_map = structured_feature_map(structured_prd)
    field_map = structured_field_map(structured_prd)
    field_context = field_context_map(structured_prd)
    case_plan_index = build_case_plan_index(case_plan)
    testcase_plan_index = build_case_plan_testcase_index(case_plan)
    active_case_plans = [
        plan
        for plan in (case_plan.get("case_plans", []) if isinstance(case_plan, dict) else [])
        if isinstance(plan, dict) and bool(plan.get("should_generate_case"))
    ]
    if active_case_plans and not (coverage_matrix.get("entries", []) or []):
        raise ValueError(
            "存在 should_generate_case=true 的 Case Plan，但 coverage_matrix.entries 为空；"
            "禁止用空生成结果覆盖正式 testcase"
        )
    seqs: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    case_drafts: list[dict[str, Any]] = []

    entries = list(coverage_matrix.get("entries", []))

    for entry in entries:
        for row in build_case_rows(entry, project_code, seqs, feature_map, field_map, field_context):
            case_drafts.append(row)

    merged_cases, duplicate_report = merge_case_drafts(case_drafts)
    flow_cases = build_flow_cases(structured_prd, coverage_matrix, case_plan_index)
    main_cases = [case for case in merged_cases if str(case.get("__emit_mode", "")).strip() == "main_testcase"]
    main_cases.extend(build_structured_rule_supplements(structured_prd))
    main_cases.extend(build_coverage_combination_supplements(coverage_matrix))
    main_cases.extend(flow_cases)
    case_plan_trace_count = apply_case_plan_trace(main_cases, case_plan_index)
    untraced_case_count = 0
    if case_plan is not None and case_plan_index:
        before_filter = len(main_cases)
        main_cases = [case for case in main_cases if case.get("__case_plan_ids")]
        untraced_case_count = before_filter - len(main_cases)
        case_plan_trace_count = len(main_cases)
    main_cases = assign_case_ids(main_cases, project_code)
    if case_plan is not None and not case_plan_index:
        if not testcase_plan_index:
            raise ValueError(
                "case_plan 缺少 source_coverage_ids / generated_testcase_ids，不能控制正式 testcase 生成"
            )
        main_cases = apply_planned_testcase_trace(main_cases, testcase_plan_index)
        case_plan_trace_count = len(main_cases)
    if active_case_plans and not main_cases:
        raise ValueError(
            "Case Plan 未匹配到任何候选 testcase；禁止写出空主用例，请补齐 source_coverage_ids 或由 AI Case Generator 生成完整 bundle"
        )
    section_order, coverage_order = build_generation_order(coverage_matrix)

    def case_sort_key(item: dict[str, Any]) -> tuple[int, int, str, str, str]:
        coverage_positions = [
            coverage_order.get(str(coverage_id).strip(), 10**9)
            for coverage_id in item.get("__coverage_ids", [])
            if str(coverage_id).strip()
        ]
        first_coverage_position = min(coverage_positions) if coverage_positions else 10**9
        page_name = str(item.get("__page_name", "")).strip()
        section_name = str(item.get("__section_name", "")).strip()
        return (
            section_order.get((page_name, section_name), 10**9),
            first_coverage_position,
            page_name,
            section_name,
            str(item.get("用例编号", "")).strip(),
        )

    main_cases.sort(key=case_sort_key)
    duplicate_report["total_cases_after_flow_append"] = len(main_cases)
    duplicate_report["flow_case_count"] = len(flow_cases)
    duplicate_report.update(compute_residual_duplicate_report(main_cases))

    field_audit = build_field_audit(coverage_matrix)
    grouped_audit = build_grouped_audit(coverage_matrix)

    return {
        "markdown": render_markdown(main_cases),
        "main_markdown": render_markdown(main_cases),
        "main_case_count": len(main_cases),
        "field_audit": field_audit,
        "grouped_audit": grouped_audit,
        "duplicate_case_report": duplicate_report,
        "case_count_before_merge": len(case_drafts),
        "case_count_after_merge": len(main_cases),
        "case_plan_trace_count": case_plan_trace_count,
        "untraced_case_count_filtered": untraced_case_count,
    }
