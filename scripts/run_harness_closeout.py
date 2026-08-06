#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.contracts import validate_named  # noqa: E402
from harness.state_store import atomic_write_json, utc_now  # noqa: E402


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def work_item_fingerprint(item_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in item_root.rglob("*") if item.is_file()):
        relative = path.relative_to(item_root)
        if relative.parts and relative.parts[0] == ".generation":
            continue
        if ".DS_Store" in relative.parts:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def output_tail(output: str, max_chars: int = 4000) -> str:
    return output[-max_chars:]


def run_command(
    command_id: str,
    argv: list[str],
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
        )
        exit_code = result.returncode
        output = (result.stdout or "") + (
            ("\n" + result.stderr) if result.stderr else ""
        )
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        output = (
            f"命令超过 {timeout_seconds}s 超时\n"
            + stdout
            + (("\n" + stderr) if stderr else "")
        )
    return {
        "id": command_id,
        "argv": argv,
        "exit_code": exit_code,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "passed": exit_code == 0,
        "output_tail": output_tail(output),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="执行 Harness-Loop 端到端只读收口验收"
    )
    parser.add_argument("--project-code", default="WX-YGJ")
    parser.add_argument("--work-item-id", default="PT083")
    parser.add_argument("--work-item-level", choices=["S", "M", "L"], default="M")
    parser.add_argument("--run-id")
    parser.add_argument("--command-timeout", type=int, default=1200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command_timeout < 1:
        print("--command-timeout 必须大于 0")
        return 2
    project_code = normalize_code(args.project_code)
    work_item_id = normalize_code(args.work_item_id)
    run_id = args.run_id or datetime.now(timezone.utc).strftime(
        "RUN-CLOSEOUT-%Y%m%dT%H%M%SZ"
    )
    item_root = (
        ROOT
        / "assets"
        / "projects"
        / project_code
        / "work_items"
        / work_item_id
    )
    if not item_root.is_dir():
        print(f"工作项不存在: {item_root}")
        return 2

    started_at = utc_now()
    before_hash = work_item_fingerprint(item_root)
    common = [
        "--project-code",
        project_code,
        "--work-item-id",
        work_item_id,
        "--run-id",
        run_id,
    ]
    commands = [
        (
            "deterministic_harness",
            [
                sys.executable,
                str(ROOT / "scripts" / "run_work_item_pipeline.py"),
                "start",
                *common,
                "--work-item-level",
                args.work_item_level,
                "--strict",
                "--stop-at",
                "strict_gate",
            ],
        ),
        (
            "run_audit",
            [
                sys.executable,
                str(ROOT / "scripts" / "run_work_item_pipeline.py"),
                "audit-run",
                *common,
            ],
        ),
        (
            "golden_eval",
            [
                sys.executable,
                str(ROOT / "scripts" / "run_eval_suite.py"),
                "--tier",
                "golden",
            ],
        ),
        (
            "quality_baseline",
            [
                sys.executable,
                str(ROOT / "scripts" / "run_quality_baseline.py"),
            ],
        ),
    ]
    results = [
        run_command(command_id, argv, args.command_timeout)
        for command_id, argv in commands
    ]
    after_hash = work_item_fingerprint(item_root)
    unchanged = before_hash == after_hash
    report = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "project_code": project_code,
        "work_item_id": work_item_id,
        "started_at": started_at,
        "completed_at": utc_now(),
        "passed": all(result["passed"] for result in results) and unchanged,
        "formal_assets_unchanged": unchanged,
        "before_hash": before_hash,
        "after_hash": after_hash,
        "commands": results,
    }
    validate_named(report, "harness_closeout_report.schema.json")
    report_path = (
        item_root
        / ".generation"
        / "runs"
        / run_id
        / "closeout_report.json"
    )
    atomic_write_json(report_path, report)
    print(f"closeout_run_id: {run_id}")
    print(f"result: {'PASS' if report['passed'] else 'FAIL'}")
    print(f"formal_assets_unchanged: {unchanged}")
    for result in results:
        print(
            f"- {result['id']}: "
            f"{'PASS' if result['passed'] else 'FAIL'} "
            f"(exit={result['exit_code']}, {result['duration_ms']}ms)"
        )
    print(f"report: {report_path.relative_to(ROOT)}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
