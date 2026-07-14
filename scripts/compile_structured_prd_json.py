#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from structured_prd_markdown_utils import normalize_structured_prd
from structured_prd_markdown_utils import parse_structured_prd_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 structured_prd.md 编译为 structured_prd.json")
    parser.add_argument("--input", required=True, help="structured_prd.md 路径")
    parser.add_argument("--output", required=True, help="structured_prd.json 输出路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    try:
        content = input_path.read_text(encoding="utf-8")
        data = normalize_structured_prd(parse_structured_prd_markdown(content))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"编译 structured_prd.json 失败: {exc}", file=sys.stderr)
        return 1

    print(f"✅ structured_prd JSON 编译完成: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
