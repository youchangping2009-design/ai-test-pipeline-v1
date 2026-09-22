#!/usr/bin/env python3
"""Reject accidental coupling between framework validation and business samples."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SAMPLE_TOKENS = ("PT" + "083", "WX-" + "YGJ")
SCAN_TARGETS = (
    "scripts",
    "tests",
    "evals",
    "START_HERE.md",
    "START_HERE_Windows.md",
    "AI_TEST_CASE_PIPELINE.md",
    "docs/autonomous_execution.md",
    "docs/operating_sop.md",
    "docs/harness_loop_closeout.md",
    "docs/target_architecture_and_roadmap.md",
    "assets/projects/README.md",
)
IGNORED_PARTS = {"__pycache__", "results"}


def text_files(target: Path):
    if target.is_file():
        yield target
        return
    for path in sorted(target.rglob("*")):
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts):
            yield path


def main() -> int:
    errors: list[str] = []
    for relative in SCAN_TARGETS:
        target = ROOT / relative
        if not target.exists():
            continue
        for path in text_files(target):
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for token in FORBIDDEN_SAMPLE_TOKENS:
                if token in content:
                    errors.append(
                        f"{path.relative_to(ROOT)} contains business sample token {token}"
                    )

    baseline = (ROOT / "scripts" / "run_quality_baseline.py").read_text(
        encoding="utf-8"
    )
    for marker in (
        "validate_work_item.py",
        "validate_project.py",
        "assets/projects/",
        "--project-code",
        "--work-item-id",
    ):
        if marker in baseline:
            errors.append(f"run_quality_baseline.py binds work-item validation: {marker}")

    suite = json.loads((ROOT / "evals" / "eval_suite.json").read_text(encoding="utf-8"))
    for tier_name, tier in suite.get("tiers", {}).items():
        for command in tier.get("commands", []):
            rendered = " ".join(str(part) for part in command)
            if any(
                marker in rendered
                for marker in ("validate_work_item.py", "validate_project.py", "assets/projects/")
            ):
                errors.append(f"eval tier {tier_name} binds a business work item: {rendered}")

    if errors:
        print("Framework sample independence validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Framework sample independence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
