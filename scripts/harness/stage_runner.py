from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from harness.diagnostics import (
    missing_artifact_diagnostics,
    normalize_validator_failure,
)
from harness.state_store import display_path, utc_now
from harness.stage_registry import ROOT, StageSpec


EventCallback = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True)
class StageExecution:
    exit_code: int
    log_path: str
    diagnostics: tuple[dict[str, Any], ...]

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


class StageRunner:
    def __init__(self, timeout_seconds: int = 300) -> None:
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        stage: StageSpec,
        item_root: Path,
        run_dir: Path,
        project_code: str,
        work_item_id: str,
        work_item_level: str,
        strict: bool,
        attempt: int,
        event_callback: EventCallback,
    ) -> StageExecution:
        log_path = run_dir / "logs" / f"{stage.stage_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostics: list[dict[str, Any]] = []
        missing = [
            relative_path
            for relative_path in stage.required_files
            if not (item_root / relative_path).is_file()
        ]
        if missing:
            message = "缺少阶段必需产物: " + ", ".join(missing)
            diagnostics.extend(
                missing_artifact_diagnostics(
                    stage_id=stage.stage_id,
                    missing_paths=missing,
                    attempt=attempt,
                )
            )
            log_path.write_text(message + "\n", encoding="utf-8")
            return StageExecution(
                exit_code=2,
                log_path=display_path(log_path),
                diagnostics=tuple(diagnostics),
            )

        commands = stage.commands(
            item_root,
            project_code,
            work_item_id,
            work_item_level,
            strict,
        )
        log_lines = [
            f"stage_id: {stage.stage_id}",
            f"started_at: {utc_now()}",
            f"required_files: {len(stage.required_files)}",
            f"commands: {len(commands)}",
            "",
        ]
        for index, command in enumerate(commands, start=1):
            event_callback(
                "command_started",
                {"index": index, "argv": command},
            )
            log_lines.append(f"$ {' '.join(command)}")
            try:
                result = subprocess.run(
                    command,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=self.timeout_seconds,
                )
                output = (result.stdout or "") + (
                    ("\n" + result.stderr) if result.stderr else ""
                )
                exit_code = result.returncode
            except subprocess.TimeoutExpired as exc:
                output = ((exc.stdout or "") + "\n" + (exc.stderr or "")).strip()
                exit_code = 124
                output = f"{output}\n命令超过 {self.timeout_seconds} 秒超时".strip()
            log_lines.extend([output.strip(), f"exit_code: {exit_code}", ""])
            event_callback(
                "command_completed",
                {"index": index, "argv": command, "exit_code": exit_code},
            )
            if exit_code != 0:
                diagnostics.extend(
                    normalize_validator_failure(
                        observed_stage_id=stage.stage_id,
                        command=command,
                        command_index=index,
                        exit_code=exit_code,
                        output=output,
                        attempt=attempt,
                    )
                )
                log_path.write_text("\n".join(log_lines), encoding="utf-8")
                return StageExecution(
                    exit_code=exit_code,
                    log_path=display_path(log_path),
                    diagnostics=tuple(diagnostics),
                )

        log_lines.append(f"completed_at: {utc_now()}")
        log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        return StageExecution(
            exit_code=0,
            log_path=display_path(log_path),
            diagnostics=(),
        )

def write_diagnostics(
    run_dir: Path,
    stage_id: str,
    attempt: int,
    diagnostics: tuple[dict[str, Any], ...],
) -> str | None:
    if not diagnostics:
        return None
    path = run_dir / "diagnostics" / stage_id / f"attempt-{attempt}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(list(diagnostics), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return display_path(path)

