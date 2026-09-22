# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | 无 block 的 tagged 返回可继续记录日志的 BroadcastLogger | BroadcastLogger 包含至少一个支持 `tagged` 的 logger。 | 无 block 调用 `BroadcastLogger#tagged`。 | 返回值是 BroadcastLogger，而不是 Array。<br>可在返回值上继续调用日志方法。 | ActiveSupport BroadcastLogger API 层 | business_behavior | confirmed |  |
| AE-002 | TG-002 | 无 block 的 tagged 为所有 tagging logger 应用标签 | BroadcastLogger 包含多个支持 `tagged` 的 logger。 | 无 block 调用 `tagged` 并通过返回对象记录一条消息。 | 每个支持 `tagged` 的 logger 收到的消息都带有指定标签。 | ActiveSupport 多 logger 标签层 | backend_job | confirmed |  |
| AE-003 | TG-003 | 无 tagged 能力的广播目标仍被保留并接收日志 | BroadcastLogger 同时包含支持和不支持 `tagged` 的 logger。 | 无 block 调用 `tagged` 并通过返回对象记录一条消息。 | 不支持 `tagged` 的 logger 仍存在于广播目标中。<br>该 logger 收到后续日志消息。 | ActiveSupport 广播目标集合与日志分发层 | backend_job | confirmed |  |
| AE-004 | TG-004 | 有 block 的 tagged 只执行一次用户 block | BroadcastLogger 包含多个支持 `tagged` 的 logger，并准备可计数的用户 block。 | 带该 block 调用 `BroadcastLogger#tagged`。 | 用户 block 的执行次数等于一次。 | ActiveSupport tagged block 控制流层 | backend_job | confirmed |  |
| AE-005 | TG-004 | 有 block 时所有 tagging logger 同时激活标签 | BroadcastLogger 包含多个支持 `tagged` 的 logger。 | 在 `BroadcastLogger#tagged` 的同一个 block 内记录日志。 | 每个支持 `tagged` 的 logger 在该 block 执行期间收到带指定标签的消息。 | ActiveSupport 多 logger block 标签层 | backend_job | confirmed |  |
| AE-006 | TG-005 | tagged block 正常结束后清理临时标签 | BroadcastLogger 包含支持 `tagged` 的 logger。 | `tagged` block 正常结束后再记录一条日志。 | block 之后的日志不包含该临时标签。 | ActiveSupport 标签生命周期层 | backend_job | confirmed |  |
| AE-007 | TG-005 | tagged block 抛出异常后仍清理临时标签 | BroadcastLogger 包含支持 `tagged` 的 logger，且 block 将抛出已知异常。 | 捕获该异常后再记录一条日志。 | 异常之后的日志不包含该临时标签。 | ActiveSupport 异常路径标签生命周期层 | backend_job | confirmed |  |
| AE-008 | TG-005 | tagged block 的异常继续传播给调用方 | 准备一个会抛出特定异常的 `tagged` block。 | 调用 `BroadcastLogger#tagged` 执行该 block。 | 调用方向外收到同一异常类型和消息。<br>异常不被 BroadcastLogger 吞掉或替换。 | ActiveSupport tagged 异常传播层 | business_behavior | confirmed |  |
| AE-009 | TG-006 | 按是否响应 tagged 决定标签处理参与者 | BroadcastLogger 包含一个响应 `tagged` 的测试替身和一个不响应 `tagged` 的测试替身。 | 调用 `BroadcastLogger#tagged`。 | 只对响应 `tagged` 的目标调用标签处理。<br>不响应 `tagged` 的目标不接收 `tagged` 调用。 | ActiveSupport logger 能力分流层 | backend_job | confirmed |  |
| AE-010 | TG-007 | 单 logger 标签与普通广播行为保持兼容 | 分别准备仅含一个 tagging logger 的 BroadcastLogger，以及用于普通广播的多个 logger。 | 执行单 logger 的 `tagged` 记录和不带标签的普通广播记录。 | 单 logger 收到带指定标签的消息。<br>普通广播中的每个目标仍收到未被改变的消息。 | ActiveSupport BroadcastLogger 兼容回归层 | business_behavior | confirmed |  |
