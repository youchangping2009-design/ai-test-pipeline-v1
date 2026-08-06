#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = "/usr/bin/python3"


@dataclass(frozen=True)
class BaselineCommand:
    name: str
    command: list[str]
    expected_pass: bool


def run_command(item: BaselineCommand) -> tuple[bool, str]:
    result = subprocess.run(
        item.command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    actual_pass = result.returncode == 0
    matched = actual_pass == item.expected_pass
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        if output:
            output += "\n"
        output += result.stderr
    return matched, output.strip()


def main() -> int:
    commands = [
        BaselineCommand(
            name="Harness runtime unit tests should pass",
            command=[
                PYTHON,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py",
            ],
            expected_pass=True,
        ),
        BaselineCommand(
            name="PT083 non-strict should pass",
            command=[
                PYTHON,
                "scripts/validate_work_item.py",
                "--project-code",
                "WX-YGJ",
                "--work-item-id",
                "PT083",
                "--skip-code-reviews",
            ],
            expected_pass=True,
        ),
        BaselineCommand(
            name="PT083 strict should pass",
            command=[
                PYTHON,
                "scripts/validate_work_item.py",
                "--project-code",
                "WX-YGJ",
                "--work-item-id",
                "PT083",
                "--skip-code-reviews",
                "--strict",
            ],
            expected_pass=True,
        ),
        BaselineCommand(
            name="Eval regression tier should pass",
            command=[
                PYTHON,
                "scripts/run_eval_suite.py",
                "--tier",
                "regression",
            ],
            expected_pass=True,
        ),
        BaselineCommand(
            name="WX-YGJ lightweight project shell should pass",
            command=[
                PYTHON,
                "scripts/validate_project.py",
                "--project-code",
                "WX-YGJ",
                "--strict",
                "--validate-work-items",
                "--skip-code-reviews",
            ],
            expected_pass=True,
        ),
    ]

    failures: list[str] = []
    print("AI Test Pipeline quality baseline")
    print(f"repo_root: {ROOT}")
    print()

    for index, item in enumerate(commands, start=1):
        expected = "PASS" if item.expected_pass else "FAIL"
        print(f"[{index}/{len(commands)}] {item.name}")
        print(f"expected: {expected}")
        print("command: " + " ".join(item.command))
        matched, output = run_command(item)
        if matched:
            print("result: OK")
        else:
            print("result: MISMATCH")
            failures.append(item.name)
        if output:
            tail_lines = output.splitlines()[-12:]
            print("output tail:")
            for line in tail_lines:
                print(f"  {line}")
        print()

    if failures:
        print("Baseline failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Baseline passed: all commands matched expected outcomes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
