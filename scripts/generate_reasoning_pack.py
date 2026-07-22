#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


IMAGE_HEADER_RE = re.compile(r"^##\s+图片\s+(.+?)\s*$")
SUB_HEADER_RE = re.compile(r"^###\s+(.+?)\s*$")
RANGE_RE = re.compile(r"\[(\d+)\s*,\s*(\d+)\]")
VARCHAR_RE = re.compile(r"varchar\((\d+)\)", re.IGNORECASE)
MAX_COUNT_RE = re.compile(r"不允许超过(\d+)条")
DATE_RE = re.compile(r"`?(\d{4}-\d{2}-\d{2})`?")


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def slugify(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return normalized or "item"


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def build_source_ref(
    source_type: str,
    path: str,
    excerpt: str,
    page_name: str = "",
    section_name: str = "",
    field_name: str = "",
) -> dict[str, str]:
    payload = {
        "source_type": source_type,
        "path": path,
        "excerpt": excerpt.strip(),
    }
    if page_name:
        payload["page_name"] = page_name
    if section_name:
        payload["section_name"] = section_name
    if field_name:
        payload["field_name"] = field_name
    return payload


def parse_received_screenshots(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    subsection = ""

    def ensure_record() -> dict[str, Any]:
        assert current is not None
        return current

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        image_match = IMAGE_HEADER_RE.match(stripped)
        if image_match:
            if current:
                records.append(current)
            current = {
                "image_label": image_match.group(1).strip(),
                "expected_files": [],
                "pages": [],
                "sections": [],
                "fields": [],
                "explicit_rules": [],
                "notes": [],
                "source_path": display_path(path),
            }
            subsection = ""
            continue

        sub_match = SUB_HEADER_RE.match(stripped)
        if sub_match:
            subsection = sub_match.group(1).strip()
            continue

        if not stripped.startswith("- ") or current is None:
            continue

        value = stripped[2:].strip()
        record = ensure_record()
        if subsection == "预期图片文件":
            record["expected_files"].append(value.strip("`"))
        elif subsection == "页面":
            record["pages"].append(value)
        elif subsection == "板块":
            record["sections"].append(value)
        elif subsection == "字段":
            record["fields"].append(value)
        elif subsection == "识别到的显式规则":
            record["explicit_rules"].append(value)
        elif subsection == "备注":
            record["notes"].append(value)
        elif subsection == "字段定义 + 说明表绑定":
            record["notes"].append(value)

    if current:
        records.append(current)
    return records


def parse_requirement_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"title": "", "sections": {}, "rule_lines": [], "source_path": ""}
    lines = path.read_text(encoding="utf-8").splitlines()
    title = ""
    current_section = ""
    sections: dict[str, list[str]] = defaultdict(list)
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
            continue
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
            continue
        if current_section:
            value = stripped[2:].strip() if stripped.startswith("- ") else stripped
            if value:
                sections[current_section].append(value)

    rule_sections = ("2. 需求结论", "5. 面向研发的需求拆解", "6. 面向测试的验收关注点", "7. 数据 / 埋点 / 接口 / 配置要求")
    rule_lines = unique_strings(
        [line for section in rule_sections for line in sections.get(section, [])]
    )
    return {
        "title": title,
        "sections": dict(sections),
        "rule_lines": rule_lines,
        "source_path": display_path(path),
    }


def collect_rule_candidates(section: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for rule in section.get("section_rules", []):
        if isinstance(rule, str) and rule.strip():
            candidates.append(rule.strip())
    for field_rule in section.get("field_rules", []):
        if isinstance(field_rule, dict):
            text = str(field_rule.get("rule_text", "")).strip()
            if text:
                candidates.append(text)
    return unique_strings(candidates)


def parse_numeric_constraints(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    varchar_match = VARCHAR_RE.search(text)
    if varchar_match:
        result["max_length"] = int(varchar_match.group(1))
    range_match = RANGE_RE.search(text)
    if range_match:
        result["min"] = int(range_match.group(1))
        result["max"] = int(range_match.group(2))
    max_count_match = MAX_COUNT_RE.search(text)
    if max_count_match:
        result["max_count"] = int(max_count_match.group(1))
    if "正整数" in text:
        result["integer_only"] = True
    if "非负整数" in text:
        result["integer_only"] = True
        result.setdefault("min", 0)
    if "仅支持上传一张图片" in text:
        result["single_image_only"] = True
    return result


def infer_rule_terms(text: str) -> list[str]:
    terms: list[str] = []
    terms.extend(match.group(1) for match in DATE_RE.finditer(text))
    if "关闭、开启" in text:
        terms.extend(["关闭", "开启"])
    if "无交互、活动中心、链接、展示企微单人单码" in text:
        terms.extend(["无交互", "活动中心", "链接", "展示企微单人单码"])
    elif "无交互、活动中心、链接" in text:
        terms.extend(["无交互", "活动中心", "链接"])
    range_match = RANGE_RE.search(text)
    if range_match:
        terms.extend([range_match.group(1), range_match.group(2)])
    varchar_match = VARCHAR_RE.search(text)
    if varchar_match:
        terms.append(varchar_match.group(1))
    max_count_match = MAX_COUNT_RE.search(text)
    if max_count_match:
        terms.append(max_count_match.group(1))
    return unique_strings(terms)


def classify_rule(text: str) -> str:
    if "来源于" in text or "状态=发布" in text or "倒序" in text:
        return "data_source_rule"
    if "默认" in text:
        return "default_rule"
    if "不允许超过" in text:
        return "max_count_rule"
    if "必填" in text or "必选" in text or "非必填" in text:
        return "field_requirement"
    if "展示" in text and "时" in text:
        return "conditional_visibility"
    if "不允许编辑" in text or "不可编辑" in text:
        return "editability_rule"
    if "排序" in text or "顺位" in text or "倒序" in text:
        return "order_rule"
    return "explicit_rule"


def build_requirement_summary(
    manifest: dict[str, Any],
    image_evidence: dict[str, Any],
    screenshot_items: list[dict[str, Any]],
    requirement_doc: dict[str, Any],
) -> dict[str, Any]:
    page_names = unique_strings([img.get("page_name", "") for img in image_evidence.get("images", [])])
    section_names = unique_strings(
        [
            section.get("section_name", "")
            for img in image_evidence.get("images", [])
            for section in img.get("sections", [])
        ]
    )
    notes = unique_strings(
        [
            note
            for item in screenshot_items
            for note in item.get("notes", [])
            if "当前图" in note or "说明" in note or "首次引入" in note
        ]
    )[:6]
    title = str(
        requirement_doc.get("title")
        or manifest.get("title")
        or manifest.get("work_item_id")
        or "待确认"
    ).strip()
    conclusions = requirement_doc.get("sections", {}).get("2. 需求结论", [])
    if conclusions:
        summary_text = " ".join(conclusions)
    else:
        summary_text = (
            f"{title} 当前输入覆盖 {len(page_names)} 个逻辑页面、{len(section_names)} 类主要板块，"
            "reasoning_pack 沉淀显式规则、字段约束、数据来源、边界和潜在风险。"
        )
    if requirement_doc.get("source_path"):
        notes = unique_strings(
            [
                *notes,
                f"归一化需求来源：{requirement_doc['source_path']}",
                *requirement_doc.get("source_notes", []),
            ]
        )
    return {
        "title": title,
        "summary_text": summary_text,
        "primary_pages": page_names,
        "primary_user_surfaces": section_names,
        "source_notes": notes,
    }


def build_explicit_rules(
    screenshot_items: list[dict[str, Any]],
    image_evidence: dict[str, Any],
    requirement_doc: dict[str, Any],
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    counter = 1

    for text in requirement_doc.get("rule_lines", []):
        key = ("需求整理", "", text)
        if key in seen:
            continue
        seen.add(key)
        rules.append(
            {
                "id": f"ER-{counter:03d}",
                "title": f"需求整理-{classify_rule(text)}",
                "statement": text,
                "confidence": 0.99,
                "reasoning_notes": ["来自主流程 requirement_summary.md 的确认需求。"],
                "must_preserve_terms": infer_rule_terms(text),
                "source_refs": [
                    build_source_ref(
                        "input_markdown",
                        str(requirement_doc.get("source_path", "")),
                        text,
                    )
                ],
            }
        )
        counter += 1

    for item in screenshot_items:
        page_name = item.get("pages", ["待确认"])[0] if item.get("pages") else "待确认"
        expected_files = item.get("expected_files", [])
        source_path = item.get("source_path", "")
        for text in item.get("explicit_rules", []):
            key = (page_name, "", text)
            if key in seen:
                continue
            seen.add(key)
            source_refs = [
                build_source_ref(
                    "input_markdown",
                    source_path,
                    text,
                    page_name=page_name,
                )
            ]
            for expected_file in expected_files:
                source_refs.append(
                    build_source_ref(
                        "image_evidence",
                        expected_file,
                        text,
                        page_name=page_name,
                    )
                )
            rules.append(
                {
                    "id": f"ER-{counter:03d}",
                    "title": f"{page_name}-{classify_rule(text)}",
                    "statement": text,
                    "confidence": 0.98,
                    "reasoning_notes": [
                        "直接来自原始截图接收记录，属于高优先级显式规则。"
                    ],
                    "must_preserve_terms": infer_rule_terms(text),
                    "source_refs": source_refs,
                }
            )
            counter += 1

    for image in image_evidence.get("images", []):
        page_name = str(image.get("page_name", "")).strip()
        source_file = str(image.get("source_file", "")).strip()
        for section in image.get("sections", []):
            section_name = str(section.get("section_name", "")).strip()
            for text in collect_rule_candidates(section):
                key = (page_name, section_name, text)
                if key in seen:
                    continue
                seen.add(key)
                rules.append(
                    {
                        "id": f"ER-{counter:03d}",
                        "title": f"{page_name}-{section_name}-{classify_rule(text)}",
                        "statement": text,
                        "confidence": float(section.get("confidence", 0.9)),
                        "reasoning_notes": [
                            "来自 image_evidence 的页面/板块规则抽取。"
                        ],
                        "must_preserve_terms": infer_rule_terms(text),
                        "source_refs": [
                            build_source_ref(
                                "image_section",
                                source_file,
                                text,
                                page_name=page_name,
                                section_name=section_name,
                            )
                        ],
                    }
                )
                counter += 1

    return rules


def build_implicit_rules(
    image_evidence: dict[str, Any],
    screenshot_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    images = image_evidence.get("images", [])
    backend_pages = [
        image
        for image in images
        if "配置页" in str(image.get("page_name", ""))
    ]
    frontend_pages = [
        image
        for image in images
        if "配置页" not in str(image.get("page_name", ""))
    ]
    section_counter = Counter(
        section.get("section_type", "")
        for image in backend_pages
        for section in image.get("sections", [])
        if section.get("section_type")
    )
    field_counter = Counter(
        field.get("field_name", "")
        for image in backend_pages
        for section in image.get("sections", [])
        for field in section.get("field_candidates", [])
        if field.get("field_name")
    )

    implicit_rules: list[dict[str, Any]] = []
    if section_counter:
        common_sections = [name for name, count in section_counter.items() if count >= 3]
        implicit_rules.append(
            {
                "id": "IR-001",
                "title": "后台配置页共享配置骨架",
                "statement": "banner、瓷片区、金刚区、弹窗等后台配置页复用同一套筛选区/列表区/操作区/添加弹窗/排序弹窗骨架，后续结构化应优先按统一配置家族建模。",
                "confidence": 0.88,
                "reasoning_notes": [
                    f"至少 {len(common_sections)} 类 section_type 在多个后台配置页重复出现。"
                ],
                "must_preserve_terms": common_sections,
                "source_refs": [
                    build_source_ref(
                        "image_evidence",
                        str(image.get("source_file", "")),
                        "重复配置页骨架",
                        page_name=str(image.get("page_name", "")),
                    )
                    for image in backend_pages[:4]
                ],
            }
        )

    repeated_fields = [name for name, count in field_counter.items() if count >= 3]
    if repeated_fields:
        implicit_rules.append(
            {
                "id": "IR-002",
                "title": "字段矩阵复用模式",
                "statement": "展示类型、X、触达用户类型、跳转类型、选择活动、链接、展示tab、状态形成跨模块复用字段矩阵，后续应保留同构字段的共性规则与差异项。",
                "confidence": 0.9,
                "reasoning_notes": [
                    "多个后台页面共享相同字段矩阵，但条数上限、跳转枚举和说明表枚举存在差异。"
                ],
                "must_preserve_terms": repeated_fields,
                "source_refs": [
                    build_source_ref(
                        "image_evidence",
                        str(image.get("source_file", "")),
                        "字段矩阵重复出现",
                        page_name=str(image.get("page_name", "")),
                    )
                    for image in backend_pages[:4]
                ],
            }
        )

    if frontend_pages:
        implicit_rules.append(
            {
                "id": "IR-003",
                "title": "后台配置驱动 C 端分发与弹窗",
                "statement": "后台导航、banner、瓷片区、金刚区和弹窗配置共同驱动小程序首页分发页、企微单人单码弹窗页和营销弹窗页的展示结果，后续 traceability 需要显式连接后台配置与 C 端表现。",
                "confidence": 0.86,
                "reasoning_notes": [
                    "截图 6 和截图 7 显示了 C 端页面与弹窗承接面。"
                ],
                "must_preserve_terms": unique_strings(
                    [str(image.get("page_name", "")) for image in frontend_pages]
                ),
                "source_refs": [
                    build_source_ref(
                        "image_evidence",
                        str(image.get("source_file", "")),
                        "C端承接面",
                        page_name=str(image.get("page_name", "")),
                    )
                    for image in frontend_pages
                ],
            }
        )

    if any("顶部tab" in note for item in screenshot_items for note in item.get("explicit_rules", []) + item.get("notes", [])):
        implicit_rules.append(
            {
                "id": "IR-004",
                "title": "顶部 tab 为统一归属维度",
                "statement": "首页 banner、瓷片区、金刚区与弹窗均从属于顶部 tab，后续生成 testcase 时不能只测配置保存，还要验证 tab 归属与展示面联动。",
                "confidence": 0.84,
                "reasoning_notes": [
                    "原始输入中多次出现“从属于顶部tab”的说明。"
                ],
                "must_preserve_terms": ["顶部tab"],
                "source_refs": [
                    build_source_ref(
                        "input_markdown",
                        item.get("source_path", ""),
                        note,
                    )
                    for item in screenshot_items
                    for note in item.get("explicit_rules", []) + item.get("notes", [])
                    if "顶部tab" in note
                ],
            }
        )

    return implicit_rules


def match_related_rules(
    image_item: dict[str, Any],
    page_name: str,
    field_name: str,
    display_name: str,
    section_rules: list[str],
) -> list[str]:
    candidates = image_item.get("explicit_rules", []) if image_item else []
    matcher_tokens = unique_strings([field_name, display_name])
    matched = []
    for rule in candidates + section_rules:
        if any(token and token in rule for token in matcher_tokens):
            matched.append(rule)
    return unique_strings(matched)


def build_field_constraints(
    image_evidence: dict[str, Any],
    screenshot_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    screenshot_by_file = {
        file_path: item
        for item in screenshot_items
        for file_path in item.get("expected_files", [])
    }
    constraints: list[dict[str, Any]] = []
    counter = 1

    for image in image_evidence.get("images", []):
        source_file = str(image.get("source_file", "")).strip()
        screenshot_item = screenshot_by_file.get(source_file)
        for section in image.get("sections", []):
            page_name = str(image.get("page_name", "")).strip()
            section_name = str(section.get("section_name", "")).strip()
            section_rule_candidates = collect_rule_candidates(section)
            for field in section.get("field_candidates", []):
                field_name = str(field.get("field_name", "")).strip()
                display_name = str(field.get("display_name", "")).strip() or field_name
                raw_rules = match_related_rules(
                    screenshot_item or {},
                    page_name,
                    field_name,
                    display_name,
                    section_rule_candidates,
                )

                normalized = {
                    "required": bool(field.get("required", False)),
                }
                if field.get("default_value") not in ("", None):
                    normalized["default_value"] = field.get("default_value")
                enum_values = [str(item).strip() for item in field.get("enum_values", []) if str(item).strip()]
                if enum_values:
                    normalized["enum_values"] = enum_values

                summary_parts = []
                if field.get("control_type"):
                    summary_parts.append(f"控件={field.get('control_type')}")
                if field.get("required") is True:
                    summary_parts.append("必填")
                if field.get("required") is False:
                    summary_parts.append("非必填")
                if field.get("default_value") not in ("", None):
                    summary_parts.append(f"默认值={field.get('default_value')}")
                if enum_values:
                    summary_parts.append("枚举=" + "、".join(enum_values))

                for rule_text in raw_rules:
                    parsed = parse_numeric_constraints(rule_text)
                    normalized.update(parsed)
                    if "在" in rule_text and "时展示" in rule_text:
                        normalized["visible_when"] = rule_text
                    if "不允许编辑" in rule_text or "不可编辑" in rule_text:
                        normalized["readonly_when"] = rule_text
                    if "必填" in rule_text or "必选" in rule_text:
                        normalized["required"] = "非必填" not in rule_text
                    if rule_text not in summary_parts:
                        summary_parts.append(rule_text)

                constraints.append(
                    {
                        "constraint_id": f"FC-{counter:03d}",
                        "page_name": page_name,
                        "section_name": section_name,
                        "field_name": field_name,
                        "display_name": display_name,
                        "control_type": str(field.get("control_type", "")).strip(),
                        "data_type": str(field.get("data_type", "")).strip(),
                        "constraint_summary": "；".join(unique_strings(summary_parts)) or f"{display_name} 字段约束待补充",
                        "normalized_constraints": normalized,
                        "raw_rule_texts": raw_rules,
                        "confidence": float(section.get("confidence", 0.9)),
                        "source_refs": [
                            build_source_ref(
                                "image_section",
                                source_file,
                                display_name,
                                page_name=page_name,
                                section_name=section_name,
                                field_name=field_name,
                            )
                        ],
                    }
                )
                counter += 1
    return constraints


def extract_filters_and_orders(text: str) -> tuple[list[str], list[str]]:
    filters: list[str] = []
    orders: list[str] = []
    if "状态=发布" in text:
        filters.append("状态=发布")
    if "小程序活动" in text:
        filters.append("活动中心渠道=小程序活动")
    if "小程序导航名称列表" in text:
        filters.append("来源=小程序导航名称列表")
    if "所有开启的导航" in text or "状态为开启的导航" in text:
        filters.append("状态=开启")
    if "创建时间倒序" in text or "按活动创建时间倒序" in text or "后台数据按照创建时间倒序排列" in text:
        orders.append("创建时间倒序")
    if "顺位上移" in text:
        orders.append("删除/关闭后顺位上移")
    if "置于最前" in text:
        orders.append("新增后置于最前")
    return unique_strings(filters), unique_strings(orders)


def build_data_source_rules(
    image_evidence: dict[str, Any],
    screenshot_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    screenshot_by_file = {
        file_path: item
        for item in screenshot_items
        for file_path in item.get("expected_files", [])
    }
    rules: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    counter = 1

    for image in image_evidence.get("images", []):
        source_file = str(image.get("source_file", "")).strip()
        screenshot_item = screenshot_by_file.get(source_file)
        for section in image.get("sections", []):
            page_name = str(image.get("page_name", "")).strip()
            section_name = str(section.get("section_name", "")).strip()
            candidate_texts = collect_rule_candidates(section)
            if screenshot_item:
                candidate_texts.extend(screenshot_item.get("explicit_rules", []))
            for text in unique_strings(candidate_texts):
                if not any(token in text for token in ["来源于", "状态=发布", "倒序", "导航名称列表", "仅展示状态为开启", "所有开启的导航"]):
                    continue
                filters, orders = extract_filters_and_orders(text)
                key = (page_name, section_name, text)
                if key in seen:
                    continue
                seen.add(key)
                data_source = ""
                if "来源于" in text:
                    data_source = text.split("来源于", 1)[1].strip("；。 ")
                elif "导航名称列表" in text:
                    data_source = "小程序导航名称列表"
                rules.append(
                    {
                        "rule_id": f"DS-{counter:03d}",
                        "title": f"{page_name}-{section_name}-数据来源/排序规则",
                        "page_name": page_name,
                        "section_name": section_name,
                        "field_name": "",
                        "statement": text,
                        "data_source": data_source,
                        "filters": filters,
                        "order_by": orders,
                        "confidence": float(section.get("confidence", 0.9)),
                        "source_refs": [
                            build_source_ref(
                                "image_section",
                                source_file,
                                text,
                                page_name=page_name,
                                section_name=section_name,
                            )
                        ],
                    }
                )
                counter += 1
    return rules


def build_business_risks(
    field_constraints: list[dict[str, Any]],
    data_source_rules: list[dict[str, Any]],
    implicit_rules: list[dict[str, Any]],
    screenshot_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = [
        {
            "risk_id": "RISK-001",
            "title": "排序与容量规则容易实现漂移",
            "risk_statement": "后台列表创建时间倒序、排序弹窗初始顺序、删除/关闭后顺位上移、新增置于最前和单 tab 条数上限同时存在，任何一个环节遗漏都可能导致线上展示顺序异常。",
            "severity": "high",
            "impact_scope": ["后台配置页", "排序弹窗", "C端首页分发位"],
            "source_refs": [
                rule["source_refs"][0]
                for rule in data_source_rules
                if any(token in rule["statement"] for token in ["顺位", "置于最前", "倒序"])
            ][:4],
        },
        {
            "risk_id": "RISK-002",
            "title": "状态过滤与展示面联动风险",
            "risk_statement": "多处规则要求只消费开启状态配置，若后台状态默认值、排序候选过滤或 C 端消费口径不一致，会出现可配置但不可展示或误展示。",
            "severity": "high",
            "impact_scope": ["状态字段", "排序候选", "首页分发页", "弹窗"],
            "source_refs": [
                item["source_refs"][0]
                for item in implicit_rules[:1]
            ]
            + [
                constraint["source_refs"][0]
                for constraint in field_constraints
                if constraint["field_name"] == "status"
            ][:3],
        },
        {
            "risk_id": "RISK-003",
            "title": "触达用户类型枚举跨模块不一致",
            "risk_statement": "banner、瓷片区、金刚区、弹窗都依赖触达用户类型说明表，但金刚区/弹窗新增了“付费未添加企微用户”等枚举，若共用契约没有区分模块差异，容易出现错误枚举或缺少附加字段。",
            "severity": "medium",
            "impact_scope": ["触达用户类型", "充值金额区间", "弹窗引流"],
            "source_refs": [
                build_source_ref(
                    "input_markdown",
                    item.get("source_path", ""),
                    note,
                )
                for item in screenshot_items
                for note in item.get("notes", [])
                if "付费未添加企微用户" in note or "说明表" in note
            ][:4],
        },
    ]

    if any(
        ("两个逻辑页面" in note) or ("两个独立页面" in note) or ("显式拆开" in note)
        for item in screenshot_items
        for note in item.get("notes", [])
    ):
        risks.append(
            {
                "risk_id": "RISK-004",
                "title": "单张截图承载多逻辑页面导致投影错误",
                "risk_statement": "截图 6 同时覆盖首页分发页和企微单人单码弹窗页，如果后续只按单页面投影，会把弹窗规则压缩进首页规则，导致 traceability 和 testcase 错位。",
                "severity": "medium",
                "impact_scope": ["首页分发页", "企微单人单码弹窗页"],
                "source_refs": [
                    build_source_ref(
                        "input_markdown",
                        item.get("source_path", ""),
                        note,
                    )
                    for item in screenshot_items
                    for note in item.get("notes", [])
                    if ("两个逻辑页面" in note) or ("两个独立页面" in note) or ("显式拆开" in note)
                ][:1],
            }
        )
    return risks


def build_edge_cases(field_constraints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    counter = 1
    for constraint in field_constraints:
        normalized = constraint.get("normalized_constraints", {})
        display_name = constraint["display_name"]
        if "max_length" in normalized:
            limit = normalized["max_length"]
            cases.append(
                {
                    "edge_case_id": f"EC-{counter:03d}",
                    "title": f"{display_name} 长度上限边界",
                    "scenario": f"{display_name} 长度等于 {limit} 与超过 {limit} 的保存行为都需要保留。",
                    "priority": "P1",
                    "related_field": constraint["field_name"],
                    "source_refs": constraint["source_refs"],
                }
            )
            counter += 1
        if "min" in normalized or "max" in normalized:
            cases.append(
                {
                    "edge_case_id": f"EC-{counter:03d}",
                    "title": f"{display_name} 数值边界",
                    "scenario": f"{display_name} 需要覆盖最小值 {normalized.get('min', '待确认')}、最大值 {normalized.get('max', '待确认')} 及越界输入。",
                    "priority": "P1",
                    "related_field": constraint["field_name"],
                    "source_refs": constraint["source_refs"],
                }
            )
            counter += 1
        if normalized.get("max_count"):
            cases.append(
                {
                    "edge_case_id": f"EC-{counter:03d}",
                    "title": f"{display_name or constraint['page_name']} 条数上限",
                    "scenario": f"同一 tab 下超过 {normalized['max_count']} 条时需要阻止保存并保留提示。",
                    "priority": "P0",
                    "related_field": constraint["field_name"],
                    "source_refs": constraint["source_refs"],
                }
            )
            counter += 1
        if normalized.get("single_image_only"):
            cases.append(
                {
                    "edge_case_id": f"EC-{counter:03d}",
                    "title": f"{display_name} 单图片上传限制",
                    "scenario": f"{display_name} 仅支持上传一张图片，超过数量或重复上传的处理需要明确。",
                    "priority": "P2",
                    "related_field": constraint["field_name"],
                    "source_refs": constraint["source_refs"],
                }
            )
            counter += 1
    return cases[:16]


def build_ambiguities(
    image_evidence: dict[str, Any],
    screenshot_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ambiguities: list[dict[str, Any]] = []
    counter = 1

    for image in image_evidence.get("images", []):
        source_file = str(image.get("source_file", "")).strip()
        for section in image.get("sections", []):
            if section.get("needs_confirmation") or str(section.get("ambiguity_reason", "")).strip():
                ambiguities.append(
                    {
                        "ambiguity_id": f"AMB-{counter:03d}",
                        "title": f"{image.get('page_name', '待确认')}-{section.get('section_name', '待确认')} 待确认",
                        "description": str(section.get("ambiguity_reason", "")).strip() or "图片证据标记了 needs_confirmation。",
                        "status": "open",
                        "suggested_resolution": "补充产品说明或在下一轮结构化前人工确认。",
                        "source_refs": [
                            build_source_ref(
                                "image_section",
                                source_file,
                                str(section.get("ambiguity_reason", "")).strip() or "needs_confirmation",
                                page_name=str(image.get("page_name", "")),
                                section_name=str(section.get("section_name", "")),
                            )
                        ],
                    }
                )
                counter += 1

    for item in screenshot_items:
        for note in item.get("notes", []):
            if ("两个逻辑页面" in note) or ("两个独立页面" in note) or ("显式拆开" in note):
                ambiguities.append(
                    {
                        "ambiguity_id": f"AMB-{counter:03d}",
                        "title": "单张截图包含两个逻辑页面",
                        "description": note,
                        "status": "mitigated",
                        "suggested_resolution": "在 reasoning/structured_prd 中拆成首页分发页与企微单人单码弹窗页两个独立页面。",
                        "source_refs": [
                            build_source_ref(
                                "input_markdown",
                                item.get("source_path", ""),
                                note,
                            )
                        ],
                    }
                )
                counter += 1
    return ambiguities


def build_test_dimensions(
    field_constraints: list[dict[str, Any]],
    data_source_rules: list[dict[str, Any]],
    business_risks: list[dict[str, Any]],
    ambiguities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = [
        {
            "dimension_id": "TD-001",
            "dimension": "字段必填与默认值",
            "rationale": "多个后台配置页依赖相同字段矩阵，字段必填、默认关闭、默认空值是基础高频风险点。",
            "priority": "high",
            "related_reasoning_ids": ["IR-002"],
        },
        {
            "dimension_id": "TD-002",
            "dimension": "条件展示与条件只读",
            "rationale": "跳转类型、展示类型和活动中心场景会改变字段显隐与编辑性，容易被压缩丢失。",
            "priority": "high",
            "related_reasoning_ids": [],
        },
        {
            "dimension_id": "TD-003",
            "dimension": "数据来源、过滤与排序",
            "rationale": "候选活动列表、展示 tab 列表、排序弹窗候选和状态过滤共同决定真实消费口径。",
            "priority": "high",
            "related_reasoning_ids": [],
        },
        {
            "dimension_id": "TD-004",
            "dimension": "条数上限与顺位变化",
            "rationale": business_risks[0]["risk_statement"] if business_risks else "排序/容量规则需要优先覆盖。",
            "priority": "high",
            "related_reasoning_ids": [],
        },
        {
            "dimension_id": "TD-005",
            "dimension": "说明表驱动语义",
            "rationale": "触达用户类型说明表和充值金额区间属于表驱动规则，不能只保留枚举名。",
            "priority": "medium",
            "related_reasoning_ids": [],
        },
        {
            "dimension_id": "TD-006",
            "dimension": "后台配置到 C 端展示面投影",
            "rationale": "Phase 1 尚不改 testcase 逻辑，但 reasoning 已明确后台配置与首页/弹窗展示面存在跨层承接关系。",
            "priority": "medium",
            "related_reasoning_ids": ["IR-003"],
        },
    ]
    if ambiguities:
        dimensions.append(
            {
                "dimension_id": "TD-007",
                "dimension": "多页面拆分与未决项追踪",
                "rationale": "存在单张截图承载多个逻辑页面的情况，需要确保后续结构化与 coverage 不串页。",
                "priority": "medium",
                "related_reasoning_ids": [],
            }
        )
    return dimensions


def build_coverage_candidates(
    image_evidence: dict[str, Any],
    field_constraints: list[dict[str, Any]],
    data_source_rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    counter = 1
    seen: set[tuple[str, str, str]] = set()

    for image in image_evidence.get("images", []):
        page_name = str(image.get("page_name", "")).strip()
        for section in image.get("sections", []):
            section_name = str(section.get("section_name", "")).strip()
            key = ("section", page_name, section_name)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "candidate_id": f"COV-{counter:03d}",
                    "candidate_type": "section",
                    "title": f"{page_name}-{section_name}",
                    "scope": f"{page_name} / {section_name}",
                    "priority": "high" if section_name in {"添加弹窗", "排序弹窗"} else "medium",
                    "rationale": "板块级 reasoning 已具备字段、规则或说明表信息，适合作为后续 structured_prd 与 testcase 的第一承接对象。",
                    "suggested_test_types": ["功能", "边界", "数据校验"],
                    "source_reasoning_ids": [],
                }
            )
            counter += 1

    for constraint in field_constraints[:8]:
        candidates.append(
            {
                "candidate_id": f"COV-{counter:03d}",
                "candidate_type": "field_group",
                "title": f"{constraint['page_name']}-{constraint['display_name']}",
                "scope": f"{constraint['page_name']} / {constraint['section_name']} / {constraint['display_name']}",
                "priority": "high",
                "rationale": "字段级约束已经被 reasoning 显式展开，后续应优先投影到 structured_prd 的 fields/rules。",
                "suggested_test_types": ["功能", "边界"],
                "source_reasoning_ids": [constraint["constraint_id"]],
            }
        )
        counter += 1

    for rule in data_source_rules[:6]:
        candidates.append(
            {
                "candidate_id": f"COV-{counter:03d}",
                "candidate_type": "rule_cluster",
                "title": rule["title"],
                "scope": f"{rule.get('page_name', '')} / {rule.get('section_name', '')}",
                "priority": "high",
                "rationale": "数据来源、过滤、排序规则是最容易在压缩过程中丢失的 AI 推理结果，应单独保留 coverage 入口。",
                "suggested_test_types": ["数据校验", "流程验证"],
                "source_reasoning_ids": [rule["rule_id"]],
            }
        )
        counter += 1
    return candidates


def render_analysis_report(reasoning_pack: dict[str, Any]) -> str:
    lines = [
        "# Analysis Report",
        "",
        "## Requirement Summary",
        f"- 标题：`{reasoning_pack['requirement_summary']['title']}`",
        f"- 摘要：{reasoning_pack['requirement_summary']['summary_text']}",
        f"- 主要页面数：{len(reasoning_pack['requirement_summary']['primary_pages'])}",
        f"- 主要展示面数：{len(reasoning_pack['requirement_summary']['primary_user_surfaces'])}",
        "",
        "## Reasoning Snapshot",
        f"- explicit_rules：{len(reasoning_pack['explicit_rules'])}",
        f"- implicit_rules：{len(reasoning_pack['implicit_rules'])}",
        f"- field_constraints：{len(reasoning_pack['field_constraints'])}",
        f"- data_source_rules：{len(reasoning_pack['data_source_rules'])}",
        f"- business_risks：{len(reasoning_pack['business_risks'])}",
        f"- edge_cases：{len(reasoning_pack['edge_cases'])}",
        f"- ambiguities：{len(reasoning_pack['ambiguities'])}",
        f"- recommended_test_dimensions：{len(reasoning_pack['recommended_test_dimensions'])}",
        f"- coverage_candidates：{len(reasoning_pack['coverage_candidates'])}",
        "",
        "## Top Explicit Rules",
    ]
    for item in reasoning_pack["explicit_rules"][:8]:
        lines.append(f"- `{item['id']}` {item['statement']}")

    lines.extend(
        [
            "",
            "## Top Implicit Rules",
        ]
    )
    for item in reasoning_pack["implicit_rules"][:5]:
        lines.append(f"- `{item['id']}` {item['statement']}")

    lines.extend(
        [
            "",
            "## Key Risks",
        ]
    )
    for item in reasoning_pack["business_risks"]:
        lines.append(f"- `{item['risk_id']}` [{item['severity']}] {item['risk_statement']}")

    lines.extend(
        [
            "",
            "## Ambiguities",
        ]
    )
    if reasoning_pack["ambiguities"]:
        for item in reasoning_pack["ambiguities"]:
            lines.append(f"- `{item['ambiguity_id']}` {item['description']}")
    else:
        lines.append("- 当前未发现需要额外人工确认的开放性歧义。")

    lines.extend(
        [
            "",
            "## Recommended Test Dimensions",
        ]
    )
    for item in reasoning_pack["recommended_test_dimensions"]:
        lines.append(f"- `{item['dimension_id']}` {item['dimension']}：{item['rationale']}")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 requirement summary/source manifest 与可选 image evidence 生成 analysis_report 和 reasoning_pack"
    )
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--work-item-root", required=False, help="工作项根目录")
    parser.add_argument("--output-json", required=False, help="reasoning_pack.json 输出路径")
    parser.add_argument("--output-md", required=False, help="analysis_report.md 输出路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.work_item_root:
        work_item_root = Path(args.work_item_root).resolve()
    elif args.project_code and args.work_item_id:
        work_item_root = resolve_work_item_root(
            normalize_code(args.project_code),
            normalize_code(args.work_item_id),
        )
    else:
        raise SystemExit("必须提供 --work-item-root，或同时提供 --project-code 与 --work-item-id")

    manifest_path = work_item_root / "manifest.json"
    requirement_summary_path = work_item_root / "inputs" / "requirement_summary.md"
    source_manifest_path = work_item_root / "inputs" / "source_manifest.json"
    inputs_path = work_item_root / "inputs" / "received_screenshots.md"
    image_evidence_path = work_item_root / "image_evidence" / "image_evidence_inventory.json"
    analysis_dir = work_item_root / "analysis"
    output_json = Path(args.output_json).resolve() if args.output_json else analysis_dir / "reasoning_pack.json"
    output_md = Path(args.output_md).resolve() if args.output_md else analysis_dir / "analysis_report.md"

    if not manifest_path.exists():
        raise SystemExit(f"manifest 不存在: {manifest_path}")
    manifest = read_json(manifest_path)
    requirement_doc = parse_requirement_summary(requirement_summary_path)
    if source_manifest_path.exists():
        source_manifest = read_json(source_manifest_path)
        requirement_doc["source_notes"] = unique_strings(
            [
                f"{item.get('source_id', '')}: {item.get('location', '')} ({item.get('status', '')})"
                for item in source_manifest.get("sources", [])
                if isinstance(item, dict)
            ]
        )
    image_evidence = (
        read_json(image_evidence_path)
        if image_evidence_path.exists()
        else {"project_code": manifest.get("project_code", ""), "images": []}
    )
    screenshot_items = parse_received_screenshots(inputs_path)

    explicit_rules = build_explicit_rules(screenshot_items, image_evidence, requirement_doc)
    implicit_rules = build_implicit_rules(image_evidence, screenshot_items)
    field_constraints = build_field_constraints(image_evidence, screenshot_items)
    data_source_rules = build_data_source_rules(image_evidence, screenshot_items)
    business_risks = build_business_risks(field_constraints, data_source_rules, implicit_rules, screenshot_items)
    edge_cases = build_edge_cases(field_constraints)
    ambiguities = build_ambiguities(image_evidence, screenshot_items)
    recommended_test_dimensions = build_test_dimensions(field_constraints, data_source_rules, business_risks, ambiguities)
    coverage_candidates = build_coverage_candidates(image_evidence, field_constraints, data_source_rules)

    reasoning_pack = {
        "project_code": str(manifest.get("project_code", "")).strip(),
        "work_item_id": str(manifest.get("work_item_id", "")).strip(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_from": unique_strings(
            [
                display_path(path)
                for path in [
                    manifest_path,
                    requirement_summary_path,
                    source_manifest_path,
                    inputs_path,
                    image_evidence_path,
                ]
                if path.exists()
            ]
        ),
        "requirement_summary": build_requirement_summary(
            manifest,
            image_evidence,
            screenshot_items,
            requirement_doc,
        ),
        "explicit_rules": explicit_rules,
        "implicit_rules": implicit_rules,
        "field_constraints": field_constraints,
        "data_source_rules": data_source_rules,
        "business_risks": business_risks,
        "edge_cases": edge_cases,
        "ambiguities": ambiguities,
        "recommended_test_dimensions": recommended_test_dimensions,
        "coverage_candidates": coverage_candidates,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(reasoning_pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_analysis_report(reasoning_pack), encoding="utf-8")

    print(f"reasoning_pack: {output_json}")
    print(f"analysis_report: {output_md}")
    print(f"explicit_rules: {len(explicit_rules)}")
    print(f"implicit_rules: {len(implicit_rules)}")
    print(f"field_constraints: {len(field_constraints)}")
    print(f"data_source_rules: {len(data_source_rules)}")
    print(f"business_risks: {len(business_risks)}")
    print(f"edge_cases: {len(edge_cases)}")
    print(f"ambiguities: {len(ambiguities)}")
    print(f"recommended_test_dimensions: {len(recommended_test_dimensions)}")
    print(f"coverage_candidates: {len(coverage_candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
