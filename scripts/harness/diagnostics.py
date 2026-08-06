from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from harness.contracts import validate_named
from harness.stage_registry import ROOT


DEFAULT_ARTIFACTS = {
    "requirement_intake": "inputs/source_manifest.json",
    "evidence": "evidence/evidence_inventory.json",
    "reasoning": "analysis/reasoning_pack.json",
    "structured_prd": "structured_prd/structured_prd.json",
    "coverage": "coverage/coverage_matrix.json",
    "testability_gate": "acceptance/testability_gate.json",
    "acceptance_examples": "acceptance/acceptance_examples.json",
    "verification_responsibility_map": "design/verification_responsibility_map.json",
    "test_design_matrix": "design/test_design_matrix.json",
    "case_plan": "testcases/case_plan.json",
    "testcases": "testcases/testcases_main.md",
    "traceability": "traceability/coverage_first_traceability.json",
    "review": "reviews/review_record.md",
    "strict_gate": "manifest.json",
}

ROUTING_RULES = (
    (("source_manifest", "requirement_summary", "需求来源"), "requirement_intake"),
    (("image_evidence", "evidence_inventory", "证据"), "evidence"),
    (("reasoning_pack", "reasoning"), "reasoning"),
    (("structured_prd", "结构化 prd"), "structured_prd"),
    (("coverage_matrix", "coverage"), "coverage"),
    (("testability_gate", "testability"), "testability_gate"),
    (("acceptance_examples", "acceptance example"), "acceptance_examples"),
    (
        ("verification_responsibility_map", "responsibility map", "责任划分"),
        "verification_responsibility_map",
    ),
    (("test_design_matrix", "test design matrix", "测试设计矩阵"), "test_design_matrix"),
    (("case_plan", "case plan"), "case_plan"),
    (
        (
            "testpoints",
            "testcase_bundle",
            "testcase grouping",
            "testcase",
            "测试用例",
            "用例分组",
        ),
        "testcases",
    ),
    (("traceability", "追溯"), "traceability"),
    (("quality_report", "review_record", "review gate", "评审"), "review"),
)

ACTIONABLE_MARKERS = (
    "失败",
    "错误",
    "缺少",
    "不存在",
    "不允许",
    "不一致",
    "未覆盖",
    "重复",
    "required property",
    "additional properties",
    "invalid",
    "must be",
    "timed out",
    "timeout",
    "❌",
)


def _redact(text: str) -> str:
    redacted = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "[REDACTED_API_KEY]", text)
    redacted = re.sub(
        r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+",
        r"\1[REDACTED]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)(ATP_API_KEY\s*=\s*)[^\s]+",
        r"\1[REDACTED]",
        redacted,
    )
    return redacted[:500]


def _source_validator(command: list[str]) -> str:
    if len(command) > 1:
        return Path(command[1]).name
    return Path(command[0]).name if command else "unknown_validator"


def _normalize_path(raw_path: str) -> str:
    path = Path(raw_path)
    if path.is_absolute():
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)
    return raw_path


def _artifact_from_command(command: list[str], stage_id: str) -> str | None:
    preferred_options = (
        "--input",
        "--coverage-first-traceability",
        "--case-plan",
        "--testcases",
        "--structured-prd",
        "--evidence",
    )
    for option in preferred_options:
        if option in command:
            index = command.index(option)
            if index + 1 < len(command):
                return _normalize_path(command[index + 1])
    return DEFAULT_ARTIFACTS.get(stage_id)


