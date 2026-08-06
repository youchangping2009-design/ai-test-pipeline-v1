from __future__ import annotations

import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from harness.contracts import validate_named, validate_run_state
from harness.stage_registry import StageSpec


ROOT = Path(__file__).resolve().parents[2]


class HarnessStateError(RuntimeError):
    """Raised when persisted Harness state cannot be safely used."""


def _process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _parse_lock_owner(raw: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {}
        for line in raw.splitlines():
            key, separator, value = line.partition("=")
            if separator:
                payload[key.strip()] = value.strip()
    if not isinstance(payload, dict):
        return None
    try:
        pid = int(payload["pid"])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "run_id": str(payload.get("run_id", "")).strip(),
        "pid": pid,
        "token": str(payload.get("token", "")).strip(),
        "created_at": str(payload.get("created_at", "")).strip(),
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def fingerprint_files(item_root: Path, relative_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    paths = ("manifest.json", *relative_paths)
    for relative_path in paths:
        path = item_root / relative_path
        digest.update(relative_path.encode("utf-8"))
        if path.exists() and path.is_file():
            digest.update(b"\0present\0")
            digest.update(path.read_bytes())
        else:
            digest.update(b"\0missing\0")
    return digest.hexdigest()


def create_stage_record(stage: StageSpec, order: int) -> dict[str, Any]:
    return {
        "stage_id": stage.stage_id,
        "order": order,
        "kind": stage.kind,
        "status": "pending",
        "attempts": 0,
        "required_files": list(stage.required_files),
        "input_fingerprint": "",
        "started_at": None,
        "completed_at": None,
        "last_exit_code": None,
        "log_path": None,
    }


class StateStore:
    def __init__(self, item_root: Path) -> None:
        self.item_root = item_root
        self.generation_root = item_root / ".generation"
        self.runs_root = self.generation_root / "runs"
        self.current_pointer = self.generation_root / "current_run.json"
        self.lock_path = self.runs_root / "pipeline.lock"

    def run_dir(self, run_id: str) -> Path:
        if not run_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for character in run_id):
            raise HarnessStateError(f"非法 run_id: {run_id!r}")
        return self.runs_root / run_id

    def state_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "run_state.json"

    def create(
        self,
        run_id: str,
        project_code: str,
        work_item_id: str,
        work_item_level: str,
        strict: bool,
        stop_at: str,
        stages: list[StageSpec],
        mode: str = "validate",
    ) -> dict[str, Any]:
        state_path = self.state_path(run_id)
        if state_path.exists():
            raise HarnessStateError(f"run 已存在，不能重复创建: {run_id}")
        now = utc_now()
        state = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "project_code": project_code,
            "work_item_id": work_item_id,
            "work_item_level": work_item_level,
            "mode": mode,
            "strict": strict,
            "status": "pending",
            "stop_at": stop_at,
            "current_stage": None,
            "created_at": now,
            "updated_at": now,
            "run_dir": display_path(self.run_dir(run_id)),
            "stages": [
                create_stage_record(stage, index)
                for index, stage in enumerate(stages)
            ],
            "last_error": None,
        }
        self.save(state)
        self.set_current(run_id)
        self.append_event(state, "run_created", None, {"stop_at": stop_at})
        return state

    def load(self, run_id: str) -> dict[str, Any]:
        path = self.state_path(run_id)
        if not path.exists():
            raise HarnessStateError(f"run 不存在: {run_id}")
        state = json.loads(path.read_text(encoding="utf-8"))
        validate_run_state(state)
        return state

    def save(self, state: dict[str, Any]) -> None:
        state["updated_at"] = utc_now()
        validate_run_state(state)
        atomic_write_json(self.state_path(str(state["run_id"])), state)

    def set_current(self, run_id: str) -> None:
        atomic_write_json(
            self.current_pointer,
            {"run_id": run_id, "updated_at": utc_now()},
        )

    def current_run_id(self) -> str:
        if not self.current_pointer.exists():
            raise HarnessStateError("当前工作项没有 current_run.json")
        payload = json.loads(self.current_pointer.read_text(encoding="utf-8"))
        run_id = str(payload.get("run_id", "")).strip()
        if not run_id:
            raise HarnessStateError("current_run.json 缺少 run_id")
        return run_id

    def append_event(
        self,
        state: dict[str, Any],
        event_type: str,
        stage_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        events_path = self.run_dir(str(state["run_id"])) / "events.jsonl"
        sequence = 1
        if events_path.exists():
            sequence += sum(1 for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip())
        event = {
            "schema_version": "1.0.0",
            "sequence": sequence,
            "timestamp": utc_now(),
            "run_id": state["run_id"],
            "event_type": event_type,
            "stage_id": stage_id,
            "payload": payload,
        }
        validate_named(event, "harness_event.schema.json")
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    @contextmanager
    def lock(self, run_id: str, force: bool = False) -> Iterator[None]:
        self.runs_root.mkdir(parents=True, exist_ok=True)
        if force and self.lock_path.exists():
            try:
                owner = _parse_lock_owner(
                    self.lock_path.read_text(encoding="utf-8")
                )
            except FileNotFoundError:
                owner = None
                force = False
            if not force:
                owner = None
            elif owner is None:
                raise HarnessStateError(
                    "Harness 进程锁所有者信息不完整，拒绝强制删除；"
                    "请先确认没有活跃进程并人工检查 pipeline.lock"
                )
            if owner is not None and _process_is_alive(int(owner["pid"])):
                raise HarnessStateError(
                    "Harness 进程锁仍由活跃进程持有，拒绝强制删除: "
                    f"run_id={owner['run_id'] or '?'} pid={owner['pid']}"
                )
            if owner is not None:
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass
        token = uuid.uuid4().hex
        descriptor: int | None = None
        try:
            descriptor = os.open(
                self.lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError as exc:
            try:
                owner = self.lock_path.read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                with self.lock(run_id, force=False):
                    yield
                return
            raise HarnessStateError(
                f"工作项已有 Harness 进程锁: {owner or self.lock_path}"
            ) from exc
        try:
            lock_owner = {
                "run_id": run_id,
                "pid": os.getpid(),
                "token": token,
                "created_at": utc_now(),
            }
            os.write(
                descriptor,
                (
                    json.dumps(lock_owner, ensure_ascii=False, sort_keys=True)
                    + "\n"
                ).encode("utf-8"),
            )
            os.close(descriptor)
            descriptor = None
            yield
        finally:
            uninitialized_owner = descriptor is not None
            if descriptor is not None:
                os.close(descriptor)
            if self.lock_path.exists():
                current = _parse_lock_owner(
                    self.lock_path.read_text(encoding="utf-8")
                )
                if uninitialized_owner or (
                    current is not None and current["token"] == token
                ):
                    self.lock_path.unlink()

