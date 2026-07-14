#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


ROOT = Path(__file__).resolve().parents[1]


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
    return parser.parse_args()


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

    if errors:
        print("reasoning_pack 校验失败:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"reasoning_pack 校验通过: {input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
