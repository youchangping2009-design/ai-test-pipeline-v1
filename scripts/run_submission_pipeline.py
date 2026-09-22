#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from work_item_policy import DEFAULT_WORK_ITEM_LEVEL
from work_item_policy import VALID_WORK_ITEM_LEVELS
from work_item_policy import persist_default_work_item_level
from work_item_policy import resolve_work_item_level

ROOT = Path(__file__).resolve().parents[1]
LEVEL_STAGE_POLICY = {
    "S": ["testability_gate", "case_plan", "testcases", "code_review"],
    "M": ["testability_gate", "acceptance_examples", "case_plan", "testcases", "code_review"],
    "L": [
        "testability_gate",
        "acceptance_examples",
        "verification_responsibility_map",
        "test_design_matrix",
        "case_plan",
        "testcases",
        "code_review",
    ],
}
DESIGN_STOP_STAGES = {
    "testability_gate",
    "acceptance_examples",
    "verification_responsibility_map",
    "test_design_matrix",
    "case_plan",
}


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


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


def work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def ensure_work_item(
    project_code: str,
    work_item_id: str,
    title: str,
    requirement_version: str,
    work_item_level: str,
) -> None:
    item_root = work_item_root(project_code, work_item_id)
    if item_root.exists():
        return
    command = [
        sys.executable,
        str(ROOT / "scripts" / "create_work_item.py"),
        "--project-code",
        project_code,
        "--work-item-id",
        work_item_id,
    ]
    if title:
        command.extend(["--title", title])
    if requirement_version:
        command.extend(["--requirement-version", requirement_version])
    command.extend(["--work-item-level", work_item_level])
    ok, output = run_command(command)
    if not ok:
        raise SystemExit(f"创建工作项失败:\n{output}")


def copy_input_path(source: Path, inputs_dir: Path) -> list[Path]:
    copied: list[Path] = []
    if source.is_file():
        target = inputs_dir / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)
        return copied

    if source.is_dir():
        base = inputs_dir / source.name
        for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
            relative = file_path.relative_to(source)
            target = base / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target)
            copied.append(target)
        return copied

    raise SystemExit(f"输入路径不存在: {source}")


def sync_inputs(item_root: Path, input_paths: list[str]) -> list[Path]:
    inputs_dir = item_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for raw_path in input_paths:
        copied.extend(copy_input_path(Path(raw_path).resolve(), inputs_dir))
    return copied


