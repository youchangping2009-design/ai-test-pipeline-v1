#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize a lightweight AI Test Pipeline project shell."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def normalize_project_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("project_code 不能为空")
    return normalized


def write_text(path: Path, content: str, force: bool, written: list[Path], skipped: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        skipped.append(path)
        return
    path.write_text(content, encoding="utf-8")
    written.append(path)


def json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_manifest(
    project_code: str,
    project_name: str,
    business_line: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "project_code": project_code,
        "project_name": project_name,
        "business_line": business_line,
        "created_at": now,
        "updated_at": now,
        "status": "active",
        "asset_model": "work_item_truth",
        "default_work_item_level": "M",
        "paths": {
            "inputs_common": "inputs/common/",
            "work_items": "work_items/",
            "indexes": "indexes/",
            "reports": "reports/",
            "knowledge": "knowledge/",
        },
    }


def build_readme(project_code: str, project_name: str, business_line: str) -> str:
    return (
        f"# {project_code}\n\n"
        f"- 项目名称：{project_name or '待补充'}\n"
        f"- 业务线：{business_line or '待补充'}\n"
        "- 资产模型：`work_item_truth`\n\n"
        "## 目录\n\n"
        "- `project_manifest.json`：项目级静态元数据\n"
        "- `inputs/common/`：跨工作项共享资料\n"
        "- `work_items/`：需求与测试资产正式真源\n"
        "- `indexes/`：工作项、用例和风险的派生索引\n"
        "- `reports/`：项目级质量汇总\n"
        "- `knowledge/`：人工确认的可复用规则与样例\n\n"
        "## 使用方式\n\n"
        "```bash\n"
        f"python3 scripts/create_work_item.py --project-code {project_code} --work-item-id REQ-001\n"
        f"python3 scripts/validate_work_item.py --project-code {project_code} --work-item-id REQ-001 --strict\n"
        f"python3 scripts/refresh_project_views.py --project-code {project_code}\n"
        f"python3 scripts/validate_project.py --project-code {project_code} --strict\n"
        "```\n\n"
        "正式 structured PRD、Case Plan、Testpoints、Testcases、Traceability 和 Review "
        "只保存在 `work_items/<WORK_ITEM_ID>/`；项目级索引与报告不得反写工作项。\n"
    )


def build_common_inputs_readme() -> str:
    return (
        "# Common Inputs\n\n"
        "存放多个工作项共享的项目资料，例如：\n\n"
        "- 公共业务规则与术语\n"
        "- 权限模型与业务枚举\n"
        "- 公共接口说明\n"
        "- 测试环境与数据准备说明\n\n"
        "工作项通过 `inputs/source_manifest.json` 引用这些资料，不复制正式工作项产物到项目根。\n"
    )


def empty_index(project_code: str, index_type: str) -> dict[str, Any]:
    return {
        "project_code": project_code,
        "index_type": index_type,
        "generated_at": "",
        "items": [],
    }


def empty_summary(project_code: str) -> dict[str, Any]:
    return {
        "project_code": project_code,
        "generated_at": "",
        "work_item_count": 0,
        "ready_work_item_count": 0,
        "incomplete_work_item_count": 0,
        "testcase_count": 0,
        "open_risk_count": 0,
        "stale_quality_report_count": 0,
        "priority_counts": {},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化轻量 AI Test Pipeline 项目壳")
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--project-name", default="")
    parser.add_argument("--business-line", default="")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        project_code = normalize_project_code(args.project_code)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    project_root = ROOT / "assets" / "projects" / project_code
    existing_manifest_path = project_root / "project_manifest.json"
    existing_manifest: dict[str, Any] = {}
    if existing_manifest_path.exists():
        try:
            existing_manifest = json.loads(
                existing_manifest_path.read_text(encoding="utf-8")
            )
        except Exception:
            existing_manifest = {}
    project_name = args.project_name.strip() or str(
        existing_manifest.get("project_name", "")
    )
    business_line = args.business_line.strip() or str(
        existing_manifest.get("business_line", "")
    )
    for directory in [
        project_root / "inputs" / "common",
        project_root / "work_items",
        project_root / "indexes",
        project_root / "reports",
        project_root / "knowledge",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    skipped: list[Path] = []
    write_text(
        project_root / "README.md",
        build_readme(project_code, project_name, business_line),
        args.force,
        written,
        skipped,
    )
    write_text(
        project_root / "project_manifest.json",
        json_text(build_manifest(project_code, project_name, business_line)),
        args.force,
        written,
        skipped,
    )
    if existing_manifest.get("created_at"):
        refreshed_manifest = json.loads(
            (project_root / "project_manifest.json").read_text(encoding="utf-8")
        )
        refreshed_manifest["created_at"] = existing_manifest["created_at"]
        refreshed_manifest["default_work_item_level"] = existing_manifest.get(
            "default_work_item_level",
            refreshed_manifest["default_work_item_level"],
        )
        refreshed_manifest["status"] = existing_manifest.get(
            "status",
            refreshed_manifest["status"],
        )
        (project_root / "project_manifest.json").write_text(
            json_text(refreshed_manifest),
            encoding="utf-8",
        )
    write_text(
        project_root / "inputs" / "common" / "README.md",
        build_common_inputs_readme(),
        args.force,
        written,
        skipped,
    )
    for name, index_type in [
        ("work_item_index.json", "work_item"),
        ("testcase_index.json", "testcase"),
        ("risk_index.json", "risk"),
    ]:
        write_text(
            project_root / "indexes" / name,
            json_text(empty_index(project_code, index_type)),
            args.force,
            written,
            skipped,
        )
    summary = empty_summary(project_code)
    write_text(
        project_root / "reports" / "project_quality_summary.json",
        json_text(summary),
        args.force,
        written,
        skipped,
    )
    write_text(
        project_root / "reports" / "project_quality_summary.md",
        f"# {project_code} Project Quality Summary\n\n尚未刷新项目视图。\n",
        args.force,
        written,
        skipped,
    )
    for name, item_type in [
        ("reusable_rules.json", "reusable_rule"),
        ("golden_examples.json", "golden_example"),
        ("defect_patterns.json", "defect_pattern"),
    ]:
        write_text(
            project_root / "knowledge" / name,
            json_text({"project_code": project_code, "item_type": item_type, "items": []}),
            False,
            written,
            skipped,
        )

    if any((project_root / "work_items").glob("*/manifest.json")):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "refresh_project_views.py"),
                "--project-code",
                project_code,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"项目视图刷新失败:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
            return 1

    print(f"project_root: {project_root}")
    print(f"written: {len(written)}")
    for path in written:
        print(f"- {path.relative_to(ROOT)}")
    print(f"skipped: {len(skipped)}")
    print(
        f"next: python3 scripts/create_work_item.py --project-code {project_code} "
        "--work-item-id REQ-001"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
