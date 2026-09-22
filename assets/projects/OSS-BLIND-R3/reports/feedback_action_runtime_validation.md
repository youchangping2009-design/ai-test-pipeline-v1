# Feedback Application Restricted Action Runtime Validation

## Scope

本阶段只强化 AI Test Pipeline 的反馈回灌执行边界，不修改任何业务代码、盲测工作项设计资产或正式 testcase。

## Implemented Controls

- `harness_feedback_action.schema.json` 仅允许 prepare、propose、record 三类动作。
- `feedback-action` CLI 是 Agent 自动回灌的统一入口。
- propose 只能写 prepare 快照内已冻结的设计层路径。
- `design/design_feedback.json`、`design/feedback_application.json` 和 `testcases/testcases_main.md` 均不能通过 propose 修改。
- propose 不迁移状态；record 是唯一 `accepted -> applied` 入口，并继续使用 receipt-first/status-second 顺序。

## Validation

```bash
/usr/bin/python3 -m unittest \
  tests.test_feedback_action_runtime \
  tests.test_manage_feedback_application \
  tests.test_feedback_application_validation \
  tests.test_harness_runtime
```

结果：40/40 通过。覆盖正常三动作链路、直接状态写入拒绝、正式 testcase 越界拒绝、未 prepare 写入拒绝及 arbitrary shell 拒绝。

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```

结果：5/5 通过，162 项单元测试通过；PT083 strict/non-strict、回归评测和项目 strict 均通过。

## Remaining Boundary

仓库级 Runtime 无法撤销外部进程已有的操作系统文件权限，因此 Review/strict receipt gate 仍是直接绕过 Runtime 时的确定性兜底。后续可增加不可变 action journal 与 audit 重放，完善动作级审计与崩溃恢复证据。
