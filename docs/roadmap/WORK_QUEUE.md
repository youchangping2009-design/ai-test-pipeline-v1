# Work Queue

本文件是仓库内任意 AI Agent 共用的自驱动任务队列。状态可取：

- `todo`
- `in_progress`
- `done`
- `blocked`

当前 Agent 每次应先读取 `NEXT_ACTION.md`。当 NEXT_ACTION 为空、已完成或阻塞时，从本文件选择最高优先级 `todo` 任务。

| Priority | Task ID | Status | Title | Scope | Exit Criteria |
|---|---|---|---|---|---|
| P1 | P1-1-001 | done | acceptance_examples strict validation | 强化 acceptance_examples schema/validator，并接入 M/L strict | M/L strict 下缺失或弱 acceptance_examples 会失败 |
| P1 | P1-1-002 | done | case_plan traces acceptance_examples | case_plan 优先追溯 source_example_ids | M/L strict 下 case_plan 缺 source_example_ids 会失败 |
| P1 | P1-1-003 | done | PT083 eval acceptance_examples assertions | PT083 eval 增加 acceptance_examples required assertions | eval 能检查 hard_block/soft_display/linkage 验收示例 |
| P1 | P1-2-001 | done | verification_responsibility_map deep validation | 深化责任划分规则，但不切 testcase 真源 | L strict 可稳定检查 B端/C端/API/风险责任 |
| P1 | P1-3-001 | done | work_item_level execution policy | 明确 S/M/L 在 pipeline 和 validator 中的执行策略 | 不同 level 的强制产物和 stop-at 行为清晰 |
| P1 | P1-4-001 | done | eval fixture expansion | 扩展 golden fixtures | 至少覆盖提示类、风险/API 类、跨端链路类 |
| P1 | P1-5-001 | done | test_design_matrix L-level integration | L 档接入 test_design_matrix，但保持模板兼容 | L strict 能识别空/弱 test_design_matrix |
| P1 | P1-6-001 | done | design_feedback from code review confirmation | code review 映证结果进入 design_feedback | 不直接覆盖 testcase，反馈到 design 层 |
| P2 | P2-001 | done | repair loop | 增加有限 repair loop | 最多 2 轮 repair，不降低规则强度 |
| P2 | P2-002 | done | eval fixture expansion | 扩展 eval 到多项目样例 | eval 能覆盖更多需求形态 |
| P3 | P3-001 | done | testcase_bundle.json compatibility-only projection | 新增 testcase_bundle.json 派生投影，不切换真源 | bundle 可从 testcases_main.md 生成并校验一致 |
| P4 | P4-001 | done | Harness contracts and deterministic orchestrator | 新增运行契约、checkpoint、start/status/resume/cancel 与只读阶段校验 | 可恢复且幂等，不修改正式测试资产，现有 strict 与基线不回退 |
| P4 | P4-002 | done | Harness structured diagnostics | 将 Validator 失败归一化为可路由 Diagnostic，并保留每次尝试历史 | strict 失败具备 code、责任 stage、path、severity、repair_hint |
| P4 | P4-003 | done | Restricted Case Plan agent loop | 模型只通过白名单 Action 操作 staging，校验后显式审批并 hash 提交 | 最多 8 turn/2 repair，默认不提交，正式真源受并发保护 |
| P4 | P4-004 | done | Harness governance and observability | 增加预算、用量、终态摘要、审批拒绝和 run replay audit | 超预算必停，run 可审计，审批生命周期完整 |
| P4 | P4-005 | done | Restricted Hook Dispatcher | 增加 pre/post/fail/approval/repair Hook、可信脚本边界、失败策略和审计 | Hook 不开放任意 shell，不改变 Validator 结论，可按策略阻塞编排 |
| P4 | P4-006 | done | Controlled full-pipeline generation | 将既有生成器按阶段接入 staging、校验、审批与原子提交 | 单工作项可一条命令生成到 strict，失败可恢复且不留下半提交真源 |
| P4 | P4-007 | done | Tiered eval and regression gate | 增加 smoke/regression/golden 三档、量化差异与 CI 入口 | 关键规则和 Harness 回归可自动拦截 |
| P4 | P4-008 | done | Multi-role restricted Agent Runtime | 将 PRD Structurer、Case Generator、Reviewer、Formatter 接入受限 Action Runtime | 四角色可调度，仍受 Schema、staging、预算和审批约束 |
| P4 | P4-009 | done | Harness-Loop end-to-end closeout | 完成故障恢复、并发、审计、清理和代表性工作项验收 | 目标架构清单关闭，无未记录缺口 |
| P4 | P4-010 | done | Case Plan commit recovery | 为审批提交增加 journal、崩溃恢复与关联审计 | approval、run state、事务与正式 Case Plan 在崩溃后可确定性恢复 |
| P5 | P5-001 | done | Parallel Reviewer Runtime | 在 Case Reviewer 阶段以 opt-in 方式并行运行 evidence、flow、testcase 三路只读 Reviewer | 3/3 barrier 后确定性聚合，默认兼容路径不变 |
| P5 | P5-002 | done | Multi-role crash recovery | 为崩溃遗留的 multi_role run 增加安全终态化入口 | 不复用部分 Reviewer 结果，不绕过 3/3，恢复后可审计和清理 |

## Selection Rules

1. 同优先级按文件顺序选择。
2. 被标记为 `blocked` 的任务不得继续推进，除非阻塞已解除。
3. 每轮只推进一个任务。
4. 若执行中发现任务范围过大，应拆分任务并更新队列。
