# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | 模型变更仅移除字段普通索引声明 | 模型字段的“字段普通索引设置”已开启，并在 `Meta.constraints` 中声明命名 `UniqueConstraint`。 | 关闭“字段普通索引设置”并生成迁移。 | 模型变更仅包含关闭“字段普通索引设置”。<br>命名 `UniqueConstraint` 的定义保持不变。 | 服务端 Django 模型与迁移层 | backend_job | confirmed |  |
| AE-002 | TG-002 | 迁移删除目标排除命名唯一约束 | MySQL 8.4 中同一字段同时存在普通非唯一索引和命名唯一约束对应的唯一索引。 | Django 为关闭“字段普通索引设置”定位待删除索引。 | 待删除目标是普通非唯一索引。<br>仍存在于 `Meta.constraints` 的命名唯一约束不属于删除目标。 | 服务端 Django 迁移与数据库层 | backend_job | confirmed |  |
| AE-003 | TG-003 | 迁移后普通非唯一索引被删除 | 初始迁移已应用，目标字段同时具有普通非唯一索引和命名唯一约束。 | 生成并应用关闭“字段普通索引设置”的迁移。 | 数据库 introspection 结果中目标字段的普通非唯一索引不存在。 | 服务端 MySQL Schema 层 | backend_job | confirmed |  |
| AE-004 | TG-003 | 迁移后命名唯一约束保持存在 | 初始迁移已应用，目标字段存在命名唯一约束及对应数据库唯一索引。 | 生成并应用仅关闭“字段普通索引设置”的迁移。 | 命名唯一约束仍存在。<br>该约束对应的数据库唯一索引仍存在。 | 服务端 MySQL Schema 层 | backend_job | confirmed |  |
| AE-005 | TG-004 | 迁移 SQL 只删除普通非唯一索引 | 已生成仅关闭“字段普通索引设置”的迁移。 | 查看该迁移在 MySQL 8.4 上生成的 SQL。 | SQL 包含删除普通非唯一索引的语句。<br>SQL 不包含删除命名唯一约束的语句。 | 服务端 Django 迁移 SQL 层 | backend_job | confirmed |  |
| AE-006 | TG-005 | 迁移后重复写入仍受唯一性保护 | 关闭“字段普通索引设置”的迁移已应用，表中已有一条合法记录。 | 向受命名唯一约束保护的字段写入重复值。 | 迁移后命名唯一约束保持生效。<br>数据库拒绝重复值写入，表中不产生重复记录。 | 服务端 MySQL 数据行为层 | business_behavior | confirmed |  |
| AE-007 | TG-006 | 迁移前已有合法数据保持不变 | 迁移前表中存在多条满足唯一约束的合法数据，并记录其主键与字段值。 | 应用关闭“字段普通索引设置”的迁移。 | 迁移后的记录数量与迁移前一致。<br>各记录的主键和业务字段值与迁移前一致。 | 服务端 MySQL 数据层 | backend_job | confirmed |  |
