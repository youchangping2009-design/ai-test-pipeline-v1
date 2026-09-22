# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | 满足开关与账户条件时显示恢复码入口 | `enableAuthRecoveryCodes=true`，账户已启用 MFA 且具有可用恢复码。 | 用户进入[MFA 验证页]。 | 页面显示【使用恢复码验证】入口。 | 认证前端展示层 | display_only | confirmed |  |
| AE-002 | TG-001 | 从[MFA 验证页]进入独立[恢复码认证页] | [MFA 验证页]已显示【使用恢复码验证】入口。 | 用户点击【使用恢复码验证】。 | 导航完成后，当前页面为[恢复码认证页]。 | 认证前端路由层 | linkage | confirmed |  |
| AE-003 | TG-002 | 有效未使用恢复码建立 MFA 完成会话 | 账户已启用 MFA，且存在一个有效、未使用的恢复码。 | 用户在[恢复码认证页]提交该恢复码。 | 系统建立登录会话。<br>该登录会话的 MFA 状态为已完成。 | 认证前端与服务端 | business_behavior | confirmed |  |
| AE-004 | TG-003 | 恢复码认证成功后可用数量减少一条 | 账户存在多个可用恢复码，并记录认证前的可用数量。 | 用户使用其中一个有效恢复码成功完成认证。 | 认证后的可用恢复码数量比认证前减少 1。 | 认证服务与数据层 | business_behavior | confirmed |  |
| AE-005 | TG-003 | 拒绝已使用恢复码再次建立登录会话 | 一个恢复码已经成功认证并被消费。 | 再次提交同一个恢复码。 | 系统不建立新的登录会话。<br>该恢复码仍处于不可用状态。 | 认证服务与数据层 | business_behavior | confirmed |  |
| AE-006 | TG-004 | 拒绝无效恢复码建立登录会话 | 账户已进入恢复码认证流程，并准备一个不属于该账户可用集合的恢复码。 | 用户提交该无效恢复码。 | 系统不建立登录会话。 | 认证服务端 | business_behavior | confirmed |  |
| AE-007 | TG-004 | 空恢复码不建立登录会话 | 用户位于[恢复码认证页]，且“恢复码”输入为空。 | 用户提交恢复码认证。 | 系统不建立登录会话。<br>不对未定义的错误文案作强断言。 | 认证前端与服务端 | business_behavior | confirmed |  |
| AE-008 | TG-004 | 已知格式不正确的恢复码不建立登录会话 | 按当前系统既有判定准备一个格式不正确的恢复码；具体格式边界不由本需求定义。 | 用户提交该恢复码。 | 系统不建立登录会话。<br>不对未定义的格式边界或错误文案作强断言。 | 认证服务端 | business_behavior | confirmed |  |
| AE-009 | TG-005 | 功能关闭时隐藏恢复码入口 | `enableAuthRecoveryCodes=false`，用户进入[MFA 验证页]。 | 页面完成认证方式展示。 | 页面不显示【使用恢复码验证】入口。 | 认证前端展示层 | display_only | confirmed |  |
| AE-010 | TG-005 | 功能关闭时直接访问[恢复码认证页]返回[MFA 验证页] | `enableAuthRecoveryCodes=false`，用户已处于需要完成 MFA 的认证阶段。 | 用户直接访问恢复码认证 URL。 | 重定向完成后，当前页面为[MFA 验证页]。<br>用户不能通过直接 URL 停留在[恢复码认证页]。 | 认证前端路由层 | linkage | confirmed |  |
| AE-011 | TG-006 | 恢复码开关两种状态下普通 MFA 路径均可用 | 分别设置 `enableAuthRecoveryCodes=true` 和 `enableAuthRecoveryCodes=false`，账户可使用普通 MFA 验证方式。 | 用户在两种开关状态下分别完成普通 MFA 验证。 | 两种开关状态下普通 MFA 验证均完成并建立已完成 MFA 的登录会话。<br>恢复码功能开关不改变普通 MFA 路径的既有结果。 | 认证前端与服务端 | business_behavior | confirmed |  |
