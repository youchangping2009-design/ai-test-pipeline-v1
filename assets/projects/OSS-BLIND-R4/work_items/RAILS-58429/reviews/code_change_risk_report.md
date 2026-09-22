# Rails #58429 盲测 Oracle 对照报告

生成时间：2026-09-22
Oracle：[rails/rails#58429](https://github.com/rails/rails/pull/58429)，head `edd687c7a77f31f1de6ae646afe4a32d76b6bc9d`

## 结论

10 条冻结用例覆盖无 block 返回值、多 logger 标签广播、block 单次执行、异常清理和混合 logger 兼容。没有范围过伸；实现还暴露“零 tagging logger 时仍 yield 一次”的能力边界，形成 1 条风险反馈。

## 证据

| 位置 | Oracle 行为 | 盲测承接 | 结论 |
|---|---|---|---|
| `broadcast_logger.rb` / 新增测试 | 无 block 返回 BroadcastLogger 且两个目标都带标签 | CP-001、CP-002 | 命中 |
| `broadcast_logger.rb` / 新增测试 | block 只 yield 一次且所有 tagging logger 同时带标签 | CP-004、CP-005 | 命中 |
| 新增测试 | 异常后两个 logger 均清除临时标签 | CP-007、CP-008 | 命中 |
| 新增测试 | 非 tagging logger 被保留并继续收到消息 | CP-003、CP-009 | 命中 |
| `_tagged` 递归终止分支 | 零 tagging logger 时直接 yield self | 无专门计划 | 风险，DF-001 |

## 验证层级

- L0：8 类资产 SHA-256 已冻结，Oracle 未参与生成。
- L1：检查固定 head 的 3 个 changed files、实现 diff 与 4 条新增回归测试。
- L2：未 checkout Rails 上游源码，未在本地运行其测试。

本报告不修改 Case Plan 或正式 testcase。
