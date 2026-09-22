#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.review_and_score_testcases import infer_fidelity_target
from scripts.review_and_score_testcases import load_testcase_rows
from scripts.review_and_score_testcases import locate_terms
from scripts.review_and_score_testcases import requirement_satisfied


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_coverage_ids(row: dict[str, str]) -> list[str]:
    return re.findall(r"来源coverage：([A-Z0-9-]+)", row.get("备注", ""))


def parse_testcase_rows(path: Path) -> list[dict[str, str]]:
    return load_testcase_rows(path)


def build_testcase_index(rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], dict[str, list[dict[str, str]]]]:
    testcase_by_id: dict[str, dict[str, str]] = {}
    testcase_by_coverage: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        testcase_id = row.get("用例编号", "").strip()
        if testcase_id:
            testcase_by_id[testcase_id] = row
        for coverage_id in extract_coverage_ids(row):
            testcase_by_coverage.setdefault(coverage_id, []).append(row)
    return testcase_by_id, testcase_by_coverage


def build_evidence_feature_index(evidence: dict[str, Any]) -> dict[tuple[str, str], list[str]]:
    index: dict[tuple[str, str], list[str]] = {}
    for item in evidence.get("evidence_items", []):
        if not isinstance(item, dict):
            continue
        evidence_id = str(item.get("evidence_id", "")).strip()
        if not evidence_id:
            continue
        for target in item.get("structured_targets", []):
            if not isinstance(target, dict):
                continue
            module_name = str(target.get("module_name", "")).strip()
            feature_name = str(target.get("feature_name", "")).strip()
            if module_name and feature_name:
                key = (module_name, feature_name)
                index.setdefault(key, [])
                if evidence_id not in index[key]:
                    index[key].append(evidence_id)
    return index


def infer_rule_id(entry: dict[str, Any]) -> str:
    rule_name = str(entry.get("rule_name", "")).strip()
    for ref in entry.get("structured_refs", []):
        match = re.search(
            r"(?:^|\.)explicit_rules\.([A-Za-z0-9_-]+)(?:$|[.\[])",
            str(ref),
        )
        if match:
            return match.group(1)
    if re.fullmatch(r"[A-Z][A-Z0-9_-]*\d+", rule_name):
        return rule_name
    module_name = str(entry.get("module_name", "")).strip()
    feature_name = str(entry.get("feature_name", "")).strip()
    field_name = str(entry.get("field_name", "")).strip()
    coverage_type = str(entry.get("coverage_type", "")).strip()
    fallback = "::".join(part for part in [module_name, feature_name, field_name, coverage_type] if part)
    return fallback or f"RULE::{entry.get('coverage_id', '')}"


def infer_structured_targets(entry: dict[str, Any]) -> list[dict[str, str]]:
    module_name = str(entry.get("module_name", "")).strip()
    feature_name = str(entry.get("feature_name", "")).strip()
    field_name = str(entry.get("field_name", "")).strip()
    if field_name:
        return [
            {
                "target_type": "field_definition",
                "module_name": module_name,
                "feature_name": feature_name,
                "field_name": field_name,
                "target_name": str(entry.get("title", "")).strip(),
            }
        ]
    if feature_name:
        return [
            {
                "target_type": "feature",
                "module_name": module_name,
                "feature_name": feature_name,
                "field_name": "",
                "target_name": str(entry.get("title", "")).strip(),
            }
        ]
    return []


def fidelity_exact_terms(entry: dict[str, Any]) -> list[str]:
    candidates = [str(entry.get("title", "")).strip()]
    candidates.extend(str(item).strip() for item in entry.get("planned_assertions", []))
    return [candidate for candidate in candidates if candidate]


def infer_fidelity_status(entry: dict[str, Any], row: dict[str, str] | None) -> str:
    target = infer_fidelity_target(entry)
    if target is None:
        return "not_applicable"
    if row is None:
        return "missing"
    locations = locate_terms(row, target["terms"])
    if not requirement_satisfied(target["required_location"], locations):
        return "missing"

    title = row.get("用例标题", "")
    steps = row.get("测试步骤", "")
    expected = row.get("预期结果", "")
    exact_terms = fidelity_exact_terms(entry)
    if any(term and term in f"{title} {steps} {expected}" for term in exact_terms):
        return "kept_exact_phrase"
    return "kept_equivalent_phrase"


def compute_false_traceability_rate(records: list[dict[str, Any]], testcase_ids: set[str], coverage_ids: set[str]) -> tuple[int, float]:
    invalid = 0
    for record in records:
        if not record.get("rule_id"):
            invalid += 1
            continue
        if record.get("coverage_id") not in coverage_ids:
            invalid += 1
            continue
        testcase_id = str(record.get("testcase_id", "")).strip()
        if not testcase_id or testcase_id not in testcase_ids:
            invalid += 1
    total = len(records)
    rate = round((invalid / total), 4) if total else 0.0
    return invalid, rate


