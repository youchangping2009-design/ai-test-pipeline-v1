# TEMPORAL-11968 Workflow 关闭后 SignalWithStart 重试去重需求整理

整理时间：2026-09-21

## 1. 资料来源

- `primary_requirement`：Temporal PR #11968 的公开说明。
- 本地冻结快照：`inputs/public_source_snapshot.md`。
- 实现 diff 与新增单元/功能测试被隔离为后续 Oracle，本阶段未消费。

## 2. 需求结论

客户端以相同 request ID 重试 `SignalWithStart` 时，即使原始 Workflow Execution 已关闭，也必须识别为同一启动请求。系统应返回原始 run，不创建新 run，也不再次发送 signal。

## 3. 前置条件 / 准备工作

- 准备可调用 `SignalWithStart` 的 namespace、workflow ID、signal 与 request ID。
- 首次请求成功创建并启动 workflow，signal 已被处理。
- 原始 workflow 在重试前进入关闭状态。
- 可查询 workflow run、signal 处理次数和去重指标。

## 4. 业务范围与不做范围

范围内：相同 request ID 的重试去重、原 run 返回、重复 signal 抑制、原执行关闭后的行为和去重可观测性。

范围外：不同 request ID 的正常新启动语义；一般 Signal、StartWorkflow 或 Update 的去重；未说明的 request ID 保留期限和跨 namespace 行为。

## 5. 面向研发的需求拆解

- 首次 `SignalWithStart` 的 request ID 与原始 run 关系在执行关闭后仍可用于去重。
- 相同 request ID 重试返回首次创建的 run 标识。
- 去重命中不得创建新 workflow run。
- 去重命中不得再次投递 signal。
- 去重事件应增加可识别的 `SignalWithStartWorkflowStartDeduped` 指标。

## 6. 面向测试的验收关注点

- 原 workflow 运行中重试与关闭后重试都验证同一 request ID 的幂等性。
- 关闭后重试返回的 run ID 与首次请求一致。
- workflow 历史或业务副作用中 signal 只出现一次。
- 不产生新的 run，也不改变已关闭原 run 的最终状态。
- 使用不同 request ID 时不被错误去重。
- 去重发生时对应指标递增，非去重请求不误计数。

## 7. 数据 / 埋点 / 接口 / 配置要求

- 关键输入：namespace、workflow ID、request ID、signal name 和 payload。
- 关键输出：原始 run ID、run 数量、signal 处理次数。
- 指标：`SignalWithStartWorkflowStartDeduped`。

## 8. 风险与兼容性

- 执行关闭与重试并发可能形成竞态，需要验证关闭提交前后边界。
- 去重记录保留时长未公开，超出保留期后的行为不能脑补为永久去重。
- 不同 namespace、workflow ID 或 request ID 的请求不得被错误关联。
- 返回原 run 与不发送重复 signal 必须同时满足，不能只验证其中一项。

## 9. 待确认问题

- request ID 去重记录的正式保留期限是什么？
- Continue-As-New、Terminate、Cancel、Fail、Complete 等不同关闭类型是否一致？
- 多节点并发重试时指标按请求数还是去重决策数计数？
- 已关闭原 run 的历史清理后应返回什么结果？

## 10. 本轮整理边界

本摘要只使用公开 PR 正文定义生成输入；代码差异和测试断言在资产冻结后用于 Oracle 评分。本阶段不生成 Structured PRD 或测试用例。
