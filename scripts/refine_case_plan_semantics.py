#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from case_plan_semantics import (
    build_source_index,
    normalized_plan_semantics,
    rewrite_case_id_type,
    semantic_signature,
    source_descriptor,
    testcase_type,
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def join_items(value: Any) -> str:
    if isinstance(value, list):
        return "<br>".join(str(item) for item in value)
    return str(value or "")


def render_table(title: str, columns: list[str], rows: list[dict[str, Any]]) -> str:
    lines = [f"# {title}", "", "| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        values = [join_items(row.get(column, "")).replace("|", "\\|") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def attach_unmapped_main_coverage(
    plans: list[dict[str, Any]],
    coverage_matrix: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
) -> None:
    assigned = {
        str(coverage_id).strip()
        for plan in plans
        for coverage_id in plan.get("source_coverage_ids", []) or []
        if str(coverage_id).strip()
    }
    for entry in coverage_matrix.get("entries", []) or []:
        coverage_id = str(entry.get("coverage_id", "")).strip()
        if entry.get("emit_mode") != "main_testcase" or not coverage_id or coverage_id in assigned:
            continue
        descriptor = source_index.get(coverage_id, entry)
        label = str(descriptor.get("display_name") or entry.get("field_name", "")).strip()
        coverage_type = str(entry.get("coverage_type", "")).strip()
        expected_words = set(re.findall(r"[\u4e00-\u9fff]{2,}", " ".join(entry.get("planned_assertions", []) or [])))

        def score(plan: dict[str, Any]) -> int:
            value = 0
            for field, weight in (("page_name", 4), ("section_name", 4), ("module_name", 2), ("feature_name", 2)):
                if str(plan.get(field, "")).strip() == str(entry.get(field, "")).strip():
                    value += weight
            plan_text = f"{plan.get('title', '')} {plan.get('assertion', '')}"
            if label and label in plan_text:
                value += 6
            value += min(4, sum(1 for word in expected_words if word in plan_text))
            if coverage_type == "required" and any(token in plan_text for token in ("必填", "必传", "均已配置", "不得重复")):
                value += 5
            if coverage_type == "value_boundary" and any(token in plan_text for token in ("上限", "最大", "大于", "边界", "字符")):
                value += 4
            if coverage_type in {"conditional_visibility", "display_rule", "happy_path_combo"} and plan.get("case_type") in {"ui_display", "linkage"}:
                value += 3
            return value

        ranked = sorted(((score(plan), index, plan) for index, plan in enumerate(plans)), key=lambda item: (-item[0], item[1]))
        if not ranked or ranked[0][0] < 10:
            continue
        target = ranked[0][2]
        target["source_coverage_ids"] = dedupe(
            [str(item).strip() for item in target.get("source_coverage_ids", []) or []]
            + [coverage_id]
        )
        assigned.add(coverage_id)