def build_traceability(coverage_matrix: dict[str, Any], evidence: dict[str, Any], testcase_rows: list[dict[str, str]]) -> dict[str, Any]:
    testcase_by_id, testcase_by_coverage = build_testcase_index(testcase_rows)
    evidence_by_feature = build_evidence_feature_index(evidence)
    records: list[dict[str, Any]] = []
    next_number = 1

    for entry in coverage_matrix.get("entries", []):
        if str(entry.get("emit_mode", "")).strip() != "main_testcase":
            continue
        coverage_id = str(entry.get("coverage_id", "")).strip()
        matched_rows = testcase_by_coverage.get(coverage_id, [])
        if not matched_rows:
            matched_rows = [None]
        for row in matched_rows:
            module_name = str(entry.get("module_name", "")).strip()
            feature_name = str(entry.get("feature_name", "")).strip()
            record = {
                "record_id": f"CFT-{next_number:04d}",
                "rule_id": infer_rule_id(entry),
                "coverage_id": coverage_id,
                "testcase_id": row.get("用例编号", "").strip() if row else "",
                "testcase_title": row.get("用例标题", "").strip() if row else "",
                "source_origin": str(entry.get("source_origin", "")).strip(),
                "coverage_level": str(entry.get("coverage_level", "")).strip(),
                "emit_mode": str(entry.get("emit_mode", "")).strip(),
                "fidelity_status": infer_fidelity_status(entry, row),
                "evidence_ids": evidence_by_feature.get((module_name, feature_name), []),
                "reasoning_refs": [str(item).strip() for item in entry.get("reasoning_refs", []) if str(item).strip()],
                "structured_targets": infer_structured_targets(entry),
            }
            records.append(record)
            next_number += 1

    testcase_ids = {testcase_id for testcase_id in testcase_by_id}
    coverage_ids = {
        str(entry.get("coverage_id", "")).strip()
        for entry in coverage_matrix.get("entries", [])
        if str(entry.get("coverage_id", "")).strip()
    }
    invalid_record_count, false_traceability_rate = compute_false_traceability_rate(records, testcase_ids, coverage_ids)
    return {
        "project_code": coverage_matrix.get("project_code", ""),
        "work_item_id": coverage_matrix.get("work_item_id", ""),
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "generated_from": [
            "coverage/coverage_matrix.json",
            "evidence/evidence_inventory.json",
            "testcases/testcases_main.md",
        ],
        "summary": {
            "record_count": len(records),
            "invalid_record_count": invalid_record_count,
            "false_traceability_rate": false_traceability_rate,
        },
        "records": records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 coverage-first traceability（并行产物）")
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--coverage-matrix", required=False, help="coverage_matrix.json 路径")
    parser.add_argument("--evidence", required=False, help="evidence_inventory.json 路径")
    parser.add_argument("--testcases", required=False, help="testcases_main.md 或 testcases.md 路径")
    parser.add_argument("--output", required=False, help="coverage_first_traceability.json 输出路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.project_code and args.work_item_id:
        root = resolve_work_item_root(normalize_code(args.project_code), normalize_code(args.work_item_id))
        coverage_matrix_path = Path(args.coverage_matrix).resolve() if args.coverage_matrix else root / "coverage" / "coverage_matrix.json"
        evidence_path = Path(args.evidence).resolve() if args.evidence else root / "evidence" / "evidence_inventory.json"
        testcase_path = (
            Path(args.testcases).resolve()
            if args.testcases
            else (root / "testcases" / "testcases_main.md" if (root / "testcases" / "testcases_main.md").exists() else root / "testcases" / "testcases.md")
        )
        output_path = Path(args.output).resolve() if args.output else root / "traceability" / "coverage_first_traceability.json"
    else:
        if not (args.coverage_matrix and args.evidence and args.testcases and args.output):
            raise SystemExit("必须提供 --project-code + --work-item-id，或显式提供 --coverage-matrix --evidence --testcases --output")
        coverage_matrix_path = Path(args.coverage_matrix).resolve()
        evidence_path = Path(args.evidence).resolve()
        testcase_path = Path(args.testcases).resolve()
        output_path = Path(args.output).resolve()

    coverage_matrix = read_json(coverage_matrix_path)
    evidence = read_json(evidence_path)
    testcase_rows = parse_testcase_rows(testcase_path)
    payload = build_traceability(coverage_matrix, evidence, testcase_rows)
    write_json(output_path, payload)
    print(f"coverage_first_traceability: {output_path}")
    print(f"records: {payload['summary']['record_count']}")
    print(f"false_traceability_rate: {payload['summary']['false_traceability_rate']}")
    print(f"invalid_record_count: {payload['summary']['invalid_record_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
