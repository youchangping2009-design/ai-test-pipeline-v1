from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from harness.contracts import validate_named
from harness.model_gateway import ModelTurnResult
from harness.state_store import atomic_write_json, utc_now


@dataclass(frozen=True)
class BudgetConfig:
    max_model_calls: int = 8
    max_wall_seconds: int = 600
    max_total_tokens: int | None = None
    max_cost_usd: float | None = None
    require_usage: bool = False

    def __post_init__(self) -> None:
        if self.max_model_calls < 1:
            raise ValueError("max_model_calls 必须大于 0")
        if self.max_wall_seconds < 1:
            raise ValueError("max_wall_seconds 必须大于 0")
        if self.max_total_tokens is not None and self.max_total_tokens < 1:
            raise ValueError("max_total_tokens 必须大于 0")
        if self.max_cost_usd is not None and self.max_cost_usd <= 0:
            raise ValueError("max_cost_usd 必须大于 0")


class RunTelemetry:
    def __init__(
        self,
        *,
        run_id: str,
        run_dir: Path,
        budget: BudgetConfig,
    ) -> None:
        self.run_id = run_id
        self.run_dir = run_dir
        self.budget = budget
        self.started_at = utc_now()
        self.started_monotonic = time.monotonic()
        self.model_calls = 0
        self.model_duration_ms = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.cost_usd = 0.0
        self.usage_reports = 0
        self.usage_complete = True
        self.models: set[str] = set()
        self.providers: set[str] = set()
        self.action_counts: dict[str, int] = {}
        self.validation_attempts = 0
        self.validation_failures = 0
        self.diagnostic_count = 0
        self.status = "running"
        self.stop_reason: str | None = None
        self.parallel_reviewers: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def before_model_call(self) -> str | None:
        with self._lock:
            reason = self.budget_exhaustion_reason()
            if reason:
                return reason
            if self.model_calls >= self.budget.max_model_calls:
                return "model_call_budget_exhausted"
            return None

    def reserve_model_call(self, reviewer: str | None = None) -> str | None:
        with self._lock:
            reason = self.before_model_call()
            if reason:
                return reason
            self.model_calls += 1
            if reviewer:
                metrics = self._reviewer_metrics(reviewer)
                metrics["calls"] += 1
            return None

    def record_reserved_model_call(
        self,
        *,
        duration_ms: int,
        result: ModelTurnResult | None,
        reviewer: str | None = None,
    ) -> str | None:
        with self._lock:
            self._record_model_result(duration_ms, result)
            if reviewer:
                metrics = self._reviewer_metrics(reviewer)
                metrics["duration_ms"] += max(duration_ms, 0)
                self._record_reviewer_usage(metrics, result)
            return self.budget_exhaustion_reason()

    def record_model_call(
        self,
        *,
        duration_ms: int,
        result: ModelTurnResult | None,
    ) -> str | None:
        with self._lock:
            self.model_calls += 1
            self._record_model_result(duration_ms, result)
            return self.budget_exhaustion_reason()

    def _record_model_result(
        self,
        duration_ms: int,
        result: ModelTurnResult | None,
    ) -> None:
        self.model_duration_ms += max(duration_ms, 0)
        if result is None or result.usage is None:
            self.usage_complete = False
        else:
            usage = result.usage
            self.usage_reports += 1
            self.input_tokens += int(usage.get("input_tokens", 0))
            self.output_tokens += int(usage.get("output_tokens", 0))
            reported_total = int(usage.get("total_tokens", 0))
            self.total_tokens += reported_total or (
                int(usage.get("input_tokens", 0))
                + int(usage.get("output_tokens", 0))
            )
            self.cost_usd += float(usage.get("cost_usd", 0.0))
        if result and result.runtime:
            model = result.runtime.get("model")
            provider = result.runtime.get("provider")
            if model:
                self.models.add(model)
            if provider:
                self.providers.add(provider)

    def record_action(self, action_type: str) -> None:
        with self._lock:
            self.action_counts[action_type] = self.action_counts.get(action_type, 0) + 1

    def record_reviewer_action(self, reviewer: str, action_type: str) -> None:
        with self._lock:
            self.record_action("parallel_%s" % action_type)
            metrics = self._reviewer_metrics(reviewer)
            counts = metrics["action_counts"]
            counts[action_type] = counts.get(action_type, 0) + 1

    def set_reviewer_terminal(
        self,
        reviewer: str,
        *,
        status: str,
        finding_count: int,
    ) -> None:
        with self._lock:
            metrics = self._reviewer_metrics(reviewer)
            metrics["status"] = status
            metrics["finding_count"] = max(0, finding_count)

    def record_validation(
        self,
        *,
        passed: bool,
        diagnostic_count: int,
    ) -> None:
        with self._lock:
            self.validation_attempts += 1
            if not passed:
                self.validation_failures += 1
            self.diagnostic_count += max(diagnostic_count, 0)

    def budget_exhaustion_reason(self) -> str | None:
        if self.elapsed_ms() >= self.budget.max_wall_seconds * 1000:
            return "wall_time_exhausted"
        usage_required = (
            self.budget.require_usage
            or self.budget.max_total_tokens is not None
            or self.budget.max_cost_usd is not None
        )
        if usage_required and not self.usage_complete:
            return "usage_unavailable"
        if (
            self.budget.max_total_tokens is not None
            and self.total_tokens > self.budget.max_total_tokens
        ):
            return "token_budget_exhausted"
        if (
            self.budget.max_cost_usd is not None
            and self.cost_usd > self.budget.max_cost_usd
        ):
            return "cost_budget_exhausted"
        return None

    def elapsed_ms(self) -> int:
        return max(0, int((time.monotonic() - self.started_monotonic) * 1000))

    def write(self) -> dict[str, Any]:
        payload = self.snapshot()
        validate_named(payload, "harness_telemetry.schema.json")
        atomic_write_json(self.run_dir / "telemetry.json", payload)
        return payload

    def finalize(
        self,
        *,
        state: dict[str, Any],
        status: str,
        stop_reason: str | None,
    ) -> None:
        self.status = status
        self.stop_reason = stop_reason
        telemetry = self.write()
        write_run_summary(
            run_dir=self.run_dir,
            state=state,
            telemetry=telemetry,
            stop_reason=stop_reason,
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
            "schema_version": "1.0.0",
            "run_id": self.run_id,
            "started_at": self.started_at,
            "updated_at": utc_now(),
            "elapsed_ms": self.elapsed_ms(),
            "model_calls": self.model_calls,
            "model_duration_ms": self.model_duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 8),
            "usage_reports": self.usage_reports,
            "usage_complete": self.usage_complete,
            "models": sorted(self.models),
            "providers": sorted(self.providers),
            "action_counts": dict(sorted(self.action_counts.items())),
            "parallel_reviewers": {
                reviewer: {
                    **metrics,
                    "action_counts": dict(
                        sorted(metrics.get("action_counts", {}).items())
                    ),
                    "cost_usd": round(float(metrics.get("cost_usd", 0.0)), 8),
                }
                for reviewer, metrics in sorted(self.parallel_reviewers.items())
            },
            "validation_attempts": self.validation_attempts,
            "validation_failures": self.validation_failures,
            "diagnostic_count": self.diagnostic_count,
            "budget": {
                "max_model_calls": self.budget.max_model_calls,
                "max_wall_seconds": self.budget.max_wall_seconds,
                "max_total_tokens": self.budget.max_total_tokens,
                "max_cost_usd": self.budget.max_cost_usd,
                "require_usage": self.budget.require_usage,
                "remaining_model_calls": max(
                    0,
                    self.budget.max_model_calls - self.model_calls,
                ),
            },
            "status": self.status,
            "stop_reason": self.stop_reason,
            }

    def _reviewer_metrics(self, reviewer: str) -> dict[str, Any]:
        return self.parallel_reviewers.setdefault(
            reviewer,
            {
                "calls": 0,
                "duration_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "usage_reports": 0,
                "action_counts": {},
                "finding_count": 0,
                "status": "running",
            },
        )

    @staticmethod
    def _record_reviewer_usage(
        metrics: dict[str, Any],
        result: ModelTurnResult | None,
    ) -> None:
        if result is None or result.usage is None:
            return
        usage = result.usage
        metrics["usage_reports"] += 1
        metrics["input_tokens"] += int(usage.get("input_tokens", 0))
        metrics["output_tokens"] += int(usage.get("output_tokens", 0))
        reported_total = int(usage.get("total_tokens", 0))
        metrics["total_tokens"] += reported_total or (
            int(usage.get("input_tokens", 0))
            + int(usage.get("output_tokens", 0))
        )
        metrics["cost_usd"] += float(usage.get("cost_usd", 0.0))


