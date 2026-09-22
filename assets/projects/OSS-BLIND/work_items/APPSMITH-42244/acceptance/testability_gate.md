# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | APP-R001 | product_behavior | testable | generate_acceptance_example | confirmed | 在真正创建连接之前检查 JDBC URL 是否属于 Databricks JDBC 协议；非法协议必须返回 The JDBC URL must use the jdbc:databricks:// protocol. | 可通过连接调用顺序及错误目标未建立连接直接验证。 |
| TG-002 | APP-R002 | field_constraint | testable | generate_acceptance_example | confirmed | 已知合法协议前缀为 jdbc:databricks://；有效且自定义的 Databricks URL 应继续进入连接流程。 | 合法协议前缀与自定义合法 URL 的兼容结果均可直接构造输入验证。 |
| TG-003 | APP-R003 | product_behavior | testable | generate_acceptance_example | confirmed | Databricks 连接由明确的 Databricks JDBC driver 处理，非 Databricks URL 被拒绝后不得转交其他已注册 driver。 | 可验证 driver 调用对象以及拒绝后不存在其他 driver 接管行为。 |
| TG-004 | APP-R004 | product_behavior | testable | generate_acceptance_example | confirmed | Databricks driver 拒绝 URL 或未返回连接时，应按失败分支返回连接创建错误并停止后续连接行为，不得判为成功。 | driver 拒绝 URL 与返回空连接是两个可独立构造和定位的失败分支，应分别形成原子验收场景。 |
| TG-005 | APP-R005 | product_behavior | testable | generate_acceptance_example | confirmed | 有效 URL 建立连接时，JDBC 属性 UID 固定为 token，PWD 使用当前 token 值；既有合法配置及安装升级场景行为不变。 | 可捕获 JDBC 连接属性，分别断言 UID 固定值、PWD token 值及连接成功结果。 |
| TG-006 | APP-R006 | product_behavior | testable | generate_acceptance_example | confirmed | JDBC URL 校验失败发生在连接创建阶段，不应先对错误目标建立网络连接。 | 可通过网络调用观测或 driver mock 验证失败前无错误目标连接副作用。 |
| TG-007 | APP-FR001 | product_behavior | testable | skip_case | confirmed | 先确认 JDBC URL 属于 Databricks JDBC 协议，再尝试建立网络连接。 | 与 APP-R001 和 APP-R006 的连接前校验及副作用断言重复，由对应显式规则统一承接。 |
| TG-008 | APP-FR002 | field_constraint | testable | skip_case | confirmed | 已知合法协议前缀为 jdbc:databricks://。 | 与 APP-R002 的协议前缀约束重复。 |
| TG-009 | APP-FR004 | product_behavior | testable | skip_case | confirmed | 返回连接创建错误，停止后续连接行为，不得判为成功。 | 与 APP-R004 的失败关闭规则重复。 |
| TG-010 | APP-FR005 | product_behavior | testable | skip_case | confirmed | 自定义合法 URL 与既有有效安装、升级场景行为不回退。 | 与 APP-R005 的兼容性规则重复。 |
| TG-011 | APP-FIELD-001 | field_constraint | testable | skip_case | confirmed | 已知合法协议前缀为 jdbc:databricks://，非 Databricks JDBC URL 在连接前被拒绝。 | 与 APP-R001、APP-R002 的 URL 校验规则重复，不额外生成同义验收场景。 |
| TG-012 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 仅检查字符串前缀可能遗漏大小写、前后空白、编码或相似协议边界，应由后续设计区分正式验收与风险加固。 | 边界处理口径尚未确认，仅保留风险，不推断为强制拒绝规则。 |
| TG-013 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | driver 返回空连接、抛出异常和拒绝 URL 的错误口径尚未完全定义。 | 错误码和文案未定义，仅保留异常口径风险。 |
| TG-014 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 历史非 Databricks URL 配置会从可尝试连接变为明确失败，这是预期行为变化。 | 该项用于记录历史配置影响，不额外生成独立产品验收。 |
