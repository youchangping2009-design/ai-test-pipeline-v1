#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CASE_PLAN_RE = re.compile(r"\bCP-\d{3,}\b")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_feedback(value: str) -> str:
    if "实现" in value or "代码" in value:
        return "implementation_gap"
    if "失效" in value or "过期" in value or "无效" in value:
        return "invalid_case"
    if "风险" in value:
        return "risk_note"
    if "确认" in value:
        return "needs_confirmation"
    if "用例" in value or "缺失" in value or "覆盖" in value:
        return "case_gap"
    return "needs_confirmation"


def parse_findings(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    findings: list[dict[str, str]] = []
    in_findings = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped == "## Findings":
            in_findings = True
            continue
        if in_findings and stripped.startswith("## "):
            break
        if not in_findings:
            continue
        if not stripped.startswith("|"):
            continue
        cols = [item.strip() for item in stripped.strip("|").split("|")]
        if len(cols) < 4:
            continue
        if cols[0] in {"序号", "---"} or all(set(item) <= {"-", ":"} for item in cols):
            continue
        finding_type = cols[1]
        description = cols[2]
        severity = cols[3]
        evidence = cols[4] if len(cols) > 4 else ""
        if not description or finding_type == "待补充":
            continue
        findings.append(
            {
                "type": finding_type,
                "description": description,
                "severity": severity,
                "evidence": evidence,
            }
        )
    return findings


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Design Feedback",
        "",
        "| feedback_id | source_review_stage | source_case_plan_ids | feedback_type | target_layer | title | finding | recommended_action | status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in payload.get("feedback_items", []):
        values = [
            item.get("feedback_id", ""),
            item.get("source_review_stage", ""),
            ",".join(item.get("source_case_plan_ids", [])),
            item.get("feedback_type", ""),
            item.get("target_layer", ""),
            item.get("title", ""),
            item.get("finding", ""),
            item.get("recommended_action", ""),
            item.get("status", ""),
        ]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in values) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="将已人工确认的代码评审 findings 转成 design_feedback")
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--work-item-id", required=True)
    args = parser.parse_args()

    project_code = args.project_code.strip().upper()
    work_item_id = args.work_item_id.strip().upper()
    item_root = ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id
    output_json = item_root / "design" / "design_feedback.json"
    output_md = item_root / "design" / "design_feedback.md"
    unmapped_output = item_root / "design" / "unmapped_code_review_findings.json"

    payload = read_json(output_json) if output_json.exists() else {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "feedback_items": [],
    }
    existing = payload.get("feedback_items", [])
    if not isinstance(existing, list):
        existing = []
    signatures = {
        (str(item.get("source_review_stage", "")), str(item.get("finding", "")))
        for item in existing
        if isinstance(item, dict)
    }
    max_id = max(
        [
            int(match.group(1))
            for item in existing
            if isinstance(item, dict)
            for match in [re.match(r"DF-(\d+)$", str(item.get("feedback_id", "")))]
            if match
        ]
        or [0]
    )

    stages = [
        ("frontend_code_review", "frontend_code_review.md", "frontend_confirmation.json"),
        ("backend_code_review", "backend_code_review.md", "backend_confirmation.json"),
    ]
    added = 0
    unmapped: list[dict[str, Any]] = []
    for stage, review_name, confirmation_name in stages:
        confirmation_path = item_root / "code_reviews" / confirmation_name
        if not confirmation_path.exists():
            continue
        confirmation = read_json(confirmation_path)
        if confirmation.get("confirmation_status") != "confirmed":
            continue
        review_path = item_root / "code_reviews" / review_name
        for finding in parse_findings(review_path):
            signature = (stage, finding["description"])
            if signature in signatures:
                continue
            max_id += 1
            case_plan_ids = sorted(set(CASE_PLAN_RE.findall(finding["description"])))
            if not case_plan_ids:
                max_id -= 1
                unmapped.append(
                    {
                        "source_review_stage": stage,
                        "source_confirmation_file": f"code_reviews/{confirmation_name}",
                        "finding": finding["description"],
                        "severity": finding["severity"],
                        "evidence": finding["evidence"],
                        "reason": "未识别到 CasePlan ID，需人工映射后才能进入 design_feedback",
                    }
                )
                continue
            existing.append(
                {
                    "feedback_id": f"DF-{max_id:03d}",
                    "source_review_stage": stage,
                    "source_confirmation_file": f"code_reviews/{confirmation_name}",
                    "source_case_plan_ids": case_plan_ids,
                    "feedback_type": classify_feedback(finding["type"]),
                    "target_layer": "case_plan",
                    "title": finding["description"][:80],
                    "finding": finding["description"],
                    "recommended_action": "由测试设计负责人确认后更新目标设计层，并重新生成下游测试资产；不得直接覆盖 testcase。",
                    "must_not_directly_overwrite_testcase": True,
                    "status": "open",
                    "severity": finding["severity"],
                    "evidence": [finding["evidence"]] if finding["evidence"] else [],
                }
            )
            signatures.add(signature)
            added += 1

    payload["project_code"] = project_code
    payload["work_item_id"] = work_item_id
    payload["feedback_items"] = existing
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(payload), encoding="utf-8")
    unmapped_output.write_text(
        json.dumps(unmapped, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"design_feedback_json: {output_json}")
    print(f"design_feedback_markdown: {output_md}")
    print(f"feedback_added: {added}")
    print(f"unmapped_findings: {len(unmapped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
