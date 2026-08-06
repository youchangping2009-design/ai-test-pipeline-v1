from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from harness.artifact_workspace import ArtifactWorkspaceError
from harness.contracts import validate_named
from harness.reviewer_specs import REVIEWER_ORDER


SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}
REVIEWER_INDEX = {name: index for index, name in enumerate(REVIEWER_ORDER)}


def _normalized_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def _normalized_key_text(value: Any) -> str:
    return _normalized_text(value).casefold()


def _safe_artifact_path(raw: Any) -> str:
    value = _normalized_text(raw)
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ArtifactWorkspaceError("finding.artifact_path 必须是安全的工作项相对路径")
    return path.as_posix()


def canonicalize_finding(reviewer: str, raw: Any) -> Dict[str, Any]:
    if reviewer not in REVIEWER_INDEX or not isinstance(raw, dict):
        raise ArtifactWorkspaceError("finding 必须是已登记 Reviewer 的 JSON object")
    required = (
        "finding_type",
        "artifact_path",
        "location",
        "severity",
        "message",
        "suggestion",
        "trace_ids",
    )
    missing = [key for key in required if key not in raw]
    if missing:
        raise ArtifactWorkspaceError("finding 缺少字段: " + ", ".join(missing))
    severity = _normalized_key_text(raw["severity"])
    if severity not in SEVERITY_ORDER:
        raise ArtifactWorkspaceError("finding.severity 非法")
    trace_ids = raw["trace_ids"]
    if not isinstance(trace_ids, list):
        raise ArtifactWorkspaceError("finding.trace_ids 必须是数组")
    normalized = {
        "reviewer": reviewer,
        "finding_type": _normalized_text(raw["finding_type"]),
        "artifact_path": _safe_artifact_path(raw["artifact_path"]),
        "location": _normalized_text(raw["location"]),
        "severity": severity,
        "message": _normalized_text(raw["message"]),
        "suggestion": _normalized_text(raw["suggestion"]),
        "trace_ids": sorted(
            set(_normalized_text(value) for value in trace_ids if _normalized_text(value))
        ),
    }
    for key in ("finding_type", "location", "message", "suggestion"):
        if not normalized[key]:
            raise ArtifactWorkspaceError("finding.%s 不能为空" % key)
    identity = "\0".join(
        [
            reviewer,
            normalized["finding_type"].casefold(),
            normalized["artifact_path"].casefold(),
            normalized["location"].casefold(),
            normalized["message"].casefold(),
        ]
    )
    dedupe_identity = "\0".join(
        [
            normalized["artifact_path"].casefold(),
            normalized["location"].casefold(),
            normalized["message"].casefold(),
        ]
    )
    normalized["finding_id"] = "FND-%s-%s" % (
        reviewer.upper(),
        hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12].upper(),
    )
    normalized["dedupe_key"] = hashlib.sha256(
        dedupe_identity.encode("utf-8")
    ).hexdigest()
    finding = {
        "finding_id": normalized["finding_id"],
        "reviewer": normalized["reviewer"],
        "finding_type": normalized["finding_type"],
        "artifact_path": normalized["artifact_path"],
        "location": normalized["location"],
        "severity": normalized["severity"],
        "message": normalized["message"],
        "suggestion": normalized["suggestion"],
        "trace_ids": normalized["trace_ids"],
        "dedupe_key": normalized["dedupe_key"],
    }
    validate_named(finding, "harness_review_finding.schema.json")
    return finding


def _sort_key(finding: Dict[str, Any]) -> Tuple[int, int, str]:
    return (
        SEVERITY_ORDER[finding["severity"]],
        REVIEWER_INDEX[finding["reviewer"]],
        finding["finding_id"],
    )


def aggregate_review_bundle(
    run_id: str,
    findings_by_reviewer: Dict[str, Iterable[Dict[str, Any]]],
) -> Dict[str, Any]:
    all_findings: List[Dict[str, Any]] = []
    for reviewer in REVIEWER_ORDER:
        all_findings.extend(findings_by_reviewer.get(reviewer, []))
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for finding in all_findings:
        validate_named(finding, "harness_review_finding.schema.json")
        grouped.setdefault(finding["dedupe_key"], []).append(finding)
    kept: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    for dedupe_key in sorted(grouped):
        group = sorted(grouped[dedupe_key], key=_sort_key)
        kept.append(group[0])
        if len(group) > 1:
            conflicts.append(
                {
                    "dedupe_key": dedupe_key,
                    "kept_finding_id": group[0]["finding_id"],
                    "conflicting_finding_ids": [
                        finding["finding_id"] for finding in group[1:]
                    ],
                }
            )
    payload = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "reviewer_order": list(REVIEWER_ORDER),
        "barrier": {"required": 3, "succeeded": 3, "passed": True},
        "findings": sorted(kept, key=_sort_key),
        "conflicts": conflicts,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    payload["bundle_hash"] = hashlib.sha256(encoded).hexdigest()
    validate_named(payload, "harness_review_bundle.schema.json")
    return payload


def render_review_record(bundle: Dict[str, Any]) -> str:
    validate_named(bundle, "harness_review_bundle.schema.json")
    findings = bundle["findings"]
    blocking = any(
        finding["severity"] in {"critical", "high"} for finding in findings
    )
    lines = [
        "# Case Reviewer 评审记录",
        "",
        "## 评审结论",
        "",
        (
            "3/3 Reviewer 已完成；存在高优先级问题，需在发布审批前人工确认。"
            if blocking
            else "3/3 Reviewer 已完成；未发现阻断发布的高优先级问题。"
        ),
        "",
        "## 问题清单",
        "",
    ]
    if not findings:
        lines.append("- 无结构化问题。")
    for finding in findings:
        traces = "、".join(finding["trace_ids"]) or "-"
        lines.extend(
            [
                "### %s [%s/%s]" % (
                    finding["finding_id"],
                    finding["reviewer"],
                    finding["severity"],
                ),
                "",
                "- 类型：%s" % finding["finding_type"],
                "- 位置：`%s` / %s"
                % (finding["artifact_path"], finding["location"]),
                "- 问题：%s" % finding["message"],
                "- 建议：%s" % finding["suggestion"],
                "- Trace IDs：%s" % traces,
                "",
            ]
        )
    lines.extend(
        [
            "## 聚合信息",
            "",
            "- Bundle Hash：`%s`" % bundle["bundle_hash"],
            "- 去重冲突：%d" % len(bundle["conflicts"]),
            "",
        ]
    )
    return "\n".join(lines)
