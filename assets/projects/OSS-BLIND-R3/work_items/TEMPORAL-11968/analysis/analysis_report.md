# Analysis Report

## Requirement Summary
- 标题：`TEMPORAL-11968 Workflow 关闭后 SignalWithStart 重试去重需求整理`
- 摘要：客户端以相同 request ID 重试 `SignalWithStart` 时，即使原始 Workflow Execution 已关闭，也必须识别为同一启动请求。系统应返回原始 run，不创建新 run，也不再次发送 signal。
- 主要页面数：0
- 主要展示面数：0

## Reasoning Snapshot
- explicit_rules：15
- implicit_rules：0
- field_constraints：0
- data_source_rules：0
- business_risks：4
- edge_cases：2
- ambiguities：4
- recommended_test_dimensions：6
- coverage_candidates：15

## Top Explicit Rules
- `ER-001` 客户端以相同 request ID 重试 `SignalWithStart` 时，即使原始 Workflow Execution 已关闭，也必须识别为同一启动请求。系统应返回原始 run，不创建新 run，也不再次发送 signal。
- `ER-002` 首次 `SignalWithStart` 的 request ID 与原始 run 关系在执行关闭后仍可用于去重。
- `ER-003` 相同 request ID 重试返回首次创建的 run 标识。
- `ER-004` 去重命中不得创建新 workflow run。
- `ER-005` 去重命中不得再次投递 signal。
- `ER-006` 去重事件应增加可识别的 `SignalWithStartWorkflowStartDeduped` 指标。
- `ER-007` 原 workflow 运行中重试与关闭后重试都验证同一 request ID 的幂等性。
- `ER-008` 关闭后重试返回的 run ID 与首次请求一致。

## Top Implicit Rules

## Key Risks
- `RISK-001` [high] 执行关闭与重试并发可能形成竞态，需要验证关闭提交前后边界。
- `RISK-002` [medium] 去重记录保留时长未公开，超出保留期后的行为不能脑补为永久去重。
- `RISK-003` [high] 不同 namespace、workflow ID 或 request ID 的请求不得被错误关联。
- `RISK-004` [medium] 返回原 run 与不发送重复 signal 必须同时满足，不能只验证其中一项。

## Ambiguities
- `AMB-001` request ID 去重记录的正式保留期限是什么？
- `AMB-002` Continue-As-New、Terminate、Cancel、Fail、Complete 等不同关闭类型是否一致？
- `AMB-003` 多节点并发重试时指标按请求数还是去重决策数计数？
- `AMB-004` 已关闭原 run 的历史清理后应返回什么结果？

## Recommended Test Dimensions
- `TD-001` 显式规则逐条验证：需求摘要已给出可追溯规则，后续设计应保持单规则单断言并验证成功与失败结果。
- `TD-002` 异常与失败处理：需求包含明确拒绝或失败语义，需要验证失败状态、错误反馈及副作用隔离。
- `TD-003` 兼容性与回归：需求要求保留既有合法行为或历史关系，需要同时验证变更路径与未变路径。
- `TD-004` 数据一致性与状态保留：需求涉及关系或状态保留，应核对操作前后数据集合而非只看接口成功。
- `TD-005` 风险与非功能约束：需求摘要已明确兼容性、性能或一致性风险，需与产品验收规则分层承接。
- `TD-006` 未决项追踪：摘要存在尚未确认的输入或验收口径，后续不得将其自动升级为强制规则。
