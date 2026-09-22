# OSS-BLIND-R3 Oracle Review

日期：2026-09-21

## 总结论

四份冻结资产均覆盖公开 PR 的核心需求方向，37 条正式 testcase 没有范围过伸，相关率均为 `1.0`。Oracle 静态对照确认 9 条待处理设计反馈：Celery 1 条、Temporal 4 条、Supabase 4 条；Django 无新增缺口。

| 样本 | 固定 head | 冻结用例 | Oracle 覆盖率 | 用例相关率 | 开放反馈 |
|---|---|---:|---:|---:|---:|
| Django #21801 | `261b95c` | 7 | 1.0 | 1.0 | 0 |
| Celery #10668 | `c4cde119` | 11 | 0.9444 | 1.0 | 1 |
| Temporal #11968 | `3766f2e3` | 8 | 0.65 | 1.0 | 4 |
| Supabase #50569 | `3e3d1348` | 11 | 0.6538 | 1.0 | 4 |

四个样本合计 38 个 Oracle assertion，按 `covered=1`、`partial=0.5`、`missing=0` 加权，兼容总体微平均覆盖率为 `0.7763`（29.5/38）；37 条 testcase 全部属于 direct match 或 requirement regression。

分层后，Django、Temporal、Supabase 的 requirement coverage 均为 `1.0`，Celery 为 `0.9444`；Temporal implementation/risk 分别为 `0.25/0.0`，Supabase implementation 为 `0.3571`。总体分保留兼容，不再用于单独判断需求用例质量。

## 主要发现

1. Django 的结构约束保留场景最完整，需求层用例已经覆盖代码测试的核心回归。
2. Celery 的行为覆盖充分，但缺少跨版本协议层的“只传 ID、最旧优先”载荷断言。
3. Temporal 的需求主链覆盖稳定，薄弱点集中在 API 响应字段、冲突策略顺序、动态开关和错误传播。
4. Supabase 的业务结果覆盖较好，但 UI 实现级导航、失败反馈、加载/重复提交状态没有从需求摘要自然生成。
5. Supabase CP-010 与实现的 `getReturnToPath` 存在潜在契约冲突，必须先确认需求，不能直接按实现改用例。

## 边界

- Oracle 解封前已冻结每个工作项 8 类主资产及 SHA-256。
- Oracle 只来自四个公开 PR 的固定 head、changed-files patch 和其中已有测试。
- 本阶段没有修改 Coverage、Gate、Acceptance、Case Plan 或正式 testcase；9 条结论仅写入 design feedback。
- 未 checkout 四个上游业务仓库，未执行上游测试；结论是 L0/L1 静态映证，不是运行时通过证明。

## 下一阶段建议

按“需求缺口、实现级风险、待确认冲突”三类处理 9 条反馈：先在 Testability Gate/Acceptance/Case Plan 应用可通用化项，再从设计层重生成并与冻结基线复测。Supabase 返回目标未确认前保持 `needs_confirmation`。
