# Structured PRD

## project_info
```json
{"project_code":"OSS-BLIND-R3","project_name":"Django","business_line":"数据库 Schema Migration","prd_source":"inputs/requirement_summary.md","prd_version":"github-pr-21801"}
```

## requirement_info
```json
{
  "requirement_title":"删除 db_index 时保留命名唯一约束",
  "requirement_background":"MySQL 将唯一约束表现为唯一索引，同列同时存在普通索引与命名唯一约束时，移除字段 db_index 可能误删未变化的唯一约束。",
  "requirement_goal":"仅删除由 db_index 产生的普通非唯一索引，同时保留 Meta.constraints 中未变化的命名 UniqueConstraint 及其唯一性。",
  "explicit_rules":[
    {"rule_id":"DJG-R001","rule_text":"模型变更只移除字段的 db_index=True，不新增、删除或修改 Meta.constraints 中的命名 UniqueConstraint。","rule_type":"state_constraint","priority":"high","applies_to":"迁移差异","source_scope":"primary_requirement"},
    {"rule_id":"DJG-R002","rule_text":"定位待删除普通索引时，必须排除 Meta.constraints 中仍存在的命名唯一约束。","rule_type":"data_rule","priority":"high","applies_to":"索引选择","source_scope":"primary_requirement"},
    {"rule_id":"DJG-R003","rule_text":"生成并应用迁移后，字段上的普通非唯一索引被删除，命名唯一约束及其数据库唯一索引仍存在。","rule_type":"state_constraint","priority":"high","applies_to":"迁移后 Schema","source_scope":"primary_requirement","atomic_assertions":["迁移后字段上的普通非唯一索引不存在。","迁移后命名唯一约束及其数据库唯一索引仍存在。"]},
    {"rule_id":"DJG-R004","rule_text":"迁移 SQL 只删除普通非唯一索引，不包含删除命名唯一约束的语句。","rule_type":"data_rule","priority":"high","applies_to":"迁移 SQL","source_scope":"primary_requirement"},
    {"rule_id":"DJG-R005","rule_text":"应用迁移后写入重复字段值时，数据库仍通过命名唯一约束拒绝该写入。","rule_type":"state_constraint","priority":"high","applies_to":"数据库唯一性","source_scope":"primary_requirement"},
    {"rule_id":"DJG-R006","rule_text":"迁移前已有的合法数据在迁移后保持不变。","rule_type":"state_constraint","priority":"medium","applies_to":"既有数据","source_scope":"primary_requirement"}
  ],
  "scope":{"in_scope":["MySQL 8.4 上同列普通索引与命名唯一约束并存的迁移","删除 db_index 后的迁移 SQL、Schema 状态和唯一性行为","迁移前合法数据保持"],"out_of_scope":["新增、删除或修改 UniqueConstraint 本身","其他数据库后端的内部实现与回归范围","外键支撑索引","复合字段、条件或表达式 UniqueConstraint","迁移回滚时普通索引恢复语义"]}
}
```

## pages
```json
[
  {"page_name":"Django Migration 执行入口","page_desc":"生成并应用模型字段索引变更的系统执行面。","sections":[
    {"section_name":"索引变更与数据库状态","section_type":"other","section_desc":"识别目标索引、生成迁移并验证迁移后的 Schema 与数据约束。","module_name":"MySQL 索引迁移","feature_names":["删除普通索引并保留唯一约束"],"section_rules":["只删除由 db_index 产生的普通索引","保留未变化的命名唯一约束","迁移后数据库继续拒绝重复值"],"field_refs":[],"field_rule_table_refs":[]}
  ]}
]
```

