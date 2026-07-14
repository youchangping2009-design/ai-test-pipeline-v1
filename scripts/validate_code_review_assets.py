#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(data: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")

    if expected_type == "object":
        if not isinstance(data, dict):
            return [f"{path} 应为 object，实际为 {type(data).__name__}"]
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                errors.append(f"{path} 缺少必填字段: {key}")
        properties = schema.get("properties", {})
        additional_allowed = schema.get("additionalProperties", True)
        for key, value in data.items():
            child_path = f"{path}.{key}"
            if key in properties:
                errors.extend(validate_schema(value, properties[key], child_path))
            elif additional_allowed is False:
                errors.append(f"{child_path} 不允许存在")
        return errors

    if expected_type == "string":
        if not isinstance(data, str):
            return [f"{path} 应为 string，实际为 {type(data).__name__}"]
        enum_values = schema.get("enum")
        if enum_values and data not in enum_values:
            errors.append(f"{path} 不在允许枚举中: {data}")
        return errors

    if expected_type == "boolean":
        if not isinstance(data, bool):
            return [f"{path} 应为 boolean，实际为 {type(data).__name__}"]
        return errors

    if expected_type == "array":
        if not isinstance(data, list):
            return [f"{path} 应为 array，实际为 {type(data).__name__}"]
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(data):
                errors.extend(validate_schema(item, item_schema, f"{path}[{index}]"))
        return errors

    return errors


def validate_review_markdown(path: Path, review_type: str) -> list[str]:
    content = path.read_text(encoding="utf-8")
    required_headings = [
        "# Code Review",
        "## Review Scope",
        "## Findings",
        "## Coverage Mapping",
        "## Invalid Or Stale Cases",
        "## Manual Confirmation",
    ]
    errors: list[str] = []
    for heading in required_headings:
        if heading not in content:
            errors.append(f"{path} 缺少关键章节: {heading}")
    if f"- review_type: `{review_type}`" not in content:
        errors.append(f"{path} 缺少 review_type 标记: {review_type}")
    if "不得修改业务代码" not in content:
        errors.append(f"{path} 缺少“不得修改业务代码”约束声明")
    if "不得修改历史产出物" not in content:
        errors.append(f"{path} 缺少“不得修改历史产出物”约束声明")
    return errors


def validate_confirmation(path: Path, schema_path: Path, expected_stage: str, expected_review_type: str) -> list[str]:
    data = load_json(path)
    schema = load_json(schema_path)
    errors = validate_schema(data, schema)
    if data.get("stage") != expected_stage:
        errors.append(f"{path} stage 应为 {expected_stage}，实际为 {data.get('stage')}")
    if data.get("review_type") != expected_review_type:
        errors.append(f"{path} review_type 应为 {expected_review_type}，实际为 {data.get('review_type')}")
    if data.get("manual_confirmation_required") is not True:
        errors.append(f"{path} manual_confirmation_required 必须为 true")
    if data.get("confirmation_status") != "confirmed":
        errors.append(f"{path} confirmation_status 必须为 confirmed，当前为 {data.get('confirmation_status')}")
    if not str(data.get("confirmed_by", "")).strip():
        errors.append(f"{path} confirmed_by 不能为空")
    if not str(data.get("confirmed_at", "")).strip():
        errors.append(f"{path} confirmed_at 不能为空")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验代码评审产物与人工确认状态")
    parser.add_argument("--frontend-review", required=False, help="前端代码评审 markdown 路径")
    parser.add_argument("--frontend-confirmation", required=False, help="前端代码评审确认 JSON 路径")
    parser.add_argument("--backend-review", required=False, help="后端代码评审 markdown 路径")
    parser.add_argument("--backend-confirmation", required=False, help="后端代码评审确认 JSON 路径")
    parser.add_argument("--schema", required=False, help="代码评审确认 schema 路径")
    args = parser.parse_args()

    schema_path = (
        Path(args.schema).resolve()
        if args.schema
        else ROOT / "schemas" / "code_review_confirmation.schema.json"
    )

    checks = [
        ("frontend_code_review", "frontend_code", args.frontend_review, args.frontend_confirmation),
        ("backend_code_review", "backend_code", args.backend_review, args.backend_confirmation),
    ]
    enabled = [check for check in checks if check[2] or check[3]]
    if not enabled:
        print("请至少传入一组代码评审产物路径", file=sys.stderr)
        return 1

    errors: list[str] = []
    for stage, review_type, review_path_raw, confirmation_path_raw in enabled:
        if not (review_path_raw and confirmation_path_raw):
            errors.append(f"{stage} 必须同时提供 review 与 confirmation 文件路径")
            continue
        review_path = Path(review_path_raw).resolve()
        confirmation_path = Path(confirmation_path_raw).resolve()
        if not review_path.exists():
            errors.append(f"评审文件不存在: {review_path}")
            continue
        if not confirmation_path.exists():
            errors.append(f"确认文件不存在: {confirmation_path}")
            continue
        errors.extend(validate_review_markdown(review_path, review_type))
        errors.extend(validate_confirmation(confirmation_path, schema_path, stage, review_type))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("code_review_assets: PASS")
    if args.frontend_review:
        print("frontend_code_review: PASS")
    if args.backend_review:
        print("backend_code_review: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
