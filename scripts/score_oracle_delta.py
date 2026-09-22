#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.testcase_markdown_utils import parse_testcase_ids_from_content


ASSERTION_DISPOSITIONS = {"covered", "partial", "missing"}
TESTCASE_DISPOSITIONS = {"direct_match", "requirement_regression", "context_overreach"}
ORACLE_SCOPES = {"requirement", "implementation", "risk"}
ASSERTION_CREDIT = {"covered": 1.0, "partial": 0.5, "missing": 0.0}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("oracle delta input 必须是 JSON object")
    return payload


def validate_and_score(payload: dict[str, Any], testcase_ids: set[str]) -> dict[str, Any]:
    errors: list[str] = []
    for field in ("project_code", "work_item_id"):
        if not str(payload.get(field, "")).strip():
            errors.append(f"{field} 不能为空")
    oracle = payload.get("oracle")
    if not isinstance(oracle, dict):
        errors.append("oracle 必须是对象")
    else:
        for field in ("source_url", "head_sha"):
            if not str(oracle.get(field, "")).strip():
                errors.append(f"oracle.{field} 不能为空")
    assertions = payload.get("assertions")
    testcase_assessments = payload.get("testcase_assessments")
    if not isinstance(assertions, list) or not assertions:
        errors.append("assertions 必须是非空数组")
        assertions = []
    if not isinstance(testcase_assessments, list):
        errors.append("testcase_assessments 必须是数组")
        testcase_assessments = []

    seen_assertions: set[str] = set()
    for index, item in enumerate(assertions, start=1):
        if not isinstance(item, dict):
            errors.append(f"assertions[{index}] 必须是对象")
            continue
        assertion_id = str(item.get("assertion_id", "")).strip()
        disposition = str(item.get("disposition", "")).strip()
        oracle_scope = str(item.get("oracle_scope", "requirement")).strip()
        if not str(item.get("summary", "")).strip():
            errors.append(f"{assertion_id or index} summary 不能为空")
        if not assertion_id or assertion_id in seen_assertions:
            errors.append(f"assertions[{index}] assertion_id 缺失或重复: {assertion_id}")
        seen_assertions.add(assertion_id)
        if disposition not in ASSERTION_DISPOSITIONS:
            errors.append(f"{assertion_id or index} disposition 非法: {disposition}")
        if oracle_scope not in ORACLE_SCOPES:
            errors.append(f"{assertion_id or index} oracle_scope 非法: {oracle_scope}")
        mapped = {str(value).strip() for value in item.get("testcase_ids", []) if str(value).strip()}
        unknown = sorted(mapped - testcase_ids)
        if unknown:
            errors.append(f"{assertion_id or index} 引用不存在 testcase: {unknown}")
        if disposition in {"covered", "partial"} and not mapped:
            errors.append(f"{assertion_id or index} 标记 {disposition} 但没有 testcase_ids")
        if disposition == "missing" and mapped:
            errors.append(f"{assertion_id or index} 标记 missing 时不得填写 testcase_ids")
        if disposition in {"partial", "missing"} and not item.get("design_feedback_ids"):
            errors.append(f"{assertion_id or index} 为 {disposition} 时必须关联 design_feedback_ids")

    seen_cases: set[str] = set()
    for index, item in enumerate(testcase_assessments, start=1):
        if not isinstance(item, dict):
            errors.append(f"testcase_assessments[{index}] 必须是对象")
            continue
        case_id = str(item.get("testcase_id", "")).strip()
        disposition = str(item.get("disposition", "")).strip()
        if case_id not in testcase_ids:
            errors.append(f"testcase_assessments[{index}] testcase 不存在: {case_id}")
        if case_id in seen_cases:
            errors.append(f"testcase_assessments testcase_id 重复: {case_id}")
        seen_cases.add(case_id)
        if disposition not in TESTCASE_DISPOSITIONS:
            errors.append(f"{case_id or index} disposition 非法: {disposition}")

    missing_case_assessments = sorted(testcase_ids - seen_cases)
    if missing_case_assessments:
        errors.append(f"以下正式 testcase 未完成 oracle 范围判定: {missing_case_assessments}")
    if errors:
        raise ValueError("\n".join(errors))

    assertion_counts = {key: 0 for key in sorted(ASSERTION_DISPOSITIONS)}
    for item in assertions:
        assertion_counts[item["disposition"]] += 1
    normalized_assertions = [
        {**item, "oracle_scope": str(item.get("oracle_scope", "requirement")).strip()}
        for item in assertions
    ]
    scope_metrics: dict[str, dict[str, Any]] = {}
    for oracle_scope in sorted(ORACLE_SCOPES):
        scoped_assertions = [
            item
            for item in normalized_assertions
            if item["oracle_scope"] == oracle_scope
        ]
        scoped_counts = {key: 0 for key in sorted(ASSERTION_DISPOSITIONS)}
        for item in scoped_assertions:
            scoped_counts[item["disposition"]] += 1
        scoped_earned = sum(
            ASSERTION_CREDIT[item["disposition"]]
            for item in scoped_assertions
        )
        scope_metrics[oracle_scope] = {
            "assertion_count": len(scoped_assertions),
            "assertion_disposition_counts": scoped_counts,
            "coverage_rate": (
                round(scoped_earned / len(scoped_assertions), 4)
                if scoped_assertions
                else None
            ),
        }
    testcase_counts = {key: 0 for key in sorted(TESTCASE_DISPOSITIONS)}
    for item in testcase_assessments:
        testcase_counts[item["disposition"]] += 1

    earned = sum(ASSERTION_CREDIT[item["disposition"]] for item in assertions)
    relevant = testcase_counts["direct_match"] + testcase_counts["requirement_regression"]
    return {
        "project_code": payload.get("project_code", ""),
        "work_item_id": payload.get("work_item_id", ""),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "metric_scope": "post_generation_oracle_review_only",
        "oracle": payload.get("oracle", {}),
        "oracle_assertion_count": len(assertions),
        "assertion_disposition_counts": assertion_counts,
        "oracle_coverage_rate": round(earned / len(assertions), 4),
        "oracle_scope_metrics": scope_metrics,
        "requirement_oracle_coverage_rate": scope_metrics["requirement"]["coverage_rate"],
        "implementation_oracle_coverage_rate": scope_metrics["implementation"]["coverage_rate"],
        "risk_oracle_coverage_rate": scope_metrics["risk"]["coverage_rate"],
        "testcase_count": len(testcase_ids),
        "testcase_disposition_counts": testcase_counts,
        "testcase_relevance_rate": round(relevant / len(testcase_ids), 4) if testcase_ids else 1.0,
        "assertions": normalized_assertions,
        "testcase_assessments": testcase_assessments,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="对冻结 testcase 与隔离 oracle 做独立 delta 评分")
    parser.add_argument("--input", required=True, help="人工映证后的 oracle delta JSON")
    parser.add_argument("--testcases", required=True, help="冻结的 testcases_main.md")
    parser.add_argument("--output", required=True, help="评分结果 JSON")
    args = parser.parse_args()

    try:
        payload = read_json(Path(args.input).resolve())
        testcase_ids = parse_testcase_ids_from_content(
            Path(args.testcases).resolve().read_text(encoding="utf-8"), strict=True
        )
        result = validate_and_score(payload, testcase_ids)
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"oracle delta 评分失败: {exc}", file=sys.stderr)
        return 1

    print(f"oracle_delta_score: {output}")
    print(f"oracle_coverage_rate: {result['oracle_coverage_rate']}")
    print(f"requirement_oracle_coverage_rate: {result['requirement_oracle_coverage_rate']}")
    print(f"implementation_oracle_coverage_rate: {result['implementation_oracle_coverage_rate']}")
    print(f"risk_oracle_coverage_rate: {result['risk_oracle_coverage_rate']}")
    print(f"testcase_relevance_rate: {result['testcase_relevance_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
