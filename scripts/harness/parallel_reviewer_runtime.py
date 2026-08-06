from __future__ import annotations

import json
import subprocess
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from harness.artifact_workspace import ArtifactWorkspaceError, file_hash
from harness.contracts import ContractError, validate_named
from harness.model_gateway import ModelGateway, ModelGatewayError, ModelTurnResult
from harness.review_aggregator import (
    aggregate_review_bundle,
    canonicalize_finding,
    render_review_record,
)
from harness.reviewer_specs import REVIEWER_ORDER, REVIEWER_SPECS, ReviewerSpec
from harness.role_workspace import ROLE_BY_STAGE, MultiRoleArtifactWorkspace
from harness.state_store import atomic_write_json, fingerprint_files, utc_now
from harness.telemetry import RunTelemetry


class ParallelReviewError(RuntimeError):
    pass


class ParallelReviewerRuntime:
    def __init__(
        self,
        *,
        run_id: str,
        run_dir: Path,
        gateway: ModelGateway,
        workspace: MultiRoleArtifactWorkspace,
        telemetry: RunTelemetry,
        append_event: Callable[[str, Dict[str, Any]], None],
        max_turns_per_reviewer: int = 4,
        max_repairs_per_reviewer: int = 2,
        reviewer_timeout_seconds: int = 120,
    ) -> None:
        if not 1 <= max_turns_per_reviewer <= 8:
            raise ParallelReviewError("max_turns_per_reviewer 必须在 1..8")
        if not 0 <= max_repairs_per_reviewer <= 2:
            raise ParallelReviewError("max_repairs_per_reviewer 必须在 0..2")
        if not 1 <= reviewer_timeout_seconds <= 600:
            raise ParallelReviewError("reviewer_timeout_seconds 必须在 1..600")
        self.run_id = run_id
        self.run_dir = run_dir
        self.gateway = gateway
        self.workspace = workspace
        self.telemetry = telemetry
        self.append_event = append_event
        self.max_turns = max_turns_per_reviewer
        self.max_repairs = max_repairs_per_reviewer
        self.timeout_seconds = reviewer_timeout_seconds
        self.parallel_root = run_dir / "parallel_review"
        self.cancelled_reviewers: set[str] = set()

    def execute(self) -> Dict[str, Any]:
        input_fingerprint = self._input_fingerprint()
        launched_at = time.monotonic()
        executor = ThreadPoolExecutor(
            max_workers=3,
            thread_name_prefix="case-reviewer",
        )
        futures: Dict[str, Future[Dict[str, Any]]] = {
            spec.reviewer: executor.submit(self._run_reviewer, spec)
            for spec in REVIEWER_SPECS
        }
        results: Dict[str, Dict[str, Any]] = {}
        try:
            for reviewer in REVIEWER_ORDER:
                remaining = max(
                    0.0,
                    self.timeout_seconds - (time.monotonic() - launched_at),
                )
                try:
                    results[reviewer] = futures[reviewer].result(timeout=remaining)
                except TimeoutError:
                    self.cancelled_reviewers.add(reviewer)
                    futures[reviewer].cancel()
                    results[reviewer] = self._timeout_result(reviewer)
                except Exception as exc:
                    results[reviewer] = self._exception_result(reviewer, exc)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        if self._input_fingerprint() != input_fingerprint:
            for result in results.values():
                if result["status"] == "succeeded":
                    result["status"] = "failed"
                    result["error"] = "reviewer_staging_drift"

        for reviewer in REVIEWER_ORDER:
            self._persist_reviewer_result(results[reviewer])
        succeeded = sum(
            1 for result in results.values() if result["status"] == "succeeded"
        )
        barrier_passed = succeeded == 3
        runtime_state = self._runtime_state(
            input_fingerprint=input_fingerprint,
            results=results,
            succeeded=succeeded,
            bundle_hash=None,
        )
        if not barrier_passed:
            atomic_write_json(
                self.parallel_root / "runtime_state.json",
                runtime_state,
            )
            self.append_event(
                "parallel_review_barrier_failed",
                {"required": 3, "succeeded": succeeded},
            )
            self.telemetry.write()
            return {
                "succeeded": False,
                "stop_reason": "parallel_review_barrier_failed",
                "runtime_state": runtime_state,
            }

        findings_by_reviewer = {
            reviewer: results[reviewer]["findings"] for reviewer in REVIEWER_ORDER
        }
        bundle = aggregate_review_bundle(self.run_id, findings_by_reviewer)
        atomic_write_json(self.parallel_root / "review_bundle.json", bundle)
        self.append_event(
            "parallel_review_barrier_passed",
            {"required": 3, "succeeded": 3},
        )
        self.append_event(
            "parallel_review_bundle_created",
            {
                "bundle_hash": bundle["bundle_hash"],
                "finding_count": len(bundle["findings"]),
                "conflict_count": len(bundle["conflicts"]),
            },
        )
        review_record = render_review_record(bundle)
        proposal = self.workspace.propose_artifacts(
            ROLE_BY_STAGE["case_reviewer"],
            {"reviews/review_record.md": review_record},
        )
        self.append_event("artifact_staged", proposal)
        validation = self.workspace.validate_role(ROLE_BY_STAGE["case_reviewer"])
        self.telemetry.record_validation(
            passed=validation.passed,
            diagnostic_count=len(validation.diagnostics),
        )
        if not validation.passed:
            runtime_state = self._runtime_state(
                input_fingerprint=input_fingerprint,
                results=results,
                succeeded=3,
                bundle_hash=bundle["bundle_hash"],
                status="failed",
            )
            atomic_write_json(
                self.parallel_root / "runtime_state.json",
                runtime_state,
            )
            self.telemetry.write()
            return {
                "succeeded": False,
                "stop_reason": "parallel_review_validation_failed",
                "runtime_state": runtime_state,
                "validation": validation,
            }
        fingerprint = self.workspace.assert_role_validated(
            ROLE_BY_STAGE["case_reviewer"]
        )
        runtime_state = self._runtime_state(
            input_fingerprint=input_fingerprint,
            results=results,
            succeeded=3,
            bundle_hash=bundle["bundle_hash"],
            status="succeeded",
        )
        atomic_write_json(self.parallel_root / "runtime_state.json", runtime_state)
        self.telemetry.write()
        return {
            "succeeded": True,
            "runtime_state": runtime_state,
            "bundle": bundle,
            "validated_fingerprint": fingerprint,
            "validation": validation,
        }

    def _run_reviewer(self, spec: ReviewerSpec) -> Dict[str, Any]:
        started = time.monotonic()
        observations: List[Dict[str, Any]] = []
        actions: List[Dict[str, Any]] = []
        events: List[Dict[str, Any]] = [
            {
                "event_type": "parallel_reviewer_started",
                "payload": {"reviewer": spec.reviewer},
            }
        ]
        findings: Optional[List[Dict[str, Any]]] = None
        repairs = 0
        calls = 0
        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
        for turn in range(1, self.max_turns + 1):
            if time.monotonic() - started >= self.timeout_seconds:
                return self._failed_result(
                    spec.reviewer,
                    "timed_out",
                    "reviewer_timeout",
                    turn - 1,
                    repairs,
                    calls,
                    usage,
                    actions,
                    events,
                    findings or [],
                    started,
                )
            budget_reason = self.telemetry.reserve_model_call(spec.reviewer)
            if budget_reason:
                return self._failed_result(
                    spec.reviewer,
                    "failed",
                    budget_reason,
                    turn - 1,
                    repairs,
                    calls,
                    usage,
                    actions,
                    events,
                    findings or [],
                    started,
                )
            calls += 1
            request = self._request(spec, turn, observations, repairs)
            call_started = time.monotonic()
            turn_result: Optional[ModelTurnResult] = None
            try:
                raw = self.gateway.next_action(request)
                turn_result = (
                    raw if isinstance(raw, ModelTurnResult) else ModelTurnResult(action=raw)
                )
                if spec.reviewer in self.cancelled_reviewers:
                    self.telemetry.record_reserved_model_call(
                        duration_ms=int((time.monotonic() - call_started) * 1000),
                        result=None,
                        reviewer=spec.reviewer,
                    )
                    return self._failed_result(
                        spec.reviewer,
                        "timed_out",
                        "reviewer_timeout",
                        turn,
                        repairs,
                        calls,
                        usage,
                        actions,
                        events,
                        findings or [],
                        started,
                    )
                budget_reason = self.telemetry.record_reserved_model_call(
                    duration_ms=int((time.monotonic() - call_started) * 1000),
                    result=turn_result,
                    reviewer=spec.reviewer,
                )
                self._add_usage(usage, turn_result)
                if budget_reason:
                    return self._failed_result(
                        spec.reviewer,
                        "failed",
                        budget_reason,
                        turn,
                        repairs,
                        calls,
                        usage,
                        actions,
                        events,
                        findings or [],
                        started,
                    )
                action = turn_result.action
                validate_named(action, "harness_subagent_action.schema.json")
                if action.get("reviewer") != spec.reviewer:
                    raise ParallelReviewError("Action reviewer 与当前 Reviewer 不一致")
                actions.append(action)
                self.telemetry.record_reviewer_action(
                    spec.reviewer, str(action["action_type"])
                )
                events.append(
                    {
                        "event_type": "parallel_reviewer_action_received",
                        "payload": {
                            "reviewer": spec.reviewer,
                            "turn": turn,
                            "action_id": action["action_id"],
                            "action_type": action["action_type"],
                        },
                    }
                )
                action_type = action["action_type"]
                arguments = action["arguments"]
                if action_type == "read_artifact":
                    observation = {
                        "ok": True,
                        "action_type": action_type,
                        "result": self._read_artifact(
                            spec, self._required_string(arguments, "path")
                        ),
                    }
                elif action_type == "submit_findings":
                    raw_findings = arguments.get("findings")
                    if not isinstance(raw_findings, list):
                        raise ArtifactWorkspaceError("submit_findings.findings 必须是数组")
                    try:
                        findings = [
                            canonicalize_finding(spec.reviewer, raw_finding)
                            for raw_finding in raw_findings
                        ]
                        observation = {
                            "ok": True,
                            "action_type": action_type,
                            "result": {"finding_count": len(findings)},
                        }
                    except (ArtifactWorkspaceError, ContractError) as exc:
                        repairs += 1
                        if repairs > self.max_repairs:
                            raise ParallelReviewError(
                                "findings_repair_exhausted: %s" % exc
                            )
                        observation = {
                            "ok": False,
                            "action_type": action_type,
                            "result": {
                                "error": str(exc),
                                "repair_round": repairs,
                            },
                        }
                else:
                    if findings is None:
                        raise ParallelReviewError(
                            "finish_review 前必须 submit_findings（允许空数组）"
                        )
                    events.append(
                        {
                            "event_type": "parallel_reviewer_completed",
                            "payload": {
                                "reviewer": spec.reviewer,
                                "status": "succeeded",
                                "finding_count": len(findings),
                            },
                        }
                    )
                    return self._failed_result(
                        spec.reviewer,
                        "succeeded",
                        None,
                        turn,
                        repairs,
                        calls,
                        usage,
                        actions,
                        events,
                        findings,
                        started,
                    )
                observations.append(observation)
            except (
                ArtifactWorkspaceError,
                ContractError,
                ModelGatewayError,
                ParallelReviewError,
                subprocess.TimeoutExpired,
                TimeoutError,
            ) as exc:
                if turn_result is None:
                    self.telemetry.record_reserved_model_call(
                        duration_ms=int((time.monotonic() - call_started) * 1000),
                        result=None,
                        reviewer=spec.reviewer,
                    )
                return self._failed_result(
                    spec.reviewer,
                    "failed",
                    "%s: %s" % (type(exc).__name__, exc),
                    turn,
                    repairs,
                    calls,
                    usage,
                    actions,
                    events,
                    findings or [],
                    started,
                )
        return self._failed_result(
            spec.reviewer,
            "failed",
            "reviewer_turn_budget_exhausted",
            self.max_turns,
            repairs,
            calls,
            usage,
            actions,
            events,
            findings or [],
            started,
        )

    def _request(
        self,
        spec: ReviewerSpec,
        turn: int,
        observations: List[Dict[str, Any]],
        repairs: int,
    ) -> Dict[str, Any]:
        return {
            "protocol_version": "1.0.0",
            "run_id": self.run_id,
            "mode": "parallel_reviewer",
            "stage_id": "case_reviewer",
            "reviewer": spec.reviewer,
            "skill_path": spec.skill_path,
            "turn": turn,
            "max_turns": self.max_turns,
            "repair_rounds_used": repairs,
            "max_repair_rounds": self.max_repairs,
            "allowed_actions": [
                "read_artifact",
                "submit_findings",
                "finish_review",
            ],
            "readable_prefixes": list(spec.readable_prefixes),
            "readable_paths": list(spec.readable_paths),
            "constraints": [
                "只读当前工作项 role staging",
                "不得写 testcase、case_plan、structured_prd 或 reviews",
                "只能提交结构化 findings",
                "不得请求 shell、网络或工作项外路径",
            ],
            "observations": observations,
        }

    def _read_artifact(self, spec: ReviewerSpec, raw_path: str) -> Dict[str, Any]:
        path = Path(raw_path)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ArtifactWorkspaceError("非法 Reviewer 读取路径")
        relative = path.as_posix()
        if relative not in spec.readable_paths and not any(
            relative.startswith(prefix) for prefix in spec.readable_prefixes
        ):
            raise ArtifactWorkspaceError(
                "%s Reviewer 无权读取: %s" % (spec.reviewer, relative)
            )
        target = self.workspace.staging_root / relative
        if not target.is_file():
            raise ArtifactWorkspaceError("Reviewer 可读产物不存在: %s" % relative)
        content = target.read_text(encoding="utf-8")
        return {
            "path": relative,
            "content": content[:200_000],
            "truncated": len(content) > 200_000,
            "sha256": file_hash(target),
        }

    def _input_fingerprint(self) -> str:
        paths = []
        for path in self.workspace.staging_root.rglob("*"):
            if path.is_file():
                relative = path.relative_to(self.workspace.staging_root).as_posix()
                if any(
                    relative in spec.readable_paths
                    or any(
                        relative.startswith(prefix)
                        for prefix in spec.readable_prefixes
                    )
                    for spec in REVIEWER_SPECS
                ):
                    paths.append(relative)
        return fingerprint_files(self.workspace.staging_root, tuple(sorted(paths)))

    def _persist_reviewer_result(self, result: Dict[str, Any]) -> None:
        reviewer = result["reviewer"]
        reviewer_root = self.parallel_root / reviewer
        for index, action in enumerate(result.pop("actions"), start=1):
            path = reviewer_root / "actions" / ("turn-%02d.json" % index)
            atomic_write_json(path, action)
            self.append_event(
                "parallel_reviewer_action_received",
                {
                    "reviewer": reviewer,
                    "turn": index,
                    "action_id": action["action_id"],
                    "action_type": action["action_type"],
                },
            )
        for event in result.pop("events"):
            if event["event_type"] == "parallel_reviewer_action_received":
                continue
            self.append_event(event["event_type"], event["payload"])
        if result["status"] == "succeeded":
            payload = {
                "schema_version": "1.0.0",
                "reviewer": reviewer,
                "findings": result["findings"],
            }
            atomic_write_json(reviewer_root / "findings.json", payload)
        self.telemetry.set_reviewer_terminal(
            reviewer,
            status=result["status"],
            finding_count=len(result["findings"]),
        )
        metrics = self.telemetry.snapshot()["parallel_reviewers"][reviewer]
        for key in (
            "calls",
            "duration_ms",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cost_usd",
        ):
            result[key] = metrics[key]

    def _runtime_state(
        self,
        *,
        input_fingerprint: str,
        results: Dict[str, Dict[str, Any]],
        succeeded: int,
        bundle_hash: Optional[str],
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        reviewer_records = []
        for reviewer in REVIEWER_ORDER:
            result = results[reviewer]
            reviewer_records.append(
                {
                    key: result[key]
                    for key in (
                        "reviewer",
                        "status",
                        "turns_used",
                        "repair_rounds_used",
                        "calls",
                        "input_tokens",
                        "output_tokens",
                        "total_tokens",
                        "cost_usd",
                        "finding_count",
                        "action_count",
                        "duration_ms",
                        "error",
                    )
                }
            )
        payload = {
            "schema_version": "1.0.0",
            "run_id": self.run_id,
            "stage_id": "case_reviewer",
            "reviewer_order": list(REVIEWER_ORDER),
            "input_fingerprint": input_fingerprint,
            "reviewers": reviewer_records,
            "barrier": {
                "required": 3,
                "succeeded": succeeded,
                "passed": succeeded == 3,
            },
            "bundle_hash": bundle_hash,
            "status": status or ("succeeded" if succeeded == 3 else "failed"),
            "updated_at": utc_now(),
        }
        validate_named(payload, "harness_parallel_review_runtime.schema.json")
        return payload

    def _timeout_result(self, reviewer: str) -> Dict[str, Any]:
        return {
            "reviewer": reviewer,
            "status": "timed_out",
            "turns_used": 0,
            "repair_rounds_used": 0,
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "finding_count": 0,
            "action_count": 0,
            "duration_ms": self.timeout_seconds * 1000,
            "error": "reviewer_timeout",
            "findings": [],
            "actions": [],
            "events": [
                {
                    "event_type": "parallel_reviewer_started",
                    "payload": {"reviewer": reviewer},
                },
                {
                    "event_type": "parallel_reviewer_completed",
                    "payload": {"reviewer": reviewer, "status": "timed_out"},
                },
            ],
        }

    def _exception_result(self, reviewer: str, exc: Exception) -> Dict[str, Any]:
        return {
            **self._timeout_result(reviewer),
            "status": "failed",
            "duration_ms": 0,
            "error": "%s: %s" % (type(exc).__name__, exc),
            "events": [
                {
                    "event_type": "parallel_reviewer_started",
                    "payload": {"reviewer": reviewer},
                },
                {
                    "event_type": "parallel_reviewer_completed",
                    "payload": {
                        "reviewer": reviewer,
                        "status": "failed",
                        "error": "%s: %s" % (type(exc).__name__, exc),
                    },
                },
            ],
        }

    @staticmethod
    def _failed_result(
        reviewer: str,
        status: str,
        error: Optional[str],
        turns: int,
        repairs: int,
        calls: int,
        usage: Dict[str, Any],
        actions: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        started: float,
    ) -> Dict[str, Any]:
        if not events or events[-1]["event_type"] != "parallel_reviewer_completed":
            events.append(
                {
                    "event_type": "parallel_reviewer_completed",
                    "payload": {
                        "reviewer": reviewer,
                        "status": status,
                        "error": error,
                    },
                }
            )
        return {
            "reviewer": reviewer,
            "status": status,
            "turns_used": turns,
            "repair_rounds_used": repairs,
            "calls": calls,
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "total_tokens": usage["total_tokens"],
            "cost_usd": round(float(usage["cost_usd"]), 8),
            "finding_count": len(findings),
            "action_count": len(actions),
            "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
            "error": error,
            "findings": findings,
            "actions": actions,
            "events": events,
        }

    @staticmethod
    def _add_usage(usage: Dict[str, Any], result: ModelTurnResult) -> None:
        if result.usage is None:
            return
        for key in ("input_tokens", "output_tokens"):
            usage[key] += int(result.usage.get(key, 0))
        total = int(result.usage.get("total_tokens", 0))
        usage["total_tokens"] += total or (
            int(result.usage.get("input_tokens", 0))
            + int(result.usage.get("output_tokens", 0))
        )
        usage["cost_usd"] += float(result.usage.get("cost_usd", 0.0))

    @staticmethod
    def _required_string(arguments: Dict[str, Any], key: str) -> str:
        value = arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ArtifactWorkspaceError("Action 缺少非空字符串参数: %s" % key)
        return value.strip()
