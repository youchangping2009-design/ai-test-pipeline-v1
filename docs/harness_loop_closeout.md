# Harness-Loop End-to-End Closeout

本文件记录 P4-009 的目标架构关闭结论。关闭表示当前本地、单工作项 Harness 已具备可恢复、可审计、可回归的受限执行链路，不表示引入分布式调度、操作系统沙箱或长期记忆。

## 已关闭能力

- Harness Run/Stage/Event/Diagnostic/Action/Approval/Telemetry/Hook/Generation/Role Runtime 均有结构化契约。
- 确定性 Orchestrator 支持 `start / status / resume / cancel`、checkpoint 指纹和失败诊断。
- Case Plan 与四角色 Agent Runtime 只允许白名单 Action，候选先进入 staging。
- 受控生成在隔离仓库执行 normalizer/strict，发布绑定 candidate、目标和上游输入 hash。
- 多文件发布具备 transaction journal、备份、发布后 strict、回滚和显式恢复。
- 工作项锁使用唯一所有权 token；活跃进程锁不能被 `--force-unlock` 删除，旧持有者不会删除后继锁。
- 崩溃恢复会先检查完整备份、删除发布临时文件，再执行全量回滚；备份缺失时拒绝部分恢复。
- Case Plan 单文件审批提交也使用独立 journal：未完成替换回滚到 pending，已 committed 替换幂等完成 approval/run metadata。
- Multi-role 进程崩溃遗留的 running run 使用 `recover-roles` 终态化：保留 run-local 证据、跳过未完成角色并取消 run，不续 turn、不复用部分 Reviewer 结果。
- `audit-run` 校验事件序列、Action/Approval/Hook 关联、Telemetry、角色状态、候选和发布事务。
- Requirement Sources 机器校验与 evidence 之间存在正式人工门：新工作项默认写入 `requirement_approval_required=true`，run 停在 `waiting_approval`；receipt 绑定摘要、来源清单、原始输入、需求版本和 run。
- `approve-requirement / reject-requirement` 要求显式 reviewer/note；`recover-requirement-approval` 可在 receipt 已写但 event/state 未完成时幂等补全。内容漂移会失效旧批准和下游 checkpoint。
- Requirement intake checkpoint 与 receipt 共用 canonical binding；manifest 的运行期/派生字段变化不撤销批准。历史完整-manifest checkpoint 在 receipt 仍匹配时会原位规范化，不要求重复审批；真实绑定漂移仍创建新的 pending approval ID 并保持审计事件隔离。
- minimal 清理拒绝删除非终结 run、pending approval、进程锁或未恢复事务；默认把发布备份和事务元数据归档到 `.generation/backups/`。
- smoke/regression/golden 与 CI 门禁已覆盖通用规则 fixture、负向检查和 Harness 单测，不默认绑定业务工作项。
- `scripts/run_harness_closeout.py` 一次执行确定性 Harness、run audit、golden 和质量基线，并校验工作项 `.generation` 之外的文件 hash 不变。

## 已确认但未采用的原建议

- 不将 `testcase_bundle.json` 切换为 testcase 真源；正式真源继续是 `testcases/testcases_main.md`。
- 不让模型直接写 traceability；当前由确定性 normalizer 派生。
- 不把 Hook handler 或 command adapter 宣称为操作系统级沙箱；二者仍是仓库内人工选择的可信代码。

## 后续阶段

以下能力不属于 P4-009，后续如有明确收益再进入新任务：

- 多机或网络文件系统上的分布式锁。
- 跨进程或分布式 Reviewer 调度；当前仅支持单机 Case Reviewer 子阶段的三路线程并发。
- 长期 memory；强约束知识仍只进入 rule、skill、checklist、schema 或 eval。
- 自动代码评审和外部系统回写。

## 已知边界

- 多文件发布是带 journal 的逻辑原子事务，不是文件系统原生多文件原子提交。
- P4-004 之前创建的历史 Agent run 没有 Telemetry/Run Summary；当前审计会如实报告缺失，不伪造回填。它们终结后可由安全清理移除。
- Agent Loop 与四角色 Runtime 不支持从中间 model turn 续跑；multi-role 崩溃 run 先用 `recover-roles` 安全取消，事务/审批走各自恢复入口，再以新 run 重跑。
- 本地锁以 PID 活性和唯一 token 保护单机工作项并发；不承诺跨主机互斥。
- `inputs/requirement_approval.json` 是长期人工凭证，不属于 `.generation` 派生物；cleanup 和 controlled generation 都不能删除、发布或伪造它。CI 只校验 receipt，不执行批准。
- 无代码 M 档可用 `validate_work_item.py --strict --skip-code-reviews` 完成工作项门禁；Harness run 当前仍无可审计的 Review `not_applicable` disposition，不得用待评审模板推进 Review checkpoint。

## Requirement approval 操作

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-requirement \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --reviewed-by <REVIEWER> \
  --note "<NOTE>"

/usr/bin/python3 scripts/run_work_item_pipeline.py reject-requirement \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --reviewed-by <REVIEWER> \
  --note "<NOTE>"

/usr/bin/python3 scripts/run_work_item_pipeline.py recover-requirement-approval \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID>
```

## 正式验收

```bash
/usr/bin/python3 scripts/run_harness_closeout.py \
  --project-code DEMO \
  --work-item-id REQ-001 \
  --work-item-level M
```

验收必须同时满足：

1. 确定性 Harness 完成且 `audit-run` 通过。
2. golden eval 通过。
3. `run_quality_baseline.py` 全部通过。
4. 显式传入工作项的 `.generation` 之外文件聚合 hash 前后一致；macOS `.DS_Store` 文件系统元数据不计入，其他流程资产全部纳入。
