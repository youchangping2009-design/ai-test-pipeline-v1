from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.diagnostics import normalize_validator_failure
from harness.contracts import validate_named
from harness.stage_runner import write_diagnostics
from harness.state_store import atomic_write_json, display_path, fingerprint_files, utc_now
from harness.stage_registry import ROOT


TARGET_RELATIVE_PATH = "testcases/case_plan.json"
READABLE_EXACT_PATHS = {
    "structured_prd/structured_prd.md",
    "structured_prd/structured_prd.json",
    "coverage/coverage_matrix.json",
    "acceptance/testability_gate.md",
    "acceptance/testability_gate.json",
    "acceptance/acceptance_examples.md",
    "acceptance/acceptance_examples.json",
    "design/verification_responsibility_map.md",
    "design/verification_responsibility_map.json",
    "design/test_design_matrix.md",
    "design/test_design_matrix.json",
    TARGET_RELATIVE_PATH,
}


class ArtifactWorkspaceError(RuntimeError):
    """Raised when an Agent action violates artifact boundaries."""


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    attempt: int
    exit_code: int
    log_path: str
    diagnostic_path: str | None
    diagnostics: tuple[dict[str, Any], ...]


def file_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CasePlanArtifactWorkspace:
    def __init__(
        self,
        item_root: Path,
        run_dir: Path,
        work_item_level: str,
    ) -> None:
        self.item_root = item_root.resolve()
        self.run_dir = run_dir
        self.work_item_level = work_item_level.upper()
        self.target_path = self.item_root / TARGET_RELATIVE_PATH
        self.staging_path = self.run_dir / "staging" / TARGET_RELATIVE_PATH
        self.manifest_path = self.run_dir / "staging" / "case_plan_workspace.json"
        self.commit_transaction_path = (
            self.run_dir / "case_plan_commit_transaction.json"
        )
        if self.work_item_level not in {"S", "M", "L"}:
            raise ArtifactWorkspaceError(
                f"work_item_level 必须是 S/M/L，实际: {work_item_level}"
            )
        if not self.manifest_path.exists():
            atomic_write_json(
                self.manifest_path,
                {
                    "schema_version": "1.0.0",
                    "target_path": TARGET_RELATIVE_PATH,
                    "expected_target_hash": file_hash(self.target_path),
                    "proposal_upstream_fingerprint": None,
                    "candidate_hash": None,
                    "validated_candidate_hash": None,
                    "validated_upstream_fingerprint": None,
                    "validation_status": "not_run",
                    "validation_attempts": 0,
                    "committed_at": None,
                },
            )

    def read_artifact(self, relative_path: str, max_chars: int = 200_000) -> dict[str, Any]:
        path = self._resolve_readable_path(relative_path)
        if not path.is_file():
            raise ArtifactWorkspaceError(f"允许读取的产物不存在: {relative_path}")
        content = path.read_text(encoding="utf-8")
        truncated = len(content) > max_chars
        return {
            "path": relative_path,
            "content": content[:max_chars],
            "truncated": truncated,
            "sha256": file_hash(path),
        }

    def search_inputs(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ArtifactWorkspaceError("search_inputs.query 不能为空")
        inputs_root = self.item_root / "inputs"
        results: list[dict[str, Any]] = []
        if not inputs_root.exists():
            return results
        for path in sorted(candidate for candidate in inputs_root.rglob("*") if candidate.is_file()):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for line_number, line in enumerate(lines, start=1):
                if normalized_query.lower() not in line.lower():
                    continue
                results.append(
                    {
                        "path": str(path.relative_to(self.item_root)),
                        "line": line_number,
                        "text": line.strip()[:500],
                    }
                )
                if len(results) >= max_results:
                    return results
        return results

    def propose_case_plan(self, content: Any) -> dict[str, Any]:
        if isinstance(content, str):
            try:
                payload = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ArtifactWorkspaceError(f"Case Plan 候选不是合法 JSON: {exc}") from exc
        else:
            payload = content
        if not isinstance(payload, dict):
            raise ArtifactWorkspaceError("Case Plan 候选必须是 JSON object")
        atomic_write_json(self.staging_path, payload)
        manifest = self._read_manifest()
        manifest.update(
            {
                "proposal_upstream_fingerprint": self.upstream_fingerprint(),
                "candidate_hash": file_hash(self.staging_path),
                "validated_candidate_hash": None,
                "validated_upstream_fingerprint": None,
                "validation_status": "not_run",
            }
        )
        atomic_write_json(self.manifest_path, manifest)
        return {
            "path": display_path(self.staging_path),
            "candidate_hash": manifest["candidate_hash"],
            "expected_target_hash": manifest["expected_target_hash"],
            "upstream_fingerprint": manifest["proposal_upstream_fingerprint"],
        }

    def validate_candidate(self) -> ValidationResult:
        if not self.staging_path.is_file():
            raise ArtifactWorkspaceError("尚未提交 Case Plan staging 候选")
        manifest = self._read_manifest()
        attempt = int(manifest.get("validation_attempts", 0)) + 1
        command = self._validator_command()
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
        log_path = self.run_dir / "logs" / f"case-plan-agent-validation-{attempt}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"$ {' '.join(command)}\n{output}\nexit_code: {result.returncode}\n",
            encoding="utf-8",
        )
        diagnostics = (
            ()
            if result.returncode == 0
            else normalize_validator_failure(
                observed_stage_id="case_plan",
                command=command,
                command_index=1,
                exit_code=result.returncode,
                output=output,
                attempt=attempt,
            )
        )
        diagnostic_path = write_diagnostics(
            self.run_dir,
            "case_plan",
            attempt,
            diagnostics,
        )
        candidate_hash = file_hash(self.staging_path)
        upstream_fingerprint = self.upstream_fingerprint()
        manifest.update(
            {
                "candidate_hash": candidate_hash,
                "validated_candidate_hash": candidate_hash,
                "validated_upstream_fingerprint": upstream_fingerprint,
                "validation_status": (
                    "passed" if result.returncode == 0 else "failed"
                ),
                "validation_attempts": attempt,
                "validated_at": utc_now(),
            }
        )
        atomic_write_json(self.manifest_path, manifest)
        return ValidationResult(
            passed=result.returncode == 0,
            attempt=attempt,
            exit_code=result.returncode,
            log_path=display_path(log_path),
            diagnostic_path=diagnostic_path,
            diagnostics=diagnostics,
        )

    def commit_validated_candidate(self) -> dict[str, Any]:
        transaction = self.prepare_commit(
            approval_id=f"{self.run_dir.name}-direct-commit",
            approved_by="direct-workspace-call",
        )
        return self.apply_commit(transaction)

    def prepare_commit(
        self,
        *,
        approval_id: str,
        approved_by: str,
    ) -> dict[str, Any]:
        self.assert_commit_ready()
        existing = self.read_commit_transaction()
        attempt = 1
        if existing is not None:
            if existing["approval_id"] != approval_id:
                raise ArtifactWorkspaceError(
                    "当前 run 已存在其他 approval 的 Case Plan commit transaction"
                )
            if existing["status"] in {"prepared", "committing"}:
                raise ArtifactWorkspaceError(
                    "存在未恢复的 Case Plan commit transaction"
                )
            if existing["status"] == "committed":
                return existing
            attempt = int(existing["attempt"]) + 1

        manifest = self._read_manifest()
        backup_path = self.run_dir / "backups" / TARGET_RELATIVE_PATH
        target_existed = self.target_path.is_file()
        if target_existed:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.target_path, backup_path)
        elif backup_path.exists():
            backup_path.unlink()
        now = utc_now()
        transaction = {
            "schema_version": "1.0.0",
            "transaction_id": f"{self.run_dir.name}-case-plan-commit",
            "run_id": self.run_dir.name,
            "approval_id": approval_id,
            "status": "prepared",
            "attempt": attempt,
            "created_at": now,
            "updated_at": now,
            "approved_by": approved_by.strip(),
            "target_path": TARGET_RELATIVE_PATH,
            "candidate_path": str(self.staging_path),
            "backup_path": str(backup_path) if target_existed else None,
            "target_existed": target_existed,
            "expected_target_hash": manifest["expected_target_hash"],
            "candidate_hash": manifest["validated_candidate_hash"],
            "expected_upstream_fingerprint": manifest[
                "validated_upstream_fingerprint"
            ],
            "applied": False,
            "error": None,
        }
        self._write_commit_transaction(transaction)
        return transaction

    def apply_commit(self, transaction: dict[str, Any]) -> dict[str, Any]:
        validate_named(
            transaction,
            "harness_case_plan_commit_transaction.schema.json",
        )
        if transaction["status"] == "committed":
            return self._commit_result(transaction)
        if transaction["status"] != "prepared":
            raise ArtifactWorkspaceError(
                f"Case Plan transaction 状态不可提交: {transaction['status']}"
            )
        self.assert_commit_ready()
        binding = self.approval_binding()
        for transaction_key, binding_key in (
            ("expected_target_hash", "expected_target_hash"),
            ("candidate_hash", "candidate_hash"),
            (
                "expected_upstream_fingerprint",
                "expected_upstream_fingerprint",
            ),
        ):
            if transaction[transaction_key] != binding[binding_key]:
                raise ArtifactWorkspaceError(
                    f"Case Plan transaction 的 {transaction_key} 已漂移"
                )

        transaction["status"] = "committing"
        self._write_commit_transaction(transaction)
        temporary = self.target_path.with_name(
            f".{self.target_path.name}.{self.run_dir.name}.tmp"
        )
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(self.staging_path, temporary)
            os.replace(temporary, self.target_path)
            committed_hash = file_hash(self.target_path)
            if committed_hash != transaction["candidate_hash"]:
                raise ArtifactWorkspaceError(
                    "Case Plan 正式目标 hash 与候选不一致"
                )
            transaction["applied"] = True
            transaction["status"] = "committed"
            transaction["error"] = None
            self._write_commit_transaction(transaction)
        except Exception as exc:
            transaction["error"] = str(exc)
            self._write_commit_transaction(transaction)
            raise
        finally:
            if temporary.exists():
                temporary.unlink()

        self.finalize_commit_manifest(transaction)
        return self._commit_result(transaction)

    def finalize_commit_manifest(
        self,
        transaction: dict[str, Any],
    ) -> None:
        if transaction["status"] != "committed":
            raise ArtifactWorkspaceError(
                "只有 committed transaction 可以更新 workspace manifest"
            )
        manifest = self._read_manifest()
        committed_hash = transaction["candidate_hash"]
        manifest.update(
            {
                "expected_target_hash": committed_hash,
                "committed_at": utc_now(),
                "committed_hash": committed_hash,
                "backup_path": (
                    transaction["backup_path"]
                ),
            }
        )
        atomic_write_json(self.manifest_path, manifest)

    def rollback_unfinished_commit(self) -> dict[str, Any]:
        transaction = self.read_commit_transaction()
        if transaction is None:
            raise ArtifactWorkspaceError(
                "Case Plan commit transaction 不存在"
            )
        if transaction["status"] == "rolled_back":
            return transaction
        if transaction["status"] == "committed":
            raise ArtifactWorkspaceError(
                "committed transaction 必须完成 metadata，不能回滚"
            )
        backup_path = (
            Path(transaction["backup_path"])
            if transaction["backup_path"]
            else None
        )
        if transaction["target_existed"] and (
            backup_path is None or not backup_path.is_file()
        ):
            raise ArtifactWorkspaceError(
                "Case Plan commit transaction 缺少回滚备份"
            )
        if (
            transaction["target_existed"]
            and backup_path is not None
            and file_hash(backup_path)
            != transaction["expected_target_hash"]
        ):
            raise ArtifactWorkspaceError(
                "Case Plan commit transaction 回滚备份 hash 不一致"
            )
        temporary = self.target_path.with_name(
            f".{self.target_path.name}.{self.run_dir.name}.tmp"
        )
        rollback_temporary = self.target_path.with_name(
            f".{self.target_path.name}.rollback.tmp"
        )
        for path in (temporary, rollback_temporary):
            if path.exists():
                path.unlink()
        if transaction["target_existed"]:
            assert backup_path is not None
            shutil.copy2(backup_path, rollback_temporary)
            os.replace(rollback_temporary, self.target_path)
        elif self.target_path.exists():
            self.target_path.unlink()
        if file_hash(self.target_path) != transaction["expected_target_hash"]:
            raise ArtifactWorkspaceError(
                "Case Plan transaction 回滚后目标 hash 不一致"
            )
        transaction["status"] = "rolled_back"
        transaction["applied"] = False
        transaction["error"] = "未完成提交已回滚"
        self._write_commit_transaction(transaction)
        return transaction

    def read_commit_transaction(self) -> dict[str, Any] | None:
        if not self.commit_transaction_path.is_file():
            return None
        transaction = json.loads(
            self.commit_transaction_path.read_text(encoding="utf-8")
        )
        validate_named(
            transaction,
            "harness_case_plan_commit_transaction.schema.json",
        )
        return transaction

    def _write_commit_transaction(
        self,
        transaction: dict[str, Any],
    ) -> None:
        transaction["updated_at"] = utc_now()
        validate_named(
            transaction,
            "harness_case_plan_commit_transaction.schema.json",
        )
        atomic_write_json(self.commit_transaction_path, transaction)

    @staticmethod
    def _commit_result(transaction: dict[str, Any]) -> dict[str, Any]:
        return {
            "target_path": TARGET_RELATIVE_PATH,
            "committed_hash": transaction["candidate_hash"],
            "backup_path": transaction["backup_path"],
            "transaction_id": transaction["transaction_id"],
        }

    def assert_commit_ready(self) -> None:
        manifest = self._read_manifest()
        if manifest.get("validation_status") != "passed":
            raise ArtifactWorkspaceError("Case Plan 候选尚未通过 Validator")
        current_candidate_hash = file_hash(self.staging_path)
        if current_candidate_hash != manifest.get("validated_candidate_hash"):
            raise ArtifactWorkspaceError("Case Plan staging 在校验后发生漂移，必须重新校验")
        current_upstream = self.upstream_fingerprint()
        if current_upstream != manifest.get("validated_upstream_fingerprint"):
            raise ArtifactWorkspaceError("Case Plan 上游产物在校验后发生漂移，必须重新生成并校验")
        current_target_hash = file_hash(self.target_path)
        if current_target_hash != manifest.get("expected_target_hash"):
            raise ArtifactWorkspaceError("正式 Case Plan 已被其他进程修改，拒绝覆盖")

    def approval_binding(self) -> dict[str, str | None]:
        manifest = self._read_manifest()
        return {
            "expected_target_hash": manifest.get("expected_target_hash"),
            "expected_upstream_fingerprint": manifest.get(
                "validated_upstream_fingerprint"
            )
            or manifest.get("proposal_upstream_fingerprint"),
            "candidate_hash": manifest.get("candidate_hash"),
        }

    def upstream_fingerprint(self) -> str:
        paths = ["acceptance/testability_gate.json"]
        if self.work_item_level in {"M", "L"}:
            paths.append("acceptance/acceptance_examples.json")
        if self.work_item_level == "L":
            paths.append("design/verification_responsibility_map.json")
        return fingerprint_files(self.item_root, tuple(paths))

    def _validator_command(self) -> list[str]:
        command = [
            sys.executable,
            str(
                ROOT
                / "skills"
                / "case-generation"
                / "scripts"
                / "validate_case_plan.py"
            ),
            "--input",
            str(self.staging_path),
            "--testability-gate",
            str(self.item_root / "acceptance" / "testability_gate.json"),
        ]
        if self.work_item_level in {"M", "L"}:
            command.extend(
                [
                    "--acceptance-examples",
                    str(self.item_root / "acceptance" / "acceptance_examples.json"),
                    "--require-examples",
                ]
            )
        if self.work_item_level == "L":
            command.extend(
                [
                    "--responsibility-map",
                    str(
                        self.item_root
                        / "design"
                        / "verification_responsibility_map.json"
                    ),
                    "--require-responsibilities",
                ]
            )
        return command

    def _resolve_readable_path(self, relative_path: str) -> Path:
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ArtifactWorkspaceError(f"禁止读取工作项外路径: {relative_path}")
        normalized = path.as_posix()
        if not (normalized.startswith("inputs/") or normalized in READABLE_EXACT_PATHS):
            raise ArtifactWorkspaceError(f"路径不在 Agent 读取白名单: {relative_path}")
        resolved = (self.item_root / path).resolve()
        if not resolved.is_relative_to(self.item_root):
            raise ArtifactWorkspaceError(f"路径逃逸工作项目录: {relative_path}")
        return resolved

    def _read_manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

