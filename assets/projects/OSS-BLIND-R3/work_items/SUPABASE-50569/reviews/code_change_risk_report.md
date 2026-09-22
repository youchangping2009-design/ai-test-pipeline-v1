# Supabase #50569 盲测 Oracle 对照报告

生成时间：2026-09-21
Oracle：[supabase/supabase#50569](https://github.com/supabase/supabase/pull/50569)，head `3e3d1348dd7ddc901c7425168cdf2ccbf5f9dbce`

## 结论

11 条冻结用例覆盖入口条件、恢复码成功/失败/一次性消费、功能开关与普通 MFA 回归。代码实现暴露了导航状态、失败反馈、直接访问返回目标和异步交互四类设计缺口；该 PR 没有新增测试文件，因此本轮只有 L1 静态映证。

## 证据与缺口

| 编号 | Oracle 行为 | 盲测状态 | 反馈 |
|---|---|---|---|
| R1 | 入口保留查询参数，成功后返回原 `returnTo` | 部分 | DF-001 |
| R2 | 空值/验证失败有可观察反馈且可重试 | 部分 | DF-002 |
| R3 | 功能关闭或未登记时按 `getReturnToPath` 跳转 | 与冻结 CP-010 的固定 MFA 目标可能冲突 | DF-003 |
| R4 | 加载/失败状态、防重复提交、粘贴与显隐交互 | 缺失 | DF-004 |

## 验证层级

- L0：冻结 8 类资产哈希。
- L1：检查固定 head 的 9 个 changed files；无新增自动化测试文件。
- L2：未 checkout Supabase 上游源码，未运行前端测试。

DF-003 必须先确认产品契约；不得以当前实现直接覆盖正式 testcase。
