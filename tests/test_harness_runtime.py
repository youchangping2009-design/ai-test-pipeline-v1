from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.contracts import ContractError, load_schema, validate_named  # noqa: E402
from harness.diagnostics import normalize_validator_failure  # noqa: E402
from harness.audit import HarnessRunAuditor  # noqa: E402
from harness.hook_dispatcher import (  # noqa: E402
    HookConfigurationError,
    HookDispatcher,
)
from harness.orchestrator import DeterministicOrchestrator  # noqa: E402
from harness.stage_registry import StageSpec, resolve_stage_plan  # noqa: E402
from harness.state_store import HarnessStateError, StateStore  # noqa: E402


ALL_LEVELS = frozenset({"S", "M", "L"})


def no_commands(
    _item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return []


def marker_command(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    marker = item_root / "allow-stage-two"
    code = (
        "from pathlib import Path; import sys; "
        f"sys.exit(0 if Path({str(marker)!r}).exists() else 7)"
    )
    return [[sys.executable, "-c", code]]


class HarnessContractTests(unittest.TestCase):
    def test_all_harness_contract_schemas_are_loadable(self) -> None:
        for schema_name in [
            "harness_run.schema.json",
            "harness_stage.schema.json",
            "harness_event.schema.json",
            "harness_diagnostic.schema.json",
            "harness_model_action.schema.json",
            "harness_approval.schema.json",
            "requirement_approval.schema.json",
            "work_item_manifest.schema.json",
            "harness_telemetry.schema.json",
            "harness_audit_report.schema.json",
            "harness_hook_config.schema.json",
            "harness_hook_execution.schema.json",
            "harness_generation_candidate.schema.json",
            "harness_publish_transaction.schema.json",
            "harness_case_plan_commit_transaction.schema.json",
            "harness_multi_role_recovery.schema.json",
            "harness_role_runtime.schema.json",
            "harness_subagent_action.schema.json",
            "harness_review_finding.schema.json",
            "harness_parallel_review_runtime.schema.json",
            "harness_review_bundle.schema.json",
            "harness_closeout_report.schema.json",
            "eval_suite_report.schema.json",
        ]:
            schema = load_schema(schema_name)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_model_action_contract_accepts_allowed_action(self) -> None:
        validate_named(
            {
                "action_id": "ACT-001",
                "action_type": "read_artifact",
                "stage_id": "case_plan",
                "arguments": {"path": "testcases/case_plan.json"},
                "expected_outcome": "读取当前计划",
            },
            "harness_model_action.schema.json",
        )

    def test_model_action_contract_rejects_arbitrary_shell(self) -> None:
        with self.assertRaises(ContractError):
            validate_named(
                {
                    "action_id": "ACT-002",
                    "action_type": "arbitrary_shell",
                    "stage_id": "case_plan",
                    "arguments": {"command": "rm -rf ."},
                    "expected_outcome": "不应执行",
                },
                "harness_model_action.schema.json",
            )

    def test_strict_gate_diagnostic_routes_to_case_plan(self) -> None:
        diagnostics = normalize_validator_failure(
            observed_stage_id="strict_gate",
            command=[
                sys.executable,
                str(ROOT / "scripts" / "validate_work_item.py"),
            ],
            command_index=1,
            exit_code=1,
            output="❌ case_plan 缺少必填字段 source_example_ids",
            attempt=1,
        )
        self.assertEqual(len(diagnostics), 1)
        diagnostic = diagnostics[0]
        self.assertEqual(diagnostic["stage_id"], "case_plan")
        self.assertEqual(diagnostic["observed_stage_id"], "strict_gate")
        self.assertEqual(diagnostic["code"], "HARNESS_SCHEMA_REQUIRED_FIELD")
        self.assertEqual(
            diagnostic["artifact_path"],
            "testcases/case_plan.json",
        )
        self.assertTrue(diagnostic["repair_hint"])

    def test_unknown_validator_output_uses_stable_fallback(self) -> None:
        diagnostics = normalize_validator_failure(
            observed_stage_id="testcases",
            command=[sys.executable, "-c", "raise SystemExit(9)"],
            command_index=2,
            exit_code=9,
            output="opaque validator payload",
            attempt=3,
        )
        diagnostic = diagnostics[0]
        self.assertEqual(diagnostic["stage_id"], "testcases")
        self.assertEqual(diagnostic["code"], "HARNESS_VALIDATOR_FAILED")
        self.assertEqual(diagnostic["command_index"], 2)
        self.assertEqual(diagnostic["exit_code"], 9)

    def test_strict_traceability_failure_routes_to_primary_traceability(self) -> None:
        diagnostic = normalize_validator_failure(
            observed_stage_id="strict_gate",
            command=[sys.executable, "validate_work_item.py"],
            command_index=1,
            exit_code=1,
            output="❌ Traceability 主链不一致",
            attempt=1,
        )[0]
        self.assertEqual(diagnostic["stage_id"], "traceability")
        self.assertEqual(diagnostic["code"], "HARNESS_TRACEABILITY_FAILED")
        self.assertEqual(
            diagnostic["artifact_path"],
            "traceability/coverage_first_traceability.json",
        )

    def test_diagnostic_excerpt_redacts_api_key(self) -> None:
        diagnostic = normalize_validator_failure(
            observed_stage_id="strict_gate",
            command=[sys.executable, "validate_work_item.py"],
            command_index=1,
            exit_code=1,
            output="错误 ATP_API_KEY=top-secret-value",
            attempt=1,
        )[0]
        self.assertNotIn("top-secret-value", diagnostic["message"])
        self.assertIn("[REDACTED]", diagnostic["message"])


class HarnessStageBoundaryTests(unittest.TestCase):
    def test_valid_case_plan_checkpoint_succeeds_before_testcases_exist(self) -> None:
        source = (
            ROOT
            / "assets"
            / "projects"
            / "WX-YGJ"
            / "work_items"
            / "PT083"
        )
        with tempfile.TemporaryDirectory() as temporary:
            item_root = Path(temporary) / "work_item"
            for relative_path in [
                "acceptance/testability_gate.json",
                "acceptance/acceptance_examples.json",
                "testcases/case_plan.json",
            ]:
                target = item_root / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative_path, target)
            testcase_template = item_root / "testcases" / "testcases_main.md"
            testcase_template.write_text(
                "# 页面：待补充\n"
                "## 板块：待补充\n"
                "| 用例编号 | 所属模块 | 所属功能点 | 用例标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 标签 | 测试类型 | 备注 |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|\n",
                encoding="utf-8",
            )

            case_plan_stage = next(
                stage
                for stage in resolve_stage_plan("M")
                if stage.stage_id == "case_plan"
            )
            command = case_plan_stage.commands(
                item_root,
                "WX-YGJ",
                "PT083",
                "M",
                True,
            )[0]
            result = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=result.stdout + result.stderr,
            )
            testcase_stage = next(
                stage
                for stage in resolve_stage_plan("M")
                if stage.stage_id == "testcases"
            )
            reverse_mapping_command = next(
                command
                for command in testcase_stage.commands(
                    item_root,
                    "WX-YGJ",
                    "PT083",
                    "M",
                    True,
                )
                if command[1].endswith("validate_case_plan.py")
            )
            downstream_result = subprocess.run(
                reverse_mapping_command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(downstream_result.returncode, 0)
            self.assertIn(
                "testcases_main.md 必须包含真实用例",
                downstream_result.stdout + downstream_result.stderr,
            )

    def test_testcases_checkpoint_succeeds_before_bundle_is_refreshed(self) -> None:
        source = (
            ROOT
            / "assets"
            / "projects"
            / "WX-YGJ"
            / "work_items"
            / "PT083"
        )
        with tempfile.TemporaryDirectory() as temporary:
            item_root = Path(temporary) / "work_item"
            for relative_path in [
                "acceptance/testability_gate.json",
                "acceptance/acceptance_examples.json",
                "testcases/case_plan.json",
                "testcases/testcases_main.md",
                "testcases/testpoints.json",
                "testcases/testcase_bundle.json",
            ]:
                target = item_root / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative_path, target)

            bundle_path = item_root / "testcases" / "testcase_bundle.json"
            stale_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            stale_bundle["cases"] = []
            bundle_path.write_text(
                json.dumps(stale_bundle, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            testcase_stage = next(
                stage
                for stage in resolve_stage_plan("M")
                if stage.stage_id == "testcases"
            )
            failures = []
            for command in testcase_stage.commands(
                item_root,
                "WX-YGJ",
                "PT083",
                "M",
                True,
            ):
                result = subprocess.run(
                    command,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode != 0:
                    failures.append(result.stdout + result.stderr)

            self.assertEqual(failures, [])
            traceability_stage = next(
                stage
                for stage in resolve_stage_plan("M")
                if stage.stage_id == "traceability"
            )
            bundle_command = next(
                command
                for command in traceability_stage.commands(
                    item_root,
                    "WX-YGJ",
                    "PT083",
                    "M",
                    True,
                )
                if command[1].endswith("validate_testcase_bundle.py")
            )
            downstream_result = subprocess.run(
                bundle_command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(downstream_result.returncode, 0)
            self.assertIn(
                "0 != 75",
                downstream_result.stdout + downstream_result.stderr,
            )


class HarnessOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.item_root = Path(self.temporary.name) / "work_item"
        self.item_root.mkdir(parents=True)
        (self.item_root / "manifest.json").write_text(
            json.dumps(
                {
                    "project_code": "DEMO",
                    "work_item_id": "WI-001",
                    "work_item_level": "S",
                }
            ),
            encoding="utf-8",
        )
        (self.item_root / "first.txt").write_text("first\n", encoding="utf-8")
        (self.item_root / "second.txt").write_text("second\n", encoding="utf-8")
        self.plan = [
            StageSpec(
                "stage_one",
                "validation",
                ALL_LEVELS,
                ("first.txt",),
                no_commands,
            ),
            StageSpec(
                "stage_two",
                "validation",
                ALL_LEVELS,
                ("second.txt",),
                no_commands,
            ),
        ]
        self.orchestrator = DeterministicOrchestrator(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_lock_rejects_concurrent_and_active_force_unlock(self) -> None:
        store = StateStore(self.item_root)
        with store.lock("RUN-OWNER"):
            with self.assertRaisesRegex(HarnessStateError, "已有 Harness 进程锁"):
                with store.lock("RUN-CONTENDER"):
                    self.fail("并发锁不应获取成功")
            with self.assertRaisesRegex(HarnessStateError, "活跃进程持有"):
                with store.lock("RUN-FORCED", force=True):
                    self.fail("不能强制删除活跃进程锁")

    def test_force_unlock_only_removes_stale_owner(self) -> None:
        store = StateStore(self.item_root)
        store.runs_root.mkdir(parents=True)
        store.lock_path.write_text(
            json.dumps(
                {
                    "run_id": "RUN-STALE",
                    "pid": 99999999,
                    "token": "stale-token",
                    "created_at": "2026-08-05T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )
        with store.lock("RUN-RECOVERED", force=True):
            owner = json.loads(store.lock_path.read_text(encoding="utf-8"))
            self.assertEqual(owner["run_id"], "RUN-RECOVERED")
            self.assertEqual(owner["pid"], os.getpid())
        self.assertFalse(store.lock_path.exists())

    def test_previous_owner_does_not_delete_replacement_lock(self) -> None:
        store = StateStore(self.item_root)
        with store.lock("RUN-OLD"):
            store.lock_path.unlink()
            replacement = {
                "run_id": "RUN-NEW",
                "pid": os.getpid(),
                "token": "replacement-token",
                "created_at": "2026-08-05T00:00:00+00:00",
            }
            store.lock_path.write_text(
                json.dumps(replacement),
                encoding="utf-8",
            )
        self.assertTrue(store.lock_path.exists())
        self.assertEqual(
            json.loads(store.lock_path.read_text(encoding="utf-8"))["token"],
            "replacement-token",
        )

    def test_start_pause_resume_is_idempotent(self) -> None:
        with (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["stage_one", "stage_two"],
            ),
        ):
            code, paused = self.orchestrator.start(
                run_id="RUN-PAUSE",
                work_item_level="S",
                strict=False,
                stop_at="stage_one",
            )
            self.assertEqual(code, 0)
            self.assertEqual(paused["status"], "paused")
            self.assertEqual(paused["stages"][0]["attempts"], 1)
            self.assertEqual(paused["stages"][1]["attempts"], 0)

            code, completed = self.orchestrator.resume(run_id="RUN-PAUSE")
            self.assertEqual(code, 0)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["stop_at"], "stage_two")
            self.assertEqual(completed["stages"][0]["attempts"], 1)
            self.assertEqual(completed["stages"][1]["attempts"], 1)

    def test_failed_stage_resumes_without_repeating_valid_checkpoint(self) -> None:
        failing_plan = [
            self.plan[0],
            StageSpec(
                "stage_two",
                "validation",
                ALL_LEVELS,
                ("second.txt",),
                marker_command,
            ),
        ]
        with (
            patch(
                "harness.orchestrator.resolve_stage_plan",
                return_value=failing_plan,
            ),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["stage_one", "stage_two"],
            ),
        ):
            code, failed = self.orchestrator.start(
                run_id="RUN-REPAIR",
                work_item_level="S",
                strict=False,
                stop_at="stage_two",
            )
            self.assertEqual(code, 7)
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["stages"][0]["attempts"], 1)
            self.assertEqual(failed["stages"][1]["attempts"], 1)
            self.assertTrue(
                (
                    self.item_root
                    / ".generation"
                    / "runs"
                    / "RUN-REPAIR"
                    / "diagnostics"
                    / "stage_two"
                    / "attempt-1.json"
                ).exists()
            )
            diagnostic_payload = json.loads(
                (
                    self.item_root
                    / ".generation"
                    / "runs"
                    / "RUN-REPAIR"
                    / "diagnostics"
                    / "stage_two"
                    / "attempt-1.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                diagnostic_payload[0]["code"],
                "HARNESS_VALIDATOR_FAILED",
            )

            (self.item_root / "allow-stage-two").write_text("ok\n", encoding="utf-8")
            code, completed = self.orchestrator.resume(run_id="RUN-REPAIR")
            self.assertEqual(code, 0)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["stages"][0]["attempts"], 1)
            self.assertEqual(completed["stages"][1]["attempts"], 2)

    def test_changed_input_invalidates_stage_and_downstream(self) -> None:
        with (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["stage_one", "stage_two"],
            ),
        ):
            _, paused = self.orchestrator.start(
                run_id="RUN-INVALIDATE",
                work_item_level="S",
                strict=False,
                stop_at="stage_one",
            )
            self.assertEqual(paused["status"], "paused")
            (self.item_root / "first.txt").write_text("changed\n", encoding="utf-8")

            code, completed = self.orchestrator.resume(run_id="RUN-INVALIDATE")
            self.assertEqual(code, 0)
            self.assertEqual(completed["stages"][0]["attempts"], 2)
            self.assertEqual(completed["stages"][1]["attempts"], 1)

    def test_failed_attempt_diagnostics_are_not_overwritten(self) -> None:
        failing_plan = [
            StageSpec(
                "stage_two",
                "validation",
                ALL_LEVELS,
                ("second.txt",),
                marker_command,
            )
        ]
        with (
            patch(
                "harness.orchestrator.resolve_stage_plan",
                return_value=failing_plan,
            ),
            patch("harness.orchestrator.stage_ids", return_value=["stage_two"]),
        ):
            first_code, _ = self.orchestrator.start(
                run_id="RUN-HISTORY",
                work_item_level="S",
                strict=False,
                stop_at="stage_two",
            )
            second_code, state = self.orchestrator.resume(run_id="RUN-HISTORY")
            self.assertEqual(first_code, 7)
            self.assertEqual(second_code, 7)
            self.assertEqual(state["stages"][0]["attempts"], 2)
            diagnostic_dir = (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-HISTORY"
                / "diagnostics"
                / "stage_two"
            )
            self.assertTrue((diagnostic_dir / "attempt-1.json").exists())
            self.assertTrue((diagnostic_dir / "attempt-2.json").exists())

    def test_cancelled_run_cannot_resume(self) -> None:
        with (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["stage_one", "stage_two"],
            ),
        ):
            self.orchestrator.start(
                run_id="RUN-CANCEL",
                work_item_level="S",
                strict=False,
                stop_at="stage_one",
            )
            cancelled = self.orchestrator.cancel(run_id="RUN-CANCEL")
            self.assertEqual(cancelled["status"], "cancelled")
            with self.assertRaises(HarnessStateError):
                self.orchestrator.resume(run_id="RUN-CANCEL")

    def test_state_store_writes_valid_event_stream(self) -> None:
        store = StateStore(self.item_root)
        state = store.create(
            run_id="RUN-EVENTS",
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="S",
            strict=False,
            stop_at="stage_two",
            stages=self.plan,
        )
        store.append_event(state, "run_started", None, {})
        events_path = (
            self.item_root
            / ".generation"
            / "runs"
            / "RUN-EVENTS"
            / "events.jsonl"
        )
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual([event["sequence"] for event in events], [1, 2])
        self.assertEqual(events[-1]["event_type"], "run_started")


class HarnessHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repository_root = Path(self.temporary.name) / "repo"
        self.handlers = self.repository_root / "scripts" / "hooks"
        self.handlers.mkdir(parents=True)
        self.config_path = (
            self.repository_root / "config" / "harness_hooks.json"
        )
        self.config_path.parent.mkdir(parents=True)
        self.item_root = self.repository_root / "work_item"
        self.item_root.mkdir()
        (self.item_root / "manifest.json").write_text(
            json.dumps(
                {
                    "project_code": "DEMO",
                    "work_item_id": "WI-001",
                    "work_item_level": "S",
                }
            ),
            encoding="utf-8",
        )
        (self.item_root / "first.txt").write_text("first\n", encoding="utf-8")
        self.plan = [
            StageSpec(
                "stage_one",
                "validation",
                ALL_LEVELS,
                ("first.txt",),
                no_commands,
            )
        ]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_handler(self, name: str, body: str) -> None:
        (self.handlers / name).write_text(body, encoding="utf-8")

    def _write_config(self, hooks: list[dict[str, object]]) -> None:
        self.config_path.write_text(
            json.dumps({"schema_version": "1.0.0", "hooks": hooks}),
            encoding="utf-8",
        )

    @staticmethod
    def _hook(
        *,
        hook_id: str,
        event: str,
        handler: str,
        failure_policy: str = "warn",
        timeout_seconds: int = 5,
    ) -> dict[str, object]:
        return {
            "hook_id": hook_id,
            "enabled": True,
            "event": event,
            "stages": ["*"],
            "handler": f"scripts/hooks/{handler}",
            "failure_policy": failure_policy,
            "timeout_seconds": timeout_seconds,
            "max_output_chars": 4096,
        }

    def test_hook_dispatch_is_persisted_redacted_and_auditable(self) -> None:
        self._write_handler(
            "echo.py",
            "import json, sys\n"
            "request = json.load(sys.stdin)\n"
            "print(json.dumps({'event': request['event'], "
            "'secret': 'sk-1234567890abcdef'}))\n",
        )
        self._write_config(
            [
                self._hook(
                    hook_id="echo",
                    event="pre_stage",
                    handler="echo.py",
                )
            ]
        )
        store = StateStore(self.item_root)
        state = store.create(
            run_id="RUN-HOOK",
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="S",
            strict=False,
            stop_at="stage_one",
            stages=self.plan,
        )
        dispatcher = HookDispatcher(
            repository_root=self.repository_root,
            config_path=self.config_path,
        )
        result = dispatcher.dispatch(
            event="pre_stage",
            state=state,
            run_dir=store.run_dir("RUN-HOOK"),
            stage_id="stage_one",
            payload={"attempt": 1},
            event_callback=lambda event_type, payload: store.append_event(
                state,
                event_type,
                "stage_one",
                payload,
            ),
        )
        self.assertIsNone(result.blocking_failure)
        execution = result.executions[0]
        self.assertEqual(execution["status"], "succeeded")
        self.assertEqual(
            execution["output"]["secret"],
            "[REDACTED_API_KEY]",
        )
        audit_code, report = HarnessRunAuditor(self.item_root).audit("RUN-HOOK")
        self.assertEqual(audit_code, 0)
        self.assertEqual(report["counts"]["hooks"], 1)
        hook_path = next(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-HOOK"
                / "hooks"
            ).glob("*.json")
        )
        hook_path.unlink()
        audit_code, report = HarnessRunAuditor(self.item_root).audit("RUN-HOOK")
        self.assertEqual(audit_code, 1)
        self.assertTrue(
            any("缺少 execution 文件" in error for error in report["errors"])
        )

    def test_hook_rejects_path_traversal(self) -> None:
        self._write_config(
            [
                self._hook(
                    hook_id="escape",
                    event="pre_stage",
                    handler="../escape.py",
                )
            ]
        )
        with self.assertRaises(HookConfigurationError):
            HookDispatcher(
                repository_root=self.repository_root,
                config_path=self.config_path,
            )

    def test_timeout_can_block_orchestrator_before_stage(self) -> None:
        self._write_handler(
            "slow.py",
            "import time\ntime.sleep(2)\n",
        )
        self._write_config(
            [
                self._hook(
                    hook_id="slow",
                    event="pre_stage",
                    handler="slow.py",
                    failure_policy="fail_run",
                    timeout_seconds=1,
                )
            ]
        )
        dispatcher = HookDispatcher(
            repository_root=self.repository_root,
            config_path=self.config_path,
        )
        orchestrator = DeterministicOrchestrator(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            hooks=dispatcher,
        )
        with (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch("harness.orchestrator.stage_ids", return_value=["stage_one"]),
        ):
            code, state = orchestrator.start(
                run_id="RUN-HOOK-BLOCK",
                work_item_level="S",
                strict=False,
                stop_at="stage_one",
            )
        self.assertEqual(code, 1)
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["last_error"]["error_type"], "hook_failure")
        self.assertEqual(state["stages"][0]["last_exit_code"], None)

    def test_approval_hooks_cannot_use_fail_run(self) -> None:
        self._write_handler("noop.py", "print('{}')\n")
        self._write_config(
            [
                self._hook(
                    hook_id="approval-block",
                    event="approval_requested",
                    handler="noop.py",
                    failure_policy="fail_run",
                )
            ]
        )
        with self.assertRaises(HookConfigurationError):
            HookDispatcher(
                repository_root=self.repository_root,
                config_path=self.config_path,
            )


if __name__ == "__main__":
    unittest.main()

