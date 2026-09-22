# Temporal #11968 盲测 Oracle 对照报告

生成时间：2026-09-21
Oracle：[temporalio/temporal#11968](https://github.com/temporalio/temporal/pull/11968)，head `3766f2e33362d34d958bd5d4a37a1823273a01a6`

## 结论

8 条冻结用例命中关闭后 request ID 去重、无新 run、无重复 signal、指标与不同 ID 分支；实现级响应字段、冲突策略前置顺序、动态开关和错误传播尚未进入设计层。

## 证据与缺口

| 编号 | Oracle 行为 | 盲测状态 | 反馈 |
|---|---|---|---|
| R1 | 响应含首次 `RunId`、`FirstExecutionRunId` 且 `Started=true` | 部分 | DF-001 |
| R2 | 重复 ID 在 `TERMINATE_EXISTING` 前去重，不终止当前 run | 缺失 | DF-002 |
| R3 | 动态开关关闭时保留旧行为且不记去重指标 | 缺失 | DF-003 |
| R4 | 首次 run 查询/并发创建错误不被吞掉且不误记指标 | 缺失 | DF-004 |

## 验证层级

- L0：冻结 8 类资产哈希。
- L1：检查固定 head 的 8 个 changed files 与新增/修改测试。
- L2：未 checkout Temporal 上游源码，未运行 Go 测试。

R3、R4 先作为 risk_note，不自动升级为正式业务用例。
