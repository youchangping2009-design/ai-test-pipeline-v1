#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.testcase_markdown_utils import parse_testcase_document

CASE_TYPES = {
    "field_constraint",
    "save_block",
    "prompt_display",
    "data_persistence",
    "linkage",
    "ui_display",
    "backend_job",
    "permission_scope",
    "risk_hardening",
}
VALIDATION_PATHS = {
    "product_acceptance",
    "api_guard",
    "security_hardening",
    "risk_note",
    "out_of_scope",
}
PRIORITIES = {"P0", "P1", "P2", "P3"}
GENERIC_TITLE_PATTERNS = [
    "字段矩阵完整性",
    "字段条件联动",
    "页面配置正确",
    "需求目标包含",
    "配置完整性检查",
]
CASE_PLAN_MARKERS = [
    re.compile(r"来源\s*CasePlan[:：]\s*(CP-[0-9]{3,})"),
    re.compile(r"来源\s*计划\s*ID[:：]\s*(CP-[0-9]{3,})"),
    re.compile(r"来源计划ID[:：]\s*(CP-[0-9]{3,})"),
    re.compile(r"case_plan_id\s*=\s*(CP-[0-9]{3,})"),
    re.compile(r"case_plan[:：]\s*(CP-[0-9]{3,})", re.IGNORECASE),
]
PLACEHOLDER_PATTERNS = ("待补充", "TODO", "TEMPLATE", "示例", "example")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_testability_gate(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return {
        str(item.get("gate_id", "")).strip(): item
        for item in items
        if isinstance(item, dict) and str(item.get("gate_id", "")).strip()
    }


def load_acceptance_examples(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    examples = payload.get("examples", []) if isinstance(payload, dict) else []
    return {
        str(item.get("example_id", "")).strip(): item
        for item in examples
        if isinstance(item, dict) and str(item.get("example_id", "")).strip()
    }


def load_responsibility_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    responsibilities = payload.get("responsibilities", []) if isinstance(payload, dict) else []
    return {
        str(item.get("responsibility_id", "")).strip(): item
        for item in responsibilities
        if isinstance(item, dict) and str(item.get("responsibility_id", "")).strip()
    }


def extract_case_plan_ids_from_remark(remark: str) -> set[str]:
    result: set[str] = set()
    for pattern in CASE_PLAN_MARKERS:
        result.update(match.group(1) for match in pattern.finditer(remark or ""))
    return result


def validate_case_plan(
    payload: dict[str, Any],
    testability_gate: dict[str, dict[str, Any]],
    acceptance_examples: dict[str, dict[str, Any]],
    responsibility_map: dict[str, dict[str, Any]],
    testcase_path: Path | None,
    require_examples: bool = False,
    require_responsibilities: bool = False,
) -> list[str]:
    errors: list[str] = []
    plans = payload.get("case_plans")
    if not isinstance(plans, list):
        return ["case_plan.case_plans 必须为数组"]
    if not plans:
        errors.append("case_plan.case_plans 不能为空，strict/review 阶段不能使用空模板")

    seen_ids: set[str] = set()
    generated_case_to_plan: dict[str, str] = {}
    active_plan_ids: set[str] = set()
    referenced_active_plan_ids: set[str] = set()
    direct_mode = payload.get("generation_mode") == "case_plan_direct"
    semantic_signatures: dict[tuple[str, str, str, str], str] = {}

    required = {
        "case_plan_id",
        "source_gate_ids",
        "title",
        "verification_side",
        "case_type",
        "priority",
        "assertion",
        "validation_path",
        "should_generate_case",
    }
    for index, plan in enumerate(plans, start=1):
        if not isinstance(plan, dict):
            errors.append(f"第 {index} 条 case_plan 必须为对象")
            continue
        missing = [field for field in sorted(required) if field not in plan or plan.get(field) in ("", None, [])]
        if missing:
            errors.append(f"第 {index} 条 case_plan 缺少必填字段: {missing}")
            continue

        plan_id = str(plan["case_plan_id"]).strip()
        source_gate_ids = [str(item).strip() for item in plan.get("source_gate_ids", []) if str(item).strip()]
        source_example_ids = [str(item).strip() for item in plan.get("source_example_ids", []) if str(item).strip()]
        source_responsibility_ids = [
            str(item).strip() for item in plan.get("source_responsibility_ids", []) if str(item).strip()
        ]
        source_coverage_ids = [
            str(item).strip()
            for item in (
                [plan.get("source_coverage_id")]
                + list(plan.get("source_coverage_ids", []) or [])
            )
            if str(item or "").strip()
        ]
        generated_testcase_ids = [
            str(item).strip()
            for item in plan.get("generated_testcase_ids", []) or []
            if str(item).strip()
        ]
        title = str(plan.get("title", "")).strip()
        case_type = str(plan.get("case_type", "")).strip()
        priority = str(plan.get("priority", "")).strip()
        assertion = str(plan.get("assertion", "")).strip()
        validation_path = str(plan.get("validation_path", "")).strip()
        should_generate = bool(plan.get("should_generate_case"))

        if plan_id in seen_ids:
            errors.append(f"case_plan_id 重复: {plan_id}")
        seen_ids.add(plan_id)
        if should_generate:
            active_plan_ids.add(plan_id)

        if not source_gate_ids:
            errors.append(f"{plan_id} 必须至少有一个 source_gate_ids")
        if require_examples and should_generate and not source_example_ids:
            errors.append(f"{plan_id} 在 M/L strict 下必须填写 source_example_ids")
        if require_responsibilities and should_generate and not source_responsibility_ids:
            errors.append(f"{plan_id} 在 L strict 下必须填写 source_responsibility_ids")
        if should_generate and not source_coverage_ids and not generated_testcase_ids:
            errors.append(
                f"{plan_id} 必须通过 source_coverage_ids 或 generated_testcase_ids 提供可执行生成映射"
            )
        if direct_mode and should_generate and len(generated_testcase_ids) != 1:
            errors.append(f"{plan_id} 在 case_plan_direct 模式下必须且只能映射一个 generated_testcase_id")
        if case_type not in CASE_TYPES:
            errors.append(f"{plan_id} case_type 非法: {case_type}")
        if priority not in PRIORITIES:
            errors.append(f"{plan_id} priority 非法: {priority}")
        if validation_path not in VALIDATION_PATHS:
            errors.append(f"{plan_id} validation_path 非法: {validation_path}")
        if not assertion:
            errors.append(f"{plan_id} 必须填写 assertion")
        if any(pattern in title for pattern in GENERIC_TITLE_PATTERNS):
            errors.append(f"{plan_id} 用例计划标题过于泛化: {title}")
        if direct_mode and re.search(r"[a-z][a-z0-9_]*\s*;\s*(?:value|data_source)_constraint", f"{title} {assertion}"):
            errors.append(f"{plan_id} 在 case_plan_direct 模式下仍暴露机器规则表达: {title}")
        if direct_mode and case_type == "save_block" and any(
            signal in title for signal in ("展示", "隐藏", "换行", "可见")
        ) and not any(signal in title for signal in ("必填", "必传", "上限", "最大", "不可保存", "不能保存")):
            errors.append(f"{plan_id} 展示类规则不得生成 save_block: {title}")
        if direct_mode and "C端" in str(plan.get("page_name", "")) and "B端写侧" == str(plan.get("verification_side", "")).strip():
            errors.append(f"{plan_id} C端页面不得仅标记为 B端写侧")
        if direct_mode and should_generate:
            signature = (
                str(plan.get("page_name", "")).strip(),
                str(plan.get("section_name", "")).strip(),
                case_type,
                re.sub(r"[\s：:，,。；;（）()]", "", title),
            )
            previous_plan = semantic_signatures.get(signature)
            if previous_plan:
                errors.append(f"{plan_id} 与 {previous_plan} 为同页面同板块同语义重复计划")
            semantic_signatures[signature] = plan_id
        for field_name, text in [
            ("title", title),
            ("assertion", assertion),
            ("verification_side", str(plan.get("verification_side", "")).strip()),
        ]:
            if any(pattern.lower() in text.lower() for pattern in PLACEHOLDER_PATTERNS):
                errors.append(f"{plan_id} 字段 {field_name} 仍是模板/占位内容: {text}")
        if validation_path in {"risk_note", "api_guard", "security_hardening"} and should_generate:
            errors.append(f"{plan_id} validation_path={validation_path} 不允许生成 product_acceptance 主用例")

        example_gate_ids: set[str] = set()
        for example_id in source_example_ids:
            example = acceptance_examples.get(example_id)
            if not example:
                if require_examples or acceptance_examples:
                    errors.append(f"{plan_id} source_example_id 不存在于 acceptance_examples: {example_id}")
                continue
            example_gate_ids.update(
                str(gate_id).strip()
                for gate_id in example.get("source_gate_ids", [])
                if str(gate_id).strip()
            )
            oracle = str(example.get("oracle_strength", "")).strip()
            if oracle == "soft_display" and case_type not in {"prompt_display", "ui_display"}:
                errors.append(f"{plan_id} 来源 {example_id} 为 soft_display，只能生成 prompt_display/ui_display 计划")
            if oracle == "hard_block":
                if case_type not in {"save_block", "field_constraint"}:
                    errors.append(f"{plan_id} 来源 {example_id} 为 hard_block，case_type 应为 save_block/field_constraint")
                if validation_path != "product_acceptance":
                    errors.append(f"{plan_id} 来源 {example_id} 为 hard_block，validation_path 必须为 product_acceptance")
        if source_example_ids and example_gate_ids and not (set(source_gate_ids) & example_gate_ids):
            errors.append(f"{plan_id} source_gate_ids 与 source_example_ids 对应 gate 完全不相关")

        for responsibility_id in source_responsibility_ids:
            responsibility = responsibility_map.get(responsibility_id)
            if not responsibility:
                if require_responsibilities or responsibility_map:
                    errors.append(f"{plan_id} source_responsibility_id 不存在于 verification_responsibility_map: {responsibility_id}")
                continue
            responsibility_source_rule_id = str(responsibility.get("source_rule_id", "")).strip()
            gate_source_rule_ids = {
                str(testability_gate.get(gate_id, {}).get("source_rule_id", "")).strip()
                for gate_id in source_gate_ids
                if testability_gate.get(gate_id)
            }
            if gate_source_rule_ids and responsibility_source_rule_id not in gate_source_rule_ids:
                errors.append(f"{plan_id} 来源 {responsibility_id} 与 source_gate_ids 对应规则不一致")
            primary_side = str(responsibility.get("primary_verification_side", "")).strip()
            if case_type == "save_block" and "写侧" not in primary_side:
                errors.append(f"{plan_id} 为 save_block，但来源 {responsibility_id} 责任未落到写侧")
            if bool(responsibility.get("risk_note_required")) and validation_path == "product_acceptance":
                errors.append(f"{plan_id} 来源 {responsibility_id} 标记 risk_note_required，不应混入 product_acceptance 主用例")
            if bool(responsibility.get("api_guard_required")) and validation_path == "product_acceptance" and case_type == "risk_hardening":
                errors.append(f"{plan_id} 来源 {responsibility_id} 为 api_guard/risk_hardening，应与主验收分池")

        for gate_id in source_gate_ids:
            gate = testability_gate.get(gate_id)
            if not gate:
                continue
            classification = str(gate.get("classification", "")).strip()
            testability = str(gate.get("testability", "")).strip()
            decision = str(gate.get("decision", "")).strip()
            if classification == "soft_prompt" and case_type not in {"prompt_display", "ui_display"}:
                errors.append(f"{plan_id} 来源 {gate_id} 为 soft_prompt，只能生成 prompt_display/ui_display 计划")
            if classification == "technical_background" and should_generate:
                errors.append(f"{plan_id} 来源 {gate_id} 为 technical_background，不能生成正式 case_plan")
            if testability == "risk_only" and validation_path != "risk_note":
                errors.append(f"{plan_id} 来源 {gate_id} 为 risk_only，只能进入 risk_note")
            if testability == "out_of_scope" and validation_path != "out_of_scope":
                errors.append(f"{plan_id} 来源 {gate_id} 为 out_of_scope，只能进入 out_of_scope")
            if testability == "needs_confirmation" and decision == "needs_confirmation" and should_generate:
                errors.append(f"{plan_id} 来源 {gate_id} 待确认，不能直接生成正式用例")

        for case_id in plan.get("generated_testcase_ids", []) or []:
            case_id_text = str(case_id).strip()
            if not case_id_text:
                continue
            previous = generated_case_to_plan.get(case_id_text)
            if previous and previous != plan_id:
                errors.append(f"testcase {case_id_text} 同时映射到多个 case_plan: {previous}, {plan_id}")
            generated_case_to_plan[case_id_text] = plan_id

    if testcase_path is not None and testcase_path.exists():
        try:
            parsed = parse_testcase_document(testcase_path.read_text(encoding="utf-8"), strict=True)
        except Exception as exc:
            errors.append(f"testcases 解析失败: {exc}")
            parsed = {"rows": []}
        rows = parsed.get("rows", [])
        if not rows:
            errors.append("testcases_main.md 必须包含真实用例，strict 阶段不能使用空模板")
        for row_index, row in enumerate(rows, start=1):
            case_id = str(row.get("用例编号", "")).strip()
            remark = str(row.get("备注", "")).strip()
            marker_ids = extract_case_plan_ids_from_remark(remark)
            mapped_id = generated_case_to_plan.get(case_id)
            valid_markers = marker_ids & seen_ids
            if not marker_ids:
                errors.append(f"第 {row_index} 条 testcase 未显式引用 case_plan_id: {case_id}")
            if not valid_markers:
                errors.append(f"第 {row_index} 条 testcase 无法追溯到已存在 case_plan: {case_id}")
            for marker_id in marker_ids:
                if marker_id not in seen_ids:
                    errors.append(f"第 {row_index} 条 testcase 引用了不存在的 case_plan: {marker_id}")
            referenced_plan_ids = valid_markers or ({mapped_id} if mapped_id else set())
            referenced_active_plan_ids.update(referenced_plan_ids & active_plan_ids)
            for plan_id in referenced_plan_ids:
                if plan_id not in active_plan_ids:
                    errors.append(f"第 {row_index} 条 testcase 映射到 should_generate_case=false 的 case_plan: {plan_id}")
                plan = next((item for item in plans if isinstance(item, dict) and item.get("case_plan_id") == plan_id), None)
                if not plan:
                    continue
                plan_validation_path = str(plan.get("validation_path", "")).strip()
                plan_case_type = str(plan.get("case_type", "")).strip()
                if plan_validation_path in {"risk_note", "api_guard", "security_hardening"}:
                    errors.append(f"第 {row_index} 条 testcase 引用了非主验收 case_plan: {plan_id} ({plan_validation_path})")
                for gate_id in plan.get("source_gate_ids", []) or []:
                    gate = testability_gate.get(str(gate_id).strip())
                    if not gate:
                        continue
                    classification = str(gate.get("classification", "")).strip()
                    if classification == "soft_prompt" and plan_case_type not in {"prompt_display", "ui_display"}:
                        errors.append(f"第 {row_index} 条 testcase 来源 soft_prompt 但 case_type 非展示类: {plan_id}")
                    if classification == "technical_background":
                        errors.append(f"第 {row_index} 条 testcase 来源 technical_background，不允许生成正式用例: {plan_id}")

        if direct_mode:
            missing_plan_ids = sorted(active_plan_ids - referenced_active_plan_ids)
            if missing_plan_ids:
                errors.append(f"case_plan_direct 存在未生成正式 testcase 的计划: {missing_plan_ids}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 case_plan.json 及 testcase 到 case_plan 的追溯")
    parser.add_argument("--input", required=True, help="case_plan.json 路径")
    parser.add_argument("--testability-gate", required=False, help="testability_gate.json 路径")
    parser.add_argument("--acceptance-examples", required=False, help="acceptance_examples.json 路径")
    parser.add_argument("--responsibility-map", required=False, help="verification_responsibility_map.json 路径")
    parser.add_argument("--testcases", required=False, help="testcases_main.md 路径")
    parser.add_argument("--require-examples", action="store_true", help="要求 case_plan.source_example_ids 非空并可追溯")
    parser.add_argument("--require-responsibilities", action="store_true", help="要求 case_plan.source_responsibility_ids 非空并可追溯")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    gate_path = Path(args.testability_gate).resolve() if args.testability_gate else None
    examples_path = Path(args.acceptance_examples).resolve() if args.acceptance_examples else None
    responsibility_map_path = Path(args.responsibility_map).resolve() if args.responsibility_map else None
    testcase_path = Path(args.testcases).resolve() if args.testcases else None

    try:
        payload = read_json(input_path)
        gates = load_testability_gate(gate_path)
        examples = load_acceptance_examples(examples_path)
        responsibilities = load_responsibility_map(responsibility_map_path)
    except Exception as exc:
        print(f"读取文件失败: {exc}", file=sys.stderr)
        return 1

    errors = validate_case_plan(
        payload,
        gates,
        examples,
        responsibilities,
        testcase_path,
        require_examples=args.require_examples,
        require_responsibilities=args.require_responsibilities,
    )
    if errors:
        print("❌ case_plan 校验失败")
        print(f"输入文件: {input_path}")
        for error in errors:
            print(f"- {error}")
        print(f"共发现 {len(errors)} 个问题")
        return 1

    print("✅ case_plan 校验通过")
    print(f"输入文件: {input_path}")
    print(f"case_plan_count: {len(payload.get('case_plans', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