def write_run_summary(
    *,
    run_dir: Path,
    state: dict[str, Any],
    telemetry: dict[str, Any],
    stop_reason: str | None,
) -> dict[str, Any]:
    summary = {
        "schema_version": "1.0.0",
        "run_id": state["run_id"],
        "mode": state["mode"],
        "status": state["status"],
        "stage_id": state["stages"][0]["stage_id"] if state["stages"] else None,
        "created_at": state["created_at"],
        "completed_at": utc_now(),
        "stop_reason": stop_reason,
        "model_calls": telemetry.get("model_calls", 0),
        "total_tokens": telemetry.get("total_tokens", 0),
        "cost_usd": telemetry.get("cost_usd", 0.0),
        "usage_complete": telemetry.get("usage_complete", False),
        "action_counts": telemetry.get("action_counts", {}),
        "validation_attempts": telemetry.get("validation_attempts", 0),
        "validation_failures": telemetry.get("validation_failures", 0),
        "diagnostic_count": telemetry.get("diagnostic_count", 0),
        "artifacts": {
            "run_state": "run_state.json",
            "events": "events.jsonl",
            "telemetry": "telemetry.json",
            "agent_state": "agent_state.json",
        },
    }
    atomic_write_json(run_dir / "run_summary.json", summary)
    return summary


def finalize_persisted_telemetry(
    *,
    run_dir: Path,
    state: dict[str, Any],
    status: str,
    stop_reason: str | None,
) -> None:
    path = run_dir / "telemetry.json"
    if not path.exists():
        return
    telemetry = json.loads(path.read_text(encoding="utf-8"))
    telemetry["status"] = status
    telemetry["stop_reason"] = stop_reason
    telemetry["updated_at"] = utc_now()
    try:
        created = datetime.fromisoformat(str(state["created_at"]))
        now = datetime.fromisoformat(utc_now())
        telemetry["elapsed_ms"] = max(
            int((now - created).total_seconds() * 1000),
            int(telemetry.get("elapsed_ms", 0)),
        )
    except (TypeError, ValueError):
        pass
    validate_named(telemetry, "harness_telemetry.schema.json")
    atomic_write_json(path, telemetry)
    write_run_summary(
        run_dir=run_dir,
        state=state,
        telemetry=telemetry,
        stop_reason=stop_reason,
    )

