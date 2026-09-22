# 开发自测用例

# 页面：Django Migration 执行入口

## 板块：索引变更与数据库状态

| 用例编号 | 所属模块 | 所属功能点 | 用例标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 标签 | 测试类型 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OSS-BLIND-R3-DJANGOMIG-INDEXSCHEMA-SERVER-DV-001 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | 模型变更仅移除字段普通索引声明 | 模型字段的“字段普通索引设置”已开启，并在 `Meta.constraints` 中声明命名 `UniqueConstraint`。 | 1. 关闭“字段普通索引设置”并生成迁移。 | 1. 模型变更仅包含关闭“字段普通索引设置”。<br>2. 命名 `UniqueConstraint` 的定义保持不变。 | P0 | AI-API用例,开发必测,测试必测 | 数据校验 | 来源 CasePlan：CP-001；来源 Acceptance：AE-001；来源 Rule：DJG-R001；来源coverage：COV-EX-0001 |
| OSS-BLIND-R3-DJANGOMIG-INDEXSCHEMA-SERVER-ST-001 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | 迁移删除目标排除命名唯一约束 | MySQL 8.4 中同一字段同时存在普通非唯一索引和命名唯一约束对应的唯一索引。 | 1. Django 为关闭“字段普通索引设置”定位待删除索引。 | 1. 待删除目标是普通非唯一索引。<br>2. 仍存在于 `Meta.constraints` 的命名唯一约束不属于删除目标。 | P0 | AI-API用例,开发必测,测试必测 | 状态流转 | 来源 CasePlan：CP-002；来源 Acceptance：AE-002；来源 Rule：DJG-R002；来源coverage：COV-EX-0002 |
| OSS-BLIND-R3-DJANGOMIG-INDEXSCHEMA-SERVER-DV-002 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | 迁移后普通非唯一索引被删除 | 初始迁移已应用，目标字段同时具有普通非唯一索引和命名唯一约束。 | 1. 生成并应用关闭“字段普通索引设置”的迁移。 | 1. 数据库 introspection 结果中目标字段的普通非唯一索引不存在。 | P0 | AI-API用例,开发必测,测试必测 | 数据校验 | 来源 CasePlan：CP-003；来源 Acceptance：AE-003；来源 Rule：DJG-R003；来源coverage：COV-EX-0003 |
| OSS-BLIND-R3-DJANGOMIG-INDEXSCHEMA-SERVER-DV-003 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | 迁移后命名唯一约束保持存在 | 初始迁移已应用，目标字段存在命名唯一约束及对应数据库唯一索引。 | 1. 生成并应用仅关闭“字段普通索引设置”的迁移。 | 1. 命名唯一约束仍存在。<br>2. 该约束对应的数据库唯一索引仍存在。 | P0 | AI-API用例,开发必测,测试必测 | 数据校验 | 来源 CasePlan：CP-004；来源 Acceptance：AE-004；来源 Rule：DJG-R003；来源coverage：COV-EX-0004 |
| OSS-BLIND-R3-DJANGOMIG-INDEXSCHEMA-SERVER-ST-002 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | 迁移 SQL 只删除普通非唯一索引 | 已生成仅关闭“字段普通索引设置”的迁移。 | 1. 查看该迁移在 MySQL 8.4 上生成的 SQL。 | 1. SQL 包含删除普通非唯一索引的语句。<br>2. SQL 不包含删除命名唯一约束的语句。 | P0 | AI-API用例,开发必测,测试必测 | 状态流转 | 来源 CasePlan：CP-005；来源 Acceptance：AE-005；来源 Rule：DJG-R004；来源coverage：COV-EX-0005 |
| OSS-BLIND-R3-DJANGOMIG-INDEXSCHEMA-SERVER-FL-001 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | 迁移后重复写入仍受唯一性保护 | 关闭“字段普通索引设置”的迁移已应用，表中已有一条合法记录。 | 1. 向受命名唯一约束保护的字段写入重复值。 | 1. 迁移后命名唯一约束保持生效。<br>2. 数据库拒绝重复值写入，表中不产生重复记录。 | P0 | AI-API用例,开发必测,测试必测 | 流程验证 | 来源 CasePlan：CP-006；来源 Flow：CP-006；来源 Acceptance：AE-006；来源 Rule：DJG-R005；来源coverage：COV-EX-0006 |