## modules
```json
[
  {"module_name":"MySQL 索引迁移","module_desc":"处理同列普通索引与唯一约束并存时的索引删除选择和迁移后状态。","features":[
    {"feature_name":"删除普通索引并保留唯一约束","page_name":"Django Migration 执行入口","section_name":"索引变更与数据库状态","feature_desc":"字段移除 db_index 时仅删除普通索引，并保持命名唯一约束及已有数据。","actors":["Django migration executor","MySQL database"],"entry_conditions":["模型字段已设置 db_index=True","同一字段在 Meta.constraints 中存在命名 UniqueConstraint","初始迁移已应用且普通索引与唯一索引同时存在"],"rules":[
      {"rule_id":"DJG-FR001","name":"排除唯一约束索引","rule_type":"data_source_constraint","target":"index_to_remove","filter":"非唯一且由 db_index 产生，并排除仍在 Meta.constraints 中的命名约束","rule_text":"待删除对象只能是字段普通非唯一索引。"},
      {"rule_id":"DJG-FR002","name":"迁移后索引状态","rule_type":"state_constraint","target":"database_schema","condition":"迁移应用完成","value":"普通索引不存在且命名唯一约束存在","rule_text":"迁移后分别检查普通索引消失和命名唯一约束保留。"},
      {"rule_id":"DJG-FR003","name":"唯一性继续生效","rule_type":"state_constraint","target":"duplicate_insert","condition":"迁移后写入重复字段值","value":"数据库拒绝写入","rule_text":"不得仅以 introspection 结果代替唯一性行为验证。"},
      {"rule_id":"DJG-FR004","name":"既有数据保持","rule_type":"state_constraint","target":"existing_rows","condition":"迁移前后对比","value":"合法数据不变","rule_text":"迁移不得修改或丢失已有合法数据。"}
    ],"fields":[],"field_definitions":[],"field_rules":[],"field_rule_tables":[],"visible_elements":["迁移 SQL","数据库索引与约束 introspection 结果"],"interactive_entries":["生成迁移","应用迁移"],"abnormal_scenarios":["索引选择误命中命名唯一约束","迁移后重复值被错误接受"],"boundary_scenarios":["其他数据库后端行为待确认","复合字段、条件或表达式唯一约束待确认","迁移回滚语义待确认"],"dependencies":["MySQL 8.4","Django migration framework"]}
  ]}
]
```

## flows
```json
[
  {"flow_id":"DJG-FLOW-001","flow_name":"移除字段普通索引并保留命名唯一约束","flow_type":"main_flow","business_goal":"安全应用仅移除 db_index 的迁移，并保持原命名唯一约束和数据。","trigger":"模型字段从 db_index=True 改为不启用 db_index","preconditions":["同一字段同时存在普通索引和命名唯一约束","初始迁移已应用"],"steps":[
    {"step_no":1,"step_name":"生成迁移","step_type":"operation","module_name":"MySQL 索引迁移","feature_name":"删除普通索引并保留唯一约束","actor":"Django migration executor","action":"根据模型差异生成移除字段 db_index 的迁移","input_data":["字段定义","Meta.constraints"],"expected_result":"迁移只选择普通非唯一索引作为删除目标","checkpoints":["迁移 SQL 不删除命名唯一约束"],"rule_references":["DJG-R001","DJG-R002","DJG-R004"],"is_key_checkpoint":true},
    {"step_no":2,"step_name":"应用迁移","step_type":"state_change","module_name":"MySQL 索引迁移","feature_name":"删除普通索引并保留唯一约束","actor":"Django migration executor","action":"在 MySQL 8.4 应用生成的迁移","expected_result":"普通非唯一索引被删除，命名唯一约束仍存在","state_transition":{"from":"普通索引与唯一约束并存","to":"仅命名唯一约束存在"},"checkpoints":["数据库 introspection 分别确认两类索引状态"],"rule_references":["DJG-R003"],"is_key_checkpoint":true},
    {"step_no":3,"step_name":"验证数据与唯一性","step_type":"data_validation","module_name":"MySQL 索引迁移","feature_name":"删除普通索引并保留唯一约束","actor":"测试者","action":"核对既有数据并尝试写入重复字段值","expected_result":"既有合法数据不变，重复值写入被数据库拒绝","checkpoints":["迁移前后数据一致","重复值写入失败"],"rule_references":["DJG-R005","DJG-R006"],"is_key_checkpoint":true}
  ],"postconditions":["普通非唯一索引不存在","命名唯一约束继续生效","既有合法数据不变"],"success_criteria":["迁移 SQL 和最终 Schema 均未删除命名唯一约束","重复值仍被拒绝","既有数据无变化"],"related_modules":["MySQL 索引迁移"],"priority":"P0","tags":["mysql","migration","unique-constraint"]}
]
```