def update_code_review_scope(item_root: Path, frontend_dirs: list[str], backend_dirs: list[str]) -> tuple[str, Path, Path]:
    code_reviews_dir = item_root / "code_reviews"
    code_reviews_dir.mkdir(parents=True, exist_ok=True)
    scope_path = code_reviews_dir / "code_review_scope.json"
    request_path = code_reviews_dir / "code_review_request.md"

    frontend_paths = [Path(path).resolve() for path in frontend_dirs]
    backend_paths = [Path(path).resolve() for path in backend_dirs]
    for path in frontend_paths + backend_paths:
        if not path.exists() or not path.is_dir():
            raise SystemExit(f"代码目录不存在或不是目录: {path}")

    frontend = [str(path) for path in frontend_paths]
    backend = [str(path) for path in backend_paths]

    if frontend and backend:
        status = "ready_for_code_review"
        next_action = "代码目录已补充完成，可进入前端代码 CR 与后端代码 CR 流程。"
    else:
        status = "awaiting_code_directories"
        missing = []
        if not frontend:
            missing.append("frontend_code_dirs")
        if not backend:
            missing.append("backend_code_dirs")
        next_action = "请补充以下代码目录后进入代码映证流程：" + ", ".join(missing)

    payload = {
        "status": status,
        "frontend_code_dirs": frontend,
        "backend_code_dirs": backend,
        "next_action": next_action,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    scope_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    request_lines = [
        "# Code Review Request",
        "",
        f"- status: `{status}`",
        f"- next_action: `{next_action}`",
        "",
        "## Required Code Directories",
        "",
        f"- frontend_code_dirs: {', '.join(frontend) if frontend else '待补充'}",
        f"- backend_code_dirs: {', '.join(backend) if backend else '待补充'}",
        "",
        "## Review Policy",
        "",
        "- 代码评审只做映证，不修改业务代码",
        "- 代码评审只新增 CR 产物，不修改历史产出物",
    ]
    request_path.write_text("\n".join(request_lines) + "\n", encoding="utf-8")
    return status, scope_path, request_path


def run_prepare_code_review(project_code: str, work_item_id: str, frontend_dirs: list[str], backend_dirs: list[str]) -> None:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "prepare_code_review_run.py"),
        "--project-code",
        project_code,
        "--work-item-id",
        work_item_id,
    ]
    for path in frontend_dirs:
        command.extend(["--frontend-code-dir", path])
    for path in backend_dirs:
        command.extend(["--backend-code-dir", path])
    ok, output = run_command(command)
    if not ok:
        raise SystemExit(f"生成代码评审请求文件失败:\n{output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="测试提交入口：自动落输入、执行到代码映证前，并提示补充代码目录")
    parser.add_argument("--project-code", required=True, help="项目编码")
    parser.add_argument("--work-item-id", required=True, help="工作项 ID")
    parser.add_argument("--title", required=False, default="", help="工作项标题")
    parser.add_argument("--requirement-version", required=False, default="", help="需求版本")
    parser.add_argument("--input", action="append", default=[], help="需求文件或补充资料目录，可多次传入")
    parser.add_argument(
        "--provider",
        choices=["existing", "command", "openai"],
        default="command",
        help="bundle 生成兼容入口；推荐按 START_HERE.md 与宿主适配层选择运行方式",
    )
    parser.add_argument("--generator-command", required=False, help="command 兼容入口使用的本地生成命令")
    parser.add_argument(
        "--model",
        required=False,
        help="兼容 HTTP endpoint 入口的覆盖模型名；默认从运行时上下文与宿主适配层解析",
    )
    parser.add_argument("--frontend-code-dir", action="append", default=[], help="前端代码目录，可多次传入")
    parser.add_argument("--backend-code-dir", action="append", default=[], help="后端代码目录，可多次传入")
    parser.add_argument("--frontend-review-command", required=False, help="前端代码评审命令")
    parser.add_argument("--backend-review-command", required=False, help="后端代码评审命令")
    parser.add_argument("--skip-generate", action="store_true", help="只落输入与任务包，不生成 bundle")
    parser.add_argument(
        "--work-item-level",
        choices=sorted(VALID_WORK_ITEM_LEVELS),
        default=None,
        help="显式覆盖 manifest.json 中的工作项级别；未指定时读取 manifest，缺失则回退 M",
    )
    parser.add_argument(
        "--stop-at",
        choices=[
            "testability_gate",
            "acceptance_examples",
            "verification_responsibility_map",
            "test_design_matrix",
            "case_plan",
            "testcases",
            "code_review",
        ],
        default="code_review",
        help="预留阶段停止点；当前用于控制是否在生成任务包后提前停止",
    )
    parser.add_argument("--strict", action="store_true", help="预留严格质量门开关；正式交付建议配合 validate_work_item.py --strict 使用")
    parser.add_argument("--repair", action="store_true", help="预留 repair loop 开关，本轮仅保留参数")
    parser.add_argument(
        "--eval-fixture",
        required=False,
        help="预留 eval fixture 名称，例如 CONFIGURATION_RULES",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_code = normalize_code(args.project_code)
    work_item_id = normalize_code(args.work_item_id)
    item_root = work_item_root(project_code, work_item_id)
    manifest_path = item_root / "manifest.json"
    if item_root.exists() and not manifest_path.exists():
        raise SystemExit(f"工作项目录已存在但缺少 manifest.json: {manifest_path}")
    if item_root.exists() and manifest_path.exists():
        persisted_level, _ = persist_default_work_item_level(manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        work_item_level, level_source = resolve_work_item_level(manifest, args.work_item_level)
    else:
        project_manifest_path = (
            ROOT
            / "assets"
            / "projects"
            / project_code
            / "project_manifest.json"
        )
        project_default_level = ""
        if project_manifest_path.exists():
            project_manifest = json.loads(
                project_manifest_path.read_text(encoding="utf-8")
            )
            project_default_level = str(
                project_manifest.get("default_work_item_level", "")
            ).strip().upper()
        work_item_level = (
            args.work_item_level
            or project_default_level
            or DEFAULT_WORK_ITEM_LEVEL
        )
        level_source = (
            "cli"
            if args.work_item_level
            else "project_manifest"
            if project_default_level
            else "default"
        )
        ensure_work_item(
            project_code,
            work_item_id,
            args.title.strip(),
            args.requirement_version.strip(),
            work_item_level,
        )
        persisted_level = work_item_level
    level_stages = LEVEL_STAGE_POLICY[work_item_level]

    copied_inputs = sync_inputs(item_root, args.input)

    ok, output = run_command(
        [
            sys.executable,
            str(ROOT / "scripts" / "prepare_regeneration_run.py"),
            "--project-code",
            project_code,
            "--work-item-id",
            work_item_id,
            "--work-item-level",
            work_item_level,
        ]
    )
    if not ok:
        raise SystemExit(f"生成任务包失败:\n{output}")

    if args.stop_at in DESIGN_STOP_STAGES:
        print(f"work_item: {item_root}")
        print(f"copied_inputs: {len(copied_inputs)}")
        for path in copied_inputs:
            print(f"- {path}")
        print(f"work_item_level: {work_item_level}")
        print(f"work_item_level_source: {level_source}")
        print(f"manifest_work_item_level: {persisted_level}")
        print(f"level_stage_policy: {','.join(level_stages)}")
        print(f"stop_at: {args.stop_at}")
        if args.stop_at not in level_stages:
            print("stop_at_policy_note: 当前 stop_at 不属于该 level 的推荐阶段，但作为预留入口保留")
        if args.stop_at == "test_design_matrix":
            print("stop_at_policy_note: test_design_matrix 为 L strict 设计矩阵门，需覆盖生成正式用例的 case_plan")
        print("pipeline_status: STOPPED_AT_DESIGN_STAGE")
        return 0

    if not args.skip_generate:
        if args.provider == "command" and not (args.generator_command or "").strip():
            raise SystemExit("provider=command 时必须提供 --generator-command")

        command = [
            sys.executable,
            str(ROOT / "scripts" / "generate_regeneration_bundle.py"),
            "--project-code",
            project_code,
            "--work-item-id",
            work_item_id,
            "--provider",
            args.provider,
        ]
        if args.provider == "command" and args.generator_command:
            command.extend(["--generator-command", args.generator_command])
        if args.provider == "openai" and args.model:
            command.extend(["--model", args.model])

        ok, output = run_command(command)
        if not ok:
            raise SystemExit(f"生成/执行 bundle 失败:\n{output}")

        execute_command = [
            sys.executable,
            str(ROOT / "scripts" / "execute_regeneration_bundle.py"),
            "--project-code",
            project_code,
            "--work-item-id",
            work_item_id,
            "--bundle",
            str(item_root / ".generation" / "latest" / "regeneration_bundle.json"),
            "--skip-code-reviews",
        ]
        if args.strict:
            execute_command.append("--strict")
        ok, output = run_command(execute_command)
        if not ok:
            raise SystemExit(f"执行重生成失败:\n{output}")

    status, scope_path, request_path = update_code_review_scope(
        item_root=item_root,
        frontend_dirs=args.frontend_code_dir,
        backend_dirs=args.backend_code_dir,
    )

    if status == "ready_for_code_review":
        run_prepare_code_review(project_code, work_item_id, args.frontend_code_dir, args.backend_code_dir)
        if (args.frontend_review_command or "").strip() or (args.backend_review_command or "").strip():
            review_command = [
                sys.executable,
                str(ROOT / "scripts" / "run_code_review_pipeline.py"),
                "--project-code",
                project_code,
                "--work-item-id",
                work_item_id,
                "--skip-validate",
            ]
            if (args.frontend_review_command or "").strip():
                review_command.extend(["--frontend-review-command", args.frontend_review_command])
            if (args.backend_review_command or "").strip():
                review_command.extend(["--backend-review-command", args.backend_review_command])
            ok, output = run_command(review_command)
            if not ok:
                raise SystemExit(f"执行代码评审流水线失败:\n{output}")

    print(f"work_item: {item_root}")
    print(f"copied_inputs: {len(copied_inputs)}")
    for path in copied_inputs:
        print(f"- {path}")
    print(f"code_review_status: {status}")
    print(f"code_review_scope: {scope_path}")
    print(f"code_review_request: {request_path}")
    print(f"work_item_level: {work_item_level}")
    print(f"work_item_level_source: {level_source}")
    print(f"manifest_work_item_level: {persisted_level}")
    print(f"strict_requested: {str(args.strict).lower()}")
    if args.repair:
        print("repair_requested: true (reserved)")
    if args.eval_fixture:
        print(f"eval_fixture: {args.eval_fixture} (reserved)")

    if status != "ready_for_code_review":
        print("pipeline_status: WAITING_FOR_CODE_DIRECTORIES")
    else:
        print("pipeline_status: READY_FOR_CODE_REVIEW")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
