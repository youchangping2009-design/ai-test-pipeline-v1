# Testpoints View

- Project: `OSS-BLIND-R3`
- Work Item: `DJANGO-21801`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | Django Migration 执行入口 | 索引变更与数据库状态 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | data_persistence | 模型变更仅移除字段普通索引声明 | 模型变更仅包含关闭“字段普通索引设置”；命名 `UniqueConstraint` 的定义保持不变。 | P0 | CP-001 | True |
| TP-002 | Django Migration 执行入口 | 索引变更与数据库状态 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | backend_job | 迁移删除目标排除命名唯一约束 | 待删除目标是普通非唯一索引；仍存在于 `Meta.constraints` 的命名唯一约束不属于删除目标。 | P0 | CP-002 | True |
| TP-003 | Django Migration 执行入口 | 索引变更与数据库状态 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | data_persistence | 迁移后普通非唯一索引被删除 | 数据库 introspection 结果中目标字段的普通非唯一索引不存在。 | P0 | CP-003 | True |
| TP-004 | Django Migration 执行入口 | 索引变更与数据库状态 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | data_persistence | 迁移后命名唯一约束保持存在 | 命名唯一约束仍存在；该约束对应的数据库唯一索引仍存在。 | P0 | CP-004 | True |
| TP-005 | Django Migration 执行入口 | 索引变更与数据库状态 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | backend_job | 迁移 SQL 只删除普通非唯一索引 | SQL 包含删除普通非唯一索引的语句；SQL 不包含删除命名唯一约束的语句。 | P0 | CP-005 | True |
| TP-006 | Django Migration 执行入口 | 索引变更与数据库状态 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | cross_surface_linkage | 迁移后重复写入仍受唯一性保护 | 迁移后命名唯一约束保持生效；数据库拒绝重复值写入，表中不产生重复记录。 | P0 | CP-006 | True |
| TP-007 | Django Migration 执行入口 | 索引变更与数据库状态 | MySQL 索引迁移 | 删除普通索引并保留唯一约束 | data_persistence | 迁移前已有合法数据保持不变 | 迁移后的记录数量与迁移前一致；各记录的主键和业务字段值与迁移前一致。 | P1 | CP-007 | True |
