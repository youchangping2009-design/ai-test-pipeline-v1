#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


ROOT = Path(__file__).resolve().parents[3]
METADATA_FIELD_NAMES = {
    "creator_name",
    "creator",
    "created_by",
    "create_time",
    "created_time",
    "created_at",
    "modifier_name",
    "modifier",
    "modified_by",
    "modify_time",
    "modified_time",
    "update_time",
    "updated_time",
    "updated_at",
}
METADATA_TITLE_KEYWORDS = ("创建人", "创建时间", "修改时间", "更新时间", "更新人")
HIGH_PRIORITY_FIDELITY_KEYWORDS = (
    "5s自动轮播",
    "每tab最多5条",
    "每tab最多4条",
    "每tab最多3条",
    "不允许超过3条",
    "默认关闭",
    "从属于顶部tab",
    "顶部tab归属",
)


def entry_text(entry: dict[str, Any]) -> str:
    values = [
        entry.get("title", ""),
        entry.get("rationale", ""),
        entry.get("field_name", ""),
        entry.get("rule_name", ""),
        " ".join(str(item) for item in entry.get("planned_assertions", [])),
        " ".join(str(item) for item in entry.get("structured_refs", [])),
    ]
    return " ".join(str(value).strip() for value in values if str(value).strip())


def is_metadata_entry(entry: dict[str, Any]) -> bool:
    field_name = str(entry.get("field_name", "")).strip()
    title = str(entry.get("title", "")).strip()
    return field_name in METADATA_FIELD_NAMES or any(
        keyword in title for keyword in METADATA_TITLE_KEYWORDS
    )


def validate_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for index, entry in enumerate(data.get("entries", [])):
        coverage_type = str(entry.get("coverage_type", "")).strip()
        coverage_level = str(entry.get("coverage_level", "")).strip()
        emit_mode = str(entry.get("emit_mode", "")).strip()
        text = entry_text(entry)

        if coverage_type in {"data_source_filter", "data_source_order"} and coverage_level != "critical":
            errors.append(
                f"entries[{index}]: {coverage_type} 必须保持 critical，当前为 {coverage_level}"
            )

        if is_metadata_entry(entry):
            if coverage_level != "audit_only":
                errors.append(
                    f"entries[{index}]: 列表元数据字段必须为 audit_only，当前为 {coverage_level}"
                )
            if emit_mode not in {"group_audit", "drop"}:
                errors.append(
                    f"entries[{index}]: 列表元数据字段不得默认进入 audit_item/main_testcase，当前 emit_mode={emit_mode}"
                )

        if coverage_type == "field_property" and not is_metadata_entry(entry):
            if emit_mode == "main_testcase" and not any(
                keyword in text for keyword in HIGH_PRIORITY_FIDELITY_KEYWORDS
            ):
                errors.append(
                    f"entries[{index}]: 普通 field_property 不应直接进入 main_testcase"
                )

        if any(
            keyword in text for keyword in HIGH_PRIORITY_FIDELITY_KEYWORDS
        ) or re.search(r"(每tab最多\d+条|单tab下[^；，。]*不允许超过\d+条)", text):
            if coverage_level != "critical":
                errors.append(
                    f"entries[{index}]: 高优 fidelity coverage 必须为 critical，当前为 {coverage_level}"
                )
            if emit_mode != "main_testcase":
                errors.append(
                    f"entries[{index}]: 高优 fidelity coverage 必须为 main_testcase，当前为 {emit_mode}"
                )
    return errors


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 coverage_matrix.json")
    parser.add_argument("--input", required=True, help="coverage_matrix.json 路径")
    parser.add_argument(
        "--schema",
        required=False,
        default=str(ROOT / "schemas" / "coverage_matrix.schema.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    schema_path = Path(args.schema).resolve()

    try:
        data = load_json(input_path)
        schema = load_json(schema_path)
    except Exception as exc:
        print(f"读取 coverage_matrix 或 schema 失败: {exc}", file=sys.stderr)
        return 1

    if jsonschema is None:
        print("未安装 jsonschema，无法校验 coverage_matrix schema", file=sys.stderr)
        return 1

    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(
        validator.iter_errors(data), key=lambda item: list(item.path)
    ):
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{path}: {error.message}")

    errors.extend(validate_semantics(data))

    if errors:
        print("coverage_matrix 校验失败:", file=sys.stderr)
        for error in errors:
            print(f"- {error}")
        return 1

    level_counter: dict[str, int] = {}
    mode_counter: dict[str, int] = {}
    for entry in data.get("entries", []):
        coverage_level = str(entry.get("coverage_level", "")).strip()
        emit_mode = str(entry.get("emit_mode", "")).strip()
        level_counter[coverage_level] = level_counter.get(coverage_level, 0) + 1
        mode_counter[emit_mode] = mode_counter.get(emit_mode, 0) + 1

    print(f"coverage_matrix 校验通过: {input_path}")
    print("coverage_level 统计:")
    for key in sorted(level_counter):
        print(f"- {key}: {level_counter[key]}")
    print("emit_mode 统计:")
    for key in sorted(mode_counter):
        print(f"- {key}: {mode_counter[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
