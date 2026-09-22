# Testpoints View

- Project: `OSS-BLIND-R3`
- Work Item: `TEMPORAL-11968`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | Temporal Workflow API | SignalWithStart 去重 | SignalWithStart 幂等 | 关闭后重试去重 | cross_surface_linkage | Workflow 关闭后仍可按原 request ID 去重 | Workflow 关闭后，首次 request ID 与原始 run 的去重关联状态仍可被命中。 | P0 | CP-001 | True |
| TP-002 | Temporal Workflow API | SignalWithStart 去重 | SignalWithStart 幂等 | 关闭后重试去重 | data_persistence | 相同请求重试返回首次创建的 run ID | 重试响应中的 run ID 等于首次请求创建的 run ID。 | P0 | CP-002 | True |
| TP-003 | Temporal Workflow API | SignalWithStart 去重 | SignalWithStart 幂等 | 关闭后重试去重 | backend_job | 去重命中不创建新的 Workflow run | 该 workflow ID 下的 run 数量不增加。 | P0 | CP-003 | True |
| TP-004 | Temporal Workflow API | SignalWithStart 去重 | SignalWithStart 幂等 | 关闭后重试去重 | backend_job | 去重命中不再次投递 signal | signal 处理次数不增加；原 run 不收到第二次相同 signal。 | P0 | CP-004 | True |
| TP-005 | Temporal Workflow API | SignalWithStart 去重 | SignalWithStart 幂等 | 关闭后重试去重 | data_persistence | 去重命中增加专用指标 | `SignalWithStartWorkflowStartDeduped` 指标按本次去重命中递增。 | P1 | CP-005 | True |
| TP-006 | Temporal Workflow API | SignalWithStart 去重 | SignalWithStart 幂等 | 关闭后重试去重 | data_persistence | 非去重请求不增加专用指标 | `SignalWithStartWorkflowStartDeduped` 指标不因该请求增加。 | P1 | CP-006 | True |
| TP-007 | Temporal Workflow API | SignalWithStart 去重 | SignalWithStart 幂等 | 关闭后重试去重 | field_rule | 不同 request ID 不命中首次请求去重结果 | 该请求不返回首次 request ID 对应的去重结果；该请求不计为首次请求的重复。 | P0 | CP-007 | True |
| TP-008 | Temporal Workflow API | SignalWithStart 去重 | SignalWithStart 幂等 | 关闭后重试去重 | backend_job | 关闭后重试不改变原 run 最终状态 | 原 run 的最终状态与重试前一致。 | P0 | CP-008 | True |
