# Django #21801 盲测 Oracle 对照报告

生成时间：2026-09-21
Oracle：[django/django#21801](https://github.com/django/django/pull/21801)，head `261b95cfe46cd8e6f2eb895acae6543772c05ce3`

## 结论

7 条冻结用例覆盖公开补丁的核心修复：移除字段普通索引时排除命名约束、删除普通索引并保留唯一约束。未发现范围误判或必须回灌设计层的新缺口。

## 证据

| 位置 | Oracle 行为 | 盲测承接 | 结论 |
|---|---|---|---|
| `django/db/backends/base/schema.py` | 删除候选同时排除 `Meta.constraints` 与 `Meta.indexes` 名称 | CP-001、CP-002 | 命中 |
| `tests/schema/tests.py` | 迁移前普通索引与命名唯一约束并存 | CP-003、CP-004 | 命中 |
| `tests/schema/tests.py` | alter 后普通索引消失、命名唯一约束保留 | CP-003、CP-004 | 命中 |
| 需求回归 | SQL、唯一性与既有数据不受损 | CP-005～CP-007 | 相关回归 |

## 验证层级

- L0：8 类资产 SHA-256 已冻结，Oracle 未参与生成。
- L1：检查固定 head 的 3 个 changed files 与新增回归测试，未发现设计缺口。
- L2：未 checkout Django 上游源码，未在本地运行其测试。

本报告不修改 Case Plan 或正式 testcase。
