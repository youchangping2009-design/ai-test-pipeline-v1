from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from harness.contracts import ContractError, validate_named
from harness.stage_registry import ROOT
from harness.state_store import atomic_write_json, utc_now


HOOK_EVENTS = frozenset(
    {
        "pre_stage",
        "post_stage",
        "fail_stage",
        "approval_requested",
        "approval_resolved",
        "repair_requested",
    }
)
WARN_ONLY_EVENTS = frozenset(
    {
        "fail_stage",
        "approval_requested",
        "approval_resolved",
    }
)
EventCallback = Callable[[str, dict[str, Any]], None]


class HookConfigurationError(ValueError):
    """Raised when a Hook configuration crosses the trusted boundary."""


@dataclass(frozen=True)
class HookDispatchResult:
    executions: tuple[dict[str, Any], ...]

    @property
    def blocking_failure(self) -> dict[str, Any] | None:
        return next(
            (
                execution
                for execution in self.executions
                if execution["status"] != "succeeded"
                and execution["failure_policy"] == "fail_run"
            ),
            None,
        )


class HookDispatcher:
    def __init__(
        self,
        *,
        repository_root: Path = ROOT,
        config_path: Path | None = None,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.config_path = (
            config_path or self.repository_root / "config" / "harness_hooks.json"
        )
        self.hooks = self._load_hooks()

    def dispatch(
        self,
        *,
        event: str,
        state: dict[str, Any],
        run_dir: Path,
        stage_id: str | None,
        payload: dict[str, Any],
        event_callback: EventCallback,
    ) -> HookDispatchResult:
        if event not in HOOK_EVENTS:
            raise HookConfigurationError(f"不支持的 Hook event: {event}")
        executions: list[dict[str, Any]] = []
        for hook in self.hooks:
            if (
                not hook["enabled"]
                or hook["event"] != event
                or not self._matches_stage(hook["stages"], stage_id)
            ):
                continue
            executions.append(
                self._execute_hook(
                    hook=hook,
                    event=event,
                    state=state,
                    run_dir=run_dir,
                    stage_id=stage_id,
                    payload=payload,
                    event_callback=event_callback,
                )
            )
        return HookDispatchResult(tuple(executions))

    def _load_hooks(self) -> list[dict[str, Any]]:
        if not self.config_path.exists():
            return []
        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
            validate_named(config, "harness_hook_config.schema.json")
        except (json.JSONDecodeError, ContractError) as exc:
            raise HookConfigurationError(f"Hook 配置非法: {exc}") from exc
        hook_ids: set[str] = set()
        hooks = config["hooks"]
        for hook in hooks:
            hook_id = str(hook["hook_id"])
            if hook_id in hook_ids:
                raise HookConfigurationError(f"Hook ID 重复: {hook_id}")
            hook_ids.add(hook_id)
            if (
                hook["event"] in WARN_ONLY_EVENTS
                and hook["failure_policy"] != "warn"
            ):
                raise HookConfigurationError(
                    f"{hook['event']} Hook 只能使用 warn: {hook_id}"
                )
            if hook["enabled"]:
                self._resolve_handler(str(hook["handler"]))
        return hooks

    def _resolve_handler(self, handler: str) -> Path:
        relative = Path(handler)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.suffix != ".py"
            or relative.parts[:2] != ("scripts", "hooks")
        ):
            raise HookConfigurationError(
                f"Hook handler 仅允许 scripts/hooks/*.py: {handler}"
            )
        resolved = (self.repository_root / relative).resolve()
        trusted_root = (self.repository_root / "scripts" / "hooks").resolve()
        try:
            resolved.relative_to(trusted_root)
        except ValueError as exc:
            raise HookConfigurationError(
                f"Hook handler 越过可信目录: {handler}"
            ) from exc
        if not resolved.is_file():
            raise HookConfigurationError(f"Hook handler 不存在: {handler}")
        return resolved

    def _execute_hook(
        self,
        *,
        hook: dict[str, Any],
        event: str,
        state: dict[str, Any],
        run_dir: Path,
        stage_id: str | None,
        payload: dict[str, Any],
        event_callback: EventCallback,
    ) -> dict[str, Any]:
        handler = self._resolve_handler(str(hook["handler"]))
        execution_id = self._next_execution_id(
            run_dir=run_dir,
            hook_id=str(hook["hook_id"]),
            event=event,
        )
        request = {
            "protocol_version": "1.0.0",
            "execution_id": execution_id,
            "run_id": state["run_id"],
            "project_code": state["project_code"],
            "work_item_id": state["work_item_id"],
            "work_item_level": state["work_item_level"],
            "event": event,
            "stage_id": stage_id,
            "payload": payload,
        }
        event_callback(
            "hook_dispatch_started",
            {
                "execution_id": execution_id,
                "hook_id": hook["hook_id"],
                "hook_event": event,
            },
        )
        started_at = utc_now()
        started = time.monotonic()
        exit_code: int | None = None
        timed_out = False
        output: dict[str, Any] | None = None
        error: str | None = None
        try:
            result = subprocess.run(
                [sys.executable, str(handler)],
                cwd=self.repository_root,
                input=json.dumps(request, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=int(hook["timeout_seconds"]),
                env=self._sanitized_environment(),
            )
            exit_code = result.returncode
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            if len(stdout) > int(hook["max_output_chars"]):
                error = "Hook stdout 超过大小限制"
            elif result.returncode != 0:
                error = self._redact(stderr.strip()[-2000:] or "Hook handler 失败")
            elif stdout.strip():
                parsed = json.loads(stdout)
                if not isinstance(parsed, dict):
                    error = "Hook stdout 必须是 JSON object"
                else:
                    output = self._sanitize_json(parsed)
        except subprocess.TimeoutExpired:
            timed_out = True
            error = f"Hook 超过 {hook['timeout_seconds']} 秒超时"
        except json.JSONDecodeError as exc:
            error = f"Hook stdout 不是合法 JSON: {exc}"
        except OSError as exc:
            error = f"Hook handler 无法启动: {exc}"

        status = (
            "timed_out"
            if timed_out
            else "succeeded"
            if exit_code == 0 and error is None
            else "failed"
        )
        execution = {
            "schema_version": "1.0.0",
            "execution_id": execution_id,
            "run_id": state["run_id"],
            "hook_id": hook["hook_id"],
            "event": event,
            "stage_id": stage_id,
            "handler": hook["handler"],
            "failure_policy": hook["failure_policy"],
            "status": status,
            "started_at": started_at,
            "completed_at": utc_now(),
            "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
            "exit_code": exit_code,
            "timed_out": timed_out,
            "output": output,
            "error": error,
        }
        validate_named(execution, "harness_hook_execution.schema.json")
        atomic_write_json(run_dir / "hooks" / f"{execution_id}.json", execution)
        event_callback(
            (
                "hook_dispatch_completed"
                if status == "succeeded"
                else "hook_dispatch_failed"
            ),
            {
                "execution_id": execution_id,
                "hook_id": hook["hook_id"],
                "hook_event": event,
                "status": status,
                "failure_policy": hook["failure_policy"],
            },
        )
        return execution

    @staticmethod
    def _matches_stage(stages: list[str], stage_id: str | None) -> bool:
        return "*" in stages or (stage_id is not None and stage_id in stages)

    @staticmethod
    def _sanitized_environment() -> dict[str, str]:
        environment = {
            "PYTHONIOENCODING": "utf-8",
        }
        for key in ("PATH", "LANG", "LC_ALL", "TMPDIR"):
            value = os.environ.get(key)
            if value:
                environment[key] = value
        return environment

    @staticmethod
    def _redact(text: str) -> str:
        redacted = re.sub(
            r"\bsk-[A-Za-z0-9_-]{8,}\b",
            "[REDACTED_API_KEY]",
            text,
        )
        return re.sub(
            r"(?i)(authorization\s*[:=]\s*)(\S+)",
            r"\1[REDACTED]",
            redacted,
        )

    @classmethod
    def _sanitize_json(cls, value: Any) -> Any:
        if isinstance(value, str):
            return cls._redact(value)
        if isinstance(value, list):
            return [cls._sanitize_json(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): cls._sanitize_json(item)
                for key, item in value.items()
            }
        return value

    @staticmethod
    def _next_execution_id(
        *,
        run_dir: Path,
        hook_id: str,
        event: str,
    ) -> str:
        hooks_dir = run_dir / "hooks"
        prefix = f"{hook_id}-{event}-"
        existing = (
            sum(1 for path in hooks_dir.glob(f"{prefix}*.json"))
            if hooks_dir.exists()
            else 0
        )
        return f"{prefix}{existing + 1}"

