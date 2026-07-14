#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def infer_binding(record: dict[str, Any]) -> tuple[str, str]:
    title = str(record.get("testcase_title", "")).strip()
    targets = " ".join(str(target.get("target_name", "")).strip() for target in record.get("structured_targets", []))
    text = f"{title} {targets}"
    if any(keyword in text for keyword in ["排序", "过滤", "数据源", "候选项"]):
        return "backend_contract", "backend_code"
    if any(keyword in text for keyword in ["轮播", "顶部tab", "默认关闭", "展示", "显隐", "编辑", "只读", "弹窗"]):
        return "frontend_behavior", "frontend_code"
    return "shared_contract", "dual_code"


def build_focus_points(record: dict[str, Any]) -> list[str]:
    points: list[str] = []
    for target in record.get("structured_targets", []):
        if not isinstance(target, dict):
            continue
        target_name = str(target.get("target_name", "")).strip()
        if target_name and target_name not in points:
            points.append(target_name)
    fidelity_status = str(record.get("fidelity_status", "")).strip()
    if fidelity_status and fidelity_status != "not_applicable":
        points.append(f"fidelity_status={fidelity_status}")
    coverage_id = str(record.get("coverage_id", "")).strip()
    if coverage_id:
        points.append(f"coverage_id={coverage_id}")
    return points


def build_adapter(coverage_first: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for index, source_record in enumerate(coverage_first.get("records", []), start=1):
        binding, stage = infer_binding(source_record)
        evidence_ids = [str(item).strip() for item in source_record.get("evidence_ids", []) if str(item).strip()]
        testcase_id = str(source_record.get("testcase_id", "")).strip()
        adapter_record = {
            "record_id": f"TRA-{index:04d}",
            "evidence_id": evidence_ids[0] if evidence_ids else "EVD-UNMAPPED",
            "coverage_level": "full" if testcase_id else "none",
            "structured_targets": source_record.get("structured_targets", []),
            "testcase_ids": [testcase_id] if testcase_id else [],
            "gap_notes": (
                "adapter_source=coverage_first_traceability;"
                f" source_record_id={source_record.get('record_id', '')};"
                f" rule_id={source_record.get('rule_id', '')};"
                f" coverage_id={source_record.get('coverage_id', '')};"
                f" fidelity_status={source_record.get('fidelity_status', '')}"
            ),
            "implementation_binding": binding,
            "recommended_cr_stage": stage,
            "manual_confirmation_required": True,
            "cr_focus_points": build_focus_points(source_record),
        }
        records.append(adapter_record)
    return {
        "project_code": coverage_first.get("project_code", ""),
        "work_item_id": coverage_first.get("work_item_id", ""),
        "records": records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 coverage-first traceability 生成旧消费方兼容 adapter")
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--input", required=False, help="coverage_first_traceability.json 路径")
    parser.add_argument("--output", required=False, help="traceability adapter 输出路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.project_code and args.work_item_id:
        root = resolve_work_item_root(normalize_code(args.project_code), normalize_code(args.work_item_id))
        input_path = Path(args.input).resolve() if args.input else root / "traceability" / "coverage_first_traceability.json"
        output_path = Path(args.output).resolve() if args.output else root / "traceability" / "traceability_adapter.json"
    else:
        if not (args.input and args.output):
            raise SystemExit("必须提供 --project-code + --work-item-id，或显式提供 --input --output")
        input_path = Path(args.input).resolve()
        output_path = Path(args.output).resolve()

    coverage_first = read_json(input_path)
    payload = build_adapter(coverage_first)
    write_json(output_path, payload)
    print(f"traceability_adapter: {output_path}")
    print(f"records: {len(payload.get('records', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
