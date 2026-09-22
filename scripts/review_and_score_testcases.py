#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.quality_gate_policy import resolve_rollout_source
from scripts.testcase_markdown_utils import parse_testcase_document
from scripts.validate_traceability_assets import build_structured_index
from scripts.validate_traceability_assets import validate_target_exists

GENERIC_TITLE_PATTERNS = [
    r"基础属性与控件定义一致",
    r"候选项展示格式正确",
    r"验证.+正确$",
]
FIDELITY_LOCATION_RULES = {
    "5s自动轮播": {
        "required_location": "must_appear_in_title",
        "terms": ["5s自动轮播"],
    },
    "每tab最多5条": {
        "required_location": "must_appear_in_expected",
        "terms": ["每tab最多5条"],
    },
    "每tab最多4条": {
        "required_location": "must_appear_in_expected",
        "terms": ["每tab最多4条"],
    },
    "单tab下弹窗不允许超过3条": {
        "required_location": "must_appear_in_expected",
        "terms": ["单tab下弹窗不允许超过3条"],
    },
    "默认关闭": {
        "required_location": "must_appear_in_expected",
        "terms": ["默认关闭", "状态默认关闭"],
    },
    "顶部tab归属": {
        "required_location": "must_appear_in_step_or_expected",
        "terms": [
            "顶部tab归属",
            "弹窗从属于顶部tab",
            "首页banner、瓷片区、金刚区均从属于顶部tab",
        ],
    },
}
DEFAULT_QUALITY_GATE_THRESHOLDS = {
    "false_traceability_rate_fail": 0.05,
    "generalized_case_rate_warn": 0.03,
    "generalized_case_count_warn": 5,
    "weak_case_rate_warn": 0.03,
    "weak_case_count_warn": 5,
    "semantic_mismatch_count_fail": 0,
    "duplicate_case_rate_warn": 0.005,
    "duplicate_case_count_warn": 1,
}

