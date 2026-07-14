#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_traceability_consumer_path(item_root: Path) -> Path:
    adapter_path = item_root / "traceability" / "traceability_adapter.json"
    if adapter_path.exists():
        return adapter_path
    return item_root / "traceability" / "traceability_matrix.json"


def resolve_testcases_consumer_path(item_root: Path) -> Path:
    main_path = item_root / "testcases" / "testcases_main.md"
    if main_path.exists():
        return main_path
    return item_root / "testcases" / "testcases.md"


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_testcase_titles(testcases_path: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    if not testcases_path.exists():
        return titles
    for line in testcases_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| YYPT") and not line.startswith("| WX") and not line.startswith("| "):
            continue
        if line.startswith("| 用例编号") or line.startswith("|---------"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) < 4:
            continue
        testcase_id = parts[0]
        title = parts[3]
        if testcase_id:
            titles[testcase_id] = title
    return titles


def aggregate_focus(
    traceability: dict[str, Any],
    testcase_titles: dict[str, str],
    stage: str,
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"testcase_ids": [], "focus_points": set(), "binding": set()})
    accepted_stages = {stage}
    if stage == "frontend_code":
        accepted_stages.add("dual_code")
    if stage == "backend_code":
        accepted_stages.add("dual_code")

    for record in traceability.get("records", []):
        recommended = record.get("recommended_cr_stage")
        if recommended not in accepted_stages:
            continue
        testcase_ids = record.get("testcase_ids", [])
        binding = record.get("implementation_binding")
        focus_points = record.get("cr_focus_points", [])
        for testcase_id in testcase_ids:
            item = groups[testcase_id]
            item["testcase_ids"].append(testcase_id)
            if binding:
                item["binding"].add(binding)
            for point in focus_points:
                if point:
                    item["focus_points"].add(point)

    result: list[dict[str, Any]] = []
    for testcase_id, payload in sorted(groups.items()):
        result.append(
            {
                "testcase_id": testcase_id,
                "title": testcase_titles.get(testcase_id, ""),
                "implementation_binding": sorted(payload["binding"]),
                "cr_focus_points": sorted(payload["focus_points"]),
            }
        )
    return result


def build_review_request(
    stage: str,
    code_dirs: list[str],
    item_root: Path,
    focus_items: list[dict[str, Any]],
    traceability_path: Path,
) -> str:
    title = "Frontend Code Review Request" if stage == "frontend_code" else "Backend Code Review Request"
    lines = [
        f"# {title}",
        "",
        f"- stage: `{stage}`",
        "- review_policy: `不得修改业务代码，不得修改历史产出物`",
        "",
        "## Code Directories",
        "",
    ]
    for code_dir in code_dirs:
        lines.append(f"- `{code_dir}`")
    lines.extend(
        [
            "",
            "## Input Assets",
            "",
            f"- `{rel(item_root / 'structured_prd' / 'structured_prd.json')}`",
            f"- `{rel(traceability_path)}`",
            f"- `{rel(item_root / 'testcases' / 'testcases.md')}`",
            "",
            "## Review Targets",
            "",
        ]
    )
    if not focus_items:
        lines.append("- 当前 traceability 中尚未标记需要本阶段代码映证的重点，请先补充 `recommended_cr_stage` 等标记。")
    else:
        for item in focus_items:
            lines.append(f"- `{item['testcase_id']}` {item['title'] or '待补充标题'}")
            if item["implementation_binding"]:
                lines.append(f"  binding: {', '.join(item['implementation_binding'])}")
            if item["cr_focus_points"]:
                lines.append(f"  focus: {', '.join(item['cr_focus_points'])}")
    lines.extend(
        [
            "",
            "## Output Requirements",
            "",
            "- 输出到工作项 `code_reviews/` 下对应 review markdown",
            "- 不修改业务代码",
            "- 不修改历史产出物",
            "- 只记录：代码缺口、用例缺口、无效项、共享契约差异",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据代码目录和 traceability 生成前后端代码评审请求文件")
    parser.add_argument("--project-code", required=True, help="项目编码")
    parser.add_argument("--work-item-id", required=True, help="工作项 ID")
    parser.add_argument("--frontend-code-dir", action="append", default=[], help="前端代码目录，可多次传入")
    parser.add_argument("--backend-code-dir", action="append", default=[], help="后端代码目录，可多次传入")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_code = normalize_code(args.project_code)
    work_item_id = normalize_code(args.work_item_id)
    item_root = work_item_root(project_code, work_item_id)
    if not item_root.exists():
        raise SystemExit(f"工作项不存在: {item_root}")

    traceability_path = resolve_traceability_consumer_path(item_root)
    testcases_path = resolve_testcases_consumer_path(item_root)
    code_reviews_dir = item_root / "code_reviews"
    code_reviews_dir.mkdir(parents=True, exist_ok=True)

    traceability = load_json(traceability_path) if traceability_path.exists() else {"records": []}
    testcase_titles = load_testcase_titles(testcases_path)

    frontend_focus = aggregate_focus(traceability, testcase_titles, "frontend_code")
    backend_focus = aggregate_focus(traceability, testcase_titles, "backend_code")

    frontend_request_path = code_reviews_dir / "frontend_review_request.md"
    backend_request_path = code_reviews_dir / "backend_review_request.md"

    frontend_request_path.write_text(
        build_review_request("frontend_code", [str(Path(path).resolve()) for path in args.frontend_code_dir], item_root, frontend_focus, traceability_path),
        encoding="utf-8",
    )
    backend_request_path.write_text(
        build_review_request("backend_code", [str(Path(path).resolve()) for path in args.backend_code_dir], item_root, backend_focus, traceability_path),
        encoding="utf-8",
    )

    print(f"frontend_review_request: {frontend_request_path}")
    print(f"backend_review_request: {backend_request_path}")
    print(f"traceability_input: {traceability_path}")
    print(f"frontend_focus_items: {len(frontend_focus)}")
    print(f"backend_focus_items: {len(backend_focus)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
