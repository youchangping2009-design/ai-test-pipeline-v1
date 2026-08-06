#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def has_artifact_with_suffix(paths: set[str], suffixes: list[str]) -> bool:
    return any(any(path.endswith(suffix) for suffix in suffixes) for path in paths)


def archive_existing(item_root: Path, relative_paths: list[str]) -> Path:
    archive_root = item_root / ".generation" / "archive" / datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_root.mkdir(parents=True, exist_ok=True)

    for relative_path in relative_paths:
        target = ROOT / relative_path
        if not target.exists():
            continue
        archive_target = archive_root / Path(relative_path).name
        ensure_parent(archive_target)
        shutil.copy2(target, archive_target)

    return archive_root


def write_artifacts(artifacts: dict[str, str]) -> list[Path]:
    written: list[Path] = []
    for relative_path, content in artifacts.items():
        target = ROOT / relative_path
        ensure_parent(target)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


def validate_bundle(
    cleanup_targets: list[str],
    artifacts: dict[str, str],
    work_item_level: str | None = None,
) -> list[str]:
    errors: list[str] = []
    cleanup_set = set(cleanup_targets)
    artifact_set = set(artifacts)

    if not cleanup_targets:
        errors.append("cleanup_targets 不能为空")
    if not artifacts:
        errors.append("artifacts 不能为空")

    required_groups = [
        ["inputs/requirement_summary.md"],
        ["inputs/source_manifest.json"],
        ["evidence/evidence_inventory.json"],
        ["structured_prd/structured_prd.json"],
        [
            "traceability/coverage_first_traceability.json",
            "traceability/traceability_matrix.json",
        ],
        ["testcases/case_plan.json"],
        ["testcases/testcases_main.md", "testcases/testcases.md"],
        ["reviews/review_record.md"],
    ]
    for suffixes in required_groups:
        if not has_artifact_with_suffix(artifact_set, suffixes):
            errors.append(f"artifacts 缺少必要产物: {' / '.join(suffixes)}")

    level = str(work_item_level or "").strip().upper()
    level_required_groups = [
        ["acceptance/testability_gate.json"],
        ["testcases/case_plan.json"],
    ]
    if level in {"M", "L"}:
        level_required_groups.append(["acceptance/acceptance_examples.json"])
    if level == "L":
        level_required_groups.extend(
            [
                ["design/verification_responsibility_map.json"],
                ["design/test_design_matrix.json"],
            ]
        )
    for suffixes in level_required_groups:
        if not has_artifact_with_suffix(artifact_set, suffixes):
            errors.append(
                f"{level or 'default'} 档 bundle 缺少设计层产物: {' / '.join(suffixes)}"
            )

    derived_suffixes = {
        "feishu_ready.md",
        "structured_prd/structured_prd.md",
        "traceability/coverage_first_traceability.json",
        "traceability/traceability_adapter.json",
        "testcases/testpoints.md",
        "testcases/testpoints.json",
    }
    missing_artifacts = sorted(
        path
        for path in cleanup_set
        if not any(path.endswith(suffix) for suffix in derived_suffixes)
        and path not in artifact_set
    )
    for path in missing_artifacts:
        errors.append(f"cleanup_targets 中的产物未在 artifacts 中提供: {path}")

    return errors


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


