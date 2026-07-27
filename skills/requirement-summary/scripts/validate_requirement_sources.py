#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


VALID_SOURCE_TYPES = {
    "local_file",
    "image",
    "feishu_doc",
    "feishu_message",
    "prototype_link",
    "public_doc",
    "markdown",
    "pdf",
    "chat_summary",
    "other",
}
VALID_STATUSES = {"available", "pending_auth", "failed", "skipped"}
SUMMARY_ARTIFACT = "inputs/requirement_summary.md"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_manifest(
    payload: dict[str, Any],
    manifest_path: Path,
    summary_path: Path | None,
    strict: bool = False,
) -> list[str]:
    errors: list[str] = []
    if payload.get("manifest_type") != "requirement_source_manifest":
        errors.append("manifest_type 必须为 requirement_source_manifest")
    if payload.get("summary_artifact") not in (None, SUMMARY_ARTIFACT):
        errors.append(f"summary_artifact 必须为 {SUMMARY_ARTIFACT}")
    if strict and payload.get("summary_artifact") != SUMMARY_ARTIFACT:
        errors.append(f"strict 主流程要求 summary_artifact={SUMMARY_ARTIFACT}")
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return errors + ["sources 必须为数组"]
    if strict and not sources:
        errors.append("strict 主流程要求 sources 至少包含一条真实需求来源")

    seen: set[str] = set()
    for index, item in enumerate(sources, start=1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 个 source 必须为对象")
            continue
        source_id = str(item.get("source_id", "")).strip()
        source_type = str(item.get("source_type", "")).strip()
        location = str(item.get("location", "")).strip()
        status = str(item.get("status", "")).strip()
        if not source_id:
            errors.append(f"第 {index} 个 source 缺少 source_id")
        elif source_id in seen:
            errors.append(f"source_id 重复: {source_id}")
        seen.add(source_id)
        if source_type not in VALID_SOURCE_TYPES:
            errors.append(f"{source_id or index} source_type 非法: {source_type}")
        if status not in VALID_STATUSES:
            errors.append(f"{source_id or index} status 非法: {status}")
        if not location:
            errors.append(f"{source_id or index} location 不能为空")
        local_artifact = str(item.get("local_artifact", "")).strip()
        if status == "available" and local_artifact:
            local_path = (manifest_path.parent.parent / local_artifact).resolve()
            if not local_path.exists():
                errors.append(f"{source_id or index} local_artifact 不存在: {local_artifact}")

    if summary_path is None or not summary_path.exists():
        if strict:
            errors.append(f"strict 主流程要求存在 {SUMMARY_ARTIFACT}")
    else:
        summary_text = summary_path.read_text(encoding="utf-8").strip()
        if not summary_text:
            errors.append(f"{SUMMARY_ARTIFACT} 存在但内容为空")
        if strict:
            required_sections = ["## 1. 资料来源", "## 2. 需求结论", "## 6. 面向测试的验收关注点"]
            for section in required_sections:
                if section not in summary_text:
                    errors.append(f"{SUMMARY_ARTIFACT} 缺少主流程章节: {section}")
            if "待补充" in summary_text or "TEMPLATE" in summary_text or "TODO" in summary_text:
                errors.append(f"{SUMMARY_ARTIFACT} 仍包含模板/占位内容")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验需求来源清单与英文 requirement_summary 输入归一化产物")
    parser.add_argument("--input", required=False, help="source_manifest.json 路径")
    parser.add_argument("--work-item-dir", required=False, help="工作项目录")
    parser.add_argument("--strict", action="store_true", help="主流程严格校验 summary 和真实来源")
    args = parser.parse_args()

    if args.input:
        manifest_path = Path(args.input).resolve()
    elif args.work_item_dir:
        manifest_path = Path(args.work_item_dir).resolve() / "inputs" / "source_manifest.json"
    else:
        raise SystemExit("Provide --input or --work-item-dir")

    if not manifest_path.exists():
        if args.strict:
            print(f"strict 主流程要求 source_manifest: {manifest_path}", file=sys.stderr)
            return 1
        print(f"source_manifest 不存在，跳过需求来源清单校验: {manifest_path}")
        return 0

    try:
        payload = read_json(manifest_path)
        if not isinstance(payload, dict):
            raise ValueError("source_manifest 必须为 JSON object")
    except Exception as exc:
        print(f"读取 source_manifest 失败: {exc}", file=sys.stderr)
        return 1

    summary_path = manifest_path.parent / "requirement_summary.md"
    errors = validate_manifest(payload, manifest_path, summary_path, strict=args.strict)
    if errors:
        print("❌ requirement source manifest 校验失败")
        for error in errors:
            print(f"- {error}")
        print(f"共发现 {len(errors)} 个问题")
        return 1

    print("✅ requirement source manifest 校验通过")
    print(f"source_count: {len(payload.get('sources', []))}")
    print(f"summary_artifact: {SUMMARY_ARTIFACT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
