# Kubernetes #141831 盲测 Oracle 对照报告

生成时间：2026-09-22
Oracle：[kubernetes/kubernetes#141831](https://github.com/kubernetes/kubernetes/pull/141831)，head `42d2a3f19edd995a73f1bfb4a964f2dbc03358cf`

## 结论

13 条冻结用例覆盖 create/update、nil/empty/scoped selector、精确文本、非阻塞语义、effect 与 warnings-as-errors。没有范围过伸；实现按指针 nil 判断范围字段，空字符串值的语义仍需确认，形成 1 条 design feedback。

## 证据

| 位置 | Oracle 行为 | 盲测承接 | 结论 |
|---|---|---|---|
| `strategy.go` | create/update 共用空 selector Warning 逻辑 | CP-001、CP-002 | 命中 |
| `strategy.go` | 三个范围字段均为 nil 才返回固定 Warning | CP-003～CP-007 | 主链命中 |
| `strategy_test.go` | nil 无警告、空 selector 有警告、driver 非空无警告 | CP-001、CP-002、CP-004、CP-005 | 命中 |
| PR 现场验证与兼容说明 | 请求不阻塞、effect 无关、warnings-as-errors 仅改变客户端退出码 | CP-008～CP-013 | 命中 |
| `strategy.go` 指针判定 | 指向空字符串的范围字段也会抑制 Warning | 无专门计划 | 待确认，DF-001 |

## 验证层级

- L0：8 类资产 SHA-256 已冻结，Oracle 未参与生成。
- L1：检查固定 head 的 2 个 changed files、实现 diff、单元测试和 PR 现场验证说明。
- L2：未 checkout Kubernetes 上游源码，未在本地运行其测试。

本报告不修改 Case Plan 或正式 testcase。
