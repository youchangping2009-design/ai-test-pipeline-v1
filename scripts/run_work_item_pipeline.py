#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.agent_loop import (
    MAX_AGENT_TURNS,
    MAX_REPAIR_ROUNDS,
    CasePlanAgentLoop,
)
from harness.approval_service import (
    CasePlanApprovalService,
    RequirementApprovalService,
)
from harness.artifact_workspace import ArtifactWorkspaceError
from harness.audit import HarnessRunAuditor
from harness.controlled_generation import ControlledGenerationService
from harness.generation_workspace import ControlledGenerationError
from harness.hook_dispatcher import HookConfigurationError
from harness.feedback_action_runtime import (
    FeedbackActionDispatchError,
    FeedbackApplicationActionRuntime,
)
from harness.model_gateway import (
    CommandModelGateway,
    ModelGatewayError,
    ScriptedModelGateway,
    parse_provider_command,
)
from harness.multi_role_runtime import (
    MAX_ROLE_REPAIRS,
    MAX_ROLE_TURNS,
    MultiRoleAgentRuntime,
)
from harness.orchestrator import DeterministicOrchestrator
from harness.review_disposition import ReviewDispositionService
from harness.state_store import HarnessStateError, StateStore
from harness.stage_registry import stage_ids
from harness.telemetry import BudgetConfig
from validate_feedback_action_journal import validate_feedback_action_journal
from work_item_policy import VALID_WORK_ITEM_LEVELS, resolve_work_item_level


ROOT = Path(__file__).resolve().parents[1]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_item_root(project_code: str, work_item_id: str) -> Path:
    return (
        ROOT
        / "assets"
        / "projects"
        / project_code
        / "work_items"
        / work_item_id
    )


