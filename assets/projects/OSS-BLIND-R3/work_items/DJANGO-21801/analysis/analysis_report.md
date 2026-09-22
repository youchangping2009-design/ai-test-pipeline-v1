# Analysis Report

## Requirement Summary
- 标题：`DJANGO-21801 删除 db_index 时保留唯一约束需求整理`
- 摘要：在 MySQL 上，当字段同时存在 `db_index=True` 生成的普通索引和 `Meta.constraints` 中同列的命名 `UniqueConstraint` 时，后续只移除 `db_index=True` 不得删除未变化的唯一约束。迁移后普通索引应被移除，命名唯一约束及其数据库唯一索引必须继续存在并强制唯一性。
- 主要页面数：0
- 主要展示面数：0

## Reasoning Snapshot
- explicit_rules：14
- implicit_rules：0
- field_constraints：0
- data_source_rules：0
- business_risks：3
- edge_cases：1
- ambiguities：3
- recommended_test_dimensions：5
- coverage_candidates：14

## Top Explicit Rules
- `ER-001` 在 MySQL 上，当字段同时存在 `db_index=True` 生成的普通索引和 `Meta.constraints` 中同列的命名 `UniqueConstraint` 时，后续只移除 `db_index=True` 不得删除未变化的唯一约束。迁移后普通索引应被移除，命名唯一约束及其数据库唯一索引必须继续存在并强制唯一性。
- `ER-002` 迁移差异只包含从字段移除 `db_index=True`。
- `ER-003` 定位待删除普通索引时，必须排除 `Meta.constraints` 中仍存在的命名约束。
- `ER-004` 执行迁移后，不再保留字段普通非唯一索引。
- `ER-005` 执行迁移后，命名唯一约束仍存在，数据库继续拒绝重复值。
- `ER-006` 初始状态可明确识别同列的普通索引和命名唯一索引。
- `ER-007` 生成的迁移 SQL 只删除普通索引，不包含删除命名唯一约束的语句。
- `ER-008` 应用迁移后命名唯一约束仍可被数据库 introspection 识别。

## Top Implicit Rules

## Key Risks
- `RISK-001` [medium] MySQL 将唯一约束表现为唯一索引，可能导致普通索引查找误命中约束索引。
- `RISK-002` [medium] 不同 Django 维护版本的迁移行为需要分别确认；来源只报告 6.1 和 4.2。
- `RISK-003` [medium] 迁移 SQL 正确不等于最终数据库状态正确，需要同时验证 schema 和重复写入行为。

## Ambiguities
- `AMB-001` PostgreSQL、SQLite、Oracle 等后端是否需要明确的“不回退”验证范围？
- `AMB-002` 复合字段、条件或表达式 `UniqueConstraint` 是否属于本次适用范围？
- `AMB-003` 迁移回滚时普通索引的恢复行为是否需要纳入正式验收？

## Recommended Test Dimensions
- `TD-001` 显式规则逐条验证：需求摘要已给出可追溯规则，后续设计应保持单规则单断言并验证成功与失败结果。
- `TD-002` 异常与失败处理：需求包含明确拒绝或失败语义，需要验证失败状态、错误反馈及副作用隔离。
- `TD-003` 数据一致性与状态保留：需求涉及关系或状态保留，应核对操作前后数据集合而非只看接口成功。
- `TD-004` 风险与非功能约束：需求摘要已明确兼容性、性能或一致性风险，需与产品验收规则分层承接。
- `TD-005` 未决项追踪：摘要存在尚未确认的输入或验收口径，后续不得将其自动升级为强制规则。
