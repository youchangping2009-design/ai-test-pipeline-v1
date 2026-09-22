#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_work_item.py

用途：
针对单个工作项执行统一校验，适用于：

assets/projects/<project_code>/work_items/<work_item_id>/

校验内容包括：
1. structured_prd 校验
2. evidence_inventory / traceability_matrix 校验
3. testcase 校验
4. review_gate 校验
5. review_record 文件存在性检查
6. manifest.json 文件存在性检查

推荐用法：

1. 最简方式
python scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id WX-YYPT-REQ-001

2. 跳过 testcase 校验
python scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id WX-YYPT-REQ-001 \
  --skip-testcases

3. 显式指定 schema
python scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id WX-YYPT-REQ-001 \
  --schema schemas/structured_prd.schema.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from backend_config_utils import has_backend_config_family_pages
from build_dev_self_testcases import build_dev_self_markdown
from harness.contracts import ContractError, validate_named
from harness.requirement_approval import validate_requirement_approval
from quality_gate_policy import resolve_rollout_source
from work_item_policy import VALID_WORK_ITEM_LEVELS
from work_item_policy import resolve_work_item_level


def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def resolve_level_policy(work_item_level: str, strict: bool) -> dict:
    if not strict:
        return {
            "required_design_artifacts": [],
            "case_plan_requires_examples": False,
            "case_plan_requires_responsibilities": False,
            "notes": ["non-strict 兼容旧流程，不强制测试设计决策层产物"],
        }
    if work_item_level == "S":
        return {
            "required_design_artifacts": ["testability_gate", "case_plan"],
            "case_plan_requires_examples": False,
            "case_plan_requires_responsibilities": False,
            "notes": ["S strict 不强制 acceptance_examples / verification_responsibility_map"],
        }
    if work_item_level == "L":
        return {
            "required_design_artifacts": [
                "testability_gate",
                "acceptance_examples",
                "verification_responsibility_map",
                "test_design_matrix",
                "case_plan",
            ],
            "case_plan_requires_examples": True,
            "case_plan_requires_responsibilities": True,
            "notes": ["L strict 强制验收示例、责任划分与测试设计矩阵"],
        }
    return {
        "required_design_artifacts": ["testability_gate", "acceptance_examples", "case_plan"],
        "case_plan_requires_examples": True,
        "case_plan_requires_responsibilities": False,
        "notes": ["M strict 强制 acceptance_examples，并要求 case_plan 追溯到 example"],
    }


def get_repo_root() -> Path:
    """
    当前脚本路径预期为：
    scripts/validate_work_item.py
    """
    return Path(__file__).resolve().parents[1]


def normalize_project_code(project_code: str) -> str:
    return project_code.strip().upper()


def normalize_work_item_id(work_item_id: str) -> str:
    value = work_item_id.strip().upper().replace(" ", "-")
    value = re.sub(r"-{2,}", "-", value)
    return value


def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def source_manifest_requires_image_evidence(source_manifest_path: Path) -> bool:
    """Return whether an available requirement source is explicitly an image.

    Missing or unreadable manifests keep the legacy strict behaviour. Their own
    validation will report the malformed source manifest separately.
    """
    if not source_manifest_path.exists():
        return True
    try:
        payload = read_json(source_manifest_path)
    except Exception:
        return True
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return True
    return any(
        isinstance(source, dict)
        and source.get("source_type") == "image"
        and source.get("status") == "available"
        for source in sources
    )


def image_evidence_contains_images(image_evidence_path: Path) -> bool:
    """Keep validating populated inventories even if source metadata is stale."""
    try:
        payload = read_json(image_evidence_path)
    except Exception:
        return True
    images = payload.get("images")
    return not isinstance(images, list) or bool(images)


def should_run_backend_config_chain(image_evidence_path: Path) -> bool:
    if not image_evidence_path.exists():
        return False
    try:
        return has_backend_config_family_pages(read_json(image_evidence_path))
    except Exception:
        return False


def run_subprocess(command: List[str]) -> Tuple[int, str]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        if output:
            output += "\n"
        output += result.stderr
    return result.returncode, output.strip()


def resolve_schema_path(repo_root: Path, user_schema: Optional[str]) -> Path:
    if user_schema:
        return Path(user_schema).resolve()

    primary = repo_root / "schemas" / "structured_prd.schema.json"
    if primary.exists():
        return primary

    fallback = (
        repo_root
        / "skills"
        / "prd-structuring"
        / "schema"
        / "structured_prd.schema.json"
    )
    return fallback


def resolve_work_item_root(repo_root: Path, project_code: str, work_item_id: str) -> Path:
    return repo_root / "assets" / "projects" / project_code / "work_items" / work_item_id


def check_file_exists(path: Path, label: str) -> Tuple[bool, str]:
    if path.exists():
        return True, f"✅ {label} 存在: {path}"
    return False, f"❌ {label} 不存在: {path}"


