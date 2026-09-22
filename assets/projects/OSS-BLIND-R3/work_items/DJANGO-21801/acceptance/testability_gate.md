# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | DJG-R001 | product_behavior | testable | generate_acceptance_example | confirmed | 模型变更只移除字段的 db_index=True，不新增、删除或修改 Meta.constraints 中的命名 UniqueConstraint。 | 模型变更范围可通过迁移前后的模型状态与生成操作直接核对。 |
| TG-002 | DJG-R002 | backend_job | testable | generate_acceptance_example | confirmed | 定位待删除普通索引时，必须排除 Meta.constraints 中仍存在的命名唯一约束。 | 可构造普通索引与命名唯一约束并存的数据库状态，验证迁移选择目标。 |
| TG-003 | DJG-R003 | backend_job | testable | generate_acceptance_example | confirmed | 生成并应用迁移后，字段上的普通非唯一索引被删除，命名唯一约束及其数据库唯一索引仍存在。 | 迁移后的普通索引消失与唯一约束保留可通过数据库 introspection 分别断言。 |
| TG-004 | DJG-R004 | backend_job | testable | generate_acceptance_example | confirmed | 迁移 SQL 只删除普通非唯一索引，不包含删除命名唯一约束的语句。 | 可直接检查生成 SQL 的删除目标和缺失的约束删除语句。 |
| TG-005 | DJG-R005 | product_behavior | testable | generate_acceptance_example | confirmed | 应用迁移后写入重复字段值时，数据库仍通过命名唯一约束拒绝该写入。 | 可在迁移后插入重复值，以数据库拒绝结果验证唯一性仍生效。 |
| TG-006 | DJG-R006 | backend_job | testable | generate_acceptance_example | confirmed | 迁移前已有的合法数据在迁移后保持不变。 | 可在迁移前准备合法数据并在迁移后逐条比对。 |
| TG-007 | DJG-FR002 | backend_job | testable | skip_case | confirmed | 迁移后分别检查普通索引消失和命名唯一约束保留。 | 与 DJG-R003 的两个原子结果重复，由显式规则统一承接。 |
| TG-008 | DJG-FR003 | product_behavior | testable | skip_case | confirmed | 不得仅以 introspection 结果代替唯一性行为验证。 | 与 DJG-R005 的重复值写入行为验证重复。 |
| TG-009 | DJG-FR004 | backend_job | testable | skip_case | confirmed | 迁移不得修改或丢失已有合法数据。 | 与 DJG-R006 的既有数据保持规则重复。 |
| TG-010 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | MySQL 将唯一约束表现为唯一索引，可能导致普通索引查找误命中约束索引。 | 该项解释缺陷触发机制，正式行为已由 DJG-R002 至 DJG-R005 覆盖。 |
| TG-011 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | 不同 Django 维护版本的迁移行为需要分别确认；来源只报告 6.1 和 4.2。 | 版本矩阵范围未被正式需求定义，仅保留兼容性风险。 |
| TG-012 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 迁移 SQL 正确不等于最终数据库状态正确，需要同时验证 schema 和重复写入行为。 | 这是测试设计完整性提醒，不单独升级为产品验收规则。 |
