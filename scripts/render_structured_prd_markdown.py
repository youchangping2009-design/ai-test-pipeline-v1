#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from structured_prd_markdown_utils import render_structured_prd_markdown


REPO_ROOT = Path(__file__).resolve().parents[1]


def normalize_project_code(project_code: str) -> str:
    normalized = project_code.strip().upper()
    if not normalized:
        raise ValueError("project_code 不能为空")
    return normalized


def normalize_work_item_id(work_item_id: str) -> str:
    normalized = "-".join(work_item_id.strip().split()).upper()
    if not normalized:
        raise ValueError("work_item_id 不能为空")
    return normalized


def resolve_from_work_item(project_code: str, work_item_id: str) -> tuple[Path, Path]:
    item_root = REPO_ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id
    return (
        item_root / "structured_prd" / "structured_prd.json",
        item_root / "structured_prd" / "structured_prd.md",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 structured_prd.json 渲染 canonical structured_prd.md")
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--structured-prd", required=False, help="structured_prd.json 路径")
    parser.add_argument("--output", required=False, help="输出 structured_prd.md 路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    structured_prd_path: Path | None = Path(args.structured_prd).resolve() if args.structured_prd else None
    output_path: Path | None = Path(args.output).resolve() if args.output else None

    if args.project_code and args.work_item_id:
        try:
            project_code = normalize_project_code(args.project_code)
            work_item_id = normalize_work_item_id(args.work_item_id)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        default_structured_prd, default_output = resolve_from_work_item(project_code, work_item_id)
        structured_prd_path = structured_prd_path or default_structured_prd
        output_path = output_path or default_output

    if not structured_prd_path or not output_path:
        print("必须提供 structured_prd 输入和输出路径，或使用 --project-code + --work-item-id。", file=sys.stderr)
        return 1

    try:
        data = json.loads(structured_prd_path.read_text(encoding="utf-8"))
        result = render_structured_prd_markdown(data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
    except Exception as exc:
        print(f"渲染 structured_prd Markdown 失败: {exc}", file=sys.stderr)
        return 1

    print(f"✅ structured_prd Markdown 已生成: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
