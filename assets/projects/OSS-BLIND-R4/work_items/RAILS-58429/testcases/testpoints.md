# Testpoints View

- Project: `OSS-BLIND-R4`
- Work Item: `RAILS-58429`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | 无 block 标签广播 | field_rule | 无 block 的 tagged 返回可继续记录日志的 BroadcastLogger | 返回值是 BroadcastLogger，而不是 Array；可在返回值上继续调用日志方法。 | P0 | CP-001 | True |
| TP-002 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | 无 block 标签广播 | backend_job | 无 block 的 tagged 为所有 tagging logger 应用标签 | 每个支持 `tagged` 的 logger 收到的消息都带有指定标签。 | P0 | CP-002 | True |
| TP-003 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | 无 block 标签广播 | backend_job | 无 tagged 能力的广播目标仍被保留并接收日志 | 不支持 `tagged` 的 logger 仍存在于广播目标中；该 logger 收到后续日志消息。 | P0 | CP-003 | True |
| TP-004 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | Block 标签上下文 | backend_job | 有 block 的 tagged 只执行一次用户 block | 用户 block 的执行次数等于一次。 | P0 | CP-004 | True |
| TP-005 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | Block 标签上下文 | backend_job | 有 block 时所有 tagging logger 同时激活标签 | 每个支持 `tagged` 的 logger 在该 block 执行期间收到带指定标签的消息。 | P0 | CP-005 | True |
| TP-006 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | Block 标签上下文 | backend_job | tagged block 正常结束后清理临时标签 | block 之后的日志不包含该临时标签。 | P0 | CP-006 | True |
| TP-007 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | Block 标签上下文 | backend_job | tagged block 抛出异常后仍清理临时标签 | 异常之后的日志不包含该临时标签。 | P0 | CP-007 | True |
| TP-008 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | Block 标签上下文 | field_rule | tagged block 的异常继续传播给调用方 | 调用方向外收到同一异常类型和消息；异常不被 BroadcastLogger 吞掉或替换。 | P0 | CP-008 | True |
| TP-009 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | 无 block 标签广播 | backend_job | 按是否响应 tagged 决定标签处理参与者 | 只对响应 `tagged` 的目标调用标签处理；不响应 `tagged` 的目标不接收 `tagged` 调用。 | P1 | CP-009 | True |
| TP-010 | BroadcastLogger 标签广播 | 多 Logger 标签上下文 | BroadcastLogger tagged | 无 block 标签广播 | cross_surface_linkage | 单 logger 标签与普通广播行为保持兼容 | 两条记录流程完成后，单 logger 收到带指定标签的消息；普通广播中的每个目标仍收到未被改变的消息。 | P0 | CP-010 | True |
