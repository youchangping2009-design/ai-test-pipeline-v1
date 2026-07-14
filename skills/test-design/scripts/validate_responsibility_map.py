#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PLACEHOLDER_PATTERNS = ("待补充", "TODO", "TEMPLATE", "示例", "example")
WRITE_SIDE_METHOD_WORDS = ("保存", "提交", "写入", "拦截", "校验")
DISPLAY_SIDE_WORDS = ("展示", "页面", "提示", "文案")
WRITE_SIDE_WORDS = ("写侧", "保存", "提交", "配置")
CONSUMER_SIDE_WORDS = ("C端", "消费", "链路", "领取")
API_SIDE_WORDS = ("API", "接口")
RISK_SIDE_WORDS = ("风险", "加固", "兜底")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_gate_source_rule_ids(testability_gate: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(testability_gate, dict):
        return {}
    items = testability_gate.get("items", [])
    if not isinstance(items, list):
        return {}
    result: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        gate_id = str(item.get("gate_id", "")).strip()
        source_rule_id = str(item.get("source_rule_id", "")).strip()
        if gate_id and source_rule_id:
            result[gate_id] = source_rule_id
    return result


def load_gate_by_source_rule_id(testability_gate: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(testability_gate, dict):
        return {}
    items = testability_gate.get("items", [])
    if not isinstance(items, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        source_rule_id = str(item.get("source_rule_id", "")).strip()
        if source_rule_id:
            result[source_rule_id] = item
    return result


def contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def validate_map(
    payload: dict[str, Any],
    case_plan: dict[str, Any] | None,
    testability_gate: dict[str, Any] | None,
) -> list[str]:
    errors: list[str] = []
    items = payload.get("responsibilities")
    if not isinstance(items, list):
        return ["verification_responsibility_map.responsibilities 必须为数组"]
    if not items:
        errors.append("verification_responsibility_map.responsibilities 不能为空，L strict 阶段不能使用空模板")

    gate_source_rule_by_id = load_gate_source_rule_ids(testability_gate)
    gate_by_source_rule_id = load_gate_by_source_rule_id(testability_gate)
    known_gate_source_rule_ids = set(gate_source_rule_by_id.values())
    source_ids_requiring_consumer: set[str] = set()
    seen_ids: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 条 responsibility 必须为对象")
            continue
        required = [
            "responsibility_id",
            "source_rule_id",
            "rule_text",
            "primary_verification_side",
            "primary_verification_method",
            "consumer_verification_required",
            "api_guard_required",
            "risk_note_required",
            "reason",
        ]
        missing = [field for field in required if field not in item or item.get(field) in ("", None)]
        if missing:
            errors.append(f"第 {index} 条 responsibility 缺少必填字段: {missing}")
            continue

        responsibility_id = str(item["responsibility_id"]).strip()
        if responsibility_id in seen_ids:
            errors.append(f"responsibility_id 重复: {responsibility_id}")
        seen_ids.add(responsibility_id)

        side = str(item.get("primary_verification_side", "")).strip()
        method = str(item.get("primary_verification_method", "")).strip()
        rule_text = str(item.get("rule_text", "")).strip()
        source_rule_id = str(item.get("source_rule_id", "")).strip()
        reason = str(item.get("reason", "")).strip()

        if gate_source_rule_by_id and source_rule_id not in known_gate_source_rule_ids:
            errors.append(f"{responsibility_id} source_rule_id 不存在于 testability_gate: {source_rule_id}")
        source_gate = gate_by_source_rule_id.get(source_rule_id, {})
        classification = str(source_gate.get("classification", "")).strip()
        testability = str(source_gate.get("testability", "")).strip()
        decision = str(source_gate.get("decision", "")).strip()

        for field_name, text in [
            ("rule_text", rule_text),
            ("primary_verification_side", side),
            ("primary_verification_method", method),
            ("reason", reason),
        ]:
            if any(pattern.lower() in text.lower() for pattern in PLACEHOLDER_PATTERNS):
                errors.append(f"{responsibility_id} 字段 {field_name} 仍是模板/占位内容: {text}")

        if any(word in rule_text for word in ["不可保存", "阻止保存", "保存失败", "必填"]) and "写侧" not in side:
            errors.append(f"{responsibility_id} hard_block/必填类规则优先应落在写侧")
        if any(word in method for word in WRITE_SIDE_METHOD_WORDS) and "写侧" not in side and "API" not in side.upper() and "接口" not in side:
            errors.append(f"{responsibility_id} 写入/保存类验证方法应明确落在写侧或接口兜底")
        if bool(item.get("api_guard_required")) and "接口" not in side and "API" not in side.upper():
            if "保存" in method:
                errors.append(f"{responsibility_id} api_guard 与 product_acceptance 需要分池，不应只写保存侧方法")
        if bool(item.get("consumer_verification_required")):
            source_ids_requiring_consumer.add(source_rule_id)
        if "平台" in rule_text and "不明确" in rule_text and bool(item.get("consumer_verification_required")):
            errors.append(f"{responsibility_id} 平台范围不明确时，不允许自动扩展多端用例")

        if classification == "soft_prompt":
            if not contains_any(side + method, DISPLAY_SIDE_WORDS):
                errors.append(f"{responsibility_id} 来源为 soft_prompt，应落在 B端页面展示/提示验证")
            if "写侧" in side or bool(item.get("api_guard_required")) or bool(item.get("risk_note_required")):
                errors.append(f"{responsibility_id} 来源为 soft_prompt，不应升级为写侧/API/风险责任")
            if bool(item.get("consumer_verification_required")):
                errors.append(f"{responsibility_id} 来源为 soft_prompt，不应要求 C端消费链路验证")
        if classification == "technical_background":
            errors.append(f"{responsibility_id} 来源为 technical_background，不应生成验证责任")
        if classification == "linkage":
            if not bool(item.get("consumer_verification_required")):
                errors.append(f"{responsibility_id} 来源为 linkage，必须判断并要求 C端消费链路验证")
            if not contains_any(side + method + rule_text, CONSUMER_SIDE_WORDS):
                errors.append(f"{responsibility_id} 来源为 linkage，责任侧/方法必须体现 C端消费链路")
        if classification == "risk_hardening" or testability == "risk_only" or decision == "risk_note_only":
            if not (bool(item.get("api_guard_required")) or bool(item.get("risk_note_required"))):
                errors.append(f"{responsibility_id} 风险/API类来源必须进入 api_guard 或 risk_note 责任")
            if not contains_any(side + method + reason, API_SIDE_WORDS + RISK_SIDE_WORDS):
                errors.append(f"{responsibility_id} 风险/API类来源的责任侧或方法必须体现 API/风险/兜底")
            if bool(item.get("consumer_verification_required")):
                errors.append(f"{responsibility_id} 风险/API类来源不应要求 C端主消费链路验证")

    if case_plan is not None:
        plans = case_plan.get("case_plans", []) if isinstance(case_plan, dict) else []
        referenced_responsibility_ids = {
            str(responsibility_id).strip()
            for plan in plans
            if isinstance(plan, dict)
            for responsibility_id in plan.get("source_responsibility_ids", []) or []
            if str(responsibility_id).strip()
        }
        known_responsibility_ids = {
            str(item.get("responsibility_id", "")).strip()
            for item in items
            if isinstance(item, dict) and str(item.get("responsibility_id", "")).strip()
        }
        for responsibility_id in sorted(referenced_responsibility_ids - known_responsibility_ids):
            errors.append(f"case_plan 引用了不存在的 responsibility_id: {responsibility_id}")
        responsibilities_by_id = {
            str(item.get("responsibility_id", "")).strip(): item
            for item in items
            if isinstance(item, dict) and str(item.get("responsibility_id", "")).strip()
        }
        for plan in plans:
            if not isinstance(plan, dict):
                continue
            plan_id = str(plan.get("case_plan_id", "")).strip() or "(unknown case_plan)"
            plan_gate_ids = [str(gate_id).strip() for gate_id in plan.get("source_gate_ids", []) or [] if str(gate_id).strip()]
            plan_source_rule_ids = {
                gate_source_rule_by_id.get(gate_id, "")
                for gate_id in plan_gate_ids
                if gate_source_rule_by_id.get(gate_id, "")
            }
            if not plan_source_rule_ids:
                continue
            for responsibility_id in plan.get("source_responsibility_ids", []) or []:
                responsibility = responsibilities_by_id.get(str(responsibility_id).strip())
                if not responsibility:
                    continue
                responsibility_source_rule_id = str(responsibility.get("source_rule_id", "")).strip()
                if responsibility_source_rule_id not in plan_source_rule_ids:
                    errors.append(
                        f"{plan_id} source_responsibility_id={responsibility_id} 与 source_gate_ids 对应规则不一致"
                    )

        linkage_source_ids = {
            gate_id
            for plan in plans
            if isinstance(plan, dict) and plan.get("case_type") == "linkage"
            for gate_id in plan.get("source_gate_ids", [])
        }
        linkage_responsibility_ids = {
            responsibility_id
            for plan in plans
            if isinstance(plan, dict) and plan.get("case_type") == "linkage"
            for responsibility_id in plan.get("source_responsibility_ids", []) or []
        }
        for source_rule_id in sorted(source_ids_requiring_consumer):
            # In P1 this is a lightweight guard: allow either direct source id or mapped gate id.
            matched_responsibilities = [
                str(item.get("responsibility_id", "")).strip()
                for item in items
                if isinstance(item, dict) and str(item.get("source_rule_id", "")).strip() == source_rule_id
            ]
            if (
                source_rule_id
                and source_rule_id not in linkage_source_ids
                and not (set(matched_responsibilities) & linkage_responsibility_ids)
            ):
                errors.append(
                    f"{source_rule_id} consumer_verification_required=true，但 case_plan 中未发现 linkage 类计划"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 verification_responsibility_map.json")
    parser.add_argument("--input", required=True, help="verification_responsibility_map.json 路径")
    parser.add_argument("--case-plan", required=False, help="case_plan.json 路径")
    parser.add_argument("--testability-gate", required=False, help="testability_gate.json 路径")
    args = parser.parse_args()

    try:
        payload = read_json(Path(args.input).resolve())
        case_plan = read_json(Path(args.case_plan).resolve()) if args.case_plan else None
        testability_gate = read_json(Path(args.testability_gate).resolve()) if args.testability_gate else None
    except Exception as exc:
        print(f"读取文件失败: {exc}", file=sys.stderr)
        return 1

    errors = validate_map(payload, case_plan, testability_gate)
    if errors:
        print("❌ verification_responsibility_map 校验失败")
        for error in errors:
            print(f"- {error}")
        return 1

    print("✅ verification_responsibility_map 校验通过")
    print(f"responsibility_count: {len(payload.get('responsibilities', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
