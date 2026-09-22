# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | GRA-R001 | backend_job | testable | generate_acceptance_example | confirmed | 配置显式 Serializer 后，写入、单条读取、列表和 watch 均优先使用该 Serializer。 | 四条操作路径均可注入可观测 Serializer 并分别核对调用。 |
| TG-002 | GRA-R002 | backend_job | testable | generate_acceptance_example | confirmed | 未配置显式 Serializer 时，声明 GVK 的写入继续使用直接 JSON，其他 GVK 的写入使用已配置 codec。 | 可构造声明与非声明 GVK，分别检查持久化结果和 codec 调用。 |
| TG-003 | GRA-R003 | backend_job | testable | generate_acceptance_example | confirmed | 未配置显式 Serializer 时，单条读取、列表和 watch 继续使用已配置 codec。 | 三条读取路径均可独立触发并观察配置 codec 的解码结果。 |
| TG-004 | GRA-R004 | backend_job | testable | generate_acceptance_example | confirmed | datasource 通用 JSON Serializer 往返处理后必须保留对象 GVK。 | 可对比序列化前后的 GVK，结果确定且可自动断言。 |
| TG-005 | GRA-R005 | backend_job | testable | generate_acceptance_example | confirmed | 同一个 Go 类型承载不同 GVK 时，持久化和读回后仍能区分目标 GVK。 | 可用同类型不同 GVK 的对象执行往返并核对各自身份。 |
| TG-006 | GRA-R006 | backend_job | testable | generate_acceptance_example | confirmed | watch 中当前对象和历史对象的解码沿用原请求 context，并能观察请求取消。 | 可分别捕获当前/历史对象的 context，并通过取消请求观察处理终止。 |
| TG-007 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 默认分支若发生变化，可能破坏既有资源的存储格式兼容性。 | 默认兼容已由 GRA-R002/GRA-R003 承接，本项仅保留回归风险。 |
| TG-008 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | 列表或 watch 中混合版本/GVK 的对象可能暴露选择不一致。 | 公开需求未定义混合版本组合的完整契约，保留为扩展风险。 |
| TG-009 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 错误的上下文传播可能导致取消失效、资源泄漏或请求结束后继续解码。 | 取消的正式行为由 GRA-R006 承接，资源泄漏属于非功能风险。 |
| TG-010 | RISK-004 | risk_hardening | risk_only | risk_note_only | confirmed | 显式 Serializer 与 codec 的职责边界不清时可能出现双重转换。 | 选择优先级已有正式规则，未定义的双重转换实现风险不升级为需求断言。 |
| TG-011 | ORACLE-GRA-DF-001 | risk_hardening | risk_only | risk_note_only | confirmed | Serializer encode/decode 错误、非法 JSON、不可编码值和不同 decode target 属于实现级异常风险。 | 公开需求没有定义这些异常契约，仅保留为代码映证和专项测试风险，不生成正式业务用例。 |
| TG-012 | ER-002 | backend_job | testable | generate_acceptance_example | confirmed | APIStore 提供可选的、接收请求上下文的 Serializer 能力。 | 该语义来自已批准需求摘要，可在写入、单条读取和列表路径注入带标记 context 并核对 Serializer 收到原值。 |
| TG-013 | ORACLE-GRA-DF-003 | risk_hardening | risk_only | risk_note_only | confirmed | Serializer 实际持久化版本、跨资源组输出和删除路径版本豁免属于待确认的实现策略。 | 获批需求未定义版本上限及转换失败规则，只保留实现级风险，不生成正式业务用例。 |
| TG-014 | ORACLE-GRA-DF-004 | risk_hardening | risk_only | risk_note_only | confirmed | Serializer 实现需要支持并发安全调用，其生命周期和共享方式属于实现级风险。 | 并发安全仅由实现接口说明，获批需求仍将其列为开放问题，因此不升级为正式验收。 |
