from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.artifact_workspace import ArtifactWorkspaceError, ValidationResult, file_hash
from harness.diagnostics import normalize_validator_failure
from harness.generation_workspace import ControlledGenerationWorkspace
from harness.stage_registry import ROOT
from harness.stage_runner import write_diagnostics
from harness.state_store import atomic_write_json, display_path, fingerprint_files, utc_now


@dataclass(frozen=True)
class RoleSpec:
    role_id: str
    stage_id: str
    skill_path: str
    readable_prefixes: tuple[str, ...]
    readable_paths: tuple[str, ...]
    writable_paths: tuple[str, ...]


ROLE_SPECS = (
    RoleSpec(
        role_id="PRD Structurer",
        stage_id="prd_structurer",
        skill_path="skills/prd-structuring/SKILL.md",
        readable_prefixes=("inputs/", "image_evidence/", "analysis/", "evidence/"),
        readable_paths=(
            "manifest.json",
            "structured_prd/structured_prd.md",
            "structured_prd/structured_prd.json",
        ),
        writable_paths=(
            "evidence/evidence_inventory.json",
            "structured_prd/structured_prd.md",
            "structured_prd/structured_prd.json",
        ),
    ),
    RoleSpec(
        role_id="Case Generator",
        stage_id="case_generator",
        skill_path="skills/case-generation/SKILL.md",
        readable_prefixes=(
            "structured_prd/",
            "coverage/",
            "acceptance/",
            "design/",
            "traceability/",
        ),
        readable_paths=(
            "manifest.json",
            "testcases/case_plan.md",
            "testcases/case_plan.json",
            "testcases/testcases_main.md",
        ),
        writable_paths=(
            "testcases/testcases_main.md",
            "testcases/testpoints.md",
            "testcases/testpoints.json",
            "testcases/testcases.md",
            "testcases/field_audit.json",
            "testcases/grouped_audit.json",
            "testcases/testcase_bundle.json",
            "testcases/dev_self_testcases.md",
        ),
    ),
    RoleSpec(
        role_id="Case Reviewer",
        stage_id="case_reviewer",
        skill_path="skills/review-gate/SKILL.md",
        readable_prefixes=(
            "evidence/",
            "image_evidence/",
            "structured_prd/",
            "acceptance/",
            "design/",
            "testcases/",
            "traceability/",
            "reviews/",
        ),
        readable_paths=("manifest.json",),
        writable_paths=(
            "reviews/review_record.md",
            "reviews/missing_rules.json",
            "reviews/missing_fidelity_points.json",
            "reviews/fidelity_hit_locations.json",
            "reviews/duplicate_case_report.json",
            "reviews/weak_cases.json",
            "reviews/generalized_cases.json",
            "reviews/quality_report.json",
        ),
    ),
    RoleSpec(
        role_id="Asset Formatter",
        stage_id="asset_formatter",
        skill_path="skills/asset-formatter/SKILL.md",
        readable_prefixes=("structured_prd/", "testcases/", "reviews/"),
        readable_paths=("manifest.json", "feishu_ready.md"),
        writable_paths=("feishu_ready.md",),
    ),
)
ROLE_BY_STAGE = {spec.stage_id: spec for spec in ROLE_SPECS}


