#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_traceability_assets import build_structured_index
from scripts.validate_traceability_assets import parse_testcase_ids
from scripts.validate_traceability_assets import validate_target_exists



def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def target_signature(target: dict[str, Any]) -> str:
    ordered = {
        "target_type": str(target.get("target_type", "")).strip(),
        "module_name": str(target.get("module_name", "")).strip(),
        "feature_name": str(target.get("feature_name", "")).strip(),
        "field_name": str(target.get("field_name", "")).strip(),
        "attribute_name": str(target.get("attribute_name", "")).strip(),
        "target_name": str(target.get("target_name", "")).strip(),
    }
    return json.dumps(ordered, ensure_ascii=False, sort_keys=True)


def record_signature(record: dict[str, Any]) -> tuple[str, tuple[str, ...], tuple[str, ...], str, str]:
    testcase_ids = tuple(dedupe_preserve_order([str(item).strip() for item in record.get("testcase_ids", [])]))
    structured_targets = tuple(
        target_signature(target)
        for target in record.get("structured_targets", [])
        if isinstance(target, dict)
    )
    return (
        str(record.get("evidence_id", "")).strip(),
        testcase_ids,
        structured_targets,
        str(record.get("implementation_binding", "")).strip(),
        str(record.get("recommended_cr_stage", "")).strip(),
    )


def slim_traceability(traceability: dict[str, Any], structured_prd: dict[str, Any], testcase_ids: set[str]) -> tuple[dict[str, Any], dict[str, int]]:
    structured_index = build_structured_index(structured_prd)
    original_records = list(traceability.get("records", []))
    kept_records: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, tuple[str, ...], tuple[str, ...], str, str]] = set()

    dropped_missing_testcase = 0
    dropped_invalid_target = 0
    dropped_duplicate = 0
    trimmed_targets = 0

    for record in original_records:
        if not isinstance(record, dict):
            continue
        valid_testcase_ids = [
            testcase_id
            for testcase_id in dedupe_preserve_order([str(item).strip() for item in record.get("testcase_ids", [])])
            if testcase_id in testcase_ids
        ]
        if not valid_testcase_ids:
            dropped_missing_testcase += 1
            continue

        valid_targets: list[dict[str, Any]] = []
        for target in record.get("structured_targets", []):
            if not isinstance(target, dict):
                continue
            if validate_target_exists(target, structured_index) is None:
                valid_targets.append(target)
            else:
                trimmed_targets += 1

        if not valid_targets:
            dropped_invalid_target += 1
            continue

        normalized_record = dict(record)
        normalized_record["testcase_ids"] = valid_testcase_ids
        normalized_record["structured_targets"] = valid_targets

        signature = record_signature(normalized_record)
        if signature in seen_signatures:
            dropped_duplicate += 1
            continue
        seen_signatures.add(signature)
        kept_records.append(normalized_record)

    payload = dict(traceability)
    payload["records"] = kept_records
    return payload, {
        "original_record_count": len(original_records),
        "kept_record_count": len(kept_records),
        "dropped_missing_testcase": dropped_missing_testcase,
        "dropped_invalid_target": dropped_invalid_target,
        "dropped_duplicate": dropped_duplicate,
        "trimmed_invalid_targets": trimmed_targets,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="物理瘦身 legacy traceability_matrix.json，移除失效 testcase/target 和重复记录")
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--structured-prd", required=False, help="structured_prd.json 路径")
    parser.add_argument("--testcases", required=False, help="testcases_main.md 或 testcases.md 路径")
    parser.add_argument("--traceability", required=False, help="traceability_matrix.json 路径")
    parser.add_argument("--write", action="store_true", help="直接写回 traceability 文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.project_code and args.work_item_id:
        root = resolve_work_item_root(normalize_code(args.project_code), normalize_code(args.work_item_id))
        structured_prd_path = Path(args.structured_prd).resolve() if args.structured_prd else root / "structured_prd" / "structured_prd.json"
        testcase_path = (
            Path(args.testcases).resolve()
            if args.testcases
            else (root / "testcases" / "testcases_main.md" if (root / "testcases" / "testcases_main.md").exists() else root / "testcases" / "testcases.md")
        )
        traceability_path = Path(args.traceability).resolve() if args.traceability else root / "traceability" / "traceability_matrix.json"
    else:
        if not (args.structured_prd and args.testcases and args.traceability):
            raise SystemExit("必须提供 --project-code + --work-item-id，或显式提供 --structured-prd --testcases --traceability")
        structured_prd_path = Path(args.structured_prd).resolve()
        testcase_path = Path(args.testcases).resolve()
        traceability_path = Path(args.traceability).resolve()

    structured_prd = read_json(structured_prd_path)
    traceability = read_json(traceability_path)
    testcase_ids = parse_testcase_ids(testcase_path)
    payload, summary = slim_traceability(traceability, structured_prd, testcase_ids)

    if args.write:
        write_json(traceability_path, payload)
        print(f"legacy_traceability: {traceability_path}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
