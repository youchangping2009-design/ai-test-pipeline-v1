# Structured PRD

## project_info
```json
{"project_code":"OSS-BLIND-R3","project_name":"Supabase","business_line":"Dashboard MFA Authentication","prd_source":"inputs/requirement_summary.md","prd_version":"github-pr-50569"}
```

## requirement_info
```json
{
  "requirement_title":"MFA 恢复码登录",
  "requirement_background":"启用 MFA 且持有恢复码的用户需要在第二阶段认证中使用一次性恢复码完成登录，同时受功能开关和路由守卫保护。",
  "requirement_goal":"提供可控的恢复码 MFA 登录路径，成功认证时原子消费恢复码，并在功能关闭时同时隐藏入口和阻止直接 URL 访问。",
  "explicit_rules":[
    {"rule_id":"SUP-R001","rule_text":"enableAuthRecoveryCodes 开启且账户具有可用恢复码时，MFA 验证页显示【使用恢复码验证】入口，并可进入独立恢复码认证页。","rule_type":"navigation_rule","priority":"high","applies_to":"恢复码入口","source_scope":"primary_requirement","atomic_assertions":["满足开关和账户条件时显示【使用恢复码验证】入口。","点击入口进入独立恢复码认证页。"]},
    {"rule_id":"SUP-R002","rule_text":"提交有效且未使用的恢复码后建立已完成 MFA 的登录会话。","rule_type":"state_constraint","priority":"high","applies_to":"恢复码认证","source_scope":"primary_requirement"},
    {"rule_id":"SUP-R003","rule_text":"成功认证与恢复码消费必须形成一次有效结果：可用恢复码数量减少 1，已使用恢复码不能再次建立登录会话。","rule_type":"state_constraint","priority":"high","applies_to":"恢复码一次性消费","source_scope":"primary_requirement","atomic_assertions":["成功认证后可用恢复码数量减少 1。","已使用恢复码再次提交不能建立登录会话。"]},
    {"rule_id":"SUP-R004","rule_text":"无效、空值或格式不正确的恢复码不得建立登录会话；具体格式规则和错误文案保持待确认。","rule_type":"data_rule","priority":"high","applies_to":"无效恢复码","source_scope":"primary_requirement","atomic_assertions":["无效恢复码不建立登录会话。","空恢复码不建立登录会话。","格式不正确的恢复码不建立登录会话。"]},
    {"rule_id":"SUP-R005","rule_text":"enableAuthRecoveryCodes 关闭时，MFA 验证页不显示恢复码入口，直接访问恢复码认证 URL 重定向回 MFA 验证页。","rule_type":"fallback_constraint","priority":"high","applies_to":"功能关闭保护","source_scope":"primary_requirement","atomic_assertions":["功能关闭时恢复码入口不可见。","功能关闭时直接访问恢复码认证 URL 返回 MFA 验证页。"],"fidelity_points":[{"constraint_type":"field_constraint","value":"enableAuthRecoveryCodes","must_preserve":true,"forbidden_rewrites":["恢复码开关"]}]},
    {"rule_id":"SUP-R006","rule_text":"普通 MFA 验证路径在 enableAuthRecoveryCodes 开启和关闭时均保持可用。","rule_type":"fallback_constraint","priority":"high","applies_to":"既有 MFA 路径","source_scope":"primary_requirement"},
    {"rule_id":"SUP-R007","rule_text":"恢复码内容不得出现在 URL、日志或客户端错误上报中。","rule_type":"data_rule","priority":"medium","applies_to":"敏感凭证保护","source_scope":"context_only","atomic_assertions":["恢复码内容不出现在 URL。","恢复码内容不出现在日志。","恢复码内容不出现在客户端错误上报。"]}
  ],
  "scope":{"in_scope":["MFA 验证页恢复码入口","独立恢复码认证页","有效恢复码认证与一次性消费","无效或已使用恢复码拒绝","功能开关关闭时的入口隐藏与路由重定向","普通 MFA 路径回归"],"out_of_scope":["恢复码生成算法","MFA 初次绑定","普通密码重置","未定义的恢复码格式、大小写和空白规则","未定义的错误文案","无可用恢复码账户的未定义展示行为"]}
}
```