def refine(
    structured_prd: dict[str, Any],
    coverage_matrix: dict[str, Any],
    gate_payload: dict[str, Any],
    example_payload: dict[str, Any],
    case_plan_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, int]]:
    source_index = build_source_index(structured_prd, coverage_matrix)
    gates = {str(item.get("gate_id", "")).strip(): item for item in gate_payload.get("items", [])}
    examples = {str(item.get("example_id", "")).strip(): item for item in example_payload.get("examples", [])}
    refined: list[dict[str, Any]] = []
    signatures: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    merged_count = 0

    for original in case_plan_payload.get("case_plans", []) or []:
        if not isinstance(original, dict) or not bool(original.get("should_generate_case")):
            continue
        plan = dict(original)
        gate_id = str((plan.get("source_gate_ids") or [""])[0]).strip()
        gate = gates.get(gate_id, {})
        descriptor = source_descriptor(plan, source_index)
        semantics = normalized_plan_semantics(plan, descriptor, gate)
        if descriptor:
            for field in ("page_name", "section_name", "module_name", "feature_name"):
                value = str(descriptor.get(field, "")).strip()
                if value:
                    plan[field] = value
        plan.update(
            {
                "title": semantics["title"],
                "verification_side": semantics["verification_side"],
                "case_type": semantics["case_type"],
                "assertion": semantics["assertion"],
            }
        )

        if semantics["case_type"] == "ui_display":
            for source_gate_id in plan.get("source_gate_ids", []) or []:
                source_gate = gates.get(str(source_gate_id).strip())
                if source_gate and source_gate.get("classification") == "field_constraint":
                    source_gate["classification"] = "product_behavior"
                    source_gate["reason"] = "规则描述的是读侧展示、隐藏或换行结果，不包含保存拦截语义。"
            for example_id in plan.get("source_example_ids", []) or []:
                example = examples.get(str(example_id).strip())
                if not example:
                    continue
                example["title"] = semantics["title"]
                example["given"] = ["对应后台配置或业务数据已准备完成。"]
                example["when"] = [f"用户进入[{plan.get('page_name', '')}]并查看{plan.get('section_name', '')}。"]
                example["then"] = [semantics["assertion"]]
                example["verification_side"] = "C端读侧"
                example["oracle_strength"] = "display_only"

        signature = semantic_signature(plan, semantics)
        existing = signatures.get(signature)
        if existing:
            merged_count += 1
            for field in ("source_gate_ids", "source_example_ids", "source_responsibility_ids", "source_rule_ids", "source_coverage_ids"):
                existing[field] = dedupe(
                    [str(item).strip() for item in existing.get(field, []) or []]
                    + [str(item).strip() for item in plan.get(field, []) or []]
                )
            continue
        plan["source_gate_ids"] = dedupe([str(item).strip() for item in plan.get("source_gate_ids", []) or []])
        plan["source_example_ids"] = dedupe([str(item).strip() for item in plan.get("source_example_ids", []) or []])
        plan["source_responsibility_ids"] = dedupe([str(item).strip() for item in plan.get("source_responsibility_ids", []) or []])
        plan["source_rule_ids"] = dedupe([str(item).strip() for item in plan.get("source_rule_ids", []) or []])
        if descriptor.get("coverage_id"):
            plan["source_coverage_ids"] = [str(descriptor["coverage_id"]).strip()]
        else:
            plan["source_coverage_ids"] = dedupe([str(item).strip() for item in plan.get("source_coverage_ids", []) or []])
        generated_id = str((plan.get("generated_testcase_ids") or [""])[0]).strip()
        plan["generated_testcase_ids"] = [
            rewrite_case_id_type(generated_id, testcase_type(semantics["case_type"], semantics["detail"]))
        ]
        signatures[signature] = plan
        refined.append(plan)

    case_plan_payload["generation_mode"] = "case_plan_direct"
    attach_unmapped_main_coverage(refined, coverage_matrix, source_index)
    case_plan_payload["case_plans"] = refined
    return gate_payload, example_payload, case_plan_payload, {
        "before": len(case_plan_payload.get("case_plans", [])) + merged_count,
        "after": len(refined),
        "merged": merged_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="规范化 Case Plan 语义并切换到直接生成模式")
    parser.add_argument("--structured-prd", required=True)
    parser.add_argument("--coverage-matrix", required=True)
    parser.add_argument("--testability-gate", required=True)
    parser.add_argument("--acceptance-examples", required=True)
    parser.add_argument("--case-plan", required=True)
    parser.add_argument("--gate-md", required=True)
    parser.add_argument("--examples-md", required=True)
    parser.add_argument("--case-plan-md", required=True)
    args = parser.parse_args()

    structured_prd = read_json(Path(args.structured_prd))
    coverage_matrix = read_json(Path(args.coverage_matrix))
    gate_payload = read_json(Path(args.testability_gate))
    example_payload = read_json(Path(args.acceptance_examples))
    case_plan_payload = read_json(Path(args.case_plan))
    gate_payload, example_payload, case_plan_payload, summary = refine(
        structured_prd, coverage_matrix, gate_payload, example_payload, case_plan_payload
    )
    write_json(Path(args.testability_gate), gate_payload)
    write_json(Path(args.acceptance_examples), example_payload)
    write_json(Path(args.case_plan), case_plan_payload)
    Path(args.gate_md).write_text(
        render_table("Testability Gate", ["gate_id", "source_rule_id", "classification", "testability", "decision", "confidence", "source_text", "reason"], gate_payload.get("items", [])),
        encoding="utf-8",
    )
    Path(args.examples_md).write_text(
        render_table("Acceptance Examples", ["example_id", "source_gate_ids", "title", "given", "when", "then", "verification_side", "oracle_strength", "confidence", "inference_basis"], example_payload.get("examples", [])),
        encoding="utf-8",
    )
    Path(args.case_plan_md).write_text(
        render_table("Case Plan", ["case_plan_id", "source_gate_ids", "source_example_ids", "source_responsibility_ids", "source_coverage_ids", "generated_testcase_ids", "page_name", "section_name", "module_name", "feature_name", "title", "verification_side", "case_type", "priority", "assertion", "validation_path", "should_generate_case"], case_plan_payload.get("case_plans", [])),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
