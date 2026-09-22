# Celery #10668 盲测 Oracle 对照报告

生成时间：2026-09-21
Oracle：[celery/celery#10668](https://github.com/celery/celery/pull/10668)，head `c4cde1198a12f6399b2e486c596f15a15afbc8ae`

## 结论

11 条冻结用例覆盖本机重新计时、容量/过期、三条同步入口、混合版本及 `LimitedSet` 边界。唯一缺口是没有直接锁定跨 Worker 载荷“只含任务 ID、最旧优先”的兼容契约。

## 证据

| 位置 | Oracle 行为 | 盲测承接 | 结论 |
|---|---|---|---|
| `celery/worker/state.py` | 外部集合先转 ID 列表，再以本机时间 merge | CP-001、CP-002 | 命中 |
| hello/mingle/statedb | 三条入口统一走本机重新计时 | CP-005～CP-007 | 命中 |
| `celery/utils/collections.py` | 序列号打破同时间戳比较，显式 `now=0` 保留 | CP-009～CP-011 | 命中 |
| 新增 smoke/unit tests | 同步响应只传 ID 且按最旧优先 | CP-005、CP-006、CP-008 | 部分命中 |

## 风险

- R1（Medium）：未直接断言同步载荷不包含远端时间戳以及顺序契约，已记录 DF-001。
- L2 未执行：当前未 checkout Celery 上游源码。

反馈只写入 `design/design_feedback.json`，不直接覆盖 testcase。
