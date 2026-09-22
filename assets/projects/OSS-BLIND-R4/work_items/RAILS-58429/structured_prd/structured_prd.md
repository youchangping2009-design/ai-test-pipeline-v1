# Structured PRD

## project_info
```json
{"project_code":"OSS-BLIND-R4","project_name":"Ruby on Rails","business_line":"Logging","prd_source":"inputs/requirement_summary.md","prd_version":"github-pr-58429"}
```

## requirement_info
```json
{
  "requirement_title":"修复 BroadcastLogger 多目标 tagged 语义",
  "requirement_background":"BroadcastLogger 包含多个支持 tagged 的 logger 时，无 block 调用可能返回 Array，有 block 调用可能重复执行用户 block，并存在异常后标签泄漏风险。",
  "requirement_goal":"让 `BroadcastLogger#tagged` 在多个及混合能力广播目标下维持可链式调用、单次 block 执行、完整广播和可靠清理。",
  "explicit_rules":[
    {"rule_id":"RAI-R001","rule_text":"无 block 调用 `BroadcastLogger#tagged` 必须返回可继续调用日志方法的 BroadcastLogger，而不是 Array。","rule_type":"interaction_rule","priority":"high","applies_to":"无 block 标签广播","source_scope":"primary_requirement"},
    {"rule_id":"RAI-R002","rule_text":"无 block 返回对象中，所有支持 tagged 的 logger 应应用指定标签。","rule_type":"state_constraint","priority":"high","applies_to":"无 block 标签广播","source_scope":"primary_requirement"},
    {"rule_id":"RAI-R003","rule_text":"不支持 tagged 的广播目标仍必须保留并收到后续日志消息。","rule_type":"fallback_constraint","priority":"high","applies_to":"无 block 标签广播","source_scope":"primary_requirement"},
    {"rule_id":"RAI-R004","rule_text":"有 block 调用时，用户 block 只执行一次，执行期间所有支持 tagged 的 logger 均激活标签。","rule_type":"interaction_rule","priority":"high","applies_to":"Block 标签上下文","source_scope":"primary_requirement","atomic_assertions":["用户 block 只执行一次。","所有支持 tagged 的 logger 在同一次 block 执行期间激活标签。"]},
    {"rule_id":"RAI-R005","rule_text":"block 正常结束或抛出异常后，临时标签都必须清理，异常继续向调用方传播。","rule_type":"state_constraint","priority":"high","applies_to":"Block 标签上下文","source_scope":"primary_requirement","atomic_assertions":["block 正常结束后清理临时标签。","block 抛出异常后清理临时标签。","block 异常继续传播给调用方。"]},
    {"rule_id":"RAI-R006","rule_text":"是否参与标签处理以广播目标是否响应 `tagged` 为能力边界。","rule_type":"fallback_constraint","priority":"medium","applies_to":"无 block 标签广播","source_scope":"primary_requirement"},
    {"rule_id":"RAI-R007","rule_text":"单个支持 tagged 的 logger 和既有普通广播行为不得回退。","rule_type":"fallback_constraint","priority":"medium","applies_to":"无 block 标签广播","source_scope":"primary_requirement"}
  ],
  "scope":{"in_scope":["多个 tagging logger","tagging 与 non-tagging logger 混合","有 block 与无 block 调用","标签清理和异常传播","既有单 logger 兼容"],"out_of_scope":["改变单个 logger 的 tagged 实现","改变日志格式","新增日志级别","修改其他广播 API"]}
}
```

## pages
```json
[
  {"page_name":"BroadcastLogger 标签广播","page_desc":"BroadcastLogger 对多个日志目标应用标签并广播消息的 API 观察面。","sections":[
    {"section_name":"多 Logger 标签上下文","section_type":"other","section_desc":"覆盖无 block 链式调用、有 block 单次执行以及标签生命周期。","module_name":"BroadcastLogger tagged","feature_names":["无 block 标签广播","Block 标签上下文"],"section_rules":["无 block 返回 BroadcastLogger","保留所有广播目标","block 只执行一次","正常及异常退出均清理标签"],"field_refs":[],"field_rule_table_refs":[]}
  ]}
]
```

## modules
```json
[
  {"module_name":"BroadcastLogger tagged","module_desc":"协调多个不同能力 logger 的标签上下文与消息广播。","features":[
    {"feature_name":"无 block 标签广播","page_name":"BroadcastLogger 标签广播","section_name":"多 Logger 标签上下文","feature_desc":"返回仍可写日志的广播对象，并仅对支持 tagged 的目标加标签。","actors":["日志调用方"],"entry_conditions":["BroadcastLogger 含一个或多个广播目标"],"rules":["返回 BroadcastLogger 而非结果数组","支持 tagged 的目标应用标签","不支持 tagged 的目标保留并接收消息"],"fields":[],"field_definitions":[],"field_rules":[],"field_rule_tables":[],"visible_elements":["返回对象类型","各 logger 接收的日志消息","标签内容"],"interactive_entries":["调用 tagged","调用 info 等日志方法"],"abnormal_scenarios":["广播目标不响应 tagged","不同 logger 的 tagged 返回值不同"],"boundary_scenarios":["单个 tagging logger","多个 tagging logger","tagging 与 non-tagging logger 混合","零个广播目标的语义待确认"],"dependencies":["BroadcastLogger","logger tagged 能力"]},
    {"feature_name":"Block 标签上下文","page_name":"BroadcastLogger 标签广播","section_name":"多 Logger 标签上下文","feature_desc":"在所有支持者的标签上下文中只执行一次用户 block，并保证退出清理。","actors":["日志调用方"],"entry_conditions":["以 block 形式调用 tagged"],"rules":["用户 block 只执行一次","全部 tagging logger 在 block 内带标签","正常和异常结束后清理标签","异常继续传播"],"fields":[],"field_definitions":[],"field_rules":[],"field_rule_tables":[],"visible_elements":["block 执行次数","block 内标签","block 后标签"],"interactive_entries":["以 block 调用 tagged","在 block 内写日志"],"abnormal_scenarios":["block 抛出异常"],"boundary_scenarios":["嵌套 tagged 的顺序待确认","线程或纤程隔离责任待确认"],"dependencies":["各 logger 的 tagged block 语义"]}
  ]}
]
```

## flows
```json
[
  {"flow_id":"RAI-FLOW-001","flow_name":"无 block 标签后继续广播","flow_type":"main_flow","business_goal":"取得带标签且保留全部目标的 BroadcastLogger，并继续发送一条日志。","trigger":"调用方执行 `broadcast_logger.tagged(tags)` 后链式写日志","preconditions":["存在多个广播目标，至少一个支持 tagged"],"steps":[
    {"step_no":1,"step_name":"构建带标签广播对象","step_type":"state_change","module_name":"BroadcastLogger tagged","feature_name":"无 block 标签广播","actor":"日志调用方","action":"无 block 调用 tagged","input_data":["标签集合","广播目标集合"],"expected_result":"返回 BroadcastLogger；支持 tagged 的目标带标签，不支持者仍在广播集合中","state_transition":{"from":"原广播目标集合","to":"带标签能力分流后的完整广播集合"},"checkpoints":["返回类型可继续写日志","目标数量未减少"],"rule_references":["RAI-R001","RAI-R002","RAI-R003","RAI-R006"],"is_key_checkpoint":true},
    {"step_no":2,"step_name":"广播日志消息","step_type":"system_response","module_name":"BroadcastLogger tagged","feature_name":"无 block 标签广播","actor":"日志调用方","action":"在返回对象上调用日志方法","expected_result":"所有广播目标收到消息，支持 tagged 的目标包含指定标签","checkpoints":["所有目标均收到一次消息","标签只作用于支持者"],"rule_references":["RAI-R002","RAI-R003"],"is_key_checkpoint":true}
  ],"postconditions":["返回对象仍可用于后续日志调用"],"success_criteria":["未返回 Array","无广播目标丢失","标签应用符合能力边界"],"related_modules":["BroadcastLogger tagged"],"priority":"P0","tags":["logging","tagged","broadcast"]},
  {"flow_id":"RAI-FLOW-002","flow_name":"Block 标签执行与清理","flow_type":"support_flow","business_goal":"在统一标签上下文中只执行一次用户 block，并在任意退出路径清理标签。","trigger":"调用方以 block 形式调用 tagged","preconditions":["存在多个支持 tagged 的 logger"],"steps":[
    {"step_no":1,"step_name":"进入标签上下文","step_type":"state_change","module_name":"BroadcastLogger tagged","feature_name":"Block 标签上下文","actor":"BroadcastLogger","action":"为所有支持 tagged 的 logger 激活指定标签","expected_result":"所有支持者在同一执行窗口内具有标签","state_transition":{"from":"无临时标签","to":"临时标签生效"},"checkpoints":["全部支持者标签生效"],"rule_references":["RAI-R004","RAI-R006"],"is_key_checkpoint":true},
    {"step_no":2,"step_name":"执行用户 block","step_type":"operation","module_name":"BroadcastLogger tagged","feature_name":"Block 标签上下文","actor":"日志调用方","action":"执行用户提供的 block","expected_result":"block 仅执行一次，其日志被广播到全部目标","checkpoints":["block 执行计数为一"],"rule_references":["RAI-R004"],"is_key_checkpoint":true},
    {"step_no":3,"step_name":"退出并清理标签","step_type":"state_change","module_name":"BroadcastLogger tagged","feature_name":"Block 标签上下文","actor":"BroadcastLogger","action":"在正常返回或异常传播前结束临时标签上下文","expected_result":"所有临时标签均被清理；异常场景保留原异常","state_transition":{"from":"临时标签生效","to":"临时标签已清理"},"checkpoints":["后续日志不含临时标签","异常继续传播"],"rule_references":["RAI-R005"],"is_key_checkpoint":true}
  ],"postconditions":["后续日志不携带本次临时标签"],"success_criteria":["block 只执行一次","全部支持者在 block 内带标签","正常和异常退出均无标签泄漏"],"related_modules":["BroadcastLogger tagged"],"priority":"P0","tags":["logging","block","cleanup"]}
]
```
