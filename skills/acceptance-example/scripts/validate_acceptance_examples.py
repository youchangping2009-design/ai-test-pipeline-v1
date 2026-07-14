#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ORACLE_STRENGTH = {
    "hard_block",
    "soft_display",
    "display_only",
    "business_behavior",
    "backend_job",
    "linkage",
    "risk_only",
}
CONFIDENCE = {"confirmed", "inferred", "unknown"}
HARD_BLOCK_WORDS = re.compile(r"(保存失败|提交失败|阻止保存|不可保存|强拦截|不允许提交|禁止上传|强制拦截)")
PLACEHOLDER_PATTERNS = ("待补充", "TODO", "TEMPLATE", "示例", "example")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_gate(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    return {
        str(item.get("gate_id", "")).strip(): item
        for item in payload.get("items", [])
        if isinstance(item, dict) and str(item.get("gate_id", "")).strip()
    }


def validate_examples(payload: dict[str, Any], gates: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    examples = payload.get("examples")
    if not isinstance(examples, list):
        return ["acceptance_examples.examples 必须为数组"]
    if not examples:
        errors.append("acceptance_examples.examples 不能为空，M/L strict 阶段不能使用空模板")

    gate_to_examples: dict[str, int] = {}
    seen_ids: set[str] = set()
    for index, example in enumerate(examples, start=1):
        if not isinstance(example, dict):
            errors.append(f"第 {index} 条 acceptance example 必须为对象")
            continue
        required = [
            "example_id",
            "source_gate_ids",
            "title",
            "given",
            "when",
            "then",
            "verification_side",
            "oracle_strength",
            "confidence",
        ]
        missing = [field for field in required if example.get(field) in ("", None, [])]
        if missing:
            errors.append(f"第 {index} 条 acceptance example 缺少必填字段: {missing}")
            continue

        example_id = str(example["example_id"]).strip()
        title = str(example.get("title", "")).strip()
        if example_id in seen_ids:
            errors.append(f"example_id 重复: {example_id}")
        seen_ids.add(example_id)
        if any(pattern.lower() in title.lower() for pattern in PLACEHOLDER_PATTERNS):
            errors.append(f"{example_id} title 仍是模板/占位内容: {title}")

        oracle = str(example.get("oracle_strength", "")).strip()
        confidence = str(example.get("confidence", "")).strip()
        if oracle not in ORACLE_STRENGTH:
            errors.append(f"{example_id} oracle_strength 非法: {oracle}")
        if confidence not in CONFIDENCE:
            errors.append(f"{example_id} confidence 非法: {confidence}")
        if confidence == "inferred" and not str(example.get("inference_basis", "")).strip():
            errors.append(f"{example_id} confidence=inferred 时必须填写 inference_basis")

        for field in ["given", "when", "then"]:
            value = example.get(field)
            if not isinstance(value, list) or not any(str(item).strip() for item in value):
                errors.append(f"{example_id} 必须填写 Given/When/Then 中的 {field}")

        source_gate_ids = [str(item).strip() for item in example.get("source_gate_ids", []) if str(item).strip()]
        for gate_id in source_gate_ids:
            gate_to_examples[gate_id] = gate_to_examples.get(gate_id, 0) + 1
            gate = gates.get(gate_id)
            if not gate:
                errors.append(f"{example_id} source_gate_id 不存在于 testability_gate: {gate_id}")
                continue
            classification = str(gate.get("classification", "")).strip()
            decision = str(gate.get("decision", "")).strip()
            testability = str(gate.get("testability", "")).strip()
            if classification == "soft_prompt":
                then_text = " ".join(str(item) for item in example.get("then", []))
                if oracle == "hard_block" or HARD_BLOCK_WORDS.search(then_text):
                    errors.append(f"{example_id} 来源 {gate_id} 为 soft_prompt，不允许出现保存失败/强拦截类 then 断言")
            if classification == "technical_background":
                errors.append(f"{example_id} 来源 {gate_id} 为 technical_background，不允许生成 acceptance example")
            if decision in {"skip_case", "risk_note_only", "out_of_scope"}:
                errors.append(f"{example_id} 来源 {gate_id} decision={decision}，不允许生成主验收 acceptance example")
            if testability == "needs_confirmation" and confidence == "confirmed":
                errors.append(f"{example_id} 来源 {gate_id} 待确认，不允许写成 confirmed")

    for gate_id, gate in gates.items():
        if gate.get("decision") == "generate_acceptance_example" and not gate_to_examples.get(gate_id):
            errors.append(f"{gate_id} decision=generate_acceptance_example，但没有对应 acceptance example")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 acceptance_examples.json")
    parser.add_argument("--input", required=True, help="acceptance_examples.json 路径")
    parser.add_argument("--testability-gate", required=False, help="testability_gate.json 路径")
    args = parser.parse_args()

    try:
        payload = read_json(Path(args.input).resolve())
        gates = load_gate(Path(args.testability_gate).resolve() if args.testability_gate else None)
    except Exception as exc:
        print(f"读取文件失败: {exc}", file=sys.stderr)
        return 1

    errors = validate_examples(payload, gates)
    if errors:
        print("❌ acceptance_examples 校验失败")
        for error in errors:
            print(f"- {error}")
        return 1

    print("✅ acceptance_examples 校验通过")
    print(f"example_count: {len(payload.get('examples', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
