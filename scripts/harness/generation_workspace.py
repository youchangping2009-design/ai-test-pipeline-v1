from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from execute_regeneration_bundle import validate_bundle
from harness.contracts import validate_named
from harness.stage_registry import ROOT
from harness.state_store import atomic_write_json, display_path, utc_now


PUBLISH_PREFIXES = (
    "analysis/",
    "evidence/",
    "image_evidence/",
    "structured_prd/",
    "coverage/",
    "acceptance/",
    "design/",
    "testcases/",
    "traceability/",
    "reviews/",
)
PUBLISH_FILES = frozenset(
    {
        "inputs/requirement_summary.md",
        "inputs/source_manifest.json",
        "feishu_ready.md",
    }
)
FormalValidator = Callable[[], tuple[bool, str]]
ReplaceFunction = Callable[[Any, Any], None]


class ControlledGenerationError(RuntimeError):
    """Raised when a generation candidate cannot be staged or published safely."""


def file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate_hash(entries: list[tuple[str, str | None]]) -> str:
    digest = hashlib.sha256()
    for path, value in sorted(entries):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((value or "<missing>").encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


class ControlledGenerationWorkspace:
    def __init__(
        self,
        *,
        item_root: Path,
        run_dir: Path,
        project_code: str,
        work_item_id: str,
        work_item_level: str,
        repository_root: Path = ROOT,
    ) -> None:
        self.item_root = item_root
        self.run_dir = run_dir
        self.project_code = project_code
        self.work_item_id = work_item_id
        self.work_item_level = work_item_level.upper()
        self.repository_root = repository_root
        self.staging_root = run_dir / "staging" / "work_item"
        self.bundle_path = run_dir / "generation_bundle.json"
        self.candidate_manifest_path = run_dir / "generation_candidate.json"
        self.transaction_path = run_dir / "publish_transaction.json"

    def stage_and_validate(
        self,
        *,
        run_id: str,
        provider: str,
        bundle: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_bundle_paths(bundle)
        atomic_write_json(self.bundle_path, bundle)
        with tempfile.TemporaryDirectory(
            prefix=f"ai-test-pipeline-{run_id}-"
        ) as temporary:
            clone_root = Path(temporary) / "repo"
            shutil.copytree(
                self.repository_root,
                clone_root,
                ignore=self._copy_ignore,
            )
            clone_item = (
                clone_root
                / "assets"
                / "projects"
                / self.project_code
                / "work_items"
                / self.work_item_id
            )
            if not clone_item.exists():
                # Tests and embedders may provide a work item outside the
                # repository tree. Seed that explicit item into the isolated
                # repository so validation does not depend on a committed
                # business sample being present at the same identity.
                shutil.copytree(
                    self.item_root,
                    clone_item,
                    ignore=self._copy_ignore,
                )
            clone_bundle = Path(temporary) / "generation_bundle.json"
            atomic_write_json(clone_bundle, bundle)
            command = [
                sys.executable,
                str(clone_root / "scripts" / "execute_regeneration_bundle.py"),
                "--project-code",
                self.project_code,
                "--work-item-id",
                self.work_item_id,
                "--bundle",
                str(clone_bundle),
                "--strict",
                "--skip-code-reviews",
                "--skip-project-refresh",
            ]
            result = subprocess.run(
                command,
                cwd=clone_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,
            )
            output = (result.stdout or "") + (
                ("\n" + result.stderr) if result.stderr else ""
            )
            log_path = self.run_dir / "logs" / "generation_validation.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(output, encoding="utf-8")
            if result.returncode != 0:
                raise ControlledGenerationError(
                    "隔离候选未通过 normalizer/strict，"
                    f"exit={result.returncode}，日志: {display_path(log_path)}"
                )
            self._copy_candidate(clone_item)

        files = self._candidate_file_records()
        candidate_hash = aggregate_hash(
            [(entry["path"], entry["sha256"]) for entry in files]
        )
        expected_target_hash = aggregate_hash(
            [
                (entry["path"], entry["expected_target_hash"])
                for entry in files
            ]
        )
        candidate = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "project_code": self.project_code,
            "work_item_id": self.work_item_id,
            "work_item_level": self.work_item_level,
            "provider": provider,
            "created_at": utc_now(),
            "bundle_hash": file_hash(self.bundle_path),
            "candidate_hash": candidate_hash,
            "expected_target_hash": expected_target_hash,
            "expected_upstream_fingerprint": self.upstream_fingerprint(),
            "files": files,
            "validation": {
                "passed": True,
                "exit_code": 0,
                "log_path": display_path(log_path),
            },
        }
        validate_named(candidate, "harness_generation_candidate.schema.json")
        atomic_write_json(self.candidate_manifest_path, candidate)
        return candidate

    def verify_candidate(self) -> dict[str, Any]:
        if not self.candidate_manifest_path.is_file():
            raise ControlledGenerationError("generation_candidate.json 不存在")
        candidate = json.loads(
            self.candidate_manifest_path.read_text(encoding="utf-8")
        )
        validate_named(candidate, "harness_generation_candidate.schema.json")
        current_candidate_entries: list[tuple[str, str | None]] = []
        current_target_entries: list[tuple[str, str | None]] = []
        for entry in candidate["files"]:
            relative = self._safe_item_relative(str(entry["path"]))
            staged = self.staging_root / relative
            staged_hash = file_hash(staged)
            if staged_hash != entry["sha256"]:
                raise ControlledGenerationError(
                    f"候选文件 hash 已漂移: {relative}"
                )
            target_hash = file_hash(self.item_root / relative)
            if target_hash != entry["expected_target_hash"]:
                raise ControlledGenerationError(
                    f"正式目标 hash 已漂移: {relative}"
                )
            current_candidate_entries.append((str(relative), staged_hash))
            current_target_entries.append((str(relative), target_hash))
        if aggregate_hash(current_candidate_entries) != candidate["candidate_hash"]:
            raise ControlledGenerationError("candidate aggregate hash 已漂移")
        if aggregate_hash(current_target_entries) != candidate["expected_target_hash"]:
            raise ControlledGenerationError("target aggregate hash 已漂移")
        if self.upstream_fingerprint() != candidate["expected_upstream_fingerprint"]:
            raise ControlledGenerationError("manifest/raw inputs 已漂移")
        return candidate

    def publish(
        self,
        *,
        formal_validator: FormalValidator,
        replace_func: ReplaceFunction = os.replace,
    ) -> dict[str, Any]:
        self.recover_unfinished()
        candidate = self.verify_candidate()
        backup_root = self.run_dir / "publish_backup"
        if backup_root.exists():
            shutil.rmtree(backup_root)
        files: list[dict[str, Any]] = []
        for entry in candidate["files"]:
            relative = self._safe_item_relative(str(entry["path"]))
            target = self.item_root / relative
            backup = backup_root / relative
            existed = target.is_file()
            if existed:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            files.append(
                {
                    "path": str(relative),
                    "existed": existed,
                    "backup_path": str(backup) if existed else None,
                    "candidate_path": str(self.staging_root / relative),
                    "applied": False,
                }
            )
        now = utc_now()
        transaction = {
            "schema_version": "1.0.0",
            "transaction_id": f"{candidate['run_id']}-publish",
            "run_id": candidate["run_id"],
            "status": "prepared",
            "created_at": now,
            "updated_at": now,
            "files": files,
            "error": None,
        }
        self._write_transaction(transaction)
        try:
            transaction["status"] = "publishing"
            self._write_transaction(transaction)
            for file_record in transaction["files"]:
                target = self.item_root / file_record["path"]
                candidate_path = Path(file_record["candidate_path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(
                    f".{target.name}.{candidate['run_id']}.tmp"
                )
                shutil.copy2(candidate_path, temporary)
                replace_func(temporary, target)
                file_record["applied"] = True
                self._write_transaction(transaction)
            passed, output = formal_validator()
            validation_log = self.run_dir / "logs" / "published_strict.log"
            validation_log.parent.mkdir(parents=True, exist_ok=True)
            validation_log.write_text(output, encoding="utf-8")
            if not passed:
                raise ControlledGenerationError(
                    "发布后正式 strict 失败，已触发回滚"
                )
            transaction["status"] = "committed"
            self._write_transaction(transaction)
            return transaction
        except Exception as exc:
            transaction["error"] = str(exc)
            for file_record in transaction["files"]:
                target = self.item_root / file_record["path"]
                temporary = target.with_name(
                    f".{target.name}.{candidate['run_id']}.tmp"
                )
                if temporary.exists():
                    temporary.unlink()
            self._rollback(transaction)
            raise

    def recover_unfinished(self) -> bool:
        if not self.transaction_path.is_file():
            return False
        transaction = json.loads(
            self.transaction_path.read_text(encoding="utf-8")
        )
        validate_named(
            transaction,
            "harness_publish_transaction.schema.json",
        )
        if transaction["status"] not in {"prepared", "publishing"}:
            return False
        self._assert_recovery_materials(transaction)
        self._cleanup_transaction_temporaries(transaction)
        transaction["error"] = "检测到未完成发布，执行自动恢复"
        self._rollback(transaction)
        return True

    def upstream_fingerprint(self) -> str:
        entries: list[tuple[str, str | None]] = [
            ("manifest.json", file_hash(self.item_root / "manifest.json"))
        ]
        inputs = self.item_root / "inputs"
        if inputs.exists():
            for path in sorted(item for item in inputs.rglob("*") if item.is_file()):
                relative = path.relative_to(self.item_root)
                if str(relative) in PUBLISH_FILES:
                    continue
                entries.append((str(relative), file_hash(path)))
        return aggregate_hash(entries)

    def approval_binding(self) -> dict[str, str]:
        candidate = self.verify_candidate()
        return {
            "candidate_hash": candidate["candidate_hash"],
            "expected_target_hash": candidate["expected_target_hash"],
            "expected_upstream_fingerprint": candidate[
                "expected_upstream_fingerprint"
            ],
        }

    def _validate_bundle_paths(self, bundle: dict[str, Any]) -> None:
        cleanup_targets = bundle.get("cleanup_targets", [])
        artifacts = bundle.get("artifacts", {})
        if not isinstance(cleanup_targets, list) or not isinstance(artifacts, dict):
            raise ControlledGenerationError("bundle 结构非法")
        errors = validate_bundle(
            cleanup_targets,
            artifacts,
            self.work_item_level,
        )
        if errors:
            raise ControlledGenerationError(
                "bundle 校验失败:\n- " + "\n- ".join(errors)
            )
        expected_prefix = (
            f"assets/projects/{self.project_code}/work_items/"
            f"{self.work_item_id}/"
        )
        for raw_path in [*cleanup_targets, *artifacts.keys()]:
            if not isinstance(raw_path, str) or not raw_path.startswith(
                expected_prefix
            ):
                raise ControlledGenerationError(
                    f"bundle 路径越过当前工作项: {raw_path!r}"
                )
            relative = self._safe_item_relative(
                raw_path[len(expected_prefix) :]
            )
            if not self._is_publishable(relative):
                raise ControlledGenerationError(
                    f"bundle 路径不属于正式资产白名单: {relative}"
                )
        for content in artifacts.values():
            if not isinstance(content, str):
                raise ControlledGenerationError("bundle artifact 内容必须是字符串")

    def _copy_candidate(self, clone_item: Path) -> None:
        if self.staging_root.exists():
            shutil.rmtree(self.staging_root)
        for path in sorted(item for item in clone_item.rglob("*") if item.is_file()):
            relative = path.relative_to(clone_item)
            if not self._is_publishable(relative):
                continue
            target = self.staging_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

    def _candidate_file_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in sorted(
            item for item in self.staging_root.rglob("*") if item.is_file()
        ):
            relative = path.relative_to(self.staging_root)
            records.append(
                {
                    "path": str(relative),
                    "sha256": file_hash(path),
                    "size_bytes": path.stat().st_size,
                    "expected_target_hash": file_hash(
                        self.item_root / relative
                    ),
                }
            )
        if not records:
            raise ControlledGenerationError("隔离校验未产生可发布候选")
        return records

    def _rollback(self, transaction: dict[str, Any]) -> None:
        rollback_errors: list[str] = []
        for file_record in reversed(transaction["files"]):
            target = self.item_root / file_record["path"]
            temporary = target.with_name(f".{target.name}.rollback.tmp")
            try:
                if file_record["existed"]:
                    backup = Path(file_record["backup_path"])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, temporary)
                    os.replace(temporary, target)
                elif target.exists():
                    target.unlink()
                file_record["applied"] = False
            except OSError as exc:
                rollback_errors.append(f"{file_record['path']}: {exc}")
            finally:
                if temporary.exists():
                    try:
                        temporary.unlink()
                    except OSError as exc:
                        rollback_errors.append(
                            f"{file_record['path']} 临时文件清理失败: {exc}"
                        )
        transaction["status"] = "rolled_back"
        if rollback_errors:
            transaction["error"] = (
                str(transaction.get("error") or "")
                + "; rollback errors: "
                + " | ".join(rollback_errors)
            )
        self._write_transaction(transaction)
        if rollback_errors:
            raise ControlledGenerationError(
                "发布回滚不完整: " + " | ".join(rollback_errors)
            )

    def _assert_recovery_materials(self, transaction: dict[str, Any]) -> None:
        missing: list[str] = []
        for file_record in transaction["files"]:
            if not file_record["existed"]:
                continue
            backup_path = file_record.get("backup_path")
            if not backup_path or not Path(str(backup_path)).is_file():
                missing.append(str(file_record["path"]))
        if missing:
            raise ControlledGenerationError(
                "未完成发布缺少回滚备份，拒绝部分恢复: "
                + ", ".join(sorted(missing))
            )

    def _cleanup_transaction_temporaries(
        self,
        transaction: dict[str, Any],
    ) -> None:
        errors: list[str] = []
        run_id = str(transaction["run_id"])
        for file_record in transaction["files"]:
            target = self.item_root / file_record["path"]
            temporary = target.with_name(f".{target.name}.{run_id}.tmp")
            if not temporary.exists():
                continue
            try:
                temporary.unlink()
            except OSError as exc:
                errors.append(f"{file_record['path']}: {exc}")
        if errors:
            raise ControlledGenerationError(
                "未完成发布临时文件清理失败: " + " | ".join(errors)
            )

    def _write_transaction(self, transaction: dict[str, Any]) -> None:
        transaction["updated_at"] = utc_now()
        validate_named(
            transaction,
            "harness_publish_transaction.schema.json",
        )
        atomic_write_json(self.transaction_path, transaction)

    @staticmethod
    def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
        ignored = {".git", "__pycache__", ".pytest_cache", ".DS_Store"}
        if ".generation" in names:
            ignored.add(".generation")
        return ignored.intersection(names)

    @staticmethod
    def _safe_item_relative(raw: str) -> Path:
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ControlledGenerationError(f"非法工作项相对路径: {raw!r}")
        return relative

    @staticmethod
    def _is_publishable(relative: Path) -> bool:
        value = relative.as_posix()
        return value in PUBLISH_FILES or value.startswith(PUBLISH_PREFIXES)
