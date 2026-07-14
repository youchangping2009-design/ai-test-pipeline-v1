#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def parse_pattern_file(path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    forbidden: list[dict[str, str]] = []
    required: list[dict[str, str]] = []
    current: list[dict[str, str]] | None = None
    current_item: dict[str, str] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "forbidden_patterns:":
            current = forbidden
            current_item = None
            continue
        if stripped == "required_patterns:":
            current = required
            current_item = None
            continue
        if current is None:
            continue
        if stripped.startswith("- id:"):
            current_item = {"id": stripped.split(":", 1)[1].strip().strip('"')}
            current.append(current_item)
            continue
        if current_item is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current_item[key.strip()] = value.strip().strip('"')

    return forbidden, required


def parse_required_assertions(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    assertions: list[dict[str, str]] = []
    current_item: dict[str, str] | None = None
    in_section = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "required_assertions:":
            in_section = True
            continue
        if not in_section:
            continue
        if stripped.startswith("- id:"):
            current_item = {"id": stripped.split(":", 1)[1].strip().strip('"')}
            assertions.append(current_item)
            continue
        if current_item is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current_item[key.strip()] = value.strip().strip('"')
    return assertions


def read_artifact(expected_dir: Path, artifact: str) -> str:
    path = expected_dir / artifact
    if not path.exists():
        raise FileNotFoundError(f"fixture artifact 不存在: {path}")
    return path.read_text(encoding="utf-8")


def read_json_artifact(expected_dir: Path, artifact: str) -> Any:
    return json.loads(read_artifact(expected_dir, artifact))


def select_items(payload: Any, selector: str) -> list[dict[str, Any]]:
    match = re.fullmatch(r"([A-Za-z0-9_]+)\[([A-Za-z0-9_]+)(=|~)(.+)\]", selector)
    if not match:
        raise ValueError(f"不支持的 selector: {selector}")
    collection_name, field_name, operator, expected = match.groups()
    collection = payload.get(collection_name) if isinstance(payload, dict) else None
    if not isinstance(collection, list):
        raise ValueError(f"selector collection 不存在或不是数组: {collection_name}")
    result: list[dict[str, Any]] = []
    for item in collection:
        if not isinstance(item, dict):
            continue
        value = item.get(field_name)
        if operator == "=" and str(value) == expected:
            result.append(item)
        elif operator == "~" and isinstance(value, list) and expected in [str(v) for v in value]:
            result.append(item)
    return result


def evaluate_required_assertions(expected_dir: Path, assertions: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for item in assertions:
        artifact = item.get("artifact", "")
        selector = item.get("selector", "")
        field = item.get("field", "")
        allowed_values = [part.strip() for part in item.get("in", "").split(",") if part.strip()]
        expects_absent = str(item.get("absent", "")).strip().lower() == "true"
        try:
            payload = read_json_artifact(expected_dir, artifact)
            matches = select_items(payload, selector)
        except Exception as exc:
            errors.append(f"[required_assertion] {item.get('id', '')}: 断言读取失败: {exc}")
            continue
        if expects_absent:
            if matches:
                errors.append(f"[required_assertion] {item.get('id', '')}: selector 不应命中但命中了: {selector} -> {artifact}")
            continue
        if not matches:
            errors.append(f"[required_assertion] {item.get('id', '')}: selector 未命中: {selector} -> {artifact}")
            continue
        normalized_allowed_values = [value.lower() for value in allowed_values]
        actual_values = [str(match.get(field, "")) for match in matches]
        normalized_actual_values = [value.lower() for value in actual_values]
        if not any(value in normalized_allowed_values for value in normalized_actual_values):
            errors.append(
                f"[required_assertion] {item.get('id', '')}: 字段 {field}={actual_values} 不在允许值 {allowed_values} -> {artifact}"
            )
    return errors


def run_expected_validators(expected_dir: Path) -> list[str]:
    gate_payload = read_json_artifact(expected_dir, "testability_gate.expected.json")
    acceptance_payload = read_json_artifact(expected_dir, "acceptance_examples.expected.json")
    examples = acceptance_payload.get("examples", []) if isinstance(acceptance_payload, dict) else []
    gate_items = gate_payload.get("items", []) if isinstance(gate_payload, dict) else []
    acceptance_required = any(
        isinstance(item, dict) and item.get("decision") == "generate_acceptance_example"
        for item in gate_items
    )
    commands = [
        [
            sys.executable,
            str(ROOT / "skills" / "test-design" / "scripts" / "validate_responsibility_map.py"),
            "--input",
            str(expected_dir / "responsibility_map.expected.json"),
            "--testability-gate",
            str(expected_dir / "testability_gate.expected.json"),
            "--case-plan",
            str(expected_dir / "case_plan.expected.json"),
        ],
        [
            sys.executable,
            str(ROOT / "skills" / "case-generation" / "scripts" / "validate_case_plan.py"),
            "--input",
            str(expected_dir / "case_plan.expected.json"),
            "--testability-gate",
            str(expected_dir / "testability_gate.expected.json"),
            "--acceptance-examples",
            str(expected_dir / "acceptance_examples.expected.json"),
            "--responsibility-map",
            str(expected_dir / "responsibility_map.expected.json"),
            "--require-examples",
            "--require-responsibilities",
        ],
    ]
    if examples or acceptance_required:
        commands.insert(
            0,
            [
                sys.executable,
                str(ROOT / "skills" / "acceptance-example" / "scripts" / "validate_acceptance_examples.py"),
                "--input",
                str(expected_dir / "acceptance_examples.expected.json"),
                "--testability-gate",
                str(expected_dir / "testability_gate.expected.json"),
            ],
        )
    errors: list[str] = []
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            output = (result.stdout + "\n" + result.stderr).strip()
            errors.append(f"[validator] {' '.join(command)}\n{output}")
    return errors


def run_fixture(fixture: str) -> int:
    fixture_root = ROOT / "evals" / "fixtures" / fixture
    expected_dir = fixture_root / "expected"
    grouping_testcases_path = expected_dir / "testcases.expected.md"
    if grouping_testcases_path.exists():
        validator = str(ROOT / "skills" / "case-generation" / "scripts" / "validate_testcase_grouping.py")
        command = [sys.executable, validator, "--input", str(grouping_testcases_path), "--strict"]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
        if result.returncode != 0:
            print(f"❌ eval fixture {fixture} 失败")
            print(output.strip())
            return 1
        invalid_grouping_path = expected_dir / "invalid_grouping.expected.md"
        invalid_output = ""
        if invalid_grouping_path.exists():
            invalid_command = [sys.executable, validator, "--input", str(invalid_grouping_path), "--strict"]
            invalid_result = subprocess.run(invalid_command, capture_output=True, text=True, encoding="utf-8")
            invalid_output = (invalid_result.stdout or "") + (("\n" + invalid_result.stderr) if invalid_result.stderr else "")
            if invalid_result.returncode == 0:
                print(f"❌ eval fixture {fixture} 失败")
                print("invalid_grouping.expected.md 预期 strict 失败，但实际通过")
                print(invalid_output.strip())
                return 1
        print(f"✅ eval fixture {fixture} 通过")
        print("validator: validate_testcase_grouping --strict")
        if output.strip():
            print(output.strip())
        if invalid_grouping_path.exists():
            print("negative_grouping: expected failure observed")
        return 0

    pattern_path = expected_dir / "forbidden_patterns.yml"
    assertions_path = expected_dir / "required_assertions.yml"
    if not pattern_path.exists():
        print(f"fixture 不存在或缺少 forbidden_patterns.yml: {pattern_path}", file=sys.stderr)
        return 1

    forbidden, required = parse_pattern_file(pattern_path)
    required_assertions = parse_required_assertions(assertions_path)
    errors: list[str] = []

    for item in forbidden:
        artifact = item.get("artifact", "")
        pattern = item.get("pattern", "")
        text = read_artifact(expected_dir, artifact)
        if re.search(pattern, text, flags=re.S):
            errors.append(f"[forbidden] {item.get('id', '')}: 命中禁止模式 {pattern} -> {artifact}")

    for item in required:
        artifact = item.get("artifact", "")
        pattern = item.get("pattern", "")
        text = read_artifact(expected_dir, artifact)
        if not re.search(pattern, text, flags=re.S):
            errors.append(f"[required] {item.get('id', '')}: 未命中必需模式 {pattern} -> {artifact}")

    errors.extend(evaluate_required_assertions(expected_dir, required_assertions))

    required_artifacts = [
        "testability_gate.expected.json",
        "acceptance_examples.expected.json",
        "responsibility_map.expected.json",
        "case_plan.expected.json",
        "forbidden_patterns.yml",
        "required_assertions.yml",
    ]
    for name in required_artifacts:
        if not (expected_dir / name).exists():
            errors.append(f"[artifact] 缺少必要 fixture 文件: {name}")
    if not any(error.startswith("[artifact]") for error in errors):
        errors.extend(run_expected_validators(expected_dir))

    if errors:
        print(f"❌ eval fixture {fixture} 失败")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"✅ eval fixture {fixture} 通过")
    print(f"forbidden_patterns: {len(forbidden)}")
    print(f"required_patterns: {len(required)}")
    print(f"required_assertions: {len(required_assertions)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 AI Test Pipeline eval/regression fixture")
    parser.add_argument("--fixture", required=False, help="fixture 名称，例如 PT083")
    parser.add_argument("--all", action="store_true", help="运行 evals/fixtures 下全部 fixture")
    args = parser.parse_args()
    if args.all:
        fixtures_root = ROOT / "evals" / "fixtures"
        fixture_names = sorted(
            path.name
            for path in fixtures_root.iterdir()
            if path.is_dir()
            and (
                (path / "expected" / "forbidden_patterns.yml").exists()
                or (path / "expected" / "testcases.expected.md").exists()
            )
        )
        if not fixture_names:
            print(f"未发现可运行 fixture: {fixtures_root}", file=sys.stderr)
            return 1
        failures: list[str] = []
        print(f"running_all_fixtures: {len(fixture_names)}")
        for fixture in fixture_names:
            print()
            code = run_fixture(fixture)
            if code != 0:
                failures.append(fixture)
        if failures:
            print("\n❌ eval --all 失败")
            for fixture in failures:
                print(f"- {fixture}")
            return 1
        print("\n✅ eval --all 通过")
        return 0
    if not args.fixture:
        parser.error("必须提供 --fixture 或 --all")
    return run_fixture(args.fixture)


if __name__ == "__main__":
    raise SystemExit(main())
