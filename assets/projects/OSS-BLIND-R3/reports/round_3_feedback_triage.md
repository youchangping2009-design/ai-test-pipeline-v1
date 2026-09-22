# OSS-BLIND-R3 Oracle Feedback Triage

日期：2026-09-21

## 结论

Oracle Review 的 9 条反馈已完成来源分流，但尚未执行设计层重生成：

- 1 条可进入正式设计主链：Celery 同步载荷契约。
- 7 条仅来自实现或代码测试，先作为 `oracle_only` 风险进入 Testability Gate，不自动生成正式业务用例。
- 1 条为实现差异：Supabase 功能关闭时，批准需求要求返回 MFA 验证页，代码当前按 `getReturnToPath()` 跳转；保留原测试预期。

## 分流明细

| 样本 | Feedback | 处置 | 理由 |
|---|---|---|---|
| Celery | DF-001 | 正式设计补强 | 已批准摘要明确“外部撤销状态只以任务 ID 参与合并”，可补载荷与顺序断言 |
| Temporal | DF-001～DF-004 | Oracle-only 风险 | 额外响应字段、冲突策略、动态开关和内部错误路径未进入批准需求，不得自动升级主验收 |
| Supabase | DF-001、DF-002、DF-004 | Oracle-only 风险 | returnTo、具体失败 UI 和异步交互来自实现，批准需求没有定义 |
| Supabase | DF-003 | 实现差异 | 批准摘要明确固定返回 MFA 验证页，不能按代码现状改写 CP-010 |

## 对流水线的含义

当前 Oracle scorer 把业务需求断言、实现级行为与运维风险等权计入单一 coverage，导致 Temporal/Supabase 的低分不能直接解释为需求用例质量低。后续需要给 Oracle assertion 增加来源范围/测试层级，并分别报告 requirement coverage 与 implementation-risk coverage。

## 下一阶段

从 Testability Gate、Acceptance Examples 与 Case Plan 应用已接受反馈：只让 Celery 的 1 条正式设计补强进入主链，7 条实现级项保持 risk/audit，Supabase 实现差异只保留评审结论。随后再从 Case Plan 重生成并复测，不直接编辑 `testcases_main.md`。
