from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas"


class ContractError(ValueError):
    """Raised when a Harness document violates its schema."""


def _matches_type(value: Any, expected: str) -> bool:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return expected in checks and checks[expected](value)


def validate_document(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        allowed_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_matches_type(value, item) for item in allowed_types):
            return [f"{path} 类型应为 {allowed_types}，实际为 {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} 必须等于 {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} 不在允许枚举中: {value!r}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path} 缺少必填字段: {key}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in properties:
                errors.extend(validate_document(child, properties[key], child_path))
            elif additional is False:
                errors.append(f"{child_path} 不允许存在")
            elif isinstance(additional, dict):
                errors.extend(validate_document(child, additional, child_path))

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{path} 至少需要 {min_items} 项")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, child in enumerate(value):
                errors.extend(validate_document(child, item_schema, f"{path}[{index}]"))

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            errors.append(f"{path} 长度不能小于 {min_length}")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.fullmatch(pattern, value) is None:
            errors.append(f"{path} 不匹配格式 {pattern}: {value!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            errors.append(f"{path} 不能小于 {minimum}")
        if isinstance(maximum, (int, float)) and value > maximum:
            errors.append(f"{path} 不能大于 {maximum}")

    return errors


def load_schema(schema_name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / schema_name
    return json.loads(path.read_text(encoding="utf-8"))


def validate_named(value: Any, schema_name: str) -> None:
    errors = validate_document(value, load_schema(schema_name))
    if errors:
        raise ContractError(f"{schema_name} 校验失败:\n- " + "\n- ".join(errors))


def validate_run_state(value: dict[str, Any]) -> None:
    validate_named(value, "harness_run.schema.json")
    for index, stage in enumerate(value.get("stages", [])):
        try:
            validate_named(stage, "harness_stage.schema.json")
        except ContractError as exc:
            raise ContractError(f"stages[{index}] 非法: {exc}") from exc

