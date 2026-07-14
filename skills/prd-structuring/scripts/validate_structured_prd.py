#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.structured_prd_markdown_utils import parse_structured_prd_markdown
PRIMARY_SCHEMA_PATH = ROOT_DIR / "schemas" / "structured_prd.schema.json"
FALLBACK_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "structured_prd.schema.json"


class ValidationError(Exception):
    """Raised when structured PRD validation fails."""


def load_structured_prd(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".md":
        return parse_structured_prd_markdown(text)
    return json.loads(text)


def resolve_schema_path() -> Path:
    if PRIMARY_SCHEMA_PATH.exists():
        return PRIMARY_SCHEMA_PATH
    if FALLBACK_SCHEMA_PATH.exists():
        return FALLBACK_SCHEMA_PATH
    raise ValidationError(
        "Schema file not found. Tried "
        f"{PRIMARY_SCHEMA_PATH} and {FALLBACK_SCHEMA_PATH}."
    )


def validate_against_schema(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    if jsonschema is None:
        return []

    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{path}: {error.message}")
    return errors


def build_module_feature_index(data: dict[str, Any]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for module in data.get("modules", []):
        module_name = module.get("module_name")
        if not module_name:
            continue
        features = {
            feature.get("feature_name")
            for feature in module.get("features", [])
            if feature.get("feature_name")
        }
        index[module_name] = features
    return index


def validate_flows_business_rules(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    module_index = build_module_feature_index(data)
    flows = data.get("flows", [])

    for flow_idx, flow in enumerate(flows):
        flow_label = flow.get("flow_id") or f"flows[{flow_idx}]"
        steps = flow.get("steps", [])
        expected_step_numbers = list(range(1, len(steps) + 1))
        actual_step_numbers = [step.get("step_no") for step in steps]

        if actual_step_numbers != expected_step_numbers:
            errors.append(
                f"{flow_label}: step_no must be continuous starting from 1, "
                f"got {actual_step_numbers}"
            )

        used_modules: set[str] = set()
        for step_idx, step in enumerate(steps):
            step_label = f"{flow_label}.steps[{step_idx}]"
            module_name = step.get("module_name")
            feature_name = step.get("feature_name")

            if module_name not in module_index:
                errors.append(
                    f"{step_label}: module_name '{module_name}' does not exist in modules"
                )
                continue

            used_modules.add(module_name)
            if feature_name not in module_index[module_name]:
                errors.append(
                    f"{step_label}: feature_name '{feature_name}' does not exist under "
                    f"module '{module_name}'"
                )

        related_modules = flow.get("related_modules")
        if related_modules is not None and set(related_modules) != used_modules:
            errors.append(
                f"{flow_label}: related_modules must match step module_names, "
                f"expected {sorted(used_modules)}, got {sorted(set(related_modules))}"
            )

        if flow.get("flow_type") == "main_flow" and not flow.get("success_criteria"):
            errors.append(f"{flow_label}: main_flow must define success_criteria")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a structured PRD JSON/Markdown file.")
    parser.add_argument("--input", required=True, help="Path to the structured PRD JSON/Markdown file.")
    parser.add_argument("--schema", required=False, help="Optional path to structured PRD schema.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    schema_path = Path(args.schema).resolve() if args.schema else resolve_schema_path()

    try:
        data = load_structured_prd(input_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to load input or schema: {exc}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    errors = []
    errors.extend(validate_against_schema(data, schema))
    errors.extend(validate_flows_business_rules(data))

    if errors:
        print("Structured PRD validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Structured PRD validation passed: {input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