## pages
```json
[
  {"page_name":"MFA 验证页","page_desc":"第一阶段登录后的 MFA 验证入口。","sections":[{"section_name":"MFA 验证方式","section_type":"action_area","section_desc":"展示普通 MFA 验证与条件化恢复码入口。","module_name":"MFA 恢复码认证","feature_names":["恢复码登录与路由保护"],"section_rules":["满足开关和账户条件时显示恢复码入口","功能关闭时隐藏恢复码入口","普通 MFA 路径保持可用"],"field_refs":[],"field_rule_table_refs":[]}]},
  {"page_name":"恢复码认证页","page_desc":"提交一次性恢复码并完成 MFA 会话认证。","sections":[{"section_name":"恢复码提交","section_type":"other","section_desc":"校验并消费恢复码，成功后建立已完成 MFA 的会话。","module_name":"MFA 恢复码认证","feature_names":["恢复码登录与路由保护"],"section_rules":["有效未使用恢复码可完成认证","成功后恢复码不可再次使用","无效输入不建立会话","功能关闭时直接访问会被重定向"],"field_refs":["recovery_code"],"field_rule_table_refs":[]}]}
]
```

## modules
```json
[
  {"module_name":"MFA 恢复码认证","module_desc":"控制恢复码入口、认证、一次性消费和关闭状态下的路由保护。","features":[{"feature_name":"恢复码登录与路由保护","page_name":"恢复码认证页","section_name":"恢复码提交","feature_desc":"使用有效恢复码完成 MFA，并保证一次性消费及功能关闭保护。","actors":["启用 MFA 的用户","认证服务","页面路由守卫"],"entry_conditions":["账户已启用 MFA","用户完成第一阶段认证并进入 MFA 验证","可配置 enableAuthRecoveryCodes"],"rules":[
    {"rule_id":"SUP-FR001","name":"恢复码入口条件显示","rule_type":"conditional_visibility","target":"recovery_code_entry","visible_when":"enableAuthRecoveryCodes=true 且账户具有可用恢复码","rule_text":"条件满足时显示【使用恢复码验证】入口。"},
    {"rule_id":"SUP-FR002","name":"有效恢复码认证","rule_type":"state_constraint","field_name":"recovery_code","condition":"恢复码有效且未使用","value":"建立已完成 MFA 的登录会话","rule_text":"认证成功后用户进入已完成 MFA 的登录状态。"},
    {"rule_id":"SUP-FR003","name":"恢复码一次性消费","rule_type":"state_constraint","field_name":"recovery_code","condition":"恢复码认证成功","value":"从可用集合移除且不可再次使用","rule_text":"认证和消费的最终结果必须一致。"},
    {"rule_id":"SUP-FR004","name":"无效输入拒绝","rule_type":"value_constraint","field_name":"recovery_code","condition":"无效、空值、格式不正确或已使用","rule_text":"不得建立已完成 MFA 的登录会话；具体格式和错误文案待确认。"},
    {"rule_id":"SUP-FR005","name":"功能关闭路由保护","rule_type":"conditional_visibility","target":"recovery_code_route","visible_when":"enableAuthRecoveryCodes=true","rule_text":"开关关闭时隐藏入口，并将恢复码认证页直接访问重定向至 MFA 验证页。"},
    {"rule_id":"SUP-FR006","name":"普通 MFA 回归","rule_type":"state_constraint","target":"standard_mfa_flow","condition":"enableAuthRecoveryCodes 为 true 或 false","value":"保持可用","rule_text":"恢复码功能不得破坏普通 MFA 验证路径。"}
  ],"fields":[{"name":"recovery_code","display_name":"恢复码","type":"credential_input","data_type":"string","required":false,"editable":true,"description":"一次性 MFA 恢复凭证；格式、大小写和空白处理规则待确认。"}],"field_definitions":[],"field_rules":[{"rule_id":"SUP-FIELD-001","field_name":"recovery_code","display_name":"恢复码","rule_text":"有效且未使用时可完成 MFA；成功后从可用集合移除，已使用、无效或空值不得建立会话。","rule_type":"status_constraint","expected_effects":["成功时建立已完成 MFA 的会话并消费一次","失败时不建立会话"],"must_cover":true}],"field_rule_tables":[],"visible_elements":["【使用恢复码验证】入口","恢复码输入项","普通 MFA 验证入口"],"interactive_entries":["进入恢复码认证页","提交恢复码","执行普通 MFA 验证"],"abnormal_scenarios":["无效恢复码","空恢复码","格式不正确的恢复码","已使用恢复码再次提交","同一恢复码并发提交","功能关闭时直接访问恢复码 URL"],"boundary_scenarios":["恢复码格式、大小写和空白规则待确认","无可用恢复码时入口行为待确认","加载或查询失败时入口行为待确认","服务异常错误文案待确认"],"dependencies":["enableAuthRecoveryCodes","MFA challenge","恢复码可用集合","认证会话"]}]}
]
```

