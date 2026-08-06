from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from harness.stage_registry import ROOT


class ModelGatewayError(RuntimeError):
    """Raised when a model adapter cannot return a valid action payload."""


@dataclass(frozen=True)
class ModelTurnResult:
    action: dict[str, Any]
    usage: dict[str, int | float] | None = None
    runtime: dict[str, str] | None = None


class ModelGateway(Protocol):
    def next_action(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any] | ModelTurnResult:
        """Return one Model Action for the current turn."""


@dataclass
class CommandModelGateway:
    command: list[str]
    timeout_seconds: int = 120
    max_output_chars: int = 1_000_000

    def __post_init__(self) -> None:
        if not self.command or not all(
            isinstance(part, str) and part for part in self.command
        ):
            raise ModelGatewayError("provider command 必须是非空 argv 数组")

    def next_action(self, request: dict[str, Any]) -> ModelTurnResult:
        result = subprocess.run(
            self.command,
            cwd=ROOT,
            input=json.dumps(request, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=self.timeout_seconds,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-2000:]
            raise ModelGatewayError(
                f"provider command 失败，退出码 {result.returncode}: {stderr}"
            )
        stdout = (result.stdout or "").strip()
        if len(stdout) > self.max_output_chars:
            raise ModelGatewayError("provider command 输出超过大小限制")
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ModelGatewayError(f"provider command 未返回合法 JSON Action: {exc}") from exc
        if not isinstance(payload, dict):
            raise ModelGatewayError("provider command 必须返回 JSON object")
        if "action" not in payload:
            return ModelTurnResult(
                action=payload,
                usage=None,
                runtime={"provider": "command"},
            )
        action = payload.get("action")
        if not isinstance(action, dict):
            raise ModelGatewayError("provider envelope.action 必须是 JSON object")
        usage = self._normalize_usage(payload.get("usage"))
        runtime_raw = payload.get("runtime")
        runtime = (
            {
                str(key): str(value)
                for key, value in runtime_raw.items()
                if isinstance(key, str) and value is not None
            }
            if isinstance(runtime_raw, dict)
            else {"provider": "command"}
        )
        runtime.setdefault("provider", "command")
        return ModelTurnResult(action=action, usage=usage, runtime=runtime)

    @staticmethod
    def _normalize_usage(raw: Any) -> dict[str, int | float] | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise ModelGatewayError("provider envelope.usage 必须是 object")
        usage: dict[str, int | float] = {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            value = raw.get(key, 0)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ModelGatewayError(f"usage.{key} 必须是非负整数")
            usage[key] = value
        cost = raw.get("cost_usd", 0.0)
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
            raise ModelGatewayError("usage.cost_usd 必须是非负数")
        usage["cost_usd"] = float(cost)
        return usage


@dataclass
class ScriptedModelGateway:
    actions: list[dict[str, Any]]
    cursor: int = 0

    def next_action(self, _request: dict[str, Any]) -> ModelTurnResult:
        if self.cursor >= len(self.actions):
            raise ModelGatewayError("scripted actions 已耗尽")
        action = self.actions[self.cursor]
        self.cursor += 1
        return ModelTurnResult(
            action=action,
            usage=None,
            runtime={"provider": "scripted"},
        )


def parse_provider_command(raw: str) -> list[str]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelGatewayError(f"--provider-command-json 不是合法 JSON: {exc}") from exc
    if not isinstance(payload, list) or not all(
        isinstance(part, str) and part for part in payload
    ):
        raise ModelGatewayError("--provider-command-json 必须是非空字符串数组")
    if not payload:
        raise ModelGatewayError("--provider-command-json 不能为空")
    executable = Path(payload[0])
    if executable.is_absolute() and not executable.exists():
        raise ModelGatewayError(f"provider 可执行文件不存在: {executable}")
    return payload

