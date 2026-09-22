# 开发自测用例

# 页面：Temporal Workflow API

## 板块：SignalWithStart 去重

| 用例编号 | 所属模块 | 所属功能点 | 用例标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 标签 | 测试类型 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OSS-BLIND-R3-TEMPORALAPI-SIGNALSTART-API-FL-001 | SignalWithStart 幂等 | 关闭后重试去重 | Workflow 关闭后仍可按原 request ID 去重 | 首次 `SignalWithStart` 已创建 run 并记录 request ID，且该 Workflow Execution 已关闭。 | 1. 使用相同 namespace、workflow ID 和 request ID 重试 `SignalWithStart`。 | 1. Workflow 关闭后，首次 request ID 与原始 run 的去重关联状态仍可被命中。 | P0 | AI-API用例,开发必测,测试必测 | 流程验证 | 来源 CasePlan：CP-001；来源 Flow：CP-001；来源 Acceptance：AE-001；来源 Rule：TMP-R001；来源coverage：COV-EX-0006 |
| OSS-BLIND-R3-TEMPORALAPI-SIGNALSTART-API-DV-001 | SignalWithStart 幂等 | 关闭后重试去重 | 相同请求重试返回首次创建的 run ID | 已记录首次 `SignalWithStart` 使用的 namespace、workflow ID、request ID 和返回 run ID。 | 1. 以相同三个标识重试 `SignalWithStart`。 | 1. 重试响应中的 run ID 等于首次请求创建的 run ID。 | P0 | AI-API用例,开发必测,测试必测 | 数据校验 | 来源 CasePlan：CP-002；来源 Acceptance：AE-002；来源 Rule：TMP-R002；来源coverage：COV-EX-0007 |
| OSS-BLIND-R3-TEMPORALAPI-SIGNALSTART-API-ST-001 | SignalWithStart 幂等 | 关闭后重试去重 | 去重命中不创建新的 Workflow run | 首次 `SignalWithStart` 创建的 run 已关闭，并记录当前 workflow ID 下的 run 数量。 | 1. 使用相同 request ID 重试 `SignalWithStart`。 | 1. 该 workflow ID 下的 run 数量不增加。 | P0 | AI-API用例,开发必测,测试必测 | 状态流转 | 来源 CasePlan：CP-003；来源 Acceptance：AE-003；来源 Rule：TMP-R003；来源coverage：COV-EX-0008 |
| OSS-BLIND-R3-TEMPORALAPI-SIGNALSTART-API-ST-002 | SignalWithStart 幂等 | 关闭后重试去重 | 去重命中不再次投递 signal | 首次 `SignalWithStart` 的 signal 已被原 run 处理，并记录 signal 处理次数。 | 1. 使用相同 request ID 重试 `SignalWithStart`。 | 1. signal 处理次数不增加。<br>2. 原 run 不收到第二次相同 signal。 | P0 | AI-API用例,开发必测,测试必测 | 状态流转 | 来源 CasePlan：CP-004；来源 Acceptance：AE-004；来源 Rule：TMP-R003；来源coverage：COV-EX-0009 |
| OSS-BLIND-R3-TEMPORALAPI-SIGNALSTART-API-AB-001 | SignalWithStart 幂等 | 关闭后重试去重 | 不同 request ID 不命中首次请求去重结果 | 已存在一次 `SignalWithStart` 请求及其 request ID。 | 1. 使用不同 request ID 发起 `SignalWithStart`。 | 1. 该请求不返回首次 request ID 对应的去重结果。<br>2. 该请求不计为首次请求的重复。 | P0 | AI-API用例,开发必测,测试必测 | 异常 | 来源 CasePlan：CP-007；来源 Acceptance：AE-007；来源 Rule：TMP-R005；来源coverage：COV-EX-0012 |
| OSS-BLIND-R3-TEMPORALAPI-SIGNALSTART-API-ST-003 | SignalWithStart 幂等 | 关闭后重试去重 | 关闭后重试不改变原 run 最终状态 | 首次请求创建的 run 已关闭，并记录其最终状态。 | 1. 使用相同 request ID 重试 `SignalWithStart`。 | 1. 原 run 的最终状态与重试前一致。 | P0 | AI-API用例,开发必测,测试必测 | 状态流转 | 来源 CasePlan：CP-008；来源 Acceptance：AE-008；来源 Rule：TMP-R006；来源coverage：COV-EX-0013 |