def load_manifest(item_root: Path) -> dict[str, Any]:
    manifest_path = item_root / "manifest.json"
    if not manifest_path.exists():
        raise HarnessStateError(f"工作项 manifest 不存在: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HarnessStateError("manifest.json 必须是 JSON object")
    return payload


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("RUN-%Y%m%dT%H%M%SZ")


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--run-id", required=False)
    parser.add_argument(
        "--force-unlock",
        action="store_true",
        help="仅在确认没有其他运行进程时清理遗留锁",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Test Pipeline Harness Orchestrator"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    start = subparsers.add_parser("start", help="创建并执行新的只读 Harness run")
    add_common_arguments(start)
    start.add_argument(
        "--work-item-level",
        choices=sorted(VALID_WORK_ITEM_LEVELS),
        default=None,
        help="显式覆盖 manifest 档位，仅影响本次 run",
    )
    start.add_argument("--strict", action="store_true", help="末段执行 strict 工作项门禁")
    start.add_argument(
        "--stop-at",
        default="strict_gate",
        help="完成指定阶段后暂停；默认运行到 strict_gate",
    )

    resume = subparsers.add_parser("resume", help="从 checkpoint 恢复 run")
    add_common_arguments(resume)
    resume.add_argument(
        "--stop-at",
        required=False,
        help="可选覆盖新的停止阶段",
    )

    status = subparsers.add_parser("status", help="查看当前或指定 run 状态")
    add_common_arguments(status)

    cancel = subparsers.add_parser("cancel", help="取消当前或指定 run")
    add_common_arguments(cancel)

    approve_requirement = subparsers.add_parser(
        "approve-requirement",
        help="人工批准当前内容绑定的 requirement summary",
    )
    add_common_arguments(approve_requirement)
    approve_requirement.add_argument("--reviewed-by", required=True)
    approve_requirement.add_argument("--note", required=True)

    reject_requirement = subparsers.add_parser(
        "reject-requirement",
        help="人工拒绝当前内容绑定的 requirement summary",
    )
    add_common_arguments(reject_requirement)
    reject_requirement.add_argument("--reviewed-by", required=True)
    reject_requirement.add_argument("--note", required=True)

    recover_requirement = subparsers.add_parser(
        "recover-requirement-approval",
        help="幂等补全 requirement approval receipt/event/run state",
    )
    add_common_arguments(recover_requirement)

    review_not_applicable = subparsers.add_parser(
        "mark-review-not-applicable",
        help="人工声明 validate run 无代码映证，仍执行 Review 确定性校验",
    )
    add_common_arguments(review_not_applicable)
    review_not_applicable.add_argument("--declared-by", required=True)
    review_not_applicable.add_argument("--reason", required=True)

    agent_case_plan = subparsers.add_parser(
        "agent-case-plan",
        help="运行受限 Case Plan Agent Loop；默认只到 staging/approval",
    )
    add_common_arguments(agent_case_plan)
    agent_case_plan.add_argument(
        "--work-item-level",
        choices=sorted(VALID_WORK_ITEM_LEVELS),
        default=None,
    )
    agent_case_plan.add_argument(
        "--provider-command-json",
        required=True,
        help="模型适配器 argv JSON；通过 stdin 接收 turn request，stdout 返回 Action JSON",
    )
    agent_case_plan.add_argument(
        "--max-turns",
        type=int,
        default=MAX_AGENT_TURNS,
    )
    agent_case_plan.add_argument(
        "--max-repairs",
        type=int,
        default=MAX_REPAIR_ROUNDS,
    )
    agent_case_plan.add_argument(
        "--max-wall-seconds",
        type=int,
        default=600,
    )
    agent_case_plan.add_argument("--max-total-tokens", type=int)
    agent_case_plan.add_argument("--max-cost-usd", type=float)
    agent_case_plan.add_argument(
        "--require-usage",
        action="store_true",
        help="适配器未报告 token/cost 时立即停止并请求审批",
    )

    approve_case_plan = subparsers.add_parser(
        "approve-case-plan",
        help="审批并提交已校验且 hash 未漂移的 Case Plan 候选",
    )
    add_common_arguments(approve_case_plan)
    approve_case_plan.add_argument("--approval-id", required=True)
    approve_case_plan.add_argument("--candidate-hash", required=True)
    approve_case_plan.add_argument("--approved-by", required=True)

    reject_case_plan = subparsers.add_parser(
        "reject-case-plan",
        help="拒绝 pending Case Plan approval 并取消 run",
    )
    add_common_arguments(reject_case_plan)
    reject_case_plan.add_argument("--approval-id", required=True)
    reject_case_plan.add_argument("--rejected-by", required=True)
    reject_case_plan.add_argument("--reason", required=True)

    recover_case_plan = subparsers.add_parser(
        "recover-case-plan",
        help="恢复未完成的 Case Plan commit transaction",
    )
    add_common_arguments(recover_case_plan)

    agent_roles = subparsers.add_parser(
        "agent-roles",
        help="按固定顺序运行四角色受限 Action Runtime；默认停在发布审批",
    )
    add_common_arguments(agent_roles)
    agent_roles.add_argument(
        "--work-item-level",
        choices=sorted(VALID_WORK_ITEM_LEVELS),
        default=None,
    )
    agent_roles.add_argument(
        "--provider-command-json",
        required=True,
        help="可信模型适配器 argv JSON；每次只返回一个角色 Action",
    )
    agent_roles.add_argument(
        "--max-turns-per-role",
        type=int,
        default=MAX_ROLE_TURNS,
    )
    agent_roles.add_argument(
        "--max-repairs-per-role",
        type=int,
        default=MAX_ROLE_REPAIRS,
    )
    agent_roles.add_argument("--max-wall-seconds", type=int, default=1800)
    agent_roles.add_argument(
        "--parallel-reviewers",
        action="store_true",
        help="在 Case Reviewer 阶段并行运行 evidence/flow/testcase 三路 Reviewer",
    )
    agent_roles.add_argument(
        "--max-turns-per-reviewer",
        type=int,
        default=4,
    )
    agent_roles.add_argument(
        "--max-repairs-per-reviewer",
        type=int,
        default=MAX_ROLE_REPAIRS,
    )
    agent_roles.add_argument(
        "--reviewer-timeout-seconds",
        type=int,
        default=120,
    )
    agent_roles.add_argument(
        "--max-model-calls",
        type=int,
        help="共享模型调用预算；并行 Reviewer 默认 48，兼容路径默认每角色 turn 之和",
    )
    agent_roles.add_argument("--max-total-tokens", type=int)
    agent_roles.add_argument("--max-cost-usd", type=float)
    agent_roles.add_argument("--require-usage", action="store_true")

    approve_roles = subparsers.add_parser(
        "approve-roles",
        help="审批并事务发布四角色最终候选",
    )
    add_common_arguments(approve_roles)
    approve_roles.add_argument("--approval-id", required=True)
    approve_roles.add_argument("--candidate-hash", required=True)
    approve_roles.add_argument("--approved-by", required=True)

    reject_roles = subparsers.add_parser(
        "reject-roles",
        help="拒绝四角色 pending approval 且不修改正式资产",
    )
    add_common_arguments(reject_roles)
    reject_roles.add_argument("--approval-id", required=True)
    reject_roles.add_argument("--rejected-by", required=True)
    reject_roles.add_argument("--reason", required=True)

    recover_roles = subparsers.add_parser(
        "recover-roles",
        help="安全终态化进程崩溃遗留的 running multi-role run",
    )
    add_common_arguments(recover_roles)
    recover_roles.add_argument("--recovered-by", required=True)
    recover_roles.add_argument("--reason", required=True)

    feedback_action = subparsers.add_parser(
        "feedback-action",
        help="通过白名单 Action Runtime 执行 design feedback 回灌动作",
    )
    feedback_action.add_argument("--project-code", required=True)
    feedback_action.add_argument("--work-item-id", required=True)
    feedback_action.add_argument("--run-id", required=True)
    feedback_action.add_argument("--actor", required=True)
    feedback_action.add_argument("--provider", required=True)
    feedback_action.add_argument(
        "--action-file",
        required=True,
        help="符合 harness_feedback_action schema 的本地 JSON 文件",
    )

    audit_feedback_actions = subparsers.add_parser(
        "audit-feedback-actions",
        help="重放校验当前工作项的 feedback Action journal",
    )
    audit_feedback_actions.add_argument("--project-code", required=True)
    audit_feedback_actions.add_argument("--work-item-id", required=True)

    audit_run = subparsers.add_parser(
        "audit-run",
        help="重放校验 run state、events、actions、approvals 与 diagnostics",
    )
    add_common_arguments(audit_run)

    generate = subparsers.add_parser(
        "generate",
        help="在隔离副本中执行 bundle normalizer/strict 并请求发布审批",
    )
    add_common_arguments(generate)
    generate.add_argument(
        "--work-item-level",
        choices=sorted(VALID_WORK_ITEM_LEVELS),
        default=None,
    )
    generate.add_argument(
        "--provider",
        choices=["existing", "command"],
        default="existing",
    )
    generate.add_argument("--provider-command-json")
    generate.add_argument("--provider-timeout-seconds", type=int, default=300)

    approve_generation = subparsers.add_parser(
        "approve-generation",
        help="审批并事务发布已通过 strict 的全链路候选",
    )
    add_common_arguments(approve_generation)
    approve_generation.add_argument("--approval-id", required=True)
    approve_generation.add_argument("--candidate-hash", required=True)
    approve_generation.add_argument("--approved-by", required=True)

    reject_generation = subparsers.add_parser(
        "reject-generation",
        help="拒绝全链路候选且不修改正式资产",
    )
    add_common_arguments(reject_generation)
    reject_generation.add_argument("--approval-id", required=True)
    reject_generation.add_argument("--rejected-by", required=True)
    reject_generation.add_argument("--reason", required=True)

    recover_generation = subparsers.add_parser(
        "recover-generation",
        help="恢复未完成的 generation publish transaction",
    )
    add_common_arguments(recover_generation)

    stages = subparsers.add_parser("stages", help="查看指定档位的阶段计划")
    stages.add_argument(
        "--work-item-level",
        choices=sorted(VALID_WORK_ITEM_LEVELS),
        required=True,
    )
    return parser.parse_args()


def print_state(state: dict[str, Any]) -> None:
    print(f"run_id: {state['run_id']}")
    print(f"status: {state['status']}")
    print(f"work_item: {state['project_code']}/{state['work_item_id']}")
    print(f"work_item_level: {state['work_item_level']}")
    print(f"strict: {str(state['strict']).lower()}")
    print(f"stop_at: {state['stop_at']}")
    print(f"current_stage: {state['current_stage'] or '-'}")
    print(f"run_dir: {state['run_dir']}")
    print("stages:")
    for record in state["stages"]:
        print(
            f"- {record['stage_id']}: {record['status']} "
            f"(attempts={record['attempts']}, exit={record['last_exit_code']})"
        )
    if state.get("last_error"):
        print("last_error:")
        print(json.dumps(state["last_error"], ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()
    if args.action == "stages":
        for stage_id in stage_ids(args.work_item_level):
            print(stage_id)
        return 0

    project_code = normalize_code(args.project_code)
    work_item_id = normalize_code(args.work_item_id)
    item_root = resolve_item_root(project_code, work_item_id)
    manifest = load_manifest(item_root)
    try:
        if args.action == "feedback-action":
            action_path = Path(args.action_file).resolve()
            action = json.loads(action_path.read_text(encoding="utf-8"))
            if not isinstance(action, dict):
                raise FeedbackActionDispatchError("feedback action 必须是 JSON object")
            observation = FeedbackApplicationActionRuntime(
                item_root=item_root,
                run_id=args.run_id,
                actor=args.actor,
                provider=args.provider,
            ).dispatch(action)
            print(json.dumps(observation, ensure_ascii=False, indent=2))
            return 0
        if args.action == "audit-feedback-actions":
            result = validate_feedback_action_journal(item_root)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.action == "mark-review-not-applicable":
            if not args.run_id:
                raise HarnessStateError(
                    "mark-review-not-applicable 必须提供 --run-id"
                )
            state, receipt = ReviewDispositionService(
                item_root
            ).declare_not_applicable(
                run_id=args.run_id,
                declared_by=args.declared_by,
                reason=args.reason,
                force_unlock=args.force_unlock,
            )
            print(f"review_disposition: {receipt['disposition']}")
            print(f"declared_by: {receipt['declared_by']}")
            print_state(state)
            return 0
        if args.action in {
            "approve-requirement",
            "reject-requirement",
            "recover-requirement-approval",
        }:
            if not args.run_id:
                raise HarnessStateError(f"{args.action} 必须提供 --run-id")
            service = RequirementApprovalService(item_root)
            if args.action == "approve-requirement":
                state, receipt = service.approve(
                    run_id=args.run_id,
                    reviewed_by=args.reviewed_by,
                    note=args.note,
                    force_unlock=args.force_unlock,
                )
            elif args.action == "reject-requirement":
                state, receipt = service.reject(
                    run_id=args.run_id,
                    reviewed_by=args.reviewed_by,
                    note=args.note,
                    force_unlock=args.force_unlock,
                )
            else:
                state, receipt = service.recover(
                    run_id=args.run_id,
                    force_unlock=args.force_unlock,
                )
            print(f"approval_id: {receipt['approval_id']}")
            print(f"approval_status: {receipt['status']}")
            print_state(state)
            return 0
        if args.action in {
            "approve-roles",
            "reject-roles",
            "recover-roles",
        }:
            if not args.run_id:
                raise HarnessStateError(f"{args.action} 必须提供 --run-id")
            persisted_state = StateStore(item_root).load(args.run_id)
            role_runtime = MultiRoleAgentRuntime(
                item_root=item_root,
                project_code=project_code,
                work_item_id=work_item_id,
                work_item_level=str(persisted_state["work_item_level"]),
                gateway=ScriptedModelGateway(actions=[]),
            )
            if args.action == "approve-roles":
                state, approval = role_runtime.approve(
                    run_id=args.run_id,
                    approval_id=args.approval_id,
                    candidate_hash=args.candidate_hash,
                    approved_by=args.approved_by,
                    force_unlock=args.force_unlock,
                )
            elif args.action == "reject-roles":
                state, approval = role_runtime.reject(
                    run_id=args.run_id,
                    approval_id=args.approval_id,
                    rejected_by=args.rejected_by,
                    reason=args.reason,
                    force_unlock=args.force_unlock,
                )
            else:
                state, recovery = role_runtime.recover(
                    run_id=args.run_id,
                    recovered_by=args.recovered_by,
                    reason=args.reason,
                    force_unlock=args.force_unlock,
                )
                print(f"recovery_id: {recovery['recovery_id']}")
                print(f"recovery_status: {recovery['status']}")
                print_state(state)
                return 0
            print(f"approval_id: {approval['approval_id']}")
            print(f"approval_status: {approval['status']}")
            print_state(state)
            return 0
        if args.action in {
            "approve-generation",
            "reject-generation",
            "recover-generation",
        }:
            if not args.run_id:
                raise HarnessStateError(f"{args.action} 必须提供 --run-id")
            persisted_state = StateStore(item_root).load(args.run_id)
            generation_service = ControlledGenerationService(
                item_root=item_root,
                project_code=project_code,
                work_item_id=work_item_id,
                work_item_level=str(persisted_state["work_item_level"]),
            )
            if args.action == "approve-generation":
                state, approval = generation_service.approve(
                    run_id=args.run_id,
                    approval_id=args.approval_id,
                    candidate_hash=args.candidate_hash,
                    approved_by=args.approved_by,
                    force_unlock=args.force_unlock,
                )
                print(f"approval_id: {approval['approval_id']}")
                print(f"approval_status: {approval['status']}")
                print_state(state)
                return 0
            if args.action == "reject-generation":
                state, approval = generation_service.reject(
                    run_id=args.run_id,
                    approval_id=args.approval_id,
                    rejected_by=args.rejected_by,
                    reason=args.reason,
                    force_unlock=args.force_unlock,
                )
                print(f"approval_id: {approval['approval_id']}")
                print(f"approval_status: {approval['status']}")
                print_state(state)
                return 0
            recovered = generation_service.recover(
                run_id=args.run_id,
                force_unlock=args.force_unlock,
            )
            print(f"run_id: {args.run_id}")
            print(f"recovered: {str(recovered).lower()}")
            return 0
        if args.action == "audit-run":
            run_id = args.run_id or StateStore(item_root).current_run_id()
            code, report = HarnessRunAuditor(item_root).audit(run_id)
            print(f"audit_run_id: {run_id}")
            print(f"audit_passed: {str(report['passed']).lower()}")
            print(f"audit_errors: {len(report['errors'])}")
            for error in report["errors"]:
                print(f"- {error}")
            return code
        if args.action == "generate":
            level, level_source = resolve_work_item_level(
                manifest,
                args.work_item_level,
            )
            run_id = args.run_id or default_run_id()
            provider_command = (
                parse_provider_command(args.provider_command_json)
                if args.provider == "command"
                and args.provider_command_json
                else None
            )
            generation_service = ControlledGenerationService(
                item_root=item_root,
                project_code=project_code,
                work_item_id=work_item_id,
                work_item_level=level,
            )
            code, state = generation_service.start(
                run_id=run_id,
                provider=args.provider,
                provider_command=provider_command,
                timeout_seconds=args.provider_timeout_seconds,
                force_unlock=args.force_unlock,
            )
            print(f"work_item_level_source: {level_source}")
            print_state(state)
            return code
        if args.action == "reject-case-plan":
            if not args.run_id:
                raise HarnessStateError("reject-case-plan 必须提供 --run-id")
            service = CasePlanApprovalService(item_root)
            state, approval = service.reject(
                run_id=args.run_id,
                approval_id=args.approval_id,
                rejected_by=args.rejected_by,
                reason=args.reason,
                force_unlock=args.force_unlock,
            )
            print(f"approval_id: {approval['approval_id']}")
            print(f"approval_status: {approval['status']}")
            print_state(state)
            return 0
        if args.action == "recover-case-plan":
            if not args.run_id:
                raise HarnessStateError(
                    "recover-case-plan 必须提供 --run-id"
                )
            service = CasePlanApprovalService(item_root)
            state, approval, transaction = service.recover(
                run_id=args.run_id,
                force_unlock=args.force_unlock,
            )
            print(f"approval_id: {approval['approval_id']}")
            print(f"approval_status: {approval['status']}")
            print(f"transaction_status: {transaction['status']}")
            print_state(state)
            return 0
        if args.action == "approve-case-plan":
            if not args.run_id:
                raise HarnessStateError("approve-case-plan 必须提供 --run-id")
            service = CasePlanApprovalService(item_root)
            state, approval = service.approve(
                run_id=args.run_id,
                approval_id=args.approval_id,
                candidate_hash=args.candidate_hash,
                approved_by=args.approved_by,
                force_unlock=args.force_unlock,
            )
            print(f"approval_id: {approval['approval_id']}")
            print(f"approval_status: {approval['status']}")
            print_state(state)
            return 0
        if args.action == "agent-case-plan":
            level, level_source = resolve_work_item_level(
                manifest,
                args.work_item_level,
            )
            run_id = args.run_id or default_run_id()
            gateway = CommandModelGateway(
                parse_provider_command(args.provider_command_json)
            )
            loop = CasePlanAgentLoop(
                item_root=item_root,
                project_code=project_code,
                work_item_id=work_item_id,
                work_item_level=level,
                gateway=gateway,
                max_turns=args.max_turns,
                max_repairs=args.max_repairs,
                budget=BudgetConfig(
                    max_model_calls=args.max_turns,
                    max_wall_seconds=args.max_wall_seconds,
                    max_total_tokens=args.max_total_tokens,
                    max_cost_usd=args.max_cost_usd,
                    require_usage=args.require_usage,
                ),
            )
            code, state = loop.run(
                run_id=run_id,
                force_unlock=args.force_unlock,
            )
            print(f"work_item_level_source: {level_source}")
            print_state(state)
            return code
        if args.action == "agent-roles":
            level, level_source = resolve_work_item_level(
                manifest,
                args.work_item_level,
            )
            run_id = args.run_id or default_run_id()
            max_model_calls = args.max_model_calls or (
                48
                if args.parallel_reviewers
                else args.max_turns_per_role * 4
            )
            command_gateway = CommandModelGateway(
                parse_provider_command(args.provider_command_json),
                timeout_seconds=(
                    args.reviewer_timeout_seconds
                    if args.parallel_reviewers
                    else 120
                ),
            )
            role_runtime = MultiRoleAgentRuntime(
                item_root=item_root,
                project_code=project_code,
                work_item_id=work_item_id,
                work_item_level=level,
                gateway=command_gateway,
                max_turns_per_role=args.max_turns_per_role,
                max_repairs_per_role=args.max_repairs_per_role,
                budget=BudgetConfig(
                    max_model_calls=max_model_calls,
                    max_wall_seconds=args.max_wall_seconds,
                    max_total_tokens=args.max_total_tokens,
                    max_cost_usd=args.max_cost_usd,
                    require_usage=args.require_usage,
                ),
                parallel_reviewers=args.parallel_reviewers,
                max_turns_per_reviewer=args.max_turns_per_reviewer,
                max_repairs_per_reviewer=args.max_repairs_per_reviewer,
                reviewer_timeout_seconds=args.reviewer_timeout_seconds,
            )
            code, state = role_runtime.run(
                run_id=run_id,
                force_unlock=args.force_unlock,
            )
            print(f"work_item_level_source: {level_source}")
            print_state(state)
            return code
        orchestrator = DeterministicOrchestrator(
            item_root=item_root,
            project_code=project_code,
            work_item_id=work_item_id,
        )
        if args.action == "start":
            level, level_source = resolve_work_item_level(
                manifest,
                args.work_item_level,
            )
            run_id = args.run_id or default_run_id()
            code, state = orchestrator.start(
                run_id=run_id,
                work_item_level=level,
                strict=args.strict,
                stop_at=args.stop_at,
                force_unlock=args.force_unlock,
            )
            print(f"work_item_level_source: {level_source}")
            print_state(state)
            return code
        if args.action == "resume":
            code, state = orchestrator.resume(
                run_id=args.run_id,
                stop_at=args.stop_at,
                force_unlock=args.force_unlock,
            )
            print_state(state)
            return code
        if args.action == "status":
            state = orchestrator.status(args.run_id)
            print_state(state)
            return 0
        if args.action == "cancel":
            state = orchestrator.cancel(
                run_id=args.run_id,
                force_unlock=args.force_unlock,
            )
            print_state(state)
            return 0
    except (
        HarnessStateError,
        FeedbackActionDispatchError,
        HookConfigurationError,
        ControlledGenerationError,
        ArtifactWorkspaceError,
        ModelGatewayError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"harness_error: {exc}")
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
