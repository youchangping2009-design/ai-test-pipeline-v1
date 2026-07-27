#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild project-level indexes and quality summary from work-item truth."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.testcase_markdown_utils import parse_testcase_document


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path, base: Path) -> str:
    return str(path.relative_to(base))


def required_artifacts(item_root: Path, level: str) -> list[Path]:
    required = [
        item_root / "inputs" / "requirement_summary.md",
        item_root / "inputs" / "source_manifest.json",
        item_root / "structured_prd" / "structured_prd.json",
        item_root / "acceptance" / "testability_gate.json",
        item_root / "testcases" / "case_plan.json",
        item_root / "testcases" / "testpoints.json",
        item_root / "testcases" / "testcases_main.md",
        item_root / "traceability" / "coverage_first_traceability.json",
        item_root / "reviews" / "review_record.md",
        item_root / "reviews" / "quality_report.json",
    ]
    if level in {"M", "L"}:
        required.append(item_root / "acceptance" / "acceptance_examples.json")
    if level == "L":
        required.extend(
            [
                item_root / "design" / "verification_responsibility_map.json",
                item_root / "design" / "test_design_matrix.json",
            ]
        )
    return required


def quality_status(item_root: Path) -> str:
    report_path = item_root / "reviews" / "quality_report.json"
    if not report_path.exists():
        return "missing"
    try:
        report = read_json(report_path)
    except Exception:
        return "stale"
    fingerprints = report.get("source_artifacts")
    if not isinstance(fingerprints, dict):
        return "stale"
    sources = {
        "structured_prd": item_root / "structured_prd" / "structured_prd.json",
        "coverage_matrix": item_root / "coverage" / "coverage_matrix.json",
        "testcases": item_root / "testcases" / "testcases_main.md",
        "coverage_first_traceability": item_root
        / "traceability"
        / "coverage_first_traceability.json",
    }
    for key, path in sources.items():
        record = fingerprints.get(key)
        if not path.exists() or not isinstance(record, dict):
            return "stale"
        if record.get("sha256") != sha256(path):
            return "stale"
    return "current"


def load_testcases(item_root: Path, work_item_id: str, project_root: Path) -> list[dict[str, Any]]:
    path = item_root / "testcases" / "testcases_main.md"
    if not path.exists():
        return []
    parsed = parse_testcase_document(path.read_text(encoding="utf-8"), strict=True)
    return [
        {
            "testcase_id": str(row.get("用例编号", "")).strip(),
            "work_item_id": work_item_id,
            "title": str(row.get("用例标题", "")).strip(),
            "priority": str(row.get("优先级", "")).strip(),
            "page_name": str(row.get("__page_name", "")).strip(),
            "section_name": str(row.get("__section_name", "")).strip(),
            "module_name": str(row.get("所属模块", "")).strip(),
            "feature_name": str(row.get("所属功能点", "")).strip(),
            "source_path": relative(path, project_root),
        }
        for row in parsed.get("rows", [])
        if str(row.get("用例编号", "")).strip()
    ]


def load_risks(item_root: Path, work_item_id: str, project_root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    quality_path = item_root / "reviews" / "quality_report.json"
    if quality_path.exists():
        try:
            quality = read_json(quality_path)
            for index, summary in enumerate(quality.get("unresolved_issues", []), start=1):
                result.append(
                    {
                        "risk_id": f"{work_item_id}-QUALITY-{index:03d}",
                        "work_item_id": work_item_id,
                        "source_type": "quality_report",
                        "summary": str(summary),
                        "status": "open",
                        "source_path": relative(quality_path, project_root),
                    }
                )
        except Exception:
            pass

    feedback_path = item_root / "design" / "design_feedback.json"
    if feedback_path.exists():
        try:
            feedback = read_json(feedback_path)
            for item in feedback.get("feedback_items", []):
                if (
                    not isinstance(item, dict)
                    or item.get("status") in {"rejected", "applied"}
                    or item.get("feedback_type") == "no_action"
                    or str(item.get("severity", "")).strip().lower() == "closed"
                ):
                    continue
                result.append(
                    {
                        "risk_id": str(item.get("feedback_id", "")).strip()
                        or f"{work_item_id}-DESIGN-{len(result) + 1:03d}",
                        "work_item_id": work_item_id,
                        "source_type": "design_feedback",
                        "summary": str(item.get("title") or item.get("finding") or "").strip(),
                        "status": str(item.get("status", "open")).strip(),
                        "severity": str(item.get("severity", "")).strip(),
                        "source_path": relative(feedback_path, project_root),
                    }
                )
        except Exception:
            pass
    return result


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['project_code']} Project Quality Summary",
        "",
        f"- 生成时间：{summary['generated_at']}",
        f"- 工作项：{summary['work_item_count']}",
        f"- 资产完整：{summary['ready_work_item_count']}",
        f"- 资产不完整：{summary['incomplete_work_item_count']}",
        f"- 正式用例：{summary['testcase_count']}",
        f"- 开放风险：{summary['open_risk_count']}",
        f"- 质量报告过期/缺失：{summary['stale_quality_report_count']}",
        "",
        "## 优先级分布",
        "",
    ]
    for priority, count in sorted(summary["priority_counts"].items()):
        lines.append(f"- {priority}: {count}")
    lines.append("")
    return "\n".join(lines)


