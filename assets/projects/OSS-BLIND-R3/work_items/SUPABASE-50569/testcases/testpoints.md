# Testpoints View

- Project: `OSS-BLIND-R3`
- Work Item: `SUPABASE-50569`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | ui_display | 满足开关与账户条件时显示恢复码入口 | 页面显示【使用恢复码验证】入口。 | P0 | CP-001 | True |
| TP-002 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | cross_surface_linkage | 从[MFA 验证页]进入独立[恢复码认证页] | 导航完成后，当前页面为[恢复码认证页]。 | P0 | CP-002 | True |
| TP-003 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | cross_surface_linkage | 有效未使用恢复码建立 MFA 完成会话 | 系统建立登录会话；该登录会话的 MFA 状态为已完成。 | P0 | CP-003 | True |
| TP-004 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | data_persistence | 恢复码认证成功后可用数量减少一条 | 认证后的可用恢复码数量比认证前减少 1。 | P0 | CP-004 | True |
| TP-005 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | field_rule | 拒绝已使用恢复码再次建立登录会话 | 系统不建立新的登录会话；该恢复码仍处于不可用状态。 | P0 | CP-005 | True |
| TP-006 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | field_rule | 拒绝无效恢复码建立登录会话 | 系统不建立登录会话。 | P0 | CP-006 | True |
| TP-007 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | field_rule | 空恢复码不建立登录会话 | 系统不建立登录会话；不对未定义的错误文案作强断言。 | P0 | CP-007 | True |
| TP-008 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | field_rule | 已知格式不正确的恢复码不建立登录会话 | 系统不建立登录会话；不对未定义的格式边界或错误文案作强断言。 | P0 | CP-008 | True |
| TP-009 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | ui_display | 功能关闭时隐藏恢复码入口 | 页面不显示【使用恢复码验证】入口。 | P0 | CP-009 | True |
| TP-010 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | cross_surface_linkage | 功能关闭时直接访问[恢复码认证页]返回[MFA 验证页] | 重定向完成后，当前页面为[MFA 验证页]；用户不能通过直接 URL 停留在[恢复码认证页]。 | P0 | CP-010 | True |
| TP-011 | 恢复码认证页 | 恢复码提交 | MFA 恢复码认证 | 恢复码登录与路由保护 | cross_surface_linkage | 恢复码开关两种状态下普通 MFA 路径均可用 | 两种开关状态下普通 MFA 验证均完成并建立已完成 MFA 的登录会话；恢复码功能开关不改变普通 MFA 路径的既有结果。 | P0 | CP-011 | True |
