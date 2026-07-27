#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the lightweight project shell and its derived indexes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEGACY_PROJECT_DIRS = [
    "image_evidence",
    "analysis",
    "coverage",
    "evidence",
    "structured_prd",
    "traceability",
    "testcases",
    "reviews",
]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="校验轻量项目壳、索引和工作项引用")
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--validate-work-items", action="store_true")
    parser.add_argument("--skip-code-reviews", action="store_true")
    args = parser.parse_args()

    project_code = normalize_code(args.project_code)
    project_root = ROOT / "assets" / "projects" / project_code
    errors: list[str] = []
    required_files = [
        "README.md",
        "project_manifest.json",
        "inputs/common/README.md",
        "indexes/work_item_index.json",
        "indexes/testcase_index.json",
        "indexes/risk_index.json",
        "reports/project_quality_summary.json",
        "reports/project_quality_summary.md",
        "knowledge/reusable_rules.json",
        "knowledge/golden_examples.json",
        "knowledge/defect_patterns.json",
    ]
    for relative_path in required_files:
        if not (project_root / relative_path).exists():
            errors.append(f"缺少项目壳文件: {relative_path}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    manifest = read_json(project_root / "project_manifest.json")
    if manifest.get("project_code") != project_code:
        errors.append("project_manifest.project_code 与目录不一致")
    if manifest.get("asset_model") != "work_item_truth":
        errors.append("project_manifest.asset_model 必须为 work_item_truth")

    work_item_index = read_json(project_root / "indexes" / "work_item_index.json")
    testcase_index = read_json(project_root / "indexes" / "testcase_index.json")
    risk_index = read_json(project_root / "indexes" / "risk_index.json")
    summary = read_json(project_root / "reports" / "project_quality_summary.json")
    for payload, expected_type, label in [
        (work_item_index, "work_item", "work_item_index"),
        (testcase_index, "testcase", "testcase_index"),
        (risk_index, "risk", "risk_index"),
    ]:
        if payload.get("project_code") != project_code:
            errors.append(f"{label}.project_code 与项目目录不一致")
        if payload.get("index_type") != expected_type:
            errors.append(f"{label}.index_type 必须为 {expected_type}")
        if not isinstance(payload.get("items"), list):
            errors.append(f"{label}.items 必须为数组")
    if summary.get("project_code") != project_code:
        errors.append("project_quality_summary.project_code 与项目目录不一致")

    actual_manifests = {
        path.parent.name: path
        for path in (project_root / "work_items").glob("*/manifest.json")
    }
    indexed_items = {
        str(item.get("work_item_id", "")): item
        for item in work_item_index.get("items", [])
        if isinstance(item, dict)
    }
    if set(actual_manifests) != set(indexed_items):
        errors.append(
            f"work_item_index 与实际目录不一致: actual={sorted(actual_manifests)}, "
            f"indexed={sorted(indexed_items)}"
        )
    for work_item_id, manifest_path in actual_manifests.items():
        item = indexed_items.get(work_item_id, {})
        if item.get("manifest_sha256") != sha256(manifest_path):
            errors.append(f"{work_item_id} manifest 指纹已变化，请刷新项目视图")

    testcase_items = testcase_index.get("items", [])
    for item in testcase_items:
        source_path = project_root / str(item.get("source_path", ""))
        if not source_path.exists():
            errors.append(
                f"testcase index 来源不存在: {item.get('testcase_id')} -> {item.get('source_path')}"
            )
        if str(item.get("work_item_id", "")) not in actual_manifests:
            errors.append(f"testcase index 引用未知工作项: {item.get('work_item_id')}")

    for item in risk_index.get("items", []):
        source_path = project_root / str(item.get("source_path", ""))
        if not source_path.exists():
            errors.append(f"risk index 来源不存在: {item.get('risk_id')}")

    expected_counts = {
        "work_item_count": len(indexed_items),
        "testcase_count": len(testcase_items),
        "open_risk_count": len(risk_index.get("items", [])),
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            errors.append(f"project quality summary.{key} 不一致: {summary.get(key)} != {expected}")

    if args.strict:
        for directory in LEGACY_PROJECT_DIRS:
            legacy_path = project_root / directory
            if legacy_path.exists() and any(legacy_path.rglob("*")):
                errors.append(f"strict 轻量项目壳禁止旧项目级产物目录: {directory}/")

    if args.validate_work_items:
        for work_item_id in sorted(actual_manifests):
            command = [
                sys.executable,
                str(ROOT / "scripts" / "validate_work_item.py"),
                "--project-code",
                project_code,
                "--work-item-id",
                work_item_id,
                "--strict",
            ]
            if args.skip_code_reviews:
                command.append("--skip-code-reviews")
            result = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if result.returncode != 0:
                errors.append(f"{work_item_id} strict 校验失败")

    if errors:
        print("❌ project validation failed")
        for error in errors:
            print(f"- {error}")
        return 1

    print("✅ project validation passed")
    print(f"project_code: {project_code}")
    print(f"work_items: {len(indexed_items)}")
    print(f"testcases: {len(testcase_items)}")
    print(f"risks: {len(risk_index.get('items', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
