#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_evals
from harness.contracts import validate_named


ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG = ROOT / "evals" / "eval_suite.json"
DEFAULT_GOLDEN_BASELINE = ROOT / "evals" / "baselines" / "golden.json"
DEFAULT_REPORT_DIR = ROOT / ".generation" / "evals"
SNAPSHOT_METRICS = (
    "fixture_count",
    "check_count",
    "expected_failure_checks",
    "command_count",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 根节点必须为对象: {path}")
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def output_tail(stdout: str, stderr: str, limit: int = 20) -> list[str]:
    combined = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
    return combined.splitlines()[-limit:] if combined else []


def fixture_fingerprint(fixture_root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        path
        for path in fixture_root.rglob("*")
        if path.is_file() and path.name.lower() != "readme.md"
    )
    if not files:
        raise ValueError(f"fixture 不存在或为空: {fixture_root}")
    for path in files:
        relative = path.relative_to(fixture_root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def count_fixture_checks(fixture_root: Path) -> tuple[int, int]:
    expected_dir = fixture_root / "expected"
    pattern_path = expected_dir / "forbidden_patterns.yml"
    if pattern_path.exists():
        forbidden, required = run_evals.parse_pattern_file(pattern_path)
        assertions = run_evals.parse_required_assertions(
            expected_dir / "required_assertions.yml"
        )
        validator_checks = 2
        gate_path = expected_dir / "testability_gate.expected.json"
        acceptance_path = expected_dir / "acceptance_examples.expected.json"
        if gate_path.exists() and acceptance_path.exists():
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            gate_items = gate.get("items", []) if isinstance(gate, dict) else []
            examples = acceptance.get("examples", []) if isinstance(acceptance, dict) else []
            if examples or any(
                isinstance(item, dict)
                and item.get("decision") == "generate_acceptance_example"
                for item in gate_items
            ):
                validator_checks += 1
        return len(forbidden) + len(required) + len(assertions) + validator_checks, 0

    if (expected_dir / "testcases.expected.md").exists():
        negative = int((expected_dir / "invalid_grouping.expected.md").exists())
        return 1 + negative, negative

    positive = fixture_root / "positive.testcases.md"
    negative = fixture_root / "negative.testcases.md"
    if positive.exists() and negative.exists():
        return 2, 1
    raise ValueError(f"无法识别 fixture 类型: {fixture_root}")


def run_fixture(fixture_id: str) -> dict[str, Any]:
    fixture_root = ROOT / "evals" / "fixtures" / fixture_id
    check_count, expected_failures = count_fixture_checks(fixture_root)
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_evals.py"), "--fixture", fixture_id],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return {
        "fixture_id": fixture_id,
        "passed": result.returncode == 0,
        "duration_ms": max(0, round((time.monotonic() - started) * 1000)),
        "check_count": check_count,
        "expected_failure_checks": expected_failures,
        "fingerprint": fixture_fingerprint(fixture_root),
        "output_tail": output_tail(result.stdout, result.stderr),
    }


def run_command(command: dict[str, Any]) -> dict[str, Any]:
    command_id = str(command.get("id", "")).strip()
    argv = command.get("argv")
    expected_exit_code = command.get("expected_exit_code", 0)
    if not command_id or not isinstance(argv, list) or not argv:
        raise ValueError(f"非法 eval command 配置: {command!r}")
    if not isinstance(expected_exit_code, int):
        raise ValueError(f"expected_exit_code 必须为整数: {command_id}")
    resolved = [
        sys.executable if str(value) == "{python}" else str(value)
        for value in argv
    ]
    started = time.monotonic()
    result = subprocess.run(
        resolved,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return {
        "command_id": command_id,
        "passed": result.returncode == expected_exit_code,
        "expected_exit_code": expected_exit_code,
        "actual_exit_code": result.returncode,
        "duration_ms": max(0, round((time.monotonic() - started) * 1000)),
        "output_tail": output_tail(result.stdout, result.stderr),
    }


def build_metrics(
    fixtures: list[dict[str, Any]],
    commands: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "fixture_count": len(fixtures),
        "fixture_passed": sum(int(item["passed"]) for item in fixtures),
        "fixture_failed": sum(int(not item["passed"]) for item in fixtures),
        "check_count": sum(int(item["check_count"]) for item in fixtures),
        "expected_failure_checks": sum(
            int(item["expected_failure_checks"]) for item in fixtures
        ),
        "command_count": len(commands),
        "command_passed": sum(int(item["passed"]) for item in commands),
        "command_failed": sum(int(not item["passed"]) for item in commands),
    }


def baseline_snapshot(
    suite_version: str,
    tier: str,
    metrics: dict[str, int],
    fixtures: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "suite_version": suite_version,
        "tier": tier,
        "metrics": {key: metrics[key] for key in SNAPSHOT_METRICS},
        "fixture_fingerprints": {
            item["fixture_id"]: item["fingerprint"] for item in fixtures
        },
    }


def compare_baseline(
    current: dict[str, Any],
    expected: dict[str, Any],
) -> list[str]:
    differences: list[str] = []
    for key in ("schema_version", "suite_version", "tier"):
        if current.get(key) != expected.get(key):
            differences.append(
                f"{key}: baseline={expected.get(key)!r}, current={current.get(key)!r}"
            )
    expected_metrics = expected.get("metrics", {})
    current_metrics = current.get("metrics", {})
    for key in SNAPSHOT_METRICS:
        if current_metrics.get(key) != expected_metrics.get(key):
            differences.append(
                f"metrics.{key}: baseline={expected_metrics.get(key)!r}, "
                f"current={current_metrics.get(key)!r}"
            )
    expected_fingerprints = expected.get("fixture_fingerprints", {})
    current_fingerprints = current.get("fixture_fingerprints", {})
    for fixture_id in sorted(set(expected_fingerprints) | set(current_fingerprints)):
        if current_fingerprints.get(fixture_id) != expected_fingerprints.get(fixture_id):
            differences.append(
                f"fixture_fingerprints.{fixture_id}: "
                f"baseline={expected_fingerprints.get(fixture_id)!r}, "
                f"current={current_fingerprints.get(fixture_id)!r}"
            )
    return differences


def resolve_baseline_path(tier: str, value: Optional[str]) -> Optional[Path]:
    if value:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path
    if tier == "golden":
        return DEFAULT_GOLDEN_BASELINE
    return None


def run_suite(
    tier: str,
    config_path: Path = DEFAULT_CONFIG,
    baseline_path: Optional[Path] = None,
    update_baseline: bool = False,
) -> dict[str, Any]:
    config = read_json(config_path)
    tiers = config.get("tiers")
    if not isinstance(tiers, dict) or tier not in tiers:
        raise ValueError(f"未知 eval tier: {tier}")
    tier_config = tiers[tier]
    fixture_ids = tier_config.get("fixtures", [])
    command_configs = tier_config.get("commands", [])
    if not isinstance(fixture_ids, list) or not fixture_ids:
        raise ValueError(f"eval tier 至少需要一个 fixture: {tier}")
    if len(fixture_ids) != len(set(fixture_ids)):
        raise ValueError(f"eval tier 存在重复 fixture: {tier}")
    if not isinstance(command_configs, list):
        raise ValueError(f"eval commands 必须为数组: {tier}")

    started_at = utc_now()
    started = time.monotonic()
    fixtures = [run_fixture(str(fixture_id)) for fixture_id in fixture_ids]
    commands = [run_command(command) for command in command_configs]
    metrics = build_metrics(fixtures, commands)
    execution_passed = metrics["fixture_failed"] == 0 and metrics["command_failed"] == 0
    snapshot = baseline_snapshot(
        str(config.get("suite_version", "")),
        tier,
        metrics,
        fixtures,
    )

    baseline = {
        "status": "not_requested",
        "path": None,
        "differences": [],
    }
    if baseline_path is not None:
        baseline["path"] = str(baseline_path.relative_to(ROOT)) if baseline_path.is_relative_to(ROOT) else str(baseline_path)
        if update_baseline:
            if not execution_passed:
                raise ValueError("Eval 未通过，禁止更新 baseline")
            atomic_write_json(baseline_path, snapshot)
            baseline["status"] = "updated"
        elif not baseline_path.exists():
            baseline["status"] = "missing"
            baseline["differences"] = [f"baseline 不存在: {baseline_path}"]
        else:
            differences = compare_baseline(snapshot, read_json(baseline_path))
            baseline["status"] = "mismatched" if differences else "matched"
            baseline["differences"] = differences

    passed = execution_passed and baseline["status"] not in {"missing", "mismatched"}
    report = {
        "schema_version": "1.0.0",
        "suite_version": str(config.get("suite_version", "")),
        "tier": tier,
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_ms": max(0, round((time.monotonic() - started) * 1000)),
        "passed": passed,
        "metrics": metrics,
        "fixtures": fixtures,
        "commands": commands,
        "baseline": baseline,
    }
    validate_named(report, "eval_suite_report.schema.json")
    return report


def print_summary(report: dict[str, Any], report_path: Path) -> None:
    metrics = report["metrics"]
    state = "PASS" if report["passed"] else "FAIL"
    print(f"eval_tier: {report['tier']}")
    print(f"result: {state}")
    print(
        "fixtures: "
        f"{metrics['fixture_passed']}/{metrics['fixture_count']} passed; "
        f"checks={metrics['check_count']}; "
        f"expected_failures={metrics['expected_failure_checks']}"
    )
    print(
        "commands: "
        f"{metrics['command_passed']}/{metrics['command_count']} passed"
    )
    print(f"baseline: {report['baseline']['status']}")
    for difference in report["baseline"]["differences"]:
        print(f"- {difference}")
    print(f"report: {report_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="运行分级 Eval 与回归门禁")
    parser.add_argument("--tier", choices=["smoke", "regression", "golden"], required=True)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--baseline", help="可选 baseline JSON；golden 默认使用仓库 baseline")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="仅在全部检查通过后显式更新 baseline",
    )
    parser.add_argument("--report", help="报告路径，默认写入 .generation/evals/")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    baseline_path = resolve_baseline_path(args.tier, args.baseline)
    if args.update_baseline and baseline_path is None:
        parser.error("--update-baseline 需要 --baseline，或使用 golden 默认 baseline")
    report_path = (
        Path(args.report)
        if args.report
        else DEFAULT_REPORT_DIR / f"{args.tier}-latest.json"
    )
    if not report_path.is_absolute():
        report_path = ROOT / report_path

    try:
        report = run_suite(
            args.tier,
            config_path=config_path,
            baseline_path=baseline_path,
            update_baseline=args.update_baseline,
        )
        atomic_write_json(report_path, report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"eval suite 执行失败: {exc}", file=sys.stderr)
        return 2
    print_summary(report, report_path)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
