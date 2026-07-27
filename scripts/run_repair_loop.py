#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAX_REPAIRS = 2


def parse_command_json(raw: str, label: str) -> list[str]:
    try:
        value: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} 必须是 JSON 字符串数组: {exc}") from exc
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise SystemExit(f"{label} 必须是非空 JSON 字符串数组")
    return value


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


def command_matches_expectation(actual_pass: bool, expect: str) -> bool:
    if expect == "pass":
        return actual_pass
    return not actual_pass


def write_human_action(task_id: str, command: list[str], expect: str, attempts: int, output: str) -> Path:
    path = ROOT / "docs" / "roadmap" / "HUMAN_ACTION_REQUIRED.md"
    tail = "\n".join(output.splitlines()[-30:]) if output else "(无输出)"
    content = (
        "# Human Action Required\n\n"
        f"Date: {datetime.utcnow().isoformat()}Z\n"
        f"Task ID: {task_id}\n"
        "Blocker: repair loop exceeded without matching expected validation result.\n"
        "Why autonomous agent cannot decide: Automated repair either was not provided or did not make the validation command match its expected outcome within 2 repair rounds.\n"
        f"Command: {' '.join(command)}\n"
        f"Expected: {expect}\n"
        f"Attempts: {attempts}\n"
        "Options: provide a targeted repair instruction, update the fixture/asset intentionally, or confirm that the expectation should change.\n"
        "Recommended option: inspect the validation output and decide whether the product/test design asset or the expected result is authoritative.\n"
        "Impact if unresolved: The autonomous agent will not continue blind changes for this task.\n\n"
        "## Last Output Tail\n\n"
        "```text\n"
        f"{tail}\n"
        "```\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="运行有限 repair loop，最多 2 轮，不降低规则强度")
    parser.add_argument("--task-id", default="manual-repair-loop", help="任务 ID，用于报告和 human action")
    parser.add_argument("--command-json", required=True, help='校验命令 JSON 数组，例如 ["/usr/bin/python3","scripts/run_quality_baseline.py"]')
    parser.add_argument("--expect", choices=["pass", "fail"], default="pass", help="期望校验命令通过或失败")
    parser.add_argument("--repair-command-json", help="可选 repair 命令 JSON 数组。每轮失败后执行，最多 2 轮")
    parser.add_argument("--max-repairs", type=int, default=MAX_REPAIRS, help="最大 repair 轮数，硬上限为 2")
    parser.add_argument(
        "--write-human-action-on-fail",
        action="store_true",
        help="超过 repair 轮数仍失败时写入 docs/roadmap/HUMAN_ACTION_REQUIRED.md",
    )
    args = parser.parse_args()

    command = parse_command_json(args.command_json, "--command-json")
    repair_command = parse_command_json(args.repair_command_json, "--repair-command-json") if args.repair_command_json else None
    max_repairs = min(max(args.max_repairs, 0), MAX_REPAIRS)
    attempts = 0
    last_output = ""

    print("AI Test Pipeline repair loop")
    print(f"task_id: {args.task_id}")
    print(f"expect: {args.expect}")
    print(f"max_repairs: {max_repairs}")
    print("command: " + " ".join(command))
    if repair_command:
        print("repair_command: " + " ".join(repair_command))
    else:
        print("repair_command: (none)")
    print()

    while True:
        attempts += 1
        actual_pass, output = run_command(command)
        last_output = output
        actual_text = "PASS" if actual_pass else "FAIL"
        print(f"[validation attempt {attempts}] actual: {actual_text}")
        if output:
            for line in output.splitlines()[-12:]:
                print(f"  {line}")
        if command_matches_expectation(actual_pass, args.expect):
            print("repair_loop_result: matched_expected_outcome")
            return 0

        repairs_used = attempts - 1
        if repairs_used >= max_repairs or repair_command is None:
            print("repair_loop_result: exhausted")
            if args.write_human_action_on_fail:
                path = write_human_action(args.task_id, command, args.expect, attempts, last_output)
                print(f"human_action_required: {path}")
            return 1

        print(f"[repair attempt {repairs_used + 1}/{max_repairs}]")
        repair_pass, repair_output = run_command(repair_command)
        repair_text = "PASS" if repair_pass else "FAIL"
        print(f"repair_command_result: {repair_text}")
        if repair_output:
            for line in repair_output.splitlines()[-12:]:
                print(f"  {line}")


if __name__ == "__main__":
    raise SystemExit(main())
