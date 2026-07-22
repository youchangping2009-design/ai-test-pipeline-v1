#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_command(command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    return result.returncode == 0, output.strip()


def run_review_command(
    command_text: str,
    review_type: str,
    item_root: Path,
    code_dirs: list[str],
) -> None:
    env = {
        "ATP_REPO_ROOT": str(ROOT),
        "ATP_WORK_ITEM_ROOT": str(item_root),
        "ATP_REVIEW_TYPE": review_type,
        "ATP_CODE_DIRS": os.pathsep.join(code_dirs),
        "ATP_INPUT_REQUEST": str(item_root / "code_reviews" / ("frontend_review_request.md" if review_type == "frontend_code" else "backend_review_request.md")),
        "ATP_OUTPUT_REVIEW": str(item_root / "code_reviews" / ("frontend_code_review.md" if review_type == "frontend_code" else "backend_code_review.md")),
        "ATP_OUTPUT_CONFIRMATION": str(item_root / "code_reviews" / ("frontend_confirmation.json" if review_type == "frontend_code" else "backend_confirmation.json")),
    }
    result = subprocess.run(
        command_text,
        cwd=ROOT,
        shell=True,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    if result.returncode != 0:
        raise SystemExit(f"{review_type} 自动代码评审执行失败:\n{output}")


def update_scope_status(scope_path: Path, status: str, next_action: str) -> None:
    scope = load_json(scope_path)
    scope["status"] = status
    scope["next_action"] = next_action
    scope["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_json(scope_path, scope)


def ensure_scope_ready(scope_path: Path) -> dict[str, Any]:
    if not scope_path.exists():
        raise SystemExit(f"缺少 code_review_scope.json: {scope_path}")
    scope = load_json(scope_path)
    if scope.get("status") not in {"ready_for_code_review", "frontend_review_in_progress", "backend_review_in_progress"}:
        raise SystemExit(f"当前 code review 状态不可执行: {scope.get('status')}")
    return scope


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="执行前后端代码评审流水线")
    parser.add_argument("--project-code", required=True, help="项目编码")
    parser.add_argument("--work-item-id", required=True, help="工作项 ID")
    parser.add_argument("--frontend-review-command", required=False, help="前端代码评审命令")
    parser.add_argument("--backend-review-command", required=False, help="后端代码评审命令")
    parser.add_argument("--skip-validate", action="store_true", help="跳过 validate_work_item")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_code = normalize_code(args.project_code)
    work_item_id = normalize_code(args.work_item_id)
    item_root = work_item_root(project_code, work_item_id)
    if not item_root.exists():
        raise SystemExit(f"工作项不存在: {item_root}")

    scope_path = item_root / "code_reviews" / "code_review_scope.json"
    scope = ensure_scope_ready(scope_path)

    frontend_dirs = scope.get("frontend_code_dirs", [])
    backend_dirs = scope.get("backend_code_dirs", [])

    if (args.frontend_review_command or "").strip():
        update_scope_status(scope_path, "frontend_review_in_progress", "前端代码评审执行中")
        run_review_command(args.frontend_review_command, "frontend_code", item_root, frontend_dirs)

    if (args.backend_review_command or "").strip():
        update_scope_status(scope_path, "backend_review_in_progress", "后端代码评审执行中")
        run_review_command(args.backend_review_command, "backend_code", item_root, backend_dirs)

    update_scope_status(scope_path, "code_review_completed", "代码评审已完成，可执行工作项级统一校验。")

    ok, output = run_command(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_design_feedback_from_code_reviews.py"),
            "--project-code",
            project_code,
            "--work-item-id",
            work_item_id,
        ]
    )
    print(output)
    if not ok:
        return 1

    if not args.skip_validate:
        ok, output = run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_work_item.py"),
                "--project-code",
                project_code,
                "--work-item-id",
                work_item_id,
            ]
        )
        print(output)
        if not ok:
            return 1

    print(f"code_review_scope: {scope_path}")
    print("code_review_pipeline: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