## flows
```json
[
  {"flow_id":"SUP-FLOW-001","flow_name":"使用恢复码完成 MFA 登录","flow_type":"main_flow","business_goal":"在功能开启时使用一次性恢复码完成 MFA，并确保认证与消费状态一致。","trigger":"用户在 MFA 验证页选择【使用恢复码验证】","preconditions":["enableAuthRecoveryCodes=true","账户已启用 MFA 并具有可用恢复码","用户已完成第一阶段认证"],"steps":[
    {"step_no":1,"step_name":"进入恢复码认证页","step_type":"operation","module_name":"MFA 恢复码认证","feature_name":"恢复码登录与路由保护","actor":"用户","action":"从 MFA 验证页进入恢复码认证页","expected_result":"满足条件时页面可访问；功能关闭时返回 MFA 验证页","checkpoints":["入口和直接 URL 均受开关保护"],"rule_references":["SUP-R001","SUP-R005"],"is_key_checkpoint":true},
    {"step_no":2,"step_name":"提交恢复码","step_type":"data_validation","module_name":"MFA 恢复码认证","feature_name":"恢复码登录与路由保护","actor":"用户","action":"提交恢复码完成第二阶段认证","input_data":["recovery_code"],"expected_result":"仅有效且未使用的恢复码建立已完成 MFA 的会话","checkpoints":["无效、空值、格式不正确或已使用值不建立会话"],"rule_references":["SUP-R002","SUP-R004"],"is_key_checkpoint":true},
    {"step_no":3,"step_name":"消费恢复码并建立会话","step_type":"state_change","module_name":"MFA 恢复码认证","feature_name":"恢复码登录与路由保护","actor":"认证服务","action":"提交认证成功结果并从可用集合移除已使用恢复码","expected_result":"会话完成 MFA，恢复码数量减少 1 且该码不能再次登录","state_transition":{"from":"待完成 MFA 且恢复码可用","to":"已完成 MFA 且该恢复码已消费"},"checkpoints":["认证状态与恢复码消费状态一致"],"rule_references":["SUP-R003"],"is_key_checkpoint":true}
  ],"postconditions":["用户持有已完成 MFA 的登录会话","本次恢复码不可再次使用"],"success_criteria":["入口与路由正确受开关保护","有效恢复码认证成功且只消费一次","失败输入不建立会话","普通 MFA 路径不回退"],"related_modules":["MFA 恢复码认证"],"priority":"P0","tags":["mfa","recovery-code","one-time-credential"]}
]
```
