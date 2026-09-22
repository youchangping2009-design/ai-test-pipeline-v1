# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | K8S-R001 | backend_job | testable | generate_acceptance_example | confirmed | create 或 update DeviceTaintRule 时，若 `spec.deviceSelector` 存在且 driver、pool、device 全为空，必须返回 Warning。 | create 与 update 均可构造空 selector 并读取响应 Warning。 |
| TG-002 | K8S-R002 | backend_job | testable | generate_acceptance_example | confirmed | 空 selector 的警告文本必须为 `spec.deviceSelector: an empty selector matches every device from every driver in the cluster`。 | Warning header 文本可逐字断言。 |
| TG-003 | K8S-R003 | backend_job | testable | generate_acceptance_example | confirmed | `spec.deviceSelector` 省略时不得返回空 selector Warning。 | 可构造 nil selector 并确认响应中不存在目标警告。 |
| TG-004 | K8S-R004 | backend_job | testable | generate_acceptance_example | confirmed | selector 指定 driver、pool 或 device 任一范围字段时不得返回空 selector Warning。 | 三个范围字段均可分别构造并检查无目标警告。 |
| TG-005 | K8S-R005 | backend_job | testable | generate_acceptance_example | confirmed | 空 selector Warning 不得阻止 create/update 成功，也不得改变既有校验、持久化或 taint 执行语义。 | 可同时核对响应、对象持久化和既有校验/执行结果。 |
| TG-006 | K8S-R006 | backend_job | testable | generate_acceptance_example | confirmed | 空 selector 的告警判断不受 taint effect 取值影响，包括既有 `None` 预览取值。 | 可对不同 effect 组合重复空 selector 请求并比较告警。 |
| TG-007 | K8S-R007 | platform_scope | testable | generate_acceptance_example | confirmed | 使用 `kubectl --warnings-as-errors` 时客户端可返回非零状态，但服务端对象仍已创建。 | 可同时检查客户端退出码与服务端对象存在性。 |
| TG-008 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 最大风险是把 `soft_prompt` 错升为 `hard_block`，导致兼容性破坏。 | 非阻塞行为已由 K8S-R005 承接，本项仅保留风险说明。 |
| TG-009 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | nil 与 `{}` 的语义必须区分，否则会对合法的省略场景产生噪声。 | 正式 nil/空对象分支已由 K8S-R001/K8S-R003 承接，本项不重复生成。 |
| TG-010 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 客户端的 warnings-as-errors 行为容易被误判为服务端创建失败，需要同时核对对象状态。 | 客户端与服务端结果已由 K8S-R007 承接，本项只保留 Oracle 风险。 |
| TG-011 | RISK-004 | risk_hardening | risk_only | risk_note_only | confirmed | 多条警告并存时的去重和顺序可能影响客户端断言。 | 公开需求未定义多警告顺序与去重，不能升级为强断言。 |
| TG-012 | AMB-001 | field_constraint | needs_confirmation | needs_confirmation | unknown | driver/pool/device 组合为空字符串或只含空白时如何判定？ | 公开实现按指针是否为 nil 判断，但已批准需求未定义空字符串或空白值是否合法、是否会被默认化，确认前不生成正式用例。 |