class MultiRoleArtifactWorkspace:
    def __init__(
        self,
        *,
        item_root: Path,
        run_dir: Path,
        project_code: str,
        work_item_id: str,
        work_item_level: str,
        base_bundle: dict[str, Any],
    ) -> None:
        self.item_root = item_root.resolve()
        self.run_dir = run_dir
        self.project_code = project_code
        self.work_item_id = work_item_id
        self.work_item_level = work_item_level.upper()
        self.staging_root = run_dir / "role_workspace" / "work_item"
        self.workspace_path = run_dir / "role_workspace.json"
        self.base_bundle_path = run_dir / "role_base_bundle.json"
        if self.work_item_level not in {"S", "M", "L"}:
            raise ArtifactWorkspaceError("work_item_level 必须为 S/M/L")
        if self.staging_root.exists():
            shutil.rmtree(self.staging_root)
        shutil.copytree(
            self.item_root,
            self.staging_root,
            ignore=lambda _directory, names: {".generation"}.intersection(names),
        )
        atomic_write_json(self.base_bundle_path, base_bundle)
        atomic_write_json(
            self.workspace_path,
            {
                "schema_version": "1.0.0",
                "staged_paths": [],
                "role_proposals": {},
                "role_validations": {},
                "created_at": utc_now(),
            },
        )

    def read_artifact(
        self,
        spec: RoleSpec,
        relative_path: str,
        max_chars: int = 200_000,
    ) -> dict[str, Any]:
        normalized = self._safe_relative(relative_path)
        if not self._is_readable(spec, normalized):
            raise ArtifactWorkspaceError(
                f"{spec.stage_id} 无权读取: {relative_path}"
            )
        path = self.staging_root / normalized
        if not path.is_file():
            raise ArtifactWorkspaceError(f"允许读取的产物不存在: {relative_path}")
        content = path.read_text(encoding="utf-8")
        return {
            "path": normalized,
            "content": content[:max_chars],
            "truncated": len(content) > max_chars,
            "sha256": file_hash(path),
        }

    def search_inputs(
        self,
        spec: RoleSpec,
        query: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        if spec.stage_id != "prd_structurer":
            raise ArtifactWorkspaceError(
                f"{spec.stage_id} 不允许 search_inputs；应读取已结构化上游产物"
            )
        normalized_query = query.strip()
        if not normalized_query:
            raise ArtifactWorkspaceError("search_inputs.query 不能为空")
        results: list[dict[str, Any]] = []
        inputs_root = self.staging_root / "inputs"
        for path in sorted(
            candidate for candidate in inputs_root.rglob("*") if candidate.is_file()
        ):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for line_number, line in enumerate(lines, start=1):
                if normalized_query.lower() not in line.lower():
                    continue
                results.append(
                    {
                        "path": str(path.relative_to(self.staging_root)),
                        "line": line_number,
                        "text": line.strip()[:500],
                    }
                )
                if len(results) >= max_results:
                    return results
        return results

    def propose_artifacts(
        self,
        spec: RoleSpec,
        artifacts: Any,
    ) -> dict[str, Any]:
        if not isinstance(artifacts, dict) or not artifacts:
            raise ArtifactWorkspaceError("propose_artifacts.artifacts 必须是非空 object")
        allowed = set(spec.writable_paths)
        normalized: dict[str, str] = {}
        for raw_path, raw_content in artifacts.items():
            path = self._safe_relative(str(raw_path))
            if path not in allowed:
                raise ArtifactWorkspaceError(
                    f"{spec.stage_id} 无权写入: {path}"
                )
            if isinstance(raw_content, (dict, list)):
                content = json.dumps(raw_content, ensure_ascii=False, indent=2) + "\n"
            elif isinstance(raw_content, str):
                content = raw_content
            else:
                raise ArtifactWorkspaceError(f"产物内容必须为 string/JSON: {path}")
            normalized[path] = content

        for path, content in normalized.items():
            target = self.staging_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        workspace = self._read_workspace()
        proposals = dict(workspace.get("role_proposals", {}))
        role_paths = set(proposals.get(spec.stage_id, []))
        role_paths.update(normalized)
        proposals[spec.stage_id] = sorted(role_paths)
        staged_paths = set(workspace.get("staged_paths", []))
        staged_paths.update(normalized)
        workspace["role_proposals"] = proposals
        workspace["staged_paths"] = sorted(staged_paths)
        workspace["updated_at"] = utc_now()
        atomic_write_json(self.workspace_path, workspace)
        return {
            "paths": sorted(normalized),
            "candidate_fingerprint": self.role_fingerprint(spec),
        }

    def validate_role(self, spec: RoleSpec) -> ValidationResult:
        workspace = self._read_workspace()
        role_paths = workspace.get("role_proposals", {}).get(spec.stage_id, [])
        if not role_paths:
            raise ArtifactWorkspaceError(
                f"{spec.stage_id} 尚未提交任何 staging 产物"
            )
        if spec.stage_id == "prd_structurer":
            required = {
                "structured_prd/structured_prd.md",
                "structured_prd/structured_prd.json",
            }
            missing = sorted(required - set(role_paths))
            if missing:
                raise ArtifactWorkspaceError(
                    "PRD Structurer 必须同步提交 Markdown authoring 真源和 JSON 投影: "
                    + ", ".join(missing)
                )
        validations = dict(workspace.get("role_validations", {}))
        previous = validations.get(spec.stage_id, {})
        attempt = int(previous.get("attempt", 0)) + 1
        precheck_error: str | None = None
        if spec.stage_id == "case_reviewer":
            try:
                self._validate_review_record()
            except ArtifactWorkspaceError as exc:
                precheck_error = str(exc)

        diagnostics: list[dict[str, Any]] = []
        output_parts: list[str] = []
        exit_code = 1 if precheck_error else 0
        if precheck_error:
            command = ["review_record_precheck"]
            output_parts.append(precheck_error)
            diagnostics.extend(
                normalize_validator_failure(
                    observed_stage_id=spec.stage_id,
                    command=command,
                    command_index=1,
                    exit_code=1,
                    output=precheck_error,
                    attempt=attempt,
                )
            )
        for index, command in enumerate(self._validator_commands(spec), start=1):
            result = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,
            )
            output = (result.stdout or "") + (
                ("\n" + result.stderr) if result.stderr else ""
            )
            output_parts.append(f"$ {' '.join(command)}\n{output}")
            if result.returncode != 0:
                exit_code = result.returncode
                diagnostics.extend(
                    normalize_validator_failure(
                        observed_stage_id=spec.stage_id,
                        command=command,
                        command_index=index,
                        exit_code=result.returncode,
                        output=output,
                        attempt=attempt,
                    )
                )
        if spec.stage_id == "prd_structurer" and exit_code == 0:
            staged_json = (
                self.staging_root / "structured_prd" / "structured_prd.json"
            )
            compiled_json = (
                self.run_dir
                / "role_workspace"
                / "compiled_structured_prd.json"
            )
            try:
                staged_payload = json.loads(staged_json.read_text(encoding="utf-8"))
                compiled_payload = json.loads(
                    compiled_json.read_text(encoding="utf-8")
                )
                if staged_payload != compiled_payload:
                    raise ArtifactWorkspaceError(
                        "structured_prd.md 编译结果与 staging JSON 不一致"
                    )
            except (OSError, json.JSONDecodeError, ArtifactWorkspaceError) as exc:
                exit_code = 1
                output = str(exc)
                output_parts.append(output)
                diagnostics.extend(
                    normalize_validator_failure(
                        observed_stage_id=spec.stage_id,
                        command=["compare_structured_prd_projection"],
                        command_index=len(self._validator_commands(spec)) + 1,
                        exit_code=1,
                        output=output,
                        attempt=attempt,
                    )
                )
        if spec.stage_id == "asset_formatter" and exit_code == 0:
            try:
                self.finalize_candidate()
            except Exception as exc:
                exit_code = 1
                output_parts.append(str(exc))
                diagnostics.extend(
                    normalize_validator_failure(
                        observed_stage_id=spec.stage_id,
                        command=["controlled_generation", "stage_and_validate"],
                        command_index=1,
                        exit_code=1,
                        output=str(exc),
                        attempt=attempt,
                    )
                )

        log_path = (
            self.run_dir
            / "logs"
            / f"{spec.stage_id}-validation-{attempt}.log"
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(output_parts), encoding="utf-8")
        diagnostic_path = write_diagnostics(
            self.run_dir,
            spec.stage_id,
            attempt,
            tuple(diagnostics),
        )
        fingerprint = self.role_fingerprint(spec)
        validations[spec.stage_id] = {
            "attempt": attempt,
            "passed": exit_code == 0,
            "fingerprint": fingerprint,
            "validated_at": utc_now(),
        }
        workspace["role_validations"] = validations
        workspace["updated_at"] = utc_now()
        atomic_write_json(self.workspace_path, workspace)
        return ValidationResult(
            passed=exit_code == 0,
            attempt=attempt,
            exit_code=exit_code,
            log_path=display_path(log_path),
            diagnostic_path=diagnostic_path,
            diagnostics=tuple(diagnostics),
        )

    def assert_role_validated(self, spec: RoleSpec) -> str:
        validation = self._read_workspace().get("role_validations", {}).get(
            spec.stage_id,
            {},
        )
        if not validation.get("passed"):
            raise ArtifactWorkspaceError(
                f"{spec.stage_id} staging 尚未通过 Validator"
            )
        fingerprint = self.role_fingerprint(spec)
        if fingerprint != validation.get("fingerprint"):
            raise ArtifactWorkspaceError(
                f"{spec.stage_id} staging 在校验后发生漂移"
            )
        return fingerprint

    def finalize_candidate(self) -> dict[str, Any]:
        bundle = json.loads(self.base_bundle_path.read_text(encoding="utf-8"))
        artifacts = dict(bundle.get("artifacts", {}))
        prefix = (
            f"assets/projects/{self.project_code}/work_items/"
            f"{self.work_item_id}/"
        )
        for relative in self._read_workspace().get("staged_paths", []):
            artifacts[prefix + relative] = (
                self.staging_root / relative
            ).read_text(encoding="utf-8")
        bundle["artifacts"] = artifacts
        bundle["provider"] = "multi_role"
        bundle["work_item_level"] = self.work_item_level
        workspace = self.generation_workspace()
        return workspace.stage_and_validate(
            run_id=self.run_dir.name,
            provider="multi_role",
            bundle=bundle,
        )

    def generation_workspace(self) -> ControlledGenerationWorkspace:
        return ControlledGenerationWorkspace(
            item_root=self.item_root,
            run_dir=self.run_dir,
            project_code=self.project_code,
            work_item_id=self.work_item_id,
            work_item_level=self.work_item_level,
        )

    def role_fingerprint(self, spec: RoleSpec) -> str:
        workspace = self._read_workspace()
        paths = tuple(
            workspace.get("role_proposals", {}).get(spec.stage_id, [])
        )
        if not paths:
            return hashlib.sha256(b"").hexdigest()
        return fingerprint_files(self.staging_root, paths)

    def staged_paths(self) -> list[str]:
        return list(self._read_workspace().get("staged_paths", []))

    def _validator_commands(self, spec: RoleSpec) -> list[list[str]]:
        staged = self.staging_root
        if spec.stage_id == "prd_structurer":
            return [
                [
                    sys.executable,
                    str(ROOT / "scripts" / "compile_structured_prd_json.py"),
                    "--input",
                    str(staged / "structured_prd" / "structured_prd.md"),
                    "--output",
                    str(
                        self.run_dir
                        / "role_workspace"
                        / "compiled_structured_prd.json"
                    ),
                ],
                [
                    sys.executable,
                    str(
                        ROOT
                        / "skills"
                        / "prd-structuring"
                        / "scripts"
                        / "validate_structured_prd.py"
                    ),
                    "--input",
                    str(staged / "structured_prd" / "structured_prd.json"),
                    "--schema",
                    str(ROOT / "schemas" / "structured_prd.schema.json"),
                ]
            ]
        if spec.stage_id == "case_generator":
            testcase = staged / "testcases" / "testcases_main.md"
            commands = [
                [
                    sys.executable,
                    str(
                        ROOT
                        / "skills"
                        / "case-generation"
                        / "scripts"
                        / "testcase_lint.py"
                    ),
                    "--input",
                    str(testcase),
                ],
                [
                    sys.executable,
                    str(
                        ROOT
                        / "skills"
                        / "case-generation"
                        / "scripts"
                        / "validate_testcase_grouping.py"
                    ),
                    "--input",
                    str(testcase),
                    "--strict",
                ],
                [
                    sys.executable,
                    str(
                        ROOT
                        / "skills"
                        / "case-generation"
                        / "scripts"
                        / "testcase_element_lint.py"
                    ),
                    "--input",
                    str(testcase),
                    "--strict",
                ],
                [
                    sys.executable,
                    str(
                        ROOT
                        / "skills"
                        / "case-generation"
                        / "scripts"
                        / "validate_testpoints_view.py"
                    ),
                    "--input",
                    str(staged / "testcases" / "testpoints.json"),
                    "--case-plan",
                    str(staged / "testcases" / "case_plan.json"),
                    "--testability-gate",
                    str(staged / "acceptance" / "testability_gate.json"),
                    "--strict",
                ],
            ]
            case_plan_command = [
                sys.executable,
                str(
                    ROOT
                    / "skills"
                    / "case-generation"
                    / "scripts"
                    / "validate_case_plan.py"
                ),
                "--input",
                str(staged / "testcases" / "case_plan.json"),
                "--testability-gate",
                str(staged / "acceptance" / "testability_gate.json"),
                "--testcases",
                str(testcase),
            ]
            if self.work_item_level in {"M", "L"}:
                case_plan_command.extend(
                    [
                        "--acceptance-examples",
                        str(staged / "acceptance" / "acceptance_examples.json"),
                        "--require-examples",
                    ]
                )
            if self.work_item_level == "L":
                case_plan_command.extend(
                    [
                        "--responsibility-map",
                        str(
                            staged
                            / "design"
                            / "verification_responsibility_map.json"
                        ),
                        "--require-responsibilities",
                    ]
                )
            commands.append(case_plan_command)
            return commands
        if spec.stage_id == "case_reviewer":
            return [
                [
                    sys.executable,
                    str(ROOT / "skills" / "review-gate" / "scripts" / "review_gate.py"),
                    "--structured-prd",
                    str(staged / "structured_prd" / "structured_prd.json"),
                    "--testcases",
                    str(staged / "testcases" / "testcases_main.md"),
                    "--checklist",
                    str(
                        ROOT
                        / "skills"
                        / "review-gate"
                        / "checklists"
                        / "manual_review_checklist.md"
                    ),
                ]
            ]
        return []

    def _validate_review_record(self) -> None:
        path = self.staging_root / "reviews" / "review_record.md"
        if not path.is_file():
            raise ArtifactWorkspaceError("Case Reviewer 缺少 reviews/review_record.md")
        content = path.read_text(encoding="utf-8")
        if "评审结论" not in content or "问题清单" not in content:
            raise ArtifactWorkspaceError(
                "review_record.md 缺少“评审结论”或“问题清单”"
            )
        upper = content.upper()
        if "TEMPLATE" in upper or "TODO" in upper:
            raise ArtifactWorkspaceError("review_record.md 仍包含模板占位内容")

    @staticmethod
    def _safe_relative(raw: str) -> str:
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ArtifactWorkspaceError(f"非法工作项相对路径: {raw!r}")
        return path.as_posix()

    @staticmethod
    def _is_readable(spec: RoleSpec, relative: str) -> bool:
        return relative in spec.readable_paths or relative in spec.writable_paths or any(
            relative.startswith(prefix) for prefix in spec.readable_prefixes
        )

    def _read_workspace(self) -> dict[str, Any]:
        return json.loads(self.workspace_path.read_text(encoding="utf-8"))
