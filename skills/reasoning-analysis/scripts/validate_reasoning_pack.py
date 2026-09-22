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
GROUNDING_CONTRACT_VERSION = "1.0"

CONTENT_COLLECTIONS = {
    "explicit_rules": ("id", "statement"),
    "implicit_rules": ("id", "statement"),
    "field_constraints": ("constraint_id", "constraint_summary"),
    "data_source_rules": ("rule_id", "statement"),
    "business_risks": ("risk_id", "risk_statement"),
    "edge_cases": ("edge_case_id", "scenario"),
    "ambiguities": ("ambiguity_id", "description"),
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 reasoning_pack.json")
    parser.add_argument("--input", required=True, help="reasoning_pack.json 路径")
    parser.add_argument(
        "--schema",
        required=False,
        default=str(ROOT / "schemas" / "reasoning_pack.schema.json"),
        help="schema 路径",
    )
    parser.add_argument(
        "--require-grounding-contract",
        action="store_true",
        help="要求当前产物声明并满足来源语义契约",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def resolve_source_path(input_path: Path, raw_path: str) -> Path | None:
    raw = Path(raw_path)
    if raw.is_absolute():
        return raw
    work_item_root = input_path.parent.parent
    candidates = [ROOT / raw, work_item_root / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def validate_semantic_grounding(
    data: dict[str, Any], input_path: Path, require_contract: bool
) -> list[str]:
    errors: list[str] = []
    contract_version = str(data.get("grounding_contract_version", "")).strip()
    if require_contract and contract_version != GROUNDING_CONTRACT_VERSION:
        errors.append(
            "grounding_contract_version: strict reasoning 要求声明 1.0 来源语义契约"
        )

    reasoning_ids: set[str] = set()
    for collection, (id_field, text_field) in CONTENT_COLLECTIONS.items():
        for index, item in enumerate(data.get(collection, [])):
            item_id = str(item.get(id_field, "")).strip()
            if item_id in reasoning_ids:
                errors.append(f"{collection}[{index}].{id_field}: 重复 ID {item_id}")
            if item_id:
                reasoning_ids.add(item_id)

            refs = item.get("source_refs", [])
            if not refs:
                errors.append(
                    f"{collection}[{index}].source_refs: {item_id or text_field} 缺少来源，不能作为正式 reasoning"
                )
                continue
            for ref_index, ref in enumerate(refs):
                prefix = f"{collection}[{index}].source_refs[{ref_index}]"
                excerpt = str(ref.get("excerpt", "")).strip()
                if not excerpt:
                    errors.append(f"{prefix}.excerpt: 来源摘录不能为空")
                raw_path = str(ref.get("path", "")).strip()
                resolved = resolve_source_path(input_path, raw_path)
                if resolved is None or not resolved.exists():
                    errors.append(f"{prefix}.path: 来源文件不存在: {raw_path}")
                    continue
                if ref.get("source_type") == "input_markdown" and excerpt:
                    try:
                        source_text = resolved.read_text(encoding="utf-8")
                    except (OSError, UnicodeError) as exc:
                        errors.append(f"{prefix}.path: 无法读取文本来源: {exc}")
                        continue
                    if normalize_text(excerpt) not in normalize_text(source_text):
                        errors.append(
                            f"{prefix}.excerpt: 摘录无法在来源文件中回查: {excerpt[:60]}"
                        )

    for collection, id_field, refs_field in [
        ("recommended_test_dimensions", "dimension_id", "related_reasoning_ids"),
        ("coverage_candidates", "candidate_id", "source_reasoning_ids"),
    ]:
        for index, item in enumerate(data.get(collection, [])):
            refs = [str(value).strip() for value in item.get(refs_field, []) if str(value).strip()]
            if contract_version == GROUNDING_CONTRACT_VERSION and not refs:
                errors.append(
                    f"{collection}[{index}].{refs_field}: {item.get(id_field, '')} 缺少 reasoning 引用"
                )
            for ref in refs:
                if ref not in reasoning_ids:
                    errors.append(
                        f"{collection}[{index}].{refs_field}: 引用了不存在的 reasoning ID {ref}"
                    )
    return errors


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    schema_path = Path(args.schema).resolve()

    try:
        data = load_json(input_path)
        schema = load_json(schema_path)
    except Exception as exc:
        print(f"读取 reasoning_pack 或 schema 失败: {exc}", file=sys.stderr)
        return 1

    if jsonschema is None:
        print("未安装 jsonschema，跳过 schema 校验", file=sys.stderr)
        return 1

    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{path}: {error.message}")

    if not errors:
        errors.extend(
            validate_semantic_grounding(
                data,
                input_path,
                require_contract=args.require_grounding_contract,
            )
        )

    if errors:
        print("reasoning_pack 校验失败:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"reasoning_pack 校验通过（含来源语义检查）: {input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
