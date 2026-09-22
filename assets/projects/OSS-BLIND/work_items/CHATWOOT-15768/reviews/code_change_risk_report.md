# Chatwoot #15768 盲测 Oracle 对照报告

生成时间：2026-09-21
工作项：OSS-BLIND/CHATWOOT-15768
Oracle：[chatwoot/chatwoot#15768](https://github.com/chatwoot/chatwoot/pull/15768)，head `ce4033d3430977e1c0de712b8295a928d753de8d`

## 结论摘要

- 建议带风险开始测试。7 条盲测用例命中了 number 控件、0/false 保留、缺失属性、严格相等及 equal/not-equal 主链。
- 新增回归测试明确覆盖空数组、空对象与 `days_before=0`，当前用例未覆盖。
- 数量徽标一致性来自关联 issue 的 context-only 信息，PR 说明已明确 inbox-ID 问题另行修复；将其作为本 PR 主验收属于范围过伸。

## 代码与测试证据

| 位置 | Oracle 行为 | 盲测承接 | 结论 |
|---|---|---|---|
| `filterHelper.js` | number 自定义属性使用 number 输入 | CP-001 | 命中 |
| `filterQueryGenerator.js` | 仅 null/undefined/空字符串为空，保留 0/false | CP-002 | 命中 |
| `validations.js` 与测试 | 0/false 有效；null/undefined/空字符串/空数组/空对象无效 | CP-002 | 漏空数组与空对象，且未区分校验层 |
| `validations.spec.js` | `created_at + days_before + 0` 仍返回 1..998 边界错误 | 无 | 缺失 |
| `filterHelpers.js` 与测试 | 0/false/42 在 equal/not-equal 下保持严格类型；属性缺失不匹配 | CP-003、CP-004、CP-005 | 命中 |
| PR 范围说明 | inbox-ID 数量/列表问题由其他修复处理 | CP-006 | 范围过伸 |

## 问题清单

| 编号 | 严重级别 | 类型 | 问题 | 建议 |
|---|---|---|---|---|
| R1 | Medium-High | case_gap | 空数组与空对象仍应触发 `VALUE_REQUIRED`，但 CP-002 只覆盖 null/undefined/空字符串。 | 在 Gate/Acceptance/Case Plan 增加集合型空值矩阵。 |
| R2 | Medium-High | case_gap | falsy 修复不得让 `days_before=0` 绕过 1..998 边界，当前无对应计划。 | 增加日期运算符专属回归计划。 |
| R3 | Medium | invalid_case | CP-006 将 context-only 的数量徽标问题作为本 PR 主验收。 | 回到 Testability Gate 标记为 out-of-scope 或独立关联需求。 |

## AI 本地验证记录

| 验证ID | 级别 | 方法 | 实际结果 | 结论 |
|---|---|---|---|---|
| V-001 | L0 | 固化 8 个盲测产物 SHA-256 | 生成前资产已冻结，oracle 未参与生成 | confirmed_pass |
| V-002 | L1 | GitHub Files API 检查 8 个 changed files 与新增 Vitest 断言 | 主链命中，但确认 R1-R3 | confirmed_gap |
| V-003 | L2 | 上游 Vitest 执行 | 当前无 Chatwoot 源码 checkout，未在本地执行 | blocked |

## 人工验证重点

1. P0：number/checkbox 属性分别以 0、false 筛选，确认请求值与列表匹配结果均保留类型。
2. P0：null、undefined、空字符串、空数组、空对象均触发必填错误；`days_before=0` 仍触发 1..998 边界错误。
3. P1：加载历史字符串值筛选，确认不发生静默迁移，并记录用户可见行为。

## 测试产物影响建议

R1-R3 已写入 `design/design_feedback.json`；需要从 Gate/Case Plan 修正，不能直接追加或删除正式 testcase。

## 反馈实施复测

R1-R3 已全部从设计层应用：空数组、空对象、`days_before=0` 分别进入原子计划；数量徽标已移出本 PR 主验收。重生成后 9 条用例，oracle coverage/relevance 为 `1.0/1.0`。