def _actionable_lines(output: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in output.splitlines():
        line = re.sub(r"^[\s\-*•]+", "", raw_line).strip()
        if not line:
            continue
        lowered = line.lower()
        if any(marker in lowered for marker in ACTIONABLE_MARKERS):
            candidates.append(_redact(line))
    if not candidates:
        nonempty = [_redact(line.strip()) for line in output.splitlines() if line.strip()]
        if nonempty:
            candidates.append(nonempty[-1])
    unique: list[str] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique[:20]


def _responsible_stage(
    observed_stage_id: str,
    source_validator: str,
    message: str,
) -> str:
    if observed_stage_id != "strict_gate" and source_validator != "validate_work_item.py":
        return observed_stage_id
    searchable = f"{source_validator} {message}".lower()
    for keywords, stage_id in ROUTING_RULES:
        if any(keyword in searchable for keyword in keywords):
            return stage_id
    return observed_stage_id


def _diagnostic_code(message: str, exit_code: int) -> str:
    lowered = message.lower()
    if exit_code == 124 or "timeout" in lowered or "timed out" in lowered or "超时" in lowered:
        return "HARNESS_VALIDATOR_TIMEOUT"
    if "人工" in lowered or "待确认" in lowered:
        return "HARNESS_HUMAN_CONFIRMATION_REQUIRED"
    if "不存在" in lowered or "文件缺失" in lowered or "artifact missing" in lowered:
        return "HARNESS_ARTIFACT_MISSING"
    if "required property" in lowered or "缺少必填字段" in lowered or "必填" in lowered:
        return "HARNESS_SCHEMA_REQUIRED_FIELD"
    if "additional properties" in lowered or "不允许存在" in lowered:
        return "HARNESS_SCHEMA_ADDITIONAL_PROPERTY"
    if "enum" in lowered or "枚举" in lowered:
        return "HARNESS_SCHEMA_ENUM_INVALID"
    if "重复" in lowered or "duplicate" in lowered:
        return "HARNESS_DUPLICATE_IDENTIFIER"
    if "grouping" in lowered or "用例分组" in lowered:
        return "HARNESS_TESTCASE_GROUPING_FAILED"
    if "traceability" in lowered or "追溯" in lowered:
        return "HARNESS_TRACEABILITY_FAILED"
    return "HARNESS_VALIDATOR_FAILED"


def _repair_hint(code: str, stage_id: str, artifact_path: str | None) -> str:
    target = artifact_path or DEFAULT_ARTIFACTS.get(stage_id) or stage_id
    if code == "HARNESS_ARTIFACT_MISSING":
        return f"补齐 `{target}` 后从 {stage_id} 阶段恢复。"
    if code.startswith("HARNESS_SCHEMA_"):
        return f"按 {stage_id} 阶段 Schema 修复 `{target}`，不要降低 Validator 规则。"
    if code == "HARNESS_TESTCASE_GROUPING_FAILED":
        return "按 rules/testcase_grouping_rules.md 修复页面与板块分组后重试。"
    if code == "HARNESS_TRACEABILITY_FAILED":
        return "修复 coverage、CasePlan 与正式 testcase 的主追溯映射后重试。"
    if code == "HARNESS_HUMAN_CONFIRMATION_REQUIRED":
        return "停止自动处理并请求人工确认，不得自行补写业务规则。"
    if code == "HARNESS_VALIDATOR_TIMEOUT":
        return "检查 Validator 是否卡住或输入规模异常；确认安全后再重试。"
    return f"查看 {stage_id} 阶段日志，按 Validator 原始输出最小修复 `{target}`。"


def _location(message: str) -> str | None:
    match = re.search(r"(?:line|第)\s*(\d+)\s*(?:行)?", message, flags=re.I)
    return f"line:{match.group(1)}" if match else None


def _build_diagnostic(
    *,
    observed_stage_id: str,
    responsible_stage_id: str,
    attempt: int,
    command_index: int | None,
    exit_code: int,
    code: str,
    artifact_path: str | None,
    message: str,
    source_validator: str,
) -> dict[str, Any]:
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()[:10]
    requires_human = code == "HARNESS_HUMAN_CONFIRMATION_REQUIRED"
    diagnostic = {
        "diagnostic_id": (
            f"{observed_stage_id}-{attempt}-{command_index or 0}-{code}-{digest}"
        ),
        "code": code,
        "stage_id": responsible_stage_id,
        "observed_stage_id": observed_stage_id,
        "artifact_path": artifact_path,
        "location": _location(message),
        "severity": "error",
        "message": _redact(message),
        "repair_hint": _repair_hint(code, responsible_stage_id, artifact_path),
        "retryable": not requires_human,
        "requires_human": requires_human,
        "source_validator": source_validator,
        "command_index": command_index,
        "exit_code": exit_code,
    }
    validate_named(diagnostic, "harness_diagnostic.schema.json")
    return diagnostic


def normalize_validator_failure(
    *,
    observed_stage_id: str,
    command: list[str],
    command_index: int,
    exit_code: int,
    output: str,
    attempt: int,
) -> tuple[dict[str, Any], ...]:
    source_validator = _source_validator(command)
    diagnostics: list[dict[str, Any]] = []
    for message in _actionable_lines(output) or [f"Validator 退出码为 {exit_code}"]:
        responsible_stage_id = _responsible_stage(
            observed_stage_id,
            source_validator,
            message,
        )
        artifact_path = _artifact_from_command(command, responsible_stage_id)
        code = _diagnostic_code(message, exit_code)
        diagnostics.append(
            _build_diagnostic(
                observed_stage_id=observed_stage_id,
                responsible_stage_id=responsible_stage_id,
                attempt=attempt,
                command_index=command_index,
                exit_code=exit_code,
                code=code,
                artifact_path=artifact_path,
                message=message,
                source_validator=source_validator,
            )
        )
    return tuple(diagnostics)


def missing_artifact_diagnostics(
    *,
    stage_id: str,
    missing_paths: list[str],
    attempt: int,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        _build_diagnostic(
            observed_stage_id=stage_id,
            responsible_stage_id=stage_id,
            attempt=attempt,
            command_index=None,
            exit_code=2,
            code="HARNESS_ARTIFACT_MISSING",
            artifact_path=path,
            message=f"缺少阶段必需产物: {path}",
            source_validator="harness.stage_runner",
        )
        for path in missing_paths
    )

