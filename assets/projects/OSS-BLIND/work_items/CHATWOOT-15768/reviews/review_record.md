# Review Record

## 评审结论

- 结论：存在范围与边界缺口；建议带风险开始测试
- 评审方式：冻结资产后的公开 PR diff / 新增测试静态 oracle 对照
- 评审时间：2026-09-21
- 核心覆盖：number 输入、0/false 保留、缺失属性、严格相等与等于/不等于均已覆盖。
- Oracle 差距：空数组/空对象、`days_before=0` 未覆盖；数量徽标用例超出本 PR 直接范围。
- 详细报告：`reviews/code_change_risk_report.md`

## 问题清单

| 序号 | 类型 | 问题描述 | 严重级别 | 建议修改 |
|---|---|---|---|---|
| 1 | Case Plan | 空数组与空对象未进入空值矩阵 | P1 | 补充集合型空值规则 |
| 2 | Testability Gate | `days_before=0` 回归边界缺失 | P1 | 新增独立边界计划 |
| 3 | Scope | 数量徽标属于关联问题背景 | P1 | 标记 out_of_scope 或迁移独立工作项 |

## 设计反馈回灌结果

- DF-001 至 DF-003 均已标记为 `applied`。
- 空数组、空对象和 `days_before=0` 已分别形成原子规则、Acceptance 和 Case Plan。
- 数量徽标规则已标记为 `context_only`，Gate 为 `out_of_scope`，原 CP-006 与正式用例已移除。
- 重生成后 9 条正式用例，weak/generalized/semantic mismatch/duplicate 均为 0，oracle coverage/relevance 均为 `1.0`。
