#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


MINIMAL_DERIVED_PATHS = [
    ".generation/latest",
    ".generation/archive",
    "testcases/testcases.md",
    "testcases/dev_self_testcases.md",
    "testcases/testpoints.md",
    "testcases/testpoints.json",
    "testcases/testcase_bundle.json",
    "testcases/field_audit.json",
    "testcases/grouped_audit.json",
    "traceability/traceability_adapter.json",
    "traceability/traceability_matrix.json",
    "feishu_ready.md",
    "reviews/missing_rules.json",
    "reviews/missing_fidelity_points.json",
    "reviews/fidelity_hit_locations.json",
    "reviews/weak_cases.json",
    "reviews/generalized_cases.json",
    "reviews/duplicate_case_report.json",
]


OPTIONAL_DERIVED_GLOBS = [
    "reviews/*_rerun_stability_report.md",
]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def remove_path(path: Path, dry_run: bool) -> bool:
    if not path.exists():
        return False
    if dry_run:
        return True
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清理工作项可再生过程产物")
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--mode", choices=["minimal"], default="minimal")
    parser.add_argument("--dry-run", action="store_true", help="只打印将删除的文件，不实际删除")
    parser.add_argument("--drop-backups", action="store_true", help="同时删除 .generation/backups；默认保留备份")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_code = normalize_code(args.project_code)
    work_item_id = normalize_code(args.work_item_id)
    work_item_root = resolve_work_item_root(project_code, work_item_id)
    if not work_item_root.exists():
        print(f"工作项不存在: {work_item_root}")
        return 1

    candidates: list[Path] = [work_item_root / relative_path for relative_path in MINIMAL_DERIVED_PATHS]
    for pattern in OPTIONAL_DERIVED_GLOBS:
        candidates.extend(sorted(work_item_root.glob(pattern)))
    if args.drop_backups:
        candidates.append(work_item_root / ".generation" / "backups")

    removed: list[Path] = []
    for path in candidates:
        if remove_path(path, args.dry_run):
            removed.append(path)

    action = "would remove" if args.dry_run else "removed"
    print(f"cleanup mode: {args.mode}")
    print(f"work_item_root: {work_item_root}")
    print(f"{action}: {len(removed)}")
    for path in removed:
        print(f"- {path.relative_to(ROOT)}")
    if not args.drop_backups:
        print("backups preserved: .generation/backups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
