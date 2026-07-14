#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.testcase_markdown_utils import parse_testcase_ids_from_content


TESTCASE_ID_PATTERN = re.compile(r"\b[A-Z0-9]+(?:-[A-Z0-9]+){3,}\b")


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_testcase_ids(path: Path) -> set[str]:
    return {
        testcase_id
        for testcase_id in parse_testcase_ids_from_content(load_text(path), strict=False)
        if TESTCASE_ID_PATTERN.fullmatch(testcase_id)
    }


def extract_review_ids(content: str) -> set[str]:
    return {match.group(0) for match in TESTCASE_ID_PATTERN.finditer(content)}


def validate_review_file(label: str, review_path: Path, testcase_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not review_path.exists():
        return [f"{label} 评审文件不存在: {review_path}"]

    content = load_text(review_path)
    required_sections = [
        "# Code Review",
        "## Findings",
        "## Coverage Mapping",
        "## Invalid Or Stale Cases",
        "## Manual Confirmation",
    ]
    for section in required_sections:
        if section not in content:
            errors.append(f"{label} 缺少关键章节: {section}")

    review_ids = extract_review_ids(content)
    unknown_ids = sorted(review_ids - testcase_ids)
    for testcase_id in unknown_ids:
        errors.append(f"{label} 引用了不存在的 testcase_id: {testcase_id}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="静态检查前后端代码映证文档与 testcase 的一致性")
    parser.add_argument("--testcases", required=True, help="testcases.md 路径")
    parser.add_argument("--frontend-review", required=True, help="frontend_code_review.md 路径")
    parser.add_argument("--backend-review", required=True, help="backend_code_review.md 路径")
    args = parser.parse_args()

    testcase_path = Path(args.testcases).resolve()
    frontend_review_path = Path(args.frontend_review).resolve()
    backend_review_path = Path(args.backend_review).resolve()

    if not testcase_path.exists():
        print(f"testcases 文件不存在: {testcase_path}", file=sys.stderr)
        return 1

    testcase_ids = parse_testcase_ids(testcase_path)
    if not testcase_ids:
        print("未解析到 testcase_id", file=sys.stderr)
        return 1

    errors: list[str] = []
    errors.extend(validate_review_file("frontend_code_review", frontend_review_path, testcase_ids))
    errors.extend(validate_review_file("backend_code_review", backend_review_path, testcase_ids))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("code_mapping_static: PASS")
    print(f"testcase_ids: {len(testcase_ids)}")
    print(f"frontend_review_refs: {len(extract_review_ids(load_text(frontend_review_path)))}")
    print(f"backend_review_refs: {len(extract_review_ids(load_text(backend_review_path)))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
