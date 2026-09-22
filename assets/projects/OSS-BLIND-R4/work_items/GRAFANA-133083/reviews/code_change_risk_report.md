# Grafana #133083 盲测 Oracle 对照报告

生成时间：2026-09-22
Oracle：[grafana/grafana#133083](https://github.com/grafana/grafana/pull/133083)，head `9aeaf1e74014e8db92593bfce51e7cf6dd0be65c`

## 结论

14 条冻结用例均与需求相关，显式 Serializer 选择、默认回退、GVK 保留及 watch context 主链已覆盖。差距集中在非 watch context、错误传播、JSON 异常输入、持久化版本策略和并发安全，共形成 4 条 design feedback。

## 证据

| 位置 | Oracle 行为 | 盲测承接 | 结论 |
|---|---|---|---|
| `pkg/storage/unified/apistore/store.go` | 显式 Serializer 覆盖默认 codec，读写/list/watch 共用 | CP-001～CP-009 | 命中 |
| `pkg/storage/unified/apistore/serializer_test.go` | JSON typed/unstructured/nil target 及错误传播 | CP-010、CP-011 | 部分命中，DF-001 |
| `pkg/storage/unified/apistore/stream_test.go` | 当前/历史 watch 对象沿用请求 context 并观察取消 | CP-012～CP-014 | 命中 |
| `pkg/storage/unified/apistore/serializer_test.go` | 一般 encode/decode 也接收请求 context | CP-001～CP-003 | 部分命中，DF-002 |
| `pkg/storage/unified/apistore/prepare_test.go` | 按实际持久化版本执行 cap、拒绝跨组、删除路径豁免 | 无正式计划 | 缺失，DF-003 |
| `pkg/storage/unified/apistore/serializer.go` | Serializer 必须可并发安全使用 | 无正式计划 | 风险，DF-004 |

## 验证层级

- L0：8 类资产 SHA-256 已冻结，Oracle 未参与生成。
- L1：检查固定 head 的 10 个 changed files、实现 diff 与新增/调整测试。
- L2：未 checkout Grafana 上游源码，未在本地运行其测试。

本报告不修改 Case Plan 或正式 testcase。

## 反馈回灌后状态

- DF-002 已通过正式设计链补充 CP-015～CP-017，对应写入、单条读取和列表读取的请求 context 传播。
- 需求层 Oracle coverage 已由 `0.8333` 提升至 `1.0`；实现错误、版本策略和并发风险继续保留为 Gate 风险项，不升级为需求用例。
- 原始冻结结果仍保留在上文，本节仅记录可审计的反馈应用结果。
