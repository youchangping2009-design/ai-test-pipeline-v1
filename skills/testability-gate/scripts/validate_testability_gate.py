#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

CLASSIFICATIONS = {
    "product_behavior",
    "field_constraint",
    "linkage",
    "soft_prompt",
    "technical_background",
    "backend_job",
    "third_party_capability",
    "permission_scope",
    "platform_scope",
    "risk_hardening",
}
TESTABILITY = {
    "testable",
    "partially_testable",
    "not_directly_testable",
    "needs_confirmation",
    "risk_only",
    "out_of_scope",
}
DECISIONS = {
    "generate_acceptance_example",
    "generate_case_plan",
    "skip_case",
    "needs_confirmation",
    "risk_note_only",
    "out_of_scope",
}
CONFIDENCE = {"confirmed", "inferred", "unknown"}
PLACEHOLDER_PATTERNS = ("待补充", "TODO", "TEMPLATE", "示例", "example")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_rule_candidates(node: Any) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            rule_id = str(value.get("rule_id", "")).strip()
            rule_text = str(value.get("rule_text", "") or value.get("description", "")).strip()
            if rule_id and rule_text:
                rules.append({"rule_id": rule_id, "rule_text": rule_text})
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, str) and child.strip():
                    # String-only rules are not stable enough for mandatory gate coverage.
                    continue
                visit(child)

    visit(node)
    deduped: dict[str, dict[str, str]] = {}
    for item in rules:
        deduped.setdefault(item["rule_id"], item)
    return list(deduped.values())


def validate_gate(payload: dict[str, Any], structured_prd: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    items = payload.get("items")
    if not isinstance(items, list):
        return ["testability_gate.items 必须为数组"]
    if not items:
        errors.append("testability_gate.items 不能为空，strict/review 阶段不能使用空模板")

    seen_gate_ids: set[str] = set()
    source_rule_ids: set[str] = set()

    required = {
        "gate_id",
        "source_rule_id",
        "source_text",
        "classification",
        "testability",
        "decision",
        "reason",
        "confidence",
    }
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 条 gate 必须为对象")
            continue
        missing = [field for field in sorted(required) if not str(item.get(field, "")).strip()]
        if missing:
            errors.append(f"第 {index} 条 gate 缺少必填字段: {missing}")
            continue

        gate_id = str(item["gate_id"]).strip()
        source_rule_id = str(item["source_rule_id"]).strip()
        classification = str(item["classification"]).strip()
        testability = str(item["testability"]).strip()
        decision = str(item["decision"]).strip()
        confidence = str(item["confidence"]).strip()

        if gate_id in seen_gate_ids:
            errors.append(f"gate_id 重复: {gate_id}")
        seen_gate_ids.add(gate_id)
        source_rule_ids.add(source_rule_id)

        if classification not in CLASSIFICATIONS:
            errors.append(f"{gate_id} classification 非法: {classification}")
        if testability not in TESTABILITY:
            errors.append(f"{gate_id} testability 非法: {testability}")
        if decision not in DECISIONS:
            errors.append(f"{gate_id} decision 非法: {decision}")
        if confidence not in CONFIDENCE:
            errors.append(f"{gate_id} confidence 非法: {confidence}")
        if confidence == "inferred" and not str(item.get("inference_basis", "")).strip():
            errors.append(f"{gate_id} confidence=inferred 时必须填写 inference_basis")
        for field in ["source_rule_id", "source_text", "reason"]:
            text = str(item.get(field, "")).strip()
            if any(pattern.lower() in text.lower() for pattern in PLACEHOLDER_PATTERNS):
                errors.append(f"{gate_id} 字段 {field} 仍是模板/占位内容: {text}")

        if classification == "technical_background" and decision in {
            "generate_case_plan",
            "generate_acceptance_example",
        }:
            errors.append(f"{gate_id} technical_background 不允许进入正式验收/用例计划")
        if classification == "soft_prompt" and decision in {"generate_case_plan", "generate_acceptance_example"}:
            # soft_prompt can still be planned later as prompt_display, but not as a hard assertion gate.
            if testability == "testable":
                errors.append(f"{gate_id} soft_prompt 不应标记为 testable 强生成；请使用 partially_testable 或 risk_note_only")
        if testability == "risk_only" and decision not in {"risk_note_only", "skip_case"}:
            errors.append(f"{gate_id} risk_only 只能进入 risk_note_only/skip_case")
        if testability == "needs_confirmation" and decision != "needs_confirmation":
            errors.append(f"{gate_id} needs_confirmation 不允许直接生成 confirmed 强断言")
        if testability == "out_of_scope" and decision != "out_of_scope":
            errors.append(f"{gate_id} out_of_scope 不允许生成主用例")

    if structured_prd is not None:
        structured_rules = iter_rule_candidates(structured_prd)
        required_rule_ids = {
            item["rule_id"] for item in structured_rules if item["rule_id"].strip()
        }
        missing_rule_ids = sorted(required_rule_ids - source_rule_ids)
        if missing_rule_ids:
            preview = ", ".join(missing_rule_ids[:20])
            suffix = " ..." if len(missing_rule_ids) > 20 else ""
            errors.append(f"structured_prd 中存在未经过 testability_gate 处理的规则: {preview}{suffix}")

        expected_text_by_rule = {
            item["rule_id"]: item["rule_text"] for item in structured_rules
        }
        for item in items:
            if not isinstance(item, dict):
                continue
            source_rule_id = str(item.get("source_rule_id", "")).strip()
            if source_rule_id not in expected_text_by_rule:
                continue
            source_text = str(item.get("source_text", "")).strip()
            if source_text != expected_text_by_rule[source_rule_id]:
                errors.append(
                    f"{item.get('gate_id', source_rule_id)} source_text 与 structured_prd 规则 {source_rule_id} 不一致"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 testability_gate.json")
    parser.add_argument("--input", required=True, help="testability_gate.json 路径")
    parser.add_argument("--structured-prd", required=False, help="structured_prd.json 路径")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    structured_path = Path(args.structured_prd).resolve() if args.structured_prd else None

    try:
        payload = read_json(input_path)
        structured = read_json(structured_path) if structured_path and structured_path.exists() else None
    except Exception as exc:
        print(f"读取文件失败: {exc}", file=sys.stderr)
        return 1

    errors = validate_gate(payload, structured)
    if errors:
        print("❌ testability_gate 校验失败")
        print(f"输入文件: {input_path}")
        for error in errors:
            print(f"- {error}")
        print(f"共发现 {len(errors)} 个问题")
        return 1

    print("✅ testability_gate 校验通过")
    print(f"输入文件: {input_path}")
    print(f"gate_count: {len(payload.get('items', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
