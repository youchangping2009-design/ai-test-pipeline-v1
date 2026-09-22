# Review Record

## 评审结论

- 结论：通过但需设计层补强；建议开始测试
- 评审方式：冻结资产后的公开 PR diff / 新增测试静态 oracle 对照
- 评审时间：2026-09-21
- 核心覆盖：前缀拒绝、指定 driver、失败关闭、token 兼容及错误目标不建连均已覆盖。
- Oracle 差距：精确错误文案、`UID/PWD` 属性映射未明确；CP-004 原子性不足。
- 详细报告：`reviews/code_change_risk_report.md`

## 问题清单

| 序号 | 类型 | 问题描述 | 严重级别 | 建议修改 |
|---|---|---|---|---|
| 1 | Acceptance | 未锁定新增 JDBC URL 错误文案 | P1 | 反馈到 Acceptance/Case Plan |
| 2 | Case Plan | 未明确 `UID=token` 与 `PWD` 映射 | P1 | 增加属性捕获断言 |
| 3 | Case Plan | CP-004 合并多个失败分支 | P2 | 拆为原子计划 |

## 设计反馈回灌结果

- DF-001 至 DF-003 均已标记为 `applied`。
- 非法协议错误文案已精确化；JDBC 属性明确为 `UID=token`、`PWD=<当前 token>`。
- driver 拒绝 URL 与返回空连接已拆为 CP-004、CP-007 两条原子计划。
- 重生成后 7 条正式用例，weak/generalized/semantic mismatch/duplicate 均为 0，oracle coverage/relevance 均为 `1.0`。
