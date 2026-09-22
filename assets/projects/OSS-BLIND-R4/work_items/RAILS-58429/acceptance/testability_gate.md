# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | RAI-R001 | backend_job | testable | generate_acceptance_example | confirmed | 无 block 调用 `BroadcastLogger#tagged` 必须返回可继续调用日志方法的 BroadcastLogger，而不是 Array。 | 可直接断言返回类型并继续调用日志方法。 |
| TG-002 | RAI-R002 | backend_job | testable | generate_acceptance_example | confirmed | 无 block 返回对象中，所有支持 tagged 的 logger 应应用指定标签。 | 可检查多个 tagging logger 各自收到消息时的标签。 |
| TG-003 | RAI-R003 | backend_job | testable | generate_acceptance_example | confirmed | 不支持 tagged 的广播目标仍必须保留并收到后续日志消息。 | 可混合能力不同的 logger 并核对非 tagging 目标仍收到消息。 |
| TG-004 | RAI-R004 | backend_job | testable | generate_acceptance_example | confirmed | 有 block 调用时，用户 block 只执行一次，执行期间所有支持 tagged 的 logger 均激活标签。 | 可同时统计 block 执行次数和各 logger 的标签状态。 |
| TG-005 | RAI-R005 | backend_job | testable | generate_acceptance_example | confirmed | block 正常结束或抛出异常后，临时标签都必须清理，异常继续向调用方传播。 | 正常与异常路径都可检查后续日志标签及异常传播。 |
| TG-006 | RAI-R006 | backend_job | testable | generate_acceptance_example | confirmed | 是否参与标签处理以广播目标是否响应 `tagged` 为能力边界。 | 可用支持和不支持 tagged 的测试替身验证能力分流。 |
| TG-007 | RAI-R007 | backend_job | testable | generate_acceptance_example | confirmed | 单个支持 tagged 的 logger 和既有普通广播行为不得回退。 | 可对单 logger 和普通广播路径执行兼容性回归。 |
| TG-008 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 返回对象如果遗漏 non-tagging logger，会造成静默日志丢失。 | 广播保留行为已由 RAI-R003 承接，本项仅记录影响风险。 |
| TG-009 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | block 重复执行可能重复业务副作用，属于高风险兼容问题。 | 单次执行行为已由 RAI-R004 承接，本项只保留风险背景。 |
| TG-010 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 异常路径清理不完整会把标签泄漏到后续请求或线程。 | 异常清理由 RAI-R005 承接，跨请求/线程影响保留为扩展风险。 |
| TG-011 | RISK-004 | risk_hardening | risk_only | risk_note_only | confirmed | 嵌套标签、并发日志和不同 logger 返回值可能暴露组合边界。 | 公开需求未定义嵌套和并发契约，不升级为正式验收。 |
| TG-012 | ORACLE-RAI-DF-001 | risk_hardening | risk_only | risk_note_only | confirmed | 没有任何 logger 响应 tagged 时，block 形式仍应只 yield 一次并保持普通广播可用。 | 该能力边界来自递归 helper 的实现行为，获批需求未定义零 tagging logger 组合，因此不升级为正式验收。 |
