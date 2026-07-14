#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_traceability_assets import BACKEND_CONFIG_PAGES
from scripts.validate_traceability_assets import BACKEND_MODAL_SECTIONS
from scripts.validate_traceability_assets import derive_field_attribute_targets


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def next_record_number(records: list[dict[str, Any]]) -> int:
    max_num = 0
    for record in records:
        record_id = str(record.get("record_id", "")).strip()
        if record_id.startswith("TR-"):
            try:
                max_num = max(max_num, int(record_id.split("-", 1)[1]))
            except ValueError:
                continue
    return max_num + 1


def feature_key(module_name: str, feature_name: str) -> tuple[str, str]:
    return module_name.strip(), feature_name.strip()


def existing_target_keys(records: list[dict[str, Any]]) -> set[tuple[str, str, str, str, str]]:
    keys: set[tuple[str, str, str, str, str]] = set()
    for record in records:
        for target in record.get("structured_targets", []):
            if not isinstance(target, dict):
                continue
            target_type = str(target.get("target_type", "")).strip()
            if target_type == "field_attribute":
                keys.add(
                    (
                        target_type,
                        str(target.get("module_name", "")).strip(),
                        str(target.get("feature_name", "")).strip(),
                        str(target.get("field_name", "")).strip(),
                        f"{str(target.get('attribute_name', '')).strip()}::{str(target.get('target_name', '')).strip()}",
                    )
                )
            elif target_type == "field_rule":
                keys.add(
                    (
                        target_type,
                        str(target.get("module_name", "")).strip(),
                        str(target.get("feature_name", "")).strip(),
                        str(target.get("field_name", "")).strip(),
                        str(target.get("target_name", "")).strip(),
                    )
                )
    return keys


def expand_traceability(structured_prd: dict[str, Any], traceability: dict[str, Any]) -> tuple[dict[str, Any], int]:
    records = list(traceability.get("records", []))
    next_num = next_record_number(records)
    seen_targets = existing_target_keys(records)
    added = 0

    base_records_by_feature: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        for target in record.get("structured_targets", []):
            if not isinstance(target, dict):
                continue
            if target.get("target_type") != "feature":
                continue
            module_name = str(target.get("module_name", "")).strip()
            feature_name = str(target.get("feature_name", "")).strip()
            if module_name and feature_name:
                base_records_by_feature.setdefault(feature_key(module_name, feature_name), []).append(record)

    for module in structured_prd.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []):
            if not isinstance(feature, dict):
                continue
            page_name = str(feature.get("page_name", "")).strip()
            section_name = str(feature.get("section_name", "")).strip()
            feature_name = str(feature.get("feature_name", "")).strip()
            if page_name not in BACKEND_CONFIG_PAGES or section_name not in BACKEND_MODAL_SECTIONS:
                continue

            base_records = base_records_by_feature.get(feature_key(module_name, feature_name), [])
            if not base_records:
                continue

            testcase_ids: list[str] = []
            for record in base_records:
                for testcase_id in record.get("testcase_ids", []):
                    if testcase_id not in testcase_ids:
                        testcase_ids.append(testcase_id)

            template_record = base_records[0]
            evidence_id = template_record.get("evidence_id", "")
            implementation_binding = template_record.get("implementation_binding")
            recommended_cr_stage = template_record.get("recommended_cr_stage")
            manual_confirmation_required = template_record.get("manual_confirmation_required")

            for field in feature.get("field_definitions", []):
                if not isinstance(field, dict):
                    continue
                field_name = str(field.get("field_name", "")).strip()
                if not field_name:
                    continue
                for attribute_name, target_name in derive_field_attribute_targets(field):
                    target_key = ("field_attribute", module_name, feature_name, field_name, f"{attribute_name}::{target_name}")
                    if target_key in seen_targets:
                        continue
                    records.append(
                        {
                            "record_id": f"TR-{next_num:03d}",
                            "evidence_id": evidence_id,
                            "coverage_level": "full",
                            "structured_targets": [
                                {
                                    "target_type": "field_attribute",
                                    "module_name": module_name,
                                    "feature_name": feature_name,
                                    "field_name": field_name,
                                    "attribute_name": attribute_name,
                                    "target_name": target_name,
                                }
                            ],
                            "testcase_ids": testcase_ids,
                            "implementation_binding": implementation_binding,
                            "recommended_cr_stage": recommended_cr_stage,
                            "manual_confirmation_required": manual_confirmation_required,
                            "cr_focus_points": [f"{field_name}.{attribute_name}:{target_name}"],
                        }
                    )
                    seen_targets.add(target_key)
                    next_num += 1
                    added += 1

            for field_rule in feature.get("field_rules", []):
                if not isinstance(field_rule, dict):
                    continue
                field_name = str(field_rule.get("field_name", "")).strip()
                rule_text = str(field_rule.get("rule_text", "")).strip()
                target_key = ("field_rule", module_name, feature_name, field_name, rule_text)
                if not field_name or not rule_text or target_key in seen_targets:
                    continue
                records.append(
                    {
                        "record_id": f"TR-{next_num:03d}",
                        "evidence_id": evidence_id,
                        "coverage_level": "full",
                        "structured_targets": [
                            {
                                "target_type": "field_rule",
                                "module_name": module_name,
                                "feature_name": feature_name,
                                "field_name": field_name,
                                "target_name": rule_text,
                            }
                        ],
                        "testcase_ids": testcase_ids,
                        "implementation_binding": implementation_binding,
                        "recommended_cr_stage": recommended_cr_stage,
                        "manual_confirmation_required": manual_confirmation_required,
                        "cr_focus_points": [rule_text],
                    }
                )
                seen_targets.add(target_key)
                next_num += 1
                added += 1

    traceability["records"] = records
    return traceability, added


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为后台配置页 edit_modal 扩展字段属性级 traceability 记录")
    parser.add_argument("--structured-prd", required=True, help="structured_prd.json 路径")
    parser.add_argument("--traceability", required=True, help="traceability_matrix.json 路径")
    parser.add_argument("--write", action="store_true", help="直接覆盖写回 traceability 文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    structured_prd_path = Path(args.structured_prd).resolve()
    traceability_path = Path(args.traceability).resolve()

    try:
        structured_prd = load_json(structured_prd_path)
        traceability = load_json(traceability_path)
    except Exception as exc:
        print(f"读取输入失败: {exc}", file=sys.stderr)
        return 1

    expanded, added = expand_traceability(structured_prd, traceability)
    if args.write:
        write_json(traceability_path, expanded)
        print(f"已写回 traceability: {traceability_path}")
    else:
        print(json.dumps(expanded, ensure_ascii=False, indent=2))
    print(f"新增记录数: {added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