def validate_manifest(manifest_path: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not manifest_path.exists():
        return False, [f"manifest.json 不存在: {manifest_path}"]

    try:
        data = read_json(manifest_path)
    except Exception as exc:
        return False, [f"manifest.json 读取失败: {exc}"]
    try:
        validate_named(data, "work_item_manifest.schema.json")
    except ContractError as exc:
        errors.append(f"manifest.json Schema 校验失败: {exc}")

    required_fields = [
        "project_code",
        "work_item_id",
        "title",
        "requirement_version",
        "created_at",
        "status",
        "artifacts",
    ]
    for field in required_fields:
        if field not in data:
            errors.append(f"manifest.json 缺少字段: {field}")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("manifest.json 中 artifacts 必须为对象")
    else:
        for field in ["inputs", "structured_prd", "testcases", "reviews"]:
            if field not in artifacts:
                errors.append(f"manifest.json.artifacts 缺少字段: {field}")

    return len(errors) == 0, errors


def validate_review_record(review_record_path: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not review_record_path.exists():
        return False, [f"review_record.md 不存在: {review_record_path}"]

    try:
        content = review_record_path.read_text(encoding="utf-8")
    except Exception as exc:
        return False, [f"review_record.md 读取失败: {exc}"]

    required_keywords = [
        "评审结论",
        "问题清单",
    ]
    for keyword in required_keywords:
        if keyword not in content:
            errors.append(f"review_record.md 缺少关键章节: {keyword}")

    return len(errors) == 0, errors


def validate_code_review_assets(
    repo_root: Path,
    frontend_review_path: Path,
    frontend_confirmation_path: Path,
    backend_review_path: Path,
    backend_confirmation_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "scripts" / "validate_code_review_assets.py"
    if not script_path.exists():
        return False, f"code review 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--frontend-review",
        str(frontend_review_path),
        "--frontend-confirmation",
        str(frontend_confirmation_path),
        "--backend-review",
        str(backend_review_path),
        "--backend-confirmation",
        str(backend_confirmation_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_code_review_scope(repo_root: Path, scope_path: Path, request_paths: list[Path]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    schema_path = repo_root / "schemas" / "code_review_scope.schema.json"
    if not scope_path.exists():
        return False, [f"code_review_scope.json 不存在: {scope_path}"]
    try:
        scope = read_json(scope_path)
        schema = read_json(schema_path)
    except Exception as exc:
        return False, [f"读取 code review scope/schema 失败: {exc}"]

    required_fields = schema.get("required", [])
    for field in required_fields:
        if field not in scope:
            errors.append(f"code_review_scope.json 缺少字段: {field}")

    for request_path in request_paths:
        if not request_path.exists():
            errors.append(f"code review request 文件不存在: {request_path}")

    return len(errors) == 0, errors


def validate_structured_prd(
    repo_root: Path,
    structured_prd_path: Path,
    schema_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "prd-structuring" / "scripts" / "validate_structured_prd.py"
    if not script_path.exists():
        return False, f"structured_prd 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(structured_prd_path),
        "--schema",
        str(schema_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_testcases(
    repo_root: Path,
    testcase_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "case-generation" / "scripts" / "testcase_lint.py"
    if not script_path.exists():
        return False, f"testcase lint 脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(testcase_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_testcase_element_notation(
    repo_root: Path,
    testcase_path: Path,
    strict: bool,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "case-generation" / "scripts" / "testcase_element_lint.py"
    if not script_path.exists():
        return False, f"testcase element lint 脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(testcase_path),
    ]
    if strict:
        command.append("--strict")
    code, output = run_subprocess(command)
    return code == 0, output


def validate_testcase_grouping(
    repo_root: Path,
    testcase_path: Path,
    strict: bool,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "case-generation" / "scripts" / "validate_testcase_grouping.py"
    if not script_path.exists():
        return False, f"testcase grouping 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(testcase_path),
    ]
    if strict:
        command.append("--strict")
    code, output = run_subprocess(command)
    return code == 0, output


def validate_testcase_bundle(
    repo_root: Path,
    testcase_bundle_path: Path,
    testcase_path: Path,
    case_plan_path: Path,
    project_code: str,
    work_item_id: str,
) -> Tuple[bool, str]:
    script_path = repo_root / "scripts" / "validate_testcase_bundle.py"
    if not script_path.exists():
        return False, f"testcase_bundle 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(testcase_bundle_path),
        "--testcases",
        str(testcase_path),
        "--case-plan",
        str(case_plan_path),
        "--project-code",
        project_code,
        "--work-item-id",
        work_item_id,
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_testpoints_view(
    repo_root: Path,
    testpoints_path: Path,
    case_plan_path: Path,
    testability_gate_path: Path,
    strict: bool,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "case-generation" / "scripts" / "validate_testpoints_view.py"
    if not script_path.exists():
        return False, f"testpoints 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(testpoints_path),
        "--case-plan",
        str(case_plan_path),
    ]
    if testability_gate_path.exists():
        command.extend(["--testability-gate", str(testability_gate_path)])
    if strict:
        command.append("--strict")
    code, output = run_subprocess(command)
    return code == 0, output


def validate_requirement_sources(
    repo_root: Path,
    source_manifest_path: Path,
    strict: bool,
) -> Tuple[bool, str]:
    script_path = (
        repo_root
        / "skills"
        / "requirement-summary"
        / "scripts"
        / "validate_requirement_sources.py"
    )
    if not script_path.exists():
        return False, f"requirement source 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(source_manifest_path),
    ]
    if strict:
        command.append("--strict")
    code, output = run_subprocess(command)
    return code == 0, output


def validate_dev_self_testcases(
    testcase_path: Path,
    dev_self_testcases_path: Path,
    required: bool = False,
) -> Tuple[bool, str]:
    if not dev_self_testcases_path.exists():
        if required:
            return False, f"strict 要求 dev_self_testcases 存在: {dev_self_testcases_path}"
        return True, f"dev_self_testcases 不存在，跳过一致性校验: {dev_self_testcases_path}"
    try:
        expected_markdown, expected_count = build_dev_self_markdown(testcase_path)
        actual_markdown = dev_self_testcases_path.read_text(encoding="utf-8")
    except Exception as exc:
        return False, f"dev_self_testcases 派生校验失败: {exc}"
    if actual_markdown != expected_markdown:
        return False, "dev_self_testcases.md 与 testcases_main.md 中 `开发必测` 标签过滤结果不一致"
    return True, f"✅ dev_self_testcases 校验通过，case_count: {expected_count}"


def validate_testability_gate(
    repo_root: Path,
    testability_gate_path: Path,
    structured_prd_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "testability-gate" / "scripts" / "validate_testability_gate.py"
    if not script_path.exists():
        return False, f"testability_gate 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(testability_gate_path),
        "--structured-prd",
        str(structured_prd_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_case_plan(
    repo_root: Path,
    case_plan_path: Path,
    testability_gate_path: Path,
    acceptance_examples_path: Optional[Path],
    responsibility_map_path: Optional[Path],
    testcase_path: Path,
    require_examples: bool,
    require_responsibilities: bool,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "case-generation" / "scripts" / "validate_case_plan.py"
    if not script_path.exists():
        return False, f"case_plan 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(case_plan_path),
        "--testability-gate",
        str(testability_gate_path),
        "--testcases",
        str(testcase_path),
    ]
    if acceptance_examples_path is not None:
        command.extend(["--acceptance-examples", str(acceptance_examples_path)])
    if responsibility_map_path is not None:
        command.extend(["--responsibility-map", str(responsibility_map_path)])
    if require_examples:
        command.append("--require-examples")
    if require_responsibilities:
        command.append("--require-responsibilities")
    code, output = run_subprocess(command)
    return code == 0, output


def validate_responsibility_map(
    repo_root: Path,
    responsibility_map_path: Path,
    case_plan_path: Path,
    testability_gate_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "test-design" / "scripts" / "validate_responsibility_map.py"
    if not script_path.exists():
        return False, f"verification_responsibility_map 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(responsibility_map_path),
        "--case-plan",
        str(case_plan_path),
        "--testability-gate",
        str(testability_gate_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_test_design_matrix(
    repo_root: Path,
    test_design_matrix_path: Path,
    testability_gate_path: Path,
    acceptance_examples_path: Path,
    responsibility_map_path: Path,
    case_plan_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "test-design" / "scripts" / "validate_test_design_matrix.py"
    if not script_path.exists():
        return False, f"test_design_matrix 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(test_design_matrix_path),
        "--testability-gate",
        str(testability_gate_path),
        "--acceptance-examples",
        str(acceptance_examples_path),
        "--responsibility-map",
        str(responsibility_map_path),
        "--case-plan",
        str(case_plan_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_design_feedback(
    repo_root: Path,
    design_feedback_path: Path,
    case_plan_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "test-design" / "scripts" / "validate_design_feedback.py"
    if not script_path.exists():
        return False, f"design_feedback 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(design_feedback_path),
        "--case-plan",
        str(case_plan_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_feedback_application(
    repo_root: Path,
    work_item_root: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "scripts" / "validate_feedback_application.py"
    if not script_path.exists():
        return False, f"feedback application 校验脚本不存在: {script_path}"
    code, output = run_subprocess(
        [sys.executable, str(script_path), "--item-root", str(work_item_root)]
    )
    return code == 0, output


def validate_feedback_action_journal(
    repo_root: Path,
    work_item_root: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "scripts" / "validate_feedback_action_journal.py"
    if not script_path.exists():
        return False, f"feedback action journal 校验脚本不存在: {script_path}"
    code, output = run_subprocess(
        [sys.executable, str(script_path), "--item-root", str(work_item_root)]
    )
    return code == 0, output


def validate_acceptance_examples(
    repo_root: Path,
    acceptance_examples_path: Path,
    testability_gate_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "acceptance-example" / "scripts" / "validate_acceptance_examples.py"
    if not script_path.exists():
        return False, f"acceptance_examples 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(acceptance_examples_path),
        "--testability-gate",
        str(testability_gate_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_traceability_assets(
    repo_root: Path,
    evidence_path: Path,
    traceability_path: Optional[Path],
    structured_prd_path: Path,
    testcase_path: Path,
    coverage_matrix_path: Optional[Path] = None,
    coverage_first_traceability_path: Optional[Path] = None,
    traceability_adapter_path: Optional[Path] = None,
    primary_only: bool = False,
) -> Tuple[bool, str]:
    script_path = repo_root / "scripts" / "validate_traceability_assets.py"
    if not script_path.exists():
        return False, f"traceability 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--evidence",
        str(evidence_path),
        "--structured-prd",
        str(structured_prd_path),
        "--testcases",
        str(testcase_path),
    ]
    if traceability_path is not None and traceability_path.exists():
        command.extend(["--traceability", str(traceability_path)])
    if primary_only:
        command.append("--primary-only")
    if coverage_matrix_path and coverage_matrix_path.exists():
        command.extend(["--coverage-matrix", str(coverage_matrix_path)])
    if coverage_first_traceability_path and coverage_first_traceability_path.exists():
        command.extend(["--coverage-first-traceability", str(coverage_first_traceability_path)])
    if traceability_adapter_path and traceability_adapter_path.exists():
        command.extend(["--traceability-adapter", str(traceability_adapter_path)])
    code, output = run_subprocess(command)
    return code == 0, output


def run_quality_report(
    repo_root: Path,
    project_code: str,
    work_item_id: str,
) -> Tuple[bool, str]:
    script_path = repo_root / "scripts" / "review_and_score_testcases.py"
    if not script_path.exists():
        return False, f"quality report 脚本不存在: {script_path}"
    command = [
        sys.executable,
        str(script_path),
        "--project-code",
        project_code,
        "--work-item-id",
        work_item_id,
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def read_existing_quality_report(
    quality_report_path: Path,
    source_paths: dict[str, Path],
) -> Tuple[bool, str]:
    if not quality_report_path.exists():
        return False, f"quality_report.json 不存在: {quality_report_path}"
    try:
        report = read_json(quality_report_path)
    except Exception as exc:
        return False, f"quality_report.json 读取失败: {exc}"
    fingerprints = report.get("source_artifacts")
    if not isinstance(fingerprints, dict):
        return False, "quality_report.json 缺少 source_artifacts，无法证明报告与当前产物一致；请使用 --write-report 刷新"
    mismatches: list[str] = []
    for key, path in source_paths.items():
        record = fingerprints.get(key)
        if not isinstance(record, dict):
            mismatches.append(f"{key}: missing fingerprint")
            continue
        if not path.exists():
            mismatches.append(f"{key}: source missing")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if record.get("sha256") != actual:
            mismatches.append(f"{key}: sha256 changed")
    if mismatches:
        return False, "quality_report.json 已过期，请使用 --write-report 刷新：\n- " + "\n- ".join(mismatches)
    return True, f"只读模式：quality_report.json 与当前主产物指纹一致: {quality_report_path}"


def resolve_quality_gate_config(manifest_data: dict, work_item_id: str) -> dict:
    config = {
        "enabled": False,
        "mode": "soft",
        "rollout_source": "legacy_report_only",
    }
    manifest_gate = manifest_data.get("quality_gate")
    if isinstance(manifest_gate, dict):
        config["enabled"] = bool(manifest_gate.get("enabled", False))
        config["mode"] = str(manifest_gate.get("mode", "soft")).strip() or "soft"
        config["rollout_source"] = resolve_rollout_source(
            str(manifest_gate.get("rollout_source", "new_work_item")).strip() or "new_work_item",
            work_item_id,
        )
    config["rollout_source"] = resolve_rollout_source(config["rollout_source"], work_item_id)
    if config["rollout_source"] == "pt081_pilot":
        config["enabled"] = True
        config["mode"] = "soft"
    return config


def validate_image_evidence(repo_root: Path, image_evidence_path: Path) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "prd-image-evidence-extractor" / "scripts" / "validate_image_evidence.py"
    if not script_path.exists():
        return False, f"image_evidence 校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(image_evidence_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_image_evidence_mapping(
    repo_root: Path,
    image_evidence_path: Path,
    structured_prd_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "scripts" / "validate_image_evidence_mapping.py"
    if not script_path.exists():
        return False, f"image evidence 映射校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--image-evidence",
        str(image_evidence_path),
        "--structured-prd",
        str(structured_prd_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_backend_config_chain(
    repo_root: Path,
    image_evidence_path: Path,
    evidence_path: Path,
    structured_prd_path: Path,
    testcase_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "scripts" / "validate_backend_config_chain.py"
    if not script_path.exists():
        return False, f"后台配置页链路校验脚本不存在: {script_path}"

    command = [
        sys.executable,
        str(script_path),
        "--image-evidence",
        str(image_evidence_path),
        "--evidence",
        str(evidence_path),
        "--structured-prd",
        str(structured_prd_path),
        "--testcases",
        str(testcase_path),
    ]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_review_gate(
    repo_root: Path,
    image_evidence_path: Optional[Path],
    evidence_path: Optional[Path],
    structured_prd_path: Optional[Path],
    traceability_path: Optional[Path],
    schema_path: Optional[Path],
    testcase_path: Optional[Path],
    checklist_path: Optional[Path],
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "review-gate" / "scripts" / "review_gate.py"
    if not script_path.exists():
        return False, f"review_gate 脚本不存在: {script_path}"

    command = [sys.executable, str(script_path)]

    if image_evidence_path:
        command.extend(["--image-evidence", str(image_evidence_path)])
    if evidence_path:
        command.extend(["--evidence", str(evidence_path)])
    if structured_prd_path:
        command.extend(["--structured-prd", str(structured_prd_path)])
    if traceability_path:
        command.extend(["--traceability", str(traceability_path)])
    if schema_path:
        command.extend(["--schema", str(schema_path)])
    if testcase_path:
        command.extend(["--testcases", str(testcase_path)])
    if checklist_path:
        command.extend(["--checklist", str(checklist_path)])

    code, output = run_subprocess(command)
    return code == 0, output


def should_run_review_gate(args: argparse.Namespace) -> Tuple[bool, str]:
    """
    review_gate 是总校验，依赖 structured_prd、testcases、checklist；
    traceability gate 额外依赖 evidence / traceability。
    当用户显式跳过这些前置项时，总控脚本应同步跳过 review_gate，
    避免出现“已跳过 testcase，但 review_gate 仍因缺少 testcase 失败”的契约冲突。
    """
    if args.skip_review_gate:
        return False, "用户显式跳过 review_gate"
    if args.skip_structured_prd:
        return False, "已跳过 structured_prd，review_gate 同步跳过"
    if args.skip_testcases:
        return False, "已跳过 testcases，review_gate 同步跳过"
    if args.skip_traceability:
        return False, "已跳过 traceability，review_gate 同步跳过"
    return True, ""


def should_run_code_review_gate(code_review_artifacts: Optional[dict], args: argparse.Namespace) -> Tuple[bool, str]:
    if args.skip_code_reviews:
        return False, "用户显式跳过 code review 校验"
    if not code_review_artifacts:
        return False, "manifest 未声明 code_reviews 产物"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="针对单个工作项执行统一校验")
    parser.add_argument(
        "--project-code",
        required=True,
        help="项目编码，如 WX-YYPT",
    )
    parser.add_argument(
        "--work-item-id",
        required=True,
        help="工作项 ID，如 WX-YYPT-REQ-001",
    )
    parser.add_argument(
        "--schema",
        required=False,
        help="显式指定 structured_prd schema 路径",
    )
    parser.add_argument(
        "--skip-structured-prd",
        action="store_true",
        help="跳过 structured_prd 校验",
    )
    parser.add_argument(
        "--skip-traceability",
        action="store_true",
        help="跳过 evidence_inventory / traceability_matrix 校验",
    )
    parser.add_argument(
        "--skip-testcases",
        action="store_true",
        help="跳过 testcase 校验",
    )
    parser.add_argument(
        "--skip-review-gate",
        action="store_true",
        help="跳过 review_gate 校验",
    )
    parser.add_argument(
        "--skip-code-reviews",
        action="store_true",
        help="跳过前后端代码评审产物检查",
    )
    parser.add_argument(
        "--skip-review-record",
        action="store_true",
        help="跳过 review_record.md 检查",
    )
    parser.add_argument(
        "--skip-manifest",
        action="store_true",
        help="跳过 manifest.json 检查",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="启用正式交付严格质量门，要求 testability_gate / case_plan 且 testcase 可追溯到 case_plan",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="显式刷新 reviews/quality_report.json；默认只读校验，不写任何报告产物",
    )
    parser.add_argument(
        "--work-item-level",
        choices=sorted(VALID_WORK_ITEM_LEVELS),
        default=None,
        help="显式覆盖 manifest.json 中的工作项复杂度级别；未指定时读取 manifest，缺失回退 M",
    )
    parser.add_argument(
        "--check-element-notation",
        action="store_true",
        help="启用测试用例元素统一标注检查；非 strict 仅 warning，strict 下明显未标注问题会失败",
    )
    parser.add_argument(
        "--retention",
        choices=["auto", "minimal", "full"],
        default="auto",
        help="产物保留策略；minimal 只要求主真源/主链产物，full 保持 legacy/兼容投影校验，auto 根据工作项现有产物自动选择",
    )
    args = parser.parse_args()

    project_code = normalize_project_code(args.project_code)
    work_item_id = normalize_work_item_id(args.work_item_id)
    repo_root = get_repo_root()
    schema_path = resolve_schema_path(repo_root, args.schema)

    work_item_root = resolve_work_item_root(repo_root, project_code, work_item_id)
    if not work_item_root.exists():
        print(
            f"工作项目录不存在: {work_item_root}\n"
            f"请先执行：python scripts/create_work_item.py --project-code {project_code} --work-item-id {work_item_id}",
            file=sys.stderr,
        )
        return 1

    structured_prd_path = work_item_root / "structured_prd" / "structured_prd.json"
    requirement_summary_path = work_item_root / "inputs" / "requirement_summary.md"
    source_manifest_path = work_item_root / "inputs" / "source_manifest.json"
    testability_gate_path = work_item_root / "acceptance" / "testability_gate.json"
    acceptance_examples_path = work_item_root / "acceptance" / "acceptance_examples.json"
    responsibility_map_path = work_item_root / "design" / "verification_responsibility_map.json"
    test_design_matrix_path = work_item_root / "design" / "test_design_matrix.json"
    design_feedback_path = work_item_root / "design" / "design_feedback.json"
    feedback_application_path = work_item_root / "design" / "feedback_application.json"
    case_plan_path = work_item_root / "testcases" / "case_plan.json"
    testpoints_path = work_item_root / "testcases" / "testpoints.json"
    testcase_bundle_path = work_item_root / "testcases" / "testcase_bundle.json"
    dev_self_testcases_path = work_item_root / "testcases" / "dev_self_testcases.md"
    coverage_matrix_path = work_item_root / "coverage" / "coverage_matrix.json"
    evidence_path = work_item_root / "evidence" / "evidence_inventory.json"
    image_evidence_path = None
    legacy_traceability_path = work_item_root / "traceability" / "traceability_matrix.json"
    coverage_first_traceability_path = work_item_root / "traceability" / "coverage_first_traceability.json"
    traceability_adapter_path = work_item_root / "traceability" / "traceability_adapter.json"
    testcase_path = (
        work_item_root / "testcases" / "testcases_main.md"
        if (work_item_root / "testcases" / "testcases_main.md").exists()
        else work_item_root / "testcases" / "testcases.md"
    )
    review_record_path = work_item_root / "reviews" / "review_record.md"
    quality_report_path = work_item_root / "reviews" / "quality_report.json"
    manifest_path = work_item_root / "manifest.json"
    checklist_path = repo_root / "skills" / "review-gate" / "checklists" / "manual_review_checklist.md"
    try:
        manifest_data = read_json(manifest_path) if manifest_path.exists() else {}
    except Exception:
        manifest_data = {}
    work_item_level, work_item_level_source = resolve_work_item_level(
        manifest_data,
        args.work_item_level,
    )
    element_notation_config = manifest_data.get("testcase_element_notation") if isinstance(manifest_data, dict) else None
    element_notation_enabled = args.check_element_notation or (
        isinstance(element_notation_config, dict) and bool(element_notation_config.get("enabled", False))
    )
    if isinstance(manifest_data.get("artifacts"), dict):
        image_evidence_raw = manifest_data.get("artifacts", {}).get("image_evidence")
        if image_evidence_raw:
            image_evidence_path = work_item_root / image_evidence_raw
    manifest_retention = manifest_data.get("artifact_retention") if isinstance(manifest_data, dict) else None
    manifest_retention_mode = ""
    if isinstance(manifest_retention, dict):
        manifest_retention_mode = str(manifest_retention.get("mode", "")).strip()
    if args.retention == "minimal":
        effective_retention = "minimal"
    elif args.retention == "full":
        effective_retention = "full"
    elif manifest_retention_mode in {"minimal", "full"}:
        effective_retention = manifest_retention_mode
    elif not legacy_traceability_path.exists() and coverage_first_traceability_path.exists():
        effective_retention = "minimal"
    else:
        effective_retention = "full"
    code_review_artifacts = manifest_data.get("artifacts", {}).get("code_reviews") if isinstance(manifest_data.get("artifacts"), dict) else None
    frontend_review_path = None
    frontend_confirmation_path = None
    backend_review_path = None
    backend_confirmation_path = None
    code_review_scope_path = None
    code_review_request_paths: list[Path] = []
    if isinstance(code_review_artifacts, dict):
        scope_raw = code_review_artifacts.get("scope")
        request_raw = code_review_artifacts.get("request")
        frontend_review_raw = code_review_artifacts.get("frontend_review")
        frontend_confirmation_raw = code_review_artifacts.get("frontend_confirmation")
        backend_review_raw = code_review_artifacts.get("backend_review")
        backend_confirmation_raw = code_review_artifacts.get("backend_confirmation")
        code_review_scope_path = work_item_root / scope_raw if scope_raw else None
        if request_raw:
            code_review_request_paths.append(work_item_root / request_raw)
        code_review_request_paths.extend(
            [
                work_item_root / "code_reviews" / "frontend_review_request.md",
                work_item_root / "code_reviews" / "backend_review_request.md",
            ]
        )
        frontend_review_path = work_item_root / frontend_review_raw if frontend_review_raw else None
        frontend_confirmation_path = work_item_root / frontend_confirmation_raw if frontend_confirmation_raw else None
        backend_review_path = work_item_root / backend_review_raw if backend_review_raw else None
        backend_confirmation_path = work_item_root / backend_confirmation_raw if backend_confirmation_raw else None

    overall_pass = True
    summary: List[str] = []

    print_section("Work Item Context")
    print(f"项目编码: {project_code}")
    print(f"工作项 ID: {work_item_id}")
    print(f"工作项目录: {work_item_root}")
    print(f"Schema: {schema_path}")
    print(f"工作项级别: {work_item_level}")
    print(f"工作项级别来源: {work_item_level_source}")
    if args.work_item_level and manifest_data.get("work_item_level") != work_item_level:
        print(f"- CLI 覆盖 manifest 工作项级别: {manifest_data.get('work_item_level', '(missing)')} -> {work_item_level}")
    requires_acceptance_examples = args.strict and work_item_level in {"M", "L"}
    requires_responsibility_map = args.strict and work_item_level == "L"
    requires_test_design_matrix = args.strict and work_item_level == "L"
    level_policy = resolve_level_policy(work_item_level, args.strict)
    print(f"Strict: {args.strict}")
    print(f"Level required design artifacts: {', '.join(level_policy['required_design_artifacts']) or '(none)'}")
    print(f"Case plan requires examples: {level_policy['case_plan_requires_examples']}")
    print(f"Case plan requires responsibilities: {level_policy['case_plan_requires_responsibilities']}")
    print(f"Element notation check: {element_notation_enabled}")
    print(f"Artifact retention: {effective_retention} (requested={args.retention})")
    for note in level_policy["notes"]:
        print(f"- {note}")

    print_section("File Existence Check")
    checks = [
        ("image_evidence", image_evidence_path, image_evidence_path is not None),
        ("requirement_summary", requirement_summary_path, args.strict or requirement_summary_path.exists()),
        ("source_manifest", source_manifest_path, args.strict or source_manifest_path.exists()),
        ("evidence", evidence_path, not args.skip_traceability),
        ("coverage_matrix", coverage_matrix_path, coverage_matrix_path.exists()),
        ("structured_prd", structured_prd_path, not args.skip_structured_prd),
        ("testability_gate", testability_gate_path, args.strict),
        ("acceptance_examples", acceptance_examples_path, requires_acceptance_examples),
        ("verification_responsibility_map", responsibility_map_path, requires_responsibility_map),
        ("test_design_matrix", test_design_matrix_path, requires_test_design_matrix),
        ("design_feedback", design_feedback_path, design_feedback_path.exists()),
        ("feedback_application", feedback_application_path, feedback_application_path.exists()),
        ("case_plan", case_plan_path, args.strict),
        ("testpoints", testpoints_path, args.strict or testpoints_path.exists()),
        ("testcase_bundle", testcase_bundle_path, testcase_bundle_path.exists()),
        ("dev_self_testcases", dev_self_testcases_path, dev_self_testcases_path.exists()),
        ("traceability_primary", coverage_first_traceability_path, (not args.skip_traceability and effective_retention == "minimal") or coverage_first_traceability_path.exists()),
        ("traceability_adapter", traceability_adapter_path, traceability_adapter_path.exists()),
        ("traceability_legacy", legacy_traceability_path, not args.skip_traceability and effective_retention == "full"),
        ("testcases", testcase_path, not args.skip_testcases),
        ("review_record", review_record_path, not args.skip_review_record),
        ("manifest", manifest_path, not args.skip_manifest),
        ("checklist", checklist_path, not args.skip_review_gate),
    ]
    if not args.skip_code_reviews and all([frontend_review_path, frontend_confirmation_path, backend_review_path, backend_confirmation_path]):
        checks.extend(
            [
                ("code_review_scope", code_review_scope_path, code_review_scope_path is not None),
                ("frontend_code_review", frontend_review_path, True),
                ("frontend_confirmation", frontend_confirmation_path, True),
                ("backend_code_review", backend_review_path, True),
                ("backend_confirmation", backend_confirmation_path, True),
            ]
        )
    for label, path, enabled in checks:
        if not enabled:
            print(f"- 跳过 {label} 检查")
            continue
        ok, msg = check_file_exists(path, label)
        print(msg)
        if not ok:
            overall_pass = False

    if not args.skip_manifest:
        print_section("Manifest Validation")
        ok, errors = validate_manifest(manifest_path)
        manifest_level = str(manifest_data.get("work_item_level", "")).strip().upper()
        if manifest_level and manifest_level not in {"S", "M", "L"}:
            errors.append(f"manifest.json.work_item_level 非法: {manifest_level}")
            ok = False
        if args.strict and not manifest_level:
            errors.append("strict 主流程要求 manifest.json 持久化 work_item_level")
            ok = False
        pipeline_policy = manifest_data.get("pipeline_policy")
        if args.strict:
            if not isinstance(pipeline_policy, dict):
                errors.append("strict 主流程要求 manifest.json.pipeline_policy")
                ok = False
            else:
                if pipeline_policy.get("requirement_intake_required") is not True:
                    errors.append("pipeline_policy.requirement_intake_required 必须为 true")
                    ok = False
                if pipeline_policy.get("testpoints_required") is not True:
                    errors.append("pipeline_policy.testpoints_required 必须为 true")
                    ok = False
        if ok:
            print("✅ manifest.json 校验通过")
            summary.append("Manifest: PASS")
        else:
            overall_pass = False
            print("❌ manifest.json 校验失败")
            for err in errors:
                print(err)
            summary.append(f"Manifest: FAIL ({len(errors)} 个问题)")

    if args.strict:
        print_section("Requirement Approval Validation")
        approval_errors = validate_requirement_approval(
            work_item_root,
            manifest_data,
        )
        if approval_errors:
            overall_pass = False
            print("❌ requirement approval 校验失败")
            for error in approval_errors:
                print(error)
            summary.append(
                f"Requirement Approval: FAIL ({len(approval_errors)} 个问题)"
            )
        else:
            print("✅ requirement approval 校验通过或 legacy policy 兼容跳过")
            summary.append("Requirement Approval: PASS")

    if source_manifest_path.exists():
        print_section("Requirement Source Manifest Validation")
        ok, output = validate_requirement_sources(repo_root, source_manifest_path, strict=args.strict)
        print(output if output else "(无输出)")
        summary.append(f"Requirement Sources: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    quality_gate_config = resolve_quality_gate_config(manifest_data, work_item_id)

    run_code_review_gate, code_review_skip_reason = should_run_code_review_gate(code_review_artifacts, args)
    if run_code_review_gate and all([frontend_review_path, frontend_confirmation_path, backend_review_path, backend_confirmation_path]):
        if code_review_scope_path is not None:
            print_section("Code Review Scope Validation")
            ok, errors = validate_code_review_scope(repo_root, code_review_scope_path, code_review_request_paths)
            if ok:
                print("✅ code review scope 检查通过")
                summary.append("Code Review Scope: PASS")
            else:
                overall_pass = False
                print("❌ code review scope 检查失败")
                for err in errors:
                    print(err)
                summary.append(f"Code Review Scope: FAIL ({len(errors)} 个问题)")
        print_section("Code Review Assets Validation")
        ok, output = validate_code_review_assets(
            repo_root=repo_root,
            frontend_review_path=frontend_review_path,
            frontend_confirmation_path=frontend_confirmation_path,
            backend_review_path=backend_review_path,
            backend_confirmation_path=backend_confirmation_path,
        )
        print(output if output else "(无输出)")
        summary.append(f"Code Reviews: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False
    else:
        print_section("Code Review Assets Validation")
        print(f"- 跳过 code review 校验：{code_review_skip_reason}")
        summary.append("Code Reviews: SKIPPED")

    if not args.skip_review_record:
        print_section("Review Record Validation")
        ok, errors = validate_review_record(review_record_path)
        if ok:
            print("✅ review_record.md 检查通过")
            summary.append("Review Record: PASS")
        else:
            overall_pass = False
            print("❌ review_record.md 检查失败")
            for err in errors:
                print(err)
            summary.append(f"Review Record: FAIL ({len(errors)} 个问题)")

    if not args.skip_structured_prd:
        print_section("Structured PRD Validation")
        ok, output = validate_structured_prd(repo_root, structured_prd_path, schema_path)
        print(output if output else "(无输出)")
        summary.append(f"Structured PRD: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if args.strict:
        print_section("Testability Gate Validation")
        ok, output = validate_testability_gate(repo_root, testability_gate_path, structured_prd_path)
        print(output if output else "(无输出)")
        summary.append(f"Testability Gate: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if requires_acceptance_examples:
        print_section("Acceptance Examples Validation")
        ok, output = validate_acceptance_examples(repo_root, acceptance_examples_path, testability_gate_path)
        print(output if output else "(无输出)")
        summary.append(f"Acceptance Examples: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if requires_responsibility_map:
        print_section("Verification Responsibility Map Validation")
        ok, output = validate_responsibility_map(repo_root, responsibility_map_path, case_plan_path, testability_gate_path)
        print(output if output else "(无输出)")
        summary.append(f"Verification Responsibility Map: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if requires_test_design_matrix:
        print_section("Test Design Matrix Validation")
        ok, output = validate_test_design_matrix(
            repo_root,
            test_design_matrix_path,
            testability_gate_path,
            acceptance_examples_path,
            responsibility_map_path,
            case_plan_path,
        )
        print(output if output else "(无输出)")
        summary.append(f"Test Design Matrix: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if design_feedback_path.exists():
        print_section("Design Feedback Validation")
        ok, output = validate_design_feedback(repo_root, design_feedback_path, case_plan_path)
        print(output if output else "(无输出)")
        summary.append(f"Design Feedback: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if design_feedback_path.exists():
        print_section("Feedback Application Validation")
        ok, output = validate_feedback_application(repo_root, work_item_root)
        print(output if output else "(无输出)")
        summary.append(f"Feedback Application: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

        print_section("Feedback Action Journal Validation")
        ok, output = validate_feedback_action_journal(repo_root, work_item_root)
        print(output if output else "(无输出)")
        summary.append(f"Feedback Action Journal: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    image_evidence_required = image_evidence_path is not None and (
        source_manifest_requires_image_evidence(source_manifest_path)
        or image_evidence_contains_images(image_evidence_path)
    )
    if image_evidence_required:
        print_section("Image Evidence Validation")
        ok, output = validate_image_evidence(repo_root, image_evidence_path)
        print(output if output else "(无输出)")
        summary.append(f"Image Evidence: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False
    elif image_evidence_path is not None:
        summary.append("Image Evidence: SKIPPED (no available image source)")

    if image_evidence_path is not None and not args.skip_structured_prd:
        print_section("Image Evidence Mapping Validation")
        ok, output = validate_image_evidence_mapping(repo_root, image_evidence_path, structured_prd_path)
        print(output if output else "(无输出)")
        summary.append(f"Image Evidence Mapping: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if not args.skip_traceability:
        print_section("Traceability Validation")
        primary_only_traceability = effective_retention == "minimal"
        ok, output = validate_traceability_assets(
            repo_root,
            evidence_path,
            None if primary_only_traceability else legacy_traceability_path,
            structured_prd_path,
            testcase_path,
            coverage_matrix_path=coverage_matrix_path,
            coverage_first_traceability_path=coverage_first_traceability_path,
            traceability_adapter_path=traceability_adapter_path if traceability_adapter_path.exists() else None,
            primary_only=primary_only_traceability,
        )
        print(output if output else "(无输出)")
        summary.append(f"Traceability: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if (
        image_evidence_path is not None
        and should_run_backend_config_chain(image_evidence_path)
        and not args.skip_structured_prd
        and not args.skip_traceability
        and not args.skip_testcases
    ):
        print_section("Backend Config Chain Validation")
        ok, output = validate_backend_config_chain(
            repo_root,
            image_evidence_path,
            evidence_path,
            structured_prd_path,
            testcase_path,
        )
        print(output if output else "(无输出)")
        summary.append(f"Backend Config Chain: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if not args.skip_testcases:
        print_section("Testcases Validation")
        ok, output = validate_testcases(repo_root, testcase_path)
        print(output if output else "(无输出)")
        summary.append(f"Testcases: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

        print_section("Testcase Grouping Validation")
        ok, output = validate_testcase_grouping(repo_root, testcase_path, strict=args.strict)
        print(output if output else "(无输出)")
        summary.append(f"Testcase Grouping: {'PASS' if ok else 'FAIL'}")
        if args.strict and not ok:
            overall_pass = False

        print_section("Developer Self-Test Projection Validation")
        ok, output = validate_dev_self_testcases(
            testcase_path,
            dev_self_testcases_path,
            required=args.strict,
        )
        print(output if output else "(无输出)")
        summary.append(f"Dev Self Testcases: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if not args.skip_testcases and element_notation_enabled:
        print_section("Testcase Element Notation Validation")
        ok, output = validate_testcase_element_notation(
            repo_root,
            testcase_path,
            strict=args.strict,
        )
        print(output if output else "(无输出)")
        summary.append(f"Element Notation: {'PASS' if ok else 'FAIL'}")
        if args.strict and not ok:
            overall_pass = False

    if not args.skip_testcases and testcase_bundle_path.exists():
        print_section("Testcase Bundle Projection Validation")
        ok, output = validate_testcase_bundle(
            repo_root,
            testcase_bundle_path,
            testcase_path,
            case_plan_path,
            project_code,
            work_item_id,
        )
        print(output if output else "(无输出)")
        summary.append(f"Testcase Bundle: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if not args.skip_testcases and testpoints_path.exists():
        print_section("Testpoints Projection Validation")
        ok, output = validate_testpoints_view(
            repo_root,
            testpoints_path,
            case_plan_path,
            testability_gate_path,
            strict=args.strict,
        )
        print(output if output else "(无输出)")
        summary.append(f"Testpoints: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if args.strict and not args.skip_testcases:
        print_section("Case Plan Validation")
        ok, output = validate_case_plan(
            repo_root,
            case_plan_path,
            testability_gate_path,
            acceptance_examples_path if requires_acceptance_examples else None,
            responsibility_map_path if requires_responsibility_map else None,
            testcase_path,
            require_examples=requires_acceptance_examples,
            require_responsibilities=requires_responsibility_map,
        )
        print(output if output else "(无输出)")
        summary.append(f"Case Plan: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if not args.skip_testcases and not args.skip_traceability:
        print_section("Quality Gate Evaluation")
        if args.write_report:
            ok, output = run_quality_report(repo_root, project_code, work_item_id)
        else:
            ok, output = read_existing_quality_report(
                quality_report_path,
                {
                    "structured_prd": structured_prd_path,
                    "coverage_matrix": coverage_matrix_path,
                    "testcases": testcase_path,
                    "coverage_first_traceability": coverage_first_traceability_path,
                },
            )
        print(output if output else "(无输出)")
        report = {}
        if quality_report_path.exists():
            try:
                report = read_json(quality_report_path)
            except Exception:
                report = {}
        gate = report.get("quality_gate", {}) if isinstance(report, dict) else {}
        gate_status = str(gate.get("status", "report_only")).strip() or "report_only"
        gate_enabled = bool(gate.get("enabled", False))
        warnings = gate.get("warnings", []) if isinstance(gate, dict) else []
        failures = gate.get("failures", []) if isinstance(gate, dict) else []
        traceability_metric_source = str(report.get("traceability_metric_source", "")).strip() if isinstance(report, dict) else ""
        primary_false_traceability_rate = report.get("false_traceability_rate_primary") if isinstance(report, dict) else None
        legacy_false_traceability_rate = report.get("false_traceability_rate_legacy") if isinstance(report, dict) else None
        if gate_enabled:
            print(f"- quality_gate: enabled ({gate.get('rollout_source', 'unknown')})")
        else:
            print(f"- quality_gate: report_only ({gate.get('rollout_source', quality_gate_config.get('rollout_source', 'unknown'))})")
        if traceability_metric_source:
            print(f"- traceability_metric_source: {traceability_metric_source}")
        if isinstance(primary_false_traceability_rate, (int, float)):
            print(f"- false_traceability_rate_primary: {round(float(primary_false_traceability_rate), 4)}")
        if isinstance(legacy_false_traceability_rate, (int, float)):
            print(f"- false_traceability_rate_legacy: {round(float(legacy_false_traceability_rate), 4)}")
        if isinstance(primary_false_traceability_rate, (int, float)) and isinstance(legacy_false_traceability_rate, (int, float)):
            delta = round(float(legacy_false_traceability_rate) - float(primary_false_traceability_rate), 4)
            print(f"- traceability_rate_delta(legacy-primary): {delta}")
        if warnings:
            print(f"- warnings: {len(warnings)}")
            for item in warnings:
                print(f"  warning[{item.get('metric', '')}]: {item.get('reason', '')} -> {item.get('artifact', '')}")
        if failures:
            print(f"- failures: {len(failures)}")
            for item in failures:
                print(f"  fail[{item.get('metric', '')}]: {item.get('reason', '')} -> {item.get('artifact', '')}")
        if gate_enabled and gate_status == "fail":
            overall_pass = False
            summary.append("Quality Gate: FAIL")
        elif gate_enabled and gate_status == "warning":
            summary.append("Quality Gate: WARNING")
        elif gate_enabled and gate_status == "pass":
            summary.append("Quality Gate: PASS")
        else:
            summary.append("Quality Gate: REPORT_ONLY")
        if isinstance(primary_false_traceability_rate, (int, float)) and isinstance(legacy_false_traceability_rate, (int, float)):
            primary_status = "FAIL" if gate_enabled and any(item.get("metric") in {"false_traceability_rate_primary", "traceability_metric_source"} for item in failures) else "PASS"
            legacy_threshold = 0.05
            legacy_status = "FAIL" if float(legacy_false_traceability_rate) > legacy_threshold else "PASS"
            summary.append(f"Traceability Primary: {primary_status} ({round(float(primary_false_traceability_rate), 4)})")
            summary.append(f"Traceability Legacy Compare: {legacy_status} ({round(float(legacy_false_traceability_rate), 4)})")
        if not ok:
            overall_pass = False
            summary.append("Quality Report Generation: FAIL")
    else:
        print_section("Quality Gate Evaluation")
        print("- 跳过 quality gate：依赖 testcase + traceability")
        summary.append("Quality Gate: SKIPPED")

    run_review_gate, review_gate_skip_reason = should_run_review_gate(args)
    if run_review_gate:
        print_section("Review Gate Validation")
        ok, output = validate_review_gate(
            repo_root=repo_root,
            image_evidence_path=image_evidence_path,
            evidence_path=None if args.skip_traceability or effective_retention == "minimal" else evidence_path,
            structured_prd_path=None if args.skip_structured_prd else structured_prd_path,
            traceability_path=None if args.skip_traceability or effective_retention == "minimal" else legacy_traceability_path,
            schema_path=schema_path,
            testcase_path=None if args.skip_testcases else testcase_path,
            checklist_path=checklist_path,
        )
        print(output if output else "(无输出)")
        summary.append(f"Review Gate: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False
    else:
        print_section("Review Gate Validation")
        print(f"- 跳过 review_gate：{review_gate_skip_reason}")
        summary.append("Review Gate: SKIPPED")

    print_section("Validate Work Item Summary")
    for item in summary:
        print(f"- {item}")

    if overall_pass:
        print("\n🎉 工作项校验通过")
        return 0

    print("\n🚫 工作项校验未通过")
    return 1


if __name__ == "__main__":
    sys.exit(main())