def run_post_write_normalizers(item_root: Path) -> tuple[bool, str]:
    manifest = read_json(item_root / "manifest.json")
    project_code = str(manifest.get("project_code", "")).strip()
    work_item_id = str(manifest.get("work_item_id", "")).strip()
    structured_prd_md_path = item_root / "structured_prd" / "structured_prd.md"
    image_evidence_path = item_root / "image_evidence" / "image_evidence_inventory.json"
    structured_prd_path = item_root / "structured_prd" / "structured_prd.json"
    traceability_path = item_root / "traceability" / "traceability_matrix.json"
    main_testcases_path = item_root / "testcases" / "testcases_main.md"
    compat_testcases_path = item_root / "testcases" / "testcases.md"
    case_plan_path = item_root / "testcases" / "case_plan.json"
    testability_gate_path = item_root / "acceptance" / "testability_gate.json"
    testpoints_json_path = item_root / "testcases" / "testpoints.json"
    testpoints_md_path = item_root / "testcases" / "testpoints.md"
    testcase_bundle_path = item_root / "testcases" / "testcase_bundle.json"
    dev_self_testcases_path = item_root / "testcases" / "dev_self_testcases.md"
    coverage_first_traceability_path = item_root / "traceability" / "coverage_first_traceability.json"
    traceability_adapter_path = item_root / "traceability" / "traceability_adapter.json"

    commands: list[list[str]] = []
    if structured_prd_md_path.exists():
        commands.append(
            [
                sys.executable,
                str(ROOT / "scripts" / "compile_structured_prd_json.py"),
                "--input",
                str(structured_prd_md_path),
                "--output",
                str(structured_prd_path),
            ]
        )

    if image_evidence_path.exists() and structured_prd_path.exists() and traceability_path.exists():
        commands.extend(
            [
                [
                    sys.executable,
                    str(ROOT / "scripts" / "sync_modal_attributes_from_image_evidence.py"),
                    "--image-evidence",
                    str(image_evidence_path),
                    "--structured-prd",
                    str(structured_prd_path),
                    "--write",
                ],
                [
                    sys.executable,
                    str(ROOT / "scripts" / "expand_backend_field_traceability.py"),
                    "--structured-prd",
                    str(structured_prd_path),
                    "--traceability",
                    str(traceability_path),
                    "--write",
                ],
            ]
        )
    if structured_prd_path.exists():
        commands.append(
            [
                sys.executable,
                str(ROOT / "scripts" / "render_structured_prd_markdown.py"),
                "--structured-prd",
                str(structured_prd_path),
                "--output",
                str(item_root / "structured_prd" / "structured_prd.md"),
            ]
        )

    if main_testcases_path.exists():
        compat_testcases_path.write_text(main_testcases_path.read_text(encoding="utf-8"), encoding="utf-8")
    elif compat_testcases_path.exists():
        main_testcases_path.write_text(compat_testcases_path.read_text(encoding="utf-8"), encoding="utf-8")

    testcase_source_path = main_testcases_path if main_testcases_path.exists() else compat_testcases_path
    if case_plan_path.exists() and testcase_source_path.exists():
        commands.extend(
            [
                [
                    sys.executable,
                    str(ROOT / "skills" / "case-generation" / "scripts" / "generate_testpoints_view.py"),
                    "--project-code",
                    project_code,
                    "--work-item-id",
                    work_item_id,
                    "--case-plan",
                    str(case_plan_path),
                    "--testcases",
                    str(testcase_source_path),
                    "--json-output",
                    str(testpoints_json_path),
                    "--md-output",
                    str(testpoints_md_path),
                ],
                [
                    sys.executable,
                    str(ROOT / "skills" / "case-generation" / "scripts" / "validate_testpoints_view.py"),
                    "--input",
                    str(testpoints_json_path),
                    "--case-plan",
                    str(case_plan_path),
                    "--testability-gate",
                    str(testability_gate_path),
                ],
            ]
        )
    if testcase_source_path.exists():
        commands.append(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_dev_self_testcases.py"),
                "--testcases",
                str(testcase_source_path),
                "--output",
                str(dev_self_testcases_path),
            ]
        )
        commands.extend(
            [
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_testcase_bundle.py"),
                    "--project-code",
                    project_code,
                    "--work-item-id",
                    work_item_id,
                    "--testcases",
                    str(testcase_source_path),
                    "--output",
                    str(testcase_bundle_path),
                ],
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_testcase_bundle.py"),
                    "--input",
                    str(testcase_bundle_path),
                    "--testcases",
                    str(testcase_source_path),
                    "--case-plan",
                    str(case_plan_path),
                    "--project-code",
                    project_code,
                    "--work-item-id",
                    work_item_id,
                ],
            ]
        )
    coverage_matrix_path = item_root / "coverage" / "coverage_matrix.json"
    evidence_path = item_root / "evidence" / "evidence_inventory.json"
    if coverage_matrix_path.exists() and evidence_path.exists() and testcase_source_path.exists():
        commands.extend(
            [
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_coverage_first_traceability.py"),
                    "--coverage-matrix",
                    str(coverage_matrix_path),
                    "--evidence",
                    str(evidence_path),
                    "--testcases",
                    str(testcase_source_path),
                    "--output",
                    str(coverage_first_traceability_path),
                ],
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_traceability_adapter.py"),
                    "--input",
                    str(coverage_first_traceability_path),
                    "--output",
                    str(traceability_adapter_path),
                ],
            ]
        )
        if traceability_path.exists():
            commands.append(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "slim_legacy_traceability.py"),
                    "--structured-prd",
                    str(structured_prd_path),
                    "--testcases",
                    str(testcase_source_path),
                    "--traceability",
                    str(traceability_path),
                    "--write",
                ]
            )
        commands.append(
            [
                sys.executable,
                str(ROOT / "scripts" / "review_and_score_testcases.py"),
                "--project-code",
                project_code,
                "--work-item-id",
                work_item_id,
            ]
        )

    if not commands:
        return True, "缺少可执行的后处理输入，跳过 post_write_normalizers"

    outputs: list[str] = []
    for command in commands:
        ok, output = run_command(command)
        outputs.append(output)
        if not ok:
            return False, "\n".join(item for item in outputs if item)
    return True, "\n".join(item for item in outputs if item)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="执行工作项重生成 bundle，归档旧产物并写入新产物")
    parser.add_argument("--project-code", required=True, help="项目编码")
    parser.add_argument("--work-item-id", required=True, help="工作项 ID")
    parser.add_argument("--bundle", required=True, help="regeneration bundle JSON 路径")
    parser.add_argument("--skip-export", action="store_true", help="跳过 feishu 导出")
    parser.add_argument("--skip-validate", action="store_true", help="跳过 validate_work_item")
    parser.add_argument("--skip-code-reviews", action="store_true", help="执行 validate_work_item 时跳过代码评审产物校验")
    parser.add_argument("--strict", action="store_true", help="执行严格工作项校验")
    parser.add_argument("--skip-project-refresh", action="store_true", help="跳过项目索引与质量汇总刷新")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_code = normalize_code(args.project_code)
    work_item_id = normalize_code(args.work_item_id)
    item_root = resolve_work_item_root(project_code, work_item_id)
    bundle_path = Path(args.bundle).resolve()

    if not item_root.exists():
        print(f"工作项不存在: {item_root}", file=sys.stderr)
        return 1
    if not bundle_path.exists():
        print(f"bundle 不存在: {bundle_path}", file=sys.stderr)
        return 1

    bundle = read_json(bundle_path)
    cleanup_targets = bundle.get("cleanup_targets", [])
    artifacts = bundle.get("artifacts", {})
    work_item_level = str(bundle.get("work_item_level", "")).strip().upper()

    if not isinstance(cleanup_targets, list) or not isinstance(artifacts, dict):
        print("bundle 结构非法：缺少 cleanup_targets 或 artifacts", file=sys.stderr)
        return 1

    bundle_errors = validate_bundle(cleanup_targets, artifacts, work_item_level)
    if bundle_errors:
        print("bundle 校验失败:", file=sys.stderr)
        for error in bundle_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    archive_root = archive_existing(item_root, cleanup_targets)
    written = write_artifacts(artifacts)

    print(f"已归档旧产物: {archive_root}")
    print("已写入新产物:")
    for path in written:
        print(f"- {path}")

    ok, output = run_post_write_normalizers(item_root)
    print("\n[post_write_normalizers]")
    print(output)
    if not ok:
        return 1

    if not args.skip_export:
        ok, output = run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "export_feishu_ready.py"),
                "--project-code",
                project_code,
                "--work-item-id",
                work_item_id,
            ]
        )
        print("\n[export_feishu_ready]")
        print(output)
        if not ok:
            return 1

    if not args.skip_validate:
        validate_command = [
            sys.executable,
            str(ROOT / "scripts" / "validate_work_item.py"),
            "--project-code",
            project_code,
            "--work-item-id",
            work_item_id,
        ]
        if work_item_level in {"S", "M", "L"}:
            validate_command.extend(["--work-item-level", work_item_level])
        if args.strict:
            validate_command.append("--strict")
        if args.skip_code_reviews:
            validate_command.append("--skip-code-reviews")
        ok, output = run_command(validate_command)
        print("\n[validate_work_item]")
        print(output)
        if not ok:
            return 1

        project_manifest = (
            ROOT
            / "assets"
            / "projects"
            / project_code
            / "project_manifest.json"
        )
        if not args.skip_project_refresh and project_manifest.exists():
            ok, output = run_command(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "refresh_project_views.py"),
                    "--project-code",
                    project_code,
                ]
            )
            print("\n[refresh_project_views]")
            print(output)
            if not ok:
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
