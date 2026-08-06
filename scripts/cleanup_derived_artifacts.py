#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


MINIMAL_DERIVED_PATHS = [
    ".generation/latest",
    ".generation/archive",
    ".generation/runs",
    ".generation/current_run.json",
    "testcases/testcases.md",
    "testcases/dev_self_testcases.md",
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
TERMINAL_RUN_STATUSES = frozenset({"completed", "cancelled"})
UNFINISHED_TRANSACTION_STATUSES = frozenset({"prepared", "publishing"})
UNFINISHED_CASE_PLAN_TRANSACTION_STATUSES = frozenset(
    {"prepared", "committing"}
)
BACKUP_METADATA_FILES = (
    "publish_transaction.json",
    "generation_candidate.json",
)


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


def harness_cleanup_blockers(work_item_root: Path) -> list[str]:
    runs_root = work_item_root / ".generation" / "runs"
    blockers: list[str] = []
    lock_path = runs_root / "pipeline.lock"
    if lock_path.exists():
        blockers.append("存在 Harness 进程锁 .generation/runs/pipeline.lock")
    if not runs_root.is_dir():
        return blockers
    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        run_id = run_dir.name
        state_path = run_dir / "run_state.json"
        if state_path.is_file():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                blockers.append(f"{run_id}: run_state.json 无法读取: {exc}")
            else:
                status = str(state.get("status", "")).strip()
                if status not in TERMINAL_RUN_STATUSES:
                    recovery_hint = (
                        "，必须先执行 recover-roles"
                        if state.get("mode") == "multi_role"
                        and status == "running"
                        else ""
                    )
                    blockers.append(
                        f"{run_id}: run 状态 {status or '<missing>'} "
                        f"尚未终结{recovery_hint}"
                    )
        transaction_path = run_dir / "publish_transaction.json"
        if transaction_path.is_file():
            try:
                transaction = json.loads(
                    transaction_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as exc:
                blockers.append(
                    f"{run_id}: publish_transaction.json 无法读取: {exc}"
                )
            else:
                status = str(transaction.get("status", "")).strip()
                if status in UNFINISHED_TRANSACTION_STATUSES:
                    blockers.append(
                        f"{run_id}: 发布事务 {status}，必须先执行恢复"
                    )
        case_plan_transaction_path = (
            run_dir / "case_plan_commit_transaction.json"
        )
        if case_plan_transaction_path.is_file():
            try:
                transaction = json.loads(
                    case_plan_transaction_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as exc:
                blockers.append(
                    f"{run_id}: Case Plan transaction 无法读取: {exc}"
                )
            else:
                status = str(transaction.get("status", "")).strip()
                if status in UNFINISHED_CASE_PLAN_TRANSACTION_STATUSES:
                    blockers.append(
                        f"{run_id}: Case Plan transaction {status}，"
                        "必须先执行 recover-case-plan"
                    )
        approvals_root = run_dir / "approvals"
        if approvals_root.is_dir():
            for approval_path in sorted(approvals_root.glob("*.json")):
                try:
                    approval = json.loads(
                        approval_path.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError) as exc:
                    blockers.append(
                        f"{run_id}: {approval_path.name} 无法读取: {exc}"
                    )
                    continue
                if approval.get("status") == "pending":
                    blockers.append(
                        f"{run_id}: 审批 {approval_path.stem} 仍为 pending"
                    )
    return blockers


def preserve_publish_backups(
    work_item_root: Path,
    dry_run: bool,
) -> list[Path]:
    runs_root = work_item_root / ".generation" / "runs"
    archive_root = work_item_root / ".generation" / "backups"
    preserved: list[Path] = []
    if not runs_root.is_dir():
        return preserved
    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        publish_backup = run_dir / "publish_backup"
        if not publish_backup.is_dir():
            continue
        destination_root = archive_root / run_dir.name
        destination = destination_root / "publish_backup"
        preserved.append(destination)
        if dry_run:
            continue
        destination_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(publish_backup, destination, dirs_exist_ok=True)
        for metadata_name in BACKUP_METADATA_FILES:
            source = run_dir / metadata_name
            if source.is_file():
                shutil.copy2(source, destination_root / metadata_name)
    return preserved


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

    blockers = harness_cleanup_blockers(work_item_root)
    if blockers and not args.dry_run:
        print("cleanup blocked: Harness 运行仍需保留或恢复")
        for blocker in blockers:
            print(f"- {blocker}")
        return 2

    candidates: list[Path] = [work_item_root / relative_path for relative_path in MINIMAL_DERIVED_PATHS]
    for pattern in OPTIONAL_DERIVED_GLOBS:
        candidates.extend(sorted(work_item_root.glob(pattern)))
    preserved_backups: list[Path] = []
    if args.drop_backups:
        candidates.append(work_item_root / ".generation" / "backups")
    else:
        preserved_backups = preserve_publish_backups(
            work_item_root,
            args.dry_run,
        )

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
    if blockers:
        print("dry-run safety blockers:")
        for blocker in blockers:
            print(f"- {blocker}")
    if not args.drop_backups:
        print(
            "backups preserved: "
            f"{len(preserved_backups)} run(s) under .generation/backups"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