def refresh(project_code: str) -> dict[str, Any]:
    project_root = ROOT / "assets" / "projects" / project_code
    manifest_path = project_root / "project_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"project_manifest 不存在: {manifest_path}")
    project_manifest = read_json(manifest_path)
    work_items_root = project_root / "work_items"
    generated_at = datetime.now().isoformat(timespec="seconds")
    work_item_items: list[dict[str, Any]] = []
    testcase_items: list[dict[str, Any]] = []
    risk_items: list[dict[str, Any]] = []

    for item_root in sorted(path for path in work_items_root.iterdir() if path.is_dir()):
        item_manifest_path = item_root / "manifest.json"
        if not item_manifest_path.exists():
            continue
        item_manifest = read_json(item_manifest_path)
        work_item_id = str(item_manifest.get("work_item_id") or item_root.name).strip()
        level = str(
            item_manifest.get("work_item_level")
            or project_manifest.get("default_work_item_level")
            or "M"
        ).strip().upper()
        testcases = load_testcases(item_root, work_item_id, project_root)
        risks = load_risks(item_root, work_item_id, project_root)
        required = required_artifacts(item_root, level)
        missing = [relative(path, project_root) for path in required if not path.exists()]
        report_status = quality_status(item_root)
        work_item_items.append(
            {
                "work_item_id": work_item_id,
                "title": str(item_manifest.get("title", "")).strip(),
                "status": str(item_manifest.get("status", "")).strip(),
                "work_item_level": level,
                "manifest_path": relative(item_manifest_path, project_root),
                "manifest_sha256": sha256(item_manifest_path),
                "artifact_status": "ready" if not missing else "incomplete",
                "missing_artifacts": missing,
                "testcase_count": len(testcases),
                "open_risk_count": len(risks),
                "quality_report_status": report_status,
                "primary_artifacts": {
                    "structured_prd": relative(
                        item_root / "structured_prd" / "structured_prd.md", project_root
                    ),
                    "testcases_main": relative(
                        item_root / "testcases" / "testcases_main.md", project_root
                    ),
                    "traceability_primary": relative(
                        item_root
                        / "traceability"
                        / "coverage_first_traceability.json",
                        project_root,
                    ),
                },
            }
        )
        testcase_items.extend(testcases)
        risk_items.extend(risks)

    work_item_index = {
        "project_code": project_code,
        "index_type": "work_item",
        "generated_at": generated_at,
        "items": work_item_items,
    }
    testcase_index = {
        "project_code": project_code,
        "index_type": "testcase",
        "generated_at": generated_at,
        "items": testcase_items,
    }
    risk_index = {
        "project_code": project_code,
        "index_type": "risk",
        "generated_at": generated_at,
        "items": risk_items,
    }
    priority_counts = Counter(item.get("priority", "") for item in testcase_items)
    summary = {
        "project_code": project_code,
        "generated_at": generated_at,
        "work_item_count": len(work_item_items),
        "ready_work_item_count": sum(
            1 for item in work_item_items if item["artifact_status"] == "ready"
        ),
        "incomplete_work_item_count": sum(
            1 for item in work_item_items if item["artifact_status"] != "ready"
        ),
        "testcase_count": len(testcase_items),
        "open_risk_count": len(risk_items),
        "stale_quality_report_count": sum(
            1
            for item in work_item_items
            if item["quality_report_status"] != "current"
        ),
        "priority_counts": {
            key: value for key, value in sorted(priority_counts.items()) if key
        },
    }

    write_json(project_root / "indexes" / "work_item_index.json", work_item_index)
    write_json(project_root / "indexes" / "testcase_index.json", testcase_index)
    write_json(project_root / "indexes" / "risk_index.json", risk_index)
    write_json(project_root / "reports" / "project_quality_summary.json", summary)
    (project_root / "reports" / "project_quality_summary.md").write_text(
        render_summary(summary), encoding="utf-8"
    )
    project_manifest["updated_at"] = generated_at
    write_json(manifest_path, project_manifest)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="从工作项真源刷新项目索引和质量汇总")
    parser.add_argument("--project-code", required=True)
    args = parser.parse_args()
    project_code = normalize_code(args.project_code)
    try:
        summary = refresh(project_code)
    except Exception as exc:
        print(f"刷新项目视图失败: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
