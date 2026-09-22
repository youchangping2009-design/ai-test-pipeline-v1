# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | Workflow 关闭后仍可按原 request ID 去重 | 首次 `SignalWithStart` 已创建 run 并记录 request ID，且该 Workflow Execution 已关闭。 | 使用相同 namespace、workflow ID 和 request ID 重试 `SignalWithStart`。 | Workflow 关闭后，首次 request ID 与原始 run 的去重关联状态仍可被命中。 | Temporal 服务端 API 与历史状态层 | backend_job | confirmed |  |
| AE-002 | TG-002 | 相同请求重试返回首次创建的 run ID | 已记录首次 `SignalWithStart` 使用的 namespace、workflow ID、request ID 和返回 run ID。 | 以相同三个标识重试 `SignalWithStart`。 | 重试响应中的 run ID 等于首次请求创建的 run ID。 | Temporal 服务端 API 层 | business_behavior | confirmed |  |
| AE-003 | TG-003 | 去重命中不创建新的 Workflow run | 首次 `SignalWithStart` 创建的 run 已关闭，并记录当前 workflow ID 下的 run 数量。 | 使用相同 request ID 重试 `SignalWithStart`。 | 该 workflow ID 下的 run 数量不增加。 | Temporal 服务端历史与持久化层 | backend_job | confirmed |  |
| AE-004 | TG-003 | 去重命中不再次投递 signal | 首次 `SignalWithStart` 的 signal 已被原 run 处理，并记录 signal 处理次数。 | 使用相同 request ID 重试 `SignalWithStart`。 | signal 处理次数不增加。<br>原 run 不收到第二次相同 signal。 | Temporal 服务端历史与 Worker 行为层 | backend_job | confirmed |  |
| AE-005 | TG-004 | 去重命中增加专用指标 | 已记录 `SignalWithStartWorkflowStartDeduped` 指标当前值，且首次请求的 run 已存在。 | 使用相同 request ID 发起命中去重的 `SignalWithStart` 重试。 | `SignalWithStartWorkflowStartDeduped` 指标按本次去重命中递增。 | Temporal 服务端指标层 | backend_job | confirmed |  |
| AE-006 | TG-004 | 非去重请求不增加专用指标 | 已记录 `SignalWithStartWorkflowStartDeduped` 指标当前值。 | 发起未命中历史 request ID 的 `SignalWithStart` 请求。 | `SignalWithStartWorkflowStartDeduped` 指标不因该请求增加。 | Temporal 服务端指标层 | backend_job | confirmed |  |
| AE-007 | TG-005 | 不同 request ID 不命中首次请求去重结果 | 已存在一次 `SignalWithStart` 请求及其 request ID。 | 使用不同 request ID 发起 `SignalWithStart`。 | 该请求不返回首次 request ID 对应的去重结果。<br>该请求不计为首次请求的重复。 | Temporal 服务端 API 与去重状态层 | business_behavior | confirmed |  |
| AE-008 | TG-006 | 关闭后重试不改变原 run 最终状态 | 首次请求创建的 run 已关闭，并记录其最终状态。 | 使用相同 request ID 重试 `SignalWithStart`。 | 原 run 的最终状态与重试前一致。 | Temporal 服务端历史状态层 | backend_job | confirmed |  |