GENERIC_STEP_FRAGMENTS = (
    "规则对应字段",
    "准备业务值并填写或选择",
)
GENERIC_EXPECTED_FRAGMENTS = (
    "直接展示或响应以下结果",
)
DISPLAY_RULE_SIGNALS = (
    "展示",
    "隐藏",
    "换行",
    "可见",
    "排序",
    "候选项来自",
)
HARD_CONSTRAINT_SIGNALS = (
    "必填",
    "必选",
    "不能为空",
    "不可为空",
    "不允许",
    "必须",
    "上限",
    "下限",
    "最大",
    "最小",
    "正整数",
    "格式",
)
TITLE_ACTION_PREFIXES = (
    "尝试违反限制时阻止提交：",
    "确认跨端联动结果：",
    "确认库存检查任务处理：",
    "确认",
)


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def artifact_fingerprint(path: Path) -> dict[str, Any]:
    try:
        display_path = str(path.relative_to(ROOT))
    except ValueError:
        display_path = str(path)
    return {
        "path": display_path,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def resolve_quality_gate_config(root: Path, project_code: str, work_item_id: str) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    config: dict[str, Any] = {
        "enabled": False,
        "mode": "soft",
        "rollout_source": "legacy_report_only",
        "thresholds": dict(DEFAULT_QUALITY_GATE_THRESHOLDS),
    }
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
            manifest_gate = manifest.get("quality_gate")
            if isinstance(manifest_gate, dict):
                config["enabled"] = bool(manifest_gate.get("enabled", False))
                config["mode"] = str(manifest_gate.get("mode", "soft")).strip() or "soft"
                config["rollout_source"] = resolve_rollout_source(
                    str(manifest_gate.get("rollout_source", "new_work_item")).strip() or "new_work_item",
                    work_item_id,
                )
                thresholds = manifest_gate.get("thresholds")
                if isinstance(thresholds, dict):
                    merged = dict(DEFAULT_QUALITY_GATE_THRESHOLDS)
                    for key, value in thresholds.items():
                        if isinstance(value, (int, float)):
                            merged[key] = value
                    config["thresholds"] = merged
        except Exception:
            pass
    config["rollout_source"] = resolve_rollout_source(config["rollout_source"], work_item_id)
    if config["rollout_source"] == "pt081_pilot":
        config["enabled"] = True
        config["mode"] = "soft"
    return config


def load_testcase_rows(path: Path) -> list[dict[str, str]]:
    parsed = parse_testcase_document(path.read_text(encoding="utf-8"), strict=True)
    return parsed["rows"]


def testcase_text(row: dict[str, str]) -> str:
    return " ".join(
        [
            row.get("用例标题", ""),
            row.get("测试步骤", ""),
            row.get("预期结果", ""),
            row.get("备注", ""),
        ]
    )


def extract_coverage_ids(row: dict[str, str]) -> list[str]:
    return re.findall(r"来源coverage：([A-Z0-9-]+)", row.get("备注", ""))


def case_has_generic_title(title: str) -> bool:
    return any(re.search(pattern, title) for pattern in GENERIC_TITLE_PATTERNS)


def load_duplicate_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def infer_fidelity_target(entry: dict[str, Any]) -> dict[str, Any] | None:
    text = " ".join(
        [
            str(entry.get("title", "")).strip(),
            str(entry.get("rationale", "")).strip(),
            str(entry.get("rule_name", "")).strip(),
            " ".join(str(item).strip() for item in entry.get("planned_assertions", [])),
        ]
    )
    if "5s自动轮播" in text:
        key = "5s自动轮播"
    elif "每tab最多5条" in text:
        key = "每tab最多5条"
    elif "每tab最多4条" in text:
        key = "每tab最多4条"
    elif "单tab下弹窗不允许超过3条" in text or "不允许超过3条" in text:
        key = "单tab下弹窗不允许超过3条"
    elif "默认关闭" in text:
        key = "默认关闭"
    elif "从属于顶部tab" in text or "顶部tab归属" in text:
        key = "顶部tab归属"
    else:
        return None
    target = dict(FIDELITY_LOCATION_RULES[key])
    target["key"] = key
    target["coverage_id"] = str(entry.get("coverage_id", "")).strip()
    target["rule_name"] = str(entry.get("rule_name", "")).strip()
    target["page_name"] = str(entry.get("page_name", "")).strip()
    target["module_name"] = str(entry.get("module_name", "")).strip()
    target["feature_name"] = str(entry.get("feature_name", "")).strip()
    return target


def locate_terms(row: dict[str, str], terms: list[str]) -> list[str]:
    title = row.get("用例标题", "")
    steps = row.get("测试步骤", "")
    expected = row.get("预期结果", "")
    locations: list[str] = []
    for term in terms:
        if term and term in title and "title" not in locations:
            locations.append("title")
        if term and term in steps and "step" not in locations:
            locations.append("step")
        if term and term in expected and "expected" not in locations:
            locations.append("expected")
    return locations


def requirement_satisfied(required_location: str, locations: list[str]) -> bool:
    if required_location == "must_appear_in_title":
        return "title" in locations
    if required_location == "must_appear_in_expected":
        return "expected" in locations
    if required_location == "must_appear_in_step_or_expected":
        return "step" in locations or "expected" in locations
    return False


def build_fidelity_reports(coverage_matrix: dict[str, Any], rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    targets: list[dict[str, Any]] = []
    for entry in coverage_matrix.get("entries", []):
        target = infer_fidelity_target(entry)
        if target:
            targets.append(target)

    missing: list[dict[str, Any]] = []
    hits: list[dict[str, Any]] = []
    for target in targets:
        matched_cases: list[dict[str, Any]] = []
        for row in rows:
            if target["module_name"] and row.get("所属模块", "").strip() != target["module_name"]:
                continue
            if target["feature_name"] and row.get("所属功能点", "").strip() != target["feature_name"]:
                continue
            locations = locate_terms(row, target["terms"])
            if not locations:
                continue
            if requirement_satisfied(target["required_location"], locations):
                matched_cases.append(
                    {
                        "case_id": row.get("用例编号", ""),
                        "title": row.get("用例标题", ""),
                        "locations": locations,
                    }
                )
        target_info = {
            "fidelity_key": target["key"],
            "coverage_id": target["coverage_id"],
            "required_location": target["required_location"],
            "accepted_terms": target["terms"],
            "page_name": target["page_name"],
            "module_name": target["module_name"],
            "feature_name": target["feature_name"],
        }
        if matched_cases:
            hits.append({**target_info, "matched_testcases": matched_cases})
        else:
            missing.append(
                {
                    **target_info,
                    "reason": "高优 fidelity point 未命中要求的 title / step / expected 落点。",
                }
            )
    return missing, hits, len(missing)


def build_generalized_cases(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        title = row.get("用例标题", "").strip()
        if case_has_generic_title(title):
            items.append(
                {
                    "case_id": row.get("用例编号", ""),
                    "title": title,
                    "module_name": row.get("所属模块", ""),
                    "feature_name": row.get("所属功能点", ""),
                    "reason": "标题偏泛化，信息量不足或偏向模板性表述。"
                }
            )
    return items


def has_explicit_baseline_comparison(expected: str) -> bool:
    """识别已绑定迁移前、重试前等基线值的可判定一致性断言。"""
    return bool(
        re.search(
            r"与[^。；<\n]{0,24}(?:迁移前|重试前|认证前|首次|原始|基线)[^。；<\n]{0,12}一致",
            expected,
        )
    )


def build_weak_cases(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        title = row.get("用例标题", "").strip()
        steps = row.get("测试步骤", "").strip()
        expected = row.get("预期结果", "").strip()
        preconditions = row.get("前置条件", "").strip()
        page_name = row.get("__page_name", "").strip()
        reasons: list[str] = []
        issue_types: list[str] = []
        if "基础属性与控件定义一致" in title:
            reasons.append("字段属性型用例过多，业务信号偏弱。")
            issue_types.append("generic_field_property")
        if "未发现" in expected or (
            "一致" in expected and not has_explicit_baseline_comparison(expected)
        ):
            reasons.append("预期结果偏抽象，判定标准不够具体。")
            issue_types.append("abstract_oracle")
        matched_step_fragments = [fragment for fragment in GENERIC_STEP_FRAGMENTS if fragment in steps]
        if matched_step_fragments:
            reasons.append(f"测试步骤仍含模板占位表达：{matched_step_fragments}。")
            issue_types.append("generic_step_placeholder")
        matched_expected_fragments = [
            fragment for fragment in GENERIC_EXPECTED_FRAGMENTS if fragment in expected
        ]
        if matched_expected_fragments:
            reasons.append(f"预期结果仍含模板占位表达：{matched_expected_fragments}。")
            issue_types.append("generic_expected_placeholder")

        compound_text = " ".join((title, preconditions, steps, expected))
        compound_branch_case = (
            "三类结果" in compound_text
            or ("分别构造" in compound_text and "每类结果" in compound_text)
        )
        if compound_branch_case:
            reasons.append("单条用例包含多个可独立失败的输入或结果分支，不满足单规则单断言倾向。")
            issue_types.append("compound_branch_case")

        save_block = "不能写入" in expected or "保存失败" in expected or "提交失败" in expected
        display_rule_without_hard_constraint = (
            save_block
            and any(signal in title for signal in DISPLAY_RULE_SIGNALS)
            and not any(signal in title for signal in HARD_CONSTRAINT_SIGNALS)
            and re.search(r"超过\s*\d+", title) is None
        )
        c_end_save_action = (
            ("C端" in page_name or "C 端" in page_name)
            and save_block
            and ("【保存】" in steps or "点击保存" in steps)
        )
        if display_rule_without_hard_constraint:
            reasons.append("展示/隐藏类规则被生成为保存或提交拦截，动作与可观察结果不匹配。")
            issue_types.append("action_oracle_mismatch")
        if c_end_save_action:
            reasons.append("C端页面用例执行后台保存拦截动作，页面责任与验证动作不匹配。")
            issue_types.append("page_responsibility_mismatch")
        if reasons:
            items.append(
                {
                    "case_id": row.get("用例编号", ""),
                    "title": title,
                    "page_name": page_name,
                    "module_name": row.get("所属模块", ""),
                    "feature_name": row.get("所属功能点", ""),
                    "issue_types": list(dict.fromkeys(issue_types)),
                    "reasons": reasons,
                }
            )
    return items


def normalize_final_case_title(title: str) -> str:
    normalized = title.strip()
    for prefix in TITLE_ACTION_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break
    normalized = re.sub(r"（场景\d+）$", "", normalized).strip()
    return re.sub(r"[\s：:，,。；;（）()]", "", normalized)


def build_final_near_duplicate_groups(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        normalized_title = normalize_final_case_title(row.get("用例标题", ""))
        if not normalized_title:
            continue
        key = (
            row.get("__page_name", "").strip(),
            row.get("__section_name", "").strip(),
            normalized_title,
        )
        groups.setdefault(key, []).append(row)

    result: list[dict[str, Any]] = []
    for (page_name, section_name, normalized_title), members in groups.items():
        if len(members) < 2:
            continue
        result.append(
            {
                "page_name": page_name,
                "section_name": section_name,
                "normalized_title": normalized_title,
                "case_ids": [row.get("用例编号", "") for row in members],
                "titles": [row.get("用例标题", "") for row in members],
            }
        )
    return result


def compute_false_traceability_rate(structured_prd: dict[str, Any], traceability: dict[str, Any], testcase_ids: set[str]) -> tuple[float, list[dict[str, Any]]]:
    index = build_structured_index(structured_prd)
    invalid_records: list[dict[str, Any]] = []
    for record in traceability.get("records", []):
        reasons: list[str] = []
        missing_testcases = [case_id for case_id in record.get("testcase_ids", []) if case_id not in testcase_ids]
        if missing_testcases:
            reasons.append(f"引用不存在的 testcase: {missing_testcases}")
        for target in record.get("structured_targets", []):
            target_error = validate_target_exists(target, index)
            if target_error:
                reasons.append(target_error)
        if reasons:
            invalid_records.append(
                {
                    "record_id": record.get("record_id", ""),
                    "reasons": reasons
                }
            )
    total = len(traceability.get("records", []))
    rate = (len(invalid_records) / total) if total else 0.0
    return rate, invalid_records


def load_primary_traceability_metric(path: Path) -> tuple[float | None, str]:
    if not path.exists():
        return None, "coverage_first_traceability_missing"
    try:
        payload = read_json(path)
    except Exception:
        return None, "coverage_first_traceability_invalid"
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return None, "coverage_first_traceability_invalid"
    rate = summary.get("false_traceability_rate")
    if not isinstance(rate, (int, float)):
        return None, "coverage_first_traceability_invalid"
    return float(rate), "coverage_first_traceability"


def load_legacy_traceability_metric(
    path: Path,
    structured_prd: dict[str, Any],
    testcase_ids: set[str],
) -> tuple[float, list[dict[str, Any]]]:
    if not path.exists():
        return 0.0, []
    return compute_false_traceability_rate(
        structured_prd,
        read_json(path),
        testcase_ids,
    )


def build_quality_report(
    coverage_matrix: dict[str, Any],
    rows: list[dict[str, str]],
    generalized_cases: list[dict[str, Any]],
    missing_fidelity_points: list[dict[str, Any]],
    high_priority_fidelity_missing: int,
    duplicate_metrics: dict[str, Any],
    quality_gate: dict[str, Any],
    false_traceability_rate_primary: float,
    false_traceability_rate_legacy: float,
    traceability_metric_source: str,
    invalid_traceability_records_legacy: list[dict[str, Any]],
    field_audit: dict[str, Any],
    grouped_audit: dict[str, Any],
    weak_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    coverage_entries = coverage_matrix.get("entries", [])
    coverage_ids_in_cases = {
        coverage_id
        for row in rows
        for coverage_id in extract_coverage_ids(row)
    }

    total_rule_entries = [entry for entry in coverage_entries if entry.get("coverage_type") != "field_property"]
    covered_rule_entries = [entry for entry in total_rule_entries if entry.get("coverage_id") in coverage_ids_in_cases]

    boundary_entries = [entry for entry in coverage_entries if entry.get("coverage_type") in {"value_boundary", "invalid_input"}]
    covered_boundary_entries = [entry for entry in boundary_entries if entry.get("coverage_id") in coverage_ids_in_cases]

    data_source_entries = [
        entry for entry in coverage_entries
        if entry.get("coverage_type") in {"data_source_filter", "data_source_display", "data_source_order"}
    ]
    covered_data_source_entries = [entry for entry in data_source_entries if entry.get("coverage_id") in coverage_ids_in_cases]

    combo_coverage_ids = {
        entry.get("coverage_id")
        for entry in coverage_entries
        if entry.get("coverage_type") == "happy_path_combo"
    }
    atomic_cases = [
        row for row in rows
        if "来源 Flow：" not in row.get("备注", "")
        and not any(coverage_id in combo_coverage_ids for coverage_id in extract_coverage_ids(row))
    ]

    unresolved: list[str] = []
    if missing_fidelity_points:
        unresolved.append(f"仍有 {high_priority_fidelity_missing} 条高优 fidelity point 未命中要求的落点。")
    if false_traceability_rate_primary > 0:
        unresolved.append("coverage-first traceability 主指标仍未收敛，请优先回归 coverage_first_traceability.json。")
    if false_traceability_rate_legacy > 0:
        unresolved.append(
            f"legacy traceability 对照仍有 {len(invalid_traceability_records_legacy)} 条记录失真或指向旧 testcase，但不再决定主门禁。"
        )
    if traceability_metric_source != "coverage_first_traceability":
        unresolved.append("主门禁未能读取 coverage-first traceability 真源，请优先补齐 coverage_first_traceability.json。")
    if generalized_cases:
        unresolved.append(f"仍有 {len(generalized_cases)} 条用例标题偏泛化。")
    semantic_mismatch_count = sum(
        1
        for item in weak_cases
        if {"action_oracle_mismatch", "page_responsibility_mismatch"}
        & set(item.get("issue_types", []))
    )
    if weak_cases:
        unresolved.append(f"仍有 {len(weak_cases)} 条用例包含泛化步骤、抽象预期或语义错型。")
    if semantic_mismatch_count:
        unresolved.append(f"其中 {semantic_mismatch_count} 条存在动作/预期或页面责任错型。")
    coverage_empty_with_cases = bool(rows) and not coverage_entries
    if coverage_empty_with_cases:
        unresolved.append(
            "存在正式 testcase，但 coverage_matrix.entries 为空；当前工作项不能通过规则生成器确定性重建。"
        )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_cases": len(rows),
        "total_coverage_entries": len(coverage_entries),
        "coverage_empty_with_cases": coverage_empty_with_cases,
        "rule_coverage_rate": round(len(covered_rule_entries) / len(total_rule_entries), 4) if total_rule_entries else 1.0,
        "atomic_case_rate": round(len(atomic_cases) / len(rows), 4) if rows else 0.0,
        "boundary_coverage_rate": round(len(covered_boundary_entries) / len(boundary_entries), 4) if boundary_entries else 1.0,
        "data_source_rule_coverage_rate": round(len(covered_data_source_entries) / len(data_source_entries), 4) if data_source_entries else 1.0,
        "generalized_case_count": len(generalized_cases),
        "generalized_case_rate": round(len(generalized_cases) / len(rows), 4) if rows else 0.0,
        "weak_case_count": len(weak_cases),
        "weak_case_rate": round(len(weak_cases) / len(rows), 4) if rows else 0.0,
        "semantic_mismatch_count": semantic_mismatch_count,
        "duplicate_case_count": int(duplicate_metrics.get("duplicate_case_count", 0)),
        "duplicate_case_rate": float(duplicate_metrics.get("duplicate_case_rate", 0.0)),
        "duplicate_group_count": int(duplicate_metrics.get("duplicate_group_count", 0)),
        "duplicate_metric_basis": duplicate_metrics.get("duplicate_metric_basis", ""),
        "missing_fidelity_points": len(missing_fidelity_points),
        "high_priority_fidelity_missing": high_priority_fidelity_missing,
        "false_traceability_rate": round(false_traceability_rate_primary, 4),
        "false_traceability_rate_primary": round(false_traceability_rate_primary, 4),
        "false_traceability_rate_legacy": round(false_traceability_rate_legacy, 4),
        "traceability_metric_source": traceability_metric_source,
        "field_audit_item_count": int(field_audit.get("item_count", 0) or 0),
        "grouped_audit_group_count": int(grouped_audit.get("group_count", 0) or 0),
        "audit_artifacts_consumed": bool(field_audit or grouped_audit),
        "quality_gate": quality_gate,
        "unresolved_issues": unresolved,
    }


def compute_duplicate_metrics(
    duplicate_report: dict[str, Any],
    rows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    final_groups = build_final_near_duplicate_groups(rows or [])
    final_count = sum(len(group["case_ids"]) - 1 for group in final_groups)
    final_total = len(rows or [])
    residual = duplicate_report.get("residual_duplicate_case_count")
    residual_groups = duplicate_report.get("residual_duplicate_group_count")
    after = int(duplicate_report.get("total_cases_after_flow_append", 0) or 0)
    if isinstance(residual, int):
        rate = round((residual / after), 4) if after else 0.0
        metrics = {
            "duplicate_case_count": residual,
            "duplicate_case_rate": rate,
            "duplicate_case_source_total": after,
            "duplicate_metric_basis": "residual_after_merge",
            "duplicate_group_count": int(residual_groups or 0),
        }
    else:
        before = int(duplicate_report.get("total_case_drafts_before_merge", 0) or 0)
        reduced = int(duplicate_report.get("reduced_case_count", 0) or 0)
        rate = round((reduced / before), 4) if before else 0.0
        metrics = {
            "duplicate_case_count": reduced,
            "duplicate_case_rate": rate,
            "duplicate_case_source_total": before,
            "duplicate_metric_basis": "merged_before_after",
            "duplicate_group_count": int(duplicate_report.get("merged_group_count", 0) or 0),
        }
    metrics["final_near_duplicate_groups"] = final_groups
    metrics["final_near_duplicate_case_count"] = final_count
    if final_count > int(metrics["duplicate_case_count"]):
        metrics.update(
            {
                "duplicate_case_count": final_count,
                "duplicate_case_rate": round(final_count / final_total, 4) if final_total else 0.0,
                "duplicate_case_source_total": final_total,
                "duplicate_metric_basis": "final_testcase_semantic_signature",
                "duplicate_group_count": len(final_groups),
            }
        )
    return metrics


def evaluate_quality_gate(
    quality_gate_config: dict[str, Any],
    generalized_case_rate: float,
    generalized_case_count: int,
    duplicate_case_rate: float,
    duplicate_case_count: int,
    false_traceability_rate_primary: float,
    traceability_metric_source: str,
    high_priority_fidelity_missing: int,
    weak_case_rate: float,
    weak_case_count: int,
    semantic_mismatch_count: int,
) -> dict[str, Any]:
    thresholds = quality_gate_config.get("thresholds", {})
    warnings: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    if traceability_metric_source != "coverage_first_traceability":
        failures.append(
            {
                "metric": "traceability_metric_source",
                "actual": traceability_metric_source,
                "threshold": "coverage_first_traceability",
                "artifact": "traceability/coverage_first_traceability.json",
                "reason": "主门禁未读取 coverage-first traceability 真源，当前结果不可作为正式放行依据。",
            }
        )
    elif false_traceability_rate_primary > float(thresholds.get("false_traceability_rate_fail", 0.05)):
        failures.append(
            {
                "metric": "false_traceability_rate_primary",
                "actual": round(false_traceability_rate_primary, 4),
                "threshold": thresholds.get("false_traceability_rate_fail"),
                "artifact": "traceability/coverage_first_traceability.json",
                "reason": "coverage-first traceability 主指标超阈值，请优先回归 coverage_first_traceability.json。",
            }
        )
    if high_priority_fidelity_missing > 0:
        failures.append(
            {
                "metric": "high_priority_fidelity_missing",
                "actual": high_priority_fidelity_missing,
                "threshold": 0,
                "artifact": "reviews/missing_fidelity_points.json",
                "reason": "仍有高优 fidelity point 未命中要求的落点。",
            }
        )
    if semantic_mismatch_count > int(thresholds.get("semantic_mismatch_count_fail", 0)):
        failures.append(
            {
                "metric": "semantic_mismatch_count",
                "actual": semantic_mismatch_count,
                "threshold": thresholds.get("semantic_mismatch_count_fail", 0),
                "artifact": "reviews/weak_cases.json",
                "reason": "存在展示规则被生成为保存拦截，或页面责任与验证动作不匹配的用例。",
            }
        )
    if (
        generalized_case_rate > float(thresholds.get("generalized_case_rate_warn", 0.03))
        or generalized_case_count > int(thresholds.get("generalized_case_count_warn", 5))
    ):
        warnings.append(
            {
                "metric": "generalized_case",
                "actual": {
                    "rate": round(generalized_case_rate, 4),
                    "count": generalized_case_count,
                },
                "threshold": {
                    "rate": thresholds.get("generalized_case_rate_warn"),
                    "count": thresholds.get("generalized_case_count_warn"),
                },
                "artifact": "reviews/generalized_cases.json",
                "reason": "主集仍存在泛化标题或低信息量用例。",
            }
        )
    if (
        duplicate_case_rate > float(thresholds.get("duplicate_case_rate_warn", 0.005))
        or duplicate_case_count > int(thresholds.get("duplicate_case_count_warn", 1))
    ):
        warnings.append(
            {
                "metric": "duplicate_case",
                "actual": {
                    "rate": round(duplicate_case_rate, 4),
                    "count": duplicate_case_count,
                },
                "threshold": {
                    "rate": thresholds.get("duplicate_case_rate_warn"),
                    "count": thresholds.get("duplicate_case_count_warn"),
                },
                "artifact": "reviews/quality_report.json#final_near_duplicate_groups",
                "reason": "去重后仍存在重复/近重复残留，建议继续收敛主集。",
            }
        )
    if (
        weak_case_rate > float(thresholds.get("weak_case_rate_warn", 0.03))
        or weak_case_count > int(thresholds.get("weak_case_count_warn", 5))
    ):
        warnings.append(
            {
                "metric": "weak_case",
                "actual": {"rate": round(weak_case_rate, 4), "count": weak_case_count},
                "threshold": {
                    "rate": thresholds.get("weak_case_rate_warn"),
                    "count": thresholds.get("weak_case_count_warn"),
                },
                "artifact": "reviews/weak_cases.json",
                "reason": "主集仍包含泛化步骤、抽象预期或语义错型用例。",
            }
        )

    if not quality_gate_config.get("enabled", False):
        status = "report_only"
    elif failures:
        status = "fail"
    elif warnings:
        status = "warning"
    else:
        status = "pass"

    return {
        "enabled": bool(quality_gate_config.get("enabled", False)),
        "mode": str(quality_gate_config.get("mode", "soft")).strip() or "soft",
        "rollout_source": str(quality_gate_config.get("rollout_source", "")).strip(),
        "status": status,
        "thresholds": thresholds,
        "warnings": warnings,
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读产出 fidelity / weak_cases / generalized_cases / quality_report")
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--structured-prd", required=False, help="structured_prd.json 路径")
    parser.add_argument("--coverage-matrix", required=False, help="coverage_matrix.json 路径")
    parser.add_argument("--testcases", required=False, help="testcases.md 路径")
    parser.add_argument("--traceability", required=False, help="traceability_matrix.json 路径")
    parser.add_argument("--coverage-first-traceability", required=False, help="coverage_first_traceability.json 路径")
    parser.add_argument("--duplicate-report", required=False, help="duplicate_case_report.json 路径")
    parser.add_argument("--field-audit", required=False, help="field_audit.json 路径")
    parser.add_argument("--grouped-audit", required=False, help="grouped_audit.json 路径")
    parser.add_argument("--output-dir", required=False, help="输出目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.project_code and args.work_item_id:
        root = resolve_work_item_root(normalize_code(args.project_code), normalize_code(args.work_item_id))
        structured_prd_path = Path(args.structured_prd).resolve() if args.structured_prd else root / "structured_prd" / "structured_prd.json"
        coverage_matrix_path = Path(args.coverage_matrix).resolve() if args.coverage_matrix else root / "coverage" / "coverage_matrix.json"
        testcase_path = (
            Path(args.testcases).resolve()
            if args.testcases
            else (
                root / "testcases" / "testcases_main.md"
                if (root / "testcases" / "testcases_main.md").exists()
                else root / "testcases" / "testcases.md"
            )
        )
        traceability_path = Path(args.traceability).resolve() if args.traceability else root / "traceability" / "traceability_matrix.json"
        coverage_first_traceability_path = Path(args.coverage_first_traceability).resolve() if args.coverage_first_traceability else root / "traceability" / "coverage_first_traceability.json"
        duplicate_report_path = Path(args.duplicate_report).resolve() if args.duplicate_report else root / "reviews" / "duplicate_case_report.json"
        field_audit_path = Path(args.field_audit).resolve() if args.field_audit else root / "testcases" / "field_audit.json"
        grouped_audit_path = Path(args.grouped_audit).resolve() if args.grouped_audit else root / "testcases" / "grouped_audit.json"
        output_dir = Path(args.output_dir).resolve() if args.output_dir else root / "reviews"
    else:
        if not (args.structured_prd and args.coverage_matrix and args.testcases and args.traceability and args.output_dir):
            raise SystemExit("必须提供 --project-code + --work-item-id，或显式提供全部输入路径与输出目录")
        structured_prd_path = Path(args.structured_prd).resolve()
        coverage_matrix_path = Path(args.coverage_matrix).resolve()
        testcase_path = Path(args.testcases).resolve()
        traceability_path = Path(args.traceability).resolve()
        coverage_first_traceability_path = Path(args.coverage_first_traceability).resolve() if args.coverage_first_traceability else traceability_path.parent / "coverage_first_traceability.json"
        duplicate_report_path = Path(args.duplicate_report).resolve() if args.duplicate_report else Path(args.output_dir).resolve() / "duplicate_case_report.json"
        field_audit_path = Path(args.field_audit).resolve() if args.field_audit else testcase_path.parent / "field_audit.json"
        grouped_audit_path = Path(args.grouped_audit).resolve() if args.grouped_audit else testcase_path.parent / "grouped_audit.json"
        output_dir = Path(args.output_dir).resolve()

    structured_prd = read_json(structured_prd_path)
    coverage_matrix = read_json(coverage_matrix_path)
    rows = load_testcase_rows(testcase_path)
    testcase_ids = {row.get("用例编号", "").strip() for row in rows if row.get("用例编号", "").strip()}
    duplicate_report = load_duplicate_report(duplicate_report_path)
    field_audit = load_duplicate_report(field_audit_path)
    grouped_audit = load_duplicate_report(grouped_audit_path)
    duplicate_metrics = compute_duplicate_metrics(duplicate_report, rows)
    quality_gate_config = resolve_quality_gate_config(root if args.project_code and args.work_item_id else output_dir.parent, normalize_code(args.project_code) if args.project_code else "", normalize_code(args.work_item_id) if args.work_item_id else "")

    missing_fidelity_points, fidelity_hit_locations, high_priority_fidelity_missing = build_fidelity_reports(coverage_matrix, rows)
    generalized_cases = build_generalized_cases(rows)
    weak_cases = build_weak_cases(rows)
    semantic_mismatch_count = sum(
        1
        for item in weak_cases
        if {"action_oracle_mismatch", "page_responsibility_mismatch"}
        & set(item.get("issue_types", []))
    )
    (
        false_traceability_rate_legacy,
        invalid_traceability_records_legacy,
    ) = load_legacy_traceability_metric(
        traceability_path,
        structured_prd,
        testcase_ids,
    )
    primary_traceability_rate, traceability_metric_source = load_primary_traceability_metric(coverage_first_traceability_path)
    false_traceability_rate_primary = primary_traceability_rate if primary_traceability_rate is not None else 0.0
    quality_gate = evaluate_quality_gate(
        quality_gate_config,
        round(len(generalized_cases) / len(rows), 4) if rows else 0.0,
        len(generalized_cases),
        duplicate_metrics["duplicate_case_rate"],
        duplicate_metrics["duplicate_case_count"],
        false_traceability_rate_primary,
        traceability_metric_source,
        high_priority_fidelity_missing,
        round(len(weak_cases) / len(rows), 4) if rows else 0.0,
        len(weak_cases),
        semantic_mismatch_count,
    )
    quality_report = build_quality_report(
        coverage_matrix,
        rows,
        generalized_cases,
        missing_fidelity_points,
        high_priority_fidelity_missing,
        duplicate_metrics,
        quality_gate,
        false_traceability_rate_primary,
        false_traceability_rate_legacy,
        traceability_metric_source,
        invalid_traceability_records_legacy,
        field_audit,
        grouped_audit,
        weak_cases,
    )
    quality_report["final_near_duplicate_groups"] = duplicate_metrics.get(
        "final_near_duplicate_groups", []
    )
    quality_report["source_artifacts"] = {
        "structured_prd": artifact_fingerprint(structured_prd_path),
        "coverage_matrix": artifact_fingerprint(coverage_matrix_path),
        "testcases": artifact_fingerprint(testcase_path),
        "coverage_first_traceability": artifact_fingerprint(
            coverage_first_traceability_path
        ),
    }

    write_json(output_dir / "missing_rules.json", missing_fidelity_points)
    write_json(output_dir / "missing_fidelity_points.json", missing_fidelity_points)
    write_json(output_dir / "fidelity_hit_locations.json", fidelity_hit_locations)
    write_json(output_dir / "weak_cases.json", weak_cases)
    write_json(output_dir / "generalized_cases.json", generalized_cases)
    write_json(output_dir / "quality_report.json", quality_report)

    print(f"missing_rules: {output_dir / 'missing_rules.json'}")
    print(f"missing_fidelity_points: {output_dir / 'missing_fidelity_points.json'}")
    print(f"fidelity_hit_locations: {output_dir / 'fidelity_hit_locations.json'}")
    print(f"weak_cases: {output_dir / 'weak_cases.json'}")
    print(f"generalized_cases: {output_dir / 'generalized_cases.json'}")
    print(f"quality_report: {output_dir / 'quality_report.json'}")
    print(json.dumps(quality_report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
