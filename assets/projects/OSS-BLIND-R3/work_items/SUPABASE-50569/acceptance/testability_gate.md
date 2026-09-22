# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | SUP-R001 | linkage | testable | generate_acceptance_example | confirmed | enableAuthRecoveryCodes 开启且账户具有可用恢复码时，MFA 验证页显示【使用恢复码验证】入口，并可进入独立恢复码认证页。 | 可分别验证条件满足时的入口显示和跨页面导航。 |
| TG-002 | SUP-R002 | product_behavior | testable | generate_acceptance_example | confirmed | 提交有效且未使用的恢复码后建立已完成 MFA 的登录会话。 | 可提交有效未使用恢复码并检查会话的 MFA 完成状态。 |
| TG-003 | SUP-R003 | product_behavior | testable | generate_acceptance_example | confirmed | 成功认证与恢复码消费必须形成一次有效结果：可用恢复码数量减少 1，已使用恢复码不能再次建立登录会话。 | 可分别核对可用码数量变化和同一码再次使用被拒绝。 |
| TG-004 | SUP-R004 | field_constraint | partially_testable | generate_acceptance_example | confirmed | 无效、空值或格式不正确的恢复码不得建立登录会话；具体格式规则和错误文案保持待确认。 | 三类输入不得建立会话的结果可验证；未确认的具体格式边界和错误文案不得写成强断言。 |
| TG-005 | SUP-R005 | linkage | testable | generate_acceptance_example | confirmed | enableAuthRecoveryCodes 关闭时，MFA 验证页不显示恢复码入口，直接访问恢复码认证 URL 重定向回 MFA 验证页。 | 可分别验证入口隐藏和直接 URL 访问的重定向目标。 |
| TG-006 | SUP-R006 | product_behavior | testable | generate_acceptance_example | confirmed | 普通 MFA 验证路径在 enableAuthRecoveryCodes 开启和关闭时均保持可用。 | 可在两种开关状态下分别执行普通 MFA 验证流程。 |
| TG-007 | SUP-R007 | risk_hardening | risk_only | risk_note_only | confirmed | 恢复码内容不得出现在 URL、日志或客户端错误上报中。 | 该规则来源范围为 context_only，只进入安全风险设计，不升级为本轮产品验收主用例。 |
| TG-008 | SUP-FR001 | linkage | testable | skip_case | confirmed | 条件满足时显示【使用恢复码验证】入口。 | 与 SUP-R001 的条件显示断言重复。 |
| TG-009 | SUP-FR002 | product_behavior | testable | skip_case | confirmed | 认证成功后用户进入已完成 MFA 的登录状态。 | 与 SUP-R002 的会话状态规则重复。 |
| TG-010 | SUP-FR003 | product_behavior | testable | skip_case | confirmed | 认证和消费的最终结果必须一致。 | 与 SUP-R003 的一次性消费结果重复。 |
| TG-011 | SUP-FR004 | field_constraint | partially_testable | skip_case | confirmed | 不得建立已完成 MFA 的登录会话；具体格式和错误文案待确认。 | 与 SUP-R004 的拒绝结果及待确认边界重复。 |
| TG-012 | SUP-FR005 | linkage | testable | skip_case | confirmed | 开关关闭时隐藏入口，并将恢复码认证页直接访问重定向至 MFA 验证页。 | 与 SUP-R005 的关闭状态路由保护规则重复。 |
| TG-013 | SUP-FR006 | product_behavior | testable | skip_case | confirmed | 恢复码功能不得破坏普通 MFA 验证路径。 | 与 SUP-R006 的普通 MFA 回归规则重复。 |
| TG-014 | SUP-FIELD-001 | field_constraint | testable | skip_case | confirmed | 有效且未使用时可完成 MFA；成功后从可用集合移除，已使用、无效或空值不得建立会话。 | 该字段汇总规则已分别由 SUP-R002、SUP-R003 和 SUP-R004 承接，避免生成复合重复验收。 |
| TG-015 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 恢复码是一次性安全凭证，成功认证与消费必须保持原子性，避免并发重复使用。 | 单次消费正式行为由 SUP-R003 覆盖，并发原子性作为风险加固项保留。 |
| TG-016 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | 页面路由守卫不能仅隐藏入口，还必须阻止直接 URL 绕过配置。 | 正式入口隐藏和重定向行为已由 SUP-R005 承接，此处只保留绕过风险。 |
| TG-017 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 检查恢复码可用性期间的加载或失败状态可能影响入口展示，但来源未定义具体交互。 | 加载和失败交互未定义，不生成具体展示或错误处理强断言。 |
| TG-018 | RISK-004 | risk_hardening | risk_only | risk_note_only | confirmed | 恢复码内容不得出现在日志、URL 或客户端错误上报中。 | 与 context_only 的 SUP-R007 相同，仅保留为风险项，不进入产品验收主链。 |
