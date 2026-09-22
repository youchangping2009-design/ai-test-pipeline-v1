# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | TMP-R001 | backend_job | testable | generate_acceptance_example | confirmed | 首次 SignalWithStart 的 request ID 与原始 run 的关联在该 Workflow Execution 关闭后仍可用于去重。 | 可先关闭首次 run，再以相同 request ID 重试并观察去重关联。 |
| TG-002 | TMP-R002 | product_behavior | testable | generate_acceptance_example | confirmed | 使用相同 namespace、workflow ID 和 request ID 重试 SignalWithStart 时，返回首次请求创建的 run ID。 | 首次与重试响应的 run ID 可直接比对。 |
| TG-003 | TMP-R003 | backend_job | testable | generate_acceptance_example | confirmed | 相同 request ID 的去重命中不得创建新的 Workflow run，也不得再次投递 signal。 | 可分别断言 run 数量不增加和 signal 处理次数不增加。 |
| TG-004 | TMP-R004 | backend_job | testable | generate_acceptance_example | confirmed | 去重命中时 SignalWithStartWorkflowStartDeduped 指标递增，非去重请求不得误计入该指标。 | 可在去重和非去重请求前后分别读取指标增量。 |
| TG-005 | TMP-R005 | product_behavior | testable | generate_acceptance_example | confirmed | 使用不同 request ID 的 SignalWithStart 请求不得被错误识别为首次请求的重复。 | 可替换 request ID 并观察请求未命中首次去重结果。 |
| TG-006 | TMP-R006 | backend_job | testable | generate_acceptance_example | confirmed | 关闭后重试不得改变原已关闭 run 的最终状态。 | 可在重试前后读取原 run 状态并比对。 |
| TG-007 | TMP-FR001 | backend_job | testable | skip_case | confirmed | 关闭状态不得使相同 request ID 失去去重关联。 | 与 TMP-R001 的关闭后去重关联规则重复。 |
| TG-008 | TMP-FR002 | product_behavior | testable | skip_case | confirmed | 重试响应不得返回新 run。 | 与 TMP-R002 的返回首次 run ID 规则重复。 |
| TG-009 | TMP-FR003 | backend_job | testable | skip_case | confirmed | 需要同时验证 run 与 signal 两类副作用。 | 与 TMP-R003 的两个原子副作用断言重复。 |
| TG-010 | TMP-FR004 | backend_job | testable | skip_case | confirmed | 非去重请求不得误计数。 | 与 TMP-R004 的非去重指标断言重复。 |
| TG-011 | TMP-FR005 | product_behavior | testable | skip_case | confirmed | 不得命中首次请求的去重结果。 | 与 TMP-R005 的不同 request ID 隔离规则重复。 |
| TG-012 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 执行关闭与重试并发可能形成竞态，需要验证关闭提交前后边界。 | 并发时序窗口未形成独立产品规则，仅保留后续风险设计提示。 |
| TG-013 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | 去重记录保留时长未公开，超出保留期后的行为不能脑补为永久去重。 | 保留期限未定义，不生成永久保留或超期行为的强断言。 |
| TG-014 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 不同 namespace、workflow ID 或 request ID 的请求不得被错误关联。 | request ID 差异的正式规则由 TMP-R005 承接，其余键维度作为风险扩展保留。 |
| TG-015 | RISK-004 | risk_hardening | risk_only | risk_note_only | confirmed | 返回原 run 与不发送重复 signal 必须同时满足，不能只验证其中一项。 | 该项是覆盖完整性提醒，正式断言已由 TMP-R002 和 TMP-R003 承接。 |
